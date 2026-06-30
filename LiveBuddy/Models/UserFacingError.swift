import Foundation

enum UserFacingErrorKind: String, Codable, Equatable {
    case provider
    case permission
    case network
    case capture
    case storage
    case unknown
}

enum UserFacingErrorAction: String, Codable, Equatable {
    case openProviderSettings
    case openMicrophoneSettings
    case openScreenRecordingSettings
    case retry
}

struct UserFacingError: Codable, Equatable {
    let kind: UserFacingErrorKind
    let titleKey: InterfaceText
    let messageKey: InterfaceText
    let recoveryKey: InterfaceText?
    let action: UserFacingErrorAction?

    static let apiKeyMissing = UserFacingError(
        kind: .provider,
        titleKey: .apiKeyMissingTitle,
        messageKey: .apiKeyMissingMessage,
        recoveryKey: .apiKeyMissingRecovery,
        action: .openProviderSettings
    )

    static let apiKeyInvalid = UserFacingError(
        kind: .provider,
        titleKey: .diagnosticAPIKeyInvalidTitle,
        messageKey: .diagnosticAPIKeyInvalidMessage,
        recoveryKey: .diagnosticOpenProviderRecovery,
        action: .openProviderSettings
    )

    static let microphonePermissionMissing = UserFacingError(
        kind: .permission,
        titleKey: .microphonePermissionRequired,
        messageKey: .microphonePermissionRequiredMessage,
        recoveryKey: .openMicrophoneSettings,
        action: .openMicrophoneSettings
    )

    static let screenRecordingPermissionMissing = UserFacingError(
        kind: .permission,
        titleKey: .screenRecordingPermissionRequired,
        messageKey: .screenRecordingPermissionRequiredMessage,
        recoveryKey: .openScreenRecordingSettings,
        action: .openScreenRecordingSettings
    )

    static func from(blockingIssues: [SetupBlockingIssue]) -> UserFacingError? {
        guard let firstIssue = blockingIssues.first else { return nil }

        switch firstIssue {
        case .apiKeyMissing:
            return .apiKeyMissing
        case .apiKeyInvalid:
            return .apiKeyInvalid
        case .microphonePermissionMissing:
            return .microphonePermissionMissing
        case .screenRecordingPermissionMissing:
            return .screenRecordingPermissionMissing
        }
    }
}
