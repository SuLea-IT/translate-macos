# Glossary Imports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add public terminology source download, custom link import, local file import, bounded parsing, and merge reporting to the existing LiveBuddy terminology glossary.

**Architecture:** Keep prompt injection unchanged and add a pure `GlossaryImport` layer for parsing/validation plus a small `GlossaryImportService` for disk-backed downloads/cache. `AppState` merges parsed entries into `AppSettings.glossaryEntries`, while `SettingsView` exposes a compact import UI below the existing manual glossary controls.

**Tech Stack:** Swift, SwiftUI, Foundation `URLSession`, `XMLParser`, `FileManager`, Process-backed `/usr/bin/unzip` for ZIP listing/extraction in the desktop sandbox, existing Swift Testing tests and local `swiftc -typecheck` verification.

---

## File Structure

- Create `LiveBuddy/Models/GlossaryImport.swift`: pure import models, URL validation, CSV/TSV/TBX parsers, ZIP orchestration, and merge logic.
- Create `LiveBuddy/Services/GlossaryImportService.swift`: HTTPS download/cache and local-file import service.
- Create `LiveBuddyTests/GlossaryImportTests.swift`: unit tests for parsing, URL validation, dedupe, limits, ZIP filtering, and service cache paths.
- Modify `LiveBuddy/Models/AppState.swift`: import status properties and async import methods.
- Modify `LiveBuddy/Views/Settings/SettingsView.swift`: import UI fields/buttons and file picker.
- Modify `LiveBuddy/Models/InterfaceLanguage.swift`: localized strings for import UI and results.
- Modify `README.md`: document public/custom glossary imports.

## Task 1: Pure import models and parser tests

**Files:**
- Create: `LiveBuddyTests/GlossaryImportTests.swift`
- Create: `LiveBuddy/Models/GlossaryImport.swift`

- [ ] **Step 1: Write failing parser tests**

Add tests covering TSV, CSV, TBX, dedupe, limit, and URL validation:

```swift
import Foundation
import Testing
@testable import LiveBuddy

struct GlossaryImportTests {
    @Test func tsvImportTrimsTermsAndKeepsCommentNote() throws {
        let data = "  OpenAI  \t  OpenAI  \t company name\n  Gemini Live\tGemini Live API\n".data(using: .utf8)!
        let result = try GlossaryImportParser().parse(data: data, fileName: "terms.tsv", sourceName: "Custom TSV", existingEntries: [], options: .default)
        #expect(result.added == 2)
        #expect(result.entries[0].sourceTerm == "OpenAI")
        #expect(result.entries[0].targetTerm == "OpenAI")
        #expect(result.entries[0].note.contains("company name"))
    }

    @Test func csvImportHandlesQuotedCommasAndHeaderMapping() throws {
        let data = "source,target,note\n\"Gemini, Live\",\"Gemini Live API\",\"quoted source\"\n".data(using: .utf8)!
        let result = try GlossaryImportParser().parse(data: data, fileName: "terms.csv", sourceName: "Custom CSV", existingEntries: [], options: .default)
        #expect(result.added == 1)
        #expect(result.entries[0].sourceTerm == "Gemini, Live")
        #expect(result.entries[0].targetTerm == "Gemini Live API")
    }

    @Test func importSkipsCaseInsensitiveDuplicatesAndAppliesLimitAfterDedupe() throws {
        let existing = [GlossaryEntry(sourceTerm: "OpenAI", targetTerm: "OpenAI")]
        let data = "openai\tduplicate\nCodex\tCodex\nGemini\tGemini\n".data(using: .utf8)!
        let result = try GlossaryImportParser().parse(data: data, fileName: "terms.tsv", sourceName: "Custom TSV", existingEntries: existing, options: GlossaryImportOptions(sourceLanguageCode: "en", targetLanguageCode: "zh", importLimit: 1))
        #expect(result.added == 1)
        #expect(result.skippedDuplicate == 1)
        #expect(result.entries.map(\.sourceTerm) == ["Codex"])
    }

    @Test func tbxImportExtractsSelectedLanguagePairs() throws {
        let xml = """
        <?xml version="1.0" encoding="UTF-8"?>
        <tbx><text><body>
          <termEntry id="c1">
            <langSet xml:lang="en"><tig><term>screen recording</term></tig></langSet>
            <langSet xml:lang="zh-CN"><tig><term>屏幕录制</term></tig></langSet>
          </termEntry>
        </body></text></tbx>
        """
        let result = try GlossaryImportParser().parse(data: Data(xml.utf8), fileName: "terms.tbx", sourceName: "TBX", existingEntries: [], options: GlossaryImportOptions(sourceLanguageCode: "en", targetLanguageCode: "zh-CN", importLimit: 500))
        #expect(result.added == 1)
        #expect(result.entries[0].sourceTerm == "screen recording")
        #expect(result.entries[0].targetTerm == "屏幕录制")
    }

    @Test func urlValidatorRejectsHttpAndAcceptsHttps() {
        #expect(GlossaryImportURLValidator.remoteURL(from: "http://example.com/terms.tsv") == nil)
        #expect(GlossaryImportURLValidator.remoteURL(from: "https://example.com/terms.tsv")?.scheme == "https")
    }
}
```

- [ ] **Step 2: Run RED check**

Run:

```bash
rm -rf /tmp/livebuddy_typecheck && mkdir -p /tmp/livebuddy_typecheck
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

Expected before implementation: tests cannot compile in Xcode/CI because `GlossaryImportParser` and related models do not exist. Local app typecheck still passes because tests are not included.

- [ ] **Step 3: Implement pure import model/parser**

Implement:

```swift
struct GlossaryImportOptions: Equatable { ... }
struct GlossaryImportResult: Equatable { ... }
enum GlossaryImportError: LocalizedError, Equatable { ... }
struct GlossaryImportURLValidator { static func remoteURL(from value: String) -> URL? }
struct GlossaryImportParser { func parse(data:fileName:sourceName:existingEntries:options:) throws -> GlossaryImportResult }
```

Parser behavior must match `docs/superpowers/specs/2026-06-29-glossary-imports-design.md` for TSV, CSV, TBX/XML, and bounded merge.

- [ ] **Step 4: Run GREEN checks**

Run local app typecheck and focused test compilation where available:

```bash
rm -rf /tmp/livebuddy_typecheck && mkdir -p /tmp/livebuddy_typecheck
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

Expected: app source typechecks; CI will run Swift Testing with full Xcode.

- [ ] **Step 5: Commit**

```bash
git add LiveBuddy/Models/GlossaryImport.swift LiveBuddyTests/GlossaryImportTests.swift
git commit -m "feat: add glossary import parser"
```

## Task 2: Disk-backed download/cache service and AppState merge

**Files:**
- Create: `LiveBuddy/Services/GlossaryImportService.swift`
- Modify: `LiveBuddy/Models/AppState.swift`
- Modify: `LiveBuddyTests/GlossaryImportTests.swift`

- [ ] **Step 1: Write failing service/merge tests**

Add tests for service path sanitization and merge:

```swift
@Test func cacheFileNameIsStableAndSanitized() throws {
    let service = GlossaryImportService(cacheDirectory: URL(fileURLWithPath: "/tmp/GlossaryImports"))
    let url = URL(string: "https://example.com/path/Microsoft Terms.tbx")!
    let fileURL = service.cacheURL(for: url, sourceID: "Microsoft Terminology")
    #expect(fileURL.lastPathComponent.hasPrefix("Microsoft-Terminology-"))
    #expect(fileURL.pathExtension == "tbx")
}

@Test func mergerAppendsImportedEntriesAndPreservesExisting() throws {
    let existing = [GlossaryEntry(sourceTerm: "OpenAI", targetTerm: "OpenAI")]
    let imported = [GlossaryEntry(sourceTerm: "Codex", targetTerm: "Codex")]
    let merged = GlossaryImportMerger().merge(existing: existing, imported: imported)
    #expect(merged.map(\.sourceTerm) == ["OpenAI", "Codex"])
}
```

- [ ] **Step 2: Run RED check**

Run local typecheck and expect missing `GlossaryImportService`/`GlossaryImportMerger` before implementation.

- [ ] **Step 3: Implement service and AppState import methods**

Add a service with:

```swift
final class GlossaryImportService {
    init(cacheDirectory: URL? = nil, session: URLSession = .shared, parser: GlossaryImportParser = GlossaryImportParser())
    func cacheURL(for url: URL, sourceID: String) -> URL
    func importRemote(url: URL, sourceName: String, existingEntries: [GlossaryEntry], options: GlossaryImportOptions) async throws -> GlossaryImportResult
    func importLocalFile(url: URL, sourceName: String, existingEntries: [GlossaryEntry], options: GlossaryImportOptions) throws -> GlossaryImportResult
}
```

Add AppState properties and methods:

```swift
@Published private(set) var glossaryImportMessage = ""
@Published private(set) var isImportingGlossary = false
func importGlossary(from url: URL, sourceName: String, importLimit: Int) async
func importGlossary(fromLocalFile url: URL, sourceName: String, importLimit: Int) async
```

- [ ] **Step 4: Run GREEN checks**

Run local source typecheck.

- [ ] **Step 5: Commit**

```bash
git add LiveBuddy/Services/GlossaryImportService.swift LiveBuddy/Models/AppState.swift LiveBuddyTests/GlossaryImportTests.swift
git commit -m "feat: add glossary import service"
```

## Task 3: Settings UI and localization

**Files:**
- Modify: `LiveBuddy/Views/Settings/SettingsView.swift`
- Modify: `LiveBuddy/Models/InterfaceLanguage.swift`

- [ ] **Step 1: Add localized string keys**

Add keys and translations for import labels/statuses. English and Simplified Chinese must be accurate; other supported languages may use concise English fallback if needed.

- [ ] **Step 2: Add Settings import controls**

In `glossarySection`, below the manual add row:

```swift
TextField(appState.t(.glossaryImportLink), text: $glossaryImportURLString)
Stepper("\(appState.t(.glossaryImportLimit)): \(glossaryImportLimit)", value: $glossaryImportLimit, in: 1...2000, step: 50)
Button(appState.t(.downloadAndImport)) { Task { await importGlossaryLink() } }
Button(appState.t(.importFromFile)) { showingGlossaryFileImporter = true }
```

Use `.fileImporter` for local files and call AppState import methods.

- [ ] **Step 3: Verify UI source typecheck**

Run local source typecheck.

- [ ] **Step 4: Commit**

```bash
git add LiveBuddy/Views/Settings/SettingsView.swift LiveBuddy/Models/InterfaceLanguage.swift
git commit -m "feat: add glossary import UI"
```

## Task 4: Documentation, final verification, and push

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README**

Document public/custom glossary import support in the terminology feature bullet.

- [ ] **Step 2: Run verifiers**

Run:

```bash
python3 scripts/verify_p0_onboarding.py
python3 scripts/verify_interface_language.py
python3 scripts/verify_ci_workflow.py
rm -rf /tmp/livebuddy_typecheck && mkdir -p /tmp/livebuddy_typecheck
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

Expected: verifier scripts pass; typecheck exits 0. Existing Swift 6 Sendable warnings may appear and are not part of this feature.

- [ ] **Step 3: Commit docs and push**

```bash
git add README.md
git commit -m "docs: document glossary imports"
git push target HEAD:main
gh run watch <new-run-id> --repo SuLea-IT/translate-macos --exit-status
```

Expected: GitHub Actions Swift workflow completes successfully.
