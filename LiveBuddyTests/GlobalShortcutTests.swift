import Foundation
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

extension GlobalShortcutTests {
    @Test func keyEquivalentHelperNamesFunctionKeys() {
        #expect(GlobalShortcut.keyEquivalent(forKeyCode: 122, characters: nil) == "F1")
        #expect(GlobalShortcut.keyEquivalent(forKeyCode: 15, characters: "r") == "R")
    }
}
