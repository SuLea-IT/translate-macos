import Foundation

struct MeetingNotes: Equatable {
    let summary: [MeetingNoteBullet]
    let keyPoints: [MeetingNoteBullet]
    let actionItems: [MeetingNoteBullet]
    let timeline: [MeetingNoteBullet]

    static let empty = MeetingNotes(summary: [], keyPoints: [], actionItems: [], timeline: [])
}

struct MeetingNoteBullet: Identifiable, Equatable {
    let id: UUID
    let timestamp: Date
    let offset: TimeInterval
    let text: String

    init(id: UUID = UUID(), timestamp: Date, offset: TimeInterval, text: String) {
        self.id = id
        self.timestamp = timestamp
        self.offset = offset
        self.text = text
    }

    var readableOffset: String {
        MeetingNotesFormatter.readableOffset(offset)
    }
}

struct MeetingNotesGenerator {
    private let maxSummaryCount = 3
    private let maxKeyPointCount = 5
    private let maxActionItemCount = 5
    private let maxTimelineCount = 8

    func generate(from session: TranscriptSession, mode: TranscriptViewMode) -> MeetingNotes {
        let candidates = candidates(from: session, mode: mode)
        guard !candidates.isEmpty else { return .empty }

        let frequencies = tokenFrequencies(for: candidates)
        let scored = candidates.map { candidate in
            ScoredCandidate(candidate: candidate, score: score(candidate, frequencies: frequencies))
        }
        .sorted { lhs, rhs in
            if lhs.score == rhs.score { return lhs.candidate.offset < rhs.candidate.offset }
            return lhs.score > rhs.score
        }

        let summary = chronologicalBullets(from: unique(scored).prefix(maxSummaryCount).map(\.candidate))
        let keyPoints = chronologicalBullets(from: unique(scored).prefix(maxKeyPointCount).map(\.candidate))
        let actionItems = chronologicalBullets(from: candidates.filter(isActionCandidate).prefix(maxActionItemCount))
        let timeline = chronologicalBullets(from: spreadCandidates(unique(scored).map(\.candidate), limit: maxTimelineCount))

        return MeetingNotes(summary: summary, keyPoints: keyPoints, actionItems: actionItems, timeline: timeline)
    }

    func markdown(for notes: MeetingNotes, session: TranscriptSession) -> String {
        let sections: [String] = [
            "# Meeting Notes",
            "",
            "- Started: \(MeetingNotesFormatter.sessionDate(session.startedAt))",
            "- Source: \(session.audioSource)",
            "- Target Language: \(session.targetLanguage)",
            "- Duration: \(session.formattedDuration)",
            "",
            "## Summary",
            bulletList(notes.summary, includeTime: false),
            "",
            "## Key Points",
            bulletList(notes.keyPoints, includeTime: false),
            "",
            "## Action Items",
            bulletList(notes.actionItems, includeTime: true, emptyText: "No action items found."),
            "",
            "## Timeline",
            bulletList(notes.timeline, includeTime: true),
            ""
        ]
        return sections.joined(separator: "\n")
    }

    func defaultFileName(session: TranscriptSession) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd-HHmm"
        return "LiveBuddy-MeetingNotes-\(formatter.string(from: session.startedAt)).md"
    }

    private func candidates(from session: TranscriptSession, mode: TranscriptViewMode) -> [MeetingCandidate] {
        session.lines
            .sorted { $0.timestamp < $1.timestamp }
            .compactMap { line in
                let text = normalized(selectedText(for: line, mode: mode))
                guard text.count >= 6 else { return nil }
                let offset = max(0, line.timestamp.timeIntervalSince(session.startedAt))
                return MeetingCandidate(timestamp: line.timestamp, offset: offset, text: text, tokens: tokens(in: text))
            }
    }

    private func selectedText(for line: TranscriptLine, mode: TranscriptViewMode) -> String {
        switch mode {
        case .both:
            if let original = line.originalText, !normalized(original).isEmpty {
                return "\(original) \(line.text)"
            }
            return line.text
        case .original:
            return line.originalText ?? line.text
        case .translated:
            return line.text
        }
    }

    private func tokenFrequencies(for candidates: [MeetingCandidate]) -> [String: Double] {
        var counts: [String: Double] = [:]
        for candidate in candidates {
            for token in candidate.tokens {
                counts[token, default: 0] += 1
            }
        }
        return counts
    }

    private func score(_ candidate: MeetingCandidate, frequencies: [String: Double]) -> Double {
        let tokenScore = candidate.tokens.reduce(0.0) { $0 + (frequencies[$1] ?? 0) }
        let uniqueTokenBonus = Double(Set(candidate.tokens).count) * 0.35
        let lengthBonus = min(Double(candidate.text.count) / 120.0, 1.5)
        let actionBonus = isActionCandidate(candidate) ? 1.8 : 0
        let decisionBonus = containsAny(candidate.text, needles: decisionCues) ? 1.4 : 0
        let questionPenalty = candidate.text.contains("?") || candidate.text.contains("？") ? -0.4 : 0
        return tokenScore + uniqueTokenBonus + lengthBonus + actionBonus + decisionBonus + questionPenalty
    }

    private func unique(_ scored: [ScoredCandidate]) -> [ScoredCandidate] {
        var seen = Set<String>()
        var output: [ScoredCandidate] = []
        for item in scored {
            let key = normalized(item.candidate.text).lowercased()
            let compactKey = key.replacingOccurrences(of: " ", with: "")
            guard !seen.contains(key), !seen.contains(compactKey) else { continue }
            seen.insert(key)
            seen.insert(compactKey)
            output.append(item)
        }
        return output
    }

    private func chronologicalBullets(from candidates: some Sequence<MeetingCandidate>) -> [MeetingNoteBullet] {
        candidates
            .sorted { $0.offset < $1.offset }
            .map { candidate in
                MeetingNoteBullet(timestamp: candidate.timestamp, offset: candidate.offset, text: candidate.text)
            }
    }

    private func spreadCandidates(_ candidates: [MeetingCandidate], limit: Int) -> [MeetingCandidate] {
        guard candidates.count > limit else {
            return candidates.sorted { $0.offset < $1.offset }
        }
        let chronological = candidates.sorted { $0.offset < $1.offset }
        let stride = max(1, chronological.count / limit)
        var selected: [MeetingCandidate] = []
        var index = 0
        while selected.count < limit && index < chronological.count {
            selected.append(chronological[index])
            index += stride
        }
        return selected
    }

    private func isActionCandidate(_ candidate: MeetingCandidate) -> Bool {
        containsAny(candidate.text, needles: actionCues)
    }

    private func containsAny(_ text: String, needles: [String]) -> Bool {
        let lowercased = text.lowercased()
        return needles.contains { lowercased.contains($0) }
    }

    private func normalized(_ text: String) -> String {
        text.components(separatedBy: .newlines)
            .joined(separator: " ")
            .split { character in character == " " || character == "\t" || character == "\r" || character == "\n" }
            .joined(separator: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func tokens(in text: String) -> [String] {
        var tokens: [String] = []
        var current = ""
        for scalar in text.lowercased().unicodeScalars {
            if CharacterSet.letters.contains(scalar) || CharacterSet.decimalDigits.contains(scalar) {
                current.unicodeScalars.append(scalar)
            } else {
                appendToken(current, to: &tokens)
                current = ""
            }
        }
        appendToken(current, to: &tokens)
        return tokens
    }

    private func appendToken(_ value: String, to tokens: inout [String]) {
        let token = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard token.count >= 2 else { return }
        guard !stopWords.contains(token) else { return }
        tokens.append(token)
    }

    private func bulletList(_ bullets: [MeetingNoteBullet], includeTime: Bool, emptyText: String = "No content.") -> String {
        guard !bullets.isEmpty else { return "- \(emptyText)" }
        return bullets.map { bullet in
            if includeTime {
                return "- [\(bullet.readableOffset)] \(bullet.text)"
            }
            return "- \(bullet.text)"
        }.joined(separator: "\n")
    }

    private var actionCues: [String] {
        [
            "todo", "to-do", "action item", "need to", "needs to", "we need", "please", "follow up", "prepare", "assign", "deadline", "before friday", "next step", "must",
            "需要", "请", "安排", "待办", "跟进", "准备", "负责人", "截止", "下一步", "必须", "要做"
        ]
    }

    private var decisionCues: [String] {
        ["decision", "decided", "agree", "approved", "ship", "launch", "决定", "确认", "同意", "发布", "上线"]
    }

    private var stopWords: Set<String> {
        [
            "the", "and", "that", "this", "with", "for", "are", "was", "were", "you", "your", "our", "have", "has", "had", "but", "not", "from", "into", "about", "will", "can", "could", "should", "would", "there", "their", "they", "them", "then", "than", "today", "reviewed",
            "我们", "这个", "那个", "然后", "就是", "一下", "进行", "一个", "可以", "因为", "所以", "以及", "已经"
        ]
    }
}

private struct MeetingCandidate: Equatable {
    let timestamp: Date
    let offset: TimeInterval
    let text: String
    let tokens: [String]
}

private struct ScoredCandidate: Equatable {
    let candidate: MeetingCandidate
    let score: Double
}

enum MeetingNotesFormatter {
    static func readableOffset(_ time: TimeInterval) -> String {
        let totalSeconds = max(0, Int(time.rounded(.down)))
        let seconds = totalSeconds % 60
        let minutes = (totalSeconds / 60) % 60
        let hours = totalSeconds / 3600
        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, seconds)
        }
        return String(format: "%02d:%02d", minutes, seconds)
    }

    static func sessionDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
}
