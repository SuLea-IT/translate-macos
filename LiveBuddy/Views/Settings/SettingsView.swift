import SwiftUI
import AppKit
import UniformTypeIdentifiers

enum NavigationItem: Hashable {
    case provider
    case caption
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
    @State private var newGlossarySourceTerm = ""
    @State private var newGlossaryTargetTerm = ""
    @State private var selectedGlossaryImportSourceID = GlossaryImportSource.microsoftTerminology.id
    @State private var glossaryImportURLString = ""
    @State private var glossaryImportLimit = 500
    @State private var showingGlossaryFileImporter = false
    @State private var glossaryImportInputMessage = ""

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
                            StatusDot(level: appState.statusLevel)
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
                            Task {
                                isCheckingToken = true
                                isTokenValid = nil
                                tokenCheckError = nil
                                do {
                                    try await appState.verifyGeminiToken()
                                    isTokenValid = true
                                } catch {
                                    isTokenValid = false
                                    tokenCheckError = error.localizedDescription
                                }
                                isCheckingToken = false
                            }
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
                        Text("\(language.name) (\(language.id))").tag(language.id as String?)
                    }
                }

                Picker(appState.t(.translateTo), selection: appState.binding(\.targetLanguageCode)) {
                    ForEach(TranslationLanguage.all) { language in
                        Text("\(language.name) (\(language.id))").tag(language.id)
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

                virtualAudioIsolationSection
            }
            .onAppear {
                appState.refreshAvailableMicrophones()
                appState.refreshAvailableOutputDevices()
            }

            usageControlSection

            glossarySection

            Section(appState.t(.globalShortcuts)) {
                Toggle(appState.t(.enableGlobalShortcuts), isOn: appState.globalShortcutsEnabledBinding())

                Text(appState.t(.customizeShortcuts))
                    .font(.caption)
                    .foregroundStyle(.secondary)

                ForEach(GlobalShortcutAction.allCases) { action in
                    ShortcutRecorderField(action: action)
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
                    ForEach(SubtitleColor.presets, id: \.name) { preset in
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
                        .help(preset.name)
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

    private var virtualAudioIsolationSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Toggle(appState.t(.virtualAudioIsolation), isOn: appState.binding(\.virtualAudioIsolationEnabled))

            if appState.settings.virtualAudioIsolationEnabled {
                Label(
                    detectedVirtualInput == nil ? appState.t(.blackHoleNotDetected) : "\(appState.t(.blackHoleDetected)): \(detectedVirtualInput?.name ?? "")",
                    systemImage: detectedVirtualInput == nil ? "exclamationmark.triangle.fill" : "checkmark.circle.fill"
                )
                .font(.caption)
                .foregroundStyle(detectedVirtualInput == nil ? .orange : .green)

                Picker(appState.t(.virtualAudioInputDevice), selection: appState.binding(\.virtualAudioInputDeviceUID)) {
                    Text(appState.t(.systemDefault)).tag(nil as String?)
                    ForEach(virtualInputPickerDevices) { device in
                        Text(device.name).tag(device.uid as String?)
                    }
                }
                .pickerStyle(.menu)

                Picker(appState.t(.translatedVoiceOutputDevice), selection: appState.binding(\.translatedAudioOutputDeviceUID)) {
                    Text(appState.t(.systemDefaultOutput)).tag(nil as String?)
                    ForEach(appState.availableOutputDevices) { device in
                        Text(device.name).tag(device.uid as String?)
                    }
                }
                .pickerStyle(.menu)

                Text(appState.t(.virtualAudioIsolationHelp))
                    .font(.caption)
                    .foregroundStyle(.secondary)

                HStack {
                    Button(appState.t(.openBlackHoleDownload)) {
                        if let url = URL(string: "https://github.com/ExistentialAudio/BlackHole") {
                            NSWorkspace.shared.open(url)
                        }
                    }

                    Button(appState.t(.openSoundSettings)) {
                        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.sound") {
                            NSWorkspace.shared.open(url)
                        }
                    }
                }
            }
        }
        .padding(.top, 4)
    }

    private var detectedVirtualInput: AudioDevice? {
        AudioDeviceManager.preferredVirtualInputDevice(
            from: appState.availableMicrophones,
            selectedUID: appState.settings.virtualAudioInputDeviceUID
        )
    }

    private var virtualInputPickerDevices: [AudioDevice] {
        let virtualDevices = appState.availableMicrophones.filter(AudioDeviceManager.isLikelyVirtualLoopbackDevice)
        return virtualDevices.isEmpty ? appState.availableMicrophones : virtualDevices
    }

    private var usageControlSection: some View {
        Section(appState.t(.costAndUsageControl)) {
            usageMetricRow(
                title: appState.t(.thisSessionTranslatedTime),
                value: AppState.formatUsageDuration(appState.usageSnapshot.sessionSentAudioSeconds)
            )
            usageMetricRow(
                title: appState.t(.todayTranslatedTime),
                value: AppState.formatUsageDuration(appState.usageSnapshot.todaySentAudioSeconds)
            )
            usageMetricRow(
                title: appState.t(.estimatedCost),
                value: "\(AppState.formatUsageCost(appState.usageSnapshot.estimatedSessionCostUSD)) / \(AppState.formatUsageCost(appState.usageSnapshot.estimatedTodayCostUSD))"
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

            HStack {
                Text(appState.t(.estimatedPricePerMinute))
                Spacer()
                Stepper(
                    String(format: "$%.4f/min", appState.settings.usageControls.estimatedCostPerMinuteUSD),
                    value: appState.binding(\.usageControls.estimatedCostPerMinuteUSD),
                    in: 0...1,
                    step: 0.001
                )
                .frame(width: 160)
            }

            Text(appState.t(.pricingEstimateNote))
                .font(.caption)
                .foregroundStyle(.secondary)
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

    private var glossarySection: some View {
        Section(appState.t(.terminologyGlossary)) {
            HStack {
                TextField(appState.t(.sourceTerm), text: $newGlossarySourceTerm)
                TextField(appState.t(.preferredTranslation), text: $newGlossaryTargetTerm)
                Button(appState.t(.addTerm)) {
                    appState.addGlossaryEntry(sourceTerm: newGlossarySourceTerm, targetTerm: newGlossaryTargetTerm)
                    newGlossarySourceTerm = ""
                    newGlossaryTargetTerm = ""
                }
                .disabled(newGlossarySourceTerm.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }

            VStack(alignment: .leading, spacing: 8) {
                Text(appState.t(.publicTerminologySources))
                    .font(.callout.weight(.semibold))
                Text(appState.t(.glossaryImportHelp))
                    .font(.caption)
                    .foregroundStyle(.secondary)

                Picker(appState.t(.glossaryImportSource), selection: $selectedGlossaryImportSourceID) {
                    ForEach(GlossaryImportSource.availableSources) { source in
                        Text(localizedGlossarySourceName(source)).tag(source.id)
                    }
                }
                .pickerStyle(.menu)

                Text(selectedGlossaryImportSource.detail)
                    .font(.caption)
                    .foregroundStyle(.secondary)

                if selectedGlossaryImportSourceRequiresURL {
                    TextField(appState.t(.glossaryImportLinkPlaceholder), text: $glossaryImportURLString)
                        .textFieldStyle(.roundedBorder)
                        .accessibilityLabel(appState.t(.glossaryImportLink))
                }

                Stepper("\(appState.t(.importLimit)): \(glossaryImportLimit)", value: $glossaryImportLimit, in: 1...2_000, step: 50)

                HStack {
                    Button(appState.t(.downloadAndImport)) {
                        Task { await importSelectedGlossarySource() }
                    }
                    .disabled(appState.isImportingGlossary || !canImportSelectedGlossarySource)

                    Button(appState.t(.importFromFile)) {
                        showingGlossaryFileImporter = true
                    }
                    .disabled(appState.isImportingGlossary)

                    if appState.isImportingGlossary {
                        ProgressView()
                            .controlSize(.small)
                        Text(appState.t(.importingGlossary))
                            .font(.caption)
                            .foregroundStyle(.secondary)
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

            ForEach(appState.settings.glossaryEntries) { entry in
                HStack {
                    Text(entry.sourceTerm)
                        .font(.callout.weight(.medium))
                    Image(systemName: "arrow.right")
                        .foregroundStyle(.secondary)
                    Text(entry.targetTerm.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? appState.t(.preserveOriginalTerm) : entry.targetTerm)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Button {
                        appState.deleteGlossaryEntry(entry)
                    } label: {
                        Image(systemName: "trash")
                    }
                    .buttonStyle(.plain)
                    .help(appState.t(.deleteTerm))
                }
            }
        }
        .fileImporter(
            isPresented: $showingGlossaryFileImporter,
            allowedContentTypes: glossaryImportContentTypes,
            allowsMultipleSelection: false
        ) { result in
            handleGlossaryFileImporterResult(result)
        }
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

    @MainActor
    private func importSelectedGlossarySource() async {
        glossaryImportInputMessage = ""
        let source = selectedGlossaryImportSource
        switch source.kind {
        case .builtIn(let url):
            await appState.importGlossary(from: url, sourceName: localizedGlossarySourceName(source), importLimit: glossaryImportLimit)
        case .customURL, .localFile:
            guard let url = GlossaryImportURLValidator.remoteURL(from: glossaryImportURLString) else {
                glossaryImportInputMessage = appState.t(.httpsLinksOnly)
                return
            }
            await appState.importGlossary(from: url, sourceName: localizedGlossarySourceName(source), importLimit: glossaryImportLimit)
        }
    }

    private func handleGlossaryFileImporterResult(_ result: Result<[URL], Error>) {
        glossaryImportInputMessage = ""
        switch result {
        case .success(let urls):
            guard let url = urls.first else { return }
            let didStartAccessing = url.startAccessingSecurityScopedResource()
            Task {
                await appState.importGlossary(fromLocalFile: url, sourceName: url.lastPathComponent, importLimit: glossaryImportLimit)
                if didStartAccessing {
                    url.stopAccessingSecurityScopedResource()
                }
            }
        case .failure(let error):
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
                    Task { await appState.runPreflightTest() }
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
                    appState.clearLogs()
                } label: {
                    Label(appState.t(.clear), systemImage: "trash")
                }
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 10)

            Divider()

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
                if !step.message.isEmpty {
                    Text(step.message)
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
