# Diagnostic Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight diagnostic layer that converts raw provider, network, permission, capture, and storage failures into localized, actionable user guidance.

**Architecture:** Keep classification pure in `DiagnosticIssue.swift`, expose only the latest `currentDiagnosticIssue` through `AppState`, and render a reusable `DiagnosticIssueBanner` in Settings. Logs remain technical; diagnostics are user-facing recovery guidance.

**Tech Stack:** Swift, SwiftUI, Codable/Equatable models, Swift Testing, Python static verifiers, GitHub Actions xcodebuild.

---

## Files

- Create `LiveBuddy/Models/DiagnosticIssue.swift`
  - Pure diagnostic value types and classifier.
- Create `LiveBuddyTests/DiagnosticIssueTests.swift`
  - Unit tests for classifier rules.
- Modify `LiveBuddy/Models/AppState.swift`
  - Publish current diagnostic, set it on errors, perform recovery actions.
- Modify `LiveBuddy/Views/Settings/SettingsView.swift`
  - Add `DiagnosticIssueBanner` near the top of Settings detail pages.
- Modify `LiveBuddy/Models/InterfaceLanguage.swift`
  - Add diagnostic title/message/recovery keys for all supported languages.
- Modify `scripts/verify_p0_onboarding.py` and `scripts/verify_interface_language.py`
  - Static coverage checks.
- Modify `README.md`
  - Document actionable diagnostics.

---

## Task 1: Pure diagnostic model and classifier

**Files:**
- Create: `LiveBuddy/Models/DiagnosticIssue.swift`
- Test: `LiveBuddyTests/DiagnosticIssueTests.swift`

- [ ] **Step 1: Write failing tests**

Create `LiveBuddyTests/DiagnosticIssueTests.swift`:

```swift
import Foundation
import Testing
@testable import LiveBuddy

struct DiagnosticIssueTests {
    @Test func classifiesInvalidAPIKeyMessages() {
        let issue = DiagnosticClassifier.from(providerStatus: .invalid(message: "API_KEY_INVALID: API key not valid", checkedAt: Date()))

        #expect(issue?.code == .apiKeyInvalid)
        #expect(issue?.action == .openProviderSettings)
    }

    @Test func classifiesQuotaAndBillingMessages() {
        let issue = DiagnosticClassifier.from(connectionEvent: .serverError("Quota exceeded. Please enable billing."))

        #expect(issue?.code == .quotaOrBilling)
        #expect(issue?.kind == .provider)
    }

    @Test func classifiesModelUnavailableMessages() {
        let issue = DiagnosticClassifier.from(connectionEvent: .serverError("Model not found: gemini-live"))

        #expect(issue?.code == .modelUnavailable)
    }

    @Test func classifiesTimeoutAsNetworkIssue() {
        let issue = DiagnosticClassifier.from(connectionEvent: .sendFailed("The request timed out."))

        #expect(issue?.code == .networkTimeout)
        #expect(issue?.action == .retry)
    }

    @Test func classifiesSetupBlockingPermissionIssue() {
        let issue = DiagnosticClassifier.from(blockingIssue: .screenRecordingPermissionMissing)

        #expect(issue.code == .screenRecordingPermissionMissing)
        #expect(issue.action == .openScreenRecordingSettings)
    }

    @Test func unknownIssueKeepsUnderlyingMessage() {
        let issue = DiagnosticClassifier.from(error: NSError(domain: "LiveBuddy", code: 9, userInfo: [NSLocalizedDescriptionKey: "strange failure"]), context: .runtime)

        #expect(issue.code == .unknown)
        #expect(issue.underlyingMessage == "strange failure")
    }
}
```

- [ ] **Step 2: Verify RED**

Because local CommandLineTools cannot run Swift Testing standalone, use a one-off check to verify missing model:

```bash
cat > /tmp/diagnostic_red.swift <<'SWIFT'
import Foundation

func check() {
    let issue = DiagnosticClassifier.from(connectionEvent: .serverError("Quota exceeded"))
    precondition(issue?.code == .quotaOrBilling)
}
SWIFT
swiftc -typecheck /tmp/diagnostic_red.swift $(find LiveBuddy -name '*.swift' | sort) 2>&1 | sed -n '1,120p'
```

Expected: failure because `DiagnosticClassifier` is not in scope.

- [ ] **Step 3: Implement `DiagnosticIssue.swift`**

Create `LiveBuddy/Models/DiagnosticIssue.swift`:

```swift
import Foundation

enum DiagnosticKind: String, Codable, Equatable {
    case provider
    case network
    case permission
    case capture
    case storage
    case unknown
}

enum DiagnosticSeverity: String, Codable, Equatable {
    case info
    case warning
    case error
}

enum DiagnosticRecoveryAction: String, Codable, Equatable {
    case openProviderSettings
    case openMicrophoneSettings
    case openScreenRecordingSettings
    case retry
}

enum DiagnosticCode: String, Codable, Equatable {
    case apiKeyMissing
    case apiKeyInvalid
    case quotaOrBilling
    case modelUnavailable
    case providerServerError
    case networkUnavailable
    case networkTimeout
    case connectionLost
    case microphonePermissionMissing
    case screenRecordingPermissionMissing
    case microphoneUnavailable
    case screenAudioUnavailable
    case settingsSaveFailed
    case transcriptSaveFailed
    case unknown
}

enum DiagnosticContext: String, Codable, Equatable {
    case startup
    case providerCheck
    case connection
    case capture
    case storage
    case runtime
}

struct DiagnosticIssue: Codable, Equatable, Identifiable {
    var id: DiagnosticCode { code }
    let code: DiagnosticCode
    let kind: DiagnosticKind
    let severity: DiagnosticSeverity
    let titleKey: InterfaceText
    let messageKey: InterfaceText
    let recoveryKey: InterfaceText
    let underlyingMessage: String?
    let action: DiagnosticRecoveryAction?
}

struct DiagnosticClassifier {
    static func from(blockingIssue: SetupBlockingIssue) -> DiagnosticIssue {
        switch blockingIssue {
        case .apiKeyMissing:
            return issue(.apiKeyMissing, kind: .provider, title: .diagnosticAPIKeyMissingTitle, message: .diagnosticAPIKeyMissingMessage, recovery: .diagnosticOpenProviderRecovery, action: .openProviderSettings)
        case .microphonePermissionMissing:
            return issue(.microphonePermissionMissing, kind: .permission, title: .diagnosticMicrophonePermissionTitle, message: .diagnosticMicrophonePermissionMessage, recovery: .diagnosticOpenMicrophoneRecovery, action: .openMicrophoneSettings)
        case .screenRecordingPermissionMissing:
            return issue(.screenRecordingPermissionMissing, kind: .permission, title: .diagnosticScreenRecordingPermissionTitle, message: .diagnosticScreenRecordingPermissionMessage, recovery: .diagnosticOpenScreenRecordingRecovery, action: .openScreenRecordingSettings)
        }
    }

    static func from(providerStatus: ProviderHealthStatus) -> DiagnosticIssue? {
        switch providerStatus {
        case .missing:
            return issue(.apiKeyMissing, kind: .provider, title: .diagnosticAPIKeyMissingTitle, message: .diagnosticAPIKeyMissingMessage, recovery: .diagnosticOpenProviderRecovery, action: .openProviderSettings)
        case .invalid(let message, _), .failed(let message, _):
            return classify(message: message, context: .providerCheck)
        case .unchecked, .checking, .valid:
            return nil
        }
    }

    static func from(connectionEvent: LiveConnectionEvent) -> DiagnosticIssue? {
        switch connectionEvent {
        case .socketOpened, .sessionReady:
            return nil
        case .disconnected(let message), .socketClosed(let message), .sendFailed(let message):
            return classify(message: message, context: .connection, fallbackCode: .connectionLost)
        case .serverError(let message):
            return classify(message: message, context: .connection, fallbackCode: .providerServerError)
        case .parseFailed(let message):
            return issue(.providerServerError, kind: .provider, title: .diagnosticProviderErrorTitle, message: .diagnosticProviderErrorMessage, recovery: .diagnosticRetryRecovery, underlying: message, action: .retry)
        }
    }

    static func from(error: Error, context: DiagnosticContext) -> DiagnosticIssue {
        if let microphoneError = error as? MicrophoneCaptureError {
            return issue(.microphoneUnavailable, kind: .capture, title: .diagnosticMicrophoneUnavailableTitle, message: .diagnosticMicrophoneUnavailableMessage, recovery: .diagnosticOpenMicrophoneRecovery, underlying: microphoneError.localizedDescription, action: .openMicrophoneSettings)
        }
        if let screenError = error as? ScreenAudioCaptureError {
            return issue(.screenAudioUnavailable, kind: .capture, title: .diagnosticScreenAudioUnavailableTitle, message: .diagnosticScreenAudioUnavailableMessage, recovery: .diagnosticOpenScreenRecordingRecovery, underlying: screenError.localizedDescription, action: .openScreenRecordingSettings)
        }
        return classify(message: error.localizedDescription, context: context) ?? unknown(error.localizedDescription)
    }

    static func storage(_ code: DiagnosticCode, underlyingMessage: String) -> DiagnosticIssue {
        let title: InterfaceText = code == .settingsSaveFailed ? .diagnosticSettingsSaveFailedTitle : .diagnosticTranscriptSaveFailedTitle
        let message: InterfaceText = code == .settingsSaveFailed ? .diagnosticSettingsSaveFailedMessage : .diagnosticTranscriptSaveFailedMessage
        return issue(code, kind: .storage, title: title, message: message, recovery: .diagnosticCheckDiskRecovery, underlying: underlyingMessage, action: nil)
    }

    private static func classify(message: String, context: DiagnosticContext, fallbackCode: DiagnosticCode? = nil) -> DiagnosticIssue? {
        let normalized = message.lowercased()
        if contains(normalized, ["api key", "api_key_invalid", "apikey", "unauthorized", "forbidden"]) {
            return issue(.apiKeyInvalid, kind: .provider, title: .diagnosticAPIKeyInvalidTitle, message: .diagnosticAPIKeyInvalidMessage, recovery: .diagnosticOpenProviderRecovery, underlying: message, action: .openProviderSettings)
        }
        if contains(normalized, ["quota", "billing", "payment", "exceeded", "resource exhausted"]) {
            return issue(.quotaOrBilling, kind: .provider, title: .diagnosticQuotaTitle, message: .diagnosticQuotaMessage, recovery: .diagnosticQuotaRecovery, underlying: message, action: .openProviderSettings)
        }
        if contains(normalized, ["model not found", "unsupported model"]) || (normalized.contains("invalid argument") && normalized.contains("model")) {
            return issue(.modelUnavailable, kind: .provider, title: .diagnosticModelUnavailableTitle, message: .diagnosticModelUnavailableMessage, recovery: .diagnosticRetryRecovery, underlying: message, action: .retry)
        }
        if contains(normalized, ["timeout", "timed out", "deadline"]) {
            return issue(.networkTimeout, kind: .network, title: .diagnosticNetworkTimeoutTitle, message: .diagnosticNetworkTimeoutMessage, recovery: .diagnosticRetryRecovery, underlying: message, action: .retry)
        }
        if contains(normalized, ["offline", "network", "internet", "cannot connect", "dns", "tls", "secure connection"]) {
            return issue(.networkUnavailable, kind: .network, title: .diagnosticNetworkUnavailableTitle, message: .diagnosticNetworkUnavailableMessage, recovery: .diagnosticRetryRecovery, underlying: message, action: .retry)
        }
        if let fallbackCode {
            switch fallbackCode {
            case .connectionLost:
                return issue(.connectionLost, kind: .network, title: .diagnosticConnectionLostTitle, message: .diagnosticConnectionLostMessage, recovery: .diagnosticRetryRecovery, underlying: message, action: .retry)
            case .providerServerError:
                return issue(.providerServerError, kind: .provider, title: .diagnosticProviderErrorTitle, message: .diagnosticProviderErrorMessage, recovery: .diagnosticRetryRecovery, underlying: message, action: .retry)
            default:
                break
            }
        }
        return nil
    }

    private static func unknown(_ message: String) -> DiagnosticIssue {
        issue(.unknown, kind: .unknown, title: .diagnosticUnknownTitle, message: .diagnosticUnknownMessage, recovery: .diagnosticRetryRecovery, underlying: message, action: .retry)
    }

    private static func contains(_ value: String, _ needles: [String]) -> Bool {
        needles.contains { value.contains($0) }
    }

    private static func issue(_ code: DiagnosticCode, kind: DiagnosticKind, severity: DiagnosticSeverity = .error, title: InterfaceText, message: InterfaceText, recovery: InterfaceText, underlying: String? = nil, action: DiagnosticRecoveryAction?) -> DiagnosticIssue {
        DiagnosticIssue(code: code, kind: kind, severity: severity, titleKey: title, messageKey: message, recoveryKey: recovery, underlyingMessage: underlying, action: action)
    }
}
```

- [ ] **Step 4: Add temporary localization stubs if needed**

Do not commit if typecheck fails only because `InterfaceText` keys are missing; Task 2 adds localization keys. If you want each task to compile independently, add English-only cases and translations now, then complete all languages in Task 3.

- [ ] **Step 5: Verify pure classifier with one-off check**

Run:

```bash
cat > /tmp/diagnostic_check.swift <<'SWIFT'
import Foundation

@main
struct DiagnosticCheck {
    static func main() {
        let quota = DiagnosticClassifier.from(connectionEvent: .serverError("Quota exceeded. Please enable billing."))
        precondition(quota?.code == .quotaOrBilling)
        let timeout = DiagnosticClassifier.from(connectionEvent: .sendFailed("The request timed out."))
        precondition(timeout?.code == .networkTimeout)
        let permission = DiagnosticClassifier.from(blockingIssue: .screenRecordingPermissionMissing)
        precondition(permission.action == .openScreenRecordingSettings)
    }
}
SWIFT
swiftc /tmp/diagnostic_check.swift $(find LiveBuddy -name '*.swift' | sort) -o /tmp/diagnostic_check
/tmp/diagnostic_check
```

Expected: exits 0 after Task 2 localization exists. If Task 1 is committed before localization, run after Task 2.

- [ ] **Step 6: Commit Task 1**

```bash
git add LiveBuddy/Models/DiagnosticIssue.swift LiveBuddyTests/DiagnosticIssueTests.swift
git commit -m "feat: add diagnostic classifier"
```

---

## Task 2: Localization keys for diagnostics

**Files:**
- Modify: `LiveBuddy/Models/InterfaceLanguage.swift`
- Modify: `scripts/verify_interface_language.py`

- [ ] **Step 1: Add `InterfaceText` cases**

Add these cases near existing setup/error keys:

```swift
case diagnosticAPIKeyMissingTitle
case diagnosticAPIKeyMissingMessage
case diagnosticAPIKeyInvalidTitle
case diagnosticAPIKeyInvalidMessage
case diagnosticQuotaTitle
case diagnosticQuotaMessage
case diagnosticQuotaRecovery
case diagnosticModelUnavailableTitle
case diagnosticModelUnavailableMessage
case diagnosticProviderErrorTitle
case diagnosticProviderErrorMessage
case diagnosticNetworkUnavailableTitle
case diagnosticNetworkUnavailableMessage
case diagnosticNetworkTimeoutTitle
case diagnosticNetworkTimeoutMessage
case diagnosticConnectionLostTitle
case diagnosticConnectionLostMessage
case diagnosticMicrophonePermissionTitle
case diagnosticMicrophonePermissionMessage
case diagnosticScreenRecordingPermissionTitle
case diagnosticScreenRecordingPermissionMessage
case diagnosticMicrophoneUnavailableTitle
case diagnosticMicrophoneUnavailableMessage
case diagnosticScreenAudioUnavailableTitle
case diagnosticScreenAudioUnavailableMessage
case diagnosticSettingsSaveFailedTitle
case diagnosticSettingsSaveFailedMessage
case diagnosticTranscriptSaveFailedTitle
case diagnosticTranscriptSaveFailedMessage
case diagnosticUnknownTitle
case diagnosticUnknownMessage
case diagnosticOpenProviderRecovery
case diagnosticOpenMicrophoneRecovery
case diagnosticOpenScreenRecordingRecovery
case diagnosticRetryRecovery
case diagnosticCheckDiskRecovery
case diagnosticDetails
case diagnosticDismiss
```

- [ ] **Step 2: Add English translations**

Use concise strings:

```swift
.diagnosticAPIKeyMissingTitle: "API key required",
.diagnosticAPIKeyMissingMessage: "LiveBuddy needs a Gemini API key before translation can start.",
.diagnosticAPIKeyInvalidTitle: "API key is invalid",
.diagnosticAPIKeyInvalidMessage: "Gemini rejected the current API key.",
.diagnosticQuotaTitle: "Gemini quota or billing issue",
.diagnosticQuotaMessage: "Gemini reported quota, billing, or payment limits for this key.",
.diagnosticQuotaRecovery: "Check your Google AI Studio quota and billing settings, or use another key.",
.diagnosticModelUnavailableTitle: "Translation model unavailable",
.diagnosticModelUnavailableMessage: "Gemini reported that the selected live translation model is unavailable.",
.diagnosticProviderErrorTitle: "Gemini provider error",
.diagnosticProviderErrorMessage: "Gemini returned an error before LiveBuddy could continue.",
.diagnosticNetworkUnavailableTitle: "Network unavailable",
.diagnosticNetworkUnavailableMessage: "LiveBuddy could not reach Gemini over the network.",
.diagnosticNetworkTimeoutTitle: "Network timed out",
.diagnosticNetworkTimeoutMessage: "The request to Gemini took too long to finish.",
.diagnosticConnectionLostTitle: "Connection lost",
.diagnosticConnectionLostMessage: "The live translation connection was interrupted.",
.diagnosticMicrophonePermissionTitle: "Microphone permission required",
.diagnosticMicrophonePermissionMessage: "The selected audio source needs microphone access.",
.diagnosticScreenRecordingPermissionTitle: "Screen Recording permission required",
.diagnosticScreenRecordingPermissionMessage: "System audio capture needs Screen Recording permission.",
.diagnosticMicrophoneUnavailableTitle: "Microphone unavailable",
.diagnosticMicrophoneUnavailableMessage: "LiveBuddy could not start the selected microphone.",
.diagnosticScreenAudioUnavailableTitle: "Screen audio unavailable",
.diagnosticScreenAudioUnavailableMessage: "LiveBuddy could not start system audio capture.",
.diagnosticSettingsSaveFailedTitle: "Settings could not be saved",
.diagnosticSettingsSaveFailedMessage: "LiveBuddy could not write the settings file.",
.diagnosticTranscriptSaveFailedTitle: "Transcript could not be saved",
.diagnosticTranscriptSaveFailedMessage: "LiveBuddy could not write transcript history.",
.diagnosticUnknownTitle: "Unexpected error",
.diagnosticUnknownMessage: "LiveBuddy hit an error that does not match a known category.",
.diagnosticOpenProviderRecovery: "Open API Provider settings and update your Gemini key.",
.diagnosticOpenMicrophoneRecovery: "Open macOS Microphone settings and allow LiveBuddy.",
.diagnosticOpenScreenRecordingRecovery: "Open macOS Screen Recording settings and allow LiveBuddy.",
.diagnosticRetryRecovery: "Check the issue, then try again.",
.diagnosticCheckDiskRecovery: "Check disk space and file permissions, then try again.",
.diagnosticDetails: "Details",
.diagnosticDismiss: "Dismiss",
```

- [ ] **Step 3: Add translations for the other seven languages**

Use clear equivalents. Keep them short. A script is acceptable if it inserts these keys consistently after `.apiKeyMissingRecovery` in every language dictionary.

- [ ] **Step 4: Update interface verifier**

Add all diagnostic keys to `required_keys` in `scripts/verify_interface_language.py`.

- [ ] **Step 5: Verify**

Run:

```bash
python3 scripts/verify_interface_language.py
rm -rf /tmp/livebuddy_typecheck && mkdir -p /tmp/livebuddy_typecheck
cp -R LiveBuddy /tmp/livebuddy_typecheck/LiveBuddy
python3 - <<'PY'
from pathlib import Path
for p in Path('/tmp/livebuddy_typecheck/LiveBuddy').rglob('*.swift'):
    text = p.read_text()
    marker = '\n#Preview {'
    idx = text.find(marker)
    if idx != -1:
        p.write_text(text[:idx].rstrip() + '\n')
PY
swiftc -typecheck $(find /tmp/livebuddy_typecheck/LiveBuddy -name '*.swift' | sort)
```

Expected: verifier passes; typecheck exits 0 with only known Sendable warnings if any.

- [ ] **Step 6: Commit Task 2**

```bash
git add LiveBuddy/Models/InterfaceLanguage.swift scripts/verify_interface_language.py
git commit -m "feat: localize diagnostic guidance"
```

---

## Task 3: AppState diagnostic integration

**Files:**
- Modify: `LiveBuddy/Models/AppState.swift`
- Modify: `LiveBuddy/Models/UserFacingError.swift` if needed

- [ ] **Step 1: Add AppState diagnostic state**

Add near existing published error state:

```swift
@Published private(set) var currentDiagnosticIssue: DiagnosticIssue?
```

- [ ] **Step 2: Add helper methods**

Add to `AppState`:

```swift
func clearDiagnosticIssue() {
    currentDiagnosticIssue = nil
}

func performDiagnosticRecoveryAction(_ action: DiagnosticRecoveryAction) {
    switch action {
    case .openProviderSettings:
        openSettingsWindow()
    case .openMicrophoneSettings:
        openMicrophoneSettings()
    case .openScreenRecordingSettings:
        openScreenRecordingSettings()
    case .retry:
        Task { await start() }
    }
}

private func setDiagnosticIssue(_ issue: DiagnosticIssue?) {
    currentDiagnosticIssue = issue
}
```

- [ ] **Step 3: Wire setup preflight failures**

In `start()`, when preflight is blocked, add:

```swift
setDiagnosticIssue(DiagnosticClassifier.from(blockingIssue: issue))
```

- [ ] **Step 4: Wire start/connect/capture catch block**

In `start()` catch block, before `updateStatus`, add:

```swift
let diagnostic = DiagnosticClassifier.from(error: error, context: .startup)
setDiagnosticIssue(diagnostic)
updateStatus(settings.interfaceLanguage.localized(diagnostic.titleKey), level: .error, log: true)
```

- [ ] **Step 5: Wire connection events**

In `handleConnectionEvent(_:)`, after appending/logging terminal errors, set:

```swift
if let issue = DiagnosticClassifier.from(connectionEvent: event) {
    setDiagnosticIssue(issue)
}
```

- [ ] **Step 6: Wire storage failures**

In `saveSettings()` catch path:

```swift
setDiagnosticIssue(DiagnosticClassifier.storage(.settingsSaveFailed, underlyingMessage: error.localizedDescription))
```

In transcript save catch path:

```swift
setDiagnosticIssue(DiagnosticClassifier.storage(.transcriptSaveFailed, underlyingMessage: error.localizedDescription))
```

- [ ] **Step 7: Wire keychain save failure**

In `updateAPIKey(_:)` catch path:

```swift
setDiagnosticIssue(DiagnosticClassifier.storage(.settingsSaveFailed, underlyingMessage: error.localizedDescription))
```

- [ ] **Step 8: Verify typecheck**

Run the full temp typecheck command from Task 2.

- [ ] **Step 9: Commit Task 3**

```bash
git add LiveBuddy/Models/AppState.swift
git commit -m "feat: surface diagnostic issues in app state"
```

---

## Task 4: Settings diagnostic banner UI

**Files:**
- Modify: `LiveBuddy/Views/Settings/SettingsView.swift`

- [ ] **Step 1: Add banner in detail area**

Wrap the detail `Group` in a `VStack` that shows a banner first:

```swift
VStack(spacing: 0) {
    if let issue = appState.currentDiagnosticIssue {
        DiagnosticIssueBanner(issue: issue)
            .padding(.horizontal, 20)
            .padding(.top, 12)
    }
    Group { ... existing switch ... }
}
```

- [ ] **Step 2: Add `DiagnosticIssueBanner`**

Add below `PreflightTestStepRow`:

```swift
private struct DiagnosticIssueBanner: View {
    @EnvironmentObject private var appState: AppState
    let issue: DiagnosticIssue

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: iconName)
                .foregroundStyle(iconColor)
                .frame(width: 20)
            VStack(alignment: .leading, spacing: 4) {
                Text(appState.t(issue.titleKey))
                    .font(.subheadline.weight(.semibold))
                Text(appState.t(issue.messageKey))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text(appState.t(issue.recoveryKey))
                    .font(.caption)
                if let underlying = issue.underlyingMessage, !underlying.isEmpty {
                    Text("\(appState.t(.diagnosticDetails)): \(underlying)")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
            }
            Spacer()
            if let action = issue.action {
                Button(actionTitle(for: action)) {
                    appState.performDiagnosticRecoveryAction(action)
                }
                .controlSize(.small)
            }
            Button(appState.t(.diagnosticDismiss)) {
                appState.clearDiagnosticIssue()
            }
            .controlSize(.small)
        }
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 12).fill(Color(nsColor: .controlBackgroundColor)))
    }

    private func actionTitle(for action: DiagnosticRecoveryAction) -> String {
        switch action {
        case .openProviderSettings: appState.t(.apiProvider)
        case .openMicrophoneSettings: appState.t(.openMicrophoneSettings)
        case .openScreenRecordingSettings: appState.t(.openScreenRecordingSettings)
        case .retry: appState.t(.start)
        }
    }

    private var iconName: String {
        switch issue.severity {
        case .info: "info.circle.fill"
        case .warning: "exclamationmark.triangle.fill"
        case .error: "xmark.octagon.fill"
        }
    }

    private var iconColor: Color {
        switch issue.severity {
        case .info: .blue
        case .warning: .orange
        case .error: .red
        }
    }
}
```

- [ ] **Step 3: Verify typecheck**

Run the full temp typecheck command.

- [ ] **Step 4: Commit Task 4**

```bash
git add LiveBuddy/Views/Settings/SettingsView.swift
git commit -m "feat: show diagnostic guidance banner"
```

---

## Task 5: Static verifier and docs

**Files:**
- Modify: `scripts/verify_p0_onboarding.py`
- Modify: `README.md`

- [ ] **Step 1: Extend P0 verifier**

Add required file:

```python
"LiveBuddy/Models/DiagnosticIssue.swift",
```

Add checks:

```python
diagnostic_file = root / "LiveBuddy/Models/DiagnosticIssue.swift"
if diagnostic_file.exists():
    text = diagnostic_file.read_text()
    for token in ["enum DiagnosticCode", "struct DiagnosticIssue", "struct DiagnosticClassifier", "quotaOrBilling", "networkTimeout"]:
        if token not in text:
            errors.append(f"DiagnosticIssue.swift missing {token}")
    for forbidden in ["GeminiLiveTranslateClient", "MicrophoneCapture(", "ScreenAudioCapture("]:
        if forbidden in text:
            errors.append(f"Diagnostic classifier must stay pure and not reference {forbidden}")
```

Add AppState checks:

```python
for token in ["currentDiagnosticIssue", "clearDiagnosticIssue", "performDiagnosticRecoveryAction", "DiagnosticClassifier"]:
    if token not in text:
        errors.append(f"AppState must expose diagnostic guidance through {token}")
```

Add SettingsView checks:

```python
if "DiagnosticIssueBanner" not in text or "currentDiagnosticIssue" not in text:
    errors.append("SettingsView must render diagnostic guidance banner")
```

- [ ] **Step 2: Update README**

Add Key Feature bullet:

```markdown
*   **Actionable Diagnostics**: Translates provider, network, permission, capture, and storage failures into clear messages with next-step recovery actions.
```

Add Configuration row:

```markdown
| **Diagnostics** | Actionable error guidance | Shows the latest issue with a clear explanation, recovery hint, and one-click action where available. |
```

- [ ] **Step 3: Full local verification**

Run:

```bash
python3 scripts/verify_p0_onboarding.py && python3 scripts/verify_interface_language.py && python3 scripts/verify_ci_workflow.py
rm -rf /tmp/livebuddy_typecheck && mkdir -p /tmp/livebuddy_typecheck
cp -R LiveBuddy /tmp/livebuddy_typecheck/LiveBuddy
python3 - <<'PY'
from pathlib import Path
for p in Path('/tmp/livebuddy_typecheck/LiveBuddy').rglob('*.swift'):
    text = p.read_text()
    marker = '\n#Preview {'
    idx = text.find(marker)
    if idx != -1:
        p.write_text(text[:idx].rstrip() + '\n')
PY
swiftc -typecheck $(find /tmp/livebuddy_typecheck/LiveBuddy -name '*.swift' | sort)
```

Expected: verifier passes; typecheck exits 0 with only known warnings.

- [ ] **Step 4: Commit Task 5**

```bash
git add scripts/verify_p0_onboarding.py README.md
git commit -m "docs: document diagnostic guidance"
```

---

## Task 6: Push and CI

- [ ] **Step 1: Push**

```bash
git push target HEAD:main
```

- [ ] **Step 2: Watch CI**

```bash
gh run list --repo SuLea-IT/translate-macos --limit 5
gh run watch <new-run-id> --repo SuLea-IT/translate-macos --exit-status
```

- [ ] **Step 3: Debug CI if needed**

Use `superpowers:systematic-debugging` before changing anything.

---

## Self-Review

- Spec coverage: model/classifier Task 1, localization Task 2, AppState Task 3, UI Task 4, verifier/docs Task 5, CI Task 6.
- No persistent history or telemetry added.
- Type names match between tasks.
- Pure classifier remains free of heavy runtime objects.
