import Foundation
import Testing
@testable import LiveBuddy

struct GlossaryImportTests {
    @Test func tsvImportTrimsTermsAndKeepsCommentNote() throws {
        let data = "  OpenAI  \t  OpenAI  \t company name\n  Gemini Live\tGemini Live API\n".data(using: .utf8)!
        let result = try GlossaryImportParser().parse(
            data: data,
            fileName: "terms.tsv",
            sourceName: "Custom TSV",
            existingEntries: [],
            options: .default
        )
        #expect(result.added == 2)
        #expect(result.entries[0].sourceTerm == "OpenAI")
        #expect(result.entries[0].targetTerm == "OpenAI")
        #expect(result.entries[0].note.contains("company name"))
    }

    @Test func csvImportHandlesQuotedCommasAndHeaderMapping() throws {
        let data = "source,target,note\n\"Gemini, Live\",\"Gemini Live API\",\"quoted source\"\n".data(using: .utf8)!
        let result = try GlossaryImportParser().parse(
            data: data,
            fileName: "terms.csv",
            sourceName: "Custom CSV",
            existingEntries: [],
            options: .default
        )
        #expect(result.added == 1)
        #expect(result.entries[0].sourceTerm == "Gemini, Live")
        #expect(result.entries[0].targetTerm == "Gemini Live API")
    }

    @Test func importSkipsCaseInsensitiveDuplicatesAndAppliesLimitAfterDedupe() throws {
        let existing = [GlossaryEntry(sourceTerm: "OpenAI", targetTerm: "OpenAI")]
        let data = "openai\tduplicate\nCodex\tCodex\nGemini\tGemini\n".data(using: .utf8)!
        let result = try GlossaryImportParser().parse(
            data: data,
            fileName: "terms.tsv",
            sourceName: "Custom TSV",
            existingEntries: existing,
            options: GlossaryImportOptions(sourceLanguageCode: "en", targetLanguageCode: "zh", importLimit: 1)
        )
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
        let result = try GlossaryImportParser().parse(
            data: Data(xml.utf8),
            fileName: "terms.tbx",
            sourceName: "TBX",
            existingEntries: [],
            options: GlossaryImportOptions(sourceLanguageCode: "en", targetLanguageCode: "zh-CN", importLimit: 500)
        )
        #expect(result.added == 1)
        #expect(result.entries[0].sourceTerm == "screen recording")
        #expect(result.entries[0].targetTerm == "屏幕录制")
    }

    @Test func urlValidatorRejectsHttpAndAcceptsHttps() {
        #expect(GlossaryImportURLValidator.remoteURL(from: "http://example.com/terms.tsv") == nil)
        #expect(GlossaryImportURLValidator.remoteURL(from: "https://example.com/terms.tsv")?.scheme == "https")
    }
}

struct GlossaryImportServiceTests {
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
}
