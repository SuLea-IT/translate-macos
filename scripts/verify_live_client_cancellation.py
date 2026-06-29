#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
client_path = root / "LiveBuddy" / "Services" / "GeminiLiveTranslateClient.swift"
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
client_text = client_path.read_text()
app_state_text = app_state_path.read_text()
errors = []

connect_match = re.search(r"func connect\(\) async throws \{(?P<body>[\s\S]*?)\n    \}\n\n    func sendAudio", client_text)
if not connect_match:
    errors.append("GeminiLiveTranslateClient.connect() not found")
else:
    body = connect_match.group("body")
    for token in [
        "try await withTaskCancellationHandler",
        "try Task.checkCancellation()",
        "onCancel: { [weak self] in",
        "self?.close()",
    ]:
        if token not in body:
            errors.append(f"GeminiLiveTranslateClient.connect() must close pending sockets when its task is cancelled through {token}")
    key_idx = body.find("let key = settings.apiKey")
    handler_idx = body.find("try await withTaskCancellationHandler")
    task_idx = body.find("let task = session.webSocketTask")
    close_idx = body.rfind("self?.close()")
    if min(key_idx, handler_idx, task_idx, close_idx) != -1 and not (handler_idx < key_idx < task_idx < close_idx):
        errors.append("GeminiLiveTranslateClient.connect() must wrap the entire connection setup in the cancellation handler")

setup_match = re.search(r"private func waitForSetupComplete\(\) async throws \{(?P<body>[\s\S]*?)\n    \}\n\n    private func receiveMessage", client_text)
if not setup_match:
    errors.append("GeminiLiveTranslateClient.waitForSetupComplete() not found")
else:
    body = setup_match.group("body")
    if "try Task.checkCancellation()" not in body:
        errors.append("GeminiLiveTranslateClient.waitForSetupComplete() must check cancellation between setup messages")
    check_idx = body.find("try Task.checkCancellation()")
    receive_idx = body.find("receiveMessage(timeout:")
    if min(check_idx, receive_idx) != -1 and not (check_idx < receive_idx):
        errors.append("GeminiLiveTranslateClient.waitForSetupComplete() must check cancellation before awaiting another receive")

for context, pattern in [
    ("reconnectGeminiClient", r"private func reconnectGeminiClient\(\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    private func scheduleStopRuntimeAfterConnectionFailure"),
    ("resumeFromUsagePause", r"private func resumeFromUsagePause\(replayChunks: \[BufferedAudioChunk\]\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    private func runningUsageStatusMessage"),
]:
    match = re.search(pattern, app_state_text)
    if not match:
        errors.append(f"AppState.{context} not found")
    else:
        body = match.group("body")
        if "try await newClient.connect()" not in body:
            errors.append(f"AppState.{context} must still await new client connection explicitly")
        if "discardAsyncClient(newClient)" not in body and "newClient.close()" not in body:
            errors.append(f"AppState.{context} must close/discard clients when cancellation or errors occur")

if errors:
    print("Live client cancellation verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Live client cancellation verification passed")
