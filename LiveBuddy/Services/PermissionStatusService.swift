import AVFoundation
import CoreGraphics
import Foundation

struct PermissionStatusSnapshot: Equatable {
    let microphone: PermissionStatus
    let screenRecording: PermissionStatus
}

struct PermissionStatusService {
    var microphoneStatus: @Sendable () -> PermissionGrantState = {
        switch AVCaptureDevice.authorizationStatus(for: .audio) {
        case .authorized:
            return .granted
        case .denied:
            return .denied
        case .restricted:
            return .restricted
        case .notDetermined:
            return .notDetermined
        @unknown default:
            return .unknown
        }
    }

    var screenRecordingStatus: @Sendable () -> PermissionGrantState = {
        CGPreflightScreenCaptureAccess() ? .granted : .denied
    }

    var requestMicrophoneAccess: @Sendable () async -> Bool = {
        await AVCaptureDevice.requestAccess(for: .audio)
    }

    var requestScreenRecordingAccess: @Sendable () -> Bool = {
        CGRequestScreenCaptureAccess()
    }

    func refreshStatuses(now: Date = Date()) async -> PermissionStatusSnapshot {
        PermissionStatusSnapshot(
            microphone: PermissionStatus(requirement: .microphone, state: microphoneStatus(), checkedAt: now),
            screenRecording: PermissionStatus(requirement: .screenRecording, state: screenRecordingStatus(), checkedAt: now)
        )
    }

    func requestMicrophonePermission(now: Date = Date()) async -> PermissionStatus {
        let granted = await requestMicrophoneAccess()
        return PermissionStatus(requirement: .microphone, state: granted ? .granted : .denied, checkedAt: now)
    }

    func requestScreenRecordingPermission(now: Date = Date()) -> PermissionStatus {
        let granted = requestScreenRecordingAccess()
        return PermissionStatus(requirement: .screenRecording, state: granted ? .granted : .denied, checkedAt: now)
    }
}
