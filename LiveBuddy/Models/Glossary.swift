import Foundation

struct GlossaryEntry: Identifiable, Codable, Equatable, Hashable {
    var id: UUID
    var sourceTerm: String
    var targetTerm: String
    var note: String
    var isEnabled: Bool

    init(id: UUID = UUID(), sourceTerm: String, targetTerm: String = "", note: String = "", isEnabled: Bool = true) {
        self.id = id
        self.sourceTerm = sourceTerm
        self.targetTerm = targetTerm
        self.note = note
        self.isEnabled = isEnabled
    }
}

struct GlossaryPromptBuilder {
    var maxEntries = 80

    func instruction(for entries: [GlossaryEntry]) -> String {
        var seen = Set<String>()
        let rules = entries.compactMap { entry -> (source: String, target: String)? in
            guard entry.isEnabled else { return nil }
            let source = normalized(entry.sourceTerm)
            guard !source.isEmpty else { return nil }
            let key = source.lowercased()
            guard !seen.contains(key) else { return nil }
            seen.insert(key)
            let target = normalized(entry.targetTerm)
            return (source, target.isEmpty ? source : target)
        }
        .sorted { lhs, rhs in
            if lhs.source.count == rhs.source.count {
                return lhs.source.localizedCaseInsensitiveCompare(rhs.source) == .orderedAscending
            }
            return lhs.source.count > rhs.source.count
        }
        .prefix(maxEntries)

        guard !rules.isEmpty else { return "" }
        let body = rules.map { "- \($0.source) => \($0.target)" }.joined(separator: "\n")
        return """
        Terminology rules:
        - Keep source terms exactly when target is identical.
        - Use these preferred terms when they appear in speech:
        \(body)
        """
    }

    private func normalized(_ value: String) -> String {
        value.split { character in
            character == " " || character == "\t" || character == "\n" || character == "\r"
        }
        .joined(separator: " ")
        .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

struct GlossaryEntryEditor {
    func add(sourceTerm: String, targetTerm: String, to entries: [GlossaryEntry]) -> [GlossaryEntry] {
        let source = normalized(sourceTerm)
        guard !source.isEmpty else { return entries }
        let target = normalized(targetTerm)
        return entries + [GlossaryEntry(sourceTerm: source, targetTerm: target)]
    }

    func delete(_ entry: GlossaryEntry, from entries: [GlossaryEntry]) -> [GlossaryEntry] {
        entries.filter { $0.id != entry.id }
    }

    private func normalized(_ value: String) -> String {
        value.split { character in
            character == " " || character == "\t" || character == "\n" || character == "\r"
        }
        .joined(separator: " ")
        .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
