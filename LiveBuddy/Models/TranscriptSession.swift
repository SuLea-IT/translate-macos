import Foundation

struct TranscriptSession: Identifiable, Codable, Equatable {
    let id: UUID
    let startedAt: Date
    var endedAt: Date?
    let targetLanguage: String
    let audioSource: String
    var lines: [TranscriptLine]

    var displayTitle: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: startedAt)
    }

    var duration: TimeInterval? {
        guard let endedAt else { return nil }
        return endedAt.timeIntervalSince(startedAt)
    }

    func finalizedIfNeeded() -> TranscriptSession {
        guard endedAt == nil else { return self }
        var copy = self
        let lastLineTimestamp = lines.map(\.timestamp).max()
        copy.endedAt = max(startedAt, lastLineTimestamp ?? startedAt)
        return copy
    }

    var formattedDuration: String {
        guard let duration else { return "In progress…" }
        let minutes = Int(duration) / 60
        let seconds = Int(duration) % 60
        if minutes > 0 {
            return "\(minutes)m \(seconds)s"
        }
        return "\(seconds)s"
    }

    var fullText: String {
        lines.map { line in
            if let original = line.originalText, !original.isEmpty {
                return "\(original) \(line.text)"
            } else {
                return line.text
            }
        }.joined(separator: "\n")
    }

    var wordCount: Int {
        lines.reduce(0) { $0 + $1.text.split(separator: " ").count + ($1.originalText?.split(separator: " ").count ?? 0) }
    }

    var shareText: String {
        textForMode(.both)
    }

    func textForMode(_ mode: TranscriptViewMode) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        let header = """
        Transcript Session: \(formatter.string(from: startedAt))
        Source: \(audioSource)
        Target Language: \(targetLanguage)
        Duration: \(formattedDuration)
        Mode: \(mode.rawValue)
        ----------------------------------------
        """
        
        let body = lines.map { line in
            let timeStr = line.formattedTime
            switch mode {
            case .both:
                if let original = line.originalText, !original.isEmpty {
                    return "[\(timeStr)]\nOriginal: \(original)\nTranslated: \(line.text)"
                } else {
                    return "[\(timeStr)]\nTranslated: \(line.text)"
                }
            case .original:
                return "[\(timeStr)]\nOriginal: \(line.originalText ?? line.text)"
            case .translated:
                return "[\(timeStr)]\nTranslated: \(line.text)"
            }
        }.joined(separator: "\n\n")
        
        return "\(header)\n\n\(body)"
    }
}

struct TranscriptListDisplay {
    var sessions: [TranscriptSession]
    var query: String
    let filteredSessions: [TranscriptSession]

    init(sessions: [TranscriptSession], query: String) {
        self.sessions = sessions
        self.query = query
        self.filteredSessions = Self.filtered(sessions: sessions, query: query)
    }

    private static func filtered(sessions: [TranscriptSession], query: String) -> [TranscriptSession] {
        let normalizedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalizedQuery.isEmpty else { return sessions }
        return sessions.filter { session in
            session.fullText.localizedCaseInsensitiveContains(normalizedQuery)
                || session.targetLanguage.localizedCaseInsensitiveContains(normalizedQuery)
        }
    }
}

struct TranscriptLine: Identifiable, Codable, Equatable {
    let id: UUID
    let text: String
    let originalText: String?
    let languageCode: String?
    let timestamp: Date

    init(id: UUID = UUID(), text: String, originalText: String? = nil, languageCode: String?, timestamp: Date = Date()) {
        self.id = id
        self.text = text
        self.originalText = originalText
        self.languageCode = languageCode
        self.timestamp = timestamp
    }

    var formattedTime: String {
        let formatter = DateFormatter()
        formatter.timeStyle = .medium
        return formatter.string(from: timestamp)
    }
}

enum TranscriptViewMode: String, CaseIterable, Identifiable, Codable {
    case both = "Both"
    case original = "Original"
    case translated = "Translated"

    var id: String { rawValue }
}
