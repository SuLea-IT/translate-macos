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

    @Test func exporterUsesSelectedInterfaceLanguageForTitleAndEmptyState() {
        let emptyText = LogExporter().export(entries: [], language: .simplifiedChinese)

        #expect(emptyText.hasPrefix("# 运行日志\n"))
        #expect(emptyText.contains("暂无日志。"))
        #expect(emptyText.contains("# Runtime Logs") == false)
        #expect(emptyText.contains("No log entries.") == false)

        let text = LogExporter().export(
            entries: [
                LogEntry(
                    timestamp: Date(timeIntervalSince1970: 1_700_000_000),
                    message: "应用已就绪",
                    level: .info
                )
            ],
            language: .simplifiedChinese
        )

        #expect(text.hasPrefix("# 运行日志\n"))
        #expect(text.contains("INFO 应用已就绪"))
        #expect(text.contains("# Runtime Logs") == false)
    }

    @Test func exporterDefaultFileNameIsExtensionSafe() {
        let fileName = LogExporter().defaultFileName(date: Date(timeIntervalSince1970: 1_700_000_000))

        #expect(fileName.hasPrefix("LiveBuddy-Logs-"))
        #expect(fileName.hasSuffix(".txt"))
        #expect(fileName.contains("/") == false)
        #expect(fileName.contains(":") == false)
    }
}
