import Foundation

struct PreflightTestRunner {
    typealias ProviderCheck = @Sendable () async -> ProviderHealthStatus
    typealias PermissionCheck = @Sendable () async -> PermissionStatusSnapshot
    typealias AudioSampler = @Sendable (_ analyzer: inout AudioLevelAnalyzer) async throws -> Void
    typealias SubtitleCheck = @Sendable () async -> Void
    typealias ReportUpdate = @MainActor (PreflightTestReport) -> Void

    var providerCheck: ProviderCheck
    var permissionCheck: PermissionCheck
    var microphoneSampler: AudioSampler
    var screenSampler: AudioSampler
    var subtitleCheck: SubtitleCheck

    init(
        providerCheck: @escaping ProviderCheck,
        permissionCheck: @escaping PermissionCheck,
        microphoneSampler: @escaping AudioSampler,
        screenSampler: @escaping AudioSampler,
        subtitleCheck: @escaping SubtitleCheck
    ) {
        self.providerCheck = providerCheck
        self.permissionCheck = permissionCheck
        self.microphoneSampler = microphoneSampler
        self.screenSampler = screenSampler
        self.subtitleCheck = subtitleCheck
    }

    func run(settings: AppSettings, update: @escaping ReportUpdate) async -> PreflightTestReport {
        var report = PreflightTestReport(startedAt: Date(), finishedAt: nil)
        await update(report)

        report = await runProvider(report: report, update: update)
        report = await runPermissions(settings: settings, report: report, update: update)
        report = await runAudioIfNeeded(settings: settings, report: report, update: update)
        report = await runSubtitle(report: report, update: update)
        report.finishedAt = Date()
        await update(report)
        return report
    }

    private func runProvider(report: PreflightTestReport, update: ReportUpdate) async -> PreflightTestReport {
        var report = report.updating(.apiKey, state: .running, message: "Checking API key")
        await update(report)
        let status = await providerCheck()
        switch status {
        case .valid:
            report = report.updating(.apiKey, state: .passed, message: "API key is valid")
        case .missing:
            report = report.updating(.apiKey, state: .failed, message: "API key is missing")
        case .unchecked, .checking:
            report = report.updating(.apiKey, state: .warning, message: "API key was not verified")
        case .invalid(let message, _), .failed(let message, _):
            report = report.updating(.apiKey, state: .failed, message: message)
        }
        await update(report)
        return report
    }

    private func runPermissions(settings: AppSettings, report: PreflightTestReport, update: ReportUpdate) async -> PreflightTestReport {
        var report = report.updating(.permissions, state: .running, message: "Checking permissions")
        await update(report)
        let permissions = await permissionCheck()
        let checklist = SetupChecklistState.derive(
            audioSource: settings.audioSource,
            apiKey: settings.apiKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? .missing : .valid(checkedAt: Date()),
            microphone: permissions.microphone,
            screenRecording: permissions.screenRecording
        )
        if checklist.blockingIssues.isEmpty {
            report = report.updating(.permissions, state: .passed, message: "Required permissions are available")
        } else {
            report = report.updating(.permissions, state: .failed, message: checklist.blockingIssues.map(\.rawValue).joined(separator: ", "))
        }
        await update(report)
        return report
    }

    private func runAudioIfNeeded(settings: AppSettings, report: PreflightTestReport, update: ReportUpdate) async -> PreflightTestReport {
        var report = report
        if settings.audioSource == .microphone || settings.audioSource == .both {
            report = await runAudioStep(.microphoneAudio, sampler: microphoneSampler, report: report, update: update)
        } else {
            report = report.updating(.microphoneAudio, state: .passed, message: "Not needed for selected audio source")
            await update(report)
        }

        if settings.audioSource == .screen || settings.audioSource == .both {
            report = await runAudioStep(.screenAudio, sampler: screenSampler, report: report, update: update)
        } else {
            report = report.updating(.screenAudio, state: .passed, message: "Not needed for selected audio source")
            await update(report)
        }
        return report
    }

    private func runAudioStep(
        _ id: PreflightTestStepID,
        sampler: AudioSampler,
        report: PreflightTestReport,
        update: ReportUpdate
    ) async -> PreflightTestReport {
        var report = report.updating(id, state: .running, message: "Sampling audio")
        await update(report)
        var analyzer = AudioLevelAnalyzer()
        do {
            try await sampler(&analyzer)
            let summary = analyzer.summary()
            if summary.totalSampleCount == 0 {
                report = report.updating(id, state: .failed, message: "No audio samples were captured", audio: summary)
            } else if summary.isClipping {
                report = report.updating(id, state: .warning, message: "Audio clipping detected", audio: summary)
            } else if summary.isSilent {
                report = report.updating(id, state: .warning, message: "Audio is too quiet", audio: summary)
            } else {
                report = report.updating(id, state: .passed, message: "Audio detected", audio: summary)
            }
        } catch {
            report = report.updating(id, state: .failed, message: error.localizedDescription)
        }
        await update(report)
        return report
    }

    private func runSubtitle(report: PreflightTestReport, update: ReportUpdate) async -> PreflightTestReport {
        var report = report.updating(.subtitleWindow, state: .running, message: "Showing subtitle test")
        await update(report)
        await subtitleCheck()
        report = report.updating(.subtitleWindow, state: .passed, message: "Subtitle window test shown")
        await update(report)
        return report
    }
}

extension PreflightTestRunner {
    static func live(
        settings: AppSettings,
        providerHealthService: ProviderHealthService = .geminiDefault,
        permissionStatusService: PermissionStatusService = PermissionStatusService(),
        sampleDuration: TimeInterval = 3,
        subtitleCheck: @escaping SubtitleCheck
    ) -> PreflightTestRunner {
        PreflightTestRunner(
            providerCheck: {
                await providerHealthService.verify(apiKey: settings.apiKey)
            },
            permissionCheck: {
                await permissionStatusService.refreshStatuses()
            },
            microphoneSampler: { analyzer in
                try await sampleMicrophone(settings: settings, duration: sampleDuration, analyzer: &analyzer)
            },
            screenSampler: { analyzer in
                try await sampleScreen(duration: sampleDuration, analyzer: &analyzer)
            },
            subtitleCheck: subtitleCheck
        )
    }

    private static func sampleMicrophone(settings: AppSettings, duration: TimeInterval, analyzer: inout AudioLevelAnalyzer) async throws {
        let box = AudioLevelAnalyzerBox(analyzer)
        let capture = MicrophoneCapture { data in
            box.process(data)
        }
        try await capture.start(selectedDeviceUID: settings.selectedMicrophoneDeviceUID)
        do {
            try await Task.sleep(nanoseconds: UInt64(duration * 1_000_000_000))
        } catch {
            capture.stop()
            throw error
        }
        capture.stop()
        analyzer = box.snapshot()
    }

    private static func sampleScreen(duration: TimeInterval, analyzer: inout AudioLevelAnalyzer) async throws {
        let box = AudioLevelAnalyzerBox(analyzer)
        let capture = ScreenAudioCapture { data in
            box.process(data)
        }
        try await capture.start()
        do {
            try await Task.sleep(nanoseconds: UInt64(duration * 1_000_000_000))
        } catch {
            await capture.stop()
            throw error
        }
        await capture.stop()
        analyzer = box.snapshot()
    }
}

private final class AudioLevelAnalyzerBox: @unchecked Sendable {
    private let lock = NSLock()
    private var analyzer: AudioLevelAnalyzer

    init(_ analyzer: AudioLevelAnalyzer) {
        self.analyzer = analyzer
    }

    func process(_ data: Data) {
        lock.lock()
        analyzer.processPCM16(data)
        lock.unlock()
    }

    func snapshot() -> AudioLevelAnalyzer {
        lock.lock()
        defer { lock.unlock() }
        return analyzer
    }
}
