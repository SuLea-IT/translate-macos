# Virtual Audio Isolation Design

## Goal

Add an optional BlackHole-style virtual audio isolation mode so users can avoid hearing the original source audio and hear only LiveBuddy's translated speech. The feature is opt-in and reversible.

## Reference

The recommended free/open-source fixture is [ExistentialAudio/BlackHole](https://github.com/ExistentialAudio/BlackHole), a macOS loopback audio driver. `gh repo view` on 2026-06-29 shows 19,265 stars. LiveBuddy will not bundle or install the driver; it detects compatible virtual devices and links users to the official project.

## User model

When enabled, LiveBuddy expects this routing:

1. Source app/system audio outputs to BlackHole or another loopback device.
2. LiveBuddy captures that loopback device as a microphone-style input.
3. LiveBuddy plays translated speech to a user-selected real output device, such as MacBook speakers or headphones.

This separates original audio from translated audio. If the user has not routed the source app/system output to BlackHole, LiveBuddy cannot suppress the original audio that another app is playing.

## UX

Settings → Caption → Translation & Audio adds:

- Toggle: **Virtual audio isolation**.
- Status: BlackHole/loopback detected or not detected.
- Picker: virtual input device, defaulting to the first detected BlackHole/loopback input.
- Picker: translated voice output device, defaulting to system default.
- Buttons: open BlackHole download and open macOS Sound settings.
- Help text explaining the routing steps.

Existing “captured audio playback volume” wording is corrected to “translated voice volume” because the slider controls Gemini translated speech, not the source audio.

## Runtime behavior

- If virtual isolation is disabled, existing screen/mic/both capture behavior remains unchanged.
- If enabled, `startCapture()` uses `MicrophoneCapture` against the configured virtual input device and skips `ScreenAudioCapture` to avoid re-capturing speaker output.
- If enabled but no virtual input is available, start fails with a clear log/status message.
- `PCM16AudioPlayer` gets an output-device selector so translated speech can play to speakers/headphones even when the system or source app outputs original audio to BlackHole.
- Changing output device applies without restarting Gemini; changing isolation input/mode requires session restart.

## Settings

Add to `AppSettings`:

```swift
var virtualAudioIsolationEnabled = false
var virtualAudioInputDeviceUID: String? = nil
var translatedAudioOutputDeviceUID: String? = nil
```

## Device helpers

Extend `AudioDeviceManager`:

- `getOutputDevices()` mirrors input device enumeration for output scope.
- `getOutputDeviceID(for:)` resolves output device UID.
- `preferredVirtualInputDevice(from:selectedUID:)` returns the selected virtual input if valid, otherwise the first input whose name/UID contains `blackhole`, `loopback`, `soundflower`, or `vb-cable`.

## Tests

- Legacy settings decode defaults with isolation disabled.
- Settings encode/decode selected virtual input and translated output UID.
- Device selection prefers explicit selected UID.
- Device selection auto-detects BlackHole by name or UID.
- Device selection returns nil when no loopback device exists.

## Verification

- Focused pure helper tests pass.
- App source `swiftc -typecheck` passes.
- Existing verifier scripts pass.
- GitHub Actions Swift build/tests pass after push.
