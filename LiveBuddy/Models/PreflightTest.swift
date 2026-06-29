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

    init(silenceThreshold: Float = 0.01, peakSilenceThreshold: Float = 0.02, clippingThreshold: Float = 0.98) {
        self.silenceThreshold = silenceThreshold
        self.peakSilenceThreshold = peakSilenceThreshold
        self.clippingThreshold = clippingThreshold
    }

    mutating func processPCM16(_ data: Data) {
        guard data.count >= 2 else { return }
        let usableCount = data.count - (data.count % 2)
        data.withUnsafeBytes { rawBuffer in
            guard let base = rawBuffer.baseAddress else { return }
            for offset in stride(from: 0, to: usableCount, by: 2) {
                let sample = base.loadUnaligned(fromByteOffset: offset, as: Int16.self).littleEndian
                let normalized: Float
                if sample == Int16.min {
                    normalized = 1
                } else {
                    normalized = abs(Float(sample) / Float(Int16.max))
                }
                peak = max(peak, normalized)
                sumSquares += Double(normalized * normalized)
                totalSampleCount += 1
                if normalized >= clippingThreshold {
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
