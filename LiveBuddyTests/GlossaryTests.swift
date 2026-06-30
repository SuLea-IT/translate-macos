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

    @Test func editorUpdatesExistingTermInsteadOfAddingDuplicate() {
        let existing = GlossaryEntry(
            id: UUID(uuidString: "00000000-0000-0000-0000-000000000101")!,
            sourceTerm: "OpenAI",
            targetTerm: "OpenAI",
            note: "keep note",
            isEnabled: false
        )

        let updated = GlossaryEntryEditor().add(sourceTerm: "  openai  ", targetTerm: "  OpenAI API  ", to: [existing])

        #expect(updated.count == 1)
        #expect(updated[0].id == existing.id)
        #expect(updated[0].sourceTerm == "OpenAI")
        #expect(updated[0].targetTerm == "OpenAI API")
        #expect(updated[0].note == "keep note")
        #expect(updated[0].isEnabled == false)
    }

    @Test func editorCollapsesLegacyDuplicateSourceTermsWhenUpdating() {
        let first = GlossaryEntry(sourceTerm: "OpenAI", targetTerm: "old")
        let duplicate = GlossaryEntry(sourceTerm: " openai ", targetTerm: "stale duplicate")
        let other = GlossaryEntry(sourceTerm: "Gemini", targetTerm: "Gemini API")

        let updated = GlossaryEntryEditor().add(sourceTerm: "OPENAI", targetTerm: "OpenAI API", to: [first, duplicate, other])

        #expect(updated.map(\.sourceTerm) == ["OpenAI", "Gemini"])
        #expect(updated.map(\.targetTerm) == ["OpenAI API", "Gemini API"])
    }

    @Test func editorDeletesOnlyMatchingEntry() {
        let first = GlossaryEntry(id: UUID(uuidString: "00000000-0000-0000-0000-000000000001")!, sourceTerm: "OpenAI")
        let second = GlossaryEntry(id: UUID(uuidString: "00000000-0000-0000-0000-000000000002")!, sourceTerm: "Gemini")

        let entries = GlossaryEntryEditor().delete(first, from: [first, second])

        #expect(entries == [second])
    }

    @Test func editorDeletesAllEntriesForBulkReset() {
        let entries = [
            GlossaryEntry(sourceTerm: "OpenAI", targetTerm: "OpenAI"),
            GlossaryEntry(sourceTerm: "Gemini", targetTerm: "Gemini API")
        ]

        let cleared = GlossaryEntryEditor().deleteAll(from: entries)

        #expect(cleared.isEmpty)
    }

    @Test func listDisplayCollapsesLargeImportedGlossariesByDefault() {
        let entries = (1...60).map { index in
            GlossaryEntry(sourceTerm: "Term \(index)", targetTerm: "术语 \(index)")
        }

        let collapsed = GlossaryListDisplay(entries: entries, isExpanded: false, collapsedLimit: 20)
        let expanded = GlossaryListDisplay(entries: entries, isExpanded: true, collapsedLimit: 20)

        #expect(collapsed.visibleEntries.count == 20)
        #expect(collapsed.hiddenCount == 40)
        #expect(collapsed.shouldShowToggle)
        #expect(expanded.visibleEntries.count == 60)
        #expect(expanded.hiddenCount == 0)
    }

    @Test func listDisplayFiltersBySourceTargetAndNoteBeforeApplyingCollapseLimit() {
        let entries = [
            GlossaryEntry(sourceTerm: "screen recording", targetTerm: "屏幕录制", note: "Imported"),
            GlossaryEntry(sourceTerm: "API key", targetTerm: "密钥", note: "Provider"),
            GlossaryEntry(sourceTerm: "meeting notes", targetTerm: "会议纪要", note: "summary")
        ]

        let sourceMatch = GlossaryListDisplay(entries: entries, query: "SCREEN", isExpanded: false, collapsedLimit: 20)
        let targetMatch = GlossaryListDisplay(entries: entries, query: "密钥", isExpanded: false, collapsedLimit: 20)
        let noteMatch = GlossaryListDisplay(entries: entries, query: "summary", isExpanded: false, collapsedLimit: 20)
        let noMatch = GlossaryListDisplay(entries: entries, query: "not found", isExpanded: false, collapsedLimit: 20)

        #expect(sourceMatch.visibleEntries.map(\.sourceTerm) == ["screen recording"])
        #expect(targetMatch.visibleEntries.map(\.sourceTerm) == ["API key"])
        #expect(noteMatch.visibleEntries.map(\.sourceTerm) == ["meeting notes"])
        #expect(noMatch.visibleEntries.isEmpty)
        #expect(sourceMatch.hiddenCount == 0)
    }

    @Test func glossaryExporterWritesCSVHeaderAndEscapesValues() {
        let entries = [
            GlossaryEntry(
                sourceTerm: "Gemini, Live",
                targetTerm: "Gemini \"Live\" API",
                note: "line\nbreak",
                isEnabled: false
            ),
            GlossaryEntry(sourceTerm: "Codex", targetTerm: "", note: "", isEnabled: true)
        ]

        let csv = GlossaryExporter().export(entries: entries)

        #expect(csv.hasPrefix("source,target,note,isEnabled\n"))
        #expect(csv.contains("\"Gemini, Live\",\"Gemini \"\"Live\"\" API\",\"line\nbreak\",false\n"))
        #expect(csv.contains("Codex,,,true\n"))
    }

    @Test func glossaryExporterDefaultFileNameIsExtensionSafe() {
        let fileName = GlossaryExporter().defaultFileName(date: Date(timeIntervalSince1970: 1_700_000_000))

        #expect(fileName.hasPrefix("LiveBuddy-Glossary-"))
        #expect(fileName.hasSuffix(".csv"))
        #expect(fileName.contains("/") == false)
        #expect(fileName.contains(":") == false)
    }
}
