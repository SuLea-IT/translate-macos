# Transcript Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SRT, WebVTT, Markdown, and TXT export for saved transcript sessions.

**Architecture:** Build a pure `TranscriptExporter` that converts `TranscriptSession` + `TranscriptViewMode` into normalized cues and format-specific strings. Keep file writing in a tiny SwiftUI `FileDocument`, and keep the transcript UI limited to selecting export format and presenting `fileExporter`.

**Tech Stack:** Swift, SwiftUI, UniformTypeIdentifiers, Swift Testing, Python static verifiers, GitHub Actions xcodebuild.

---

## File Structure

Create:

- `LiveBuddy/Models/TranscriptExport.swift` — export formats, cue model, filename helper, pure exporter.
- `LiveBuddy/Services/TranscriptExportDocument.swift` — minimal `FileDocument` for UTF-8 text export.
- `LiveBuddyTests/TranscriptExportTests.swift` — tests for cue generation and format output.

Modify:

- `LiveBuddy/Views/Settings/TranscriptsView.swift` — add export menu and `.fileExporter` presentation.
- `LiveBuddy/Models/InterfaceLanguage.swift` — add export labels for all supported UI languages.
- `scripts/verify_p0_onboarding.py` — static checks for exporter and UI wiring.
- `scripts/verify_interface_language.py` — require export localization keys.
- `README.md` — document transcript export formats.

---

### Task 1: Pure transcript exporter

**Files:**
- Create: `LiveBuddyTests/TranscriptExportTests.swift`
- Create: `LiveBuddy/Models/TranscriptExport.swift`

- [ ] **Step 1: Write failing tests**

Create `LiveBuddyTests/TranscriptExportTests.swift` with tests that expect:

- Cue end times use the next cue start.
- Bilingual mode preserves original and translated text on separate lines.
- SRT uses comma milliseconds.
- WebVTT uses `WEBVTT` header and dot milliseconds.
- Markdown includes metadata and selected text.
- TXT exports selected mode without subtitle timing.
- File names are extension-safe.

- [ ] **Step 2: Verify RED**

Run:

```bash
cat > /tmp/transcript_export_red.swift <<'SWIFT'
import Foundation

func check() {
    _ = TranscriptExporter()
    _ = TranscriptExportFormat.srt
}
SWIFT
swiftc -typecheck LiveBuddy/Models/TranscriptSession.swift /tmp/transcript_export_red.swift
```

Expected: compile failure because `TranscriptExporter` and `TranscriptExportFormat` do not exist.

- [ ] **Step 3: Implement exporter**

Create `LiveBuddy/Models/TranscriptExport.swift` with:

- `TranscriptExportFormat`
- `TranscriptExportCue`
- `TranscriptExporter`
- filename sanitization helper

Implementation requirements:

- Generate cues in O(n), sorting by timestamp once.
- Normalize whitespace per line while preserving bilingual line breaks.
- Clamp negative cue starts to `0`.
- Use next cue start as current cue end.
- Estimate final cue duration from text length, clamped to 1.5–6.0 seconds.
- Format SRT timestamps as `HH:MM:SS,mmm`.
- Format WebVTT timestamps as `HH:MM:SS.mmm`.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
cat > /tmp/transcript_export_check.swift <<'SWIFT'
import Foundation

@main
struct Check {
    static func main() {
        let start = Date(timeIntervalSince1970: 100)
        let session = TranscriptSession(
            id: UUID(uuidString: "00000000-0000-0000-0000-000000000001")!,
            startedAt: start,
            endedAt: start.addingTimeInterval(10),
            targetLanguage: "English",
            audioSource: "Screen audio",
            lines: [
                TranscriptLine(text: "Hello", originalText: "你好", languageCode: "en", timestamp: start.addingTimeInterval(0)),
                TranscriptLine(text: "World", originalText: "世界", languageCode: "en", timestamp: start.addingTimeInterval(2))
            ]
        )
        let exporter = TranscriptExporter()
        let srt = exporter.export(session: session, mode: .both, format: .srt)
        precondition(srt.contains("00:00:00,000 --> 00:00:02,000"))
        precondition(srt.contains("你好\nHello"))
        let vtt = exporter.export(session: session, mode: .translated, format: .webVTT)
        precondition(vtt.hasPrefix("WEBVTT\n\n"))
        precondition(vtt.contains("00:00:00.000 --> 00:00:02.000"))
        print("transcript exporter check passed")
    }
}
SWIFT
swiftc -parse-as-library LiveBuddy/Models/TranscriptSession.swift LiveBuddy/Models/TranscriptExport.swift /tmp/transcript_export_check.swift -o /tmp/transcript_export_check
/tmp/transcript_export_check
```

Expected: prints `transcript exporter check passed`.

- [ ] **Step 5: Commit**

```bash
git add LiveBuddy/Models/TranscriptExport.swift LiveBuddyTests/TranscriptExportTests.swift
git commit -m "feat: add transcript export formatter"
```

---

### Task 2: FileDocument wrapper

**Files:**
- Create: `LiveBuddy/Services/TranscriptExportDocument.swift`

- [ ] **Step 1: Write failing typecheck**

Run:

```bash
cat > /tmp/transcript_export_document_red.swift <<'SWIFT'
import SwiftUI
import UniformTypeIdentifiers

func check() {
    _ = TranscriptExportDocument(text: "hello", contentType: .plainText)
}
SWIFT
swiftc -typecheck /tmp/transcript_export_document_red.swift
```

Expected: compile failure because `TranscriptExportDocument` does not exist.

- [ ] **Step 2: Implement document**

Create `LiveBuddy/Services/TranscriptExportDocument.swift`:

- Import `SwiftUI` and `UniformTypeIdentifiers`.
- Store `text` and `contentType`.
- Expose `static var readableContentTypes` with plain text, Markdown, SRT, WebVTT.
- Implement `init(configuration:)` by reading UTF-8 data.
- Implement `fileWrapper(configuration:)` by writing UTF-8 data.

- [ ] **Step 3: Verify typecheck**

Run:

```bash
swiftc -typecheck LiveBuddy/Models/TranscriptExport.swift LiveBuddy/Services/TranscriptExportDocument.swift LiveBuddy/Models/TranscriptSession.swift /tmp/transcript_export_document_red.swift
```

Expected: exit 0.

- [ ] **Step 4: Commit**

```bash
git add LiveBuddy/Services/TranscriptExportDocument.swift
git commit -m "feat: add transcript export document"
```

---

### Task 3: SwiftUI export UI and localization

**Files:**
- Modify: `LiveBuddy/Views/Settings/TranscriptsView.swift`
- Modify: `LiveBuddy/Models/InterfaceLanguage.swift`
- Modify: `scripts/verify_interface_language.py`
- Modify: `scripts/verify_p0_onboarding.py`

- [ ] **Step 1: Add localization keys**

Add `InterfaceText` cases:

- `exportTranscript`
- `exportAsSRT`
- `exportAsWebVTT`
- `exportAsMarkdown`
- `exportAsPlainText`
- `exportFailed`

Add translations for English, Simplified Chinese, Japanese, Korean, Spanish, French, German, and Vietnamese.

- [ ] **Step 2: Add export state to `TranscriptsView`**

Add:

```swift
@State private var exportDocument: TranscriptExportDocument?
@State private var exportFileName = "LiveBuddy-Transcript"
@State private var exportContentType: UTType = .plainText
@State private var exportErrorMessage: String?
private let transcriptExporter = TranscriptExporter()
```

Import `UniformTypeIdentifiers`.

- [ ] **Step 3: Add export menu**

In transcript detail header, after `ShareLink`, add a `Menu` labeled `appState.t(.exportTranscript)` and one button per `TranscriptExportFormat.allCases`.

Each button calls:

```swift
private func prepareExport(session: TranscriptSession, format: TranscriptExportFormat) {
    let text = transcriptExporter.export(session: session, mode: viewMode, format: format)
    exportDocument = TranscriptExportDocument(text: text, contentType: format.contentType)
    exportContentType = format.contentType
    exportFileName = transcriptExporter.defaultFileName(session: session, mode: viewMode, format: format)
}
```

- [ ] **Step 4: Present file exporter**

Attach `.fileExporter` to the detail view using a binding derived from `exportDocument != nil`. On completion, clear the document. On failure, store `exportErrorMessage` and render it as a small red caption near the header.

- [ ] **Step 5: Update verifiers**

Update static checks so CI requires:

- `TranscriptExport.swift`
- `TranscriptExportDocument.swift`
- `TranscriptExporter`, `TranscriptExportFormat`, `TranscriptExportCue`
- `TranscriptsView` uses `fileExporter`, `TranscriptExportDocument`, and `TranscriptExportFormat.allCases`
- all export localization keys translated for every supported language

- [ ] **Step 6: Verify and commit**

Run:

```bash
python3 scripts/verify_p0_onboarding.py
python3 scripts/verify_interface_language.py
rm -rf /tmp/livebuddy_typecheck
mkdir -p /tmp/livebuddy_typecheck
cp -R LiveBuddy /tmp/livebuddy_typecheck/LiveBuddy
python3 - <<'PY'
from pathlib import Path
for p in Path('/tmp/livebuddy_typecheck/LiveBuddy').rglob('*.swift'):
    text = p.read_text()
    marker = '\n#Preview {'
    idx = text.find(marker)
    if idx != -1:
        p.write_text(text[:idx].rstrip() + '\n')
PY
swiftc -typecheck $(find /tmp/livebuddy_typecheck/LiveBuddy -name '*.swift' | sort)
```

Expected: verifier scripts pass and `swiftc` exits 0.

Commit:

```bash
git add LiveBuddy/Views/Settings/TranscriptsView.swift LiveBuddy/Models/InterfaceLanguage.swift scripts/verify_interface_language.py scripts/verify_p0_onboarding.py
git commit -m "feat: add transcript export UI"
```

---

### Task 4: Documentation, push, and CI

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document export formats**

Add transcript export to Key Features and Configuration sections:

- SRT for subtitle editors/video tools.
- WebVTT for web players.
- Markdown/TXT for notes and sharing.

- [ ] **Step 2: Full verification**

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
for p in Path('/tmp/livebuddy_typecheck/LiveBuddy').rglob('*.swift'):
    text = p.read_text()
    marker = '\n#Preview {'
    idx = text.find(marker)
    if idx != -1:
        p.write_text(text[:idx].rstrip() + '\n')
PY
swiftc -typecheck $(find /tmp/livebuddy_typecheck/LiveBuddy -name '*.swift' | sort)
```

Expected: all commands exit 0.

- [ ] **Step 3: Commit and push**

```bash
git add README.md
git commit -m "docs: document transcript export"
git push target HEAD:main
```

- [ ] **Step 4: Watch CI**

Run:

```bash
gh run list --repo SuLea-IT/translate-macos --limit 5
gh run watch <new-run-id> --repo SuLea-IT/translate-macos --exit-status
```

Expected: GitHub Actions `Swift` workflow succeeds.

## Self-Review

- Spec coverage: export formats, cue generation, UI, localization, docs, and verification are all mapped to tasks.
- Placeholder scan: no TBD/TODO placeholders; implementation details are explicit.
- Type consistency: `TranscriptExportFormat`, `TranscriptExportCue`, `TranscriptExporter`, and `TranscriptExportDocument` are consistently named across tasks.
