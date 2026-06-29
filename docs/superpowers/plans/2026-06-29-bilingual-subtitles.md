# Bilingual Subtitle HUD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a HUD subtitle display mode so users can show translated only, original only, or original + translated two-line captions.

**Architecture:** Keep transcript data as structured `CaptionLine` records and derive HUD display lines on demand through a pure `SubtitleDisplayTextBuilder`. Update the AppKit text renderer to style original and translated roles differently without persisting duplicate rendered strings.

**Tech Stack:** Swift, SwiftUI, AppKit `NSTextView`, Swift Testing, Python static verifier, existing GitHub Actions xcodebuild workflow.

---

## File Structure

Create:

- `LiveBuddy/Models/SubtitleDisplayMode.swift` — display mode enum, display roles, pure line builder.
- `LiveBuddyTests/SubtitleDisplayModeTests.swift` — pure rendering behavior tests.

Modify:

- `LiveBuddy/Models/AppSettings.swift` — persist `subtitleDisplayMode` with default `.translated`.
- `LiveBuddy/Models/AppState.swift` — expose `subtitleLines` derived from existing captions/drafts.
- `LiveBuddy/Views/Caption/CaptionView.swift` — pass display lines into the scroll text view.
- `LiveBuddy/Views/Components/CaptionScrollTextView.swift` — render attributed text by role.
- `LiveBuddy/Views/Settings/SettingsView.swift` — add subtitle display mode picker.
- `LiveBuddy/Views/MenuBar/MenuBarView.swift` — add compact subtitle display mode picker.
- `LiveBuddy/Models/InterfaceLanguage.swift` — add `subtitleDisplayMode` label in all interface languages.
- `scripts/verify_p0_onboarding.py` — static checks for integration.
- `README.md` — document bilingual subtitle display.

---

### Task 1: Pure subtitle display builder

**Files:**
- Create: `LiveBuddy/Models/SubtitleDisplayMode.swift`
- Create: `LiveBuddyTests/SubtitleDisplayModeTests.swift`

- [ ] **Step 1: Write the failing tests**

Create `LiveBuddyTests/SubtitleDisplayModeTests.swift`:

```swift
import Testing
@testable import LiveBuddy

struct SubtitleDisplayModeTests {
    @Test func translatedModeKeepsCurrentSingleTrackText() {
        let lines = SubtitleDisplayTextBuilder.lines(
            items: [SubtitleDisplayItem(original: "Hello", translated: "你好")],
            translatedDraft: "",
            originalDraft: "",
            mode: .translated
        )

        #expect(SubtitleDisplayTextBuilder.plainText(from: lines) == "你好")
    }

    @Test func bilingualModePlacesOriginalAboveTranslation() {
        let lines = SubtitleDisplayTextBuilder.lines(
            items: [SubtitleDisplayItem(original: "Hello", translated: "你好")],
            translatedDraft: "",
            originalDraft: "",
            mode: .bilingual
        )

        #expect(lines.map(\.role) == [.original, .translated])
        #expect(SubtitleDisplayTextBuilder.plainText(from: lines) == "Hello\n你好")
    }

    @Test func originalModeFallsBackToTranslationWhenOriginalMissing() {
        let lines = SubtitleDisplayTextBuilder.lines(
            items: [SubtitleDisplayItem(original: nil, translated: "你好")],
            translatedDraft: "",
            originalDraft: "",
            mode: .original
        )

        #expect(SubtitleDisplayTextBuilder.plainText(from: lines) == "你好")
    }
}
```

- [ ] **Step 2: Verify failure**

Run a local fallback compile:

```bash
cat > /tmp/subtitle_display_red.swift <<'SWIFT'
import Foundation

@main
struct Check {
    static func main() {
        _ = SubtitleDisplayTextBuilder.lines(
            items: [SubtitleDisplayItem(original: "Hello", translated: "你好")],
            translatedDraft: "",
            originalDraft: "",
            mode: .bilingual
        )
    }
}
SWIFT
swiftc -parse-as-library /tmp/subtitle_display_red.swift -o /tmp/subtitle_display_red
```

Expected: compile failure because `SubtitleDisplayTextBuilder` does not exist.

- [ ] **Step 3: Implement pure model**

Create `LiveBuddy/Models/SubtitleDisplayMode.swift` with:

```swift
import Foundation

enum SubtitleDisplayMode: String, CaseIterable, Codable, Identifiable {
    case translated
    case original
    case bilingual

    var id: String { rawValue }
}

enum SubtitleDisplayRole: String, Codable, Equatable {
    case original
    case translated
    case spacer
}

struct SubtitleDisplayLine: Identifiable, Codable, Equatable {
    let id: UUID
    let text: String
    let role: SubtitleDisplayRole

    init(id: UUID = UUID(), text: String, role: SubtitleDisplayRole) {
        self.id = id
        self.text = text
        self.role = role
    }
}

struct SubtitleDisplayItem: Equatable {
    let original: String?
    let translated: String
}

struct SubtitleDisplayTextBuilder {
    static func lines(
        items: [SubtitleDisplayItem],
        translatedDraft: String,
        originalDraft: String,
        mode: SubtitleDisplayMode
    ) -> [SubtitleDisplayLine] {
        var result: [SubtitleDisplayLine] = []
        for item in items {
            append(item: item, to: &result, mode: mode)
        }

        let translatedDraft = translatedDraft.trimmingCharacters(in: .whitespacesAndNewlines)
        let originalDraft = originalDraft.trimmingCharacters(in: .whitespacesAndNewlines)
        if !translatedDraft.isEmpty || !originalDraft.isEmpty {
            append(
                item: SubtitleDisplayItem(original: originalDraft.isEmpty ? nil : originalDraft, translated: translatedDraft.isEmpty ? originalDraft : translatedDraft),
                to: &result,
                mode: mode
            )
        }

        return result
    }

    static func plainText(from lines: [SubtitleDisplayLine]) -> String {
        lines.map(\.text).joined(separator: "\n")
    }

    private static func append(item: SubtitleDisplayItem, to result: inout [SubtitleDisplayLine], mode: SubtitleDisplayMode) {
        let translated = item.translated.trimmingCharacters(in: .whitespacesAndNewlines)
        let original = item.original?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard !translated.isEmpty || !original.isEmpty else { return }

        if !result.isEmpty, mode == .bilingual {
            result.append(SubtitleDisplayLine(text: "", role: .spacer))
        }

        switch mode {
        case .translated:
            result.append(SubtitleDisplayLine(text: translated.isEmpty ? original : translated, role: .translated))
        case .original:
            result.append(SubtitleDisplayLine(text: original.isEmpty ? translated : original, role: .original))
        case .bilingual:
            if !original.isEmpty {
                result.append(SubtitleDisplayLine(text: original, role: .original))
            }
            if !translated.isEmpty {
                result.append(SubtitleDisplayLine(text: translated, role: .translated))
            }
        }
    }
}
```

- [ ] **Step 4: Verify behavior**

Run:

```bash
cat > /tmp/subtitle_display_check.swift <<'SWIFT'
import Foundation

@main
struct Check {
    static func main() {
        let translated = SubtitleDisplayTextBuilder.lines(
            items: [SubtitleDisplayItem(original: "Hello", translated: "你好")],
            translatedDraft: "",
            originalDraft: "",
            mode: .translated
        )
        precondition(SubtitleDisplayTextBuilder.plainText(from: translated) == "你好")

        let bilingual = SubtitleDisplayTextBuilder.lines(
            items: [SubtitleDisplayItem(original: "Hello", translated: "你好")],
            translatedDraft: "",
            originalDraft: "",
            mode: .bilingual
        )
        precondition(bilingual.map(\.role) == [.original, .translated])
        precondition(SubtitleDisplayTextBuilder.plainText(from: bilingual) == "Hello\n你好")
        print("subtitle display check passed")
    }
}
SWIFT
swiftc -parse-as-library LiveBuddy/Models/SubtitleDisplayMode.swift /tmp/subtitle_display_check.swift -o /tmp/subtitle_display_check
/tmp/subtitle_display_check
```

Expected: prints `subtitle display check passed`.

- [ ] **Step 5: Commit**

```bash
git add LiveBuddy/Models/SubtitleDisplayMode.swift LiveBuddyTests/SubtitleDisplayModeTests.swift
git commit -m "feat: add subtitle display model"
```

---

### Task 2: Persist display mode and expose AppState lines

**Files:**
- Modify: `LiveBuddy/Models/AppSettings.swift`
- Modify: `LiveBuddy/Models/AppState.swift`

- [ ] **Step 1: Add setting**

Add to `AppSettings`:

```swift
var subtitleDisplayMode: SubtitleDisplayMode = .translated
```

Add `case subtitleDisplayMode` to `CodingKeys`, decode it with default, and encode it in `encode(to:)`. Do not include it in `requiresSessionRestart` because changing HUD mode must not restart Gemini.

- [ ] **Step 2: Expose AppState display lines**

Replace `subtitleText` internals with `subtitleLines` + plain text compatibility:

```swift
var subtitleLines: [SubtitleDisplayLine] {
    let items = captions
        .filter { $0.kind == .output }
        .map { SubtitleDisplayItem(original: $0.originalText, translated: $0.text) }
    return SubtitleDisplayTextBuilder.lines(
        items: items,
        translatedDraft: captionDraft,
        originalDraft: originalDraft,
        mode: settings.subtitleDisplayMode
    )
}

var subtitleText: String {
    SubtitleDisplayTextBuilder.plainText(from: subtitleLines)
}
```

- [ ] **Step 3: Verify typecheck**

Run the full typecheck command from final verification.

- [ ] **Step 4: Commit**

```bash
git add LiveBuddy/Models/AppSettings.swift LiveBuddy/Models/AppState.swift
git commit -m "feat: persist subtitle display mode"
```

---

### Task 3: HUD renderer and settings UI

**Files:**
- Modify: `LiveBuddy/Views/Caption/CaptionView.swift`
- Modify: `LiveBuddy/Views/Components/CaptionScrollTextView.swift`
- Modify: `LiveBuddy/Views/Settings/SettingsView.swift`
- Modify: `LiveBuddy/Views/MenuBar/MenuBarView.swift`
- Modify: `LiveBuddy/Models/InterfaceLanguage.swift`
- Modify: `scripts/verify_p0_onboarding.py`

- [ ] **Step 1: Update renderer input**

Change `CaptionView` to pass:

```swift
CaptionScrollTextView(
    lines: appState.subtitleLines,
    settings: appState.settings
)
```

Change `CaptionScrollTextView` from `let text: String` to `let lines: [SubtitleDisplayLine]` and build attributed text from line roles.

- [ ] **Step 2: Add attributed role styling**

In `CaptionScrollTextView`, original lines should use `settings.subtitleFontSize * 0.78` and `settings.subtitleColor.nsColor.withAlphaComponent(0.74)`. Translated lines keep the current font/color. Spacer lines append a blank line.

- [ ] **Step 3: Add UI pickers**

In `SettingsView.captionForm`, add a picker near target language:

```swift
Picker(appState.t(.subtitleDisplayMode), selection: appState.binding(\.subtitleDisplayMode)) {
    ForEach(SubtitleDisplayMode.allCases) { mode in
        Text(mode.localizedTitle(language: appState.settings.interfaceLanguage)).tag(mode)
    }
}
```

Add the same compact picker in `MenuBarView` near translation controls.

- [ ] **Step 4: Add localization**

Add `case subtitleDisplayMode` to `InterfaceText`, with translations for all supported languages. Add:

```swift
extension SubtitleDisplayMode {
    func localizedTitle(language: InterfaceLanguage) -> String {
        switch self {
        case .translated: language.localized(.translated)
        case .original: language.localized(.original)
        case .bilingual: language.localized(.both)
        }
    }
}
```

- [ ] **Step 5: Add verifier checks**

Update `scripts/verify_p0_onboarding.py` to require:

- `SubtitleDisplayMode.swift` exists.
- `AppState.swift` contains `subtitleLines`.
- `CaptionView.swift` contains `CaptionScrollTextView(` and `subtitleLines`.
- `CaptionScrollTextView.swift` contains `SubtitleDisplayLine` and `withAlphaComponent`.
- `SettingsView.swift` and `MenuBarView.swift` contain `subtitleDisplayMode`.

- [ ] **Step 6: Verify and commit**

Run local verifiers and typecheck, then commit:

```bash
git add LiveBuddy/Views/Caption/CaptionView.swift LiveBuddy/Views/Components/CaptionScrollTextView.swift LiveBuddy/Views/Settings/SettingsView.swift LiveBuddy/Views/MenuBar/MenuBarView.swift LiveBuddy/Models/InterfaceLanguage.swift scripts/verify_p0_onboarding.py
git commit -m "feat: render bilingual subtitles in HUD"
```

---

### Task 4: Documentation, final verification, push

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document display mode**

Add a short note that HUD captions can show translated only, original only, or original + translated.

- [ ] **Step 2: Run full verification**

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

Expected: verifiers pass; typecheck exits 0, existing Sendable warnings may remain.

- [ ] **Step 3: Commit and push**

```bash
git add README.md
git commit -m "docs: document bilingual subtitle display"
git push target HEAD:main
```

- [ ] **Step 4: Watch CI**

```bash
gh run list --repo SuLea-IT/translate-macos --limit 5
gh run watch <new-run-id> --repo SuLea-IT/translate-macos --exit-status
```

Expected: GitHub Actions `Swift` workflow succeeds.

## Self-Review

- Spec coverage: display mode, structured display lines, HUD rendering, settings/menu UI, localization, docs all covered.
- Placeholder scan: no TODO/TBD placeholders.
- Type consistency: `SubtitleDisplayMode`, `SubtitleDisplayLine`, `SubtitleDisplayTextBuilder`, and `subtitleLines` names are consistent.
