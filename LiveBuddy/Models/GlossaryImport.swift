import Foundation

struct GlossaryImportSource: Identifiable, Equatable {
    enum Kind: Equatable {
        case builtIn(URL)
        case customURL
        case localFile
    }

    var id: String
    var displayName: String
    var detail: String
    var kind: Kind

    static let microsoftTerminologyURL = URL(string: "https://download.microsoft.com/download/b/2/d/b2db7a7c-8d33-47f3-b2c1-ee5e6445cf45/MicrosoftTermCollection.zip")!

    static let microsoftTerminology = GlossaryImportSource(
        id: "microsoft-terminology",
        displayName: "Microsoft Terminology",
        detail: "Download Microsoft software terminology package from Microsoft Download Center.",
        kind: .builtIn(microsoftTerminologyURL)
    )

    static let iateExport = GlossaryImportSource(
        id: "iate-export",
        displayName: "IATE export / custom link",
        detail: "Import a CSV, TBX, XML, TSV, TXT, or ZIP export link.",
        kind: .customURL
    )

    static let customLink = GlossaryImportSource(
        id: "custom-link",
        displayName: "Custom link",
        detail: "Import a glossary from a user-provided HTTPS URL.",
        kind: .customURL
    )

    static let availableSources: [GlossaryImportSource] = [
        .microsoftTerminology,
        .iateExport,
        .customLink
    ]
}

struct GlossaryImportOptions: Equatable {
    var sourceLanguageCode: String
    var targetLanguageCode: String
    var importLimit: Int

    static let `default` = GlossaryImportOptions(sourceLanguageCode: "en", targetLanguageCode: "zh-CN", importLimit: 500)

    var sanitizedImportLimit: Int {
        min(max(importLimit, 1), 2_000)
    }
}

struct GlossaryImportResult: Equatable {
    var sourceName: String
    var added: Int
    var skippedEmpty: Int
    var skippedDuplicate: Int
    var skippedUnsupported: Int
    var totalParsed: Int
    var entries: [GlossaryEntry]

    static func empty(sourceName: String) -> GlossaryImportResult {
        GlossaryImportResult(
            sourceName: sourceName,
            added: 0,
            skippedEmpty: 0,
            skippedDuplicate: 0,
            skippedUnsupported: 0,
            totalParsed: 0,
            entries: []
        )
    }
}

struct GlossaryImportProgress: Equatable {
    var fractionCompleted: Double?

    static let indeterminate = GlossaryImportProgress(fractionCompleted: nil)

    init(fractionCompleted: Double?) {
        if let fractionCompleted {
            self.fractionCompleted = min(max(fractionCompleted, 0), 1)
        } else {
            self.fractionCompleted = nil
        }
    }
}

enum GlossaryImportError: LocalizedError, Equatable {
    case unsupportedURL
    case unsupportedFormat(String)
    case emptyImport
    case fileTooLarge
    case downloadFailed(String)
    case parseFailed(String)

    var errorDescription: String? {
        switch self {
        case .unsupportedURL:
            return "Only HTTPS glossary links are supported."
        case .unsupportedFormat(let fileName):
            return "Unsupported glossary format: \(fileName)"
        case .emptyImport:
            return "No glossary terms were found."
        case .fileTooLarge:
            return "The glossary file is too large."
        case .downloadFailed(let message):
            return "Glossary download failed: \(message)"
        case .parseFailed(let message):
            return "Glossary import failed: \(message)"
        }
    }
}

struct GlossaryImportURLValidator {
    static func remoteURL(from value: String) -> URL? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, let url = URL(string: trimmed) else { return nil }
        guard url.scheme?.lowercased() == "https" else { return nil }
        guard url.host?.isEmpty == false else { return nil }
        return url
    }
}

struct GlossaryImportMerger {
    func merge(existing: [GlossaryEntry], imported: [GlossaryEntry]) -> [GlossaryEntry] {
        var seen = Set(existing.map { key(for: $0.sourceTerm) })
        var merged = existing
        for entry in imported {
            let source = normalized(entry.sourceTerm)
            guard !source.isEmpty else { continue }
            let key = key(for: source)
            guard !seen.contains(key) else { continue }
            seen.insert(key)
            merged.append(entry)
        }
        return merged
    }

    private func key(for value: String) -> String {
        normalized(value).lowercased()
    }

    private func normalized(_ value: String) -> String {
        GlossaryImportNormalizer.normalized(value)
    }
}

struct GlossaryImportParser {
    private let maxDataBytes: Int

    init(maxDataBytes: Int = 25 * 1024 * 1024) {
        self.maxDataBytes = maxDataBytes
    }

    func parse(
        data: Data,
        fileName: String,
        sourceName: String,
        existingEntries: [GlossaryEntry],
        options: GlossaryImportOptions
    ) throws -> GlossaryImportResult {
        guard data.count <= maxDataBytes else { throw GlossaryImportError.fileTooLarge }
        let ext = URL(fileURLWithPath: fileName).pathExtension.lowercased()
        let candidates: [GlossaryImportCandidate]
        switch ext {
        case "tsv", "txt":
            candidates = parseTSV(data: data)
        case "csv":
            candidates = parseCSV(data: data)
        case "tbx", "xml":
            candidates = try parseTBX(data: data, options: options)
        case "zip":
            throw GlossaryImportError.unsupportedFormat(fileName)
        default:
            if looksLikeXML(data) {
                candidates = try parseTBX(data: data, options: options)
            } else if looksLikeCSV(data) {
                candidates = parseCSV(data: data)
            } else {
                throw GlossaryImportError.unsupportedFormat(fileName)
            }
        }
        return buildResult(
            from: candidates,
            sourceName: sourceName,
            existingEntries: existingEntries,
            options: options
        )
    }

    func parse(
        fileURL: URL,
        sourceName: String,
        existingEntries: [GlossaryEntry],
        options: GlossaryImportOptions
    ) throws -> GlossaryImportResult {
        let fileName = fileURL.lastPathComponent
        if fileURL.pathExtension.lowercased() == "zip" {
            return try parseZIP(fileURL: fileURL, sourceName: sourceName, existingEntries: existingEntries, options: options)
        }
        let data = try Data(contentsOf: fileURL)
        return try parse(data: data, fileName: fileName, sourceName: sourceName, existingEntries: existingEntries, options: options)
    }

    private func parseTSV(data: Data) -> [GlossaryImportCandidate] {
        let text = String(decoding: data, as: UTF8.self)
        return text
            .split(whereSeparator: \.isNewline)
            .map(String.init)
            .compactMap { line in
                let columns = line.components(separatedBy: "\t")
                guard columns.count >= 2 else {
                    return GlossaryImportCandidate(source: line, target: "", note: "", unsupported: true)
                }
                return GlossaryImportCandidate(
                    source: columns[0],
                    target: columns[1],
                    note: columns.dropFirst(2).joined(separator: " "),
                    unsupported: false
                )
            }
    }

    private func parseCSV(data: Data) -> [GlossaryImportCandidate] {
        let text = String(decoding: data, as: UTF8.self)
        let rows = CSVRowParser().parse(text)
        guard !rows.isEmpty else { return [] }

        let first = rows[0].map { $0.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() }
        let sourceHeaders = ["source", "sourceterm", "source term", "term", "source_term"]
        let targetHeaders = ["target", "targetterm", "target term", "translation", "preferred translation", "target_term"]
        let noteHeaders = ["note", "comment", "description"]
        let sourceIndex = first.firstIndex { sourceHeaders.contains($0) }
        let targetIndex = first.firstIndex { targetHeaders.contains($0) }
        let noteIndex = first.firstIndex { noteHeaders.contains($0) }
        let hasHeader = sourceIndex != nil && targetIndex != nil
        let dataRows = hasHeader ? rows.dropFirst() : rows[...]

        return dataRows.map { row in
            let sourcePosition = sourceIndex ?? 0
            let targetPosition = targetIndex ?? 1
            guard row.indices.contains(sourcePosition), row.indices.contains(targetPosition) else {
                return GlossaryImportCandidate(source: "", target: "", note: "", unsupported: true)
            }
            let note: String
            if let noteIndex, row.indices.contains(noteIndex) {
                note = row[noteIndex]
            } else if !hasHeader, row.count > 2 {
                note = row.dropFirst(2).joined(separator: " ")
            } else {
                note = ""
            }
            return GlossaryImportCandidate(source: row[sourcePosition], target: row[targetPosition], note: note, unsupported: false)
        }
    }

    private func parseTBX(data: Data, options: GlossaryImportOptions) throws -> [GlossaryImportCandidate] {
        let delegate = TBXTermParserDelegate(options: options)
        let parser = XMLParser(data: data)
        parser.delegate = delegate
        guard parser.parse() else {
            throw GlossaryImportError.parseFailed(parser.parserError?.localizedDescription ?? "Invalid XML")
        }
        return delegate.candidates
    }

    private func parseZIP(
        fileURL: URL,
        sourceName: String,
        existingEntries: [GlossaryEntry],
        options: GlossaryImportOptions
    ) throws -> GlossaryImportResult {
        let archive = ZIPGlossaryArchive(fileURL: fileURL, maxEntryBytes: maxDataBytes)
        let entries = try archive.supportedEntries()
        var aggregate = GlossaryImportResult.empty(sourceName: sourceName)
        var existing = existingEntries

        for entry in entries {
            guard aggregate.added < options.sanitizedImportLimit else { break }
            let remaining = options.sanitizedImportLimit - aggregate.added
            let data = try archive.data(for: entry)
            let partial = try parse(
                data: data,
                fileName: entry,
                sourceName: sourceName,
                existingEntries: existing,
                options: GlossaryImportOptions(
                    sourceLanguageCode: options.sourceLanguageCode,
                    targetLanguageCode: options.targetLanguageCode,
                    importLimit: remaining
                )
            )
            aggregate.added += partial.added
            aggregate.skippedEmpty += partial.skippedEmpty
            aggregate.skippedDuplicate += partial.skippedDuplicate
            aggregate.skippedUnsupported += partial.skippedUnsupported
            aggregate.totalParsed += partial.totalParsed
            aggregate.entries.append(contentsOf: partial.entries)
            existing.append(contentsOf: partial.entries)
        }

        if entries.isEmpty {
            aggregate.skippedUnsupported += 1
        }
        return aggregate
    }

    private func buildResult(
        from candidates: [GlossaryImportCandidate],
        sourceName: String,
        existingEntries: [GlossaryEntry],
        options: GlossaryImportOptions
    ) -> GlossaryImportResult {
        var result = GlossaryImportResult.empty(sourceName: sourceName)
        var seen = Set(existingEntries.map { GlossaryImportNormalizer.key($0.sourceTerm) })
        let limit = options.sanitizedImportLimit

        for candidate in candidates {
            result.totalParsed += 1
            if candidate.unsupported {
                result.skippedUnsupported += 1
                continue
            }

            let source = GlossaryImportNormalizer.normalized(candidate.source)
            let target = GlossaryImportNormalizer.normalized(candidate.target)
            let note = GlossaryImportNormalizer.normalized(candidate.note)
            guard !source.isEmpty else {
                result.skippedEmpty += 1
                continue
            }

            let key = GlossaryImportNormalizer.key(source)
            guard !seen.contains(key) else {
                result.skippedDuplicate += 1
                continue
            }
            guard result.entries.count < limit else { break }

            seen.insert(key)
            let importNote = note.isEmpty ? "Imported from \(sourceName)" : "Imported from \(sourceName) — \(note)"
            result.entries.append(GlossaryEntry(sourceTerm: source, targetTerm: target, note: importNote))
        }

        result.added = result.entries.count
        return result
    }

    private func looksLikeXML(_ data: Data) -> Bool {
        let prefix = String(decoding: data.prefix(256), as: UTF8.self).trimmingCharacters(in: .whitespacesAndNewlines)
        return prefix.hasPrefix("<")
    }

    private func looksLikeCSV(_ data: Data) -> Bool {
        let prefix = String(decoding: data.prefix(512), as: UTF8.self)
        return prefix.contains(",") || prefix.contains("\t")
    }
}

private struct GlossaryImportCandidate {
    var source: String
    var target: String
    var note: String
    var unsupported: Bool
}

private enum GlossaryImportNormalizer {
    static func normalized(_ value: String) -> String {
        value
            .split { character in
                character == " " || character == "\t" || character == "\n" || character == "\r"
            }
            .joined(separator: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    static func key(_ value: String) -> String {
        normalized(value).lowercased()
    }
}

private struct CSVRowParser {
    func parse(_ text: String) -> [[String]] {
        var rows: [[String]] = []
        var row: [String] = []
        var field = ""
        var isQuoted = false
        var iterator = text.makeIterator()

        while let character = iterator.next() {
            if isQuoted {
                if character == "\"" {
                    if let next = iterator.next() {
                        if next == "\"" {
                            field.append("\"")
                        } else {
                            isQuoted = false
                            consumeUnquoted(next, field: &field, row: &row, rows: &rows)
                        }
                    } else {
                        isQuoted = false
                    }
                } else {
                    field.append(character)
                }
            } else if character == "\"" {
                isQuoted = true
            } else {
                consumeUnquoted(character, field: &field, row: &row, rows: &rows)
            }
        }

        if !field.isEmpty || !row.isEmpty {
            row.append(field)
            rows.append(row)
        }
        return rows.filter { row in
            row.contains { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        }
    }

    private func consumeUnquoted(_ character: Character, field: inout String, row: inout [String], rows: inout [[String]]) {
        switch character {
        case ",":
            row.append(field)
            field = ""
        case "\n":
            row.append(field)
            rows.append(row)
            row = []
            field = ""
        case "\r":
            break
        default:
            field.append(character)
        }
    }
}

private final class TBXTermParserDelegate: NSObject, XMLParserDelegate {
    let options: GlossaryImportOptions
    private(set) var candidates: [GlossaryImportCandidate] = []
    private var currentConcept: [String: [String]] = [:]
    private var currentLanguage: String?
    private var isInsideTerm = false
    private var termBuffer = ""

    init(options: GlossaryImportOptions) {
        self.options = options
    }

    func parser(_ parser: XMLParser, didStartElement elementName: String, namespaceURI: String?, qualifiedName qName: String?, attributes attributeDict: [String : String] = [:]) {
        let name = elementName.lowercased()
        if name == "termentry" {
            currentConcept = [:]
        } else if name == "langset" {
            currentLanguage = languageCode(from: attributeDict)
        } else if name == "term" {
            isInsideTerm = true
            termBuffer = ""
        }
    }

    func parser(_ parser: XMLParser, foundCharacters string: String) {
        if isInsideTerm {
            termBuffer.append(string)
        }
    }

    func parser(_ parser: XMLParser, didEndElement elementName: String, namespaceURI: String?, qualifiedName qName: String?) {
        let name = elementName.lowercased()
        if name == "term" {
            isInsideTerm = false
            let term = GlossaryImportNormalizer.normalized(termBuffer)
            if !term.isEmpty, let language = currentLanguage {
                currentConcept[language, default: []].append(term)
            }
            termBuffer = ""
        } else if name == "langset" {
            currentLanguage = nil
        } else if name == "termentry" {
            appendCandidatesForCurrentConcept()
            currentConcept = [:]
        }
    }

    private func languageCode(from attributes: [String: String]) -> String? {
        let possibleKeys = ["xml:lang", "lang", "language", "locale"]
        for key in possibleKeys {
            if let value = attributes[key], !value.isEmpty { return value }
        }
        if let match = attributes.first(where: { $0.key.lowercased().hasSuffix("lang") })?.value, !match.isEmpty {
            return match
        }
        return nil
    }

    private func appendCandidatesForCurrentConcept() {
        guard !currentConcept.isEmpty else { return }
        let sourceTerms = terms(matching: options.sourceLanguageCode) ?? fallbackTerms(at: 0)
        let targetTerms = terms(matching: options.targetLanguageCode) ?? fallbackTerms(at: 1)
        guard let sourceTerms, let targetTerms else { return }

        for source in sourceTerms {
            for target in targetTerms {
                guard source != target else { continue }
                candidates.append(GlossaryImportCandidate(source: source, target: target, note: "TBX", unsupported: false))
            }
        }
    }

    private func terms(matching desiredCode: String) -> [String]? {
        let desired = desiredCode.lowercased()
        if let exact = currentConcept.first(where: { $0.key.lowercased() == desired })?.value {
            return exact
        }
        let desiredBase = desired.split(separator: "-").first.map(String.init) ?? desired
        return currentConcept.first { key, _ in
            let lower = key.lowercased()
            return lower == desiredBase || lower.hasPrefix(desiredBase + "-")
        }?.value
    }

    private func fallbackTerms(at index: Int) -> [String]? {
        let keys = currentConcept.keys.sorted()
        guard keys.indices.contains(index) else { return nil }
        return currentConcept[keys[index]]
    }
}

private struct ZIPGlossaryArchive {
    let fileURL: URL
    let maxEntryBytes: Int

    func supportedEntries() throws -> [String] {
        let output = try runUnzip(arguments: ["-l", fileURL.path])
        return output
            .split(whereSeparator: \.isNewline)
            .compactMap { line -> (name: String, size: Int)? in
                let parts = line.split(maxSplits: 3, omittingEmptySubsequences: true, whereSeparator: \.isWhitespace)
                guard parts.count == 4, let size = Int(parts[0]) else { return nil }
                return (String(parts[3]).trimmingCharacters(in: .whitespacesAndNewlines), size)
            }
            .filter { entry, size in
                guard size <= maxEntryBytes else { return false }
                guard !entry.hasSuffix("/") else { return false }
                guard !entry.hasPrefix("__MACOSX/"), !entry.contains("/._"), !entry.hasPrefix("._") else { return false }
                let ext = URL(fileURLWithPath: entry).pathExtension.lowercased()
                return ["csv", "tsv", "txt", "tbx", "xml"].contains(ext)
            }
            .map(\.name)
    }

    func data(for entry: String) throws -> Data {
        guard !entry.contains("../"), !entry.hasPrefix("/") else {
            throw GlossaryImportError.unsupportedFormat(entry)
        }
        let output = try runUnzip(arguments: ["-p", fileURL.path, entry])
        return Data(output.utf8)
    }

    private func runUnzip(arguments: [String]) throws -> String {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/unzip")
        process.arguments = arguments
        let pipe = Pipe()
        let errorPipe = Pipe()
        process.standardOutput = pipe
        process.standardError = errorPipe
        try process.run()
        process.waitUntilExit()
        let output = String(decoding: pipe.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self)
        if process.terminationStatus != 0 {
            let error = String(decoding: errorPipe.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self)
            throw GlossaryImportError.parseFailed(error.isEmpty ? "unzip failed" : error)
        }
        return output
    }
}
