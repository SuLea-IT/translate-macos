import Foundation

struct ProviderHealthService {
    typealias Ping = (String) async -> Result<Void, Error>

    var ping: Ping

    init(ping: @escaping Ping) {
        self.ping = ping
    }

    func verify(apiKey: String, now: Date = Date()) async -> ProviderHealthStatus {
        let trimmed = apiKey.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return .missing
        }
        guard !Task.isCancelled else {
            return .unchecked
        }

        let result = await ping(trimmed)
        guard !Task.isCancelled else {
            return .unchecked
        }
        switch result {
        case .success:
            return .valid(checkedAt: now)
        case .failure(let error):
            if Self.isCancellationError(error) {
                return .unchecked
            }
            let message = error.localizedDescription
            if message.localizedCaseInsensitiveContains("API key")
                || message.localizedCaseInsensitiveContains("API_KEY_INVALID") {
                return .invalid(message: message, checkedAt: now)
            }
            return .failed(message: message, checkedAt: now)
        }
    }
}

extension ProviderHealthService {
    private static let requestTimeout: TimeInterval = 8

    static let geminiDefault = ProviderHealthService { apiKey in
        let modelsToTry = ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-1.5-flash"]
        var lastError: Error?

        for model in modelsToTry {
            if Task.isCancelled {
                return .failure(CancellationError())
            }
            do {
                try Task.checkCancellation()
                try await pingGeminiModel(model, withKey: apiKey)
                try Task.checkCancellation()
                return .success(())
            } catch {
                if Self.isCancellationError(error) || Task.isCancelled {
                    return .failure(CancellationError())
                }
                lastError = error
                let nsError = error as NSError
                if nsError.domain == "LiveBuddy" && (nsError.code == 400 || nsError.code == 403) {
                    let message = nsError.localizedDescription
                    if message.localizedCaseInsensitiveContains("API key")
                        || message.localizedCaseInsensitiveContains("API_KEY_INVALID") {
                        return .failure(error)
                    }
                }
            }
        }

        return .failure(lastError ?? NSError(
            domain: "LiveBuddy",
            code: 500,
            userInfo: [NSLocalizedDescriptionKey: "Verification failed"]
        ))
    }

    private static func pingGeminiModel(_ modelName: String, withKey key: String) async throws {
        try Task.checkCancellation()
        guard let escapedKey = key.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
              let url = URL(string: "https://generativelanguage.googleapis.com/v1beta/models/\(modelName):generateContent?key=\(escapedKey)") else {
            throw NSError(domain: "LiveBuddy", code: 400, userInfo: [NSLocalizedDescriptionKey: "Invalid API key format"])
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: [
            "contents": [
                [
                    "parts": [
                        ["text": "ping"]
                    ]
                ]
            ]
        ])

        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = requestTimeout
        configuration.timeoutIntervalForResource = requestTimeout
        let session = URLSession(configuration: configuration)
        defer {
            session.invalidateAndCancel()
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch is CancellationError {
            throw CancellationError()
        } catch let error as URLError where error.code == .cancelled {
            throw CancellationError()
        } catch let error as URLError where error.code == .timedOut {
            throw NSError(
                domain: "LiveBuddy",
                code: NSURLErrorTimedOut,
                userInfo: [NSLocalizedDescriptionKey: "Timed out after \(Int(requestTimeout.rounded())) seconds."]
            )
        }
        try Task.checkCancellation()

        guard let httpResponse = response as? HTTPURLResponse else {
            throw NSError(domain: "LiveBuddy", code: 500, userInfo: [NSLocalizedDescriptionKey: "Invalid server response"])
        }

        if httpResponse.statusCode != 200 {
            if let errorObject = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let error = errorObject["error"] as? [String: Any],
               let message = error["message"] as? String {
                throw NSError(domain: "LiveBuddy", code: httpResponse.statusCode, userInfo: [NSLocalizedDescriptionKey: message])
            }
            throw NSError(domain: "LiveBuddy", code: httpResponse.statusCode, userInfo: [NSLocalizedDescriptionKey: "HTTP Error \(httpResponse.statusCode)"])
        }
    }

    private static func isCancellationError(_ error: Error) -> Bool {
        if error is CancellationError {
            return true
        }
        let nsError = error as NSError
        return nsError.domain == NSURLErrorDomain
            && (nsError.code == NSURLErrorCancelled || nsError.code == URLError.Code.cancelled.rawValue)
    }
}
