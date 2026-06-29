# Transcript Export Design

## Goal

Let users export a saved transcript session as SRT, WebVTT, Markdown, or plain text from the transcript detail view. The implementation should be lightweight, testable, and derived from structured transcript data instead of duplicating stored export strings.

This follows the product direction: study mature subtitle/export projects and specs, borrow their algorithms and architecture patterns, then implement LiveBuddy-specific code without copying source or adding heavy dependencies.

## Current State

LiveBuddy already stores transcript sessions in `LiveBuddy/Models/TranscriptSession.swift`:

- `TranscriptSession.startedAt` and `endedAt` define session time range.
- `TranscriptLine.timestamp` records when each line was captured.
- `TranscriptLine.text` stores translated text.
- `TranscriptLine.originalText` stores the paired original sentence when available.
- `TranscriptViewMode` already chooses `.both`, `.original`, or `.translated` rendering.
- `TranscriptsView` currently supports copy/share text, but not file export.

Main gaps:

- No dedicated export model or formatter.
- No SRT/WebVTT timing generation.
- No macOS save-file UX for transcript export.
- No export-specific localized labels.

## References and Borrowed Ideas

### cdown/srt

Repository: https://github.com/cdown/srt

Relevant ideas to borrow:

- Represent subtitles as structured records before composing text.
- Keep formatter functions pure and deterministic.
- Sanitize text for subtitle output by normalizing whitespace and avoiding malformed cue bodies.

What we will not copy:

- We will not port Python source or expose a general-purpose subtitle library.
- We will not add a parser/import pipeline in this pass.

### WebVTT specification

Spec: https://www.w3.org/TR/webvtt1/

Relevant requirements to follow:

- WebVTT files start with a `WEBVTT` header.
- Cues use `start --> end` timing lines.
- Cue payload text follows the timing line, separated by blank lines.
- Timing format uses dot-separated milliseconds.

What we will simplify:

- No cue settings, regions, CSS, notes, chapters, or metadata tracks in this pass.

### Subtitle Edit

Repository: https://github.com/SubtitleEdit/subtitleedit

Relevant ideas to borrow:

- Treat export format as a user-facing choice independent from the editing/view mode.
- Support multiple plain text and subtitle formats from one internal model.
- Keep format-specific logic separate from UI actions.

What we will not copy:

- No heavy editor UI, timing waveform, batch conversion, OCR, or advanced subtitle repair.

### Apple SwiftUI file export

Documentation: https://developer.apple.com/documentation/swiftui/view/fileexporter%28ispresented%3Adocument%3Acontenttype%3Adefaultfilename%3Aoncompletion%3A%29

Relevant ideas to use:

- Use the platform file export flow instead of manually managing `NSSavePanel` state where possible.
- Encapsulate exported text in a small `FileDocument` so SwiftUI owns save-panel presentation.

## Design

### Export model

Add `TranscriptExportFormat`:

```swift
enum TranscriptExportFormat: String, CaseIterable, Identifiable, Codable {
    case srt
    case webVTT
    case markdown
    case plainText
}
```

Each format provides:

- `fileExtension`
- `contentType`
- `displayTitle`

Add `TranscriptExportCue`:

```swift
struct TranscriptExportCue: Equatable {
    let index: Int
    let start: TimeInterval
    let end: TimeInterval
    let text: String
}
```

### Cue generation algorithm

Borrow the structured-cue approach from subtitle libraries:

1. Sort transcript lines by timestamp.
2. Convert each line timestamp to a relative offset from `session.startedAt`.
3. Clamp negative offsets to `0`.
4. For each line, choose visible text using `TranscriptViewMode`:
   - `.translated`: translated text only.
   - `.original`: original text if available, otherwise translated text.
   - `.both`: original line and translated line, separated by newline.
5. Normalize text:
   - trim leading/trailing whitespace;
   - collapse spaces and tabs inside a line;
   - preserve intentional line breaks between original/translated text;
   - skip empty cues.
6. Determine cue end time:
   - if a next non-empty cue exists, use the next cue start;
   - otherwise estimate duration from text length, clamped between 1.5 and 6.0 seconds;
   - if `session.endedAt` exists, do not end after it unless the last cue starts after the stored end, in which case still give it the minimum duration.
7. Ensure every cue has `end > start` by at least 0.5 seconds.

This is O(n) time and O(n) cue memory for a transcript. Exports are generated only on demand and are not persisted.

### Formatters

`TranscriptExporter` exposes:

```swift
struct TranscriptExporter {
    func cues(for session: TranscriptSession, mode: TranscriptViewMode) -> [TranscriptExportCue]
    func export(session: TranscriptSession, mode: TranscriptViewMode, format: TranscriptExportFormat) -> String
}
```

SRT format:

```text
1
00:00:00,000 --> 00:00:02,000
Hello

2
00:00:02,000 --> 00:00:04,000
World
```

WebVTT format:

```text
WEBVTT

00:00:00.000 --> 00:00:02.000
Hello
```

Markdown format includes metadata and human-readable timestamps.

Plain text format reuses the same selected mode without metadata-heavy subtitle timing.

### File document

Add `TranscriptExportDocument`, a minimal `FileDocument` wrapper around UTF-8 text. It imports `UniformTypeIdentifiers` and only writes text data.

### UI

In `TranscriptsView` detail header:

- Keep mode picker, Copy All, Share.
- Add an `Export` menu with four options: SRT, WebVTT, Markdown, TXT.
- Selecting a format creates `TranscriptExportDocument` and presents SwiftUI `fileExporter`.
- Default file names include date, mode, and extension-safe text.

No batch export in this pass. No export from the list context menu in this pass.

### Localization

Add localized keys for:

- `exportTranscript`
- `exportAsSRT`
- `exportAsWebVTT`
- `exportAsMarkdown`
- `exportAsPlainText`
- `exportFailed`

All supported interface languages must define these keys so non-English UI does not regress.

### Verification

- Unit tests for cue generation, SRT formatting, WebVTT formatting, Markdown formatting, plain text formatting, filename sanitization.
- Static verifier checks that exporter files exist, UI exposes export, and localization keys are complete.
- Existing CI workflow and typecheck remain passing.

## Non-goals

- Editing timestamps.
- Importing subtitle files.
- Batch exporting all sessions.
- ZIP export.
- Advanced subtitle splitting by character count.
- Speaker diarization.
- Live recording to subtitle file while a session is still running.
