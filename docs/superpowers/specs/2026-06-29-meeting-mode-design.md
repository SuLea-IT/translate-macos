# Meeting Mode MVP Design

## Goal

Add a no-extra-cost meeting mode to transcript history. Users can open a saved transcript and generate a structured meeting note containing a short summary, key points, action items, and a timeline. The first iteration is fully local and deterministic so it does not increase Gemini API usage.

## Algorithm references and borrowed ideas

- TextRank-style extractive summarization: represent sentences as ranked candidates and select the most central lines rather than asking a model to rewrite everything. This is inspired by the TextRank paper by Mihalcea and Tarau, but implemented as small LiveBuddy-specific scoring over transcript lines.
- Common meeting-note tools separate notes into summary, key points, action items, and timeline. We use the same structure, but source all content from existing transcript lines.

## User experience

In the transcript detail view:

1. User clicks **Meeting Notes**.
2. A meeting notes panel appears above the transcript lines.
3. The panel contains:
   - Summary: 2-3 concise extracted lines.
   - Key points: up to 5 important transcript lines.
   - Action items: lines containing task-like cues such as “todo”, “need to”, “please”, “安排”, “需要”, “待办”.
   - Timeline: timestamped key moments.
4. User can copy the meeting notes as Markdown.
5. User can export meeting notes as Markdown with the existing SwiftUI file exporter path.

## Non-goals

- No LLM-generated abstractive summary in this pass.
- No speaker diarization in this pass.
- No persistent stored summary field in transcript JSON. Notes regenerate from transcript data, so old transcript storage stays compatible.
- No PDF export in this pass.

## Data model

Add `MeetingNotes.swift`:

```swift
struct MeetingNotes: Equatable {
    let summary: [MeetingNoteBullet]
    let keyPoints: [MeetingNoteBullet]
    let actionItems: [MeetingNoteBullet]
    let timeline: [MeetingNoteBullet]
}

struct MeetingNoteBullet: Identifiable, Equatable {
    let id: UUID
    let timestamp: Date
    let offset: TimeInterval
    let text: String
}
```

`MeetingNotesGenerator` exposes:

```swift
func generate(from session: TranscriptSession, mode: TranscriptViewMode) -> MeetingNotes
func markdown(for notes: MeetingNotes, session: TranscriptSession) -> String
func defaultFileName(session: TranscriptSession) -> String
```

## Scoring approach

1. Convert transcript lines to candidate sentences using selected transcript view mode.
2. Normalize text: trim whitespace, collapse repeated spaces, remove empty lines.
3. Tokenize by Unicode letters/numbers, lowercase, remove short/common stop words for English and common Chinese filler particles.
4. Score candidates using:
   - word-frequency sum;
   - longer useful lines get a small boost;
   - lines with question/decision/action cues get a boost;
   - duplicate or near-duplicate text is skipped.
5. Summary picks top 3 candidates in original chronological order.
6. Key points pick top 5 candidates in chronological order.
7. Action items pick up to 5 lines with action cues in chronological order.
8. Timeline picks up to 8 important candidates spread through the session by respecting chronological order and skipping near duplicates.

## UI integration

Modify `TranscriptsView`:

- Add a Meeting Notes button near copy/share/export controls.
- Tapping toggles a generated meeting-note panel.
- The panel shows sections and copy/export buttons.
- Export uses `TranscriptExportDocument` with `.markdown` content type.

## Localization

Add interface strings for:

- Meeting Notes
- Generate Meeting Notes
- Hide Meeting Notes
- Summary
- Key Points
- Action Items
- Timeline
- Copy Meeting Notes
- Export Meeting Notes
- No Action Items Found

## Testing

Unit tests cover:

1. Generator extracts summary and key points from sample transcript.
2. Action item detection catches English and Chinese cue words.
3. Timeline is chronological and includes readable offsets.
4. Markdown export contains all expected sections and metadata.
5. Empty transcript returns empty sections without crashing.

## Verification

- Existing static verifiers pass.
- `swiftc -typecheck` passes for app sources.
- GitHub Actions Swift workflow passes after push.
