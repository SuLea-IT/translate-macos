import Foundation
import Testing
@testable import LiveBuddy

struct GlossaryTests {
    @Test func settingsDefaultToEmptyGlossary() {
        #expect(AppSettings().glossaryEntries.isEmpty)
    }

    @Test func changingGlossaryRequiresSessionRestart() {
        let oldSettings = AppSettings()
        var newSettings = oldSettings
        newSettings.glossaryEntries = [GlossaryEntry(sourceTerm: "OpenAI", targetTerm: "OpenAI")]

        #expect(newSettings.requiresSessionRestart(comparedTo: oldSettings))
    }

    @Test func promptBuilderSortsDeduplicatesAndSkipsDisabledEntries() {
        let entries = [
            GlossaryEntry(sourceTerm: "AI", targetTerm: "AI"),
            GlossaryEntry(sourceTerm: "Gemini Live", targetTerm: "Gemini Live API"),
            GlossaryEntry(sourceTerm: "ai", targetTerm: "duplicate"),
            GlossaryEntry(sourceTerm: "unused", targetTerm: "unused", isEnabled: false)
        ]

        let prompt = GlossaryPromptBuilder().instruction(for: entries)

        #expect(prompt.contains("Gemini Live => Gemini Live API"))
        #expect(prompt.contains("AI => AI"))
        #expect(prompt.contains("duplicate") == false)
        #expect(prompt.contains("unused") == false)
        #expect(prompt.range(of: "Gemini Live")!.lowerBound < prompt.range(of: "AI => AI")!.lowerBound)
    }

    @Test func emptyTargetMeansPreserveSourceTerm() {
        let prompt = GlossaryPromptBuilder().instruction(for: [
            GlossaryEntry(sourceTerm: "Codex", targetTerm: "")
        ])

        #expect(prompt.contains("Codex => Codex"))
    }

    @Test func editorTrimsAndAddsNonEmptyTerms() {
        let entries = GlossaryEntryEditor().add(
            sourceTerm: "  Gemini   Live  ",
            targetTerm: "  Gemini Live API  ",
            to: []
        )

        #expect(entries.count == 1)
        #expect(entries[0].sourceTerm == "Gemini Live")
        #expect(entries[0].targetTerm == "Gemini Live API")
    }

    @Test func editorSkipsEmptySourceTerms() {
        let existing = [GlossaryEntry(sourceTerm: "OpenAI", targetTerm: "OpenAI")]
        let entries = GlossaryEntryEditor().add(sourceTerm: "   ", targetTerm: "ignored", to: existing)

        #expect(entries == existing)
    }

    @Test func editorDeletesOnlyMatchingEntry() {
        let first = GlossaryEntry(id: UUID(uuidString: "00000000-0000-0000-0000-000000000001")!, sourceTerm: "OpenAI")
        let second = GlossaryEntry(id: UUID(uuidString: "00000000-0000-0000-0000-000000000002")!, sourceTerm: "Gemini")

        let entries = GlossaryEntryEditor().delete(first, from: [first, second])

        #expect(entries == [second])
    }
}
