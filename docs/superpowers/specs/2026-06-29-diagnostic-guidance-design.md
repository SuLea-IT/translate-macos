# Diagnostic Guidance Design

## Goal

Convert low-level provider, network, permission, capture, and storage failures into user-facing diagnostics that explain:

1. what happened;
2. why LiveBuddy thinks it happened;
3. what the user can do next;
4. which one-click recovery action is available.

The feature must stay lightweight: classify errors into small value types, keep only the latest actionable diagnostic, avoid retaining long logs or raw payloads, and reuse existing setup/checklist/action services.

## Open-Source References and Borrowed Ideas

- [Rust compiler diagnostics](https://doc.rust-lang.org/rustc/diagnostics.html) separate a stable error code, concise message, and help text. Borrow: stable diagnostic codes and one clear recovery hint.
- [Kubernetes Status object](https://kubernetes.io/docs/reference/kubernetes-api/common-definitions/status/) separates `reason`, `message`, and `details`. Borrow: classify machine-readable reason separately from the human message.
- [Docker CLI](https://github.com/docker/cli) and [Homebrew](https://github.com/Homebrew/brew) patterns commonly translate raw subsystem failures into concise actionable messages. Borrow: show next action rather than only raw error output.

## Existing Gaps

LiveBuddy already has `UserFacingError` for setup-blocking issues, but most runtime paths still call `updateStatus(error.localizedDescription, level: .error)` or log raw Gemini/WebSocket strings.

Current gaps:

- invalid API key and quota/billing errors are not consistently surfaced as actionable provider diagnostics;
- model unavailable/not found errors are raw provider strings;
- network timeout/disconnect/TLS/DNS errors are raw localized descriptions;
- capture failures are raw capture errors;
- settings/transcript storage failures are raw strings;
- Settings UI does not show a durable latest diagnostic with a recovery button.

## Design

### Model

Create `LiveBuddy/Models/DiagnosticIssue.swift`.

Types:

- `DiagnosticKind`
  - `provider`
  - `network`
  - `permission`
  - `capture`
  - `storage`
  - `unknown`
- `DiagnosticSeverity`
  - `info`
  - `warning`
  - `error`
- `DiagnosticRecoveryAction`
  - `openProviderSettings`
  - `openMicrophoneSettings`
  - `openScreenRecordingSettings`
  - `retry`
- `DiagnosticCode`
  - provider: `apiKeyMissing`, `apiKeyInvalid`, `quotaOrBilling`, `modelUnavailable`, `providerServerError`
  - network: `networkUnavailable`, `networkTimeout`, `connectionLost`
  - permission: `microphonePermissionMissing`, `screenRecordingPermissionMissing`
  - capture: `microphoneUnavailable`, `screenAudioUnavailable`
  - storage: `settingsSaveFailed`, `transcriptSaveFailed`
  - fallback: `unknown`
- `DiagnosticIssue`
  - stable `code`
  - `kind`
  - `severity`
  - localized `titleKey`, `messageKey`, `recoveryKey`
  - optional `underlyingMessage`
  - optional `action`

Keep this as a small Codable/Equatable value. Do not append every diagnostic to a new persistent history in this pass.

### Classifier

Create `DiagnosticClassifier` in the same file.

Classify by normalized lowercase message and typed context:

- `from(blockingIssue:)`
- `from(providerStatus:)`
- `from(connectionEvent:)`
- `from(error:context:)`
- `storage(kind:underlyingMessage:)`

Classification rules:

- API key invalid if message contains `api key`, `api_key_invalid`, `apikey`, `unauthorized`, or `forbidden`.
- Quota/billing if message contains `quota`, `billing`, `payment`, `exceeded`, or `resource exhausted`.
- Model unavailable if message contains `model not found`, `not found`, `unsupported model`, or `invalid argument` with model terms.
- Timeout if message contains `timeout`, `timed out`, `deadline`, or URL error timed out wording.
- Network unavailable if message contains `offline`, `network`, `internet`, `cannot connect`, `dns`, `tls`, or `secure connection`.
- Connection lost for WebSocket close/disconnect/send failures not otherwise classified.
- Capture errors from `MicrophoneCaptureError` or `ScreenAudioCaptureError` map to capture diagnostics.
- Unknown preserves a short underlying message for logs but displays a generic recovery hint.

### UI

Add a reusable `DiagnosticIssueBanner` in Settings UI:

- icon by severity;
- title;
- user-facing message;
- recovery text;
- optional action button;
- raw underlying detail behind compact secondary text.

Show the latest diagnostic near the top of Settings detail pages when `AppState.currentDiagnosticIssue` is not nil. Keep existing setup checklist and runtime logs.

### AppState Integration

Add:

```swift
@Published private(set) var currentDiagnosticIssue: DiagnosticIssue?

func clearDiagnosticIssue()
func performDiagnosticRecoveryAction(_ action: DiagnosticRecoveryAction)
```

Set diagnostics in these places:

- setup preflight failure;
- provider token verification failure;
- start/connect/capture catch block;
- terminal connection failure;
- API key Keychain save failure;
- settings save failure;
- transcript save failure.

Do not replace logs. Logs remain technical; diagnostic banner is user-facing.

### Localization

Add interface keys for title/message/recovery text. Keep the first pass concise and localized for all eight interface languages.

### Non-Goals

- No persistent diagnostic history.
- No full log analytics.
- No remote telemetry.
- No automatic browser opening.
- No new retry policy beyond existing retry/reconnect actions.

## Testing Strategy

Pure tests:

- API key invalid classification.
- quota/billing classification.
- model unavailable classification.
- network timeout classification.
- permission blocking issue classification.
- capture error classification.
- unknown error keeps underlying text.

Integration/static checks:

- `DiagnosticIssue.swift` exists.
- `AppState` exposes `currentDiagnosticIssue`, `clearDiagnosticIssue`, and `performDiagnosticRecoveryAction`.
- `SettingsView` renders `DiagnosticIssueBanner`.
- All diagnostic localization keys are translated for every supported language.
- Classifier is pure and does not reference heavy capture, WebSocket, or UI objects.

## Rollout

1. Commit this design.
2. Write implementation plan.
3. Implement pure diagnostic model and classifier with TDD.
4. Wire AppState and Settings banner.
5. Update docs/verifiers.
6. Push and wait for CI.
