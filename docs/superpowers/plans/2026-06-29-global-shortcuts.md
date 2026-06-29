# Global Shortcuts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add global keyboard shortcuts for start/stop, show captions, and mute/unmute translated audio.

**Architecture:** Add a pure shortcut model, a Carbon-backed registrar, and AppState routing. Keep low-level Carbon code isolated and avoid polling or third-party dependencies.

**Tech Stack:** Swift, Carbon HIToolbox `RegisterEventHotKey`, SwiftUI, Swift Testing, Python static verifier, GitHub Actions xcodebuild.

---

## File Structure

Create:

- `LiveBuddy/Models/GlobalShortcut.swift` — pure shortcut model and default bindings.
- `LiveBuddy/Services/CarbonGlobalShortcutRegistrar.swift` — Carbon registration wrapper.
- `LiveBuddyTests/GlobalShortcutTests.swift` — pure model tests.

Modify:

- `LiveBuddy/Models/AppSettings.swift` — add `globalShortcutsEnabled`.
- `LiveBuddy/Models/AppState.swift` — own registrar, register/unregister, route shortcut actions.
- `LiveBuddy/Views/Settings/SettingsView.swift` — show enable toggle and bindings list.
- `LiveBuddy/Models/InterfaceLanguage.swift` — add localized labels.
- `scripts/verify_p0_onboarding.py` — add static checks.
- `README.md` — document default shortcuts.

---

### Task 1: Pure shortcut model

**Files:**
- Create: `LiveBuddy/Models/GlobalShortcut.swift`
- Create: `LiveBuddyTests/GlobalShortcutTests.swift`

- [ ] **Step 1: Write failing tests**

Create `LiveBuddyTests/GlobalShortcutTests.swift`:

```swift
import Testing
@testable import LiveBuddy

struct GlobalShortcutTests {
    @Test func defaultShortcutsHaveUniqueActionsAndIdentifiers() {
        let shortcuts = GlobalShortcut.defaults

        #expect(Set(shortcuts.map(\.action)).count == shortcuts.count)
        #expect(Set(shortcuts.map(\.id)).count == shortcuts.count)
    }

    @Test func defaultShortcutDisplayTextIsHumanReadable() {
        let toggle = GlobalShortcut.defaults.first { $0.action == .toggleTranslation }

        #expect(toggle?.displayText == "⌃⌥⌘T")
    }
}
```

- [ ] **Step 2: Verify failure**

Run:

```bash
cat > /tmp/global_shortcut_red.swift <<'SWIFT'
@main
struct Check {
    static func main() {
        _ = GlobalShortcut.defaults
    }
}
SWIFT
swiftc -parse-as-library /tmp/global_shortcut_red.swift -o /tmp/global_shortcut_red
```

Expected: compile failure because `GlobalShortcut` does not exist.

- [ ] **Step 3: Implement pure model**

Create `LiveBuddy/Models/GlobalShortcut.swift`:

```swift
import Foundation

enum GlobalShortcutAction: UInt32, CaseIterable, Codable, Identifiable, Hashable {
    case toggleTranslation = 1
    case showCaptionWindow = 2
    case toggleMute = 3

    var id: UInt32 { rawValue }
}

struct ShortcutModifierSet: OptionSet, Codable, Hashable {
    let rawValue: UInt32

    static let control = ShortcutModifierSet(rawValue: 1 << 0)
    static let option = ShortcutModifierSet(rawValue: 1 << 1)
    static let command = ShortcutModifierSet(rawValue: 1 << 2)
    static let shift = ShortcutModifierSet(rawValue: 1 << 3)

    var displayText: String {
        var text = ""
        if contains(.control) { text += "⌃" }
        if contains(.option) { text += "⌥" }
        if contains(.shift) { text += "⇧" }
        if contains(.command) { text += "⌘" }
        return text
    }
}

struct GlobalShortcut: Identifiable, Codable, Equatable, Hashable {
    let action: GlobalShortcutAction
    let keyCode: UInt32
    let keyEquivalent: String
    let modifiers: ShortcutModifierSet

    var id: UInt32 { action.rawValue }
    var displayText: String { "\(modifiers.displayText)\(keyEquivalent.uppercased())" }

    static let defaults: [GlobalShortcut] = [
        GlobalShortcut(action: .toggleTranslation, keyCode: 17, keyEquivalent: "T", modifiers: [.control, .option, .command]),
        GlobalShortcut(action: .showCaptionWindow, keyCode: 8, keyEquivalent: "C", modifiers: [.control, .option, .command]),
        GlobalShortcut(action: .toggleMute, keyCode: 46, keyEquivalent: "M", modifiers: [.control, .option, .command])
    ]
}

enum GlobalShortcutRegistrationStatus: Equatable {
    case registered
    case failed(Int32)
}

struct GlobalShortcutRegistrationResult: Equatable {
    let shortcut: GlobalShortcut
    let status: GlobalShortcutRegistrationStatus
}
```

- [ ] **Step 4: Verify**

Run:

```bash
cat > /tmp/global_shortcut_check.swift <<'SWIFT'
@main
struct Check {
    static func main() {
        let shortcuts = GlobalShortcut.defaults
        precondition(Set(shortcuts.map(\.action)).count == shortcuts.count)
        precondition(shortcuts.first { $0.action == .toggleTranslation }?.displayText == "⌃⌥⌘T")
        print("global shortcut model check passed")
    }
}
SWIFT
swiftc -parse-as-library LiveBuddy/Models/GlobalShortcut.swift /tmp/global_shortcut_check.swift -o /tmp/global_shortcut_check
/tmp/global_shortcut_check
```

Expected: prints `global shortcut model check passed`.

- [ ] **Step 5: Commit**

```bash
git add LiveBuddy/Models/GlobalShortcut.swift LiveBuddyTests/GlobalShortcutTests.swift
git commit -m "feat: add global shortcut model"
```

---

### Task 2: Carbon registrar

**Files:**
- Create: `LiveBuddy/Services/CarbonGlobalShortcutRegistrar.swift`

- [ ] **Step 1: Implement registrar**

Create `LiveBuddy/Services/CarbonGlobalShortcutRegistrar.swift`:

```swift
import Carbon.HIToolbox
import Foundation

protocol GlobalShortcutRegistering: AnyObject {
    func register(_ shortcuts: [GlobalShortcut], handler: @escaping (GlobalShortcutAction) -> Void) -> [GlobalShortcutRegistrationResult]
    func unregisterAll()
}

final class CarbonGlobalShortcutRegistrar: GlobalShortcutRegistering {
    private let signature = OSType(0x4C425548) // LBUH
    private var hotKeys: [UInt32: EventHotKeyRef] = [:]
    private var handler: ((GlobalShortcutAction) -> Void)?
    private var eventHandler: EventHandlerRef?

    func register(_ shortcuts: [GlobalShortcut], handler: @escaping (GlobalShortcutAction) -> Void) -> [GlobalShortcutRegistrationResult] {
        unregisterAll()
        self.handler = handler
        installHandlerIfNeeded()

        return shortcuts.map { shortcut in
            var hotKeyRef: EventHotKeyRef?
            var hotKeyID = EventHotKeyID(signature: signature, id: shortcut.action.rawValue)
            let status = RegisterEventHotKey(
                shortcut.keyCode,
                carbonModifiers(from: shortcut.modifiers),
                hotKeyID,
                GetApplicationEventTarget(),
                0,
                &hotKeyRef
            )
            if status == noErr, let hotKeyRef {
                hotKeys[shortcut.action.rawValue] = hotKeyRef
                return GlobalShortcutRegistrationResult(shortcut: shortcut, status: .registered)
            }
            return GlobalShortcutRegistrationResult(shortcut: shortcut, status: .failed(Int32(status)))
        }
    }

    func unregisterAll() {
        for hotKey in hotKeys.values {
            UnregisterEventHotKey(hotKey)
        }
        hotKeys.removeAll()
        handler = nil
    }

    deinit {
        unregisterAll()
        if let eventHandler {
            RemoveEventHandler(eventHandler)
        }
    }

    private func installHandlerIfNeeded() {
        guard eventHandler == nil else { return }
        var eventSpec = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        InstallEventHandler(
            GetApplicationEventTarget(),
            { _, event, userData in
                guard let event, let userData else { return noErr }
                var hotKeyID = EventHotKeyID()
                let status = GetEventParameter(
                    event,
                    EventParamName(kEventParamDirectObject),
                    EventParamType(typeEventHotKeyID),
                    nil,
                    MemoryLayout<EventHotKeyID>.size,
                    nil,
                    &hotKeyID
                )
                guard status == noErr else { return status }
                let registrar = Unmanaged<CarbonGlobalShortcutRegistrar>.fromOpaque(userData).takeUnretainedValue()
                registrar.handle(id: hotKeyID.id)
                return noErr
            },
            1,
            &eventSpec,
            Unmanaged.passUnretained(self).toOpaque(),
            &eventHandler
        )
    }

    private func handle(id: UInt32) {
        guard let action = GlobalShortcutAction(rawValue: id) else { return }
        DispatchQueue.main.async { [handler] in
            handler?(action)
        }
    }

    private func carbonModifiers(from modifiers: ShortcutModifierSet) -> UInt32 {
        var flags: UInt32 = 0
        if modifiers.contains(.control) { flags |= UInt32(controlKey) }
        if modifiers.contains(.option) { flags |= UInt32(optionKey) }
        if modifiers.contains(.command) { flags |= UInt32(cmdKey) }
        if modifiers.contains(.shift) { flags |= UInt32(shiftKey) }
        return flags
    }
}
```

- [ ] **Step 2: Verify typecheck**

Run the final typecheck command.

- [ ] **Step 3: Commit**

```bash
git add LiveBuddy/Services/CarbonGlobalShortcutRegistrar.swift
git commit -m "feat: add Carbon global shortcut registrar"
```

---

### Task 3: AppState integration and UI

**Files:**
- Modify: `LiveBuddy/Models/AppSettings.swift`
- Modify: `LiveBuddy/Models/AppState.swift`
- Modify: `LiveBuddy/Views/Settings/SettingsView.swift`
- Modify: `LiveBuddy/Models/InterfaceLanguage.swift`
- Modify: `scripts/verify_p0_onboarding.py`

- [ ] **Step 1: Add setting**

Add to `AppSettings`:

```swift
var globalShortcutsEnabled = true
```

Add it to `CodingKeys`, decode with default, and encode it. Do not include it in `requiresSessionRestart`.

- [ ] **Step 2: Integrate AppState**

Add:

```swift
private let globalShortcutRegistrar: GlobalShortcutRegistering
```

Change init to accept `globalShortcutRegistrar: GlobalShortcutRegistering = CarbonGlobalShortcutRegistrar()`.

Call `configureGlobalShortcuts()` after setup. Add:

```swift
func configureGlobalShortcuts() {
    guard settings.globalShortcutsEnabled else {
        globalShortcutRegistrar.unregisterAll()
        return
    }
    let results = globalShortcutRegistrar.register(GlobalShortcut.defaults) { [weak self] action in
        Task { @MainActor in
            self?.performGlobalShortcut(action)
        }
    }
    for result in results {
        if case .failed(let code) = result.status {
            appendLog("Global shortcut \(result.shortcut.displayText) failed to register: \(code)", level: .error)
        }
    }
}

func performGlobalShortcut(_ action: GlobalShortcutAction) {
    switch action {
    case .toggleTranslation:
        toggle()
    case .showCaptionWindow:
        NotificationCenter.default.post(name: .showCaptionWindow, object: nil)
    case .toggleMute:
        updateSetting(\.audioPlayerMuted, to: !settings.audioPlayerMuted)
    }
}
```

In `updateSetting`, if `keyPath == \.globalShortcutsEnabled`, call `configureGlobalShortcuts()`.

- [ ] **Step 3: Add Settings UI**

Add a section in `SettingsView.captionForm`:

```swift
Section(appState.t(.globalShortcuts)) {
    Toggle(appState.t(.enableGlobalShortcuts), isOn: appState.binding(\.globalShortcutsEnabled))
    ForEach(GlobalShortcut.defaults) { shortcut in
        HStack {
            Text(shortcut.action.localizedTitle(language: appState.settings.interfaceLanguage))
            Spacer()
            Text(shortcut.displayText).monospaced()
        }
    }
}
```

- [ ] **Step 4: Add localization**

Add InterfaceText cases and translations:

```swift
case globalShortcuts
case enableGlobalShortcuts
case shortcutToggleTranslation
case shortcutShowCaptionWindow
case shortcutToggleMute
```

Add:

```swift
extension GlobalShortcutAction {
    func localizedTitle(language: InterfaceLanguage) -> String {
        switch self {
        case .toggleTranslation: language.localized(.shortcutToggleTranslation)
        case .showCaptionWindow: language.localized(.shortcutShowCaptionWindow)
        case .toggleMute: language.localized(.shortcutToggleMute)
        }
    }
}
```

- [ ] **Step 5: Add verifier checks**

Update verifier to require global shortcut model, Carbon registrar APIs, `configureGlobalShortcuts`, `performGlobalShortcut`, and settings UI.

- [ ] **Step 6: Verify and commit**

Run verifiers and typecheck, then commit:

```bash
git add LiveBuddy/Models/AppSettings.swift LiveBuddy/Models/AppState.swift LiveBuddy/Views/Settings/SettingsView.swift LiveBuddy/Models/InterfaceLanguage.swift scripts/verify_p0_onboarding.py
git commit -m "feat: wire global shortcuts into app"
```

---

### Task 4: Documentation, push, CI

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document shortcuts**

Add default shortcut list to README.

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

- [ ] **Step 3: Commit and push**

```bash
git add README.md
git commit -m "docs: document global shortcuts"
git push target HEAD:main
```

- [ ] **Step 4: Watch CI**

Use `gh run watch` for the new run. Expected: GitHub Actions `Swift` workflow succeeds.

## Self-Review

- Spec coverage: model, Carbon lifecycle, AppState routing, UI, localization, docs all covered.
- Placeholder scan: no TODO/TBD placeholders.
- Type consistency: `GlobalShortcutAction`, `GlobalShortcut`, `GlobalShortcutRegistering`, and `configureGlobalShortcuts()` are consistent.
