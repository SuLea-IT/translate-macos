import SwiftUI
import UniformTypeIdentifiers

struct TranscriptsView: View {
    @EnvironmentObject private var appState: AppState
    @Binding var selectedSession: TranscriptSession?
    @State private var searchText = ""
    @State private var viewMode: TranscriptViewMode = .both
    @State private var exportDocument: TranscriptExportDocument?
    @State private var exportFileName = "LiveBuddy-Transcript"
    @State private var exportContentType: UTType = .plainText
    @State private var exportErrorMessage: String?
    @State private var generatedMeetingNotes: MeetingNotes?
    @State private var meetingNotesSessionID: UUID?

    private let transcriptExporter = TranscriptExporter()
    private let meetingNotesGenerator = MeetingNotesGenerator()

    private var filteredSessions: [TranscriptSession] {
        if searchText.isEmpty {
            return appState.transcriptSessions
        }
        return appState.transcriptSessions.filter {
            $0.fullText.localizedCaseInsensitiveContains(searchText)
            || $0.targetLanguage.localizedCaseInsensitiveContains(searchText)
        }
    }

    var body: some View {
        if let session = selectedSession {
            detailContent(session)
        } else {
            listView
        }
    }

    // MARK: - List View

    private var listView: some View {
        VStack(spacing: 0) {
            listHeader
            Divider()

            if appState.transcriptSessions.isEmpty {
                emptyState
            } else {
                VStack(spacing: 0) {
                    searchBar
                    sessionList
                }
            }
        }
    }

    private var listHeader: some View {
        HStack {
            Text(appState.t(.transcripts))
                .font(.headline)
            Spacer()
            if !appState.transcriptSessions.isEmpty {
                Button(role: .destructive) {
                    appState.deleteAllTranscriptSessions()
                    selectedSession = nil
                } label: {
                    Label(appState.t(.clearAll), systemImage: "trash")
                }
                .foregroundStyle(.red)
            }
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 10)
    }

    private var searchBar: some View {
        HStack(spacing: 8) {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(.secondary)
                .font(.system(size: 13))
            TextField(appState.t(.searchTranscripts), text: $searchText)
                .textFieldStyle(.plain)
                .font(.system(size: 13))
        }
        .padding(8)
        .background(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .fill(Color(nsColor: .controlBackgroundColor))
        )
        .padding(.horizontal, 16)
        .padding(.top, 10)
        .padding(.bottom, 6)
    }

    private var sessionList: some View {
        ScrollView {
            LazyVStack(spacing: 6) {
                ForEach(filteredSessions) { session in
                    SessionCard(session: session)
                        .contentShape(Rectangle())
                        .onTapGesture {
                            withAnimation(.easeInOut(duration: 0.2)) {
                                selectedSession = session
                            }
                        }
                        .contextMenu {
                            Button(appState.t(.copyTranscript)) {
                                NSPasteboard.general.clearContents()
                                NSPasteboard.general.setString(session.fullText, forType: .string)
                            }
                            Divider()
                            Button(appState.t(.delete), role: .destructive) {
                                appState.deleteTranscriptSession(session)
                                if selectedSession?.id == session.id {
                                    selectedSession = nil
                                }
                            }
                        }
                }

                if filteredSessions.isEmpty && !searchText.isEmpty {
                    VStack(spacing: 6) {
                        Image(systemName: "magnifyingglass")
                            .font(.system(size: 24))
                            .foregroundStyle(.quaternary)
                        Text(appState.t(.noResultsForSearch, searchText))
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 40)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
        }
    }

    private var emptyState: some View {
        VStack(spacing: 12) {
            Spacer()
            Image(systemName: "text.bubble")
                .font(.system(size: 40))
                .foregroundStyle(.quaternary)
            Text(appState.t(.noTranscriptsYet))
                .font(.headline)
                .foregroundStyle(.secondary)
            Text(appState.t(.startSessionPrompt))
                .font(.subheadline)
                .foregroundStyle(.tertiary)
                .multilineTextAlignment(.center)
            Spacer()
        }
        .frame(maxWidth: .infinity)
    }




    private func detailContent(_ session: TranscriptSession) -> some View {
        VStack(spacing: 0) {
            // Session metadata
            VStack(spacing: 8) {
                HStack {
                    Label(session.displayTitle, systemImage: "calendar")
                        .font(.subheadline.weight(.medium))
                    Spacer()
                    Label(session.formattedDuration, systemImage: "clock")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                HStack {
                    Label(session.targetLanguage, systemImage: "globe")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Label(session.audioSource, systemImage: "waveform")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text(appState.t(.lineWordCount, session.lines.count, session.wordCount))
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
                
                Divider()
                    .padding(.vertical, 4)
                
                HStack(spacing: 12) {
                    Picker("", selection: $viewMode) {
                        ForEach(TranscriptViewMode.allCases) { mode in
                            Text(mode.localizedTitle(language: appState.settings.interfaceLanguage)).tag(mode)
                        }
                    }
                    .pickerStyle(.segmented)
                    .labelsHidden()
                    .frame(width: 240)

                    Spacer()

                    Button {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(session.textForMode(viewMode), forType: .string)
                    } label: {
                        Label(appState.t(.copyAll), systemImage: "doc.on.doc")
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.regular)

                    ShareLink(item: session.textForMode(viewMode)) {
                        Label(appState.t(.share), systemImage: "square.and.arrow.up")
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.regular)

                    Button {
                        toggleMeetingNotes(for: session)
                    } label: {
                        Label(
                            isShowingMeetingNotes(for: session) ? appState.t(.hideMeetingNotes) : appState.t(.generateMeetingNotes),
                            systemImage: "list.bullet.clipboard"
                        )
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.regular)
                    .disabled(session.lines.isEmpty)

                    Menu {
                        ForEach(TranscriptExportFormat.allCases) { format in
                            Button(format.localizedTitle(language: appState.settings.interfaceLanguage)) {
                                prepareExport(session: session, format: format)
                            }
                        }
                    } label: {
                        Label(appState.t(.exportTranscript), systemImage: "square.and.arrow.down")
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.regular)
                }

                if let exportErrorMessage {
                    Text(appState.t(.exportFailed, exportErrorMessage))
                        .font(.caption)
                        .foregroundStyle(.red)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }

                if let generatedMeetingNotes, meetingNotesSessionID == session.id {
                    meetingNotesPanel(notes: generatedMeetingNotes, session: session)
                }
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 12)
            .background(Color(nsColor: .controlBackgroundColor).opacity(0.5))

            Divider()

            // Transcript lines
            if session.lines.isEmpty {
                VStack(spacing: 8) {
                    Spacer()
                    Image(systemName: "text.alignleft")
                        .font(.system(size: 28))
                        .foregroundStyle(.quaternary)
                    Text(appState.t(.noTranscriptLinesCaptured))
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    if session.endedAt == nil {
                        Text(appState.t(.sessionStillInProgress))
                            .font(.caption)
                            .foregroundStyle(.tertiary)
                    }
                    Spacer()
                }
                .frame(maxWidth: .infinity)
            } else {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 10) {
                        ForEach(session.lines) { line in
                            TranscriptLineRow(line: line, mode: viewMode)
                        }
                    }
                    .padding(20)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .textSelection(.enabled)
                }
            }
        }
        .fileExporter(
            isPresented: Binding(
                get: { exportDocument != nil },
                set: { isPresented in
                    if !isPresented {
                        exportDocument = nil
                    }
                }
            ),
            document: exportDocument,
            contentType: exportContentType,
            defaultFilename: exportFileName
        ) { result in
            switch result {
            case .success:
                exportDocument = nil
                exportErrorMessage = nil
            case .failure(let error):
                exportDocument = nil
                exportErrorMessage = error.localizedDescription
            }
        }
    }

    private func prepareExport(session: TranscriptSession, format: TranscriptExportFormat) {
        let text = transcriptExporter.export(session: session, mode: viewMode, format: format)
        exportDocument = TranscriptExportDocument(text: text, contentType: format.contentType)
        exportContentType = format.contentType
        exportFileName = transcriptExporter.defaultFileName(session: session, mode: viewMode, format: format)
        exportErrorMessage = nil
    }

    private func toggleMeetingNotes(for session: TranscriptSession) {
        if isShowingMeetingNotes(for: session) {
            generatedMeetingNotes = nil
            meetingNotesSessionID = nil
            return
        }
        generatedMeetingNotes = meetingNotesGenerator.generate(from: session, mode: viewMode)
        meetingNotesSessionID = session.id
    }

    private func isShowingMeetingNotes(for session: TranscriptSession) -> Bool {
        generatedMeetingNotes != nil && meetingNotesSessionID == session.id
    }

    private func copyMeetingNotes(_ notes: MeetingNotes, session: TranscriptSession) {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(meetingNotesGenerator.markdown(for: notes, session: session), forType: .string)
    }

    private func exportMeetingNotes(_ notes: MeetingNotes, session: TranscriptSession) {
        let contentType = UTType(filenameExtension: "md") ?? .plainText
        exportDocument = TranscriptExportDocument(text: meetingNotesGenerator.markdown(for: notes, session: session), contentType: contentType)
        exportContentType = contentType
        exportFileName = meetingNotesGenerator.defaultFileName(session: session)
        exportErrorMessage = nil
    }

    private func meetingNotesPanel(notes: MeetingNotes, session: TranscriptSession) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label(appState.t(.meetingNotes), systemImage: "list.bullet.clipboard")
                    .font(.headline)
                Spacer()
                Button {
                    copyMeetingNotes(notes, session: session)
                } label: {
                    Label(appState.t(.copyMeetingNotes), systemImage: "doc.on.doc")
                }
                .buttonStyle(.bordered)
                .controlSize(.small)

                Button {
                    exportMeetingNotes(notes, session: session)
                } label: {
                    Label(appState.t(.exportMeetingNotes), systemImage: "square.and.arrow.down")
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
            }

            meetingNotesSection(title: appState.t(.meetingSummary), bullets: notes.summary, includeTime: false)
            meetingNotesSection(title: appState.t(.meetingKeyPoints), bullets: notes.keyPoints, includeTime: false)
            meetingNotesSection(title: appState.t(.meetingActionItems), bullets: notes.actionItems, includeTime: true, emptyText: appState.t(.noActionItemsFound))
            meetingNotesSection(title: appState.t(.meetingTimeline), bullets: notes.timeline, includeTime: true)
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .fill(Color(nsColor: .windowBackgroundColor))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .stroke(Color(nsColor: .separatorColor), lineWidth: 0.5)
        )
    }

    private func meetingNotesSection(title: String, bullets: [MeetingNoteBullet], includeTime: Bool, emptyText: String? = nil) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(title)
                .font(.subheadline.weight(.semibold))
            if bullets.isEmpty {
                Text(emptyText ?? "—")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(bullets) { bullet in
                    HStack(alignment: .top, spacing: 6) {
                        Text("•")
                            .foregroundStyle(.secondary)
                        if includeTime {
                            Text("[\(bullet.readableOffset)]")
                                .font(.caption.monospacedDigit())
                                .foregroundStyle(.tertiary)
                        }
                        Text(bullet.text)
                            .font(.caption)
                            .foregroundStyle(.primary)
                            .textSelection(.enabled)
                    }
                }
            }
        }
    }
}

// MARK: - Session Card

struct SessionCard: View {
    @EnvironmentObject private var appState: AppState
    let session: TranscriptSession

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(session.displayTitle)
                    .font(.subheadline.weight(.medium))
                Spacer()
                Text(session.formattedDuration)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            if !session.lines.isEmpty {
                Text(session.lines.prefix(2).map(\.text).joined(separator: " "))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }

            HStack(spacing: 10) {
                Label(session.targetLanguage, systemImage: "globe")
                Label(session.audioSource, systemImage: "waveform")
                Spacer()
                Text(appState.t(.linesFormat, session.lines.count))

                if session.endedAt == nil {
                    Text(appState.t(.live))
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Capsule().fill(.red))
                }
            }
            .font(.caption2)
            .foregroundStyle(.tertiary)
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .fill(Color(nsColor: .controlBackgroundColor))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .stroke(Color(nsColor: .separatorColor), lineWidth: 0.5)
        )
    }
}

// MARK: - Transcript Line Row

struct TranscriptLineRow: View {
    let line: TranscriptLine
    let mode: TranscriptViewMode

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Text(line.timestamp, style: .time)
                .font(.caption.monospacedDigit())
                .foregroundStyle(.tertiary)
                .frame(width: 60, alignment: .leading)

            VStack(alignment: .leading, spacing: 4) {
                switch mode {
                case .both:
                    if let originalText = line.originalText, !originalText.isEmpty {
                        Text(originalText)
                            .font(.callout)
                            .foregroundStyle(.secondary)
                    }
                    Text(line.text)
                        .font(.callout.weight(.medium))
                        .foregroundStyle(.primary)
                case .original:
                    Text(line.originalText ?? line.text)
                        .font(.callout)
                        .foregroundStyle(.primary)
                case .translated:
                    Text(line.text)
                        .font(.callout.weight(.medium))
                        .foregroundStyle(.primary)
                }
            }
        }
    }
}
