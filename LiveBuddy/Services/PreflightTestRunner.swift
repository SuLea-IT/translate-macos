import Foundation

struct PreflightTestRunner {
    typealias ProviderCheck = @Sendable (_ apiKey: String) async -> ProviderHealthStatus
    typealias PermissionCheck = @Sendable () async -> PermissionStatusSnapshot
    typealias AudioSampler = @Sendable (_ selectedDeviceUID: String?, _ analyzer: inout AudioLevelAnalyzer) async throws -> Void
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
        guard !Task.isCancelled else { return report }

        report = await runProvider(settings: settings, report: report, update: update)
        guard !Task.isCancelled else { return report }
        report = await runPermissions(settings: settings, report: report, update: update)
        guard !Task.isCancelled else { return report }
        report = await runAudioIfNeeded(settings: settings, report: report, update: update)
        guard !Task.isCancelled else { return report }
        report = await runSubtitle(report: report, update: update)
        guard !Task.isCancelled else { return report }
        report.finishedAt = Date()
        await update(report)
        return report
    }

    private func runProvider(settings: AppSettings, report: PreflightTestReport, update: ReportUpdate) async -> PreflightTestReport {
        var report = report.updating(.apiKey, state: .running, messageKey: .preflightCheckingAPIKey)
        await update(report)
        let status = await providerCheck(settings.apiKey)
        guard !Task.isCancelled else { return report }
        switch status {
        case .valid:
            report = report.updating(.apiKey, state: .passed, messageKey: .preflightAPIKeyValid)
        case .missing:
            report = report.updating(.apiKey, state: .failed, messageKey: .preflightAPIKeyMissing)
        case .unchecked, .checking:
            report = report.updating(.apiKey, state: .warning, messageKey: .preflightAPIKeyNotVerified)
        case .invalid(let message, _), .failed(let message, _):
            report = report.updating(.apiKey, state: .failed, message: message)
        }
        await update(report)
        return report
    }

    private func runPermissions(settings: AppSettings, report: PreflightTestReport, update: ReportUpdate) async -> PreflightTestReport {
        var report = report.updating(.permissions, state: .running, messageKey: .preflightCheckingPermissions)
        await update(report)
        let permissions = await permissionCheck()
        guard !Task.isCancelled else { return report }
        let checklist = SetupChecklistState.derive(
            audioSource: settings.audioSource,
            apiKey: settings.apiKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? .missing : .valid(checkedAt: Date()),
            microphone: permissions.microphone,
            screenRecording: permissions.screenRecording
        )
        if checklist.blockingIssues.isEmpty {
            report = report.updating(.permissions, state: .passed, messageKey: .preflightPermissionsAvailable)
        } else {
            report = report.updating(.permissions, state: .failed, messageKey: .preflightPermissionsMissing)
        }
        await update(report)
        return report
    }

    private func runAudioIfNeeded(settings: AppSettings, report: PreflightTestReport, update: ReportUpdate) async -> PreflightTestReport {
        var report = report
        guard !Task.isCancelled else { return report }
        if settings.audioSource == .microphone || settings.audioSource == .both {
            report = await runAudioStep(
                .microphoneAudio,
                selectedDeviceUID: settings.selectedMicrophoneDeviceUID,
                sampler: microphoneSampler,
                report: report,
                update: update
            )
        } else {
            report = report.updating(.microphoneAudio, state: .passed, messageKey: .preflightNotNeededForAudioSource)
            await update(report)
        }
        guard !Task.isCancelled else { return report }

        if settings.audioSource == .screen || settings.audioSource == .both {
            report = await runAudioStep(
                .screenAudio,
                selectedDeviceUID: nil,
                sampler: screenSampler,
                report: report,
                update: update
            )
        } else {
            report = report.updating(.screenAudio, state: .passed, messageKey: .preflightNotNeededForAudioSource)
            await update(report)
        }
        guard !Task.isCancelled else { return report }
        return report
    }

    private func runAudioStep(
        _ id: PreflightTestStepID,
        selectedDeviceUID: String?,
        sampler: AudioSampler,
        report: PreflightTestReport,
        update: ReportUpdate
    ) async -> PreflightTestReport {
        var report = report.updating(id, state: .running, messageKey: .preflightSamplingAudio)
        await update(report)
        guard !Task.isCancelled else { return report }
        var analyzer = AudioLevelAnalyzer()
        do {
            try await sampler(selectedDeviceUID, &analyzer)
            guard !Task.isCancelled else { return report }
            let summary = analyzer.summary()
            if summary.totalSampleCount == 0 {
                report = report.updating(id, state: .failed, messageKey: .preflightNoAudioCaptured, audio: summary)
            } else if summary.isClipping {
                report = report.updating(id, state: .warning, messageKey: .audioClippingDetected, audio: summary)
            } else if summary.isSilent {
                report = report.updating(id, state: .warning, messageKey: .audioTooQuiet, audio: summary)
            } else {
                report = report.updating(id, state: .passed, messageKey: .audioDetected, audio: summary)
            }
        } catch is CancellationError {
            return report
        } catch {
            report = report.updating(id, state: .failed, message: error.localizedDescription)
        }
        guard !Task.isCancelled else { return report }
        await update(report)
        return report
    }

    private func runSubtitle(report: PreflightTestReport, update: ReportUpdate) async -> PreflightTestReport {
        var report = report.updating(.subtitleWindow, state: .running, messageKey: .preflightShowingSubtitleTest)
        await update(report)
        guard !Task.isCancelled else { return report }
        await subtitleCheck()
        guard !Task.isCancelled else { return report }
        report = report.updating(.subtitleWindow, state: .passed, messageKey: .preflightSubtitleWindowShown)
        await update(report)
        return report
    }
}

extension PreflightTestRunner {
    static func live(
        settings _: AppSettings,
        providerHealthService: ProviderHealthService = .geminiDefault,
        permissionStatusService: PermissionStatusService = PermissionStatusService(),
        sampleDuration: TimeInterval = 3,
        subtitleCheck: @escaping SubtitleCheck
    ) -> PreflightTestRunner {
        PreflightTestRunner(
            providerCheck: { apiKey in
                await providerHealthService.verify(apiKey: apiKey)
            },
            permissionCheck: {
                await permissionStatusService.refreshStatuses()
            },
            microphoneSampler: { selectedDeviceUID, analyzer in
                try await sampleMicrophone(selectedDeviceUID: selectedDeviceUID, duration: sampleDuration, analyzer: &analyzer)
            },
            screenSampler: { _, analyzer in
                try await sampleScreen(duration: sampleDuration, analyzer: &analyzer)
            },
            subtitleCheck: subtitleCheck
        )
    }

    private static func sampleMicrophone(selectedDeviceUID: String?, duration: TimeInterval, analyzer: inout AudioLevelAnalyzer) async throws {
        try Task.checkCancellation()
        let box = AudioLevelAnalyzerBox(analyzer)
        let capture = MicrophoneCapture { data in
            box.process(data)
        }
        do {
            try await capture.start(selectedDeviceUID: selectedDeviceUID)
            try Task.checkCancellation()
            try await Task.sleep(nanoseconds: UInt64(duration * 1_000_000_000))
        } catch {
            capture.stop()
            throw error
        }
        capture.stop()
        analyzer = box.snapshot()
    }

    private static func sampleScreen(duration: TimeInterval, analyzer: inout AudioLevelAnalyzer) async throws {
        try Task.checkCancellation()
        let box = AudioLevelAnalyzerBox(analyzer)
        let capture = ScreenAudioCapture { data in
            box.process(data)
        }
        do {
            try await capture.start()
            try Task.checkCancellation()
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
