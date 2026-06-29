import Foundation
import Testing
@testable import LiveBuddy

struct GlossaryImportTests {
    @Test func importProgressClampsKnownFractionAndAllowsIndeterminate() {
        #expect(GlossaryImportProgress(fractionCompleted: -0.5).fractionCompleted == 0)
        #expect(GlossaryImportProgress(fractionCompleted: 1.5).fractionCompleted == 1)
        #expect(GlossaryImportProgress.indeterminate.fractionCompleted == nil)
        #expect(GlossaryImportProgress(fractionCompleted: 1).switchingToProcessing().fractionCompleted == nil)
    }

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

    @Test func zipImportSkipsHiddenAndUnsupportedFiles() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("GlossaryImportZipTests-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let termsURL = root.appendingPathComponent("terms.tsv")
        let hiddenDirectory = root.appendingPathComponent("__MACOSX", isDirectory: true)
        let unsupportedURL = root.appendingPathComponent("notes.md")
        try FileManager.default.createDirectory(at: hiddenDirectory, withIntermediateDirectories: true)
        try "Codex\tCodex\n".write(to: termsURL, atomically: true, encoding: .utf8)
        try "hidden\t隐藏\n".write(to: hiddenDirectory.appendingPathComponent("._terms.tsv"), atomically: true, encoding: .utf8)
        try "not glossary".write(to: unsupportedURL, atomically: true, encoding: .utf8)

        let archiveURL = root.appendingPathComponent("terms.zip")
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/zip")
        process.currentDirectoryURL = root
        process.arguments = ["-qr", archiveURL.path, "terms.tsv", "__MACOSX", "notes.md"]
        try process.run()
        process.waitUntilExit()
        #expect(process.terminationStatus == 0)

        let result = try GlossaryImportParser().parse(
            fileURL: archiveURL,
            sourceName: "ZIP",
            existingEntries: [],
            options: .default
        )

        #expect(result.added == 1)
        #expect(result.entries[0].sourceTerm == "Codex")
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
