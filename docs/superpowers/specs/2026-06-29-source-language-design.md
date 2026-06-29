# Source Language Selection and Detection Display Design

## Goal

Let users see and control the source side of translation without adding unsupported provider parameters or extra runtime memory use. LiveBuddy should default to automatic source-language detection, display the detected input language when Gemini returns it, and optionally let the user bias translation with a source-language hint.

## Current State

- `AppSettings` stores only `targetLanguageCode`.
- Gemini setup sends `translationConfig.targetLanguageCode` and `echoTargetLanguage`.
- `GeminiLiveTranslateClient` already receives `inputTranscription.languageCode` and forwards it through `onInputTranscript`.
- `AppState` logs the input language code but does not store it for UI.
- `CaptionView` top controls show only the target language.

## References and Borrowed Ideas

### Gemini Live Translate behavior

Google's Gemini 3.5 Live Translate materials describe live translation as automatically detecting multilingual input and translating it to the configured target language. The current Live API setup used by this app has a `translationConfig` with target language and echo settings; there is no source-language config field in the app's current API shape.

Design decision: do not add a fake `sourceLanguageCode` to the provider JSON. Instead, keep provider-compatible setup and add a system-instruction source hint only when the user explicitly chooses a source language.

### Whisper-style language detection

OpenAI Whisper and many ASR pipelines separate source-language detection from transcription output. Relevant pattern: keep the chosen/expected language and detected language as different pieces of state because a model may detect a different language than the user's hint.

Borrowed idea: LiveBuddy will store `settings.sourceLanguageCode` as an optional user hint and `detectedSourceLanguageCode` as runtime observation.

### Subtitle/player UI patterns

Players such as mpv/IINA expose selected subtitle/audio languages separately from detected or metadata-derived language labels. Relevant pattern: UI can show a compact source-to-target pair while keeping language metadata as structured codes.

Borrowed idea: show `Auto → Target`, `Detected: Source → Target`, or `Chosen Source → Target` in the HUD without rewriting transcript data.

## Design

### Settings model

Add:

```swift
var sourceLanguageCode: String? = nil
```

`nil` means automatic detection. It is persisted in `settings.json` and decoded as nil for legacy settings.

Changing `sourceLanguageCode` should require a session restart because it changes the setup prompt sent to Gemini.

### Provider setup behavior

Do not add `sourceLanguageCode` to `translationConfig`.

If `sourceLanguageCode` is non-nil, prepend a compact source hint to `systemInstruction`:

```text
The input speech is primarily in Japanese (ja). Translate from this source language unless the speaker clearly switches language.
```

Then append the user's custom prompt. If auto-detect is selected, no hint is added.

### Runtime detection state

Add to `AppState`:

```swift
@Published private(set) var detectedSourceLanguageCode: String?
```

Update it when `onInputTranscript` receives a non-empty language code. Reset it on every new `start()`.

Expose:

```swift
var sourceLanguageDisplayText: String
var languagePairDisplayText: String
```

Examples:

- auto and no detection yet: `Auto → Vietnamese`
- auto and detected English: `Detected: English → Vietnamese`
- manual Japanese: `Japanese → Vietnamese`

### UI

In Settings and Menu Bar:

- Add `Translate from` picker above `Translate to`.
- First option: `Auto Detect` tagged as `nil`.
- Then all `TranslationLanguage.all` languages.

In HUD top controls:

- Replace target-only label with `languagePairDisplayText`.
- Keep it compact with line limit and wider max width.

### Localization

Add keys:

- `translateFrom`
- `autoDetectLanguage`
- `detectedSourceLanguage`

Translate all eight interface languages.

### Memory/performance

- Store only one optional detected language code string.
- No language-detection model or local audio analysis.
- No buffering, no transcript duplication.
- Provider setup remains minimal.

## Non-goals

- Local language detection model.
- Forced provider `sourceLanguageCode` config field.
- Per-segment language switching UI.
- Editing transcript language metadata.
