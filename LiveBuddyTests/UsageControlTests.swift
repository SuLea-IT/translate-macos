import Foundation
import Testing
@testable import LiveBuddy

struct UsageControlTests {
    private func chunk(seconds: TimeInterval, at date: Date = Date(timeIntervalSince1970: 0), byte: UInt8 = 1) -> BufferedAudioChunk {
        let byteCount = Int(seconds * 16_000 * 2)
        return BufferedAudioChunk(data: Data(repeating: byte, count: byteCount), capturedAt: date)
    }

    @Test func sentAudioDurationIsCountedFromPCMBytes() {
        let settings = LiveUsageSettings()
        let start = Date(timeIntervalSince1970: 1_000)
        var engine = UsageControlEngine(
            settings: settings,
            now: start,
            ledger: UsageLedger(dayKey: UsageLedger.dayKey(for: start), sentAudioSeconds: 30)
        )

        let decision = engine.ingest(chunk: chunk(seconds: 2, at: start), level: 0.08, now: start)

        #expect(decision.shouldSend)
        #expect(engine.snapshot.sessionSentAudioSeconds == 2)
        #expect(engine.snapshot.todaySentAudioSeconds == 32)
    }

    @Test func quietAudioEntersIdleWarningBeforePause() {
        var settings = LiveUsageSettings()
        settings.idlePauseDelaySeconds = 60
        settings.idleWarningSeconds = 10
        let start = Date(timeIntervalSince1970: 2_000)
        var engine = UsageControlEngine(settings: settings, now: start, ledger: .empty(for: start))

        _ = engine.ingest(chunk: chunk(seconds: 1, at: start), level: 0.08, now: start)
        let warning = engine.ingest(chunk: chunk(seconds: 1, at: start.addingTimeInterval(51)), level: 0.0, now: start.addingTimeInterval(51))

        #expect(warning.shouldSend)
        #expect(warning.pauseReason == nil)
        #expect(engine.snapshot.runtimeState == .idleWarning(remainingSeconds: 9))
    }

    @Test func quietAudioSoftPausesAfterIdleDelay() {
        var settings = LiveUsageSettings()
        settings.idlePauseDelaySeconds = 60
        let start = Date(timeIntervalSince1970: 3_000)
        var engine = UsageControlEngine(settings: settings, now: start, ledger: .empty(for: start))

        _ = engine.ingest(chunk: chunk(seconds: 1, at: start), level: 0.08, now: start)
        let pause = engine.ingest(chunk: chunk(seconds: 1, at: start.addingTimeInterval(61)), level: 0.0, now: start.addingTimeInterval(61))

        #expect(pause.shouldSend == false)
        #expect(pause.pauseReason == .idle)
        #expect(engine.snapshot.runtimeState == .paused(reason: .idle))
    }

    @Test func hysteresisKeepsMidLevelAudioFromFlappingToIdle() {
        var settings = LiveUsageSettings()
        settings.idlePauseDelaySeconds = 10
        settings.speechStartThreshold = 0.020
        settings.speechEndThreshold = 0.012
        let start = Date(timeIntervalSince1970: 4_000)
        var engine = UsageControlEngine(settings: settings, now: start, ledger: .empty(for: start))

        _ = engine.ingest(chunk: chunk(seconds: 1, at: start), level: 0.030, now: start)
        let mid = engine.ingest(chunk: chunk(seconds: 1, at: start.addingTimeInterval(20)), level: 0.015, now: start.addingTimeInterval(20))

        #expect(mid.shouldSend)
        #expect(mid.pauseReason == nil)
        #expect(engine.snapshot.runtimeState == .active)
    }

    @Test func idleResumeReturnsPrerollAndPausedBuffer() {
        var settings = LiveUsageSettings()
        settings.idlePauseDelaySeconds = 3
        settings.prerollSeconds = 3
        settings.resumeBufferLimitSeconds = 15
        let start = Date(timeIntervalSince1970: 5_000)
        var engine = UsageControlEngine(settings: settings, now: start, ledger: .empty(for: start))

        _ = engine.ingest(chunk: chunk(seconds: 1, at: start, byte: 1), level: 0.08, now: start)
        _ = engine.ingest(chunk: chunk(seconds: 1, at: start.addingTimeInterval(1), byte: 2), level: 0.08, now: start.addingTimeInterval(1))
        _ = engine.ingest(chunk: chunk(seconds: 1, at: start.addingTimeInterval(2), byte: 3), level: 0.08, now: start.addingTimeInterval(2))
        _ = engine.ingest(chunk: chunk(seconds: 1, at: start.addingTimeInterval(6), byte: 4), level: 0.0, now: start.addingTimeInterval(6))
        _ = engine.ingest(chunk: chunk(seconds: 1, at: start.addingTimeInterval(7), byte: 5), level: 0.0, now: start.addingTimeInterval(7))

        let resume = engine.ingest(chunk: chunk(seconds: 1, at: start.addingTimeInterval(8), byte: 6), level: 0.08, now: start.addingTimeInterval(8))

        #expect(resume.shouldResume)
        #expect(resume.replayChunks.count >= 4)
        #expect(resume.replayChunks.contains { $0.data.first == 3 })
        #expect(resume.replayChunks.last?.data.first == 6)
        #expect(engine.snapshot.runtimeState == .resuming)
    }

    @Test func perSessionLimitPausesBeforeSendingMoreAudio() {
        var settings = LiveUsageSettings()
        settings.perSessionLimitMinutes = 0.05
        settings.idleAutoPauseEnabled = false
        let start = Date(timeIntervalSince1970: 6_000)
        var engine = UsageControlEngine(settings: settings, now: start, ledger: .empty(for: start))

        _ = engine.ingest(chunk: chunk(seconds: 2, at: start), level: 0.08, now: start)
        let limit = engine.ingest(chunk: chunk(seconds: 2, at: start.addingTimeInterval(2)), level: 0.08, now: start.addingTimeInterval(2))

        #expect(limit.shouldSend == false)
        #expect(limit.pauseReason == .sessionLimit)
        #expect(engine.snapshot.sessionSentAudioSeconds == 2)
    }

    @Test func dailyLedgerResetsWhenDayChanges() {
        let today = Date(timeIntervalSince1970: 1_783_008_000)
        let yesterday = today.addingTimeInterval(-86_400)
        let stale = UsageLedger(dayKey: UsageLedger.dayKey(for: yesterday), sentAudioSeconds: 123)

        let engine = UsageControlEngine(settings: LiveUsageSettings(), now: today, ledger: stale)

        #expect(engine.ledger.dayKey == UsageLedger.dayKey(for: today))
        #expect(engine.snapshot.todaySentAudioSeconds == 0)
    }
}

extension UsageControlTests {
    @Test func legacySettingsDecodeUsageControlDefaults() throws {
        let legacyJSON = #"{"activeProvider":"gemini","targetLanguageCode":"ja"}"#.data(using: .utf8)!

        let settings = try JSONDecoder().decode(AppSettings.self, from: legacyJSON)

        #expect(settings.usageControls.idleAutoPauseEnabled)
        #expect(settings.usageControls.idlePauseDelaySeconds == 60)
    }


    @Test func legacyEstimatedCostSettingIsIgnoredWhenEncodingUsageControls() throws {
        let legacyJSON = #"{"activeProvider":"gemini","targetLanguageCode":"ja","usageControls":{"idleAutoPauseEnabled":true,"idlePauseDelaySeconds":60,"idleWarningSeconds":10,"prerollSeconds":3,"resumeBufferLimitSeconds":15,"speechStartThreshold":0.02,"speechEndThreshold":0.012,"estimatedCostPerMinuteUSD":0.99,"perSessionLimitMinutes":15,"dailyLimitMinutes":45}}"#.data(using: .utf8)!

        let settings = try JSONDecoder().decode(AppSettings.self, from: legacyJSON)
        let encoded = try JSONEncoder().encode(settings)
        let encodedString = try #require(String(data: encoded, encoding: .utf8))

        #expect(settings.usageControls.perSessionLimitMinutes == 15)
        #expect(settings.usageControls.dailyLimitMinutes == 45)
        #expect(!encodedString.contains("estimatedCostPerMinuteUSD"))
    }

    @Test func usageControlSettingsRoundTripThroughCodable() throws {
        var settings = AppSettings()
        settings.usageControls.idleAutoPauseEnabled = false
        settings.usageControls.perSessionLimitMinutes = 15
        settings.usageControls.dailyLimitMinutes = 45

        let data = try JSONEncoder().encode(settings)
        let decoded = try JSONDecoder().decode(AppSettings.self, from: data)

        #expect(decoded.usageControls.idleAutoPauseEnabled == false)
        #expect(decoded.usageControls.perSessionLimitMinutes == 15)
        #expect(decoded.usageControls.dailyLimitMinutes == 45)
    }
}
