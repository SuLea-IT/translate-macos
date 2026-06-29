# P0 Onboarding and Permissions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lightweight first-run/setup checklist, permission status checks, provider health status, start preflight, friendly errors, and localized guidance for LiveBuddy.

**Architecture:** Follow the design in `docs/superpowers/specs/2026-06-29-p0-onboarding-permissions-design.md`. Borrow PermissionFlow's separation between permission status and UI, QuickRecorder's distinction between permission preflight and capture runtime, and Scripta's setup-before-recording pattern, but implement LiveBuddy-owned services and models without adding dependencies. Keep state as small value types, refresh only on launch/settings/open/start/user action, and avoid timers or capture-stream creation for permission checks.

**Tech Stack:** Swift, SwiftUI, AVFoundation, CoreGraphics screen-capture permission APIs, AppKit `NSWorkspace`, Swift Testing, existing Xcode project and GitHub Actions.

---

## File Structure

Create:

- `LiveBuddy/Models/PermissionStatus.swift` — pure permission/checklist/preflight value models.
- `LiveBuddy/Models/ProviderHealthStatus.swift` — pure provider API-key health value models.
- `LiveBuddy/Models/UserFacingError.swift` — typed user-friendly error model and mapping helpers.
- `LiveBuddy/Services/SystemSettingsNavigator.swift` — AppKit wrapper for privacy Settings URLs.
- `LiveBuddy/Services/PermissionStatusService.swift` — lightweight microphone/screen-recording status and request service.
- `LiveBuddy/Services/ProviderHealthService.swift` — extracted Gemini API-key validation service.
- `LiveBuddy/Views/Settings/SetupChecklistView.swift` — reusable SwiftUI checklist card.
- `LiveBuddyTests/SetupChecklistTests.swift` — derivation/preflight tests.
- `LiveBuddyTests/UserFacingErrorTests.swift` — low-level-error mapping tests.
- `LiveBuddyTests/ProviderHealthStatusTests.swift` — provider status tests.
- `scripts/verify_p0_onboarding.py` — static verifier for P0 integration.

Modify:

- `LiveBuddy/Models/AppState.swift` — add setup checklist state, use services, run preflight before connecting/capture, expose permission/settings actions.
- `LiveBuddy/Models/InterfaceLanguage.swift` — add localized setup, permission, provider-health, and status keys for all eight languages.
- `LiveBuddy/Services/MicrophoneCapture.swift` — expose errors in a way `UserFacingError` can map without string parsing.
- `LiveBuddy/Services/ScreenAudioCapture.swift` — expose errors in a way `UserFacingError` can map without string parsing.
- `LiveBuddy/Views/Settings/SettingsView.swift` — render `SetupChecklistView` in provider page and setup sheet.
- `LiveBuddy/Views/MenuBar/MenuBarView.swift` — show compact setup warning and settings shortcut when setup is incomplete.
- `README.md` — document first-run checklist and permissions flow.
- `scripts/verify_interface_language.py` — require new localization keys across all languages.

## Reference Rules While Implementing

- Do not copy source from PermissionFlow, QuickRecorder, Scripta, or any other project.
- Borrow patterns only: status-service separation, explicit user-triggered permission requests, no polling, and setup preflight before capture.
- Keep permission status checks lightweight: do not create `SCStream`, `AVAudioEngine`, or WebSocket clients during checklist refresh.
- Keep `AppState` as orchestrator only; move provider and permission details into services.

---

### Task 1: Pure setup and permission models

**Files:**
- Create: `LiveBuddy/Models/PermissionStatus.swift`
- Test: `LiveBuddyTests/SetupChecklistTests.swift`

- [ ] **Step 1: Write the failing tests**

Add this to `LiveBuddyTests/SetupChecklistTests.swift`:

```swift
import Foundation
import Testing
@testable import LiveBuddy

struct SetupChecklistTests {
    @Test func screenAudioRequiresOnlyScreenRecordingPermission() {
        let state = SetupChecklistState.derive(
            audioSource: .screen,
            apiKey: .valid(checkedAt: Date()),
            microphone: PermissionStatus(requirement: .microphone, state: .denied, checkedAt: Date()),
            screenRecording: PermissionStatus(requirement: .screenRecording, state: .granted, checkedAt: Date())
        )

        #expect(state.microphone.requirementState == .notNeeded)
        #expect(state.screenRecording.requirementState == .satisfied)
        #expect(state.blockingIssues.isEmpty)
    }

    @Test func microphoneSourceBlocksWhenMicrophonePermissionMissing() {
        let state = SetupChecklistState.derive(
            audioSource: .microphone,
            apiKey: .valid(checkedAt: Date()),
            microphone: PermissionStatus(requirement: .microphone, state: .denied, checkedAt: Date()),
            screenRecording: PermissionStatus(requirement: .screenRecording, state: .granted, checkedAt: Date())
        )

        #expect(state.microphone.requirementState == .blocked)
        #expect(state.blockingIssues == [.microphonePermissionMissing])
    }

    @Test func bothSourceRequiresBothPermissions() {
        let state = SetupChecklistState.derive(
            audioSource: .both,
            apiKey: .valid(checkedAt: Date()),
            microphone: PermissionStatus(requirement: .microphone, state: .granted, checkedAt: Date()),
            screenRecording: PermissionStatus(requirement: .screenRecording, state: .denied, checkedAt: Date())
        )

        #expect(state.microphone.requirementState == .satisfied)
        #expect(state.screenRecording.requirementState == .blocked)
        #expect(state.blockingIssues == [.screenRecordingPermissionMissing])
    }

    @Test func emptyApiKeyBlocksStartBeforePermissionsMatter() {
        let state = SetupChecklistState.derive(
            audioSource: .screen,
            apiKey: .missing,
            microphone: PermissionStatus(requirement: .microphone, state: .granted, checkedAt: Date()),
            screenRecording: PermissionStatus(requirement: .screenRecording, state: .granted, checkedAt: Date())
        )

        #expect(state.blockingIssues.contains(.apiKeyMissing))
    }
}
```

- [ ] **Step 2: Verify the test fails for the expected reason**

Run:

```bash
xcodebuild test -project LiveBuddy.xcodeproj -scheme LiveBuddy -destination 'platform=macOS' -only-testing:LiveBuddyTests/SetupChecklistTests CODE_SIGNING_ALLOWED=NO
```

Expected on a machine with Xcode: compile failure because `SetupChecklistState`, `PermissionStatus`, `PermissionRequirement`, and `ProviderHealthStatus` do not exist yet.

Local fallback on this machine:

```bash
python3 scripts/verify_p0_onboarding.py
```

Expected before implementation: failure showing missing `LiveBuddy/Models/PermissionStatus.swift`.

- [ ] **Step 3: Implement minimal pure models**

Create `LiveBuddy/Models/PermissionStatus.swift`:

```swift
import Foundation

enum PermissionRequirement: String, Codable, CaseIterable, Equatable {
    case microphone
    case screenRecording
}

enum PermissionGrantState: String, Codable, Equatable {
    case granted
    case denied
    case notDetermined
    case restricted
    case unknown

    var isGranted: Bool { self == .granted }
}

struct PermissionStatus: Codable, Equatable {
    let requirement: PermissionRequirement
    let state: PermissionGrantState
    let checkedAt: Date

    static func unknown(_ requirement: PermissionRequirement, checkedAt: Date = Date()) -> PermissionStatus {
        PermissionStatus(requirement: requirement, state: .unknown, checkedAt: checkedAt)
    }
}

enum ChecklistRequirementState: String, Codable, Equatable {
    case satisfied
    case blocked
    case notNeeded
    case unknown
}

struct PermissionChecklistItem: Codable, Equatable {
    let requirement: PermissionRequirement
    let permissionState: PermissionGrantState
    let requirementState: ChecklistRequirementState
    let checkedAt: Date
}

enum SetupBlockingIssue: String, Codable, CaseIterable, Equatable {
    case apiKeyMissing
    case microphonePermissionMissing
    case screenRecordingPermissionMissing
}

struct SetupChecklistState: Codable, Equatable {
    let apiKey: ProviderHealthStatus
    let microphone: PermissionChecklistItem
    let screenRecording: PermissionChecklistItem
    let blockingIssues: [SetupBlockingIssue]

    var canStart: Bool { blockingIssues.isEmpty }

    static let initial = SetupChecklistState.derive(
        audioSource: .screen,
        apiKey: .missing,
        microphone: .unknown(.microphone),
        screenRecording: .unknown(.screenRecording)
    )

    static func derive(
        audioSource: AudioSource,
        apiKey: ProviderHealthStatus,
        microphone: PermissionStatus,
        screenRecording: PermissionStatus
    ) -> SetupChecklistState {
        var issues: [SetupBlockingIssue] = []
        if apiKey.blocksStart {
            issues.append(.apiKeyMissing)
        }

        let needsMicrophone = audioSource == .microphone || audioSource == .both
        let needsScreen = audioSource == .screen || audioSource == .both
        let microphoneItem = item(for: microphone, needed: needsMicrophone)
        let screenItem = item(for: screenRecording, needed: needsScreen)

        if microphoneItem.requirementState == .blocked {
            issues.append(.microphonePermissionMissing)
        }
        if screenItem.requirementState == .blocked {
            issues.append(.screenRecordingPermissionMissing)
        }

        return SetupChecklistState(
            apiKey: apiKey,
            microphone: microphoneItem,
            screenRecording: screenItem,
            blockingIssues: issues
        )
    }

    private static func item(for status: PermissionStatus, needed: Bool) -> PermissionChecklistItem {
        let requirementState: ChecklistRequirementState
        if !needed {
            requirementState = .notNeeded
        } else if status.state == .granted {
            requirementState = .satisfied
        } else if status.state == .unknown || status.state == .notDetermined {
            requirementState = .unknown
        } else {
            requirementState = .blocked
        }

        return PermissionChecklistItem(
            requirement: status.requirement,
            permissionState: status.state,
            requirementState: requirementState,
            checkedAt: status.checkedAt
        )
    }
}
```

Create `LiveBuddy/Models/ProviderHealthStatus.swift` with the minimal type required by the tests:

```swift
import Foundation

enum ProviderHealthStatus: Codable, Equatable {
    case missing
    case unchecked
    case checking
    case valid(checkedAt: Date)
    case invalid(message: String, checkedAt: Date)
    case failed(message: String, checkedAt: Date)

    var blocksStart: Bool {
        switch self {
        case .missing:
            true
        case .unchecked, .checking, .valid, .invalid, .failed:
            false
        }
    }
}
```

- [ ] **Step 4: Run the tests and verifier**

Run:

```bash
python3 scripts/verify_p0_onboarding.py
xcodebuild test -project LiveBuddy.xcodeproj -scheme LiveBuddy -destination 'platform=macOS' -only-testing:LiveBuddyTests/SetupChecklistTests CODE_SIGNING_ALLOWED=NO
```

Expected: verifier passes; Xcode test passes on a machine with full Xcode.

- [ ] **Step 5: Commit**

```bash
git add LiveBuddy/Models/PermissionStatus.swift LiveBuddy/Models/ProviderHealthStatus.swift LiveBuddyTests/SetupChecklistTests.swift scripts/verify_p0_onboarding.py
git commit -m "feat: add setup checklist models"
```

---

### Task 2: User-facing error model and mappings

**Files:**
- Create: `LiveBuddy/Models/UserFacingError.swift`
- Modify: `LiveBuddy/Models/InterfaceLanguage.swift`
- Test: `LiveBuddyTests/UserFacingErrorTests.swift`

- [ ] **Step 1: Write the failing tests**

Add `LiveBuddyTests/UserFacingErrorTests.swift`:

```swift
import Testing
@testable import LiveBuddy

struct UserFacingErrorTests {
    @Test func microphoneDeniedMapsToPermissionRecovery() {
        let error = UserFacingError.microphonePermissionMissing

        #expect(error.kind == .permission)
        #expect(error.action == .openMicrophoneSettings)
        #expect(error.titleKey == .microphonePermissionRequired)
    }

    @Test func missingApiKeyMapsToProviderRecovery() {
        let error = UserFacingError.apiKeyMissing

        #expect(error.kind == .provider)
        #expect(error.action == .openProviderSettings)
        #expect(error.titleKey == .apiKeyMissingTitle)
    }

    @Test func setupBlockingIssueMapsToFirstActionableError() {
        let error = UserFacingError.from(blockingIssues: [.screenRecordingPermissionMissing])

        #expect(error == .screenRecordingPermissionMissing)
    }
}
```

- [ ] **Step 2: Verify failure**

Run:

```bash
xcodebuild test -project LiveBuddy.xcodeproj -scheme LiveBuddy -destination 'platform=macOS' -only-testing:LiveBuddyTests/UserFacingErrorTests CODE_SIGNING_ALLOWED=NO
```

Expected: compile failure because `UserFacingError` and new localization keys do not exist.

- [ ] **Step 3: Implement the error model**

Create `LiveBuddy/Models/UserFacingError.swift`:

```swift
enum UserFacingErrorKind: String, Codable, Equatable {
    case provider
    case permission
    case network
    case capture
    case storage
    case unknown
}

enum UserFacingErrorAction: String, Codable, Equatable {
    case openProviderSettings
    case openMicrophoneSettings
    case openScreenRecordingSettings
    case retry
}

struct UserFacingError: Codable, Equatable {
    let kind: UserFacingErrorKind
    let titleKey: InterfaceText
    let messageKey: InterfaceText
    let recoveryKey: InterfaceText?
    let action: UserFacingErrorAction?

    static let apiKeyMissing = UserFacingError(
        kind: .provider,
        titleKey: .apiKeyMissingTitle,
        messageKey: .apiKeyMissingMessage,
        recoveryKey: .apiKeyMissingRecovery,
        action: .openProviderSettings
    )

    static let microphonePermissionMissing = UserFacingError(
        kind: .permission,
        titleKey: .microphonePermissionRequired,
        messageKey: .microphonePermissionRequiredMessage,
        recoveryKey: .openMicrophoneSettings,
        action: .openMicrophoneSettings
    )

    static let screenRecordingPermissionMissing = UserFacingError(
        kind: .permission,
        titleKey: .screenRecordingPermissionRequired,
        messageKey: .screenRecordingPermissionRequiredMessage,
        recoveryKey: .openScreenRecordingSettings,
        action: .openScreenRecordingSettings
    )

    static func from(blockingIssues: [SetupBlockingIssue]) -> UserFacingError? {
        guard let first = blockingIssues.first else { return nil }
        switch first {
        case .apiKeyMissing:
            return .apiKeyMissing
        case .microphonePermissionMissing:
            return .microphonePermissionMissing
        case .screenRecordingPermissionMissing:
            return .screenRecordingPermissionMissing
        }
    }
}
```

Add the required `InterfaceText` keys and localized values:

```swift
case apiKeyMissingTitle
case apiKeyMissingMessage
case apiKeyMissingRecovery
case microphonePermissionRequired
case microphonePermissionRequiredMessage
case screenRecordingPermissionRequired
case screenRecordingPermissionRequiredMessage
case openMicrophoneSettings
case openScreenRecordingSettings
case cannotStart
```

English values:

```swift
.apiKeyMissingTitle: "API Key Required",
.apiKeyMissingMessage: "Add a Gemini API key before starting live translation.",
.apiKeyMissingRecovery: "Open API Provider settings and enter your Gemini API key.",
.microphonePermissionRequired: "Microphone Permission Required",
.microphonePermissionRequiredMessage: "LiveBuddy needs microphone access for the selected audio source.",
.screenRecordingPermissionRequired: "Screen Recording Permission Required",
.screenRecordingPermissionRequiredMessage: "LiveBuddy needs Screen Recording permission to capture system audio.",
.openMicrophoneSettings: "Open Microphone Settings",
.openScreenRecordingSettings: "Open Screen Recording Settings",
.cannotStart: "Cannot Start",
```

Chinese values:

```swift
.apiKeyMissingTitle: "需要 API 密钥",
.apiKeyMissingMessage: "开始实时翻译前，请先添加 Gemini API 密钥。",
.apiKeyMissingRecovery: "打开 API 提供商设置并填写 Gemini API 密钥。",
.microphonePermissionRequired: "需要麦克风权限",
.microphonePermissionRequiredMessage: "当前音频来源需要 LiveBuddy 访问麦克风。",
.screenRecordingPermissionRequired: "需要屏幕录制权限",
.screenRecordingPermissionRequiredMessage: "捕获系统音频需要开启屏幕录制权限。",
.openMicrophoneSettings: "打开麦克风设置",
.openScreenRecordingSettings: "打开屏幕录制设置",
.cannotStart: "无法开始",
```

For Japanese, Korean, Spanish, French, German, and Vietnamese, add concise equivalent translations in the existing language dictionaries in `InterfaceLanguage.swift`. Use the same keys and keep every supported language dictionary complete so non-English UI does not fall back to English for new P0 messages.

- [ ] **Step 4: Verify**

Run:

```bash
python3 scripts/verify_interface_language.py
xcodebuild test -project LiveBuddy.xcodeproj -scheme LiveBuddy -destination 'platform=macOS' -only-testing:LiveBuddyTests/UserFacingErrorTests CODE_SIGNING_ALLOWED=NO
```

Expected: verifier and test pass.

- [ ] **Step 5: Commit**

```bash
git add LiveBuddy/Models/UserFacingError.swift LiveBuddy/Models/InterfaceLanguage.swift LiveBuddyTests/UserFacingErrorTests.swift scripts/verify_interface_language.py
git commit -m "feat: add user-facing setup errors"
```

---

### Task 3: System Settings navigator

**Files:**
- Create: `LiveBuddy/Services/SystemSettingsNavigator.swift`
- Test: `LiveBuddyTests/SystemSettingsNavigatorTests.swift`

- [ ] **Step 1: Write the failing tests**

Add `LiveBuddyTests/SystemSettingsNavigatorTests.swift`:

```swift
import Testing
@testable import LiveBuddy

struct SystemSettingsNavigatorTests {
    @Test func microphoneSettingsURLTargetsPrivacyPane() {
        #expect(SystemSettingsDestination.microphone.url.absoluteString.contains("Privacy_Microphone"))
    }

    @Test func screenRecordingSettingsURLTargetsPrivacyPane() {
        #expect(SystemSettingsDestination.screenRecording.url.absoluteString.contains("Privacy_ScreenCapture"))
    }
}
```

- [ ] **Step 2: Verify failure**

Run:

```bash
xcodebuild test -project LiveBuddy.xcodeproj -scheme LiveBuddy -destination 'platform=macOS' -only-testing:LiveBuddyTests/SystemSettingsNavigatorTests CODE_SIGNING_ALLOWED=NO
```

Expected: compile failure because `SystemSettingsDestination` does not exist.

- [ ] **Step 3: Implement navigator**

Create `LiveBuddy/Services/SystemSettingsNavigator.swift`:

```swift
import AppKit
import Foundation

enum SystemSettingsDestination: Equatable {
    case microphone
    case screenRecording
    case privacy

    var url: URL {
        switch self {
        case .microphone:
            URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone")!
        case .screenRecording:
            URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture")!
        case .privacy:
            URL(string: "x-apple.systempreferences:com.apple.preference.security")!
        }
    }
}

protocol SystemSettingsOpening {
    @discardableResult
    func open(_ url: URL) -> Bool
}

extension NSWorkspace: SystemSettingsOpening {}

struct SystemSettingsNavigator {
    var opener: SystemSettingsOpening = NSWorkspace.shared

    @discardableResult
    func open(_ destination: SystemSettingsDestination) -> Bool {
        if opener.open(destination.url) {
            return true
        }
        return opener.open(SystemSettingsDestination.privacy.url)
    }
}
```

- [ ] **Step 4: Verify**

Run:

```bash
xcodebuild test -project LiveBuddy.xcodeproj -scheme LiveBuddy -destination 'platform=macOS' -only-testing:LiveBuddyTests/SystemSettingsNavigatorTests CODE_SIGNING_ALLOWED=NO
```

Expected: tests pass.

- [ ] **Step 5: Commit**

```bash
git add LiveBuddy/Services/SystemSettingsNavigator.swift LiveBuddyTests/SystemSettingsNavigatorTests.swift
git commit -m "feat: add system settings navigator"
```

---

### Task 4: Permission status service

**Files:**
- Create: `LiveBuddy/Services/PermissionStatusService.swift`
- Test: `LiveBuddyTests/PermissionStatusServiceTests.swift`

- [ ] **Step 1: Write the failing tests using injected providers**

Add `LiveBuddyTests/PermissionStatusServiceTests.swift`:

```swift
import Testing
@testable import LiveBuddy

struct PermissionStatusServiceTests {
    @Test func serviceReturnsInjectedMicrophoneAndScreenStatuses() async {
        let service = PermissionStatusService(
            microphoneStatus: { .granted },
            screenRecordingStatus: { .denied },
            requestMicrophoneAccess: { true },
            requestScreenRecordingAccess: { false }
        )

        let statuses = await service.refreshStatuses()

        #expect(statuses.microphone.state == .granted)
        #expect(statuses.screenRecording.state == .denied)
    }

    @Test func requestingMicrophoneConvertsGrantedBooleanToStatus() async {
        let service = PermissionStatusService(
            microphoneStatus: { .notDetermined },
            screenRecordingStatus: { .unknown },
            requestMicrophoneAccess: { true },
            requestScreenRecordingAccess: { false }
        )

        let status = await service.requestMicrophonePermission()

        #expect(status.state == .granted)
    }
}
```

- [ ] **Step 2: Verify failure**

Run:

```bash
xcodebuild test -project LiveBuddy.xcodeproj -scheme LiveBuddy -destination 'platform=macOS' -only-testing:LiveBuddyTests/PermissionStatusServiceTests CODE_SIGNING_ALLOWED=NO
```

Expected: compile failure because `PermissionStatusService` does not exist.

- [ ] **Step 3: Implement service with lightweight status checks**

Create `LiveBuddy/Services/PermissionStatusService.swift`:

```swift
import AVFoundation
import CoreGraphics
import Foundation

struct PermissionStatusSnapshot: Equatable {
    let microphone: PermissionStatus
    let screenRecording: PermissionStatus
}

struct PermissionStatusService {
    var microphoneStatus: @Sendable () -> PermissionGrantState = {
        switch AVCaptureDevice.authorizationStatus(for: .audio) {
        case .authorized:
            return .granted
        case .denied:
            return .denied
        case .restricted:
            return .restricted
        case .notDetermined:
            return .notDetermined
        @unknown default:
            return .unknown
        }
    }

    var screenRecordingStatus: @Sendable () -> PermissionGrantState = {
        CGPreflightScreenCaptureAccess() ? .granted : .denied
    }

    var requestMicrophoneAccess: @Sendable () async -> Bool = {
        await AVCaptureDevice.requestAccess(for: .audio)
    }

    var requestScreenRecordingAccess: @Sendable () -> Bool = {
        CGRequestScreenCaptureAccess()
    }

    func refreshStatuses(now: Date = Date()) async -> PermissionStatusSnapshot {
        PermissionStatusSnapshot(
            microphone: PermissionStatus(requirement: .microphone, state: microphoneStatus(), checkedAt: now),
            screenRecording: PermissionStatus(requirement: .screenRecording, state: screenRecordingStatus(), checkedAt: now)
        )
    }

    func requestMicrophonePermission(now: Date = Date()) async -> PermissionStatus {
        let granted = await requestMicrophoneAccess()
        return PermissionStatus(requirement: .microphone, state: granted ? .granted : .denied, checkedAt: now)
    }

    func requestScreenRecordingPermission(now: Date = Date()) -> PermissionStatus {
        let granted = requestScreenRecordingAccess()
        return PermissionStatus(requirement: .screenRecording, state: granted ? .granted : .denied, checkedAt: now)
    }
}
```

- [ ] **Step 4: Verify service does not create heavy capture objects**

Run:

```bash
python3 scripts/verify_p0_onboarding.py
```

Expected: pass; script checks `PermissionStatusService.swift` does not reference `SCStream`, `SCShareableContent`, `AVAudioEngine`, or `GeminiLiveTranslateClient`.

- [ ] **Step 5: Run tests and commit**

```bash
xcodebuild test -project LiveBuddy.xcodeproj -scheme LiveBuddy -destination 'platform=macOS' -only-testing:LiveBuddyTests/PermissionStatusServiceTests CODE_SIGNING_ALLOWED=NO
git add LiveBuddy/Services/PermissionStatusService.swift LiveBuddyTests/PermissionStatusServiceTests.swift scripts/verify_p0_onboarding.py
git commit -m "feat: add lightweight permission status service"
```

---

### Task 5: Provider health service extraction

**Files:**
- Create: `LiveBuddy/Services/ProviderHealthService.swift`
- Modify: `LiveBuddy/Models/AppState.swift:188-256`
- Test: `LiveBuddyTests/ProviderHealthStatusTests.swift`

- [ ] **Step 1: Write failing tests**

Add `LiveBuddyTests/ProviderHealthStatusTests.swift`:

```swift
import Foundation
import Testing
@testable import LiveBuddy

struct ProviderHealthStatusTests {
    @Test func emptyKeyReturnsMissingWithoutNetworkCall() async {
        var wasCalled = false
        let service = ProviderHealthService { _ in
            wasCalled = true
            return .success(())
        }

        let status = await service.verify(apiKey: "   ")

        #expect(status == .missing)
        #expect(wasCalled == false)
    }

    @Test func successfulPingReturnsValidStatus() async {
        let service = ProviderHealthService { _ in .success(()) }

        let status = await service.verify(apiKey: "abc")

        if case .valid = status {
            #expect(true)
        } else {
            Issue.record("Expected valid provider status")
        }
    }

    @Test func failedPingReturnsInvalidStatus() async {
        let service = ProviderHealthService { _ in
            .failure(NSError(domain: "LiveBuddy", code: 403, userInfo: [NSLocalizedDescriptionKey: "API key not valid"]))
        }

        let status = await service.verify(apiKey: "abc")

        if case .invalid(let message, _) = status {
            #expect(message.contains("API key"))
        } else {
            Issue.record("Expected invalid provider status")
        }
    }
}
```

- [ ] **Step 2: Verify failure**

Run:

```bash
xcodebuild test -project LiveBuddy.xcodeproj -scheme LiveBuddy -destination 'platform=macOS' -only-testing:LiveBuddyTests/ProviderHealthStatusTests CODE_SIGNING_ALLOWED=NO
```

Expected: compile failure because `ProviderHealthService` does not exist.

- [ ] **Step 3: Implement service**

Create `LiveBuddy/Services/ProviderHealthService.swift`:

```swift
import Foundation

struct ProviderHealthService {
    typealias Ping = @Sendable (String) async -> Result<Void, Error>

    var ping: Ping

    init(ping: @escaping Ping) {
        self.ping = ping
    }

    func verify(apiKey: String, now: Date = Date()) async -> ProviderHealthStatus {
        let trimmed = apiKey.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return .missing
        }

        let result = await ping(trimmed)
        switch result {
        case .success:
            return .valid(checkedAt: now)
        case .failure(let error):
            let message = error.localizedDescription
            if message.localizedCaseInsensitiveContains("API key") || message.localizedCaseInsensitiveContains("API_KEY_INVALID") {
                return .invalid(message: message, checkedAt: now)
            }
            return .failed(message: message, checkedAt: now)
        }
    }
}
```

- [ ] **Step 4: Move existing network ping from AppState into service factory**

Modify `LiveBuddy/Models/AppState.swift`:

- Keep public method `verifyGeminiToken() async throws` temporarily for UI compatibility.
- Internally call `ProviderHealthService.verify(apiKey:)`.
- Move existing `pingGeminiModel` body into a `private static func makeGeminiHealthService() -> ProviderHealthService` or a dedicated `GeminiProviderHealthClient` inside `ProviderHealthService.swift`.
- Preserve existing model fallback order: `gemini-3.1-flash-lite`, `gemini-2.5-flash`, `gemini-1.5-flash`.

- [ ] **Step 5: Verify and commit**

```bash
xcodebuild test -project LiveBuddy.xcodeproj -scheme LiveBuddy -destination 'platform=macOS' -only-testing:LiveBuddyTests/ProviderHealthStatusTests CODE_SIGNING_ALLOWED=NO
git add LiveBuddy/Services/ProviderHealthService.swift LiveBuddy/Models/AppState.swift LiveBuddyTests/ProviderHealthStatusTests.swift
git commit -m "feat: extract provider health checks"
```

---

### Task 6: AppState checklist state and start preflight

**Files:**
- Modify: `LiveBuddy/Models/AppState.swift`
- Test: `LiveBuddyTests/SetupChecklistTests.swift`
- Static verify: `scripts/verify_p0_onboarding.py`

- [ ] **Step 1: Add failing preflight tests**

Append to `LiveBuddyTests/SetupChecklistTests.swift`:

```swift
@Test func preflightBlocksWhenScreenRecordingIsMissing() {
    let checklist = SetupChecklistState.derive(
        audioSource: .screen,
        apiKey: .valid(checkedAt: Date()),
        microphone: PermissionStatus(requirement: .microphone, state: .granted, checkedAt: Date()),
        screenRecording: PermissionStatus(requirement: .screenRecording, state: .denied, checkedAt: Date())
    )

    let result = SetupPreflightResult.from(checklist)

    #expect(result == .blocked(.screenRecordingPermissionMissing))
}

@Test func preflightAllowsWhenChecklistHasNoBlockingIssues() {
    let checklist = SetupChecklistState.derive(
        audioSource: .screen,
        apiKey: .valid(checkedAt: Date()),
        microphone: PermissionStatus(requirement: .microphone, state: .denied, checkedAt: Date()),
        screenRecording: PermissionStatus(requirement: .screenRecording, state: .granted, checkedAt: Date())
    )

    let result = SetupPreflightResult.from(checklist)

    #expect(result == .allowed)
}
```

- [ ] **Step 2: Verify failure**

Run:

```bash
xcodebuild test -project LiveBuddy.xcodeproj -scheme LiveBuddy -destination 'platform=macOS' -only-testing:LiveBuddyTests/SetupChecklistTests CODE_SIGNING_ALLOWED=NO
```

Expected: compile failure because `SetupPreflightResult` does not exist.

- [ ] **Step 3: Add preflight result model**

Add to `LiveBuddy/Models/PermissionStatus.swift`:

```swift
enum SetupPreflightResult: Equatable {
    case allowed
    case blocked(SetupBlockingIssue)

    static func from(_ checklist: SetupChecklistState) -> SetupPreflightResult {
        if let first = checklist.blockingIssues.first {
            return .blocked(first)
        }
        return .allowed
    }
}
```

- [ ] **Step 4: Wire AppState without changing capture internals**

Modify `LiveBuddy/Models/AppState.swift`:

- Add small service properties:

```swift
private let permissionStatusService = PermissionStatusService()
private let systemSettingsNavigator = SystemSettingsNavigator()
private let providerHealthService = ProviderHealthService.geminiDefault
```

- Add published state:

```swift
@Published private(set) var setupChecklist: SetupChecklistState = .initial
@Published private(set) var currentUserFacingError: UserFacingError?
```

- Add refresh method:

```swift
func refreshSetupChecklist() {
    Task {
        let permissions = await permissionStatusService.refreshStatuses()
        await MainActor.run {
            self.setupChecklist = SetupChecklistState.derive(
                audioSource: self.settings.audioSource,
                apiKey: self.providerHealthStatusForCurrentKey,
                microphone: permissions.microphone,
                screenRecording: permissions.screenRecording
            )
        }
    }
}
```

- Add start preflight before creating `GeminiLiveTranslateClient` or capture objects:

```swift
func runStartPreflight() async -> SetupPreflightResult {
    let permissions = await permissionStatusService.refreshStatuses()
    let apiStatus: ProviderHealthStatus = settings.apiKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? .missing : .unchecked
    let checklist = SetupChecklistState.derive(
        audioSource: settings.audioSource,
        apiKey: apiStatus,
        microphone: permissions.microphone,
        screenRecording: permissions.screenRecording
    )
    setupChecklist = checklist
    return SetupPreflightResult.from(checklist)
}
```

- Change the beginning of `start()`:

```swift
let preflight = await runStartPreflight()
if case .blocked(let issue) = preflight {
    let error = UserFacingError.from(blockingIssues: [issue])
    currentUserFacingError = error
    updateStatus(error.map { settings.interfaceLanguage.localized($0.titleKey) } ?? settings.interfaceLanguage.localized(.cannotStart), level: .error, log: true)
    openSettingsWindow()
    showSetupSheet = true
    return
}
```

- [ ] **Step 5: Static verify preflight happens before capture/client creation**

Update `scripts/verify_p0_onboarding.py` so it checks in `AppState.swift`:

- `runStartPreflight()` exists.
- `start()` mentions `runStartPreflight()` before `GeminiLiveTranslateClient(settings:)`.
- `start()` mentions `runStartPreflight()` before `startCapture()`.

Run:

```bash
python3 scripts/verify_p0_onboarding.py
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add LiveBuddy/Models/AppState.swift LiveBuddy/Models/PermissionStatus.swift LiveBuddyTests/SetupChecklistTests.swift scripts/verify_p0_onboarding.py
git commit -m "feat: block start on setup preflight issues"
```

---

### Task 7: Setup checklist UI

**Files:**
- Create: `LiveBuddy/Views/Settings/SetupChecklistView.swift`
- Modify: `LiveBuddy/Views/Settings/SettingsView.swift`
- Modify: `LiveBuddy/Views/MenuBar/MenuBarView.swift`
- Modify: `LiveBuddy/Models/InterfaceLanguage.swift`
- Static verify: `scripts/verify_p0_onboarding.py`

- [ ] **Step 1: Add static failing verifier rules**

Update `scripts/verify_p0_onboarding.py` to require:

- `LiveBuddy/Views/Settings/SetupChecklistView.swift` exists.
- `SettingsView.swift` contains `SetupChecklistView(`.
- `ProviderSetupSheet` contains `SetupChecklistView(`.
- `MenuBarView.swift` contains `setupChecklist`.

Run:

```bash
python3 scripts/verify_p0_onboarding.py
```

Expected: failure because UI file and integrations do not exist.

- [ ] **Step 2: Implement `SetupChecklistView`**

Create `LiveBuddy/Views/Settings/SetupChecklistView.swift`:

```swift
import SwiftUI

struct SetupChecklistView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(appState.t(.setupChecklist))
                    .font(.headline)
                Spacer()
                Button(appState.t(.refreshStatus)) {
                    appState.refreshSetupChecklist()
                }
                .controlSize(.small)
            }

            SetupChecklistRow(
                title: appState.t(.apiKey),
                detail: providerDetail,
                state: appState.setupChecklist.apiKey.checklistState
            )

            SetupChecklistRow(
                title: appState.t(.microphonePermission),
                detail: detail(for: appState.setupChecklist.microphone),
                state: appState.setupChecklist.microphone.requirementState
            ) {
                appState.openMicrophoneSettings()
            }

            SetupChecklistRow(
                title: appState.t(.screenRecordingPermission),
                detail: detail(for: appState.setupChecklist.screenRecording),
                state: appState.setupChecklist.screenRecording.requirementState
            ) {
                appState.openScreenRecordingSettings()
            }
        }
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 12).fill(Color(nsColor: .controlBackgroundColor)))
        .onAppear { appState.refreshSetupChecklist() }
    }

    private var providerDetail: String {
        switch appState.setupChecklist.apiKey {
        case .missing:
            return appState.t(.apiKeyMissingMessage)
        case .unchecked:
            return appState.t(.apiKeyUnchecked)
        case .checking:
            return appState.t(.checking)
        case .valid:
            return appState.t(.apiKeyValid)
        case .invalid(let message, _), .failed(let message, _):
            return message
        }
    }

    private func detail(for item: PermissionChecklistItem) -> String {
        switch item.requirementState {
        case .satisfied:
            return appState.t(.granted)
        case .blocked:
            return appState.t(.missing)
        case .notNeeded:
            return appState.t(.notNeeded)
        case .unknown:
            return appState.t(.unknown)
        }
    }
}

private struct SetupChecklistRow: View {
    let title: String
    let detail: String
    let state: ChecklistRequirementState
    var action: (() -> Void)? = nil

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: iconName)
                .foregroundStyle(iconColor)
                .frame(width: 18)
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.subheadline.weight(.medium))
                Text(detail).font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            if let action, state == .blocked {
                Button("Open", action: action).controlSize(.small)
            }
        }
    }

    private var iconName: String {
        switch state {
        case .satisfied, .notNeeded:
            return "checkmark.circle.fill"
        case .blocked:
            return "exclamationmark.triangle.fill"
        case .unknown:
            return "questionmark.circle.fill"
        }
    }

    private var iconColor: Color {
        switch state {
        case .satisfied:
            return .green
        case .notNeeded, .unknown:
            return .secondary
        case .blocked:
            return .orange
        }
    }
}
```

- [ ] **Step 3: Wire the view into settings**

Modify `providerForm` in `LiveBuddy/Views/Settings/SettingsView.swift`:

```swift
Section {
    SetupChecklistView()
}
```

Place it before the active provider section.

Modify `ProviderSetupSheet` so the `Form` starts with:

```swift
SetupChecklistView()
```

Modify `MenuBarView` below the header divider:

```swift
if !appState.setupChecklist.canStart {
    Button {
        openWindow(id: "settings")
        NSApp.activate(ignoringOtherApps: true)
    } label: {
        Label(appState.t(.setupIncomplete), systemImage: "exclamationmark.triangle.fill")
    }
}
```

- [ ] **Step 4: Add localization keys**

Add to `InterfaceText` and all language dictionaries:

```swift
case setupChecklist
case refreshStatus
case microphonePermission
case screenRecordingPermission
case granted
case missing
case notNeeded
case unknown
case checking
case apiKeyUnchecked
case apiKeyValid
case setupIncomplete
```

- [ ] **Step 5: Verify and commit**

```bash
python3 scripts/verify_p0_onboarding.py
python3 scripts/verify_interface_language.py
git add LiveBuddy/Views/Settings/SetupChecklistView.swift LiveBuddy/Views/Settings/SettingsView.swift LiveBuddy/Views/MenuBar/MenuBarView.swift LiveBuddy/Models/InterfaceLanguage.swift scripts/verify_p0_onboarding.py scripts/verify_interface_language.py
git commit -m "feat: add setup checklist UI"
```

---

### Task 8: README and CI verification

**Files:**
- Modify: `README.md`
- Modify: `scripts/verify_p0_onboarding.py`

- [ ] **Step 1: Extend static verifier**

Ensure `scripts/verify_p0_onboarding.py` checks:

- README mentions `setup checklist`.
- README mentions microphone and screen recording permission checks.
- README mentions no continuous polling or no background polling for permission checks.

- [ ] **Step 2: Update README**

Add a section under Setup Instructions:

```markdown
### First-Run Checklist

LiveBuddy now shows a setup checklist before starting translation. It checks the Gemini API key, microphone permission, and screen recording permission needed by the selected audio source. Permission status is refreshed on app launch, settings open, start preflight, or when you click Refresh Status; LiveBuddy does not continuously poll permissions in the background.
```

- [ ] **Step 3: Run all available verification**

Run:

```bash
python3 scripts/verify_p0_onboarding.py
python3 scripts/verify_interface_language.py
python3 scripts/verify_ci_workflow.py
rm -rf /tmp/livebuddy_typecheck
mkdir -p /tmp/livebuddy_typecheck
cp -R LiveBuddy /tmp/livebuddy_typecheck/LiveBuddy
python3 - <<'PY'
from pathlib import Path
p = Path('/tmp/livebuddy_typecheck/LiveBuddy/Views/Settings/SettingsView.swift')
text = p.read_text()
marker = '\n#Preview {'
idx = text.find(marker)
if idx != -1:
    text = text[:idx].rstrip() + '\n'
p.write_text(text)
PY
swiftc -typecheck $(find /tmp/livebuddy_typecheck/LiveBuddy -name '*.swift' | sort)
```

Expected: all Python verifiers pass; `swiftc -typecheck` exits 0. Existing Sendable warnings may still appear and are not introduced by P0.

On GitHub Actions after push, expected: `Swift` workflow succeeds.

- [ ] **Step 4: Commit and push**

```bash
git add README.md scripts/verify_p0_onboarding.py
git commit -m "docs: document P0 setup checklist"
git push target HEAD:main
```

---

## Self-Review Checklist

Spec coverage:

- Permission status model: Task 1.
- Setup checklist derived state: Task 1.
- Friendly errors: Task 2.
- System Settings links: Task 3.
- Lightweight permission service with no polling/heavy capture objects: Task 4.
- Provider health extraction: Task 5.
- Start preflight before capture/client creation: Task 6.
- Settings/setup/menu UI: Task 7.
- Localization and README: Tasks 7 and 8.
- Open-source reference discipline: Header and Reference Rules section.

Type consistency:

- `ProviderHealthStatus` is used by `SetupChecklistState` and `ProviderHealthService`.
- `PermissionChecklistItem.requirementState` is used by tests and UI.
- `SetupBlockingIssue` is used by `SetupPreflightResult` and `UserFacingError.from(blockingIssues:)`.
- `SystemSettingsDestination` is used by `SystemSettingsNavigator` and tests.

Execution rule:

- Implement tasks in order.
- Do not write production code before the failing test or verifier for that task.
- Commit after each task.
