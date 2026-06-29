import Foundation

enum SubtitleDisplayMode: String, CaseIterable, Codable, Identifiable {
    case translated
    case original
    case bilingual

    var id: String { rawValue }
}

enum SubtitleDisplayRole: String, Codable, Equatable {
    case original
    case translated
    case spacer
}

struct SubtitleDisplayLine: Identifiable, Codable, Equatable {
    let id: UUID
    let text: String
    let role: SubtitleDisplayRole

    init(id: UUID = UUID(), text: String, role: SubtitleDisplayRole) {
        self.id = id
        self.text = text
        self.role = role
    }
}

struct SubtitleDisplayItem: Equatable {
    let original: String?
    let translated: String
}

struct SubtitleDisplayTextBuilder {
    static func lines(
        items: [SubtitleDisplayItem],
        translatedDraft: String,
        originalDraft: String,
        mode: SubtitleDisplayMode
    ) -> [SubtitleDisplayLine] {
        var result: [SubtitleDisplayLine] = []
        for item in items {
            append(item: item, to: &result, mode: mode)
        }

        let translatedDraft = translatedDraft.trimmingCharacters(in: .whitespacesAndNewlines)
        let originalDraft = originalDraft.trimmingCharacters(in: .whitespacesAndNewlines)
        if !translatedDraft.isEmpty || !originalDraft.isEmpty {
            append(
                item: SubtitleDisplayItem(
                    original: originalDraft.isEmpty ? nil : originalDraft,
                    translated: translatedDraft.isEmpty ? originalDraft : translatedDraft
                ),
                to: &result,
                mode: mode
            )
        }

        return result
    }

    static func plainText(from lines: [SubtitleDisplayLine]) -> String {
        lines.map(\.text).joined(separator: "\n")
    }

    private static func append(item: SubtitleDisplayItem, to result: inout [SubtitleDisplayLine], mode: SubtitleDisplayMode) {
        let translated = item.translated.trimmingCharacters(in: .whitespacesAndNewlines)
        let original = item.original?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        guard !translated.isEmpty || !original.isEmpty else { return }

        if !result.isEmpty, mode == .bilingual {
            result.append(SubtitleDisplayLine(text: "", role: .spacer))
        }

        switch mode {
        case .translated:
            result.append(SubtitleDisplayLine(text: translated.isEmpty ? original : translated, role: .translated))
        case .original:
            result.append(SubtitleDisplayLine(text: original.isEmpty ? translated : original, role: .original))
        case .bilingual:
            if !original.isEmpty {
                result.append(SubtitleDisplayLine(text: original, role: .original))
            }
            if !translated.isEmpty {
                result.append(SubtitleDisplayLine(text: translated, role: .translated))
            }
        }
    }
}
