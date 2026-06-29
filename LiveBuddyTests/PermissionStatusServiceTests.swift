import Testing
@testable import LiveBuddy

struct PermissionStatusServiceTests {
    @Test func serviceReturnsInjectedMicrophoneAndScreenStatuses() async {
        let service = PermissionStatusService(
            microphoneStatus: { .granted },
            screenRecordingStatus: { .denied },
            requestMicrophoneAccess: { true },
            requestScreenRecordingAccess: { false }
        )

        let statuses = await service.refreshStatuses()

        #expect(statuses.microphone.state == .granted)
        #expect(statuses.screenRecording.state == .denied)
    }

    @Test func requestingMicrophoneConvertsGrantedBooleanToStatus() async {
        let service = PermissionStatusService(
            microphoneStatus: { .notDetermined },
            screenRecordingStatus: { .unknown },
            requestMicrophoneAccess: { true },
            requestScreenRecordingAccess: { false }
        )

        let status = await service.requestMicrophonePermission()

        #expect(status.state == .granted)
    }
}
