import Foundation
import Testing
@testable import LiveBuddy

struct MeetingNotesTests {
    @Test func generatorExtractsSummaryAndKeyPoints() {
        let session = sampleSession()
        let notes = MeetingNotesGenerator().generate(from: session, mode: .translated)

        #expect(notes.summary.isEmpty == false)
        #expect(notes.summary.count <= 3)
        #expect(notes.keyPoints.count <= 5)
        #expect(notes.keyPoints.contains { $0.text.localizedCaseInsensitiveContains("launch timeline") })
    }

    @Test func actionItemDetectionSupportsEnglishAndChineseCues() {
        let session = sampleSession()
        let notes = MeetingNotesGenerator().generate(from: session, mode: .both)

        #expect(notes.actionItems.contains { $0.text.localizedCaseInsensitiveContains("please prepare") })
        #expect(notes.actionItems.contains { $0.text.contains("需要") })
    }

    @Test func timelineIsChronological() {
        let notes = MeetingNotesGenerator().generate(from: sampleSession(), mode: .translated)
        let offsets = notes.timeline.map(\.offset)

        #expect(offsets == offsets.sorted())
        #expect(notes.timeline.count <= 8)
    }

    @Test func markdownContainsExpectedSections() {
        let session = sampleSession()
        let notes = MeetingNotesGenerator().generate(from: session, mode: .translated)
        let markdown = MeetingNotesGenerator().markdown(for: notes, session: session)

        #expect(markdown.contains("# Meeting Notes"))
        #expect(markdown.contains("## Summary"))
        #expect(markdown.contains("## Key Points"))
        #expect(markdown.contains("## Action Items"))
        #expect(markdown.contains("## Timeline"))
    }

    @Test func emptyTranscriptReturnsEmptyNotes() {
        let session = TranscriptSession(
            id: UUID(uuidString: "00000000-0000-0000-0000-000000000100")!,
            startedAt: Date(timeIntervalSince1970: 0),
            endedAt: Date(timeIntervalSince1970: 60),
            targetLanguage: "English",
            audioSource: "Screen",
            lines: []
        )

        let notes = MeetingNotesGenerator().generate(from: session, mode: .translated)

        #expect(notes.summary.isEmpty)
        #expect(notes.keyPoints.isEmpty)
        #expect(notes.actionItems.isEmpty)
        #expect(notes.timeline.isEmpty)
    }

    private func sampleSession() -> TranscriptSession {
        let start = Date(timeIntervalSince1970: 1_000)
        return TranscriptSession(
            id: UUID(uuidString: "00000000-0000-0000-0000-000000000101")!,
            startedAt: start,
            endedAt: start.addingTimeInterval(600),
            targetLanguage: "English",
            audioSource: "Screen + Mic",
            lines: [
                TranscriptLine(text: "Today we reviewed the product launch timeline and translation quality risks.", originalText: "今天我们回顾了产品发布排期和翻译质量风险。", languageCode: "en", timestamp: start.addingTimeInterval(10)),
                TranscriptLine(text: "The launch timeline depends on packaging, glossary import, and meeting notes.", originalText: "发布排期取决于打包、术语导入和会议纪要。", languageCode: "en", timestamp: start.addingTimeInterval(70)),
                TranscriptLine(text: "Please prepare the release checklist before Friday.", originalText: "请在周五前准备发布检查清单。", languageCode: "en", timestamp: start.addingTimeInterval(130)),
                TranscriptLine(text: "We need to reduce API cost and add idle pause controls.", originalText: "我们需要降低 API 成本并增加空闲暂停控制。", languageCode: "en", timestamp: start.addingTimeInterval(190)),
                TranscriptLine(text: "需要安排一次用户测试来验证字幕显示。", originalText: "需要安排一次用户测试来验证字幕显示。", languageCode: "zh", timestamp: start.addingTimeInterval(260)),
                TranscriptLine(text: "The decision is to ship the free release workflow first.", originalText: "决定先发布免费发布流程。", languageCode: "en", timestamp: start.addingTimeInterval(330))
            ]
        )
    }
}
