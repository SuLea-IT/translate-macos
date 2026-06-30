import Foundation
import Combine
import SwiftUI
import AppKit
import CoreAudio

@MainActor
final class AppState: ObservableObject {
    private static let apiKeySaveDebounceNanoseconds: UInt64 = 750_000_000
    private static let settingsSaveDebounceNanoseconds: UInt64 = 750_000_000
    private static let transcriptSaveDebounceNanoseconds: UInt64 = 750_000_000
    private static let maxTranscriptDraftCharacters = 4_000
    private static let maxPendingOriginalSentences = 120
    private static let maxPendingOriginalSentenceCharacters = 1_000

    private enum RuntimeControlRequest {
        case toggle
        case start
        case stop
    }

    @Published private(set) var settings: AppSettings {
        didSet {
            scheduleSettingsSaveIfNeeded(oldValue: oldValue)
            rebuildRunningSessionIfNeeded(oldValue: oldValue)
            configureGlobalShortcutsIfNeeded(oldValue: oldValue)
            updateAudioPlayerVolumeIfNeeded(oldValue: oldValue)
            updateUsageControlSettingsIfNeeded(oldValue: oldValue)
            refreshSetupChecklistIfNeeded(oldValue: oldValue)
        }
    }
    @Published private(set) var captions: [CaptionLine] = []
    @Published private(set) var captionDraft = ""
    @Published private(set) var isRunning = false
    @Published private(set) var statusMessage = "Ready"
    @Published private(set) var statusLevel: LiveStatusLevel = .stopped
    @Published private(set) var transcriptSessions: [TranscriptSession] = []
    @Published private(set) var logs: [LogEntry] = []
    @Published var showSetupSheet = false
    @Published private(set) var availableMicrophones: [AudioDevice] = []
    @Published private(set) var audioLevel: Float = 0.0
    @Published private(set) var setupChecklist: SetupChecklistState = .initial
    @Published private(set) var currentUserFacingError: UserFacingError?
    @Published private(set) var currentDiagnosticIssue: DiagnosticIssue?
    @Published private(set) var detectedSourceLanguageCode: String?
    @Published private(set) var preflightTestReport: PreflightTestReport = .idle
    @Published private(set) var isRunningPreflightTest = false
    @Published private(set) var glossaryImportMessage = ""
    @Published private(set) var isImportingGlossary = false
    @Published private(set) var glossaryImportProgress: GlossaryImportProgress?
    @Published private(set) var usageSnapshot = LiveUsageSnapshot()
    
    var openWindowAction: OpenWindowAction?

    
    private var propertyListenerBlock: AudioObjectPropertyListenerBlock?

    var isProviderConfigured: Bool {
        !settings.apiKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    var sourceLanguageDisplayText: String {
        if let sourceLanguageCode = settings.sourceLanguageCode, !sourceLanguageCode.isEmpty {
            return TranslationLanguage.name(for: sourceLanguageCode)
        }
        if let detectedSourceLanguageCode, !detectedSourceLanguageCode.isEmpty {
            return settings.interfaceLanguage.localized(.detectedSourceLanguage, arguments: [TranslationLanguage.name(for: detectedSourceLanguageCode)])
        }
        return settings.interfaceLanguage.localized(.autoDetectLanguage)
    }

    var languagePairDisplayText: String {
        "\(sourceLanguageDisplayText) → \(TranslationLanguage.name(for: settings.targetLanguageCode))"
    }


    private let settingsURL: URL
    private let transcriptsURL: URL
    private let usageLedgerURL: URL
    private var client: GeminiLiveTranslateClient?
    private var microphoneCapture: MicrophoneCapture?
    private var screenCapture: ScreenAudioCapture?
    private let audioPlayer = PCM16AudioPlayer()
    private let providerHealthService = ProviderHealthService.geminiDefault
    private let permissionStatusService = PermissionStatusService()
    private let systemSettingsNavigator = SystemSettingsNavigator()
    private let apiKeyStore: APIKeyStore
    private let globalShortcutRegistrar: GlobalShortcutRegistering
    private let glossaryImportService: GlossaryImportService
    private var runtimeControlTask: Task<Void, Never>?
    private var pendingRuntimeControlRequest: RuntimeControlRequest?
    private var restartTask: Task<Void, Never>?
    private let connectionRecoveryPolicy = ConnectionRecoveryPolicy.default
    private var reconnectTask: Task<Void, Never>?
    private var connectionStopTask: Task<Void, Never>?
    private var usageResumeTask: Task<Void, Never>?
    private var setupChecklistRefreshTask: Task<Void, Never>?
    private var audioSendTask: Task<Void, Never>?
    private var apiKeySaveTask: Task<Void, Never>?
    private var settingsSaveTask: Task<Void, Never>?
    private var preflightTestTask: Task<Void, Never>?
    private var temporaryTestCaptionTask: Task<Void, Never>?
    private var temporaryTestCaptionPreviousDraft: String?
    private var glossaryImportTask: Task<Void, Never>?
    private var transcriptSaveTask: Task<Void, Never>?
    private var glossaryImportGeneration = UUID()
    private var pendingAudioSendChunks = 0
    private let maxPendingAudioSendChunks = 120
    private var audioSendGeneration = UUID()
    private var audioCaptureGeneration = UUID()
    private var lastAudioSendBackpressureLogAt = Date.distantPast
    private var reconnectAttempts = 0
    private var userInitiatedStop = false
    private var currentSessionID: UUID?
    private var currentTranscriptLines: [TranscriptLine] = []
    private var usageEngine: UsageControlEngine
    private var micChunkCount = 0
    private var screenChunkCount = 0
    private var sentChunkCount = 0
    private var lastAudioStatusAt = Date.distantPast
    
    private var originalDraft = ""
    private var completedOriginalSentences: [String] = []
    private var pendingAPIKeyForKeychain: String?
    private var cachedProviderHealthAPIKey: String?
    private var cachedProviderHealthStatus: ProviderHealthStatus?

    init(
        apiKeyStore: APIKeyStore = .liveBuddy,
        globalShortcutRegistrar: GlobalShortcutRegistering = CarbonGlobalShortcutRegistrar(),
        glossaryImportService: GlossaryImportService = GlossaryImportService()
    ) {
        self.apiKeyStore = apiKeyStore
        self.globalShortcutRegistrar = globalShortcutRegistrar
        self.glossaryImportService = glossaryImportService
        let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
            .appendingPathComponent("LiveBuddy", isDirectory: true)
        settingsURL = support.appendingPathComponent("settings.json")
        transcriptsURL = support.appendingPathComponent("transcripts.json")
        usageLedgerURL = support.appendingPathComponent("usage-ledger.json")

        var loadedSettings: AppSettings
        if let data = try? Data(contentsOf: settingsURL),
           let decoded = try? JSONDecoder().decode(AppSettings.self, from: data) {
            loadedSettings = decoded
        } else {
            loadedSettings = AppSettings()
        }

        var shouldRewriteSettings = false
        let legacyAPIKey = loadedSettings.apiKey.trimmingCharacters(in: .whitespacesAndNewlines)
        do {
            if let storedAPIKey = try apiKeyStore.read(), !storedAPIKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                loadedSettings.apiKey = storedAPIKey
            } else if !legacyAPIKey.isEmpty {
                try apiKeyStore.save(legacyAPIKey)
                loadedSettings.apiKey = legacyAPIKey
                shouldRewriteSettings = true
            }
        } catch {
            loadedSettings.apiKey = legacyAPIKey
        }

        settings = loadedSettings
        let now = Date()
        usageEngine = UsageControlEngine(
            settings: loadedSettings.usageControls,
            now: now,
            ledger: Self.loadUsageLedger(from: usageLedgerURL, now: now)
        )
        usageSnapshot = usageEngine.snapshot
        loadTranscriptSessions()
        appendLog("App ready", level: .info)
        if shouldRewriteSettings {
            saveSettingsImmediately()
        }
        updateAudioPlayerVolume()
        refreshAvailableMicrophones()
        refreshSetupChecklist()
        startListeningForDeviceChanges()
        configureGlobalShortcuts()
    }

    func start() async {
        guard !isRunning else { return }
        cancelPreflightTest()

        let preflight = await runStartPreflight()
        if case .blocked(let issue) = preflight {
            let error = UserFacingError.from(blockingIssues: [issue])
            currentUserFacingError = error
            setDiagnosticIssue(DiagnosticClassifier.from(blockingIssue: issue))
            updateStatus(error.map { settings.interfaceLanguage.localized($0.titleKey) } ?? settings.interfaceLanguage.localized(.cannotStart), level: .error, log: true)
            openSettingsWindow()
            showSetupSheet = true
            return
        }

        currentUserFacingError = nil
        setDiagnosticIssue(nil)
        userInitiatedStop = false
        reconnectAttempts = 0
        reconnectTask?.cancel()
        reconnectTask = nil
        connectionStopTask?.cancel()
        connectionStopTask = nil
        usageResumeTask?.cancel()
        usageResumeTask = nil
        resetAudioSendPipeline()
        audioCaptureGeneration = UUID()
        detectedSourceLanguageCode = nil
        NotificationCenter.default.post(name: .showCaptionWindow, object: nil)

        captions.removeAll()
        captionDraft = ""
        originalDraft = ""
        completedOriginalSentences.removeAll()
        currentTranscriptLines.removeAll()
        resetAudioCounters()
        resetUsageSession()
        updateStatus("Connecting", level: .connecting, log: true)

        let client = makeGeminiClient()

        do {
            try await client.connect()
            self.client = client
            try await startCapture()
            beginTranscriptSession()
            isRunning = true
            updateStatus("Listening", level: .running, log: true)
        } catch {
            await stop()
            let diagnostic = DiagnosticClassifier.from(error: error, context: .startup)
            setDiagnosticIssue(diagnostic)
            updateStatus(settings.interfaceLanguage.localized(diagnostic.titleKey), level: .error, log: true)
        }
    }

    func stop() async {
        await stop(cancelPendingRestart: true)
    }

    private func stop(cancelPendingRestart: Bool) async {
        userInitiatedStop = true
        reconnectTask?.cancel()
        reconnectTask = nil
        connectionStopTask?.cancel()
        connectionStopTask = nil
        usageResumeTask?.cancel()
        usageResumeTask = nil
        reconnectAttempts = 0
        if cancelPendingRestart {
            restartTask?.cancel()
            restartTask = nil
        }
        cancelPreflightTest()
        resetAudioSendPipeline()
        audioCaptureGeneration = UUID()
        microphoneCapture?.stop()
        microphoneCapture = nil
        await screenCapture?.stop()
        screenCapture = nil
        client?.close()
        client = nil
        audioPlayer.stop()
        finishTranscriptSession()
        saveUsageLedger()
        audioLevel = 0.0
        isRunning = false
        updateStatus("Stopped", level: .stopped, log: true)
    }

    func requestStart() {
        scheduleRuntimeControl(.start)
    }

    func requestStop() {
        scheduleRuntimeControl(.stop)
    }

    func toggle() {
        scheduleRuntimeControl(.toggle)
    }

    private func scheduleRuntimeControl(_ request: RuntimeControlRequest) {
        if runtimeControlTask != nil {
            pendingRuntimeControlRequest = request
            return
        }
        runtimeControlTask = Task { @MainActor [weak self] in
            guard let self else { return }
            var currentRequest = request
            await self.performRuntimeControl(currentRequest)
            guard !Task.isCancelled else { return }
            while let pendingRequest = self.pendingRuntimeControlRequest {
                self.pendingRuntimeControlRequest = nil
                currentRequest = pendingRequest
                await self.performRuntimeControl(currentRequest)
                guard !Task.isCancelled else { return }
            }
            self.runtimeControlTask = nil
        }
    }

    private func performRuntimeControl(_ request: RuntimeControlRequest) async {
        switch request {
        case .toggle:
            if isRunning {
                await stop()
            } else {
                await start()
            }
        case .start:
            await start()
        case .stop:
            await stop()
        }
    }

    func flushPendingStateBeforeTermination() {
        saveAPIKeyImmediately()
        saveSettingsImmediately()
        saveTranscriptSessionsImmediately()
        saveUsageLedger()
    }

    func binding<Value>(_ keyPath: WritableKeyPath<AppSettings, Value>) -> Binding<Value> {
        Binding(
            get: { self.settings[keyPath: keyPath] },
            set: { [weak self] value in
                DispatchQueue.main.async {
                    self?.updateSetting(keyPath, to: value)
                }
            }
        )
    }

    func apiKeyBinding() -> Binding<String> {
        Binding(
            get: { self.settings.apiKey },
            set: { [weak self] value in
                DispatchQueue.main.async {
                    self?.updateAPIKey(value)
                }
            }
        )
    }

    func globalShortcutsEnabledBinding() -> Binding<Bool> {
        Binding(
            get: { self.settings.globalShortcutsEnabled },
            set: { [weak self] value in
                DispatchQueue.main.async {
                    self?.updateGlobalShortcutsEnabled(value)
                }
            }
        )
    }

    func updateGlobalShortcutsEnabled(_ value: Bool) {
        settings.globalShortcutsEnabled = value
    }

    @discardableResult
    func updateGlobalShortcut(_ shortcut: GlobalShortcut) -> GlobalShortcutValidationResult {
        var next = settings.globalShortcuts
        let result = next.update(shortcut)
        guard result == .valid else { return result }
        settings.globalShortcuts = next
        return .valid
    }

    func clearGlobalShortcut(_ action: GlobalShortcutAction) {
        var next = settings.globalShortcuts
        next.clear(action)
        settings.globalShortcuts = next
    }

    func resetGlobalShortcut(_ action: GlobalShortcutAction) {
        var next = settings.globalShortcuts
        next.reset(action)
        settings.globalShortcuts = next
    }

    func resetAllGlobalShortcuts() {
        var next = settings.globalShortcuts
        next.resetAll()
        settings.globalShortcuts = next
    }

    func clearDiagnosticIssue() {
        currentDiagnosticIssue = nil
    }

    func performDiagnosticRecoveryAction(_ action: DiagnosticRecoveryAction) {
        switch action {
        case .openProviderSettings:
            openSettingsWindow()
        case .openMicrophoneSettings:
            openMicrophoneSettings()
        case .openScreenRecordingSettings:
            openScreenRecordingSettings()
        case .retry:
            requestStart()
        }
    }

    func updateAPIKey(_ apiKey: String) {
        invalidateCachedProviderHealthStatusIfNeeded(for: apiKey)
        settings.apiKey = apiKey
        scheduleAPIKeySave(apiKey)
    }

    private func scheduleAPIKeySave(_ apiKey: String) {
        pendingAPIKeyForKeychain = apiKey
        apiKeySaveTask?.cancel()
        apiKeySaveTask = Task { @MainActor [weak self] in
            do {
                try await Task.sleep(nanoseconds: Self.apiKeySaveDebounceNanoseconds)
            } catch {
                self?.apiKeySaveTask = nil
                return
            }
            guard !Task.isCancelled else {
                self?.apiKeySaveTask = nil
                return
            }
            guard let self else { return }
            self.savePendingAPIKeyToKeychain()
            self.apiKeySaveTask = nil
        }
    }

    private func saveAPIKeyImmediately() {
        pendingAPIKeyForKeychain = settings.apiKey
        apiKeySaveTask?.cancel()
        apiKeySaveTask = nil
        savePendingAPIKeyToKeychain()
    }

    private func savePendingAPIKeyToKeychain() {
        guard let apiKey = pendingAPIKeyForKeychain else { return }
        do {
            try apiKeyStore.save(apiKey)
            pendingAPIKeyForKeychain = nil
        } catch {
            let issue = DiagnosticClassifier.storage(.settingsSaveFailed, underlyingMessage: error.localizedDescription)
            setDiagnosticIssue(issue)
            updateStatus(settings.interfaceLanguage.localized(issue.titleKey), level: .error, log: true)
        }
    }

    func updateSetting<Value>(_ keyPath: WritableKeyPath<AppSettings, Value>, to value: Value) {
        settings[keyPath: keyPath] = value
    }

    func addGlossaryEntry(sourceTerm: String, targetTerm: String) {
        settings.glossaryEntries = GlossaryEntryEditor().add(
            sourceTerm: sourceTerm,
            targetTerm: targetTerm,
            to: settings.glossaryEntries
        )
    }

    func deleteGlossaryEntry(_ entry: GlossaryEntry) {
        settings.glossaryEntries = GlossaryEntryEditor().delete(entry, from: settings.glossaryEntries)
    }

    func clearGlossaryEntries() {
        guard !settings.glossaryEntries.isEmpty else { return }
        settings.glossaryEntries = GlossaryEntryEditor().deleteAll(from: settings.glossaryEntries)
        glossaryImportMessage = settings.interfaceLanguage.localized(.glossaryCleared)
        updateStatus(glossaryImportMessage, level: isRunning ? .running : .stopped, log: true)
    }

    func startGlossaryImport(from url: URL, sourceName: String, importLimit: Int) {
        guard glossaryImportTask == nil else { return }
        let generation = UUID()
        glossaryImportGeneration = generation
        glossaryImportTask = Task { @MainActor [weak self] in
            defer {
                if self?.glossaryImportGeneration == generation {
                    self?.glossaryImportTask = nil
                }
            }
            await self?.importGlossary(from: url, sourceName: sourceName, importLimit: importLimit)
        }
    }

    func startGlossaryImportFromLocalFile(url: URL, sourceName: String, importLimit: Int) {
        guard glossaryImportTask == nil else { return }
        let generation = UUID()
        glossaryImportGeneration = generation
        glossaryImportTask = Task { @MainActor [weak self] in
            defer {
                if self?.glossaryImportGeneration == generation {
                    self?.glossaryImportTask = nil
                }
            }
            let didStartAccessing = url.startAccessingSecurityScopedResource()
            defer {
                if didStartAccessing {
                    url.stopAccessingSecurityScopedResource()
                }
            }
            await self?.importGlossary(fromLocalFile: url, sourceName: sourceName, importLimit: importLimit)
        }
    }

    func cancelGlossaryImport() {
        glossaryImportGeneration = UUID()
        glossaryImportTask?.cancel()
        glossaryImportTask = nil
        isImportingGlossary = false
        glossaryImportProgress = nil
    }

    func importGlossary(from url: URL, sourceName: String, importLimit: Int) async {
        guard !isImportingGlossary else { return }
        let generation = glossaryImportGeneration
        isImportingGlossary = true
        glossaryImportProgress = .indeterminate
        defer {
            if glossaryImportGeneration == generation {
                isImportingGlossary = false
                glossaryImportProgress = nil
            }
        }

        do {
            let result = try await glossaryImportService.importRemote(
                url: url,
                sourceName: sourceName,
                existingEntries: settings.glossaryEntries,
                options: glossaryImportOptions(importLimit: importLimit),
                progress: { [weak self] progress in
                    await MainActor.run {
                        guard self?.glossaryImportGeneration == generation else { return }
                        self?.glossaryImportProgress = progress
                    }
                }
            )
            guard !Task.isCancelled else { return }
            guard glossaryImportGeneration == generation else { return }
            applyGlossaryImportResult(result)
        } catch {
            guard glossaryImportGeneration == generation else { return }
            handleGlossaryImportFailure(error)
        }
    }

    func importGlossary(fromLocalFile url: URL, sourceName: String, importLimit: Int) async {
        guard !isImportingGlossary else { return }
        let generation = glossaryImportGeneration
        isImportingGlossary = true
        glossaryImportProgress = .indeterminate
        defer {
            if glossaryImportGeneration == generation {
                isImportingGlossary = false
                glossaryImportProgress = nil
            }
        }

        do {
            let service = glossaryImportService
            let existingEntries = settings.glossaryEntries
            let options = glossaryImportOptions(importLimit: importLimit)
            let importTask = Task.detached(priority: .userInitiated) {
                try service.importLocalFile(
                    url: url,
                    sourceName: sourceName,
                    existingEntries: existingEntries,
                    options: options
                )
            }
            let result = try await withTaskCancellationHandler {
                try await importTask.value
            } onCancel: {
                importTask.cancel()
            }
            guard !Task.isCancelled else { return }
            guard glossaryImportGeneration == generation else { return }
            applyGlossaryImportResult(result)
        } catch {
            guard glossaryImportGeneration == generation else { return }
            handleGlossaryImportFailure(error)
        }
    }

    private func glossaryImportOptions(importLimit: Int) -> GlossaryImportOptions {
        GlossaryImportOptions(
            sourceLanguageCode: settings.sourceLanguageCode ?? "en",
            targetLanguageCode: settings.targetLanguageCode,
            importLimit: importLimit
        )
    }

    private func applyGlossaryImportResult(_ result: GlossaryImportResult) {
        settings.glossaryEntries = GlossaryImportMerger().merge(existing: settings.glossaryEntries, imported: result.entries)
        glossaryImportMessage = settings.interfaceLanguage.localized(
            .importedTermsResult,
            arguments: [result.added, result.sourceName, result.skippedDuplicate]
        )
        updateStatus(glossaryImportMessage, level: isRunning ? .running : .stopped, log: true)
        refreshSetupChecklist()
    }

    private func handleGlossaryImportFailure(_ error: Error) {
        if error is CancellationError {
            glossaryImportMessage = ""
            return
        }
        if let importError = error as? GlossaryImportError {
            switch importError {
            case .unsupportedURL:
                glossaryImportMessage = settings.interfaceLanguage.localized(.httpsLinksOnly)
            case .unsupportedFormat:
                glossaryImportMessage = settings.interfaceLanguage.localized(.unsupportedGlossaryFormat)
            case .emptyImport:
                glossaryImportMessage = settings.interfaceLanguage.localized(.glossaryImportEmpty)
            case .downloadFailed(let message):
                let baseMessage = settings.interfaceLanguage.localized(.glossaryDownloadFailed)
                let detail = message.trimmingCharacters(in: .whitespacesAndNewlines)
                glossaryImportMessage = detail.isEmpty ? baseMessage : "\(baseMessage): \(detail)"
            case .fileTooLarge, .parseFailed:
                glossaryImportMessage = importError.localizedDescription
            }
        } else {
            glossaryImportMessage = error.localizedDescription
        }
        updateStatus(glossaryImportMessage, level: .error, log: true)
    }

    func configureGlobalShortcuts() {
        guard settings.globalShortcutsEnabled else {
            globalShortcutRegistrar.unregisterAll()
            return
        }

        let results = globalShortcutRegistrar.register(settings.globalShortcuts.enabledShortcuts) { [weak self] action in
            Task { @MainActor [weak self] in
                self?.performGlobalShortcut(action)
            }
        }

        for result in results {
            if case .failed(let code) = result.status {
                appendLog("Global shortcut \(result.shortcut.displayText) failed to register: \(code)", level: .error)
            }
        }
    }

    private func configureGlobalShortcutsIfNeeded(oldValue: AppSettings) {
        let shortcutsChanged =
            oldValue.globalShortcutsEnabled != settings.globalShortcutsEnabled ||
            oldValue.globalShortcuts != settings.globalShortcuts
        guard shortcutsChanged else { return }
        configureGlobalShortcuts()
    }

    func performGlobalShortcut(_ action: GlobalShortcutAction) {
        switch action {
        case .toggleTranslation:
            toggle()
        case .showCaptionWindow:
            NotificationCenter.default.post(name: .showCaptionWindow, object: nil)
        case .toggleMute:
            updateSetting(\.audioPlayerMuted, to: !settings.audioPlayerMuted)
        }
    }

    private func refreshSetupChecklistIfNeeded(oldValue: AppSettings) {
        let setupInputsChanged =
            oldValue.apiKey != settings.apiKey ||
            oldValue.audioSource != settings.audioSource
        guard setupInputsChanged else { return }
        refreshSetupChecklist()
    }

    func refreshSetupChecklist() {
        setupChecklistRefreshTask?.cancel()
        setupChecklistRefreshTask = Task { [weak self] in
            guard let self else { return }
            let permissions = await self.permissionStatusService.refreshStatuses()
            guard !Task.isCancelled else { return }
            self.setupChecklist = SetupChecklistState.derive(
                audioSource: self.settings.audioSource,
                apiKey: self.providerHealthStatusForCurrentKey,
                microphone: permissions.microphone,
                screenRecording: permissions.screenRecording
            )
            self.setupChecklistRefreshTask = nil
        }
    }

    func runStartPreflight() async -> SetupPreflightResult {
        let permissions = await permissionStatusService.refreshStatuses()
        let checklist = SetupChecklistState.derive(
            audioSource: settings.audioSource,
            apiKey: providerHealthStatusForCurrentKey,
            microphone: permissions.microphone,
            screenRecording: permissions.screenRecording
        )
        setupChecklist = checklist
        return SetupPreflightResult.from(checklist)
    }

    func runPreflightTest() async {
        guard !isRunning else {
            preflightTestReport = PreflightTestReport(steps: [
                PreflightTestStep(id: .apiKey, state: .failed, message: "Stop translation before running diagnostics")
            ])
            return
        }
        guard !isRunningPreflightTest else { return }
        isRunningPreflightTest = true
        defer { isRunningPreflightTest = false }

        let runner = PreflightTestRunner.live(settings: settings) { [weak self] in
            await self?.showTemporaryTestCaption()
        }
        _ = await runner.run(settings: settings) { [weak self] report in
            guard !Task.isCancelled else { return }
            self?.preflightTestReport = report
        }
        guard !Task.isCancelled else { return }
        refreshSetupChecklist()
    }

    func startPreflightTest() {
        guard preflightTestTask == nil else { return }
        preflightTestTask = Task { @MainActor [weak self] in
            await self?.runPreflightTest()
            guard !Task.isCancelled else { return }
            self?.preflightTestTask = nil
        }
    }

    func showTemporaryTestCaption() async {
        temporaryTestCaptionTask?.cancel()
        temporaryTestCaptionTask = nil
        restoreTemporaryTestCaptionIfNeeded()
        let previousDraft = captionDraft
        temporaryTestCaptionPreviousDraft = previousDraft
        NotificationCenter.default.post(name: .showCaptionWindow, object: nil)
        captionDraft = settings.interfaceLanguage.localized(.subtitleTestMessage)
        temporaryTestCaptionTask = Task { @MainActor [weak self] in
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            guard !Task.isCancelled else { return }
            guard let self else { return }
            self.restoreTemporaryTestCaptionIfNeeded()
            temporaryTestCaptionTask = nil
        }
        await temporaryTestCaptionTask?.value
    }

    private func cancelPreflightTest() {
        preflightTestTask?.cancel()
        preflightTestTask = nil
        temporaryTestCaptionTask?.cancel()
        temporaryTestCaptionTask = nil
        restoreTemporaryTestCaptionIfNeeded()
        isRunningPreflightTest = false
    }

    private func restoreTemporaryTestCaptionIfNeeded() {
        guard let previousDraft = temporaryTestCaptionPreviousDraft else { return }
        if !isRunning {
            captionDraft = previousDraft
        }
        temporaryTestCaptionPreviousDraft = nil
    }

    func openMicrophoneSettings() {
        systemSettingsNavigator.open(.microphone)
    }

    func openScreenRecordingSettings() {
        systemSettingsNavigator.open(.screenRecording)
    }

    private var providerHealthStatusForCurrentKey: ProviderHealthStatus {
        let trimmed = settings.apiKey.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return .missing }
        if cachedProviderHealthAPIKey == trimmed,
           let cachedProviderHealthStatus {
            return cachedProviderHealthStatus
        }
        return .unchecked
    }

    func clearLogs() {
        logs.removeAll()
    }

    func saveSubtitleScreenFrame(_ frame: NSRect) {
        let saved = SubtitleScreenFrame(
            x: frame.origin.x,
            y: frame.origin.y,
            width: frame.size.width,
            height: frame.size.height
        )
        guard settings.subtitleScreenFrame != saved else { return }
        settings.subtitleScreenFrame = saved
    }

    func openSettingsWindow() {
        NSApp.activate(ignoringOtherApps: true)
        if let openWindowAction {
            openWindowAction(id: "settings")
            return
        }
        for window in NSApp.windows where window.title == "Settings" || window.identifier?.rawValue.contains("settings") == true {
            window.makeKeyAndOrderFront(nil)
            return
        }
        NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
    }

    func verifyGeminiToken() async throws {
        try Task.checkCancellation()
        let status = await providerHealthService.verify(apiKey: settings.apiKey)
        try Task.checkCancellation()
        rememberProviderHealthStatus(status, apiKey: settings.apiKey)
        updateSetupChecklist(apiKeyStatus: status)
        switch status {
        case .valid:
            setDiagnosticIssue(nil)
            return
        case .missing:
            setDiagnosticIssue(DiagnosticClassifier.from(providerStatus: status))
            throw NSError(domain: "LiveBuddy", code: 400, userInfo: [NSLocalizedDescriptionKey: "API Key cannot be empty"])
        case .invalid(let message, _):
            setDiagnosticIssue(DiagnosticClassifier.from(providerStatus: status))
            throw NSError(domain: "LiveBuddy", code: 403, userInfo: [NSLocalizedDescriptionKey: message])
        case .failed(let message, _):
            setDiagnosticIssue(DiagnosticClassifier.from(providerStatus: status))
            throw NSError(domain: "LiveBuddy", code: 500, userInfo: [NSLocalizedDescriptionKey: message])
        case .unchecked, .checking:
            setDiagnosticIssue(DiagnosticClassifier.from(providerStatus: status))
            throw NSError(domain: "LiveBuddy", code: 500, userInfo: [NSLocalizedDescriptionKey: "Verification failed"])
        }
    }

    private func rememberProviderHealthStatus(_ status: ProviderHealthStatus, apiKey: String) {
        let trimmed = apiKey.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            cachedProviderHealthAPIKey = nil
            cachedProviderHealthStatus = nil
            return
        }
        cachedProviderHealthAPIKey = trimmed
        cachedProviderHealthStatus = status
    }

    private func invalidateCachedProviderHealthStatusIfNeeded(for apiKey: String) {
        let trimmed = apiKey.trimmingCharacters(in: .whitespacesAndNewlines)
        guard cachedProviderHealthAPIKey != trimmed else { return }
        cachedProviderHealthAPIKey = nil
        cachedProviderHealthStatus = nil
    }

    private func updateSetupChecklist(apiKeyStatus: ProviderHealthStatus) {
        setupChecklist = SetupChecklistState.derive(
            audioSource: settings.audioSource,
            apiKey: apiKeyStatus,
            microphone: permissionStatus(from: setupChecklist.microphone),
            screenRecording: permissionStatus(from: setupChecklist.screenRecording)
        )
    }

    private func permissionStatus(from item: PermissionChecklistItem) -> PermissionStatus {
        PermissionStatus(
            requirement: item.requirement,
            state: item.permissionState,
            checkedAt: item.checkedAt
        )
    }


    private func makeGeminiClient() -> GeminiLiveTranslateClient {
        let client = GeminiLiveTranslateClient(settings: settings)
        let audioPlayer = self.audioPlayer
        client.onInputTranscript = { [weak self, weak client] text, language in
            Task { @MainActor [weak self, weak client] in
                guard let self, let client, self.client === client else { return }
                if let language, !language.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    self.detectedSourceLanguageCode = language
                }
                self.appendLog("Input\(language.map { " [\($0)]" } ?? ""): \(text)", level: .info)
                self.appendOriginalText(text)
            }
        }
        client.onOutputTranscript = { [weak self, weak client] text, language in
            Task { @MainActor [weak self, weak client] in
                guard let self, let client, self.client === client else { return }
                self.appendCaption(text, language: language, kind: .output)
            }
        }
        client.onAudioChunk = { [weak self, weak client, audioPlayer] data in
            Task { @MainActor [weak self, weak client] in
                guard let self, let client, self.client === client else { return }
                audioPlayer.playPCM16(data, sampleRate: 24_000)
            }
        }
        client.onStatus = { [weak self, weak client] message in
            Task { @MainActor [weak self, weak client] in
                guard let self, let client, self.client === client else { return }
                self.handleClientStatus(message)
            }
        }
        client.onConnectionEvent = { [weak self, weak client] event in
            Task { @MainActor [weak self, weak client] in
                guard let self, let client, self.client === client else { return }
                self.handleConnectionEvent(event)
            }
        }
        return client
    }

    private func handleConnectionEvent(_ event: LiveConnectionEvent) {
        switch event {
        case .socketOpened, .sessionReady:
            return
        case .disconnected, .socketClosed, .sendFailed, .serverError, .parseFailed:
            break
        }

        guard isRunning, !userInitiatedStop else { return }

        if let issue = DiagnosticClassifier.from(connectionEvent: event) {
            setDiagnosticIssue(issue)
        }

        if event.isRecoverable {
            scheduleReconnect(after: event)
        } else {
            updateStatus(
                settings.interfaceLanguage.localized(.connectionProviderError, arguments: [event.statusMessage]),
                level: .error,
                log: true
            )
            scheduleStopRuntimeAfterConnectionFailure()
        }
    }

    private func scheduleReconnect(after event: LiveConnectionEvent) {
        guard reconnectTask == nil else { return }
        reconnectAttempts += 1

        guard reconnectAttempts <= connectionRecoveryPolicy.maxAttempts else {
            updateStatus(
                settings.interfaceLanguage.localized(.connectionReconnectFailed, arguments: [connectionRecoveryPolicy.maxAttempts]),
                level: .error,
                log: true
            )
            scheduleStopRuntimeAfterConnectionFailure()
            return
        }

        let delay = connectionRecoveryPolicy.delay(forAttempt: reconnectAttempts)
        let message = settings.interfaceLanguage.localized(
            .connectionReconnecting,
            arguments: reconnectingArguments(attempt: reconnectAttempts, maxAttempts: connectionRecoveryPolicy.maxAttempts, delay: delay)
        )
        updateStatus(message, level: .connecting, log: true)
        appendLog(event.statusMessage, level: .error)

        let oldClient = client
        resetAudioSendPipeline()
        client = nil
        reconnectTask = Task { [weak self] in
            let nanoseconds = UInt64(max(delay, 0) * 1_000_000_000)
            do {
                try await Task.sleep(nanoseconds: nanoseconds)
            } catch {
                return
            }
            guard !Task.isCancelled else { return }
            await self?.reconnectGeminiClient()
        }
        oldClient?.close()
    }

    private func shouldContinueRuntimeConnection() -> Bool {
        !Task.isCancelled && isRunning && !userInitiatedStop
    }

    private func discardAsyncClient(_ candidate: GeminiLiveTranslateClient) {
        if client === candidate {
            client = nil
        }
        candidate.close()
    }

    private func reconnectGeminiClient() async {
        guard shouldContinueRuntimeConnection() else {
            reconnectTask = nil
            return
        }

        let newClient = makeGeminiClient()
        do {
            try await newClient.connect()
            guard shouldContinueRuntimeConnection() else {
                discardAsyncClient(newClient)
                reconnectTask = nil
                return
            }
            client = newClient
            reconnectTask = nil
            reconnectAttempts = 0
            setDiagnosticIssue(nil)
            updateStatus(settings.interfaceLanguage.localized(.connectionRecovered), level: .running, log: true)
        } catch {
            newClient.close()
            guard shouldContinueRuntimeConnection() else {
                reconnectTask = nil
                return
            }
            reconnectTask = nil
            handleConnectionEvent(connectionEvent(from: error))
        }
    }

    private func scheduleStopRuntimeAfterConnectionFailure() {
        guard connectionStopTask == nil else { return }
        connectionStopTask = Task { @MainActor [weak self] in
            await self?.stopRuntimeAfterConnectionFailure()
            guard !Task.isCancelled else { return }
            self?.connectionStopTask = nil
        }
    }

    private func stopRuntimeAfterConnectionFailure() async {
        userInitiatedStop = true
        reconnectTask?.cancel()
        reconnectTask = nil
        restartTask?.cancel()
        restartTask = nil
        usageResumeTask?.cancel()
        usageResumeTask = nil
        reconnectAttempts = 0
        resetAudioSendPipeline()
        audioCaptureGeneration = UUID()
        microphoneCapture?.stop()
        microphoneCapture = nil
        await screenCapture?.stop()
        guard !Task.isCancelled else { return }
        screenCapture = nil
        client?.close()
        client = nil
        audioPlayer.stop()
        finishTranscriptSession()
        saveUsageLedger()
        audioLevel = 0.0
        isRunning = false
        connectionStopTask?.cancel()
        connectionStopTask = nil
    }

    private func connectionEvent(from error: Error) -> LiveConnectionEvent {
        guard let liveError = error as? LiveTranslateError else {
            return .disconnected(error.localizedDescription)
        }

        switch liveError {
        case .invalidAPIKey:
            return .serverError(liveError.localizedDescription)
        case .notConnected, .setupTimedOut:
            return .disconnected(liveError.localizedDescription)
        case .server(let message):
            return .serverError(message)
        case .invalidMessage, .unsupportedMessage:
            return .parseFailed(liveError.localizedDescription)
        case .socketClosed(let message):
            return .socketClosed(message)
        }
    }

    private func reconnectingArguments(attempt: Int, maxAttempts: Int, delay: TimeInterval) -> [CVarArg] {
        switch settings.interfaceLanguage {
        case .english, .spanish, .french, .german, .vietnamese:
            return [attempt, maxAttempts, delay]
        case .simplifiedChinese, .japanese, .korean:
            return [delay, attempt, maxAttempts]
        }
    }

    private func startCapture() async throws {
        let generation = audioCaptureGeneration
        if settings.audioSource == .microphone || settings.audioSource == .both {
            let mic = MicrophoneCapture(onAudioChunk: audioSink(source: .microphone, generation: generation))
            try await mic.start(selectedDeviceUID: settings.selectedMicrophoneDeviceUID)
            microphoneCapture = mic
            updateStatus("Microphone capture started", level: .connecting, log: true)
        }

        if settings.audioSource == .screen || settings.audioSource == .both {
            let screen = ScreenAudioCapture(
                onAudioChunk: audioSink(source: .screen, generation: generation),
                onStatus: { [weak self] message in
                    Task { @MainActor [weak self] in
                        guard self?.audioCaptureGeneration == generation else { return }
                        self?.updateStatus(message, level: .error, log: true)
                    }
                }
            )
            try await screen.start()
            screenCapture = screen
            updateStatus("Screen audio capture started", level: .connecting, log: true)
        }
    }

    private func audioSink(source: AudioSource, generation: UUID) -> @Sendable (Data) -> Void {
        { [weak self] data in
            Task { @MainActor [weak self] in
                guard let self, self.audioCaptureGeneration == generation else { return }
                let level = AppState.calculateRMS(data: data)
                self.handleCapturedAudio(data, source: source, level: level)
            }
        }
    }

    private func handleCapturedAudio(_ data: Data, source: AudioSource, level: Float) {
        let now = Date()
        recordAudioChunk(source: source, level: level)

        let chunk = BufferedAudioChunk(data: data, capturedAt: now)
        let decision = usageEngine.ingest(chunk: chunk, level: level, now: now)
        usageSnapshot = usageEngine.snapshot

        if let pauseReason = decision.pauseReason {
            enterUsagePause(reason: pauseReason)
            updateRunningUsageStatus(now: now, force: true)
            return
        }

        if decision.shouldResume {
            scheduleUsageResume(replayChunks: decision.replayChunks)
            updateRunningUsageStatus(now: now, force: true)
            return
        }

        if decision.shouldSend {
            if enqueueAudioSend(data) {
                sentChunkCount += 1
                usageEngine.markSent(chunk)
                usageSnapshot = usageEngine.snapshot
                saveUsageLedger()
            }
        }

        updateRunningUsageStatus(now: now)
    }

    private func recordAudioChunk(source: AudioSource, level: Float) {
        switch source {
        case .microphone:
            micChunkCount += 1
        case .screen:
            screenChunkCount += 1
        case .both:
            break
        }

        audioLevel = audioLevel * 0.7 + level * 0.3
    }

    private func updateRunningUsageStatus(now: Date, force: Bool = false) {
        guard force || now.timeIntervalSince(lastAudioStatusAt) >= 1 else { return }
        lastAudioStatusAt = now
        statusMessage = runningUsageStatusMessage()
        statusLevel = usageSnapshot.runtimeState == .resuming ? .connecting : .running
    }

    private func resetAudioCounters() {
        micChunkCount = 0
        screenChunkCount = 0
        sentChunkCount = 0
        lastAudioStatusAt = .distantPast
        audioLevel = 0.0
    }

    private func resetUsageSession() {
        let now = Date()
        usageEngine.resetSession(now: now, ledger: Self.loadUsageLedger(from: usageLedgerURL, now: now))
        usageSnapshot = usageEngine.snapshot
    }

    private func enqueueAudioSend(_ data: Data) -> Bool {
        guard !data.isEmpty, let client else { return false }
        guard pendingAudioSendChunks < maxPendingAudioSendChunks else {
            let now = Date()
            if now.timeIntervalSince(lastAudioSendBackpressureLogAt) >= 5 {
                lastAudioSendBackpressureLogAt = now
                appendLog("Audio send queue is full; dropping live audio chunks to keep latency bounded", level: .error)
            }
            return false
        }

        pendingAudioSendChunks += 1
        let generation = audioSendGeneration
        let previousTask = audioSendTask
        audioSendTask = Task { [weak self, client, data, previousTask, generation] in
            if let previousTask {
                await withTaskCancellationHandler {
                    await previousTask.value
                } onCancel: {
                    previousTask.cancel()
                }
            }
            defer {
                Task { @MainActor [weak self] in
                    guard let self else { return }
                    pendingAudioSendChunks = max(0, pendingAudioSendChunks - 1)
                    if pendingAudioSendChunks == 0, audioSendGeneration == generation {
                        audioSendTask = nil
                    }
                }
            }
            guard !Task.isCancelled else { return }
            let shouldSend = await MainActor.run { [weak self, client] in
                guard let self else { return false }
                return audioSendGeneration == generation && self.client === client
            }
            guard shouldSend else { return }
            await client.sendAudio(data)
        }
        return true
    }

    private func resetAudioSendPipeline() {
        audioSendGeneration = UUID()
        audioSendTask?.cancel()
        audioSendTask = nil
        pendingAudioSendChunks = 0
    }

    private func updateUsageControlSettingsIfNeeded(oldValue: AppSettings) {
        let usageControlsChanged = oldValue.usageControls != settings.usageControls
        guard usageControlsChanged else { return }
        updateUsageControlSettings()
    }

    private func updateUsageControlSettings() {
        let now = Date()
        usageEngine.updateSettings(settings.usageControls, now: now)
        let decision = usageEngine.reevaluatePauseAfterSettingsChange(now: now)
        usageSnapshot = usageEngine.snapshot
        if isRunning, decision.shouldResume {
            scheduleUsageResume(replayChunks: decision.replayChunks)
            updateRunningUsageStatus(now: now, force: true)
        }
    }

    private func enterUsagePause(reason: UsageControlPauseReason) {
        resetAudioSendPipeline()
        client?.close()
        client = nil
        audioPlayer.stop()
        saveUsageLedger()
        appendLog(usagePauseLogMessage(reason), level: .info)
    }

    private func scheduleUsageResume(replayChunks: [BufferedAudioChunk]) {
        guard usageResumeTask == nil else { return }
        usageResumeTask = Task { [weak self] in
            await self?.resumeFromUsagePause(replayChunks: replayChunks)
        }
    }

    private func resumeFromUsagePause(replayChunks: [BufferedAudioChunk]) async {
        guard shouldContinueRuntimeConnection() else {
            usageResumeTask = nil
            return
        }

        updateStatus("Resuming · replaying buffered audio", level: .connecting, log: true)
        let newClient = makeGeminiClient()
        do {
            try await newClient.connect()
            guard shouldContinueRuntimeConnection() else {
                discardAsyncClient(newClient)
                usageResumeTask = nil
                return
            }
            client = newClient
            for chunk in replayChunks {
                guard shouldContinueRuntimeConnection(), client === newClient else {
                    discardAsyncClient(newClient)
                    usageResumeTask = nil
                    return
                }
                await newClient.sendAudio(chunk.data)
            }
            guard shouldContinueRuntimeConnection(), client === newClient else {
                discardAsyncClient(newClient)
                usageResumeTask = nil
                return
            }
            sentChunkCount += replayChunks.count
            usageEngine.markReplaySent(replayChunks)
            usageEngine.markResumed(now: Date())
            usageSnapshot = usageEngine.snapshot
            saveUsageLedger()
            updateStatus(runningUsageStatusMessage(), level: .running, log: true)
        } catch {
            newClient.close()
            guard shouldContinueRuntimeConnection() else {
                usageResumeTask = nil
                return
            }
            client = nil
            usageEngine.forcePause(.idle)
            usageSnapshot = usageEngine.snapshot
            let diagnostic = DiagnosticClassifier.from(error: error, context: .runtime)
            setDiagnosticIssue(diagnostic)
            updateStatus(settings.interfaceLanguage.localized(diagnostic.titleKey), level: .error, log: true)
        }
        usageResumeTask = nil
    }

    private func runningUsageStatusMessage() -> String {
        let apiTime = Self.formatUsageDuration(usageSnapshot.sessionSentAudioSeconds)
        let base = "mic \(micChunkCount) · screen \(screenChunkCount) · sent \(sentChunkCount) · API \(apiTime)"
        switch usageSnapshot.runtimeState {
        case .active:
            return "Listening · \(base)"
        case .idleWarning(let remainingSeconds):
            return "Idle soon · auto-pause in \(remainingSeconds)s · \(base)"
        case .paused(let reason):
            return "\(usagePauseLogMessage(reason)) · \(base)"
        case .resuming:
            return "Resuming · replaying buffered audio · \(base)"
        }
    }

    private func usagePauseLogMessage(_ reason: UsageControlPauseReason) -> String {
        switch reason {
        case .idle:
            return "API paused · monitoring locally"
        case .sessionLimit:
            return "Session usage limit reached · API paused"
        case .dailyLimit:
            return "Daily usage limit reached · API paused"
        }
    }

    static func formatUsageDuration(_ seconds: TimeInterval) -> String {
        let totalSeconds = max(0, Int(seconds.rounded()))
        let hours = totalSeconds / 3_600
        let minutes = (totalSeconds % 3_600) / 60
        let seconds = totalSeconds % 60
        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, seconds)
        }
        return String(format: "%02d:%02d", minutes, seconds)
    }

    nonisolated private static func calculateRMS(data: Data) -> Float {
        let count = data.count / 2
        guard count > 0 else { return 0 }
        
        return data.withUnsafeBytes { buffer -> Float in
            guard let pointer = buffer.bindMemory(to: Int16.self).baseAddress else { return 0 }
            
            var sumSquares: Float = 0
            for i in 0..<count {
                let sample = Float(pointer[i])
                sumSquares += sample * sample
            }
            
            let rms = sqrt(sumSquares / Float(count))
            let normalized = rms / 32767.0
            return min(max(normalized, 0.0), 1.0)
        }
    }

    private func appendOriginalText(_ text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        usageEngine.noteTranscriptActivity(at: Date())
        usageSnapshot = usageEngine.snapshot
        let pending = boundedTranscriptDraft(originalDraft + (originalDraft.isEmpty ? "" : " ") + trimmed)
        let sentences = completedSentences(from: pending)
        for sentence in sentences.completed {
            completedOriginalSentences.append(boundedOriginalSentence(sentence))
        }
        trimPendingOriginalSentences()
        originalDraft = boundedTranscriptDraft(sentences.remainder)
    }

    private func boundedTranscriptDraft(_ text: String) -> String {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count > Self.maxTranscriptDraftCharacters else { return trimmed }
        return String(trimmed.suffix(Self.maxTranscriptDraftCharacters))
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func boundedOriginalSentence(_ sentence: String) -> String {
        let trimmed = sentence.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count > Self.maxPendingOriginalSentenceCharacters else { return trimmed }
        return String(trimmed.suffix(Self.maxPendingOriginalSentenceCharacters))
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func trimPendingOriginalSentences() {
        guard completedOriginalSentences.count > Self.maxPendingOriginalSentences else { return }
        completedOriginalSentences.removeFirst(completedOriginalSentences.count - Self.maxPendingOriginalSentences)
    }

    private func appendCaption(_ text: String, language: String?, kind: CaptionKind) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        usageEngine.noteTranscriptActivity(at: Date())
        usageSnapshot = usageEngine.snapshot
        var pending = boundedTranscriptDraft(captionDraft + (captionDraft.isEmpty ? "" : " ") + trimmed)
        let sentences = completedSentences(from: pending)
        for sentence in sentences.completed {
            let original: String?
            if !completedOriginalSentences.isEmpty {
                original = completedOriginalSentences.removeFirst()
            } else if !originalDraft.isEmpty {
                original = originalDraft
                originalDraft = ""
            } else {
                original = nil
            }
            let line = CaptionLine(text: sentence, originalText: original, languageCode: language, kind: kind)
            captions.append(line)
            appendCurrentTranscriptLine(from: line)
        }
        pending = sentences.remainder
        captionDraft = boundedTranscriptDraft(pending)
        if captions.count > 80 {
            captions.removeFirst(captions.count - 80)
        }
    }

    private func appendCurrentTranscriptLine(from line: CaptionLine) {
        guard line.kind == .output else { return }
        let transcriptLine = TranscriptLine(
            id: line.id,
            text: line.text,
            originalText: line.originalText,
            languageCode: line.languageCode,
            timestamp: line.timestamp
        )
        currentTranscriptLines.append(transcriptLine)
        if let sessionID = currentSessionID,
           let index = transcriptSessions.firstIndex(where: { $0.id == sessionID }) {
            transcriptSessions[index].lines = currentTranscriptLines
            scheduleTranscriptSave()
        }
    }

    var subtitleLines: [SubtitleDisplayLine] {
        let items = captions
            .filter { $0.kind == .output }
            .map { SubtitleDisplayItem(original: $0.originalText, translated: $0.text) }
        return SubtitleDisplayTextBuilder.lines(
            items: items,
            translatedDraft: captionDraft,
            originalDraft: originalDraft,
            mode: settings.subtitleDisplayMode
        )
    }

    var subtitleText: String {
        SubtitleDisplayTextBuilder.plainText(from: subtitleLines)
    }

    private func completedSentences(from text: String) -> (completed: [String], remainder: String) {
        let terminators = CharacterSet(charactersIn: ".?!。？！")
        var completed: [String] = []
        var start = text.startIndex
        var index = text.startIndex

        while index < text.endIndex {
            let scalar = text[index].unicodeScalars.first
            if let scalar, terminators.contains(scalar) {
                var end = text.index(after: index)
                
                while end < text.endIndex,
                    let nextScalar = text[end].unicodeScalars.first,
                    terminators.contains(nextScalar) {
                    end = text.index(after: end)
                }
                
                var isEndOfSentence = false
                if end == text.endIndex {
                    isEndOfSentence = true
                } else if let nextScalar = text[end].unicodeScalars.first,
                        CharacterSet.whitespacesAndNewlines.contains(nextScalar) {
                    isEndOfSentence = true
                }
                
                if isEndOfSentence {
                    let sentence = String(text[start..<end]).trimmingCharacters(in: .whitespacesAndNewlines)
                    if !sentence.isEmpty {
                        completed.append(sentence)
                    }
                    start = end
                }
                index = end
            } else {
                index = text.index(after: index)
            }
        }

        let remainder = String(text[start...]).trimmingCharacters(in: .whitespacesAndNewlines)
        return (completed, remainder)
    }

    private func scheduleSettingsSaveIfNeeded(oldValue: AppSettings) {
        guard settings.requiresSettingsFileSave(comparedTo: oldValue) else { return }
        scheduleSettingsSave()
    }

    private func scheduleSettingsSave() {
        guard settingsSaveTask == nil else { return }
        settingsSaveTask = Task { @MainActor [weak self] in
            do {
                try await Task.sleep(nanoseconds: Self.settingsSaveDebounceNanoseconds)
            } catch {
                self?.settingsSaveTask = nil
                return
            }
            guard !Task.isCancelled else {
                self?.settingsSaveTask = nil
                return
            }
            guard let self else { return }
            self.saveSettings()
            self.settingsSaveTask = nil
        }
    }

    private func saveSettingsImmediately() {
        settingsSaveTask?.cancel()
        settingsSaveTask = nil
        saveSettings()
    }

    private func saveSettings() {
        do {
            try FileManager.default.createDirectory(at: settingsURL.deletingLastPathComponent(), withIntermediateDirectories: true)
            let data = try JSONEncoder().encode(settings)
            try data.write(to: settingsURL, options: [.atomic])
        } catch {
            let issue = DiagnosticClassifier.storage(.settingsSaveFailed, underlyingMessage: error.localizedDescription)
            setDiagnosticIssue(issue)
            updateStatus(settings.interfaceLanguage.localized(issue.titleKey), level: .error, log: true)
        }
    }

    private static func loadUsageLedger(from url: URL, now: Date) -> UsageLedger {
        let fallback = UsageLedger.empty(for: now)
        guard let data = try? Data(contentsOf: url),
              let decoded = try? JSONDecoder().decode(UsageLedger.self, from: data) else {
            return fallback
        }
        return decoded.dayKey == UsageLedger.dayKey(for: now) ? decoded : fallback
    }

    private func saveUsageLedger() {
        do {
            try FileManager.default.createDirectory(at: usageLedgerURL.deletingLastPathComponent(), withIntermediateDirectories: true)
            let data = try JSONEncoder().encode(usageEngine.ledger)
            try data.write(to: usageLedgerURL, options: [.atomic])
        } catch {
            appendLog("Cannot save usage ledger: \(error.localizedDescription)", level: .error)
        }
    }

    private func rebuildRunningSessionIfNeeded(oldValue: AppSettings) {
        guard isRunning, settings.requiresSessionRestart(comparedTo: oldValue) else { return }
        restartTask?.cancel()
        restartTask = Task { @MainActor [weak self] in
            guard let self else { return }
            do {
                try await Task.sleep(for: .milliseconds(350))
            } catch {
                return
            }
            guard !Task.isCancelled else { return }
            await self.stop(cancelPendingRestart: false)
            guard !Task.isCancelled else { return }
            await self.start()
            guard !Task.isCancelled else { return }
            self.restartTask = nil
        }
    }

    private func updateAudioPlayerVolumeIfNeeded(oldValue: AppSettings) {
        let audioOutputChanged =
            oldValue.audioPlayerVolume != settings.audioPlayerVolume ||
            oldValue.audioPlayerMuted != settings.audioPlayerMuted
        guard audioOutputChanged else { return }
        updateAudioPlayerVolume()
    }

    private func updateAudioPlayerVolume() {
        let volume = settings.audioPlayerMuted ? 0.0 : settings.audioPlayerVolume
        audioPlayer.setVolume(Float(volume))
    }

    private func handleClientStatus(_ message: String) {
        let lowered = message.lowercased()
        if lowered.contains("error") || lowered.contains("failed") || lowered.contains("closed") || lowered.contains("disconnected") {
            updateStatus(message, level: .error, log: true)
        } else if lowered.contains("ready") || lowered.contains("listening") || lowered.contains("receiving") {
            updateStatus(message, level: .running, log: false)
        } else {
            updateStatus(message, level: isRunning ? .running : .connecting, log: false)
        }
    }

    private func updateStatus(_ message: String, level: LiveStatusLevel, log: Bool) {
        statusMessage = message
        statusLevel = level
        if log {
            appendLog(message, level: level == .error ? .error : .info)
        }
    }

    private func setDiagnosticIssue(_ issue: DiagnosticIssue?) {
        currentDiagnosticIssue = issue
    }

    private func appendLog(_ message: String, level: LogLevel) {
        let trimmed = message.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        logs.append(LogEntry(message: trimmed, level: level))
        if logs.count > 400 {
            logs.removeFirst(logs.count - 400)
        }
    }

    // MARK: - Transcript Sessions

    private func beginTranscriptSession() {
        currentTranscriptLines.removeAll()
        let session = TranscriptSession(
            id: UUID(),
            startedAt: Date(),
            endedAt: nil,
            targetLanguage: TranslationLanguage.name(for: settings.targetLanguageCode),
            audioSource: settings.audioSource.title,
            lines: []
        )
        currentSessionID = session.id
        transcriptSessions.insert(session, at: 0)
        saveTranscriptSessionsImmediately()
    }

    private func finishTranscriptSession() {
        guard let sessionID = currentSessionID else { return }
        guard let index = transcriptSessions.firstIndex(where: { $0.id == sessionID }) else {
            clearActiveTranscriptState()
            return
        }

        // Flush any remaining drafts
        if !captionDraft.isEmpty {
            let original = !completedOriginalSentences.isEmpty ? completedOriginalSentences.joined(separator: " ") : originalDraft
            captions.append(CaptionLine(
                text: captionDraft,
                originalText: original.isEmpty ? nil : original,
                languageCode: settings.targetLanguageCode,
                kind: .output
            ))
            if let line = captions.last {
                appendCurrentTranscriptLine(from: line)
            }
            captionDraft = ""
            originalDraft = ""
            completedOriginalSentences.removeAll()
        }

        var session = transcriptSessions[index]
        session.lines = currentTranscriptLines
        session.endedAt = Date()
        transcriptSessions[index] = session
        currentSessionID = nil
        currentTranscriptLines.removeAll()
        saveTranscriptSessionsImmediately()
    }

    func deleteTranscriptSession(_ session: TranscriptSession) {
        let wasActiveSession = currentSessionID == session.id
        if wasActiveSession {
            clearActiveTranscriptState()
        }
        transcriptSessions.removeAll { $0.id == session.id }
        if wasActiveSession {
            restartTranscriptSessionIfRunning()
        }
        saveTranscriptSessionsImmediately()
    }

    func deleteAllTranscriptSessions() {
        clearActiveTranscriptState()
        transcriptSessions.removeAll()
        restartTranscriptSessionIfRunning()
        saveTranscriptSessionsImmediately()
    }

    private func restartTranscriptSessionIfRunning() {
        guard isRunning else { return }
        captionDraft = ""
        originalDraft = ""
        completedOriginalSentences.removeAll()
        currentTranscriptLines.removeAll()
        captions.removeAll()
        beginTranscriptSession()
    }

    private func clearActiveTranscriptState() {
        currentSessionID = nil
        captionDraft = ""
        originalDraft = ""
        completedOriginalSentences.removeAll()
        currentTranscriptLines.removeAll()
    }

    private func scheduleTranscriptSave() {
        guard transcriptSaveTask == nil else { return }
        transcriptSaveTask = Task { @MainActor [weak self] in
            do {
                try await Task.sleep(nanoseconds: Self.transcriptSaveDebounceNanoseconds)
            } catch {
                self?.transcriptSaveTask = nil
                return
            }
            guard !Task.isCancelled else {
                self?.transcriptSaveTask = nil
                return
            }
            guard let self else { return }
            self.saveTranscriptSessions()
            self.transcriptSaveTask = nil
        }
    }

    private func saveTranscriptSessionsImmediately() {
        transcriptSaveTask?.cancel()
        transcriptSaveTask = nil
        saveTranscriptSessions()
    }

    private func saveTranscriptSessions() {
        do {
            try FileManager.default.createDirectory(at: transcriptsURL.deletingLastPathComponent(), withIntermediateDirectories: true)
            let data = try JSONEncoder().encode(transcriptSessions)
            try data.write(to: transcriptsURL, options: [.atomic])
        } catch {
            setDiagnosticIssue(DiagnosticClassifier.storage(.transcriptSaveFailed, underlyingMessage: error.localizedDescription))
            appendLog("Cannot save transcripts: \(error.localizedDescription)", level: .error)
        }
    }

    private func loadTranscriptSessions() {
        guard let data = try? Data(contentsOf: transcriptsURL),
              let decoded = try? JSONDecoder().decode([TranscriptSession].self, from: data) else { return }
        transcriptSessions = decoded
    }

    func refreshAvailableMicrophones() {
        availableMicrophones = AudioDeviceManager.getInputDevices()
    }

    private func startListeningForDeviceChanges() {
        var propertyAddress = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )
        
        let block: AudioObjectPropertyListenerBlock = { [weak self] _, _ in
            Task { @MainActor [weak self] in
                self?.refreshAvailableMicrophones()
            }
        }
        
        self.propertyListenerBlock = block
        
        AudioObjectAddPropertyListenerBlock(
            AudioObjectID(kAudioObjectSystemObject),
            &propertyAddress,
            DispatchQueue.main,
            block
        )
    }

    deinit {
        runtimeControlTask?.cancel()
        pendingRuntimeControlRequest = nil
        restartTask?.cancel()
        reconnectTask?.cancel()
        connectionStopTask?.cancel()
        usageResumeTask?.cancel()
        setupChecklistRefreshTask?.cancel()
        audioSendTask?.cancel()
        apiKeySaveTask?.cancel()
        apiKeySaveTask = nil
        settingsSaveTask?.cancel()
        settingsSaveTask = nil
        preflightTestTask?.cancel()
        temporaryTestCaptionTask?.cancel()
        glossaryImportTask?.cancel()
        transcriptSaveTask?.cancel()
        transcriptSaveTask = nil
        microphoneCapture?.stop()
        if let screenCaptureForDeinit = screenCapture {
            Task {
                await screenCaptureForDeinit.stop()
            }
        }
        client?.close()
        audioPlayer.stop()
        globalShortcutRegistrar.unregisterAll()

        if let block = propertyListenerBlock {
            var propertyAddress = AudioObjectPropertyAddress(
                mSelector: kAudioHardwarePropertyDevices,
                mScope: kAudioObjectPropertyScopeGlobal,
                mElement: kAudioObjectPropertyElementMain
            )
            AudioObjectRemovePropertyListenerBlock(
                AudioObjectID(kAudioObjectSystemObject),
                &propertyAddress,
                DispatchQueue.main,
                block
            )
        }
    }
}

enum LiveStatusLevel {
    case stopped
    case connecting
    case running
    case error
}

enum LogLevel {
    case info
    case error
}

struct LogEntry: Identifiable, Equatable {
    let id: UUID
    let timestamp: Date
    let message: String
    let level: LogLevel

    init(id: UUID = UUID(), timestamp: Date = Date(), message: String, level: LogLevel) {
        self.id = id
        self.timestamp = timestamp
        self.message = message
        self.level = level
    }
}

struct LogExporter {
    func export(entries: [LogEntry]) -> String {
        guard !entries.isEmpty else {
            return "# Runtime Logs\n\nNo log entries.\n"
        }

        let lines = entries.map { entry in
            "[\(formattedTimestamp(entry.timestamp))] \(levelText(entry.level)) \(entry.message)"
        }
        return "# Runtime Logs\n\n\(lines.joined(separator: "\n"))\n"
    }

    func defaultFileName(date: Date = Date()) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd-HHmm"
        return "LiveBuddy-Logs-\(formatter.string(from: date)).txt"
    }

    private func formattedTimestamp(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
        return formatter.string(from: date)
    }

    private func levelText(_ level: LogLevel) -> String {
        switch level {
        case .info:
            return "INFO"
        case .error:
            return "ERROR"
        }
    }
}

enum CaptionKind {
    case input
    case output
}

struct CaptionLine: Identifiable, Equatable {
    let id: UUID
    let text: String
    let originalText: String?
    let languageCode: String?
    let kind: CaptionKind
    let timestamp: Date

    init(id: UUID = UUID(), text: String, originalText: String? = nil, languageCode: String?, kind: CaptionKind, timestamp: Date = Date()) {
        self.id = id
        self.text = text
        self.originalText = originalText
        self.languageCode = languageCode
        self.kind = kind
        self.timestamp = timestamp
    }
}
