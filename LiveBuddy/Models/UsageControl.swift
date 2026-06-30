import Foundation

struct LiveUsageSettings: Codable, Equatable {
    var idleAutoPauseEnabled = true
    var idlePauseDelaySeconds = 60.0
    var idleWarningSeconds = 10.0
    var prerollSeconds = 3.0
    var resumeBufferLimitSeconds = 15.0
    var speechStartThreshold = 0.020
    var speechEndThreshold = 0.012
    var perSessionLimitMinutes = 0.0
    var dailyLimitMinutes = 0.0

    var sanitized: LiveUsageSettings {
        var copy = self
        copy.idlePauseDelaySeconds = max(5, copy.idlePauseDelaySeconds)
        copy.idleWarningSeconds = min(max(0, copy.idleWarningSeconds), copy.idlePauseDelaySeconds)
        copy.prerollSeconds = min(max(0, copy.prerollSeconds), 10)
        copy.resumeBufferLimitSeconds = min(max(copy.prerollSeconds, copy.resumeBufferLimitSeconds), 60)
        copy.speechStartThreshold = min(max(0.001, copy.speechStartThreshold), 1)
        copy.speechEndThreshold = min(max(0.0005, copy.speechEndThreshold), copy.speechStartThreshold)
        copy.perSessionLimitMinutes = max(0, copy.perSessionLimitMinutes)
        copy.dailyLimitMinutes = max(0, copy.dailyLimitMinutes)
        return copy
    }
}

enum UsageControlPauseReason: String, Codable, Equatable {
    case idle
    case sessionLimit
    case dailyLimit
}

enum UsageControlRuntimeState: Equatable {
    case active
    case idleWarning(remainingSeconds: Int)
    case paused(reason: UsageControlPauseReason)
    case resuming
}

struct LiveUsageSnapshot: Equatable {
    var sessionSentAudioSeconds: TimeInterval = 0
    var todaySentAudioSeconds: TimeInterval = 0
    var runtimeState: UsageControlRuntimeState = .active
    var resumeBufferOverflowed = false
}

struct UsageLedger: Codable, Equatable {
    var dayKey: String
    var sentAudioSeconds: TimeInterval

    static func empty(for date: Date, calendar: Calendar = .current) -> UsageLedger {
        UsageLedger(dayKey: dayKey(for: date, calendar: calendar), sentAudioSeconds: 0)
    }

    static func dayKey(for date: Date, calendar: Calendar = .current) -> String {
        let components = calendar.dateComponents([.year, .month, .day], from: date)
        let year = components.year ?? 1970
        let month = components.month ?? 1
        let day = components.day ?? 1
        return String(format: "%04d-%02d-%02d", year, month, day)
    }
}

struct BufferedAudioChunk: Equatable {
    var data: Data
    var capturedAt: Date

    var duration: TimeInterval {
        Double(data.count) / 32_000.0
    }
}

struct UsageControlDecision: Equatable {
    var shouldSend: Bool
    var pauseReason: UsageControlPauseReason?
    var shouldResume: Bool
    var replayChunks: [BufferedAudioChunk]

    static let send = UsageControlDecision(shouldSend: true, pauseReason: nil, shouldResume: false, replayChunks: [])

    static func pause(_ reason: UsageControlPauseReason) -> UsageControlDecision {
        UsageControlDecision(shouldSend: false, pauseReason: reason, shouldResume: false, replayChunks: [])
    }

    static func resume(replayChunks: [BufferedAudioChunk]) -> UsageControlDecision {
        UsageControlDecision(shouldSend: false, pauseReason: nil, shouldResume: true, replayChunks: replayChunks)
    }

    static let hold = UsageControlDecision(shouldSend: false, pauseReason: nil, shouldResume: false, replayChunks: [])
}

struct UsageControlEngine {
    private(set) var settings: LiveUsageSettings
    private(set) var snapshot: LiveUsageSnapshot
    private(set) var ledger: UsageLedger

    private var sessionSentAudioSeconds: TimeInterval = 0
    private var lastVoiceActivityAt: Date
    private var lastTranscriptActivityAt: Date
    private var speechActive = false
    private var prerollBuffer: [BufferedAudioChunk] = []
    private var pausedBuffer: [BufferedAudioChunk] = []
    private var pausedReason: UsageControlPauseReason?
    private var didOverflowPausedBuffer = false

    init(settings: LiveUsageSettings, now: Date, ledger: UsageLedger) {
        let sanitized = settings.sanitized
        self.settings = sanitized
        let todayKey = UsageLedger.dayKey(for: now)
        if ledger.dayKey == todayKey {
            self.ledger = ledger
        } else {
            self.ledger = .empty(for: now)
        }
        self.snapshot = LiveUsageSnapshot(todaySentAudioSeconds: self.ledger.sentAudioSeconds)
        self.lastVoiceActivityAt = now
        self.lastTranscriptActivityAt = now
        refreshSnapshot(runtimeState: .active)
    }

    mutating func updateSettings(_ settings: LiveUsageSettings, now: Date) {
        self.settings = settings.sanitized
        resetLedgerIfNeeded(now: now)
        refreshSnapshot(runtimeState: snapshot.runtimeState)
    }

    mutating func reevaluatePauseAfterSettingsChange(now: Date) -> UsageControlDecision {
        resetLedgerIfNeeded(now: now)
        if let limitReason = currentLimitReason() {
            pausedReason = limitReason
            refreshSnapshot(runtimeState: .paused(reason: limitReason))
            return .pause(limitReason)
        }
        guard let pausedReason else {
            refreshSnapshot(runtimeState: snapshot.runtimeState)
            return .hold
        }

        switch pausedReason {
        case .idle:
            guard settings.idleAutoPauseEnabled else {
                return resumeReplayIfAllowed()
            }
        case .sessionLimit, .dailyLimit:
            return resumeReplayIfAllowed()
        }

        refreshSnapshot(runtimeState: .paused(reason: pausedReason))
        return .hold
    }

    mutating func resetSession(now: Date, ledger: UsageLedger? = nil) {
        if let ledger {
            self.ledger = ledger.dayKey == UsageLedger.dayKey(for: now) ? ledger : .empty(for: now)
        } else {
            resetLedgerIfNeeded(now: now)
        }
        sessionSentAudioSeconds = 0
        lastVoiceActivityAt = now
        lastTranscriptActivityAt = now
        speechActive = false
        prerollBuffer.removeAll(keepingCapacity: true)
        pausedBuffer.removeAll(keepingCapacity: true)
        pausedReason = nil
        didOverflowPausedBuffer = false
        refreshSnapshot(runtimeState: .active)
    }

    mutating func noteTranscriptActivity(at date: Date) {
        lastTranscriptActivityAt = date
        if pausedReason == nil {
            refreshSnapshot(runtimeState: .active)
        }
    }

    mutating func ingest(chunk: BufferedAudioChunk, level: Float, now: Date) -> UsageControlDecision {
        resetLedgerIfNeeded(now: now)
        updateSpeechState(level: level, now: now)

        if let pausedReason {
            appendPaused(chunk)
            if speechActive {
                return resumeReplayIfAllowed()
            }
            refreshSnapshot(runtimeState: .paused(reason: pausedReason))
            return .hold
        }

        appendPreroll(chunk)

        if let limitReason = limitReasonIfSending(chunk.duration) {
            self.pausedReason = limitReason
            appendPaused(chunk)
            refreshSnapshot(runtimeState: .paused(reason: limitReason))
            return .pause(limitReason)
        }

        if settings.idleAutoPauseEnabled, !speechActive {
            let idleReference = max(lastVoiceActivityAt, lastTranscriptActivityAt)
            let idleSeconds = now.timeIntervalSince(idleReference)
            if idleSeconds >= settings.idlePauseDelaySeconds {
                pausedReason = .idle
                appendPaused(chunk)
                refreshSnapshot(runtimeState: .paused(reason: .idle))
                return .pause(.idle)
            }
            let remaining = settings.idlePauseDelaySeconds - idleSeconds
            if remaining <= settings.idleWarningSeconds {
                refreshSnapshot(runtimeState: .idleWarning(remainingSeconds: max(0, Int(ceil(remaining)))))
                return .send
            }
        }

        refreshSnapshot(runtimeState: .active)
        return .send
    }

    mutating func markResumed(now: Date) {
        pausedReason = nil
        pausedBuffer.removeAll(keepingCapacity: true)
        didOverflowPausedBuffer = false
        lastVoiceActivityAt = now
        lastTranscriptActivityAt = max(lastTranscriptActivityAt, now)
        refreshSnapshot(runtimeState: .active)
    }

    mutating func forcePause(_ reason: UsageControlPauseReason) {
        pausedReason = reason
        refreshSnapshot(runtimeState: .paused(reason: reason))
    }

    mutating func forceActive(now: Date) {
        pausedReason = nil
        pausedBuffer.removeAll(keepingCapacity: true)
        didOverflowPausedBuffer = false
        lastVoiceActivityAt = now
        lastTranscriptActivityAt = now
        refreshSnapshot(runtimeState: .active)
    }

    mutating func markSent(_ chunk: BufferedAudioChunk) {
        countSent(chunk.duration)
        refreshSnapshot(runtimeState: snapshot.runtimeState)
    }

    mutating func markReplaySent(_ chunks: [BufferedAudioChunk]) {
        for chunk in chunks {
            countSent(chunk.duration)
        }
        refreshSnapshot(runtimeState: snapshot.runtimeState)
    }

    private mutating func resumeReplayIfAllowed() -> UsageControlDecision {
        let replayDuration = replayBufferDuration
        if let limitReason = limitReasonIfSending(replayDuration) {
            pausedReason = limitReason
            refreshSnapshot(runtimeState: .paused(reason: limitReason))
            return .hold
        }
        let replay = replayBuffer
        refreshSnapshot(runtimeState: .resuming)
        return .resume(replayChunks: replay)
    }

    private var replayBuffer: [BufferedAudioChunk] {
        prerollBuffer + pausedBuffer
    }

    private var replayBufferDuration: TimeInterval {
        replayBuffer.reduce(0) { $0 + $1.duration }
    }

    private mutating func updateSpeechState(level: Float, now: Date) {
        let value = Double(level)
        if value >= settings.speechStartThreshold {
            speechActive = true
        } else if value <= settings.speechEndThreshold {
            speechActive = false
        }
        if speechActive {
            lastVoiceActivityAt = now
        }
    }

    private mutating func appendPreroll(_ chunk: BufferedAudioChunk) {
        guard settings.prerollSeconds > 0 else { return }
        prerollBuffer.append(chunk)
        trim(&prerollBuffer, toDuration: settings.prerollSeconds, overflowFlag: nil)
    }

    private mutating func appendPaused(_ chunk: BufferedAudioChunk) {
        pausedBuffer.append(chunk)
        trim(&pausedBuffer, toDuration: settings.resumeBufferLimitSeconds, overflowFlag: &didOverflowPausedBuffer)
    }

    private func limitReasonIfSending(_ duration: TimeInterval) -> UsageControlPauseReason? {
        let projectedSession = sessionSentAudioSeconds + duration
        let projectedToday = ledger.sentAudioSeconds + duration
        if settings.perSessionLimitMinutes > 0, projectedSession > settings.perSessionLimitMinutes * 60 {
            return .sessionLimit
        }
        if settings.dailyLimitMinutes > 0, projectedToday > settings.dailyLimitMinutes * 60 {
            return .dailyLimit
        }
        return nil
    }

    private func currentLimitReason() -> UsageControlPauseReason? {
        if settings.perSessionLimitMinutes > 0, sessionSentAudioSeconds >= settings.perSessionLimitMinutes * 60 {
            return .sessionLimit
        }
        if settings.dailyLimitMinutes > 0, ledger.sentAudioSeconds >= settings.dailyLimitMinutes * 60 {
            return .dailyLimit
        }
        return nil
    }

    private mutating func countSent(_ duration: TimeInterval) {
        guard duration > 0 else { return }
        sessionSentAudioSeconds += duration
        ledger.sentAudioSeconds += duration
    }

    private mutating func resetLedgerIfNeeded(now: Date) {
        let todayKey = UsageLedger.dayKey(for: now)
        if ledger.dayKey != todayKey {
            ledger = .empty(for: now)
        }
    }

    private mutating func refreshSnapshot(runtimeState: UsageControlRuntimeState) {
        snapshot = LiveUsageSnapshot(
            sessionSentAudioSeconds: sessionSentAudioSeconds,
            todaySentAudioSeconds: ledger.sentAudioSeconds,
            runtimeState: runtimeState,
            resumeBufferOverflowed: didOverflowPausedBuffer
        )
    }

    private func trim(_ buffer: inout [BufferedAudioChunk], toDuration maxDuration: TimeInterval, overflowFlag: UnsafeMutablePointer<Bool>?) {
        guard maxDuration > 0 else {
            if !buffer.isEmpty { overflowFlag?.pointee = true }
            buffer.removeAll(keepingCapacity: true)
            return
        }
        var total = buffer.reduce(0) { $0 + $1.duration }
        while total > maxDuration, !buffer.isEmpty {
            let removed = buffer.removeFirst()
            total -= removed.duration
            overflowFlag?.pointee = true
        }
    }
}
