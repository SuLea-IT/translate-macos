import AppKit
import Foundation

enum GlobalShortcutAction: UInt32, CaseIterable, Codable, Identifiable, Hashable {
    case toggleTranslation = 1
    case showCaptionWindow = 2
    case toggleMute = 3

    var id: UInt32 { rawValue }
}

struct ShortcutModifierSet: OptionSet, Codable, Hashable {
    let rawValue: UInt32

    init(rawValue: UInt32) {
        self.rawValue = rawValue
    }

    static let control = ShortcutModifierSet(rawValue: 1 << 0)
    static let option = ShortcutModifierSet(rawValue: 1 << 1)
    static let command = ShortcutModifierSet(rawValue: 1 << 2)
    static let shift = ShortcutModifierSet(rawValue: 1 << 3)

    init(eventModifierFlags: NSEvent.ModifierFlags) {
        var result: ShortcutModifierSet = []
        if eventModifierFlags.contains(.control) { result.insert(.control) }
        if eventModifierFlags.contains(.option) { result.insert(.option) }
        if eventModifierFlags.contains(.command) { result.insert(.command) }
        if eventModifierFlags.contains(.shift) { result.insert(.shift) }
        self = result
    }

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

    static func defaultShortcut(for action: GlobalShortcutAction) -> GlobalShortcut {
        defaults.first { $0.action == action }!
    }

    static func defaultShortcutsByAction() -> [GlobalShortcutAction: GlobalShortcut] {
        Dictionary(uniqueKeysWithValues: defaults.map { ($0.action, $0) })
    }

    static func keyEquivalent(forKeyCode keyCode: UInt32, characters: String?) -> String {
        let functionKeys: [UInt32: String] = [
            122: "F1", 120: "F2", 99: "F3", 118: "F4", 96: "F5",
            97: "F6", 98: "F7", 100: "F8", 101: "F9", 109: "F10",
            103: "F11", 111: "F12", 105: "F13", 107: "F14", 113: "F15",
            106: "F16", 64: "F17", 79: "F18", 80: "F19", 90: "F20"
        ]
        if let functionKey = functionKeys[keyCode] {
            return functionKey
        }
        return characters?.trimmingCharacters(in: .whitespacesAndNewlines).uppercased() ?? ""
    }

    var isFunctionKey: Bool {
        let functionKeyCodes: Set<UInt32> = [
            122, 120, 99, 118, 96, 97, 98, 100, 101, 109,
            103, 111, 105, 107, 113, 106, 64, 79, 80, 90
        ]
        if functionKeyCodes.contains(keyCode) {
            return true
        }
        let uppercased = keyEquivalent.uppercased()
        guard uppercased.hasPrefix("F") else { return false }
        return Int(uppercased.dropFirst()).map { (1...20).contains($0) } ?? false
    }

    func matchesKeyCombination(_ other: GlobalShortcut) -> Bool {
        keyCode == other.keyCode && modifiers == other.modifiers
    }
}

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

    @discardableResult
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

    private enum CodingKeys: String, CodingKey {
        case shortcuts
    }

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
        guard !shortcut.keyEquivalent.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return .emptyKey
        }
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

enum GlobalShortcutRegistrationStatus: Equatable {
    case registered
    case failed(Int32)
}

struct GlobalShortcutRegistrationResult: Equatable {
    let shortcut: GlobalShortcut
    let status: GlobalShortcutRegistrationStatus
}
