import Foundation
import Testing
@testable import LiveBuddy

struct TranscriptSessionTests {
    @Test func finalizedIfNeededClosesOpenSessionAtLastLineTimestamp() {
        let start = Date(timeIntervalSince1970: 1_700_000_000)
        let lastLine = start.addingTimeInterval(42)
        let session = TranscriptSession(
            id: UUID(uuidString: "00000000-0000-0000-0000-000000000021")!,
            startedAt: start,
            endedAt: nil,
            targetLanguage: "English",
            audioSource: "Screen audio",
            lines: [
                TranscriptLine(text: "First", languageCode: "en", timestamp: start.addingTimeInterval(1)),
                TranscriptLine(text: "Last", languageCode: "en", timestamp: lastLine)
            ]
        )

        let finalized = session.finalizedIfNeeded()

        #expect(finalized.endedAt == lastLine)
        #expect(finalized.lines == session.lines)
    }

    @Test func finalizedIfNeededKeepsAlreadyClosedSessionUnchanged() {
        let start = Date(timeIntervalSince1970: 1_700_000_000)
        let ended = start.addingTimeInterval(12)
        let session = TranscriptSession(
            id: UUID(uuidString: "00000000-0000-0000-0000-000000000022")!,
            startedAt: start,
            endedAt: ended,
            targetLanguage: "English",
            audioSource: "Microphone",
            lines: [
                TranscriptLine(text: "Late line", languageCode: "en", timestamp: start.addingTimeInterval(99))
            ]
        )

        let finalized = session.finalizedIfNeeded()

        #expect(finalized == session)
    }

    @Test func textForModeUsesSelectedInterfaceLanguageForCopyAndShareText() {
        let start = Date(timeIntervalSince1970: 1_700_000_000)
        let session = TranscriptSession(
            id: UUID(uuidString: "00000000-0000-0000-0000-000000000023")!,
            startedAt: start,
            endedAt: start.addingTimeInterval(10),
            targetLanguage: "English",
            audioSource: "Screen audio",
            lines: [
                TranscriptLine(
                    text: "Hello world",
                    originalText: "你好 世界",
                    languageCode: "en",
                    timestamp: start.addingTimeInterval(1)
                )
            ]
        )

        let text = session.textForMode(.both, language: .simplifiedChinese)

        #expect(text.contains("转录记录:"))
        #expect(text.contains("来源: Screen audio"))
        #expect(text.contains("目标语言: English"))
        #expect(text.contains("时长: 10s"))
        #expect(text.contains("模式: 双语"))
        #expect(text.contains("原文: 你好 世界"))
        #expect(text.contains("译文: Hello world"))
        #expect(text.contains("Transcript Session:") == false)
        #expect(text.contains("Original:") == false)
        #expect(text.contains("Translated:") == false)
    }

    @Test func activeDurationUsesSelectedInterfaceLanguage() {
        let start = Date(timeIntervalSince1970: 1_700_000_000)
        let session = TranscriptSession(
            id: UUID(uuidString: "00000000-0000-0000-0000-000000000024")!,
            startedAt: start,
            endedAt: nil,
            targetLanguage: "English",
            audioSource: "Microphone",
            lines: []
        )

        #expect(session.formattedDuration(language: .simplifiedChinese) == "进行中")
    }
}
