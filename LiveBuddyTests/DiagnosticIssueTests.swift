import Foundation
import Testing
@testable import LiveBuddy

struct DiagnosticIssueTests {
    @Test func classifiesInvalidAPIKeyMessages() {
        let issue = DiagnosticClassifier.from(providerStatus: .invalid(message: "API_KEY_INVALID: API key not valid", checkedAt: Date()))

        #expect(issue?.code == .apiKeyInvalid)
        #expect(issue?.action == .openProviderSettings)
    }

    @Test func providerInvalidStatusFallsBackToAPIKeyDiagnostic() {
        let issue = DiagnosticClassifier.from(providerStatus: .invalid(message: "Provider rejected the credential.", checkedAt: Date()))

        #expect(issue?.code == .apiKeyInvalid)
        #expect(issue?.kind == .provider)
        #expect(issue?.action == .openProviderSettings)
        #expect(issue?.underlyingMessage == "Provider rejected the credential.")
    }

    @Test func providerFailedStatusFallsBackToProviderDiagnostic() {
        let issue = DiagnosticClassifier.from(providerStatus: .failed(message: "Unexpected upstream failure.", checkedAt: Date()))

        #expect(issue?.code == .providerServerError)
        #expect(issue?.kind == .provider)
        #expect(issue?.action == .retry)
        #expect(issue?.underlyingMessage == "Unexpected upstream failure.")
    }

    @Test func classifiesQuotaAndBillingMessages() {
        let issue = DiagnosticClassifier.from(connectionEvent: .serverError("Quota exceeded. Please enable billing."))

        #expect(issue?.code == .quotaOrBilling)
        #expect(issue?.kind == .provider)
    }

    @Test func classifiesModelUnavailableMessages() {
        let issue = DiagnosticClassifier.from(connectionEvent: .serverError("Model not found: gemini-live"))

        #expect(issue?.code == .modelUnavailable)
    }

    @Test func classifiesTimeoutAsNetworkIssue() {
        let issue = DiagnosticClassifier.from(connectionEvent: .sendFailed("The request timed out."))

        #expect(issue?.code == .networkTimeout)
        #expect(issue?.action == .retry)
    }

    @Test func classifiesSetupBlockingPermissionIssue() {
        let issue = DiagnosticClassifier.from(blockingIssue: .screenRecordingPermissionMissing)

        #expect(issue.code == .screenRecordingPermissionMissing)
        #expect(issue.action == .openScreenRecordingSettings)
    }

    @Test func unknownIssueKeepsUnderlyingMessage() {
        let issue = DiagnosticClassifier.from(error: NSError(domain: "LiveBuddy", code: 9, userInfo: [NSLocalizedDescriptionKey: "strange failure"]), context: .runtime)

        #expect(issue.code == .unknown)
        #expect(issue.underlyingMessage == "strange failure")
    }
}
