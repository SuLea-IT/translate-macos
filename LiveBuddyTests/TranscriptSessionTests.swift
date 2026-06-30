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
}
