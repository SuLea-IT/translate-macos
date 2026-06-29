import Foundation

enum DiagnosticKind: String, Codable, Equatable {
    case provider
    case network
    case permission
    case capture
    case storage
    case unknown
}

enum DiagnosticSeverity: String, Codable, Equatable {
    case info
    case warning
    case error
}

enum DiagnosticRecoveryAction: String, Codable, Equatable {
    case openProviderSettings
    case openMicrophoneSettings
    case openScreenRecordingSettings
    case retry
}

enum DiagnosticCode: String, Codable, Equatable {
    case apiKeyMissing
    case apiKeyInvalid
    case quotaOrBilling
    case modelUnavailable
    case providerServerError
    case networkUnavailable
    case networkTimeout
    case connectionLost
    case microphonePermissionMissing
    case screenRecordingPermissionMissing
    case microphoneUnavailable
    case screenAudioUnavailable
    case settingsSaveFailed
    case transcriptSaveFailed
    case unknown
}

enum DiagnosticContext: String, Codable, Equatable {
    case startup
    case providerCheck
    case connection
    case capture
    case storage
    case runtime
}

struct DiagnosticIssue: Codable, Equatable, Identifiable {
    var id: DiagnosticCode { code }
    let code: DiagnosticCode
    let kind: DiagnosticKind
    let severity: DiagnosticSeverity
    let titleKey: InterfaceText
    let messageKey: InterfaceText
    let recoveryKey: InterfaceText
    let underlyingMessage: String?
    let action: DiagnosticRecoveryAction?
}

struct DiagnosticClassifier {
    static func from(blockingIssue: SetupBlockingIssue) -> DiagnosticIssue {
        switch blockingIssue {
        case .apiKeyMissing:
            return issue(.apiKeyMissing, kind: .provider, title: .diagnosticAPIKeyMissingTitle, message: .diagnosticAPIKeyMissingMessage, recovery: .diagnosticOpenProviderRecovery, action: .openProviderSettings)
        case .microphonePermissionMissing:
            return issue(.microphonePermissionMissing, kind: .permission, title: .diagnosticMicrophonePermissionTitle, message: .diagnosticMicrophonePermissionMessage, recovery: .diagnosticOpenMicrophoneRecovery, action: .openMicrophoneSettings)
        case .screenRecordingPermissionMissing:
            return issue(.screenRecordingPermissionMissing, kind: .permission, title: .diagnosticScreenRecordingPermissionTitle, message: .diagnosticScreenRecordingPermissionMessage, recovery: .diagnosticOpenScreenRecordingRecovery, action: .openScreenRecordingSettings)
        }
    }

    static func from(providerStatus: ProviderHealthStatus) -> DiagnosticIssue? {
        switch providerStatus {
        case .missing:
            return issue(.apiKeyMissing, kind: .provider, title: .diagnosticAPIKeyMissingTitle, message: .diagnosticAPIKeyMissingMessage, recovery: .diagnosticOpenProviderRecovery, action: .openProviderSettings)
        case .invalid(let message, _), .failed(let message, _):
            return classify(message: message, context: .providerCheck)
        case .unchecked, .checking, .valid:
            return nil
        }
    }

    static func from(connectionEvent: LiveConnectionEvent) -> DiagnosticIssue? {
        switch connectionEvent {
        case .socketOpened, .sessionReady:
            return nil
        case .disconnected(let message), .socketClosed(let message), .sendFailed(let message):
            return classify(message: message, context: .connection, fallbackCode: .connectionLost)
        case .serverError(let message):
            return classify(message: message, context: .connection, fallbackCode: .providerServerError)
        case .parseFailed(let message):
            return issue(.providerServerError, kind: .provider, title: .diagnosticProviderErrorTitle, message: .diagnosticProviderErrorMessage, recovery: .diagnosticRetryRecovery, underlying: message, action: .retry)
        }
    }

    static func from(error: Error, context: DiagnosticContext) -> DiagnosticIssue {
        if let microphoneError = error as? MicrophoneCaptureError {
            return issue(.microphoneUnavailable, kind: .capture, title: .diagnosticMicrophoneUnavailableTitle, message: .diagnosticMicrophoneUnavailableMessage, recovery: .diagnosticOpenMicrophoneRecovery, underlying: microphoneError.localizedDescription, action: .openMicrophoneSettings)
        }
        if let screenError = error as? ScreenAudioCaptureError {
            return issue(.screenAudioUnavailable, kind: .capture, title: .diagnosticScreenAudioUnavailableTitle, message: .diagnosticScreenAudioUnavailableMessage, recovery: .diagnosticOpenScreenRecordingRecovery, underlying: screenError.localizedDescription, action: .openScreenRecordingSettings)
        }
        return classify(message: error.localizedDescription, context: context) ?? unknown(error.localizedDescription)
    }

    static func storage(_ code: DiagnosticCode, underlyingMessage: String) -> DiagnosticIssue {
        let title: InterfaceText = code == .settingsSaveFailed ? .diagnosticSettingsSaveFailedTitle : .diagnosticTranscriptSaveFailedTitle
        let message: InterfaceText = code == .settingsSaveFailed ? .diagnosticSettingsSaveFailedMessage : .diagnosticTranscriptSaveFailedMessage
        return issue(code, kind: .storage, title: title, message: message, recovery: .diagnosticCheckDiskRecovery, underlying: underlyingMessage, action: nil)
    }

    private static func classify(message: String, context: DiagnosticContext, fallbackCode: DiagnosticCode? = nil) -> DiagnosticIssue? {
        let normalized = message.lowercased()
        if contains(normalized, ["api key", "api_key_invalid", "apikey", "unauthorized", "forbidden"]) {
            return issue(.apiKeyInvalid, kind: .provider, title: .diagnosticAPIKeyInvalidTitle, message: .diagnosticAPIKeyInvalidMessage, recovery: .diagnosticOpenProviderRecovery, underlying: message, action: .openProviderSettings)
        }
        if contains(normalized, ["quota", "billing", "payment", "exceeded", "resource exhausted"]) {
            return issue(.quotaOrBilling, kind: .provider, title: .diagnosticQuotaTitle, message: .diagnosticQuotaMessage, recovery: .diagnosticQuotaRecovery, underlying: message, action: .openProviderSettings)
        }
        if contains(normalized, ["model not found", "unsupported model"]) || (normalized.contains("invalid argument") && normalized.contains("model")) {
            return issue(.modelUnavailable, kind: .provider, title: .diagnosticModelUnavailableTitle, message: .diagnosticModelUnavailableMessage, recovery: .diagnosticRetryRecovery, underlying: message, action: .retry)
        }
        if contains(normalized, ["timeout", "timed out", "deadline"]) {
            return issue(.networkTimeout, kind: .network, title: .diagnosticNetworkTimeoutTitle, message: .diagnosticNetworkTimeoutMessage, recovery: .diagnosticRetryRecovery, underlying: message, action: .retry)
        }
        if contains(normalized, ["offline", "network", "internet", "cannot connect", "dns", "tls", "secure connection"]) {
            return issue(.networkUnavailable, kind: .network, title: .diagnosticNetworkUnavailableTitle, message: .diagnosticNetworkUnavailableMessage, recovery: .diagnosticRetryRecovery, underlying: message, action: .retry)
        }
        if let fallbackCode {
            switch fallbackCode {
            case .connectionLost:
                return issue(.connectionLost, kind: .network, title: .diagnosticConnectionLostTitle, message: .diagnosticConnectionLostMessage, recovery: .diagnosticRetryRecovery, underlying: message, action: .retry)
            case .providerServerError:
                return issue(.providerServerError, kind: .provider, title: .diagnosticProviderErrorTitle, message: .diagnosticProviderErrorMessage, recovery: .diagnosticRetryRecovery, underlying: message, action: .retry)
            default:
                break
            }
        }
        return nil
    }

    private static func unknown(_ message: String) -> DiagnosticIssue {
        issue(.unknown, kind: .unknown, title: .diagnosticUnknownTitle, message: .diagnosticUnknownMessage, recovery: .diagnosticRetryRecovery, underlying: message, action: .retry)
    }

    private static func contains(_ value: String, _ needles: [String]) -> Bool {
        needles.contains { value.contains($0) }
    }

    private static func issue(_ code: DiagnosticCode, kind: DiagnosticKind, severity: DiagnosticSeverity = .error, title: InterfaceText, message: InterfaceText, recovery: InterfaceText, underlying: String? = nil, action: DiagnosticRecoveryAction?) -> DiagnosticIssue {
        DiagnosticIssue(code: code, kind: kind, severity: severity, titleKey: title, messageKey: message, recoveryKey: recovery, underlyingMessage: underlying, action: action)
    }
}
