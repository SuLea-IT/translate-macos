import Foundation

@MainActor
final class GeminiLiveTranslateClient: NSObject, URLSessionWebSocketDelegate {
    var onInputTranscript: (@Sendable (String, String?) -> Void)?
    var onOutputTranscript: (@Sendable (String, String?) -> Void)?
    var onAudioChunk: (@Sendable (Data) -> Void)?
    var onStatus: (@Sendable (String) -> Void)?
    var onConnectionEvent: (@Sendable (LiveConnectionEvent) -> Void)?

    private let settings: AppSettings
    private var webSocket: URLSessionWebSocketTask?
    private var openContinuation: CheckedContinuation<Void, Error>?
    private var isOpen = false
    private var isClosed = false
    private var receivedAudioChunks = 0
    private var lastReceiveStatusAt = Date.distantPast
    private let socketOpenTimeout: TimeInterval
    private let setupMessageTimeout: TimeInterval
    private var session: URLSession?

    init(settings: AppSettings, socketOpenTimeout: TimeInterval = 8, setupMessageTimeout: TimeInterval = 8) {
        self.settings = settings
        self.socketOpenTimeout = socketOpenTimeout
        self.setupMessageTimeout = setupMessageTimeout
    }

    deinit {
        MainActor.assumeIsolated {
            close()
        }
    }

    func connect() async throws {
        try await withTaskCancellationHandler {
            try Task.checkCancellation()
            isClosed = false
            let key = settings.apiKey.trimmingCharacters(in: .whitespacesAndNewlines)
            guard let escapedKey = key.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
                  let url = URL(string: "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=\(escapedKey)") else {
                throw LiveTranslateError.invalidAPIKey
            }

            let task = activeSession().webSocketTask(with: url)
            webSocket = task
            do {
                try await waitForSocketOpen(task)
                try Task.checkCancellation()
                try await sendSetup()
                try Task.checkCancellation()
                try await waitForSetupComplete()
                receiveLoop()
        } catch {
                close()
                throw error
            }
        } onCancel: { [weak self] in
            Task { @MainActor [weak self] in
                self?.close()
            }
        }
    }

    private func activeSession() -> URLSession {
        if let session {
            return session
        }
        let session = URLSession(configuration: .default, delegate: self, delegateQueue: .main)
        self.session = session
        return session
    }

    func sendAudio(_ data: Data) async {
        guard !data.isEmpty else { return }
        let message: [String: Any] = [
            "realtimeInput": [
                "audio": [
                    "data": data.base64EncodedString(),
                    "mimeType": "audio/pcm;rate=16000"
                ]
            ]
        ]
        do {
            try await sendJSON(message)
        } catch is CancellationError {
            return
        } catch {
            let nsError = error as NSError
            if Task.isCancelled || (nsError.domain == NSURLErrorDomain && nsError.code == NSURLErrorCancelled) {
                return
            }
            report(.sendFailed(error.localizedDescription))
        }
    }

    func close() {
        isClosed = true
        openContinuation?.resume(throwing: LiveTranslateError.socketClosed("Closed"))
        openContinuation = nil
        isOpen = false
        webSocket?.cancel(with: .goingAway, reason: nil)
        webSocket = nil
        let closingSession = session
        session = nil
        closingSession?.invalidateAndCancel()
        clearCallbacks()
    }

    private func clearCallbacks() {
        onInputTranscript = nil
        onOutputTranscript = nil
        onAudioChunk = nil
        onStatus = nil
        onConnectionEvent = nil
    }

    private func sendSetup() async throws {
        let instruction = setupInstruction()
        var setup: [String: Any] = [
            "model": "models/gemini-3.5-live-translate-preview",
            "generationConfig": [
                "responseModalities": ["AUDIO"],
                "translationConfig": [
                    "targetLanguageCode": settings.targetLanguageCode,
                    "echoTargetLanguage": settings.echoTargetLanguage
                ]
            ],
            "inputAudioTranscription": [:],
            "outputAudioTranscription": [:],
            "contextWindowCompression": [
                "triggerTokens": "0",
                "slidingWindow": ["targetTokens": "0"]
            ]
        ]
        if !instruction.isEmpty {
            setup["systemInstruction"] = ["parts": [["text": instruction]]]
        }
        try await sendJSON(["setup": setup])
    }

    private func setupInstruction() -> String {
        let userInstruction = settings.userPrompt.trimmingCharacters(in: .whitespacesAndNewlines)
        let sourceHint: String?
        if let code = settings.sourceLanguageCode, !code.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            let name = TranslationLanguage.name(for: code)
            sourceHint = "The input speech is primarily in \(name) (\(code)). Translate from this source language unless the speaker clearly switches language."
        } else {
            sourceHint = nil
        }

        let glossaryInstruction = GlossaryPromptBuilder().instruction(for: settings.glossaryEntries)

        return [glossaryInstruction, sourceHint, userInstruction]
            .compactMap { $0?.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
            .joined(separator: "\n\n")
    }

    private func waitForSocketOpen(_ task: URLSessionWebSocketTask) async throws {
        if isOpen { return }
        try await withCheckedThrowingContinuation { continuation in
            openContinuation = continuation
            task.resume()
            DispatchQueue.main.asyncAfter(deadline: .now() + socketOpenTimeout) { [weak self, weak task] in
                guard let self, let task, self.webSocket === task, !self.isOpen, self.openContinuation != nil else { return }
                self.openContinuation?.resume(throwing: LiveTranslateError.setupTimedOut)
                self.openContinuation = nil
                task.cancel(with: .goingAway, reason: nil)
            }
        }
    }

    nonisolated func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didOpenWithProtocol protocol: String?) {
        Task { @MainActor [weak self] in
            self?.handleSocketOpened()
        }
    }

    private func handleSocketOpened() {
        guard !isClosed else { return }
        isOpen = true
        report(.socketOpened)
        openContinuation?.resume()
        openContinuation = nil
    }

    nonisolated func urlSession(
        _ session: URLSession,
        webSocketTask: URLSessionWebSocketTask,
        didCloseWith closeCode: URLSessionWebSocketTask.CloseCode,
        reason: Data?
    ) {
        let reasonText = reason.flatMap { String(data: $0, encoding: .utf8) }
        let message = [String(describing: closeCode), reasonText]
            .compactMap { $0 }
            .joined(separator: ": ")
        Task { @MainActor [weak self] in
            self?.handleSocketClosed(message: message)
        }
    }

    private func handleSocketClosed(message: String) {
        guard !isClosed else { return }
        isOpen = false
        openContinuation?.resume(throwing: LiveTranslateError.socketClosed(message))
        openContinuation = nil
        report(.socketClosed(message))
    }

    private func sendJSON(_ object: [String: Any]) async throws {
        guard let webSocket, isOpen else { throw LiveTranslateError.notConnected }
        let data = try JSONSerialization.data(withJSONObject: object)
        let text = String(decoding: data, as: UTF8.self)
        try await webSocket.send(.string(text))
    }

    private func waitForSetupComplete() async throws {
        let deadline = Date().addingTimeInterval(setupMessageTimeout)
        while Date() < deadline {
            try Task.checkCancellation()
            let remaining = max(0.01, deadline.timeIntervalSinceNow)
            let message = try await receiveMessage(timeout: remaining)
            let root = try decodedObject(from: message)
            if let error = root["error"] as? [String: Any],
               let message = error["message"] as? String {
                report(.serverError(message))
                throw LiveTranslateError.server(message)
            }
            if root["setupComplete"] != nil {
                report(.sessionReady)
                return
            }
            handle(root)
        }
        throw LiveTranslateError.setupTimedOut
    }

    private func receiveMessage() async throws -> URLSessionWebSocketTask.Message {
        guard let webSocket else { throw LiveTranslateError.notConnected }
        return try await withCheckedThrowingContinuation { continuation in
            webSocket.receive { result in
                continuation.resume(with: result)
            }
        }
    }

    private func receiveMessage(timeout: TimeInterval) async throws -> URLSessionWebSocketTask.Message {
        guard let webSocket else { throw LiveTranslateError.notConnected }
        return try await withLiveTimeout(seconds: timeout, onTimeout: { [weak webSocket] in
            webSocket?.cancel(with: .goingAway, reason: nil)
        }) { complete in
            webSocket.receive { result in
                complete(result)
            }
        }
    }

    private func withLiveTimeout<Value>(
        seconds: TimeInterval,
        onTimeout: @escaping @Sendable () -> Void = {},
        start: (@escaping @Sendable (Result<Value, Error>) -> Void) -> Void
    ) async throws -> Value {
        try await withCheckedThrowingContinuation { continuation in
            let completion = LiveTimeoutCompletion(continuation)
            start { result in
                completion.resume(with: result)
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + max(seconds, 0)) {
                if completion.resume(throwing: LiveTranslateError.setupTimedOut) {
                    onTimeout()
                }
            }
        }
    }

    private func receiveLoop() {
        guard !isClosed, let webSocket else { return }
        webSocket.receive { [weak self, weak webSocket] result in
            Task { @MainActor [weak self, weak webSocket] in
                guard let self, let webSocket, !self.isClosed, self.webSocket === webSocket else { return }
                switch result {
                case .success(let message):
                    do {
                        let root = try self.decodedObject(from: message)
                        self.handle(root)
                    } catch {
                        self.report(.parseFailed(error.localizedDescription))
                    }
                    guard !self.isClosed, self.webSocket === webSocket else { return }
                    self.receiveLoop()
                case .failure(let error):
                    self.report(.disconnected(error.localizedDescription))
                }
            }
        }
    }

    private func decodedObject(from message: URLSessionWebSocketTask.Message) throws -> [String: Any] {
        let data: Data
        switch message {
        case .string(let text):
            data = Data(text.utf8)
        case .data(let payload):
            data = payload
        @unknown default:
            throw LiveTranslateError.unsupportedMessage
        }

        guard let root = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw LiveTranslateError.invalidMessage
        }
        return root
    }

    private func handle(_ root: [String: Any]) {
        guard !isClosed else { return }
        if let error = root["error"] as? [String: Any],
           let message = error["message"] as? String {
            report(.serverError(message))
            return
        }
        guard let content = root["serverContent"] as? [String: Any] else { return }

        if let input = content["inputTranscription"] as? [String: Any],
           let text = input["text"] as? String {
            onInputTranscript?(text, input["languageCode"] as? String)
        }

        if let output = content["outputTranscription"] as? [String: Any],
           let text = output["text"] as? String {
            onOutputTranscript?(text, output["languageCode"] as? String)
        }

        if let modelTurn = content["modelTurn"] as? [String: Any],
           let parts = modelTurn["parts"] as? [[String: Any]] {
            for part in parts {
                if let inline = part["inlineData"] as? [String: Any],
                   let encoded = inline["data"] as? String,
                   let audio = Data(base64Encoded: encoded) {
                    receivedAudioChunks += 1
                    reportReceiveStatusIfNeeded()
                    onAudioChunk?(audio)
                }
                if let text = part["text"] as? String {
                    onOutputTranscript?(text, nil)
                }
            }
        }
    }

    private func report(_ event: LiveConnectionEvent) {
        guard !isClosed else { return }
        switch event {
        case .socketOpened, .sessionReady:
            onStatus?(event.statusMessage)
        case .disconnected, .socketClosed, .sendFailed, .serverError, .parseFailed:
            break
        }
        onConnectionEvent?(event)
    }

    private func reportReceiveStatusIfNeeded() {
        guard !isClosed else { return }
        let now = Date()
        guard now.timeIntervalSince(lastReceiveStatusAt) >= 1 else { return }
        lastReceiveStatusAt = now
        onStatus?("Receiving translated audio: \(receivedAudioChunks) chunks")
    }
}

private final class LiveTimeoutCompletion<Value>: @unchecked Sendable {
    private let lock = NSLock()
    private var continuation: CheckedContinuation<Value, Error>?

    init(_ continuation: CheckedContinuation<Value, Error>) {
        self.continuation = continuation
    }

    @discardableResult
    func resume(with result: Result<Value, Error>) -> Bool {
        lock.lock()
        guard let continuation else {
            lock.unlock()
            return false
        }
        self.continuation = nil
        lock.unlock()
        continuation.resume(with: result)
        return true
    }

    @discardableResult
    func resume(throwing error: Error) -> Bool {
        resume(with: .failure(error))
    }
}

enum LiveTranslateError: LocalizedError {
    case invalidAPIKey
    case notConnected
    case setupTimedOut
    case server(String)
    case invalidMessage
    case unsupportedMessage
    case socketClosed(String)

    var errorDescription: String? {
        switch self {
        case .invalidAPIKey: "Invalid Gemini API key"
        case .notConnected: "Gemini Live session is not connected"
        case .setupTimedOut: "Gemini Live setup timed out"
        case .server(let message): "Gemini error: \(message)"
        case .invalidMessage: "Gemini returned an invalid message"
        case .unsupportedMessage: "Gemini returned an unsupported WebSocket message"
        case .socketClosed(let message): "Gemini socket closed: \(message)"
        }
    }
}
