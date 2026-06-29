import Foundation
import Testing
@testable import LiveBuddy

struct ProviderHealthStatusTests {
    @Test func emptyKeyReturnsMissingWithoutNetworkCall() async {
        final class CallRecorder {
            var wasCalled = false
        }
        let recorder = CallRecorder()
        let service = ProviderHealthService { _ in
            recorder.wasCalled = true
            return .success(())
        }

        let status = await service.verify(apiKey: "   ")

        #expect(status == .missing)
        #expect(recorder.wasCalled == false)
    }

    @Test func successfulPingReturnsValidStatus() async {
        let service = ProviderHealthService { _ in .success(()) }

        let status = await service.verify(apiKey: "abc")

        if case .valid = status {
            #expect(true)
        } else {
            Issue.record("Expected valid provider status")
        }
    }

    @Test func failedPingReturnsInvalidStatus() async {
        let service = ProviderHealthService { _ in
            .failure(NSError(domain: "LiveBuddy", code: 403, userInfo: [NSLocalizedDescriptionKey: "API key not valid"]))
        }

        let status = await service.verify(apiKey: "abc")

        if case .invalid(let message, _) = status {
            #expect(message.contains("API key"))
        } else {
            Issue.record("Expected invalid provider status")
        }
    }

    @Test func cancellationErrorReturnsUncheckedStatus() async {
        let service = ProviderHealthService { _ in
            .failure(CancellationError())
        }

        let status = await service.verify(apiKey: "abc")

        #expect(status == .unchecked)
    }

    @Test func urlCancellationReturnsUncheckedStatus() async {
        let service = ProviderHealthService { _ in
            .failure(URLError(.cancelled))
        }

        let status = await service.verify(apiKey: "abc")

        #expect(status == .unchecked)
    }
}
