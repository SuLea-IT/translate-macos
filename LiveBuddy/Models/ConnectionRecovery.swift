import Foundation

struct ConnectionRecoveryPolicy: Equatable {
    let maxAttempts: Int
    let initialDelay: TimeInterval
    let multiplier: Double
    let maxDelay: TimeInterval

    static let `default` = ConnectionRecoveryPolicy(
        maxAttempts: 4,
        initialDelay: 0.75,
        multiplier: 2,
        maxDelay: 8
    )

    func delay(forAttempt attempt: Int) -> TimeInterval {
        guard attempt > 0 else { return 0 }
        let uncapped = initialDelay * pow(multiplier, Double(attempt - 1))
        return min(uncapped, maxDelay)
    }
}

enum LiveConnectionEvent: Equatable {
    case socketOpened
    case sessionReady
    case disconnected(String)
    case socketClosed(String)
    case sendFailed(String)
    case serverError(String)
    case parseFailed(String)

    var isRecoverable: Bool {
        switch self {
        case .socketOpened, .sessionReady:
            false
        case .disconnected, .socketClosed, .sendFailed:
            true
        case .parseFailed:
            false
        case .serverError(let message):
            Self.isRecoverableServerMessage(message)
        }
    }

    var statusMessage: String {
        switch self {
        case .socketOpened:
            "Gemini socket opened"
        case .sessionReady:
            "Gemini session ready"
        case .disconnected(let message):
            "Gemini disconnected: \(message)"
        case .socketClosed(let message):
            "Gemini socket closed: \(message)"
        case .sendFailed(let message):
            "Send failed: \(message)"
        case .serverError(let message):
            "Gemini error: \(message)"
        case .parseFailed(let message):
            "Gemini parse failed: \(message)"
        }
    }

    private static func isRecoverableServerMessage(_ message: String) -> Bool {
        let lowercased = message.lowercased()
        let terminalNeedles = [
            "api key",
            "apikey",
            "auth",
            "unauthorized",
            "forbidden",
            "permission",
            "quota",
            "billing",
            "invalid argument",
            "model not found",
            "not found"
        ]
        if terminalNeedles.contains(where: lowercased.contains) {
            return false
        }

        let transientNeedles = [
            "unavailable",
            "deadline",
            "timeout",
            "timed out",
            "internal",
            "overload",
            "overloaded",
            "temporarily",
            "500",
            "502",
            "503",
            "504"
        ]
        return transientNeedles.contains(where: lowercased.contains)
    }
}
