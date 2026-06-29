import Foundation
import Testing
@testable import LiveBuddy

struct ConnectionRecoveryTests {
    @Test func exponentialBackoffIsCapped() {
        let policy = ConnectionRecoveryPolicy(maxAttempts: 4, initialDelay: 0.75, multiplier: 2, maxDelay: 3)

        #expect(policy.delay(forAttempt: 1) == 0.75)
        #expect(policy.delay(forAttempt: 2) == 1.5)
        #expect(policy.delay(forAttempt: 3) == 3.0)
        #expect(policy.delay(forAttempt: 4) == 3.0)
    }

    @Test func transportEventsAreRecoverable() {
        #expect(LiveConnectionEvent.disconnected("network lost").isRecoverable)
        #expect(LiveConnectionEvent.socketClosed("goingAway").isRecoverable)
        #expect(LiveConnectionEvent.sendFailed("timed out").isRecoverable)
    }

    @Test func authAndQuotaServerErrorsAreTerminal() {
        #expect(LiveConnectionEvent.serverError("API key not valid").isRecoverable == false)
        #expect(LiveConnectionEvent.serverError("quota exceeded").isRecoverable == false)
        #expect(LiveConnectionEvent.serverError("permission denied").isRecoverable == false)
    }

    @Test func transientServerErrorsAreRecoverable() {
        #expect(LiveConnectionEvent.serverError("503 unavailable").isRecoverable)
        #expect(LiveConnectionEvent.serverError("deadline exceeded").isRecoverable)
        #expect(LiveConnectionEvent.serverError("internal server error").isRecoverable)
    }

    @Test func parseFailuresAreNotRecoveredAutomatically() {
        #expect(LiveConnectionEvent.parseFailed("invalid JSON").isRecoverable == false)
    }
}
