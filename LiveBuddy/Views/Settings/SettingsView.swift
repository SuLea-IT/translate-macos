import SwiftUI
import AppKit
import UniformTypeIdentifiers

enum NavigationItem: Hashable {
    case provider
    case caption
    case glossary
    case test
    case transcripts
    case logs
}

struct SettingsView: View {
    @EnvironmentObject private var appState: AppState
    @State private var selectedItem: NavigationItem? = .caption
    @State private var selectedTranscript: TranscriptSession?
    @State private var isCheckingToken = false
    @State private var isTokenValid: Bool? = nil
    @State private var tokenCheckError: String? = nil
    @State private var tokenCheckTask: Task<Void, Never>?
    @State private var tokenCheckGeneration = UUID()
    @State private var recordingShortcutAction: GlobalShortcutAction?
    @State private var newGlossarySourceTerm = ""
    @State private var newGlossaryTargetTerm = ""
    @State private var selectedGlossaryImportSourceID = GlossaryImportSource.microsoftTerminology.id
    @State private var glossaryImportURLString = ""
    @State private var glossaryImportLimit = 500
    @State private var showingGlossaryFileImporter = false
    @State private var glossaryImportInputMessage = ""
    @State private var isGlossaryListExpanded = false
    @State private var glossarySearchText = ""
    @State private var glossaryExportDocument: GlossaryExportDocument?
    @State private var glossaryExportFileName = "LiveBuddy-Glossary.csv"
    @State private var glossaryExportErrorMessage: String?
    @State private var isShowingClearGlossaryConfirmation = false
    @State private var logExportDocument: TranscriptExportDocument?
    @State private var logExportFileName = "LiveBuddy-Logs.txt"
    @State private var logExportErrorMessage: String?
    @State private var logCopyErrorMessage: String?
    @State private var isShowingClearLogsConfirmation = false

    var body: some View {
        NavigationSplitView {
            List(selection: $selectedItem) {
                HStack(spacing: 8) {
                    Image(systemName: "captions.bubble.fill")
                        .font(.system(size: 20, weight: .semibold))
                        .foregroundStyle(.tint)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(appState.t(.liveTranslate))
                            .font(.headline)
                        HStack(spacing: 5) {
                            StatusDot(level: appState.statusLevel, interfaceLanguage: appState.settings.interfaceLanguage)
                            Text(appState.statusMessage)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .lineLimit(1)
                        }
                    }
                }
                .padding(.vertical, 12)
                .padding(.horizontal, 4)
                
                Section(appState.t(.settings)) {
                    NavigationLink(value: NavigationItem.caption) {
                        Label(appState.t(.caption), systemImage: "captions.bubble")
                    }
                    NavigationLink(value: NavigationItem.glossary) {
                        Label(appState.t(.terminologyGlossary), systemImage: "text.book.closed")
                    }
                    NavigationLink(value: NavigationItem.provider) {
                        Label(appState.t(.apiProvider), systemImage: "network")
                    }
                    NavigationLink(value: NavigationItem.test) {
                        Label(appState.t(.test), systemImage: "checkmark.seal")
                    }
                }
                
                Section(appState.t(.historyAndData)) {
                    NavigationLink(value: NavigationItem.transcripts) {
                        Label(appState.t(.transcripts), systemImage: "text.bubble")
                    }
                    
                    NavigationLink(value: NavigationItem.logs) {
                        Label(appState.t(.logs), systemImage: "list.bullet.rectangle")
                    }
                }
            }
            .navigationSplitViewColumnWidth(min: 200, ideal: 220, max: 260)
        } detail: {
            VStack(spacing: 0) {
                if let issue = appState.currentDiagnosticIssue {
                    DiagnosticIssueBanner(issue: issue)
                        .padding(.horizontal, 20)
                        .padding(.top, 12)
                }

                Group {
                    switch selectedItem {
                    case .provider, .none:
                        providerForm
                    case .caption:
                        captionForm
                    case .glossary:
                        glossaryForm
                    case .test:
                        preflightTestForm
                    case .transcripts:
                        TranscriptsView(selectedSession: $selectedTranscript)
                    case .logs:
                        logsView
                    }
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Color(nsColor: .windowBackgroundColor))
            .toolbar {
                if selectedItem == .transcripts && selectedTranscript != nil {
                    ToolbarItem(placement: .navigation) {
                        Button {
                            withAnimation(.easeInOut(duration: 0.2)) {
                                selectedTranscript = nil
                            }
                        } label: {
                            Image(systemName: "chevron.left")
                        }
                        .help(appState.t(.backToTranscriptsList))
                    }
                }
                
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        appState.toggle()
                    } label: {
                        Label(appState.isRunning ? appState.t(.stop) : appState.t(.start), systemImage: appState.isRunning ? "stop.fill" : "play.fill")
                            .labelStyle(.titleAndIcon)
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)
                    .disabled(appState.settings.apiKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    .padding(.horizontal, 16)
                }
            }
        }
        .sheet(isPresented: $appState.showSetupSheet) {
            ProviderSetupSheet()
        }
        .onDisappear {
            cancelTokenCheck()
            recordingShortcutAction = nil
        }
    }

    private var providerForm: some View {
        Form {
            Section(appState.t(.settings)) {
                Picker(appState.t(.interfaceLanguage), selection: appState.binding(\.interfaceLanguage)) {
                    ForEach(InterfaceLanguage.allCases) { language in
                        Text(language.displayName).tag(language)
                    }
                }
                .pickerStyle(.menu)
            }

            Section {
                SetupChecklistView()
            }

            Section(appState.t(.activeProvider)) {
                Picker(appState.t(.provider), selection: appState.binding(\.activeProvider)) {
                    ForEach(AIProvider.allCases) { provider in
                        Text(provider.title).tag(provider)
                    }
                }
                .pickerStyle(.menu)
            }
            
            if appState.settings.activeProvider == .gemini {
                Section(appState.t(.googleGemini)) {
                    HStack(spacing: 8) {
                        SecureField(appState.t(.apiKey), text: appState.apiKeyBinding())
                        
                        if isCheckingToken {
                            ProgressView()
                                .controlSize(.small)
                                .frame(width: 16, height: 16)
                        } else if let isValid = isTokenValid {
                            Image(systemName: isValid ? "checkmark.circle.fill" : "exclamationmark.circle.fill")
                                .foregroundColor(isValid ? .green : .red)
                                .imageScale(.medium)
                                .help(tokenCheckError ?? (isValid ? appState.t(.tokenValid) : appState.t(.verificationFailed)))
                        }
                        
                        Button(appState.t(.check)) {
                            startTokenCheck()
                        }
                        .disabled(appState.settings.apiKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isCheckingToken)
                    }
                    
                    if let error = tokenCheckError, !error.isEmpty {
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                    }
                }
            }
            
            Section(appState.t(.translationPrompt)) {
                TextEditor(text: appState.binding(\.userPrompt))
                    .font(.body)
                    .frame(minHeight: 92)
            }

            Section(appState.t(.updates)) {
                Text(appState.t(.freeBuildInstallHint))
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Button {
                    if let url = URL(string: "https://github.com/SuLea-IT/translate-macos/releases") {
                        NSWorkspace.shared.open(url)
                    }
                } label: {
                    Label(appState.t(.checkForUpdates), systemImage: "arrow.down.circle")
                }
                .help(appState.t(.openGitHubReleases))
            }
        }
        .formStyle(.grouped)
        .onChange(of: appState.settings.apiKey) { _, _ in
            cancelTokenCheck()
            isTokenValid = nil
            tokenCheckError = nil
        }
    }

    private var captionForm: some View {
        Form {
            Section(appState.t(.translationAndAudio)) {
                Picker(appState.t(.audioSource), selection: appState.binding(\.audioSource)) {
                    ForEach(AudioSource.allCases) { source in
                        Text(source.localizedTitle(language: appState.settings.interfaceLanguage)).tag(source)
                    }
                }
                .pickerStyle(.segmented)

                if appState.settings.audioSource == .microphone || appState.settings.audioSource == .both {
                    Picker(appState.t(.microphone), selection: appState.binding(\.selectedMicrophoneDeviceUID)) {
                        Text(appState.t(.systemDefault)).tag(nil as String?)
                        ForEach(appState.availableMicrophones) { device in
                            Text(device.name).tag(device.uid as String?)
                        }
                    }
                    .pickerStyle(.menu)
                    .onAppear {
                        appState.refreshAvailableMicrophones()
                    }
                }
                
                Picker(appState.t(.translateFrom), selection: appState.binding(\.sourceLanguageCode)) {
                    Text(appState.t(.autoDetectLanguage)).tag(nil as String?)
                    ForEach(TranslationLanguage.all) { language in
                        Text("\(language.localizedName(language: appState.settings.interfaceLanguage)) (\(language.id))").tag(language.id as String?)
                    }
                }

                Picker(appState.t(.translateTo), selection: appState.binding(\.targetLanguageCode)) {
                    ForEach(TranslationLanguage.all) { language in
                        Text("\(language.localizedName(language: appState.settings.interfaceLanguage)) (\(language.id))").tag(language.id)
                    }
                }

                Picker(appState.t(.subtitleDisplayMode), selection: appState.binding(\.subtitleDisplayMode)) {
                    ForEach(SubtitleDisplayMode.allCases) { mode in
                        Text(mode.localizedTitle(language: appState.settings.interfaceLanguage)).tag(mode)
                    }
                }

                Toggle(appState.t(.echoTargetLanguage), isOn: appState.binding(\.echoTargetLanguage))
                
                HStack {
                    Text(appState.t(.translationVolume))
                    Spacer()
                    Button {
                        appState.updateSetting(\.audioPlayerMuted, to: !appState.settings.audioPlayerMuted)
                    } label: {
                        Image(systemName: appState.settings.audioPlayerMuted || appState.settings.audioPlayerVolume == 0 ? "speaker.slash.fill" : (appState.settings.audioPlayerVolume < 0.5 ? "speaker.wave.1.fill" : "speaker.wave.2.fill"))
                            .frame(width: 20)
                    }
                    .buttonStyle(.plain)
                    
                    Slider(value: appState.binding(\.audioPlayerVolume), in: 0...1)
                        .disabled(appState.settings.audioPlayerMuted)
                        .frame(width: 100)
                    
                    Text("\(Int(appState.settings.audioPlayerVolume * 100))%")
                        .monospacedDigit()
                        .frame(width: 42, alignment: .trailing)
                }
            }
            .onAppear {
                appState.refreshAvailableMicrophones()
            }

            usageControlSection

            Section(appState.t(.globalShortcuts)) {
                Toggle(appState.t(.enableGlobalShortcuts), isOn: appState.globalShortcutsEnabledBinding())

                Text(appState.t(.customizeShortcuts))
                    .font(.caption)
                    .foregroundStyle(.secondary)

                ForEach(GlobalShortcutAction.allCases) { action in
                    ShortcutRecorderField(action: action, recordingAction: $recordingShortcutAction)
                }

                Button(appState.t(.resetAllShortcuts)) {
                    appState.resetAllGlobalShortcuts()
                }
            }

            Section(appState.t(.captionWindow)) {
                HStack {
                    Text(appState.t(.blackTransparency))
                    Slider(value: appState.binding(\.backgroundOpacity), in: 0.15...0.95)
                    Text("\(Int(appState.settings.backgroundOpacity * 100))%")
                        .monospacedDigit()
                        .frame(width: 42, alignment: .trailing)
                }
            }

            Section(appState.t(.subtitleStyle)) {
                HStack {
                    Text(appState.t(.fontSize))
                    Slider(value: appState.binding(\.subtitleFontSize), in: 14...60, step: 1)
                    Text("\(Int(appState.settings.subtitleFontSize)) pt")
                        .monospacedDigit()
                        .frame(width: 48, alignment: .trailing)
                }

                Picker(appState.t(.font), selection: appState.binding(\.subtitleFontName)) {
                    ForEach(SubtitleFontName.allCases) { font in
                        Text(font.displayName).tag(font)
                    }
                }

                HStack(spacing: 12) {
                    Text(appState.t(.style))
                    Spacer()
                    Toggle(isOn: appState.binding(\.subtitleIsBold)) {
                        Text("B").font(.system(size: 14, weight: .bold))
                    }
                    .toggleStyle(.button)
                    .help(appState.t(.bold))

                    Toggle(isOn: appState.binding(\.subtitleIsItalic)) {
                        Text("I").font(.system(size: 14, weight: .regular).italic())
                    }
                    .toggleStyle(.button)
                    .help(appState.t(.italic))

                    Toggle(isOn: appState.binding(\.subtitleIsUnderline)) {
                        Text("U").font(.system(size: 14, weight: .regular)).underline()
                    }
                    .toggleStyle(.button)
                    .help(appState.t(.underline))
                }

                HStack(spacing: 8) {
                    Text(appState.t(.color))
                    Spacer()
                    ForEach(SubtitleColor.presets, id: \.id) { preset in
                        Button {
                            appState.updateSetting(\.subtitleColor, to: preset.color)
                        } label: {
                            Circle()
                                .fill(preset.color.swiftUIColor)
                                .frame(width: 20, height: 20)
                                .overlay(
                                    Circle()
                                        .stroke(Color.primary, lineWidth: appState.settings.subtitleColor == preset.color ? 2 : 0)
                                        .frame(width: 24, height: 24)
                                )
                        }
                        .buttonStyle(.plain)
                        .help(appState.t(preset.titleKey))
                    }
                }

                Text(appState.t(.previewText))
                    .font(.system(size: CGFloat(appState.settings.subtitleFontSize)))
                    .bold(appState.settings.subtitleIsBold)
                    .italic(appState.settings.subtitleIsItalic)
                    .underline(appState.settings.subtitleIsUnderline)
                    .foregroundStyle(appState.settings.subtitleColor.swiftUIColor)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding(.vertical, 6)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(.black.opacity(0.6))
                    )
            }
        }
        .formStyle(.grouped)
    }

    private var usageControlSection: some View {
        Section(appState.t(.usageControl)) {
            usageMetricRow(
                title: appState.t(.thisSessionTranslatedTime),
                value: AppState.formatUsageDuration(appState.usageSnapshot.sessionSentAudioSeconds)
            )
            usageMetricRow(
                title: appState.t(.todayTranslatedTime),
                value: AppState.formatUsageDuration(appState.usageSnapshot.todaySentAudioSeconds)
            )
            Toggle(appState.t(.idleAutoPause), isOn: appState.binding(\.usageControls.idleAutoPauseEnabled))

            HStack {
                Text(appState.t(.idlePauseDelay))
                Spacer()
                Stepper(
                    "\(Int(appState.settings.usageControls.idlePauseDelaySeconds))s",
                    value: appState.binding(\.usageControls.idlePauseDelaySeconds),
                    in: 15...300,
                    step: 15
                )
                .frame(width: 120)
            }
            .disabled(!appState.settings.usageControls.idleAutoPauseEnabled)

            HStack {
                Text(appState.t(.sessionUsageLimit))
                Spacer()
                Stepper(
                    usageLimitText(appState.settings.usageControls.perSessionLimitMinutes),
                    value: appState.binding(\.usageControls.perSessionLimitMinutes),
                    in: 0...480,
                    step: 5
                )
                .frame(width: 140)
            }

            HStack {
                Text(appState.t(.dailyUsageLimit))
                Spacer()
                Stepper(
                    usageLimitText(appState.settings.usageControls.dailyLimitMinutes),
                    value: appState.binding(\.usageControls.dailyLimitMinutes),
                    in: 0...1_440,
                    step: 10
                )
                .frame(width: 140)
            }
        }
    }

    private func usageMetricRow(title: String, value: String) -> some View {
        HStack {
            Text(title)
            Spacer()
            Text(value)
                .monospacedDigit()
                .foregroundStyle(.secondary)
        }
    }

    private func usageLimitText(_ minutes: Double) -> String {
        minutes <= 0 ? appState.t(.usageLimitDisabled) : "\(Int(minutes)) min"
    }

    private var glossaryForm: some View {
        Form {
            glossaryEditorSection
            glossaryImportSection
            glossaryEntriesSection
        }
        .formStyle(.grouped)
        .fileImporter(
            isPresented: $showingGlossaryFileImporter,
            allowedContentTypes: glossaryImportContentTypes,
            allowsMultipleSelection: false
        ) { result in
            handleGlossaryFileImporterResult(result)
        }
        .fileExporter(
            isPresented: Binding(
                get: { glossaryExportDocument != nil },
                set: { isPresented in
                    if !isPresented {
                        glossaryExportDocument = nil
                    }
                }
            ),
            document: glossaryExportDocument,
            contentType: .commaSeparatedText,
            defaultFilename: glossaryExportFileName
        ) { result in
            switch result {
            case .success:
                glossaryExportDocument = nil
                glossaryExportErrorMessage = nil
            case .failure(let error):
                glossaryExportDocument = nil
                if isUserCancelledFileExport(error) {
                    glossaryExportErrorMessage = nil
                    return
                }
                glossaryExportErrorMessage = error.localizedDescription
            }
        }
        .confirmationDialog(
            appState.t(.clearGlossaryConfirmationTitle),
            isPresented: $isShowingClearGlossaryConfirmation,
            titleVisibility: .visible
        ) {
            Button(appState.t(.clearGlossary), role: .destructive) {
                clearGlossaryEntriesFromUI()
            }
            Button(appState.t(.cancel), role: .cancel) {}
        } message: {
            Text(appState.t(.clearGlossaryConfirmationMessage, appState.settings.glossaryEntries.count))
        }
    }

    private var glossaryEditorSection: some View {
        Section(appState.t(.terminologyGlossary)) {
            HStack {
                TextField(appState.t(.sourceTerm), text: $newGlossarySourceTerm)
                TextField(appState.t(.preferredTranslation), text: $newGlossaryTargetTerm)
                Button(appState.t(.addTerm)) {
                    addGlossaryEntryFromUI()
                }
                .disabled(!canMutateGlossaryEntries || newGlossarySourceTerm.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
        }
    }

    private var glossaryImportSection: some View {
        Section(appState.t(.publicTerminologySources)) {
            VStack(alignment: .leading, spacing: 8) {
                Text(appState.t(.glossaryImportHelp))
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Picker(appState.t(.glossaryImportSource), selection: $selectedGlossaryImportSourceID) {
                    ForEach(GlossaryImportSource.availableSources) { source in
                        Text(localizedGlossarySourceName(source)).tag(source.id)
                    }
                }
                .pickerStyle(.menu)
                .onChange(of: selectedGlossaryImportSourceID) { _, _ in
                    clearGlossaryImportSelectionFeedback()
                }

                Text(localizedGlossarySourceDetail(selectedGlossaryImportSource))
                    .font(.caption)
                    .foregroundStyle(.secondary)

                if selectedGlossaryImportSourceRequiresURL {
                    TextField(appState.t(.glossaryImportLinkPlaceholder), text: $glossaryImportURLString)
                        .textFieldStyle(.roundedBorder)
                        .accessibilityLabel(appState.t(.glossaryImportLink))
                        .onChange(of: glossaryImportURLString) { _, _ in
                            clearGlossaryImportSelectionFeedback()
                        }
                }

                Stepper("\(appState.t(.importLimit)): \(glossaryImportLimit)", value: $glossaryImportLimit, in: 1...2_000, step: 50)
                    .onChange(of: glossaryImportLimit) { _, _ in
                        clearGlossaryImportSelectionFeedback()
                    }

                HStack {
                    Button(appState.t(.downloadAndImport)) {
                        importSelectedGlossarySource()
                    }
                    .disabled(appState.isImportingGlossary || !canImportSelectedGlossarySource)

                    Button(appState.t(.importFromFile)) {
                        showingGlossaryFileImporter = true
                    }
                    .disabled(appState.isImportingGlossary)

                    if appState.isImportingGlossary {
                        Button(appState.t(.cancel)) {
                            appState.cancelGlossaryImport()
                        }
                    }

                    if let progress = appState.glossaryImportProgress {
                        HStack(spacing: 6) {
                            if let fraction = progress.fractionCompleted {
                                ProgressView(value: fraction, total: 1)
                                    .progressViewStyle(.linear)
                                Text("\(Int((fraction * 100).rounded()))%")
                                    .font(.caption)
                                    .monospacedDigit()
                                    .foregroundStyle(.secondary)
                                    .frame(width: 38, alignment: .trailing)
                            } else {
                                ProgressView()
                                    .progressViewStyle(.linear)
                                Text(appState.t(.importingGlossary))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .frame(width: 190)
                    }
                }

                if !glossaryImportInputMessage.isEmpty {
                    Text(glossaryImportInputMessage)
                        .font(.caption)
                        .foregroundStyle(.orange)
                }

                if !appState.glossaryImportMessage.isEmpty {
                    Text(appState.glossaryImportMessage)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(.vertical, 4)
        }
    }

    private var glossaryEntriesSection: some View {
        let display = GlossaryListDisplay(
            entries: appState.settings.glossaryEntries,
            query: glossarySearchText,
            isExpanded: isGlossaryListExpanded,
            collapsedLimit: 20
        )

        return Section {
            HStack(spacing: 8) {
                TextField(appState.t(.searchGlossaryTerms), text: $glossarySearchText)
                    .textFieldStyle(.roundedBorder)

                Button {
                    prepareGlossaryExport()
                } label: {
                    Label(appState.t(.exportGlossary), systemImage: "square.and.arrow.down")
                }
                .disabled(appState.settings.glossaryEntries.isEmpty || !canMutateGlossaryEntries)

                Button(role: .destructive) {
                    isShowingClearGlossaryConfirmation = true
                } label: {
                    Label(appState.t(.clearGlossary), systemImage: "trash")
                }
                .disabled(appState.settings.glossaryEntries.isEmpty || !canMutateGlossaryEntries)
            }

            if let glossaryExportErrorMessage {
                Text(appState.t(.exportFailed, glossaryExportErrorMessage))
                    .font(.caption)
                    .foregroundStyle(.red)
            }

            HStack {
                Text(appState.t(.glossaryEntrySummary, display.visibleEntries.count, display.matchingEntries.count))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
                if display.shouldShowToggle {
                    Button(isGlossaryListExpanded ? appState.t(.showFewerTerms) : appState.t(.showAllTerms)) {
                        withAnimation(.easeInOut(duration: 0.2)) {
                            isGlossaryListExpanded.toggle()
                        }
                    }
                    .buttonStyle(.borderless)
                }
            }

            if display.matchingEntries.isEmpty {
                glossaryEmptyState(display: display)
            } else {
                ForEach(display.visibleEntries) { entry in
                    HStack {
                        Text(entry.sourceTerm)
                            .font(.callout.weight(.medium))
                        Image(systemName: "arrow.right")
                            .foregroundStyle(.secondary)
                        Text(entry.targetTerm.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? appState.t(.preserveOriginalTerm) : entry.targetTerm)
                            .foregroundStyle(.secondary)
                        Spacer()
                        Button {
                            deleteGlossaryEntryFromUI(entry)
                        } label: {
                            Image(systemName: "trash")
                        }
                        .buttonStyle(.plain)
                        .disabled(!canMutateGlossaryEntries)
                        .help(appState.t(.deleteTerm))
                    }
                }
            }
        } header: {
            Text(appState.t(.terminologyGlossary))
        }
    }

    @ViewBuilder
    private func glossaryEmptyState(display: GlossaryListDisplay) -> some View {
        let query = glossarySearchText.trimmingCharacters(in: .whitespacesAndNewlines)
        let hasStoredEntries = !display.entries.isEmpty

        HStack {
            Spacer()
            VStack(spacing: 8) {
                Image(systemName: hasStoredEntries ? "magnifyingglass" : "text.book.closed")
                    .font(.title2)
                    .foregroundStyle(.secondary)
                Text(hasStoredEntries && !query.isEmpty ? appState.t(.glossaryNoSearchResults, query) : appState.t(.glossaryEmptyStateTitle))
                    .font(.callout.weight(.medium))
                if !hasStoredEntries {
                    Text(appState.t(.glossaryEmptyStateMessage))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                }
            }
            .frame(maxWidth: 380)
            Spacer()
        }
        .padding(.vertical, 18)
    }

    private var selectedGlossaryImportSource: GlossaryImportSource {
        GlossaryImportSource.availableSources.first { $0.id == selectedGlossaryImportSourceID } ?? .microsoftTerminology
    }

    private var selectedGlossaryImportSourceRequiresURL: Bool {
        switch selectedGlossaryImportSource.kind {
        case .builtIn:
            return false
        case .customURL, .localFile:
            return true
        }
    }

    private var canImportSelectedGlossarySource: Bool {
        switch selectedGlossaryImportSource.kind {
        case .builtIn:
            return true
        case .customURL, .localFile:
            return GlossaryImportURLValidator.remoteURL(from: glossaryImportURLString) != nil
        }
    }

    private var canMutateGlossaryEntries: Bool {
        !appState.isImportingGlossary
    }

    private func startTokenCheck() {
        tokenCheckTask?.cancel()
        let generation = UUID()
        tokenCheckGeneration = generation
        isCheckingToken = true
        isTokenValid = nil
        tokenCheckError = nil
        tokenCheckTask = Task { @MainActor in
            do {
                try await appState.verifyGeminiToken()
                guard tokenCheckGeneration == generation, !Task.isCancelled else { return }
                isTokenValid = true
            } catch {
                guard tokenCheckGeneration == generation, !Task.isCancelled else { return }
                isTokenValid = false
                tokenCheckError = error.localizedDescription
            }
            guard tokenCheckGeneration == generation, !Task.isCancelled else { return }
            isCheckingToken = false
            if tokenCheckGeneration == generation {
                tokenCheckTask = nil
            }
        }
    }

    private func cancelTokenCheck() {
        tokenCheckGeneration = UUID()
        tokenCheckTask?.cancel()
        tokenCheckTask = nil
        isCheckingToken = false
    }

    private var glossaryImportContentTypes: [UTType] {
        [
            .commaSeparatedText,
            .plainText,
            .xml,
            UTType(filenameExtension: "tsv"),
            UTType(filenameExtension: "txt"),
            UTType(filenameExtension: "tbx"),
            UTType(filenameExtension: "zip")
        ].compactMap { $0 }
    }

    private func clearGlossaryImportSelectionFeedback() {
        glossaryImportInputMessage = ""
        appState.clearGlossaryImportFeedback()
    }

    private func clearGlossaryExportFeedback() {
        glossaryExportDocument = nil
        glossaryExportErrorMessage = nil
    }

    private func prepareGlossaryExport() {
        let exporter = GlossaryExporter()
        glossaryExportDocument = GlossaryExportDocument(csvText: exporter.export(entries: appState.settings.glossaryEntries))
        glossaryExportFileName = exporter.defaultFileName()
        glossaryExportErrorMessage = nil
    }

    private func addGlossaryEntryFromUI() {
        guard canMutateGlossaryEntries else { return }
        appState.addGlossaryEntry(sourceTerm: newGlossarySourceTerm, targetTerm: newGlossaryTargetTerm)
        newGlossarySourceTerm = ""
        newGlossaryTargetTerm = ""
        clearGlossaryExportFeedback()
    }

    private func deleteGlossaryEntryFromUI(_ entry: GlossaryEntry) {
        guard canMutateGlossaryEntries else { return }
        appState.deleteGlossaryEntry(entry)
        clearGlossaryExportFeedback()
    }

    private func clearGlossaryEntriesFromUI() {
        guard canMutateGlossaryEntries else { return }
        appState.clearGlossaryEntries()
        glossarySearchText = ""
        isGlossaryListExpanded = false
        clearGlossaryExportFeedback()
    }

    private func localizedGlossarySourceName(_ source: GlossaryImportSource) -> String {
        switch source.id {
        case GlossaryImportSource.microsoftTerminology.id:
            return appState.t(.microsoftTerminology)
        case GlossaryImportSource.iateExport.id:
            return appState.t(.iateExportSource)
        case GlossaryImportSource.customLink.id:
            return appState.t(.customGlossaryLink)
        default:
            return source.displayName
        }
    }

    private func localizedGlossarySourceDetail(_ source: GlossaryImportSource) -> String {
        switch source.id {
        case GlossaryImportSource.microsoftTerminology.id:
            return appState.t(.microsoftTerminologyDetail)
        case GlossaryImportSource.iateExport.id:
            return appState.t(.iateExportSourceDetail)
        case GlossaryImportSource.customLink.id:
            return appState.t(.customGlossaryLinkDetail)
        default:
            return source.detail
        }
    }

    private func importSelectedGlossarySource() {
        glossaryImportInputMessage = ""
        appState.clearGlossaryImportFeedback()
        clearGlossaryExportFeedback()
        let source = selectedGlossaryImportSource
        switch source.kind {
        case .builtIn(let url):
            appState.startGlossaryImport(from: url, sourceName: localizedGlossarySourceName(source), importLimit: glossaryImportLimit)
        case .customURL, .localFile:
            guard let url = GlossaryImportURLValidator.remoteURL(from: glossaryImportURLString) else {
                glossaryImportInputMessage = appState.t(.httpsLinksOnly)
                return
            }
            appState.startGlossaryImport(from: url, sourceName: localizedGlossarySourceName(source), importLimit: glossaryImportLimit)
        }
    }

    private func handleGlossaryFileImporterResult(_ result: Result<[URL], Error>) {
        glossaryImportInputMessage = ""
        appState.clearGlossaryImportFeedback()
        clearGlossaryExportFeedback()
        switch result {
        case .success(let urls):
            guard let url = urls.first else { return }
            appState.startGlossaryImportFromLocalFile(url: url, sourceName: url.lastPathComponent, importLimit: glossaryImportLimit)
        case .failure(let error):
            if isUserCancelledFileDialog(error) {
                return
            }
            glossaryImportInputMessage = error.localizedDescription
        }
    }

    private var preflightTestForm: some View {
        Form {
            Section(appState.t(.preflightTest)) {
                Text(appState.t(.preflightTestDescription))
                    .font(.callout)
                    .foregroundStyle(.secondary)

                Button(appState.t(.runTest)) {
                    appState.startPreflightTest()
                }
                .disabled(appState.isRunning || appState.isRunningPreflightTest)
            }

            Section {
                ForEach(appState.preflightTestReport.steps) { step in
                    PreflightTestStepRow(step: step, language: appState.settings.interfaceLanguage)
                }
            }
        }
        .formStyle(.grouped)
    }

    private var logsView: some View {
        VStack(spacing: 0) {
            HStack {
                Text(appState.t(.runtimeLogs))
                    .font(.headline)
                Spacer()
                Button {
                    copyLogsFromUI()
                } label: {
                    Label(appState.t(.copyLogs), systemImage: "doc.on.doc")
                }
                .disabled(appState.logs.isEmpty)

                Button {
                    exportLogsFromUI()
                } label: {
                    Label(appState.t(.exportLogs), systemImage: "square.and.arrow.down")
                }
                .disabled(appState.logs.isEmpty)

                Button(role: .destructive) {
                    isShowingClearLogsConfirmation = true
                } label: {
                    Label(appState.t(.clear), systemImage: "trash")
                }
                .disabled(appState.logs.isEmpty)
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 10)

            Divider()

            if let logCopyErrorMessage {
                Text(logCopyErrorMessage)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 20)
                    .padding(.top, 8)
            }

            if let logExportErrorMessage {
                Text(appState.t(.exportFailed, logExportErrorMessage))
                    .font(.caption)
                    .foregroundStyle(.red)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 20)
                    .padding(.top, 8)
            }

            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 8) {
                        ForEach(appState.logs) { entry in
                            LogRow(entry: entry)
                                .id(entry.id)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(20)
                }
                .onChange(of: appState.logs.last?.id) { _, id in
                    guard let id else { return }
                    proxy.scrollTo(id, anchor: .bottom)
                }
            }
        }
        .fileExporter(
            isPresented: Binding(
                get: { logExportDocument != nil },
                set: { isPresented in
                    if !isPresented {
                        logExportDocument = nil
                    }
                }
            ),
            document: logExportDocument,
            contentType: .plainText,
            defaultFilename: logExportFileName
        ) { result in
            switch result {
            case .success:
                logExportDocument = nil
                logExportErrorMessage = nil
                logCopyErrorMessage = nil
            case .failure(let error):
                logExportDocument = nil
                if isUserCancelledFileExport(error) {
                    logExportErrorMessage = nil
                    logCopyErrorMessage = nil
                    return
                }
                logExportErrorMessage = error.localizedDescription
                logCopyErrorMessage = nil
            }
        }
        .confirmationDialog(
            appState.t(.clearLogsConfirmationTitle),
            isPresented: $isShowingClearLogsConfirmation,
            titleVisibility: .visible
        ) {
            Button(appState.t(.clear), role: .destructive) {
                clearLogsFromUI()
            }
            Button(appState.t(.cancel), role: .cancel) {}
        } message: {
            Text(appState.t(.clearLogsConfirmationMessage, appState.logs.count))
        }
    }

    private func copyLogsFromUI() {
        let logText = LogExporter().export(entries: appState.logs, language: appState.settings.interfaceLanguage)
        NSPasteboard.general.clearContents()
        let didCopy = NSPasteboard.general.setString(logText, forType: .string)
        guard didCopy else {
            logCopyErrorMessage = appState.t(.copyFailed)
            logExportErrorMessage = nil
            return
        }
        logCopyErrorMessage = nil
        logExportErrorMessage = nil
    }

    private func exportLogsFromUI() {
        let exporter = LogExporter()
        let logText = exporter.export(entries: appState.logs, language: appState.settings.interfaceLanguage)
        logExportDocument = TranscriptExportDocument(text: logText, contentType: .plainText)
        logExportFileName = exporter.defaultFileName()
        logExportErrorMessage = nil
        logCopyErrorMessage = nil
    }

    private func clearLogsFromUI() {
        appState.clearLogs()
        logExportErrorMessage = nil
        logCopyErrorMessage = nil
    }
}

private struct PreflightTestStepRow: View {
    let step: PreflightTestStep
    let language: InterfaceLanguage

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: iconName)
                .foregroundStyle(iconColor)
                .frame(width: 18)

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.subheadline.weight(.medium))
                if !messageText.isEmpty {
                    Text(messageText)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                if let audio = step.audio {
                    ProgressView(value: Double(audio.rms), total: 1) {
                        Text("RMS \(Int(audio.rms * 100))% · Peak \(Int(audio.peak * 100))%")
                            .font(.caption2)
                    }
                }
            }

            Spacer()
        }
    }

    private var messageText: String {
        if let key = step.messageKey {
            return language.localized(key)
        }
        return step.message
    }

    private var title: String {
        switch step.id {
        case .apiKey:
            language.localized(.apiKeyTest)
        case .permissions:
            language.localized(.permissionsTest)
        case .microphoneAudio:
            language.localized(.microphoneAudioTest)
        case .screenAudio:
            language.localized(.screenAudioTest)
        case .subtitleWindow:
            language.localized(.subtitleWindowTest)
        }
    }

    private var iconName: String {
        switch step.state {
        case .pending:
            "circle"
        case .running:
            "arrow.triangle.2.circlepath"
        case .passed:
            "checkmark.circle.fill"
        case .warning:
            "exclamationmark.triangle.fill"
        case .failed:
            "xmark.octagon.fill"
        }
    }

    private var iconColor: Color {
        switch step.state {
        case .pending:
            .secondary
        case .running:
            .blue
        case .passed:
            .green
        case .warning:
            .orange
        case .failed:
            .red
        }
    }
}

private struct DiagnosticIssueBanner: View {
    @EnvironmentObject private var appState: AppState
    let issue: DiagnosticIssue

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: iconName)
                .foregroundStyle(iconColor)
                .frame(width: 20)

            VStack(alignment: .leading, spacing: 4) {
                Text(appState.t(issue.titleKey))
                    .font(.subheadline.weight(.semibold))
                Text(appState.t(issue.messageKey))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text(appState.t(issue.recoveryKey))
                    .font(.caption)

                if let underlying = issue.underlyingMessage, !underlying.isEmpty {
                    Text("\(appState.t(.diagnosticDetails)): \(underlying)")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                        .textSelection(.enabled)
                }
            }

            Spacer()

            if let action = issue.action {
                Button(actionTitle(for: action)) {
                    appState.performDiagnosticRecoveryAction(action)
                }
                .controlSize(.small)
            }

            Button(appState.t(.diagnosticDismiss)) {
                appState.clearDiagnosticIssue()
            }
            .controlSize(.small)
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(nsColor: .controlBackgroundColor))
        )
    }

    private func actionTitle(for action: DiagnosticRecoveryAction) -> String {
        switch action {
        case .openProviderSettings:
            appState.t(.apiProvider)
        case .openMicrophoneSettings:
            appState.t(.openMicrophoneSettings)
        case .openScreenRecordingSettings:
            appState.t(.openScreenRecordingSettings)
        case .retry:
            appState.t(.start)
        }
    }

    private var iconName: String {
        switch issue.severity {
        case .info:
            "info.circle.fill"
        case .warning:
            "exclamationmark.triangle.fill"
        case .error:
            "xmark.octagon.fill"
        }
    }

    private var iconColor: Color {
        switch issue.severity {
        case .info:
            .blue
        case .warning:
            .orange
        case .error:
            .red
        }
    }
}

struct LogRow: View {
    let entry: LogEntry

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Circle()
                .fill(entry.level == .error ? Color.red : Color.secondary.opacity(0.55))
                .frame(width: 7, height: 7)
                .padding(.top, 6)

            VStack(alignment: .leading, spacing: 2) {
                Text(entry.timestamp, style: .time)
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(.secondary)
                Text(entry.message)
                    .font(.callout)
                    .textSelection(.enabled)
                    .foregroundStyle(entry.level == .error ? .red : .primary)
            }
        }
    }
}

struct ProviderSetupSheet: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "captions.bubble.fill")
                .font(.system(size: 48))
                .foregroundStyle(.tint)
            
            Text(appState.t(.welcomeToLiveBuddy))
                .font(.title2)
                .bold()
            
            Text(appState.t(.configureProviderPrompt))
                .font(.body)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)

            SetupChecklistView()
            
            Form {
                Picker(appState.t(.interfaceLanguage), selection: appState.binding(\.interfaceLanguage)) {
                    ForEach(InterfaceLanguage.allCases) { language in
                        Text(language.displayName).tag(language)
                    }
                }
                .pickerStyle(.menu)

                Picker(appState.t(.provider), selection: appState.binding(\.activeProvider)) {
                    ForEach(AIProvider.allCases) { provider in
                        Text(provider.title).tag(provider)
                    }
                }
                .pickerStyle(.menu)
                
                SecureField(appState.t(.apiKeyUpper), text: appState.apiKeyBinding())
            }
            .formStyle(.grouped)
            .frame(height: 160)
            
            HStack {
                Button(appState.t(.cancel)) {
                    appState.showSetupSheet = false
                }
                .keyboardShortcut(.cancelAction)
                
                Spacer()
                
                Button(appState.t(.getStarted)) {
                    appState.showSetupSheet = false
                    if appState.isProviderConfigured {
                        NotificationCenter.default.post(name: .showCaptionWindow, object: nil)
                    }
                }
                .keyboardShortcut(.defaultAction)
                .disabled(!appState.isProviderConfigured)
                .buttonStyle(.borderedProminent)
            }
            .padding(.top, 10)
        }
        .padding(30)
        .frame(width: 450)
    }
}

#Preview {
    SettingsView()
        .environmentObject(AppState())
}
