# P0 Onboarding, Permissions, and User-Friendly Errors Design

## Goal

Make LiveBuddy usable by a non-technical macOS user before adding more advanced features. The app should explain what is missing, guide the user to fix it, avoid unnecessary background polling, and preserve the current lightweight menu-bar architecture.

This design follows the user's requirement: study mature open-source implementations first, borrow their algorithms and architecture patterns, then implement our own code instead of copying source.

## Current Project State

LiveBuddy already has:

- Gemini API key storage and a manual token check in `LiveBuddy/Models/AppState.swift` and `LiveBuddy/Views/Settings/SettingsView.swift`.
- Microphone capture through `AVAudioEngine` in `LiveBuddy/Services/MicrophoneCapture.swift`.
- System audio capture through `ScreenCaptureKit` in `LiveBuddy/Services/ScreenAudioCapture.swift`.
- Runtime status messages and logs inside `AppState`.
- Basic setup sheet shown when the API key is empty.
- Interface language support for eight UI languages via `LiveBuddy/Models/InterfaceLanguage.swift`.

Main gaps:

- No central permission status model.
- Permission errors are mostly raw technical strings.
- The first-run sheet only handles API key entry.
- Start can fail after the user clicks it instead of giving a preflight checklist.
- Status text such as `Ready`, `Connecting`, `Listening`, and several error messages are not yet fully localized.

## Open-Source References and Borrowed Ideas

### PermissionFlow

Repository: https://github.com/jaywcjlove/PermissionFlow

Relevant ideas to borrow:

- Separate permission status detection from UI rendering.
- Use official Apple APIs for status checks where possible, without forcing permission prompts.
- Provide direct System Settings links instead of making the user search manually.
- Keep a single active guidance flow at a time.
- Show a compact visual status: granted, missing, not needed, checking.

What we will not copy:

- We will not copy its floating drag-to-authorize panel implementation in P0.
- We will not add the package dependency for P0; we will build a minimal native service that matches LiveBuddy's UI.

### QuickRecorder

Repository: https://github.com/lihaoyun6/QuickRecorder

Relevant ideas to borrow:

- Treat ScreenCaptureKit permission and runtime capture failures as separate states.
- Avoid doing heavy capture setup just to check permissions.
- Keep screen/audio capture concerns isolated from settings UI.

What we will not copy:

- QuickRecorder is a screen recorder, not a translator. We will not import recording/export logic in P0.

### Scripta

Repository: https://github.com/thehwang/Scripta

Relevant ideas to borrow:

- Meeting/transcription apps need a clear setup pipeline before recording starts.
- Keep user-facing setup status separate from low-level capture/transcription internals.
- Use privacy-first language and explain what happens to audio/transcripts.

What we will not copy:

- Scripta's local Whisper/Ollama pipeline is outside P0.

### Apple platform APIs

The P0 implementation should prefer platform APIs before dependencies:

- Microphone status: `AVCaptureDevice.authorizationStatus(for: .audio)` and `AVCaptureDevice.requestAccess(for: .audio)` when needed.
- Screen recording preflight: `CGPreflightScreenCaptureAccess()` where available.
- Screen recording prompt: `CGRequestScreenCaptureAccess()` only from a deliberate user action.
- Settings navigation: `NSWorkspace.shared.open(...)` with System Settings privacy URLs.

## Recommended Approach

Use a lightweight built-in implementation for P0.

Reasons:

- LiveBuddy currently has no SPM dependencies; adding a package for a small P0 surface adds maintenance and CI cost.
- P0 mostly needs status checks, user guidance, and localized messages, not a full permission-flow framework.
- A local service is easier to test with dependency injection and mock status providers.

## User-Facing Behavior

### Setup checklist card

Add a compact setup checklist at the top of the Provider settings page and setup sheet.

Rows:

1. API Key
   - Missing
   - Filled but unchecked
   - Checking
   - Valid
   - Invalid
2. Microphone Permission
   - Granted
   - Missing
   - Not needed for current audio source
   - Unknown
3. Screen Recording Permission
   - Granted
   - Missing
   - Not needed for current audio source
   - Unknown
4. Network/API Health
   - Not checked
   - Checking
   - Reachable
   - Failed

Each row has:

- Status icon.
- Localized title.
- One short localized explanation.
- Optional action button.

### Permission action buttons

Buttons:

- `Open Microphone Settings`
- `Open Screen Recording Settings`
- `Request Microphone Permission`
- `Request Screen Recording Permission`
- `Refresh Status`

Behavior:

- Opening settings is always explicit and user-triggered.
- Requesting screen recording permission is explicit; do not prompt automatically on app launch.
- Refresh checks use preflight APIs and do not start capture streams.

### Start preflight

Before starting translation, `AppState.start()` should run a lightweight preflight:

1. Check API key is non-empty.
2. Check required permissions based on `settings.audioSource`.
3. Optionally check recent provider health; if no recent result exists, show a warning but allow manual verification from settings.
4. If a blocking issue exists, do not start capture. Show a localized, actionable error and open settings.

Blocking examples:

- Missing API key.
- Microphone selected but microphone permission denied.
- Screen audio selected but screen recording permission denied.

Non-blocking examples:

- API key has not been checked recently.
- Network was previously unavailable but user explicitly retries.

### Friendly error model

Introduce a typed model:

```swift
struct UserFacingError: Equatable {
    let kind: UserFacingErrorKind
    let titleKey: InterfaceText
    let messageKey: InterfaceText
    let recoveryKey: InterfaceText?
    let action: UserFacingErrorAction?
}
```

Low-level errors map to this model:

- `MicrophoneCaptureError.permissionDenied` -> microphone permission missing.
- `ScreenAudioCaptureError.noDisplay` -> no display available.
- Gemini invalid key/network/server errors -> provider-specific user-facing errors.
- Settings/transcript save errors -> storage error.

The raw error should still go into logs for debugging, but the UI should show the friendly message.

## Data Model

### PermissionStatus

```swift
enum PermissionRequirement: String, Codable, CaseIterable {
    case microphone
    case screenRecording
}

enum PermissionGrantState: Equatable, Codable {
    case granted
    case denied
    case notDetermined
    case restricted
    case unknown
}

struct PermissionStatus: Equatable, Codable {
    let requirement: PermissionRequirement
    let state: PermissionGrantState
    let checkedAt: Date
}
```

### SetupChecklistState

```swift
struct SetupChecklistState: Equatable {
    let apiKey: ProviderHealthStatus
    let microphone: PermissionChecklistItem
    let screenRecording: PermissionChecklistItem
    let network: ProviderHealthStatus
    let blockingIssues: [SetupBlockingIssue]
}
```

The checklist is derived state, not persisted. Persist only minimal provider health metadata if needed.

## Services

### PermissionStatusService

Responsibilities:

- Read current microphone permission state.
- Read current screen recording state.
- Request microphone permission only when a user action explicitly asks.
- Request screen recording permission only when a user action explicitly asks.
- Open System Settings privacy pages through `SystemSettingsNavigator`.

Performance strategy:

- No timer.
- No capture stream creation for status checks.
- No retained heavy system objects.
- Cache the latest statuses in `AppState` only as small value structs.

### SystemSettingsNavigator

Responsibilities:

- Open microphone privacy page.
- Open screen recording privacy page.
- Fall back to general Privacy & Security if the exact pane URL fails.

### ProviderHealthService

Responsibilities:

- Move Gemini key verification logic out of `AppState`.
- Return typed status instead of throwing raw user-facing strings.
- Keep the existing `pingGeminiModel` behavior initially, but wrap results in typed states.

Performance strategy:

- Do not verify the API key continuously.
- Only verify on explicit Check button or preflight when needed.
- Store `lastCheckedAt` and avoid rechecking within a short freshness window unless forced.

## AppState Integration

Add published state:

```swift
@Published private(set) var setupChecklist = SetupChecklistState.initial
@Published private(set) var currentUserFacingError: UserFacingError?
```

Add methods:

```swift
func refreshSetupChecklist()
func requestMicrophonePermission()
func requestScreenRecordingPermission()
func openMicrophoneSettings()
func openScreenRecordingSettings()
func runStartPreflight() async -> SetupPreflightResult
```

`start()` flow becomes:

1. `let result = await runStartPreflight()`
2. If blocked, set `currentUserFacingError`, update status/log, open settings, return.
3. Otherwise continue with existing Gemini connection and capture setup.

## UI Integration

### SettingsView

- Add `SetupChecklistView` near the top of Provider settings.
- Keep existing API key field and Check button.
- Add permission action buttons only when relevant.

### ProviderSetupSheet

- Replace the simple API-key-only form with the same checklist component.
- Keep it compact, not a multi-screen wizard in P0.

### MenuBarView

- Show a small warning row if setup is incomplete.
- Provide one click to open settings.

## Localization Plan

Add keys to `InterfaceText`:

- Status: ready, connecting, listening, stopped, error.
- Setup: setupChecklist, required, optional, granted, missing, notNeeded, checking, refreshStatus.
- API: apiKeyMissing, apiKeyUnchecked, apiKeyValid, apiKeyInvalid, checkApiKey.
- Permissions: microphonePermission, screenRecordingPermission, openMicrophoneSettings, openScreenRecordingSettings, requestPermission.
- Errors: cannotStart, permissionRequired, providerUnavailable, networkUnavailable, settingsSaveFailed.

P0 should localize all new setup and error messages in all eight currently supported interface languages. If translations are imperfect, prefer clear concise wording over leaving English fallback in non-English UI.

## Testing Strategy

### Unit tests

- Permission-to-checklist derivation:
  - screen source requires screen recording only.
  - microphone source requires microphone only.
  - both requires both.
  - missing required permission blocks start.
  - not-needed permission is not blocking.

- Error mapping:
  - microphone denied maps to microphone permission error.
  - invalid API key maps to API key invalid error.
  - screen capture no-display maps to display unavailable error.

- Provider health:
  - empty key is blocking without network request.
  - valid result stores status.
  - stale result can be refreshed.

### Static verification scripts

Extend existing scripts:

- `scripts/verify_interface_language.py` should ensure new `InterfaceText` keys exist in all languages.
- Add a P0 verifier to ensure `AppState.start()` calls preflight before creating capture/client objects.

### Manual verification

Because this machine lacks full Xcode, local manual verification can use:

- `swiftc -typecheck` against source copy without `#Preview`.
- Manual temporary `.app` launch via `swiftc` for UI inspection.
- GitHub Actions `xcodebuild build/test` as authoritative CI.

## Implementation Order

1. Add pure models and tests: `PermissionStatus`, `SetupChecklistState`, `UserFacingError`.
2. Add `SystemSettingsNavigator` with tests for URL construction where possible.
3. Add `PermissionStatusService` with injectable status provider for tests.
4. Add `ProviderHealthService` by moving existing Gemini ping logic out of `AppState`.
5. Add `SetupChecklistView` and wire it into Settings/setup sheet.
6. Add `AppState.start()` preflight.
7. Localize all new keys.
8. Update README with setup flow.
9. Verify locally and through GitHub Actions.

## Scope Boundaries

P0 will not implement:

- Global hotkeys.
- Launch at login.
- Transcript export formats.
- Sparkle auto-update.
- SQLite/FTS transcript indexing.
- Drag-to-authorize floating helper panels.

These remain later batches with their own designs and open-source reference studies.

## Risks and Mitigations

- macOS privacy APIs differ by OS version.
  - Keep checks conservative and fallback to user guidance.
- Exact System Settings URLs may change.
  - Use a fallback to general Privacy & Security.
- Full Xcode is not installed locally.
  - Rely on GitHub Actions for authoritative `xcodebuild`.
- Large `AppState` file may grow further.
  - Move provider health and permission logic into services, not into `AppState`.
