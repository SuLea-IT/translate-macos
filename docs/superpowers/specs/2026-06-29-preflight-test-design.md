# Preflight Test Page Design

## Goal

Give users a one-click way to verify that LiveBuddy is ready before starting a real translation session. The test should answer four practical questions:

1. Is the Gemini API key usable?
2. Are the required macOS permissions available for the selected audio source?
3. Is audio actually arriving from the selected microphone and/or system audio source?
4. Can the subtitle window appear and render a temporary caption?

The test must be lightweight: it must not start a Gemini Live translation session, must not create a transcript, must not retain audio buffers, and must release capture resources immediately after the short test window.

## Open-Source References and Borrowed Ideas

- [WebRTC audio volume sample](https://webrtc.github.io/samples/src/content/getusermedia/volume/) demonstrates a user-facing microphone volume test with short live sampling.
- [WebRTC SoundMeter](https://raw.githubusercontent.com/webrtc/samples/gh-pages/src/content/getusermedia/volume/js/soundmeter.js) stores only compact meter state such as instant, slow, and clip values instead of retaining audio.
- [WebRTC volume meter processor](https://raw.githubusercontent.com/webrtc/samples/gh-pages/src/content/getusermedia/volume/js/volume-meter-processor.js) computes RMS over incoming samples as a streaming signal-quality indicator.
- [OBS Audio Mixer technical details](https://obsproject.com/kb/audio-mixer-technical-details) distinguishes peak, RMS/VU-style level, and clipping indicators so users can tell whether audio is present, too quiet, or too loud.

Borrowed principles:

- Stream audio through a small analyzer rather than storing audio.
- Track peak, RMS, clipping, and silence indicators as simple scalar values.
- Keep the test user-initiated and time-limited.
- Separate readiness checks from real recording/translation state.

## User Experience

Add a new Settings sidebar item: **Test**.

The page contains:

- A short explanation: run this before starting translation to verify API, permissions, audio, and subtitle display.
- A **Run Test** button.
- Step rows for:
  - API Key
  - Permissions
  - Microphone Audio, only when selected source is microphone or both
  - Screen Audio, only when selected source is screen or both
  - Subtitle Window
- Each row shows one of: pending, running, passed, warning, failed.
- Audio rows show peak/RMS percentages and a short diagnosis:
  - audio detected
  - too quiet / silence
  - clipping detected
- A short summary at the top: Ready, Needs Attention, or Failed.

The test is disabled while translation is already running. Running a test while a previous test is still active cancels or ignores the old task and starts a fresh test.

## Data Model

Create a pure model file, tentatively `LiveBuddy/Models/PreflightTest.swift`.

Types:

```swift
enum PreflightTestStepID: String, CaseIterable, Codable, Hashable {
    case apiKey
    case permissions
    case microphoneAudio
    case screenAudio
    case subtitleWindow
}

enum PreflightTestStepState: String, Codable, Equatable {
    case pending
    case running
    case passed
    case warning
    case failed
}

struct AudioLevelSample: Codable, Equatable {
    var peak: Float
    var rms: Float
    var clippedSampleCount: Int
    var totalSampleCount: Int
}

struct AudioLevelSummary: Codable, Equatable {
    var peak: Float
    var rms: Float
    var isSilent: Bool
    var isClipping: Bool
}

struct PreflightTestStep: Identifiable, Codable, Equatable {
    var id: PreflightTestStepID
    var state: PreflightTestStepState
    var message: String
    var audio: AudioLevelSummary?
}

struct PreflightTestReport: Codable, Equatable {
    var startedAt: Date?
    var finishedAt: Date?
    var steps: [PreflightTestStep]
}
```

## Audio Analyzer

Create a pure `AudioLevelAnalyzer` that accepts already-produced PCM16 chunks and updates scalar metrics only.

Algorithm:

- Interpret input as little-endian signed 16-bit PCM.
- Convert each sample to `abs(Float(sample) / Float(Int16.max))`.
- Maintain:
  - `peak = max(peak, absSample)`
  - `sumSquares += normalized * normalized`
  - `totalSampleCount += 1`
  - `clippedSampleCount += 1` when `abs(sample) >= clippingThreshold`
- Compute `rms = sqrt(sumSquares / totalSampleCount)`.
- Mark silent when `rms < silenceThreshold` and `peak < peakSilenceThreshold`.
- Mark clipping when `clippedSampleCount > 0` or peak exceeds clipping threshold.

Initial thresholds:

- `silenceThreshold = 0.01`
- `peakSilenceThreshold = 0.02`
- `clippingThreshold = 0.98`

Memory behavior:

- No retained audio buffer.
- One analyzer per source.
- Only scalar counters and floats survive after each chunk.

## Test Runner

Create `LiveBuddy/Services/PreflightTestRunner.swift`.

Responsibilities:

1. API test:
   - call `ProviderHealthService.verify(apiKey:)`.
2. Permission test:
   - call `PermissionStatusService.refreshStatuses()`.
   - derive selected-source readiness with existing `SetupChecklistState`.
3. Audio source test:
   - run a short capture for selected source(s), default 3 seconds.
   - feed chunks into `AudioLevelAnalyzer`.
   - stop capture immediately after timeout.
   - never forward chunks to Gemini.
4. Subtitle test:
   - ask `AppState` to show a temporary caption window message.
   - do not add transcript lines.

The runner should expose progress through an async callback:

```swift
struct PreflightTestRunner {
    var sampleDuration: TimeInterval = 3
    func run(settings: AppSettings, update: @MainActor (PreflightTestReport) -> Void) async -> PreflightTestReport
}
```

For testability, the runner should accept injectable closures for API verification, permission refresh, audio sample providers, and subtitle display. The live runner wires those closures to existing services and capture classes.

## AppState Integration

Add:

```swift
@Published private(set) var preflightTestReport: PreflightTestReport = .idle
@Published private(set) var isRunningPreflightTest = false

func runPreflightTest() async
func showTemporaryTestCaption()
```

Behavior:

- If translation is running, fail fast with a user-facing message.
- Set `isRunningPreflightTest` while the runner is active.
- Update report as each step changes.
- For subtitle test, post `.showCaptionWindow` and set temporary caption text/draft without saving transcript.
- Restore prior caption draft after a short delay if the app is not running.

## UI Integration

Update `SettingsView`:

- Add `NavigationItem.test`.
- Add sidebar link: **Test** with `checkmark.seal` or `stethoscope` icon.
- Create `preflightTestForm`.
- Render summary and step rows.
- Show audio meters as small progress bars for peak/RMS.

Keep the existing `SetupChecklistView` intact. The checklist is passive readiness. The new Test page is an active one-shot diagnostic.

## Localization

Add interface keys for all supported UI languages:

- `test`
- `runTest`
- `preflightTest`
- `preflightTestDescription`
- `apiKeyTest`
- `permissionsTest`
- `microphoneAudioTest`
- `screenAudioTest`
- `subtitleWindowTest`
- `testPassed`
- `testWarning`
- `testFailed`
- `testRunning`
- `audioDetected`
- `audioTooQuiet`
- `audioClippingDetected`
- `subtitleTestMessage`

## Error Handling

- API failures show provider error text.
- Permission failures reuse existing permission messages and system-settings actions where practical.
- Audio capture failures show the localized error description.
- If no audio is detected, mark the step as warning rather than failed because silence may be expected.
- If clipping is detected, mark warning.
- If a capture throws before producing samples, mark failed.

## Non-Goals

- No Gemini Live connection.
- No translated audio playback test.
- No transcript creation.
- No audio file saving.
- No continuous monitoring in the background.
- No advanced device calibration UI in this pass.

## Testing Strategy

Unit/pure tests:

- `AudioLevelAnalyzer` calculates RMS/peak from PCM16 chunks.
- silence detection works.
- clipping detection works.
- analyzer does not retain full sample arrays.
- `PreflightTestReport` derives summary state correctly.

Runner tests with injected closures:

- API failure marks API step failed and still reports skipped/dependent state consistently.
- Permission missing marks permissions failed.
- Quiet audio marks warning.
- Normal audio marks passed.
- Capture error marks failed.

Static verifiers:

- `PreflightTest.swift` exists.
- `PreflightTestRunner.swift` exists.
- `SettingsView` exposes `NavigationItem.test` and `preflightTestForm`.
- `AppState` exposes `runPreflightTest` and `preflightTestReport`.
- `PreflightTestRunner` must not reference `GeminiLiveTranslateClient`.
- interface language keys are translated for every supported language.

## Rollout

1. Commit this design.
2. Write implementation plan.
3. Implement with TDD:
   - pure model/analyzer first;
   - runner with injection second;
   - AppState/UI third;
   - docs and CI last.
