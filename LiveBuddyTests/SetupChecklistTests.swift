import Foundation
import Testing
@testable import LiveBuddy

struct SetupChecklistTests {
    @Test func screenAudioRequiresOnlyScreenRecordingPermission() {
        let state = SetupChecklistState.derive(
            audioSource: .screen,
            apiKey: .valid(checkedAt: Date()),
            microphone: PermissionStatus(requirement: .microphone, state: .denied, checkedAt: Date()),
            screenRecording: PermissionStatus(requirement: .screenRecording, state: .granted, checkedAt: Date())
        )

        #expect(state.microphone.requirementState == .notNeeded)
        #expect(state.screenRecording.requirementState == .satisfied)
        #expect(state.blockingIssues.isEmpty)
    }

    @Test func microphoneSourceBlocksWhenMicrophonePermissionMissing() {
        let state = SetupChecklistState.derive(
            audioSource: .microphone,
            apiKey: .valid(checkedAt: Date()),
            microphone: PermissionStatus(requirement: .microphone, state: .denied, checkedAt: Date()),
            screenRecording: PermissionStatus(requirement: .screenRecording, state: .granted, checkedAt: Date())
        )

        #expect(state.microphone.requirementState == .blocked)
        #expect(state.blockingIssues == [.microphonePermissionMissing])
    }

    @Test func bothSourceRequiresBothPermissions() {
        let state = SetupChecklistState.derive(
            audioSource: .both,
            apiKey: .valid(checkedAt: Date()),
            microphone: PermissionStatus(requirement: .microphone, state: .granted, checkedAt: Date()),
            screenRecording: PermissionStatus(requirement: .screenRecording, state: .denied, checkedAt: Date())
        )

        #expect(state.microphone.requirementState == .satisfied)
        #expect(state.screenRecording.requirementState == .blocked)
        #expect(state.blockingIssues == [.screenRecordingPermissionMissing])
    }

    @Test func emptyApiKeyBlocksStartBeforePermissionsMatter() {
        let state = SetupChecklistState.derive(
            audioSource: .screen,
            apiKey: .missing,
            microphone: PermissionStatus(requirement: .microphone, state: .granted, checkedAt: Date()),
            screenRecording: PermissionStatus(requirement: .screenRecording, state: .granted, checkedAt: Date())
        )

        #expect(state.blockingIssues.contains(.apiKeyMissing))
    }

    @Test func invalidApiKeyBlocksStartAfterManualVerification() {
        let state = SetupChecklistState.derive(
            audioSource: .screen,
            apiKey: .invalid(message: "API key not valid", checkedAt: Date()),
            microphone: PermissionStatus(requirement: .microphone, state: .granted, checkedAt: Date()),
            screenRecording: PermissionStatus(requirement: .screenRecording, state: .granted, checkedAt: Date())
        )

        #expect(state.blockingIssues.contains(.apiKeyInvalid))
    }

    @Test func transientProviderFailureDoesNotBlockStart() {
        let state = SetupChecklistState.derive(
            audioSource: .screen,
            apiKey: .failed(message: "Timed out", checkedAt: Date()),
            microphone: PermissionStatus(requirement: .microphone, state: .granted, checkedAt: Date()),
            screenRecording: PermissionStatus(requirement: .screenRecording, state: .granted, checkedAt: Date())
        )

        #expect(state.blockingIssues.contains(.apiKeyInvalid) == false)
        #expect(state.blockingIssues.contains(.apiKeyMissing) == false)
    }

    @Test func preflightBlocksWhenScreenRecordingIsMissing() {
        let checklist = SetupChecklistState.derive(
            audioSource: .screen,
            apiKey: .valid(checkedAt: Date()),
            microphone: PermissionStatus(requirement: .microphone, state: .granted, checkedAt: Date()),
            screenRecording: PermissionStatus(requirement: .screenRecording, state: .denied, checkedAt: Date())
        )

        let result = SetupPreflightResult.from(checklist)

        #expect(result == .blocked(.screenRecordingPermissionMissing))
    }

    @Test func preflightBlocksWhenApiKeyIsKnownInvalid() {
        let checklist = SetupChecklistState.derive(
            audioSource: .screen,
            apiKey: .invalid(message: "API key not valid", checkedAt: Date()),
            microphone: PermissionStatus(requirement: .microphone, state: .granted, checkedAt: Date()),
            screenRecording: PermissionStatus(requirement: .screenRecording, state: .granted, checkedAt: Date())
        )

        let result = SetupPreflightResult.from(checklist)

        #expect(result == .blocked(.apiKeyInvalid))
    }

    @Test func preflightAllowsWhenChecklistHasNoBlockingIssues() {
        let checklist = SetupChecklistState.derive(
            audioSource: .screen,
            apiKey: .valid(checkedAt: Date()),
            microphone: PermissionStatus(requirement: .microphone, state: .denied, checkedAt: Date()),
            screenRecording: PermissionStatus(requirement: .screenRecording, state: .granted, checkedAt: Date())
        )

        let result = SetupPreflightResult.from(checklist)

        #expect(result == .allowed)
    }
}
