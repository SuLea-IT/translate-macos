#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Services" / "GeminiLiveTranslateClient.swift"
text = path.read_text()
errors: list[str] = []

match = re.search(r"private func receiveLoop\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func decodedObject", text)
if not match:
    errors.append("GeminiLiveTranslateClient.receiveLoop() not found")
else:
    body = match.group("body")
    for token in [
        "guard !isClosed, let webSocket else { return }",
        "webSocket.receive { [weak self, weak webSocket] result in",
        "guard let self, let webSocket, !self.isClosed, self.webSocket === webSocket else { return }",
        "guard !self.isClosed, self.webSocket === webSocket else { return }",
        "self.receiveLoop()",
    ]:
        if token not in body:
            errors.append(f"receiveLoop must bind receives to the current live socket through {token}")
    first_guard_idx = body.find("guard !isClosed, let webSocket else { return }")
    receive_idx = body.find("webSocket.receive")
    callback_guard_idx = body.find("guard let self, let webSocket, !self.isClosed, self.webSocket === webSocket else { return }")
    decode_idx = body.find("self.decodedObject")
    recurse_guard_idx = body.find("guard !self.isClosed, self.webSocket === webSocket else { return }")
    recurse_idx = body.find("self.receiveLoop()")
    if -1 in [first_guard_idx, receive_idx] or not (first_guard_idx < receive_idx):
        errors.append("receiveLoop must check closed/current websocket before registering a receive callback")
    if -1 in [callback_guard_idx, decode_idx] or not (callback_guard_idx < decode_idx):
        errors.append("receiveLoop must reject stale websocket callbacks before parsing/handling messages")
    if -1 in [recurse_guard_idx, recurse_idx] or not (decode_idx < recurse_guard_idx < recurse_idx):
        errors.append("receiveLoop must re-check closed/current websocket before scheduling the next receive")
    if "webSocket?.receive" in body:
        errors.append("receiveLoop must unwrap the current websocket once instead of optional-chaining a possibly stale socket")

if errors:
    print("Live client receive loop guard verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Live client receive loop guard verification passed")
