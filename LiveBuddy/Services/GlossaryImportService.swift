import Foundation

final class GlossaryImportService {
    private let cacheDirectory: URL
    private let session: URLSession
    private let parser: GlossaryImportParser
    private let maxDownloadBytes: Int

    init(
        cacheDirectory: URL? = nil,
        session: URLSession = .shared,
        parser: GlossaryImportParser = GlossaryImportParser(),
        maxDownloadBytes: Int = 25 * 1024 * 1024
    ) {
        if let cacheDirectory {
            self.cacheDirectory = cacheDirectory
        } else {
            let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
                .appendingPathComponent("LiveBuddy", isDirectory: true)
            self.cacheDirectory = support.appendingPathComponent("GlossaryImports", isDirectory: true)
        }
        self.session = session
        self.parser = parser
        self.maxDownloadBytes = maxDownloadBytes
    }

    func cacheURL(for url: URL, sourceID: String) -> URL {
        let sanitizedSource = sanitizedFileComponent(sourceID)
        let hash = stableHash(url.absoluteString)
        let ext = sanitizedExtension(from: url)
        return cacheDirectory.appendingPathComponent("\(sanitizedSource)-\(hash).\(ext)")
    }

    func importRemote(
        url: URL,
        sourceName: String,
        existingEntries: [GlossaryEntry],
        options: GlossaryImportOptions
    ) async throws -> GlossaryImportResult {
        guard url.scheme?.lowercased() == "https" else {
            throw GlossaryImportError.unsupportedURL
        }
        try FileManager.default.createDirectory(at: cacheDirectory, withIntermediateDirectories: true)

        let (temporaryURL, response): (URL, URLResponse)
        do {
            (temporaryURL, response) = try await session.download(from: url)
        } catch {
            throw GlossaryImportError.downloadFailed(error.localizedDescription)
        }

        if let httpResponse = response as? HTTPURLResponse, !(200..<300).contains(httpResponse.statusCode) {
            throw GlossaryImportError.downloadFailed("HTTP \(httpResponse.statusCode)")
        }

        try enforceFileSizeLimit(temporaryURL)
        let destination = cacheURL(for: url, sourceID: sourceName)
        if FileManager.default.fileExists(atPath: destination.path) {
            try FileManager.default.removeItem(at: destination)
        }
        try FileManager.default.moveItem(at: temporaryURL, to: destination)
        let result = try parser.parse(fileURL: destination, sourceName: sourceName, existingEntries: existingEntries, options: options)
        if result.entries.isEmpty {
            throw GlossaryImportError.emptyImport
        }
        return result
    }

    func importLocalFile(
        url: URL,
        sourceName: String,
        existingEntries: [GlossaryEntry],
        options: GlossaryImportOptions
    ) throws -> GlossaryImportResult {
        try enforceFileSizeLimit(url)
        let result = try parser.parse(fileURL: url, sourceName: sourceName, existingEntries: existingEntries, options: options)
        if result.entries.isEmpty {
            throw GlossaryImportError.emptyImport
        }
        return result
    }

    private func enforceFileSizeLimit(_ url: URL) throws {
        let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
        let size = (attributes[.size] as? NSNumber)?.intValue ?? 0
        if size > maxDownloadBytes {
            throw GlossaryImportError.fileTooLarge
        }
    }

    private func sanitizedFileComponent(_ value: String) -> String {
        let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "-_"))
        let scalars = value.unicodeScalars.map { scalar -> Character in
            allowed.contains(scalar) ? Character(scalar) : "-"
        }
        let compacted = String(scalars).split(separator: "-").joined(separator: "-")
        return compacted.isEmpty ? "Glossary" : compacted
    }

    private func sanitizedExtension(from url: URL) -> String {
        let ext = url.pathExtension.lowercased()
        guard ["csv", "tsv", "txt", "tbx", "xml", "zip"].contains(ext) else { return "dat" }
        return ext
    }

    private func stableHash(_ value: String) -> String {
        var hash: UInt64 = 14_695_981_039_346_656_037
        for byte in value.utf8 {
            hash ^= UInt64(byte)
            hash &*= 1_099_511_628_211
        }
        return String(hash, radix: 16)
    }
}
