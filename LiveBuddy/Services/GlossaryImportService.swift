import Foundation

final class GlossaryImportService: @unchecked Sendable {
    private let cacheDirectory: URL
    private let session: URLSession
    private let parser: GlossaryImportParser
    private let maxDownloadBytes: Int

    init(
        cacheDirectory: URL? = nil,
        session: URLSession = .shared,
        parser: GlossaryImportParser = GlossaryImportParser(),
        maxDownloadBytes: Int = 250 * 1024 * 1024
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
        options: GlossaryImportOptions,
        progress: ((GlossaryImportProgress) async -> Void)? = nil
    ) async throws -> GlossaryImportResult {
        guard url.scheme?.lowercased() == "https" else {
            throw GlossaryImportError.unsupportedURL
        }
        try FileManager.default.createDirectory(at: cacheDirectory, withIntermediateDirectories: true)

        let (temporaryURL, response) = try await download(url: url, progress: progress)

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

    private func download(
        url: URL,
        progress: ((GlossaryImportProgress) async -> Void)?
    ) async throws -> (URL, URLResponse) {
        do {
            let (bytes, response) = try await session.bytes(from: url)
            if let httpResponse = response as? HTTPURLResponse, !(200..<300).contains(httpResponse.statusCode) {
                return (FileManager.default.temporaryDirectory, httpResponse)
            }

            let temporaryURL = cacheDirectory.appendingPathComponent("download-\(UUID().uuidString).tmp")
            FileManager.default.createFile(atPath: temporaryURL.path, contents: nil)
            let handle = try FileHandle(forWritingTo: temporaryURL)
            defer {
                try? handle.close()
            }

            let expectedBytes = response.expectedContentLength
            var downloadedBytes: Int64 = 0
            var lastReportedBytes: Int64 = 0
            var buffer = Data()
            buffer.reserveCapacity(64 * 1024)
            await progress?(.indeterminate)

            for try await byte in bytes {
                buffer.append(byte)
                downloadedBytes += 1

                if downloadedBytes > maxDownloadBytes {
                    try? handle.close()
                    try? FileManager.default.removeItem(at: temporaryURL)
                    throw GlossaryImportError.fileTooLarge
                }

                if buffer.count >= 64 * 1024 {
                    try handle.write(contentsOf: buffer)
                    buffer.removeAll(keepingCapacity: true)
                    if shouldReportProgress(downloadedBytes: downloadedBytes, expectedBytes: expectedBytes, lastReportedBytes: lastReportedBytes) {
                        await reportProgress(downloadedBytes: downloadedBytes, expectedBytes: expectedBytes, progress: progress)
                        lastReportedBytes = downloadedBytes
                    }
                }
            }

            if !buffer.isEmpty {
                try handle.write(contentsOf: buffer)
            }
            await reportProgress(downloadedBytes: downloadedBytes, expectedBytes: expectedBytes, progress: progress)
            return (temporaryURL, response)
        } catch let error as GlossaryImportError {
            throw error
        } catch {
            throw GlossaryImportError.downloadFailed(error.localizedDescription)
        }
    }

    private func shouldReportProgress(downloadedBytes: Int64, expectedBytes: Int64, lastReportedBytes: Int64) -> Bool {
        guard expectedBytes > 0 else { return false }
        let step = max(Int64(64 * 1024), expectedBytes / 100)
        return downloadedBytes - lastReportedBytes >= step || downloadedBytes >= expectedBytes
    }

    private func reportProgress(
        downloadedBytes: Int64,
        expectedBytes: Int64,
        progress: ((GlossaryImportProgress) async -> Void)?
    ) async {
        guard expectedBytes > 0 else {
            await progress?(.indeterminate)
            return
        }
        await progress?(GlossaryImportProgress(fractionCompleted: Double(downloadedBytes) / Double(expectedBytes)))
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
