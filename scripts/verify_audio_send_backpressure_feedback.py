#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state = (root / "LiveBuddy" / "Models" / "AppState.swift").read_text()
interface = (root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift").read_text()
errors: list[str] = []

if "case statusAudioSendBackpressure" not in interface:
    errors.append("InterfaceText must include statusAudioSendBackpressure")
if interface.count(".statusAudioSendBackpressure:") != 8:
    errors.append("statusAudioSendBackpressure must be translated for all 8 interface languages")

enqueue_match = re.search(r"private func enqueueAudioSend\(_ data: Data\) -> Bool \{(?P<body>[\s\S]*?)\n    \}\n\n    private func resetAudioSendPipeline", app_state)
if not enqueue_match:
    errors.append("AppState.enqueueAudioSend(_:) not found")
else:
    body = enqueue_match.group("body")
    if "reportAudioSendBackpressure(now: now)" not in body:
        errors.append("enqueueAudioSend must report localized backpressure feedback when dropping chunks")
    if "Audio send queue is full; dropping live audio chunks" in body:
        errors.append("enqueueAudioSend must not use a hard-coded English backpressure message")

helper_match = re.search(r"private func reportAudioSendBackpressure\(now: Date\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func resetAudioSendPipeline", app_state)
if not helper_match:
    errors.append("AppState.reportAudioSendBackpressure(now:) not found")
else:
    body = helper_match.group("body")
    for token in [
        "now.timeIntervalSince(lastAudioSendBackpressureLogAt) >= 5",
        "lastAudioSendBackpressureLogAt = now",
        "let message = localizedStatus(.statusAudioSendBackpressure)",
        "updateStatus(message, level: .error, log: true)",
        "lastAudioStatusAt = now",
    ]:
        if token not in body:
            errors.append(f"reportAudioSendBackpressure must keep visible localized throttled feedback through {token}")

if errors:
    print("Audio send backpressure feedback verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Audio send backpressure feedback verification passed")
