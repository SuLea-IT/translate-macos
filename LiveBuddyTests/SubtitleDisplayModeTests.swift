import Testing
@testable import LiveBuddy

struct SubtitleDisplayModeTests {
    @Test func translatedModeKeepsCurrentSingleTrackText() {
        let lines = SubtitleDisplayTextBuilder.lines(
            items: [SubtitleDisplayItem(original: "Hello", translated: "你好")],
            translatedDraft: "",
            originalDraft: "",
            mode: .translated
        )

        #expect(SubtitleDisplayTextBuilder.plainText(from: lines) == "你好")
    }

    @Test func bilingualModePlacesOriginalAboveTranslation() {
        let lines = SubtitleDisplayTextBuilder.lines(
            items: [SubtitleDisplayItem(original: "Hello", translated: "你好")],
            translatedDraft: "",
            originalDraft: "",
            mode: .bilingual
        )

        #expect(lines.map(\.role) == [.original, .translated])
        #expect(SubtitleDisplayTextBuilder.plainText(from: lines) == "Hello\n你好")
    }

    @Test func originalModeFallsBackToTranslationWhenOriginalMissing() {
        let lines = SubtitleDisplayTextBuilder.lines(
            items: [SubtitleDisplayItem(original: nil, translated: "你好")],
            translatedDraft: "",
            originalDraft: "",
            mode: .original
        )

        #expect(SubtitleDisplayTextBuilder.plainText(from: lines) == "你好")
    }
}
