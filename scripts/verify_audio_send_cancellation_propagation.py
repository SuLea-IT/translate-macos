#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

body_match = re.search(r"private func enqueueAudioSend\(_ data: Data\) -> Bool \{(?P<body>[\s\S]*?)\n    \}\n\n    private func resetAudioSendPipeline", text)
if not body_match:
    errors.append("AppState.enqueueAudioSend(_:) not found")
else:
    body = body_match.group("body")
    for token in [
        "let previousTask = audioSendTask",
        "if let previousTask {",
        "await withTaskCancellationHandler",
        "await previousTask.value",
        "onCancel: {",
        "previousTask.cancel()",
        "guard !Task.isCancelled else { return }",
        "await client.sendAudio(data)",
    ]:
        if token not in body:
            errors.append(f"Audio send queue must propagate cancellation through {token}")
    handler_idx = body.find("await withTaskCancellationHandler")
    send_idx = body.find("await client.sendAudio(data)")
    if min(handler_idx, send_idx) != -1 and handler_idx > send_idx:
        errors.append("Audio send task must wait for previous sends with a cancellation handler before sending new audio")

reset_match = re.search(r"private func resetAudioSendPipeline\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func updateUsageControlSettingsIfNeeded", text)
if not reset_match:
    errors.append("AppState.resetAudioSendPipeline() not found")
else:
    body = reset_match.group("body")
    for token in ["audioSendGeneration = UUID()", "audioSendTask?.cancel()", "audioSendTask = nil", "pendingAudioSendChunks = 0"]:
        if token not in body:
            errors.append(f"resetAudioSendPipeline must cancel the latest task and clear counters through {token}")

if errors:
    print("Audio send cancellation propagation verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Audio send cancellation propagation verification passed")
