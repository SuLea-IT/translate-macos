import Foundation
import Testing
@testable import LiveBuddy

struct LogExportTests {
    @Test func exporterFormatsRuntimeLogsWithLevelsAndTimestamps() {
        let entries = [
            LogEntry(
                id: UUID(uuidString: "00000000-0000-0000-0000-000000000001")!,
                timestamp: Date(timeIntervalSince1970: 1_700_000_000),
                message: "App ready",
                level: .info
            ),
            LogEntry(
                id: UUID(uuidString: "00000000-0000-0000-0000-000000000002")!,
                timestamp: Date(timeIntervalSince1970: 1_700_000_060),
                message: "Network failed",
                level: .error
            )
        ]

        let text = LogExporter().export(entries: entries)

        #expect(text.hasPrefix("# Runtime Logs\n"))
        #expect(text.contains("INFO App ready"))
        #expect(text.contains("ERROR Network failed"))
        #expect(text.hasSuffix("\n"))
    }

    @Test func exporterUsesHelpfulMessageForEmptyLogs() {
        let text = LogExporter().export(entries: [])

        #expect(text.contains("No log entries."))
    }

    @Test func exporterDefaultFileNameIsExtensionSafe() {
        let fileName = LogExporter().defaultFileName(date: Date(timeIntervalSince1970: 1_700_000_000))

        #expect(fileName.hasPrefix("LiveBuddy-Logs-"))
        #expect(fileName.hasSuffix(".txt"))
        #expect(fileName.contains("/") == false)
        #expect(fileName.contains(":") == false)
    }
}
