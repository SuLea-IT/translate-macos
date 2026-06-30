#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
client_path = root / "LiveBuddy" / "Services" / "GeminiLiveTranslateClient.swift"
client = client_path.read_text()
errors: list[str] = []

if "private var session: URLSession?" not in client:
    errors.append("GeminiLiveTranslateClient must store URLSession as optional so close() can drop the client->session edge")
if "private var isClosed = false" not in client:
    errors.append("GeminiLiveTranslateClient must track closed state to ignore late websocket callbacks")
if "private func activeSession() -> URLSession" not in client:
    errors.append("GeminiLiveTranslateClient must lazily create sessions through activeSession() without forcing one during close/deinit")
if "let task = activeSession().webSocketTask(with: url)" not in client:
    errors.append("connect() must use activeSession() so a reused/new client creates a live session")

close_match = re.search(r"func close\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func sendSetup", client)
if not close_match:
    errors.append("GeminiLiveTranslateClient.close() not found")
else:
    body = close_match.group("body")
    for token in [
        "isClosed = true",
        "let closingSession = session",
        "session = nil",
        "closingSession?.invalidateAndCancel()",
        "clearCallbacks()",
    ]:
        if token not in body:
            errors.append(f"close() must fully break websocket/session/callback ownership through {token}")
    if "session.invalidateAndCancel()" in body:
        errors.append("close() must not access a lazy non-optional session directly, because that can create a session during cleanup")

if "private func clearCallbacks()" not in client:
    errors.append("GeminiLiveTranslateClient must centralize callback clearing")
else:
    clear_match = re.search(r"private func clearCallbacks\(\) \{(?P<body>[\s\S]*?)\n    \}", client)
    if not clear_match:
        errors.append("clearCallbacks() body not found")
    else:
        body = clear_match.group("body")
        for token in [
            "onInputTranscript = nil",
            "onOutputTranscript = nil",
            "onAudioChunk = nil",
            "onStatus = nil",
            "onConnectionEvent = nil",
        ]:
            if token not in body:
                errors.append(f"clearCallbacks() must release closure captures through {token}")

if "deinit {\n        MainActor.assumeIsolated {\n            close()\n        }\n    }" not in client:
    errors.append("GeminiLiveTranslateClient.deinit must call close() inside MainActor.assumeIsolated for defensive cleanup")

for helper_name in ["handleSocketOpened", "handleSocketClosed"]:
    helper_match = re.search(rf"private func {helper_name}[\s\S]*?\{{(?P<body>[\s\S]*?)\n    \}}", client)
    if not helper_match:
        errors.append(f"{helper_name} callback helper not found")
    elif "guard !isClosed else { return }" not in helper_match.group("body"):
        errors.append(f"{helper_name} must ignore late websocket callbacks after close")

report_index = client.find("private func report(")
if report_index == -1:
    errors.append("report callback method not found")
else:
    body_end = client.find("\n    }\n", report_index)
    body = client[report_index:body_end if body_end != -1 else len(client)]
    if "guard !isClosed else { return }" not in body:
        errors.append("report must ignore late websocket callbacks/reports after close")

if errors:
    print("Live client session lifecycle verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Live client session lifecycle verification passed")
