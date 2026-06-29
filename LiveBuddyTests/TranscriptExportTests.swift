import Foundation
import Testing
@testable import LiveBuddy

struct TranscriptExportTests {
    private let start = Date(timeIntervalSince1970: 1_700_000_000)

    private func sampleSession() -> TranscriptSession {
        TranscriptSession(
            id: UUID(uuidString: "00000000-0000-0000-0000-000000000001")!,
            startedAt: start,
            endedAt: start.addingTimeInterval(10),
            targetLanguage: "English",
            audioSource: "Screen audio",
            lines: [
                TranscriptLine(
                    id: UUID(uuidString: "00000000-0000-0000-0000-000000000011")!,
                    text: "  Hello   world  ",
                    originalText: "  你好   世界  ",
                    languageCode: "en",
                    timestamp: start.addingTimeInterval(0)
                ),
                TranscriptLine(
                    id: UUID(uuidString: "00000000-0000-0000-0000-000000000012")!,
                    text: "Second line",
                    originalText: "第二句",
                    languageCode: "en",
                    timestamp: start.addingTimeInterval(2)
                )
            ]
        )
    }

    @Test func cuesUseNextStartAsEndAndPreserveBilingualLineBreaks() {
        let cues = TranscriptExporter().cues(for: sampleSession(), mode: .both)

        #expect(cues.count == 2)
        #expect(cues[0].start == 0)
        #expect(cues[0].end == 2)
        #expect(cues[0].text == "你好 世界\nHello world")
    }

    @Test func srtUsesCommaMillisecondsAndSequentialIndexes() {
        let srt = TranscriptExporter().export(session: sampleSession(), mode: .translated, format: .srt)

        #expect(srt.contains("1\n00:00:00,000 --> 00:00:02,000\nHello world"))
        #expect(srt.contains("2\n00:00:02,000 -->"))
    }

    @Test func webVTTUsesHeaderAndDotMilliseconds() {
        let vtt = TranscriptExporter().export(session: sampleSession(), mode: .translated, format: .webVTT)

        #expect(vtt.hasPrefix("WEBVTT\n\n"))
        #expect(vtt.contains("00:00:00.000 --> 00:00:02.000\nHello world"))
    }

    @Test func markdownIncludesMetadataAndSelectedText() {
        let markdown = TranscriptExporter().export(session: sampleSession(), mode: .original, format: .markdown)

        #expect(markdown.contains("# Transcript"))
        #expect(markdown.contains("- Source: Screen audio"))
        #expect(markdown.contains("你好 世界"))
        #expect(markdown.contains("第二句"))
    }

    @Test func plainTextDoesNotIncludeSubtitleTiming() {
        let text = TranscriptExporter().export(session: sampleSession(), mode: .translated, format: .plainText)

        #expect(text.contains("Hello world"))
        #expect(text.contains("Second line"))
        #expect(text.contains("-->" ) == false)
        #expect(text.contains("WEBVTT") == false)
    }

    @Test func defaultFileNameIsExtensionSafe() {
        let session = TranscriptSession(
            id: UUID(uuidString: "00000000-0000-0000-0000-000000000002")!,
            startedAt: start,
            endedAt: start.addingTimeInterval(1),
            targetLanguage: "English / Japanese",
            audioSource: "Screen:Audio",
            lines: []
        )

        let fileName = TranscriptExporter().defaultFileName(session: session, mode: .both, format: .webVTT)

        #expect(fileName.hasSuffix(".vtt"))
        #expect(fileName.contains("/") == false)
        #expect(fileName.contains(":") == false)
        #expect(fileName.contains("both"))
    }
}
