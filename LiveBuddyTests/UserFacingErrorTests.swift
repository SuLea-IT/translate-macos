import Testing
@testable import LiveBuddy

struct UserFacingErrorTests {
    @Test func microphoneDeniedMapsToPermissionRecovery() {
        let error = UserFacingError.microphonePermissionMissing

        #expect(error.kind == .permission)
        #expect(error.action == .openMicrophoneSettings)
        #expect(error.titleKey == .microphonePermissionRequired)
    }

    @Test func missingApiKeyMapsToProviderRecovery() {
        let error = UserFacingError.apiKeyMissing

        #expect(error.kind == .provider)
        #expect(error.action == .openProviderSettings)
        #expect(error.titleKey == .apiKeyMissingTitle)
    }

    @Test func setupBlockingIssueMapsToFirstActionableError() {
        let error = UserFacingError.from(blockingIssues: [.screenRecordingPermissionMissing])

        #expect(error == .screenRecordingPermissionMissing)
    }
}
