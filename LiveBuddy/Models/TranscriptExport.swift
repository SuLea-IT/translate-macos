import Foundation
import UniformTypeIdentifiers

enum TranscriptExportFormat: String, CaseIterable, Identifiable, Codable {
    case srt
    case webVTT
    case markdown
    case plainText

    var id: String { rawValue }

    var fileExtension: String {
        switch self {
        case .srt:
            "srt"
        case .webVTT:
            "vtt"
        case .markdown:
            "md"
        case .plainText:
            "txt"
        }
    }

    var contentType: UTType {
        switch self {
        case .srt:
            UTType(filenameExtension: "srt") ?? .plainText
        case .webVTT:
            UTType(filenameExtension: "vtt") ?? .plainText
        case .markdown:
            UTType(filenameExtension: "md") ?? .plainText
        case .plainText:
            .plainText
        }
    }
}

struct TranscriptExportCue: Equatable {
    let index: Int
    let start: TimeInterval
    let end: TimeInterval
    let text: String
}

struct TranscriptExporter {
    private let minimumFinalDuration: TimeInterval = 1.5
    private let maximumFinalDuration: TimeInterval = 6.0
    private let minimumCueGap: TimeInterval = 0.5
    private let secondsPerCharacter: TimeInterval = 0.06

    func cues(for session: TranscriptSession, mode: TranscriptViewMode) -> [TranscriptExportCue] {
        let entries = session.lines
            .sorted { $0.timestamp < $1.timestamp }
            .compactMap { line -> (start: TimeInterval, text: String)? in
                let text = normalizedCueText(selectedText(for: line, mode: mode))
                guard !text.isEmpty else { return nil }
                let start = max(0, line.timestamp.timeIntervalSince(session.startedAt))
                return (start, sanitizedCuePayload(text))
            }

        guard !entries.isEmpty else { return [] }

        return entries.enumerated().map { offset, entry in
            let end: TimeInterval
            if offset + 1 < entries.count, entries[offset + 1].start > entry.start {
                end = entries[offset + 1].start
            } else {
                end = finalEndTime(for: entry, session: session)
            }
            return TranscriptExportCue(
                index: offset + 1,
                start: entry.start,
                end: max(end, entry.start + minimumCueGap),
                text: entry.text
            )
        }
    }

    func export(session: TranscriptSession, mode: TranscriptViewMode, format: TranscriptExportFormat) -> String {
        switch format {
        case .srt:
            composeSRT(cues: cues(for: session, mode: mode))
        case .webVTT:
            composeWebVTT(cues: cues(for: session, mode: mode))
        case .markdown:
            composeMarkdown(session: session, mode: mode)
        case .plainText:
            composePlainText(session: session, mode: mode)
        }
    }

    func defaultFileName(session: TranscriptSession, mode: TranscriptViewMode, format: TranscriptExportFormat) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd-HHmm"
        let datePart = formatter.string(from: session.startedAt)
        let modePart = mode.rawValue.lowercased()
        let languagePart = sanitizedFileNameComponent(session.targetLanguage, fallback: "transcript")
        return "LiveBuddy-\(datePart)-\(languagePart)-\(modePart).\(format.fileExtension)"
    }

    private func composeSRT(cues: [TranscriptExportCue]) -> String {
        cues.map { cue in
            """
            \(cue.index)
            \(formatTimestamp(cue.start, millisecondSeparator: ",")) --> \(formatTimestamp(cue.end, millisecondSeparator: ","))
            \(cue.text)
            """
        }
        .joined(separator: "\n\n")
        .appending(cues.isEmpty ? "" : "\n")
    }

    private func composeWebVTT(cues: [TranscriptExportCue]) -> String {
        let body = cues.map { cue in
            """
            \(formatTimestamp(cue.start, millisecondSeparator: ".")) --> \(formatTimestamp(cue.end, millisecondSeparator: "."))
            \(cue.text)
            """
        }
        .joined(separator: "\n\n")
        return body.isEmpty ? "WEBVTT\n" : "WEBVTT\n\n\(body)\n"
    }

    private func composeMarkdown(session: TranscriptSession, mode: TranscriptViewMode) -> String {
        var sections = [
            "# Transcript",
            "",
            "- Started: \(formattedSessionDate(session.startedAt))",
            "- Source: \(session.audioSource)",
            "- Target Language: \(session.targetLanguage)",
            "- Duration: \(session.formattedDuration)",
            "- Mode: \(mode.rawValue)",
            "",
            "---",
            ""
        ]

        let body = cues(for: session, mode: mode).map { cue in
            "## \(formatReadableOffset(cue.start))\n\n\(cue.text)"
        }.joined(separator: "\n\n")
        if !body.isEmpty {
            sections.append(body)
            sections.append("")
        }
        return sections.joined(separator: "\n")
    }

    private func composePlainText(session: TranscriptSession, mode: TranscriptViewMode) -> String {
        cues(for: session, mode: mode)
            .map(\.text)
            .joined(separator: "\n\n")
            .appending(session.lines.isEmpty ? "" : "\n")
    }

    private func selectedText(for line: TranscriptLine, mode: TranscriptViewMode) -> String {
        switch mode {
        case .both:
            if let original = line.originalText, !original.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                return "\(original)\n\(line.text)"
            }
            return line.text
        case .original:
            if let original = line.originalText, !original.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                return original
            }
            return line.text
        case .translated:
            return line.text
        }
    }

    private func normalizedCueText(_ text: String) -> String {
        text.components(separatedBy: .newlines)
            .map { line in
                line.split { character in
                    character == " " || character == "\t"
                }
                .joined(separator: " ")
                .trimmingCharacters(in: .whitespacesAndNewlines)
            }
            .filter { !$0.isEmpty }
            .joined(separator: "\n")
    }

    private func sanitizedCuePayload(_ text: String) -> String {
        text.replacingOccurrences(of: "-->", with: "→")
    }

    private func finalEndTime(for entry: (start: TimeInterval, text: String), session: TranscriptSession) -> TimeInterval {
        let estimated = min(
            max(Double(entry.text.count) * secondsPerCharacter, minimumFinalDuration),
            maximumFinalDuration
        )
        let estimatedEnd = entry.start + estimated
        guard let endedAt = session.endedAt else { return estimatedEnd }
        let sessionEnd = endedAt.timeIntervalSince(session.startedAt)
        guard sessionEnd > entry.start else { return estimatedEnd }
        return min(estimatedEnd, sessionEnd)
    }

    private func formatTimestamp(_ time: TimeInterval, millisecondSeparator: String) -> String {
        let totalMilliseconds = max(0, Int((time * 1000).rounded()))
        let milliseconds = totalMilliseconds % 1000
        let totalSeconds = totalMilliseconds / 1000
        let seconds = totalSeconds % 60
        let totalMinutes = totalSeconds / 60
        let minutes = totalMinutes % 60
        let hours = totalMinutes / 60
        return String(format: "%02d:%02d:%02d%@%03d", hours, minutes, seconds, millisecondSeparator, milliseconds)
    }

    private func formatReadableOffset(_ time: TimeInterval) -> String {
        let totalSeconds = max(0, Int(time.rounded(.down)))
        let seconds = totalSeconds % 60
        let minutes = (totalSeconds / 60) % 60
        let hours = totalSeconds / 3600
        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, seconds)
        }
        return String(format: "%02d:%02d", minutes, seconds)
    }

    private func formattedSessionDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateStyle = .medium
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }

    private func sanitizedFileNameComponent(_ value: String, fallback: String) -> String {
        let disallowed = CharacterSet(charactersIn: "/\\?%*|\"<>:").union(.newlines).union(.controlCharacters)
        let parts = value.components(separatedBy: disallowed)
            .joined(separator: "-")
            .split { $0 == " " || $0 == "\t" }
            .joined(separator: "-")
            .trimmingCharacters(in: CharacterSet(charactersIn: ".- "))
        return parts.isEmpty ? fallback : parts
    }
}

struct TranscriptArchiveExporter {
    private let transcriptExporter = TranscriptExporter()

    func export(sessions: [TranscriptSession], mode: TranscriptViewMode) -> String {
        var sections = [
            "# LiveBuddy Transcript Archive",
            "",
            "- Sessions: \(sessions.count)",
            "- Mode: \(mode.rawValue)",
            "",
            "---",
            ""
        ]

        for (index, session) in sessions.enumerated() {
            sections.append("## \(index + 1). \(session.displayTitle)")
            sections.append("")
            sections.append(transcriptExporter.export(session: session, mode: mode, format: .markdown).trimmingCharacters(in: .whitespacesAndNewlines))
            sections.append("")
            sections.append("---")
            sections.append("")
        }

        return sections.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines) + "\n"
    }

    func defaultFileName(date: Date = Date()) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd-HHmm"
        return "LiveBuddy-Transcript-Archive-\(formatter.string(from: date)).md"
    }
}
