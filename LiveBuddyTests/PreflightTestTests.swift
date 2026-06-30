import Foundation
import Testing
@testable import LiveBuddy

struct PreflightTestTests {
    private func pcm16(_ samples: [Int16]) -> Data {
        var data = Data(capacity: samples.count * 2)
        for sample in samples {
            var littleEndian = sample.littleEndian
            withUnsafeBytes(of: &littleEndian) { data.append(contentsOf: $0) }
        }
        return data
    }

    @Test func analyzerComputesPeakAndRMSWithoutKeepingSamples() {
        var analyzer = AudioLevelAnalyzer()

        analyzer.processPCM16(pcm16([0, 16_384, -16_384, 32_767]))
        let summary = analyzer.summary()

        #expect(summary.totalSampleCount == 4)
        #expect(summary.peak > 0.99)
        #expect(summary.rms > 0.55)
        #expect(summary.rms < 0.62)
        #expect(summary.retainedSampleCount == 0)
    }

    @Test func analyzerMarksSilenceWhenPeakAndRMSAreLow() {
        var analyzer = AudioLevelAnalyzer(silenceThreshold: 0.01, peakSilenceThreshold: 0.02)

        analyzer.processPCM16(pcm16([0, 0, 40, -40, 0]))
        let summary = analyzer.summary()

        #expect(summary.isSilent)
        #expect(summary.isClipping == false)
    }

    @Test func analyzerMarksClippingForNearFullScaleSamples() {
        var analyzer = AudioLevelAnalyzer(clippingThreshold: 0.98)

        analyzer.processPCM16(pcm16([0, 32_767, -32_768]))
        let summary = analyzer.summary()

        #expect(summary.isClipping)
        #expect(summary.clippedSampleCount == 2)
    }

    @Test func reportSummaryIsFailedWhenAnyStepFailsAndWarningWhenOnlyWarningsExist() {
        let failed = PreflightTestReport(steps: [
            PreflightTestStep(id: .apiKey, state: .passed, message: "ok"),
            PreflightTestStep(id: .permissions, state: .failed, message: "missing")
        ])
        let warning = PreflightTestReport(steps: [
            PreflightTestStep(id: .apiKey, state: .passed, message: "ok"),
            PreflightTestStep(id: .microphoneAudio, state: .warning, message: "quiet")
        ])

        #expect(failed.summaryState == .failed)
        #expect(warning.summaryState == .warning)
    }
}

extension PreflightTestTests {
    @Test func runnerPublishesMessageKeysForFixedStatuses() async {
        let runner = PreflightTestRunner(
            providerCheck: { _ in .valid(checkedAt: Date()) },
            permissionCheck: {
                PermissionStatusSnapshot(
                    microphone: PermissionStatus(requirement: .microphone, state: .granted, checkedAt: Date()),
                    screenRecording: PermissionStatus(requirement: .screenRecording, state: .granted, checkedAt: Date())
                )
            },
            microphoneSampler: { _, analyzer in
                analyzer.processPCM16(pcm16([0, 8_000, -8_000, 12_000]))
            },
            screenSampler: { _, _ in },
            subtitleCheck: {}
        )
        var settings = AppSettings()
        settings.audioSource = .microphone
        settings.apiKey = "test-key"

        let report = await runner.run(settings: settings) { _ in }

        #expect(report.steps.first { $0.id == .apiKey }?.messageKey == .preflightAPIKeyValid)
        #expect(report.steps.first { $0.id == .permissions }?.messageKey == .preflightPermissionsAvailable)
        #expect(report.steps.first { $0.id == .microphoneAudio }?.messageKey == .audioDetected)
        #expect(report.steps.first { $0.id == .screenAudio }?.messageKey == .preflightNotNeededForAudioSource)
        #expect(report.steps.first { $0.id == .subtitleWindow }?.messageKey == .preflightSubtitleWindowShown)
    }

    @Test func runnerMarksNormalAudioAsPassed() async {
        let runner = PreflightTestRunner(
            providerCheck: { _ in .valid(checkedAt: Date()) },
            permissionCheck: {
                PermissionStatusSnapshot(
                    microphone: PermissionStatus(requirement: .microphone, state: .granted, checkedAt: Date()),
                    screenRecording: PermissionStatus(requirement: .screenRecording, state: .granted, checkedAt: Date())
                )
            },
            microphoneSampler: { _, analyzer in
                analyzer.processPCM16(pcm16([0, 8_000, -8_000, 12_000]))
            },
            screenSampler: { _, _ in },
            subtitleCheck: {}
        )
        var settings = AppSettings()
        settings.audioSource = .microphone
        settings.apiKey = "test-key"

        let report = await runner.run(settings: settings) { _ in }

        let audio = report.steps.first { $0.id == .microphoneAudio }
        #expect(audio?.state == .passed)
        #expect(audio?.audio?.isSilent == false)
    }

    @Test func runnerMarksQuietAudioAsWarning() async {
        let runner = PreflightTestRunner(
            providerCheck: { _ in .valid(checkedAt: Date()) },
            permissionCheck: {
                PermissionStatusSnapshot(
                    microphone: PermissionStatus(requirement: .microphone, state: .granted, checkedAt: Date()),
                    screenRecording: PermissionStatus(requirement: .screenRecording, state: .granted, checkedAt: Date())
                )
            },
            microphoneSampler: { _, analyzer in
                analyzer.processPCM16(pcm16([0, 0, 10, -10]))
            },
            screenSampler: { _, _ in },
            subtitleCheck: {}
        )
        var settings = AppSettings()
        settings.audioSource = .microphone
        settings.apiKey = "test-key"

        let report = await runner.run(settings: settings) { _ in }

        #expect(report.steps.first { $0.id == .microphoneAudio }?.state == .warning)
    }

    @Test func runnerPassesSelectedMicrophoneUIDToMicrophoneSampler() async {
        let recorder = SelectedMicrophoneUIDRecorder()
        let runner = PreflightTestRunner(
            providerCheck: { _ in .valid(checkedAt: Date()) },
            permissionCheck: {
                PermissionStatusSnapshot(
                    microphone: PermissionStatus(requirement: .microphone, state: .granted, checkedAt: Date()),
                    screenRecording: PermissionStatus(requirement: .screenRecording, state: .granted, checkedAt: Date())
                )
            },
            microphoneSampler: { selectedDeviceUID, analyzer in
                await recorder.record(selectedDeviceUID)
                analyzer.processPCM16(pcm16([0, 8_000, -8_000, 12_000]))
            },
            screenSampler: { _, _ in },
            subtitleCheck: {}
        )
        var settings = AppSettings()
        settings.audioSource = .microphone
        settings.apiKey = "test-key"
        settings.selectedMicrophoneDeviceUID = "mic-uid-123"

        _ = await runner.run(settings: settings) { _ in }

        #expect(await recorder.value == "mic-uid-123")
    }

}

private actor SelectedMicrophoneUIDRecorder {
    private(set) var value: String?

    func record(_ value: String?) {
        self.value = value
    }
}
