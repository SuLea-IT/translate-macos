# Preflight Test Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight one-click preflight test page that verifies API key, permissions, selected audio input, and subtitle window rendering before a real translation session.

**Architecture:** Keep pure diagnostic state and audio-level math in `PreflightTest.swift`, run checks through an injectable `PreflightTestRunner`, and expose progress through `AppState`. The live runner reuses existing provider/permission/audio capture services, computes streaming peak/RMS/clip metrics without retaining audio, and never starts Gemini or writes transcripts.

**Tech Stack:** Swift, SwiftUI, AVFoundation/ScreenCaptureKit through existing capture classes, Codable models, Swift Testing, Python static verifiers, GitHub Actions xcodebuild.

---

## File Structure

- Create `LiveBuddy/Models/PreflightTest.swift`
  - `PreflightTestStepID`, `PreflightTestStepState`, `AudioLevelSummary`, `PreflightTestStep`, `PreflightTestReport`, `AudioLevelAnalyzer`.
  - Pure model/math only; no UI, network, AVFoundation, or ScreenCaptureKit.
- Create `LiveBuddy/Services/PreflightTestRunner.swift`
  - Async runner with injected closures for provider, permission, audio sampling, and subtitle test.
  - Live factory wires to `ProviderHealthService`, `PermissionStatusService`, `MicrophoneCapture`, `ScreenAudioCapture`.
  - Must not reference `GeminiLiveTranslateClient`.
- Modify `LiveBuddy/Models/AppState.swift`
  - Published preflight report state and `runPreflightTest()`.
  - Temporary caption helper that does not write transcripts.
- Modify `LiveBuddy/Views/Settings/SettingsView.swift`
  - Add Test navigation page and preflight test UI.
- Modify `LiveBuddy/Models/InterfaceLanguage.swift`
  - Add localization keys for all eight supported languages.
- Modify `scripts/verify_p0_onboarding.py` and `scripts/verify_interface_language.py`
  - Static checks for runner/model/UI/localization.
- Create `LiveBuddyTests/PreflightTestTests.swift`
  - Pure analyzer/report/runner injection tests.
- Modify `README.md`
  - Document the new preflight test page.

---

## Task 1: Pure preflight model and streaming audio analyzer

**Files:**
- Create: `LiveBuddy/Models/PreflightTest.swift`
- Test: `LiveBuddyTests/PreflightTestTests.swift`

- [ ] **Step 1: Write failing analyzer and report tests**

Create `LiveBuddyTests/PreflightTestTests.swift`:

```swift
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
```

- [ ] **Step 2: Verify RED**

Run:

```bash
swiftc -typecheck LiveBuddyTests/PreflightTestTests.swift LiveBuddy/Models/PreflightTest.swift 2>&1 | sed -n '1,120p'
```

Expected: failure because `LiveBuddy/Models/PreflightTest.swift` does not exist or `AudioLevelAnalyzer` is undefined.

- [ ] **Step 3: Implement pure model and analyzer**

Create `LiveBuddy/Models/PreflightTest.swift`:

```swift
import Foundation

enum PreflightTestStepID: String, CaseIterable, Codable, Hashable, Identifiable {
    case apiKey
    case permissions
    case microphoneAudio
    case screenAudio
    case subtitleWindow

    var id: String { rawValue }
}

enum PreflightTestStepState: String, Codable, Equatable {
    case pending
    case running
    case passed
    case warning
    case failed
}

struct AudioLevelSummary: Codable, Equatable {
    var peak: Float
    var rms: Float
    var clippedSampleCount: Int
    var totalSampleCount: Int
    var retainedSampleCount: Int
    var isSilent: Bool
    var isClipping: Bool

    static let empty = AudioLevelSummary(
        peak: 0,
        rms: 0,
        clippedSampleCount: 0,
        totalSampleCount: 0,
        retainedSampleCount: 0,
        isSilent: true,
        isClipping: false
    )
}

struct PreflightTestStep: Identifiable, Codable, Equatable {
    var id: PreflightTestStepID
    var state: PreflightTestStepState
    var message: String
    var audio: AudioLevelSummary?

    init(id: PreflightTestStepID, state: PreflightTestStepState = .pending, message: String = "", audio: AudioLevelSummary? = nil) {
        self.id = id
        self.state = state
        self.message = message
        self.audio = audio
    }
}

struct PreflightTestReport: Codable, Equatable {
    var startedAt: Date?
    var finishedAt: Date?
    var steps: [PreflightTestStep]

    static let idle = PreflightTestReport(startedAt: nil, finishedAt: nil, steps: PreflightTestStepID.allCases.map { PreflightTestStep(id: $0) })

    init(startedAt: Date? = nil, finishedAt: Date? = nil, steps: [PreflightTestStep] = PreflightTestReport.idle.steps) {
        self.startedAt = startedAt
        self.finishedAt = finishedAt
        self.steps = steps
    }

    var summaryState: PreflightTestStepState {
        if steps.contains(where: { $0.state == .failed }) { return .failed }
        if steps.contains(where: { $0.state == .running }) { return .running }
        if steps.contains(where: { $0.state == .warning }) { return .warning }
        if steps.allSatisfy({ $0.state == .passed }) { return .passed }
        return .pending
    }

    func updating(_ id: PreflightTestStepID, state: PreflightTestStepState, message: String, audio: AudioLevelSummary? = nil) -> PreflightTestReport {
        var copy = self
        if let index = copy.steps.firstIndex(where: { $0.id == id }) {
            copy.steps[index] = PreflightTestStep(id: id, state: state, message: message, audio: audio)
        } else {
            copy.steps.append(PreflightTestStep(id: id, state: state, message: message, audio: audio))
        }
        return copy
    }
}

struct AudioLevelAnalyzer {
    var silenceThreshold: Float = 0.01
    var peakSilenceThreshold: Float = 0.02
    var clippingThreshold: Float = 0.98

    private var peak: Float = 0
    private var sumSquares: Double = 0
    private var clippedSampleCount = 0
    private var totalSampleCount = 0

    mutating func processPCM16(_ data: Data) {
        guard data.count >= 2 else { return }
        let usableCount = data.count - (data.count % 2)
        data.withUnsafeBytes { rawBuffer in
            guard let base = rawBuffer.baseAddress else { return }
            for offset in stride(from: 0, to: usableCount, by: 2) {
                let sample = base.loadUnaligned(fromByteOffset: offset, as: Int16.self).littleEndian
                let absValue = abs(Float(sample) / Float(Int16.max))
                peak = max(peak, absValue)
                sumSquares += Double(absValue * absValue)
                totalSampleCount += 1
                if absValue >= clippingThreshold {
                    clippedSampleCount += 1
                }
            }
        }
    }

    func summary() -> AudioLevelSummary {
        guard totalSampleCount > 0 else { return .empty }
        let rms = Float(sqrt(sumSquares / Double(totalSampleCount)))
        return AudioLevelSummary(
            peak: peak,
            rms: rms,
            clippedSampleCount: clippedSampleCount,
            totalSampleCount: totalSampleCount,
            retainedSampleCount: 0,
            isSilent: rms < silenceThreshold && peak < peakSilenceThreshold,
            isClipping: clippedSampleCount > 0 || peak >= clippingThreshold
        )
    }
}
```

- [ ] **Step 4: Verify GREEN for pure model**

Run:

```bash
swiftc -typecheck LiveBuddy/Models/PreflightTest.swift LiveBuddyTests/PreflightTestTests.swift
```

Expected: typecheck passes for the new model/tests when compiled in the project target. If standalone `@testable import LiveBuddy` blocks direct `swiftc`, additionally run the full temp typecheck from the verification section after Task 1.

- [ ] **Step 5: Commit Task 1**

```bash
git add LiveBuddy/Models/PreflightTest.swift LiveBuddyTests/PreflightTestTests.swift
git commit -m "feat: add preflight test model"
```

---

## Task 2: Injectable preflight runner

**Files:**
- Create: `LiveBuddy/Services/PreflightTestRunner.swift`
- Modify: `LiveBuddyTests/PreflightTestTests.swift`

- [ ] **Step 1: Add failing runner tests with injected closures**

Append to `LiveBuddyTests/PreflightTestTests.swift`:

```swift
extension PreflightTestTests {
    @Test func runnerMarksNormalAudioAsPassed() async {
        let runner = PreflightTestRunner(
            providerCheck: { .valid(checkedAt: Date()) },
            permissionCheck: {
                PermissionStatusSnapshot(
                    microphone: PermissionStatus(requirement: .microphone, state: .granted, checkedAt: Date()),
                    screenRecording: PermissionStatus(requirement: .screenRecording, state: .granted, checkedAt: Date())
                )
            },
            microphoneSampler: { analyzer in
                analyzer.processPCM16(pcm16([0, 8_000, -8_000, 12_000]))
            },
            screenSampler: { _ in },
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
            providerCheck: { .valid(checkedAt: Date()) },
            permissionCheck: {
                PermissionStatusSnapshot(
                    microphone: PermissionStatus(requirement: .microphone, state: .granted, checkedAt: Date()),
                    screenRecording: PermissionStatus(requirement: .screenRecording, state: .granted, checkedAt: Date())
                )
            },
            microphoneSampler: { analyzer in
                analyzer.processPCM16(pcm16([0, 0, 10, -10]))
            },
            screenSampler: { _ in },
            subtitleCheck: {}
        )
        var settings = AppSettings()
        settings.audioSource = .microphone
        settings.apiKey = "test-key"

        let report = await runner.run(settings: settings) { _ in }

        #expect(report.steps.first { $0.id == .microphoneAudio }?.state == .warning)
    }

    @Test func runnerDoesNotRunGeminiClient() async {
        let runnerSource = try! String(contentsOfFile: "LiveBuddy/Services/PreflightTestRunner.swift")

        #expect(runnerSource.contains("GeminiLiveTranslateClient") == false)
    }
}
```

- [ ] **Step 2: Verify RED**

Run:

```bash
swiftc -typecheck $(find LiveBuddy/Models LiveBuddy/Services -name '*.swift' | sort) LiveBuddyTests/PreflightTestTests.swift 2>&1 | sed -n '1,160p'
```

Expected: failure because `PreflightTestRunner` does not exist.

- [ ] **Step 3: Implement runner with injection and live audio sampling hooks**

Create `LiveBuddy/Services/PreflightTestRunner.swift`:

```swift
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

        report = await runProvider(settings: settings, report: report, update: update)
        report = await runPermissions(settings: settings, report: report, update: update)
        report = await runAudioIfNeeded(settings: settings, report: report, update: update)
        report = await runSubtitle(report: report, update: update)
        report.finishedAt = Date()
        await update(report)
        return report
    }

    private func runProvider(settings: AppSettings, report: PreflightTestReport, update: ReportUpdate) async -> PreflightTestReport {
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

    private func runAudioStep(_ id: PreflightTestStepID, sampler: AudioSampler, report: PreflightTestReport, update: ReportUpdate) async -> PreflightTestReport {
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
```

- [ ] **Step 4: Add live factory after injected runner is green**

Append to `LiveBuddy/Services/PreflightTestRunner.swift`:

```swift
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
        try await Task.sleep(nanoseconds: UInt64(duration * 1_000_000_000))
        capture.stop()
        analyzer = box.snapshot()
    }

    private static func sampleScreen(duration: TimeInterval, analyzer: inout AudioLevelAnalyzer) async throws {
        let box = AudioLevelAnalyzerBox(analyzer)
        let capture = ScreenAudioCapture { data in
            box.process(data)
        }
        try await capture.start()
        try await Task.sleep(nanoseconds: UInt64(duration * 1_000_000_000))
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
```

- [ ] **Step 5: Verify runner**

Run:

```bash
python3 scripts/verify_p0_onboarding.py
rm -rf /tmp/livebuddy_typecheck && mkdir -p /tmp/livebuddy_typecheck
cp -R LiveBuddy /tmp/livebuddy_typecheck/LiveBuddy
python3 - <<'PY'
from pathlib import Path
for p in Path('/tmp/livebuddy_typecheck/LiveBuddy').rglob('*.swift'):
    text = p.read_text()
    marker = '\n#Preview {'
    idx = text.find(marker)
    if idx != -1:
        p.write_text(text[:idx].rstrip() + '\n')
PY
swiftc -typecheck $(find /tmp/livebuddy_typecheck/LiveBuddy -name '*.swift' | sort)
```

Expected: verifier passes; typecheck exits 0 with only pre-existing Sendable warnings if any.

- [ ] **Step 6: Commit Task 2**

```bash
git add LiveBuddy/Services/PreflightTestRunner.swift LiveBuddyTests/PreflightTestTests.swift
git commit -m "feat: add preflight test runner"
```

---

## Task 3: AppState integration and temporary subtitle test

**Files:**
- Modify: `LiveBuddy/Models/AppState.swift`
- Test: `LiveBuddyTests/PreflightTestTests.swift`

- [ ] **Step 1: Add static verifier checks before implementation**

Modify `scripts/verify_p0_onboarding.py` later in Task 5 to require these tokens. For this task, first inspect current absence:

```bash
rg -n "preflightTestReport|runPreflightTest|showTemporaryTestCaption" LiveBuddy/Models/AppState.swift || true
```

Expected: no matches before implementation.

- [ ] **Step 2: Add AppState properties**

In `LiveBuddy/Models/AppState.swift`, near existing published state, add:

```swift
@Published private(set) var preflightTestReport: PreflightTestReport = .idle
@Published private(set) var isRunningPreflightTest = false
```

- [ ] **Step 3: Add `runPreflightTest()`**

In `AppState`, near `runStartPreflight()`, add:

```swift
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
        self?.preflightTestReport = report
    }
    refreshSetupChecklist()
}
```

- [ ] **Step 4: Add temporary caption helper**

Add to `AppState`:

```swift
func showTemporaryTestCaption() async {
    let previousDraft = captionDraft
    NotificationCenter.default.post(name: .showCaptionWindow, object: nil)
    captionDraft = settings.interfaceLanguage.localized(.subtitleTestMessage)
    try? await Task.sleep(nanoseconds: 2_000_000_000)
    if !isRunning {
        captionDraft = previousDraft
    }
}
```

- [ ] **Step 5: Verify AppState typecheck**

Run the full temp typecheck command from Task 2 Step 5.

Expected: exits 0 with only pre-existing warnings.

- [ ] **Step 6: Commit Task 3**

```bash
git add LiveBuddy/Models/AppState.swift
git commit -m "feat: wire preflight test state"
```

---

## Task 4: UI and localization

**Files:**
- Modify: `LiveBuddy/Views/Settings/SettingsView.swift`
- Modify: `LiveBuddy/Models/InterfaceLanguage.swift`
- Modify: `scripts/verify_interface_language.py`

- [ ] **Step 1: Add localization keys to `InterfaceText`**

In `LiveBuddy/Models/InterfaceLanguage.swift`, add cases:

```swift
case test
case runTest
case preflightTest
case preflightTestDescription
case apiKeyTest
case permissionsTest
case microphoneAudioTest
case screenAudioTest
case subtitleWindowTest
case testPassed
case testWarning
case testFailed
case testRunning
case audioDetected
case audioTooQuiet
case audioClippingDetected
case subtitleTestMessage
```

- [ ] **Step 2: Add English translations**

In the English dictionary, add:

```swift
.test: "Test",
.runTest: "Run Test",
.preflightTest: "Preflight Test",
.preflightTestDescription: "Check API access, permissions, audio input, and subtitle display before starting translation.",
.apiKeyTest: "API Key",
.permissionsTest: "Permissions",
.microphoneAudioTest: "Microphone Audio",
.screenAudioTest: "Screen Audio",
.subtitleWindowTest: "Subtitle Window",
.testPassed: "Passed",
.testWarning: "Needs attention",
.testFailed: "Failed",
.testRunning: "Running",
.audioDetected: "Audio detected",
.audioTooQuiet: "Audio is too quiet",
.audioClippingDetected: "Audio clipping detected",
.subtitleTestMessage: "LiveBuddy subtitle test",
```

- [ ] **Step 3: Add translations for Chinese, Japanese, Korean, Spanish, French, German, Vietnamese**

Use concise user-facing equivalents:

Chinese:

```swift
.test: "测试",
.runTest: "运行测试",
.preflightTest: "翻译前测试",
.preflightTestDescription: "开始翻译前检查 API、权限、音频输入和字幕显示。",
.apiKeyTest: "API 密钥",
.permissionsTest: "权限",
.microphoneAudioTest: "麦克风音频",
.screenAudioTest: "屏幕音频",
.subtitleWindowTest: "字幕窗口",
.testPassed: "已通过",
.testWarning: "需要注意",
.testFailed: "失败",
.testRunning: "运行中",
.audioDetected: "检测到音频",
.audioTooQuiet: "音频过低",
.audioClippingDetected: "检测到爆音",
.subtitleTestMessage: "LiveBuddy 字幕测试",
```

Japanese:

```swift
.test: "テスト",
.runTest: "テストを実行",
.preflightTest: "開始前テスト",
.preflightTestDescription: "翻訳開始前に API、権限、音声入力、字幕表示を確認します。",
.apiKeyTest: "API キー",
.permissionsTest: "権限",
.microphoneAudioTest: "マイク音声",
.screenAudioTest: "画面音声",
.subtitleWindowTest: "字幕ウィンドウ",
.testPassed: "合格",
.testWarning: "要確認",
.testFailed: "失敗",
.testRunning: "実行中",
.audioDetected: "音声を検出しました",
.audioTooQuiet: "音声が小さすぎます",
.audioClippingDetected: "クリッピングを検出しました",
.subtitleTestMessage: "LiveBuddy 字幕テスト",
```

Korean:

```swift
.test: "테스트",
.runTest: "테스트 실행",
.preflightTest: "시작 전 테스트",
.preflightTestDescription: "번역 시작 전에 API, 권한, 오디오 입력, 자막 표시를 확인합니다.",
.apiKeyTest: "API 키",
.permissionsTest: "권한",
.microphoneAudioTest: "마이크 오디오",
.screenAudioTest: "화면 오디오",
.subtitleWindowTest: "자막 창",
.testPassed: "통과",
.testWarning: "확인 필요",
.testFailed: "실패",
.testRunning: "실행 중",
.audioDetected: "오디오 감지됨",
.audioTooQuiet: "오디오가 너무 작습니다",
.audioClippingDetected: "클리핑 감지됨",
.subtitleTestMessage: "LiveBuddy 자막 테스트",
```

Spanish:

```swift
.test: "Prueba",
.runTest: "Ejecutar prueba",
.preflightTest: "Prueba previa",
.preflightTestDescription: "Comprueba API, permisos, entrada de audio y subtítulos antes de traducir.",
.apiKeyTest: "Clave API",
.permissionsTest: "Permisos",
.microphoneAudioTest: "Audio del micrófono",
.screenAudioTest: "Audio de pantalla",
.subtitleWindowTest: "Ventana de subtítulos",
.testPassed: "Aprobado",
.testWarning: "Revisar",
.testFailed: "Falló",
.testRunning: "Ejecutando",
.audioDetected: "Audio detectado",
.audioTooQuiet: "Audio demasiado bajo",
.audioClippingDetected: "Recorte de audio detectado",
.subtitleTestMessage: "Prueba de subtítulos de LiveBuddy",
```

French:

```swift
.test: "Test",
.runTest: "Lancer le test",
.preflightTest: "Test préalable",
.preflightTestDescription: "Vérifie l’API, les permissions, l’entrée audio et les sous-titres avant la traduction.",
.apiKeyTest: "Clé API",
.permissionsTest: "Autorisations",
.microphoneAudioTest: "Audio du micro",
.screenAudioTest: "Audio de l’écran",
.subtitleWindowTest: "Fenêtre de sous-titres",
.testPassed: "Réussi",
.testWarning: "À vérifier",
.testFailed: "Échec",
.testRunning: "En cours",
.audioDetected: "Audio détecté",
.audioTooQuiet: "Audio trop faible",
.audioClippingDetected: "Écrêtage audio détecté",
.subtitleTestMessage: "Test de sous-titres LiveBuddy",
```

German:

```swift
.test: "Test",
.runTest: "Test ausführen",
.preflightTest: "Vorabtest",
.preflightTestDescription: "Prüft API, Berechtigungen, Audioeingang und Untertitelanzeige vor der Übersetzung.",
.apiKeyTest: "API-Schlüssel",
.permissionsTest: "Berechtigungen",
.microphoneAudioTest: "Mikrofon-Audio",
.screenAudioTest: "Bildschirm-Audio",
.subtitleWindowTest: "Untertitelfenster",
.testPassed: "Bestanden",
.testWarning: "Prüfen",
.testFailed: "Fehlgeschlagen",
.testRunning: "Läuft",
.audioDetected: "Audio erkannt",
.audioTooQuiet: "Audio ist zu leise",
.audioClippingDetected: "Audio-Clipping erkannt",
.subtitleTestMessage: "LiveBuddy Untertiteltest",
```

Vietnamese:

```swift
.test: "Kiểm tra",
.runTest: "Chạy kiểm tra",
.preflightTest: "Kiểm tra trước khi dịch",
.preflightTestDescription: "Kiểm tra API, quyền, âm thanh đầu vào và phụ đề trước khi bắt đầu dịch.",
.apiKeyTest: "Khóa API",
.permissionsTest: "Quyền",
.microphoneAudioTest: "Âm thanh micrô",
.screenAudioTest: "Âm thanh màn hình",
.subtitleWindowTest: "Cửa sổ phụ đề",
.testPassed: "Đạt",
.testWarning: "Cần chú ý",
.testFailed: "Thất bại",
.testRunning: "Đang chạy",
.audioDetected: "Đã phát hiện âm thanh",
.audioTooQuiet: "Âm thanh quá nhỏ",
.audioClippingDetected: "Phát hiện vỡ tiếng",
.subtitleTestMessage: "Kiểm tra phụ đề LiveBuddy",
```

- [ ] **Step 4: Add test navigation UI**

In `NavigationItem`, add:

```swift
case test
```

In the Settings sidebar `Section(appState.t(.settings))`, add:

```swift
NavigationLink(value: NavigationItem.test) {
    Label(appState.t(.test), systemImage: "checkmark.seal")
}
```

In the detail switch, add:

```swift
case .test:
    preflightTestForm
```

- [ ] **Step 5: Add `preflightTestForm` and row helpers**

In `SettingsView`, add:

```swift
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
```

Add below `SettingsView`:

```swift
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
        case .apiKey: language.localized(.apiKeyTest)
        case .permissions: language.localized(.permissionsTest)
        case .microphoneAudio: language.localized(.microphoneAudioTest)
        case .screenAudio: language.localized(.screenAudioTest)
        case .subtitleWindow: language.localized(.subtitleWindowTest)
        }
    }

    private var iconName: String {
        switch step.state {
        case .pending: "circle"
        case .running: "arrow.triangle.2.circlepath"
        case .passed: "checkmark.circle.fill"
        case .warning: "exclamationmark.triangle.fill"
        case .failed: "xmark.octagon.fill"
        }
    }

    private var iconColor: Color {
        switch step.state {
        case .pending: .secondary
        case .running: .blue
        case .passed: .green
        case .warning: .orange
        case .failed: .red
        }
    }
}
```

- [ ] **Step 6: Update interface verifier**

In `scripts/verify_interface_language.py`, add the new localization keys to `required_keys`.

- [ ] **Step 7: Verify UI/localization**

Run:

```bash
python3 scripts/verify_interface_language.py
python3 scripts/verify_p0_onboarding.py
```

Expected: both pass.

- [ ] **Step 8: Commit Task 4**

```bash
git add LiveBuddy/Views/Settings/SettingsView.swift LiveBuddy/Models/InterfaceLanguage.swift scripts/verify_interface_language.py
git commit -m "feat: add preflight test UI"
```

---

## Task 5: Static verifier and docs

**Files:**
- Modify: `scripts/verify_p0_onboarding.py`
- Modify: `README.md`

- [ ] **Step 1: Extend P0 verifier**

Add required files:

```python
"LiveBuddy/Models/PreflightTest.swift",
"LiveBuddy/Services/PreflightTestRunner.swift",
```

Add AppState token checks:

```python
for token in ["preflightTestReport", "isRunningPreflightTest", "runPreflightTest", "showTemporaryTestCaption"]:
    if token not in text:
        errors.append(f"AppState must expose preflight test support through {token}")
```

Add SettingsView checks:

```python
if "NavigationItem.test" not in text and "case test" not in text:
    errors.append("SettingsView must expose Test navigation item")
if "preflightTestForm" not in text or "runPreflightTest" not in text:
    errors.append("SettingsView must expose preflight test form")
```

Add runner checks:

```python
preflight_runner_file = root / "LiveBuddy/Services/PreflightTestRunner.swift"
if preflight_runner_file.exists():
    text = preflight_runner_file.read_text()
    for token in ["struct PreflightTestRunner", "AudioLevelAnalyzer", "MicrophoneCapture", "ScreenAudioCapture"]:
        if token not in text:
            errors.append(f"PreflightTestRunner.swift missing {token}")
    if "GeminiLiveTranslateClient" in text:
        errors.append("PreflightTestRunner must not create a Gemini Live translation session")
```

- [ ] **Step 2: Update README**

Add Key Feature bullet:

```markdown
*   **Preflight Test Page**: Run a one-click diagnostic for API key, permissions, selected audio input, and subtitle window rendering before starting a real translation session.
```

Add Configuration row:

```markdown
| **Diagnostics** | Preflight test | Checks API key, permissions, microphone/screen audio levels, and subtitle window rendering without starting Gemini or saving transcripts. |
```

- [ ] **Step 3: Run full local verification**

Run:

```bash
python3 scripts/verify_p0_onboarding.py && python3 scripts/verify_interface_language.py && python3 scripts/verify_ci_workflow.py
rm -rf /tmp/livebuddy_typecheck && mkdir -p /tmp/livebuddy_typecheck
cp -R LiveBuddy /tmp/livebuddy_typecheck/LiveBuddy
python3 - <<'PY'
from pathlib import Path
for p in Path('/tmp/livebuddy_typecheck/LiveBuddy').rglob('*.swift'):
    text = p.read_text()
    marker = '\n#Preview {'
    idx = text.find(marker)
    if idx != -1:
        p.write_text(text[:idx].rstrip() + '\n')
PY
swiftc -typecheck $(find /tmp/livebuddy_typecheck/LiveBuddy -name '*.swift' | sort)
```

Expected: Python verifiers pass; Swift typecheck exits 0 with only known pre-existing Sendable warnings if any.

- [ ] **Step 4: Commit Task 5**

```bash
git add scripts/verify_p0_onboarding.py README.md
git commit -m "docs: document preflight test page"
```

---

## Task 6: Push and CI

**Files:**
- No code changes unless CI fails.

- [ ] **Step 1: Push to target main**

```bash
git push target HEAD:main
```

Expected: push succeeds.

- [ ] **Step 2: Watch CI**

```bash
gh run list --repo SuLea-IT/translate-macos --limit 5
gh run watch <new-run-id> --repo SuLea-IT/translate-macos --exit-status
```

Expected: GitHub Actions build and unit tests pass.

- [ ] **Step 3: If CI fails, debug systematically**

Use `superpowers:systematic-debugging` before any fix. Read the failing job output, identify root cause, create/adjust a failing local check, then fix one variable at a time.

---

## Self-Review Checklist

- Spec coverage:
  - API key test: Task 2 runner, Task 3 AppState, Task 4 UI.
  - Permission test: Task 2 runner.
  - Microphone/screen audio short sampling: Task 2 live factory.
  - Peak/RMS/silence/clipping: Task 1 analyzer.
  - Subtitle window test: Task 3 helper, Task 4 UI.
  - No Gemini session: Task 2 verifier and runner design.
  - No transcript/audio retention: Task 1 analyzer, Task 3 temporary caption only.
  - Localization: Task 4.
  - Docs/CI: Task 5 and Task 6.
- Placeholder scan: no TODO/TBD placeholders are present.
- Type consistency:
  - `PreflightTestStepID`, `PreflightTestStepState`, `PreflightTestReport`, `AudioLevelAnalyzer`, `PreflightTestRunner`, `runPreflightTest`, and `preflightTestForm` are used consistently across tasks.
