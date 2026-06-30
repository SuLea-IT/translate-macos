#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Services" / "GeminiLiveTranslateClient.swift"
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
app_state = app_state_path.read_text()
errors: list[str] = []

if "@MainActor\nfinal class GeminiLiveTranslateClient" not in text:
    errors.append("GeminiLiveTranslateClient must be MainActor-isolated so websocket/session/open state is single-threaded")

connect_match = re.search(r"func connect\(\) async throws \{(?P<body>[\s\S]*?)\n    \}\n\n    private func activeSession", text)
if not connect_match:
    errors.append("GeminiLiveTranslateClient.connect() not found")
else:
    body = connect_match.group("body")
    if "Task { @MainActor [weak self] in" not in body or "self?.close()" not in body:
        errors.append("connect() cancellation handler must close on MainActor instead of touching client state from a nonisolated callback")
    if "DispatchQueue.main.async" in body:
        errors.append("connect() cancellation handler should not use DispatchQueue.main.async for MainActor-isolated state")

for signature, helper in [
    ("urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didOpenWithProtocol protocol: String?)", "handleSocketOpened()"),
    ("urlSession(\n        _ session: URLSession,\n        webSocketTask: URLSessionWebSocketTask,\n        didCloseWith closeCode: URLSessionWebSocketTask.CloseCode,\n        reason: Data?\n    )", "handleSocketClosed(message: message)"),
]:
    if f"nonisolated func {signature}" not in text:
        errors.append(f"URLSessionWebSocketDelegate method must be nonisolated and bridge to MainActor: {signature}")
    method_idx = text.find(f"nonisolated func {signature}")
    if method_idx != -1:
        method_end = text.find("\n    }", method_idx)
        body = text[method_idx:method_end if method_end != -1 else len(text)]
        if "Task { @MainActor [weak self] in" not in body:
            errors.append(f"Delegate method must hop back to MainActor before touching client state: {signature}")
        if helper not in body:
            errors.append(f"Delegate method must delegate isolated state mutation through {helper}")

for helper_name, required in [
    (
        "handleSocketOpened",
        ["guard !isClosed else { return }", "isOpen = true", "report(.socketOpened)", "openContinuation?.resume()", "openContinuation = nil"],
    ),
    (
        "handleSocketClosed",
        ["guard !isClosed else { return }", "isOpen = false", "openContinuation?.resume(throwing: LiveTranslateError.socketClosed(message))", "openContinuation = nil", "report(.socketClosed(message))"],
    ),
]:
    helper_match = re.search(rf"private func {helper_name}[\s\S]*?\{{(?P<body>[\s\S]*?)\n    \}}", text)
    if not helper_match:
        errors.append(f"GeminiLiveTranslateClient.{helper_name} helper not found")
    else:
        body = helper_match.group("body")
        for token in required:
            if token not in body:
                errors.append(f"{helper_name} must mutate isolated websocket state through {token}")

receive_match = re.search(r"private func receiveLoop\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func decodedObject", text)
if not receive_match:
    errors.append("GeminiLiveTranslateClient.receiveLoop() not found")
else:
    body = receive_match.group("body")
    for token in [
        "webSocket.receive { [weak self, weak webSocket] result in",
        "Task { @MainActor [weak self, weak webSocket] in",
        "guard let self, let webSocket, !self.isClosed, self.webSocket === webSocket else { return }",
        "guard !self.isClosed, self.webSocket === webSocket else { return }",
        "self.receiveLoop()",
    ]:
        if token not in body:
            errors.append(f"receiveLoop must process async callbacks on MainActor through {token}")



if "deinit {\n        MainActor.assumeIsolated {\n            close()\n        }\n    }" not in text:
    errors.append("GeminiLiveTranslateClient.deinit must close inside MainActor.assumeIsolated")

deinit_idx = app_state.find("deinit {")
if deinit_idx == -1:
    errors.append("AppState.deinit not found")
else:
    deinit_end = app_state.find("\n}\n\nenum LiveStatusLevel", deinit_idx)
    body = app_state[deinit_idx:deinit_end if deinit_end != -1 else len(app_state)]
    expected_close_block = "MainActor.assumeIsolated {\n            client?.close()\n        }"
    if expected_close_block not in body:
        errors.append("AppState.deinit must keep client?.close() within an explicit MainActor.assumeIsolated block")

if errors:
    print("Live client MainActor isolation verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Live client MainActor isolation verification passed")
