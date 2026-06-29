# Bilingual Subtitle HUD Design

## Goal

Let users choose how the floating HUD renders captions: translated only, original only, or original + translated as two subtitle lines. Keep history/export behavior unchanged and avoid storing duplicate rendered strings.

## Current State

LiveBuddy already receives both input transcript and output transcript from Gemini:

- `AppState.appendOriginalText(_:)` buffers original input sentences.
- `AppState.appendCaption(_:language:kind:)` pairs a translated output sentence with the next available original sentence.
- `CaptionLine` already stores `originalText` and translated `text`.
- `TranscriptsView` can already show both original and translated text.
- `CaptionView` currently calls `appState.subtitleText`, and `subtitleText` only joins translated output lines plus `captionDraft`.

So the data exists; the missing feature is a HUD-specific display mode and a renderer that can produce two-line caption layout without duplicating stored transcript data.

## Open-Source References and Borrowed Ideas

### mpv

Project: https://github.com/mpv-player/mpv
Manual: https://mpv.io/manual/stable/

Relevant idea: mpv separates primary subtitles from secondary subtitles (`sid` / `secondary-sid`) and lets the renderer decide how to combine visible subtitle tracks. We borrow that separation: original text and translated text remain distinct fields, while the HUD display mode decides what to render.

### IINA

Project: https://github.com/iina/iina

Relevant idea: IINA builds on mpv and exposes subtitle selection/display choices at the player UI layer rather than rewriting media subtitle data. We borrow the UI-level toggle: LiveBuddy will not mutate transcript history when the HUD display mode changes.

### LLPlayer / dual subtitle players

Project example: https://github.com/umlx5h/LLPlayer

Relevant idea: language-learning players often display a smaller secondary line above or below the primary subtitle. We borrow the visual hierarchy: original text is rendered smaller and dimmer; translated text remains the primary styled caption.

### AutoSub / AutoSRT-style pipelines

Project examples: https://github.com/agermanidis/autosub and https://github.com/abhirooptalasila/Auto-SRT

Relevant idea: subtitle pipelines keep timed segments as structured records, then render them to different output formats. We borrow this by adding `SubtitleDisplayLine` records and deriving plain/attributed HUD output on demand.

## Design

### Display mode

Add a HUD-specific enum:

```swift
enum SubtitleDisplayMode: String, CaseIterable, Codable, Identifiable {
    case translated
    case original
    case bilingual
}
```

Default: `.translated` to preserve current behavior.

### Runtime renderer

Add pure value types:

```swift
enum SubtitleDisplayRole: String, Codable, Equatable {
    case original
    case translated
    case spacer
}

struct SubtitleDisplayLine: Codable, Equatable, Identifiable {
    let id: UUID
    let text: String
    let role: SubtitleDisplayRole
}

struct SubtitleDisplayItem: Equatable {
    let original: String?
    let translated: String
}
```

`SubtitleDisplayTextBuilder` derives lines from current `CaptionLine` data and current drafts. It does not persist extra strings. The HUD can render attributed lines; tests can verify plain text/roles.

### HUD rendering

`CaptionScrollTextView` changes from a single string input to `[SubtitleDisplayLine]`:

- `.translated` lines use the existing subtitle font/color settings.
- `.original` lines use about 78% of the font size and a dimmed color.
- `.spacer` lines add separation between caption pairs.
- Smooth scroll-to-bottom behavior remains unchanged.

### Settings

Add `AppSettings.subtitleDisplayMode`, shown in Settings and Menu Bar near translation/audio controls. This is a UI-only setting and must not restart the Gemini session.

### Localization

Add one key: `subtitleDisplayMode`, and reuse existing localized `original`, `translated`, and `both` labels for the picker options.

## Verification

- Pure tests for `SubtitleDisplayTextBuilder`:
  - translated-only preserves current behavior.
  - bilingual mode returns original line then translated line.
  - original-only falls back to translated text when original is missing.
- Static verifier checks Settings/MenuBar expose `subtitleDisplayMode` and `CaptionView` renders `subtitleLines`.
- `swiftc -typecheck` verifies SwiftUI/AppKit integration locally.
- GitHub Actions verifies xcodebuild build + unit tests after push.

## Out of Scope

- Per-language font families.
- Separate colors/sliders for original line.
- Timestamp alignment fixes for imperfect Gemini transcript pairing.
- SRT/VTT export changes; history already supports original/translated modes.
