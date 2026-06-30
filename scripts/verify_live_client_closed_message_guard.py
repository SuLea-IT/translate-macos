#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Services" / "GeminiLiveTranslateClient.swift"
text = path.read_text()
errors: list[str] = []

handle_match = re.search(r"private func handle\(_ root: \[String: Any\]\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func report", text)
if not handle_match:
    errors.append("GeminiLiveTranslateClient.handle(_:) not found")
else:
    body = handle_match.group("body")
    guard_token = "guard !isClosed else { return }"
    if guard_token not in body:
        errors.append("handle(_:) must ignore late server messages after close")
    first_guard_idx = body.find(guard_token)
    mutation_tokens = [
        "report(.serverError(message))",
        "onInputTranscript?",
        "onOutputTranscript?",
        "receivedAudioChunks += 1",
        "reportReceiveStatusIfNeeded()",
        "onAudioChunk?",
    ]
    if first_guard_idx == -1:
        errors.append("handle(_:) must check closed state before any callback/count mutation")
    else:
        for token in mutation_tokens:
            idx = body.find(token)
            if idx != -1 and idx < first_guard_idx:
                errors.append(f"handle(_:) must not run {token} before the closed-state guard")

status_match = re.search(r"private func reportReceiveStatusIfNeeded\(\) \{(?P<body>[\s\S]*?)\n    \}\n\}", text)
if not status_match:
    errors.append("GeminiLiveTranslateClient.reportReceiveStatusIfNeeded() not found")
else:
    body = status_match.group("body")
    if "guard !isClosed else { return }" not in body:
        errors.append("reportReceiveStatusIfNeeded() must ignore late audio status after close")
    guard_idx = body.find("guard !isClosed else { return }")
    status_idx = body.find("onStatus?")
    if status_idx != -1 and (guard_idx == -1 or guard_idx > status_idx):
        errors.append("reportReceiveStatusIfNeeded() must check closed state before onStatus callback")

if errors:
    print("Live client closed-message guard verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Live client closed-message guard verification passed")
