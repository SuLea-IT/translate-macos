# Custom Global Shortcuts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users record, validate, persist, clear, and reset LiveBuddy's global shortcuts from Settings.

**Architecture:** Extend the existing shortcut model with a compact Codable shortcut set and pure validator, then register settings-backed shortcuts through the existing Carbon registrar. Add a short-lived SwiftUI/AppKit recorder field that installs a local key monitor only while recording.

**Tech Stack:** Swift, SwiftUI, AppKit `NSEvent` local monitor, Carbon `RegisterEventHotKey`, Swift Testing, Python static verifiers, GitHub Actions xcodebuild.

---

## Files

- Modify `LiveBuddy/Models/GlobalShortcut.swift`
  - Add `GlobalShortcutSet`, validation result types, function-key detection, default lookup, and normalized comparison helpers.
- Modify `LiveBuddy/Models/AppSettings.swift`
  - Persist `globalShortcuts` with legacy default decode.
- Modify `LiveBuddy/Models/AppState.swift`
  - Register settings-backed shortcuts and expose update/reset/clear methods.
- Modify `LiveBuddy/Views/Settings/SettingsView.swift`
  - Replace read-only shortcut rows with editable rows.
- Create `LiveBuddy/Views/Settings/ShortcutRecorderField.swift`
  - Short-lived local key monitor recorder control.
- Modify `LiveBuddy/Models/InterfaceLanguage.swift`
  - Add eight-language shortcut customization strings.
- Modify `LiveBuddyTests/GlobalShortcutTests.swift`
  - Add model, validation, and Codable tests.
- Modify `scripts/verify_p0_onboarding.py`
  - Add static checks for custom shortcut integration and no event tap.
- Modify `README.md`
  - Document custom global shortcut editing.

---

## Task 1: Shortcut model and validation

**Files:**
- Modify: `LiveBuddy/Models/GlobalShortcut.swift`
- Test: `LiveBuddyTests/GlobalShortcutTests.swift`

- [ ] **Step 1: Write failing tests**

Append these tests to `LiveBuddyTests/GlobalShortcutTests.swift`:

```swift
extension GlobalShortcutTests {
    @Test func shortcutSetDefaultsContainAllActions() {
        let set = GlobalShortcutSet.defaults

        #expect(set.shortcut(for: .toggleTranslation)?.displayText == "⌃⌥⌘T")
        #expect(set.shortcut(for: .showCaptionWindow)?.displayText == "⌃⌥⌘C")
        #expect(set.shortcut(for: .toggleMute)?.displayText == "⌃⌥⌘M")
        #expect(set.enabledShortcuts.count == GlobalShortcutAction.allCases.count)
    }

    @Test func customShortcutSetRoundTripsThroughCodable() throws {
        var set = GlobalShortcutSet.defaults
        let custom = GlobalShortcut(action: .toggleMute, keyCode: 15, keyEquivalent: "R", modifiers: [.control, .command])

        let result = set.update(custom)
        #expect(result == .valid)

        let data = try JSONEncoder().encode(set)
        let decoded = try JSONDecoder().decode(GlobalShortcutSet.self, from: data)

        #expect(decoded.shortcut(for: .toggleMute) == custom)
    }

    @Test func duplicateShortcutIsRejectedWithinLiveBuddy() {
        var set = GlobalShortcutSet.defaults
        let duplicate = GlobalShortcut(action: .toggleMute, keyCode: 17, keyEquivalent: "T", modifiers: [.control, .option, .command])

        let result = set.update(duplicate)

        #expect(result == .duplicateLiveBuddyShortcut(conflictingAction: .toggleTranslation))
        #expect(set.shortcut(for: .toggleMute)?.displayText == "⌃⌥⌘M")
    }

    @Test func bareLetterShortcutIsInvalidButFunctionKeyIsValid() {
        let bareLetter = GlobalShortcut(action: .toggleTranslation, keyCode: 0, keyEquivalent: "A", modifiers: [])
        let functionKey = GlobalShortcut(action: .toggleTranslation, keyCode: 122, keyEquivalent: "F1", modifiers: [])

        #expect(GlobalShortcutValidator.validate(bareLetter, in: .defaults) == .missingRequiredModifier)
        #expect(GlobalShortcutValidator.validate(functionKey, in: .defaults) == .valid)
    }

    @Test func resetRestoresDefaultShortcut() {
        var set = GlobalShortcutSet.defaults
        _ = set.update(GlobalShortcut(action: .toggleMute, keyCode: 15, keyEquivalent: "R", modifiers: [.control, .command]))

        set.reset(.toggleMute)

        #expect(set.shortcut(for: .toggleMute)?.displayText == "⌃⌥⌘M")
    }
}
```

- [ ] **Step 2: Verify RED**

Use local typecheck to confirm the new symbols are missing:

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
swiftc -typecheck $(find /tmp/livebuddy_typecheck/LiveBuddy -name '*.swift' | sort) LiveBuddyTests/GlobalShortcutTests.swift
```

Expected: failure mentioning `GlobalShortcutSet` or `GlobalShortcutValidator`.

- [ ] **Step 3: Implement model and validator**

In `LiveBuddy/Models/GlobalShortcut.swift`, add below `GlobalShortcut`:

```swift
enum GlobalShortcutValidationResult: Equatable {
    case valid
    case emptyKey
    case missingRequiredModifier
    case duplicateLiveBuddyShortcut(conflictingAction: GlobalShortcutAction)
    case systemConflict
    case menuConflict(String)
}

struct GlobalShortcutSet: Codable, Equatable {
    private var shortcutsByAction: [GlobalShortcutAction: GlobalShortcut]

    static let defaults = GlobalShortcutSet(shortcuts: GlobalShortcut.defaults)

    var enabledShortcuts: [GlobalShortcut] {
        GlobalShortcutAction.allCases.compactMap { shortcutsByAction[$0] }
    }

    init(shortcuts: [GlobalShortcut] = GlobalShortcut.defaults) {
        var values = GlobalShortcut.defaultShortcutsByAction()
        for shortcut in shortcuts {
            values[shortcut.action] = shortcut
        }
        shortcutsByAction = values
    }

    func shortcut(for action: GlobalShortcutAction) -> GlobalShortcut? {
        shortcutsByAction[action]
    }

    mutating func update(_ shortcut: GlobalShortcut) -> GlobalShortcutValidationResult {
        let result = GlobalShortcutValidator.validate(shortcut, in: self)
        guard result == .valid else { return result }
        shortcutsByAction[shortcut.action] = shortcut
        return .valid
    }

    mutating func clear(_ action: GlobalShortcutAction) {
        shortcutsByAction.removeValue(forKey: action)
    }

    mutating func reset(_ action: GlobalShortcutAction) {
        shortcutsByAction[action] = GlobalShortcut.defaultShortcut(for: action)
    }

    mutating func resetAll() {
        shortcutsByAction = GlobalShortcut.defaultShortcutsByAction()
    }

    private enum CodingKeys: String, CodingKey { case shortcuts }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let shortcuts = try container.decodeIfPresent([GlobalShortcut].self, forKey: .shortcuts) ?? GlobalShortcut.defaults
        self.init(shortcuts: shortcuts)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(enabledShortcuts, forKey: .shortcuts)
    }
}

struct GlobalShortcutValidator {
    static func validate(_ shortcut: GlobalShortcut, in set: GlobalShortcutSet) -> GlobalShortcutValidationResult {
        guard !shortcut.keyEquivalent.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return .emptyKey }
        if !shortcut.isFunctionKey && !shortcut.modifiers.contains(.command) && !shortcut.modifiers.contains(.control) {
            return .missingRequiredModifier
        }
        for existing in set.enabledShortcuts where existing.action != shortcut.action {
            if existing.matchesKeyCombination(shortcut) {
                return .duplicateLiveBuddyShortcut(conflictingAction: existing.action)
            }
        }
        return .valid
    }
}
```

Also add helpers inside/near `GlobalShortcut`:

```swift
static func defaultShortcut(for action: GlobalShortcutAction) -> GlobalShortcut {
    defaults.first { $0.action == action }!
}

static func defaultShortcutsByAction() -> [GlobalShortcutAction: GlobalShortcut] {
    Dictionary(uniqueKeysWithValues: defaults.map { ($0.action, $0) })
}

var isFunctionKey: Bool { (122...126).contains(keyCode) || (96...111).contains(keyCode) }

func matchesKeyCombination(_ other: GlobalShortcut) -> Bool {
    keyCode == other.keyCode && modifiers == other.modifiers
}
```

- [ ] **Step 4: Verify GREEN**

Run the typecheck command from Step 2. Expected: exit 0 with only existing Sendable warnings.

- [ ] **Step 5: Commit**

```bash
git add LiveBuddy/Models/GlobalShortcut.swift LiveBuddyTests/GlobalShortcutTests.swift
git commit -m "feat: add custom shortcut model"
```

---

## Task 2: Persist custom shortcuts in settings

**Files:**
- Modify: `LiveBuddy/Models/AppSettings.swift`
- Test: `LiveBuddyTests/InterfaceLanguageTests.swift` or `LiveBuddyTests/GlobalShortcutTests.swift`

- [ ] **Step 1: Write failing tests**

Append to `LiveBuddyTests/GlobalShortcutTests.swift`:

```swift
extension GlobalShortcutTests {
    @Test func legacySettingsDecodeDefaultGlobalShortcuts() throws {
        let legacyJSON = #"{"activeProvider":"gemini","targetLanguageCode":"ja"}"#.data(using: .utf8)!

        let settings = try JSONDecoder().decode(AppSettings.self, from: legacyJSON)

        #expect(settings.globalShortcuts.shortcut(for: .toggleTranslation)?.displayText == "⌃⌥⌘T")
    }

    @Test func settingsEncodeCustomGlobalShortcuts() throws {
        var settings = AppSettings()
        _ = settings.globalShortcuts.update(GlobalShortcut(action: .toggleMute, keyCode: 15, keyEquivalent: "R", modifiers: [.control, .command]))

        let data = try JSONEncoder().encode(settings)
        let decoded = try JSONDecoder().decode(AppSettings.self, from: data)

        #expect(decoded.globalShortcuts.shortcut(for: .toggleMute)?.displayText == "⌃⌘R")
    }
}
```

- [ ] **Step 2: Verify RED**

Run the typecheck command from Task 1 Step 2. Expected: failure because `AppSettings.globalShortcuts` is missing.

- [ ] **Step 3: Implement settings persistence**

In `LiveBuddy/Models/AppSettings.swift`:

1. Add property near `globalShortcutsEnabled`:

```swift
var globalShortcuts: GlobalShortcutSet = .defaults
```

2. Add `case globalShortcuts` to `CodingKeys`.

3. In `init(from:)`, decode:

```swift
globalShortcuts = try container.decodeIfPresent(GlobalShortcutSet.self, forKey: .globalShortcuts) ?? defaults.globalShortcuts
```

4. In `encode(to:)`, encode:

```swift
try container.encode(globalShortcuts, forKey: .globalShortcuts)
```

Do not add `globalShortcuts` to `requiresSessionRestart`.

- [ ] **Step 4: Verify GREEN**

Run the typecheck command. Expected: exit 0 with only existing Sendable warnings.

- [ ] **Step 5: Commit**

```bash
git add LiveBuddy/Models/AppSettings.swift LiveBuddyTests/GlobalShortcutTests.swift
git commit -m "feat: persist custom global shortcuts"
```

---

## Task 3: AppState uses settings shortcuts

**Files:**
- Modify: `LiveBuddy/Models/AppState.swift`
- Test: static one-off verifier in `/tmp/custom_shortcut_appstate_contract.py`

- [ ] **Step 1: Write failing static contract**

Create `/tmp/custom_shortcut_appstate_contract.py`:

```python
from pathlib import Path
text = Path('/Users/sule/Documents/mac翻译/gemini-live-translate-macos/LiveBuddy/Models/AppState.swift').read_text()
required = [
    'settings.globalShortcuts.enabledShortcuts',
    'updateGlobalShortcut(',
    'clearGlobalShortcut(',
    'resetGlobalShortcut(',
    'resetAllGlobalShortcuts()'
]
missing = [token for token in required if token not in text]
if missing:
    raise SystemExit('missing AppState shortcut integration: ' + ', '.join(missing))
```

Run:

```bash
python3 /tmp/custom_shortcut_appstate_contract.py
```

Expected: failure listing missing tokens.

- [ ] **Step 2: Implement AppState methods**

In `AppState.configureGlobalShortcuts()`, replace `GlobalShortcut.defaults` with `settings.globalShortcuts.enabledShortcuts`.

Add methods near `updateGlobalShortcutsEnabled`:

```swift
@discardableResult
func updateGlobalShortcut(_ shortcut: GlobalShortcut) -> GlobalShortcutValidationResult {
    var next = settings.globalShortcuts
    let result = next.update(shortcut)
    guard result == .valid else { return result }
    settings.globalShortcuts = next
    configureGlobalShortcuts()
    return .valid
}

func clearGlobalShortcut(_ action: GlobalShortcutAction) {
    var next = settings.globalShortcuts
    next.clear(action)
    settings.globalShortcuts = next
    configureGlobalShortcuts()
}

func resetGlobalShortcut(_ action: GlobalShortcutAction) {
    var next = settings.globalShortcuts
    next.reset(action)
    settings.globalShortcuts = next
    configureGlobalShortcuts()
}

func resetAllGlobalShortcuts() {
    var next = settings.globalShortcuts
    next.resetAll()
    settings.globalShortcuts = next
    configureGlobalShortcuts()
}
```

- [ ] **Step 3: Verify**

Run:

```bash
python3 /tmp/custom_shortcut_appstate_contract.py
```

Expected: exit 0.

Run full typecheck. Expected: exit 0 with only existing Sendable warnings.

- [ ] **Step 4: Commit**

```bash
git add LiveBuddy/Models/AppState.swift
git commit -m "feat: register configured global shortcuts"
```

---

## Task 4: Shortcut recorder UI

**Files:**
- Create: `LiveBuddy/Views/Settings/ShortcutRecorderField.swift`
- Modify: `LiveBuddy/Views/Settings/SettingsView.swift`
- Modify: `LiveBuddy/Models/InterfaceLanguage.swift`

- [ ] **Step 1: Add localization keys**

Add `InterfaceText` cases:

```swift
case customizeShortcuts
case recordShortcut
case recordingShortcut
case clearShortcut
case resetShortcut
case resetAllShortcuts
case shortcutInvalid
case shortcutDuplicate
```

Add English translations:

```swift
.customizeShortcuts: "Customize shortcuts",
.recordShortcut: "Record",
.recordingShortcut: "Press a shortcut…",
.clearShortcut: "Clear",
.resetShortcut: "Reset",
.resetAllShortcuts: "Reset All",
.shortcutInvalid: "Use Command or Control for letter and number shortcuts.",
.shortcutDuplicate: "This shortcut is already used by another LiveBuddy action.",
```

Add equivalents for Simplified Chinese, Japanese, Korean, Spanish, French, German, and Vietnamese.

- [ ] **Step 2: Create recorder field**

Create `LiveBuddy/Views/Settings/ShortcutRecorderField.swift`:

```swift
import AppKit
import SwiftUI

struct ShortcutRecorderField: View {
    @EnvironmentObject private var appState: AppState
    let action: GlobalShortcutAction
    @State private var isRecording = false
    @State private var validationResult: GlobalShortcutValidationResult = .valid

    private var shortcut: GlobalShortcut? {
        appState.settings.globalShortcuts.shortcut(for: action)
    }

    var body: some View {
        HStack(spacing: 8) {
            Text(action.localizedTitle(language: appState.settings.interfaceLanguage))
            Spacer()
            Text(isRecording ? appState.t(.recordingShortcut) : (shortcut?.displayText ?? "—"))
                .monospaced()
                .foregroundStyle(isRecording ? .tint : .secondary)
                .frame(minWidth: 96, alignment: .trailing)
            Button(appState.t(.recordShortcut)) { isRecording = true }
                .controlSize(.small)
            Button(appState.t(.clearShortcut)) { appState.clearGlobalShortcut(action) }
                .controlSize(.small)
            Button(appState.t(.resetShortcut)) { appState.resetGlobalShortcut(action) }
                .controlSize(.small)
        }
        .background(
            ShortcutRecorderMonitor(isRecording: $isRecording) { event in
                handle(event)
            }
            .frame(width: 0, height: 0)
        )
        if validationResult != .valid {
            Text(message(for: validationResult))
                .font(.caption)
                .foregroundStyle(.red)
        }
    }

    private func handle(_ event: NSEvent) {
        let key = event.charactersIgnoringModifiers?.uppercased() ?? ""
        if event.keyCode == 53 {
            isRecording = false
            return
        }
        if event.keyCode == 51 || event.keyCode == 117 {
            appState.clearGlobalShortcut(action)
            validationResult = .valid
            isRecording = false
            return
        }
        let shortcut = GlobalShortcut(action: action, keyCode: UInt32(event.keyCode), keyEquivalent: key, modifiers: ShortcutModifierSet(eventModifierFlags: event.modifierFlags))
        validationResult = appState.updateGlobalShortcut(shortcut)
        if validationResult == .valid { isRecording = false }
    }

    private func message(for result: GlobalShortcutValidationResult) -> String {
        switch result {
        case .valid:
            ""
        case .duplicateLiveBuddyShortcut:
            appState.t(.shortcutDuplicate)
        case .emptyKey, .missingRequiredModifier, .systemConflict, .menuConflict:
            appState.t(.shortcutInvalid)
        }
    }
}

private struct ShortcutRecorderMonitor: NSViewRepresentable {
    @Binding var isRecording: Bool
    let onEvent: (NSEvent) -> Void

    func makeNSView(context: Context) -> NSView { NSView() }

    func updateNSView(_ nsView: NSView, context: Context) {
        context.coordinator.update(isRecording: isRecording, onEvent: onEvent)
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    final class Coordinator {
        private var monitor: Any?

        func update(isRecording: Bool, onEvent: @escaping (NSEvent) -> Void) {
            if isRecording, monitor == nil {
                monitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { event in
                    onEvent(event)
                    return nil
                }
            } else if !isRecording, let monitor {
                NSEvent.removeMonitor(monitor)
                self.monitor = nil
            }
        }

        deinit {
            if let monitor { NSEvent.removeMonitor(monitor) }
        }
    }
}
```

Add initializer to `ShortcutModifierSet` in `GlobalShortcut.swift`:

```swift
init(eventModifierFlags: NSEvent.ModifierFlags) {
    var result: ShortcutModifierSet = []
    if eventModifierFlags.contains(.control) { result.insert(.control) }
    if eventModifierFlags.contains(.option) { result.insert(.option) }
    if eventModifierFlags.contains(.command) { result.insert(.command) }
    if eventModifierFlags.contains(.shift) { result.insert(.shift) }
    self = result
}
```

This requires importing AppKit in `GlobalShortcut.swift`.

- [ ] **Step 3: Replace Settings rows**

In `SettingsView` global shortcut section, replace `ForEach(GlobalShortcut.defaults)` rows with:

```swift
Text(appState.t(.customizeShortcuts))
    .font(.caption)
    .foregroundStyle(.secondary)

ForEach(GlobalShortcutAction.allCases) { action in
    ShortcutRecorderField(action: action)
}

Button(appState.t(.resetAllShortcuts)) {
    appState.resetAllGlobalShortcuts()
}
```

- [ ] **Step 4: Verify**

Run interface verifier and full typecheck. Expected: verifier passes; typecheck exits 0 with only existing Sendable warnings.

- [ ] **Step 5: Commit**

```bash
git add LiveBuddy/Views/Settings/ShortcutRecorderField.swift LiveBuddy/Views/Settings/SettingsView.swift LiveBuddy/Models/InterfaceLanguage.swift LiveBuddy/Models/GlobalShortcut.swift
git commit -m "feat: add shortcut recorder UI"
```

---

## Task 5: Static verifier and docs

**Files:**
- Modify: `scripts/verify_p0_onboarding.py`
- Modify: `scripts/verify_interface_language.py`
- Modify: `README.md`

- [ ] **Step 1: Extend static verifier**

In `scripts/verify_p0_onboarding.py`, add checks:

```python
shortcut_recorder_file = root / "LiveBuddy/Views/Settings/ShortcutRecorderField.swift"
if not shortcut_recorder_file.exists():
    errors.append("missing ShortcutRecorderField.swift")
else:
    text = shortcut_recorder_file.read_text()
    for token in ["ShortcutRecorderField", "addLocalMonitorForEvents", "removeMonitor", "updateGlobalShortcut", "clearGlobalShortcut", "resetGlobalShortcut"]:
        if token not in text:
            errors.append(f"ShortcutRecorderField.swift missing {token}")
    if "CGEventTapCreate" in text:
        errors.append("Shortcut recorder must not create a global event tap")
```

Add checks under `GlobalShortcut.swift`:

```python
for token in ["struct GlobalShortcutSet", "struct GlobalShortcutValidator", "GlobalShortcutValidationResult", "defaultShortcut(for:"]:
    if token not in text:
        errors.append(f"GlobalShortcut.swift missing custom shortcut support {token}")
```

Add AppState check:

```python
for token in ["settings.globalShortcuts.enabledShortcuts", "updateGlobalShortcut", "resetAllGlobalShortcuts"]:
    if token not in text:
        errors.append(f"AppState must support custom global shortcuts through {token}")
```

- [ ] **Step 2: Extend interface verifier**

Add these required keys in `scripts/verify_interface_language.py`:

```python
"customizeShortcuts",
"recordShortcut",
"recordingShortcut",
"clearShortcut",
"resetShortcut",
"resetAllShortcuts",
"shortcutInvalid",
"shortcutDuplicate",
```

- [ ] **Step 3: Update README**

Change the global shortcuts row to:

```markdown
| **Global Shortcuts** | Custom shortcuts | Toggle macOS-wide shortcuts, record custom bindings for each action, clear conflicts, or restore defaults. |
```

Add key feature bullet:

```markdown
*   **Custom Global Shortcuts**: Record, clear, and reset macOS-wide shortcuts for starting translation, showing captions, and muting translated audio.
```

- [ ] **Step 4: Full local verification**

Run:

```bash
python3 scripts/verify_p0_onboarding.py && python3 scripts/verify_interface_language.py && python3 scripts/verify_ci_workflow.py
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

Expected: verifier passes; typecheck exits 0 with only known Sendable warnings.

- [ ] **Step 5: Commit**

```bash
git add scripts/verify_p0_onboarding.py scripts/verify_interface_language.py README.md
git commit -m "docs: document custom global shortcuts"
```

---

## Task 6: Push and CI

- [ ] **Step 1: Push**

```bash
git push target HEAD:main
```

- [ ] **Step 2: Watch CI**

```bash
gh run list --repo SuLea-IT/translate-macos --limit 5
gh run watch <new-run-id> --repo SuLea-IT/translate-macos --exit-status
```

- [ ] **Step 3: If CI fails**

Use `superpowers:systematic-debugging` before changing anything.

---

## Self-review

- Spec coverage: model, persistence, AppState registration, recorder UI, localization, verifier/docs, CI.
- No third-party dependency is added.
- Recorder uses local monitor only while recording; no event tap or background polling.
- TDD steps specify failing tests before production code.
- Commands are concrete and use existing local typecheck workflow.
