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
        let sourceKey = key(for: source)
        var updatedEntries: [GlossaryEntry] = []
        updatedEntries.reserveCapacity(entries.count + 1)
        var didUpdate = false

        for entry in entries {
            if key(for: entry.sourceTerm) == sourceKey {
                if didUpdate {
                    continue
                }
                var updated = entry
                updated.targetTerm = target
                updatedEntries.append(updated)
                didUpdate = true
            } else {
                updatedEntries.append(entry)
            }
        }

        if !didUpdate {
            updatedEntries.append(GlossaryEntry(sourceTerm: source, targetTerm: target))
        }
        return updatedEntries
    }

    func delete(_ entry: GlossaryEntry, from entries: [GlossaryEntry]) -> [GlossaryEntry] {
        entries.filter { $0.id != entry.id }
    }

    func deleteAll(from entries: [GlossaryEntry]) -> [GlossaryEntry] {
        []
    }

    private func key(for value: String) -> String {
        normalized(value).lowercased()
    }

    private func normalized(_ value: String) -> String {
        value.split { character in
            character == " " || character == "\t" || character == "\n" || character == "\r"
        }
        .joined(separator: " ")
        .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

struct GlossaryExporter {
    func export(entries: [GlossaryEntry]) -> String {
        let header = "source,target,note,isEnabled"
        let rows = entries.map { entry in
            [
                csvField(entry.sourceTerm),
                csvField(entry.targetTerm),
                csvField(entry.note),
                entry.isEnabled ? "true" : "false"
            ].joined(separator: ",")
        }
        return ([header] + rows).joined(separator: "\n") + "\n"
    }

    func defaultFileName(date: Date = Date()) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd-HHmm"
        return "LiveBuddy-Glossary-\(formatter.string(from: date)).csv"
    }

    private func csvField(_ value: String) -> String {
        let needsQuotes = value.contains(",")
            || value.contains("\"")
            || value.contains("\n")
            || value.contains("\r")
        let escaped = value.replacingOccurrences(of: "\"", with: "\"\"")
        return needsQuotes ? "\"\(escaped)\"" : escaped
    }
}

struct GlossaryListDisplay {
    var entries: [GlossaryEntry]
    var query: String
    var isExpanded: Bool
    var collapsedLimit: Int = 20
    let matchingEntries: [GlossaryEntry]
    let visibleEntries: [GlossaryEntry]

    init(entries: [GlossaryEntry], query: String = "", isExpanded: Bool, collapsedLimit: Int = 20) {
        self.entries = entries
        self.query = query
        self.isExpanded = isExpanded
        self.collapsedLimit = collapsedLimit
        let matches = Self.filtered(entries: entries, query: query)
        self.matchingEntries = matches
        self.visibleEntries = isExpanded ? matches : Array(matches.prefix(max(collapsedLimit, 0)))
    }

    var hiddenCount: Int {
        max(matchingEntries.count - visibleEntries.count, 0)
    }

    var shouldShowToggle: Bool {
        matchingEntries.count > max(collapsedLimit, 0)
    }

    private static func filtered(entries: [GlossaryEntry], query: String) -> [GlossaryEntry] {
        let normalizedQuery = normalized(query).lowercased()
        guard !normalizedQuery.isEmpty else { return entries }
        return entries.filter { entry in
            normalized(entry.sourceTerm).lowercased().contains(normalizedQuery)
                || normalized(entry.targetTerm).lowercased().contains(normalizedQuery)
                || normalized(entry.note).lowercased().contains(normalizedQuery)
        }
    }

    private static func normalized(_ value: String) -> String {
        value
            .split { character in
                character == " " || character == "\t" || character == "\n" || character == "\r"
            }
            .joined(separator: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
