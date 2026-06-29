# Cost and Usage Control Design

## Goal

Add clear live cost controls for Gemini Live Translate usage: show current translated duration, estimated cost, idle auto-pause, and per-session/daily usage limits. The idle pause must save API cost without intentionally dropping the beginning of the next utterance.

## External references

- `ggml-org/whisper.cpp` (`51,135` GitHub stars via `gh repo view` on 2026-06-29) includes a simple local VAD style that compares recent audio energy against broader energy using thresholds. LiveBuddy borrows the idea of cheap local energy detection rather than adding a heavy model dependency.
- `snakers4/silero-vad` (`9,451` GitHub stars via `gh repo view` on 2026-06-29) exposes concepts such as speech threshold, lower negative threshold, minimum silence duration, and speech padding. LiveBuddy borrows those state-machine concepts: hysteresis, minimum silence before splitting/pausing, and pre-roll padding.
- Google Gemini pricing page for `gemini-3.5-live-translate-preview` currently lists audio input and audio output pricing and states billing is based on 25 tokens per second of audio, with an effective approximate price of `$0.0368/min`. LiveBuddy uses this as the default estimate but keeps the per-minute price editable because pricing can change.

## User experience

Settings → Caption adds a **Cost & Usage Control** section:

1. Shows **This session translated time**, **Today translated time**, and **Estimated cost**.
2. Lets users enable/disable idle auto-pause.
3. Lets users configure idle pause delay, session limit, daily limit, and estimated USD/minute.
4. Explains that estimates are local and approximate.

Runtime status adds visible states:

- `Listening · ... · API 00:03 · $0.00`
- `Idle soon · auto-pause in 10s`
- `API paused · monitoring locally`
- `Resuming · replaying buffered audio`
- `Usage limit reached · API paused`

The menu bar view also shows compact usage and pause state so users do not need to open Settings to understand cost.

## Safety model for idle auto-pause

Idle auto-pause is a soft pause, not a full stop:

1. Microphone/screen capture keeps running locally.
2. Gemini WebSocket is closed only after a conservative idle delay.
3. A local ring buffer always keeps recent audio pre-roll while active.
4. While API-paused, incoming chunks continue to append to a resume buffer.
5. When local speech energy crosses the resume threshold, LiveBuddy reconnects Gemini and flushes the buffered audio before sending new live audio.

This cannot mathematically guarantee no missed content under all conditions, but it prevents LiveBuddy from intentionally discarding normal speech if local capture is working, the buffer has not overflowed, and reconnect succeeds.

## Detection approach

Use local PCM16 RMS already computed in `AppState.audioSink`:

- Voice threshold: default `0.020` normalized RMS.
- Exit threshold: default `0.012`, lower than voice threshold to provide hysteresis.
- Idle delay: default `60s` continuous quiet and no transcript activity.
- Warning window: default `10s` before pause.
- Pre-roll: default `3s` audio buffer.
- Resume buffer cap: default `15s`.

The engine treats a chunk as speech when RMS is above the voice threshold. It treats chunks as quiet only below the lower exit threshold. Values between thresholds keep the previous speech/quiet state to avoid rapid flapping.

## Usage accounting

Count only audio chunks actually sent to Gemini as billable audio seconds:

```swift
seconds = Double(data.count) / (16_000 samples/s * 2 bytes/sample)
```

For `screen + microphone`, each stream contributes its own sent chunks, matching API load more closely than wall-clock time.

Daily usage persists to Application Support as a tiny JSON ledger:

```swift
struct UsageLedger: Codable {
    var dayKey: String
    var sentAudioSeconds: TimeInterval
}
```

When the local calendar day changes, LiveBuddy starts a new ledger day automatically.

## Limits

- Session limit default: `0` minutes, disabled.
- Daily limit default: `0` minutes, disabled.
- If a limit is reached, LiveBuddy closes Gemini but keeps local monitoring active and shows `Usage limit reached`.
- Users can increase or disable the limit in Settings, then stop/start or speak again to resume.
- Auto-pause and limits never delete transcript history.

## Data model

Add `LiveUsageSettings` to `AppSettings`:

```swift
struct LiveUsageSettings: Codable, Equatable {
    var idleAutoPauseEnabled = true
    var idlePauseDelaySeconds = 60.0
    var idleWarningSeconds = 10.0
    var prerollSeconds = 3.0
    var resumeBufferLimitSeconds = 15.0
    var speechStartThreshold = 0.020
    var speechEndThreshold = 0.012
    var estimatedCostPerMinuteUSD = 0.0368
    var perSessionLimitMinutes = 0.0
    var dailyLimitMinutes = 0.0
}
```

Add `LiveUsageSnapshot` and `UsageControlEngine` in a focused model file. `AppState` owns the engine and exposes published snapshots for UI.

## Integration points

- `AppState.start()` resets session usage state and loads today's ledger.
- `audioSink(source:)` sends chunks through a new gating method rather than directly calling `client.sendAudio(data)`.
- `appendOriginalText` and `appendCaption` mark transcript activity so the idle timer does not pause during delayed output.
- Reconnect recovery remains separate: idle resume uses the same `makeGeminiClient()` but does not count as an error.

## Testing

Focused unit tests cover:

1. Sent audio duration and estimated cost calculations.
2. Idle warning before idle pause.
3. Idle pause after quiet period.
4. Hysteresis avoids flapping near thresholds.
5. Pre-roll and paused resume buffers preserve audio before resume.
6. Per-session limit pauses sending.
7. Daily ledger resets on day change.
8. Legacy settings decode with usage defaults.

## Verification

- Focused Swift tests pass.
- `python3 scripts/verify_interface_language.py` passes.
- `swiftc -typecheck` passes for app sources.
- Full GitHub Actions Swift workflow passes after push.
