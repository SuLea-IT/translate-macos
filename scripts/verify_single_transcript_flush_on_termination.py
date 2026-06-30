#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = app_state_path.read_text()
errors: list[str] = []

match = re.search(
    r"func flushPendingStateBeforeTermination\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func binding",
    text,
)
if not match:
    errors.append("AppState.flushPendingStateBeforeTermination() not found")
else:
    body = match.group("body")
    transcript_flush_count = body.count("saveTranscriptSessionsImmediately()")
    if transcript_flush_count != 1:
        errors.append(
            "Termination flush should save transcript sessions exactly once; "
            f"found {transcript_flush_count} calls"
        )
    for token in [
        "finishTranscriptSession(saveImmediately: false)",
        "saveAPIKeyImmediately()",
        "saveSettingsImmediately()",
        "saveTranscriptSessionsImmediately()",
        "saveUsageLedger()",
    ]:
        if token not in body:
            errors.append(f"Termination flush must preserve state flush step: {token}")
    if "finishTranscriptSession()" in body:
        errors.append("Termination flush must not call the default finishTranscriptSession() because it saves immediately and causes duplicate transcript writes")

finish_match = re.search(
    r"private func finishTranscriptSession\(saveImmediately: Bool = true\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func deleteTranscriptSession",
    text,
)
if not finish_match:
    errors.append("AppState.finishTranscriptSession(saveImmediately:) not found")
else:
    body = finish_match.group("body")
    if "if saveImmediately {" not in body or "saveTranscriptSessionsImmediately()" not in body:
        errors.append("finishTranscriptSession(saveImmediately:) must keep normal stop-path persistence behind the saveImmediately guard")

if errors:
    print("Termination transcript flush verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Termination transcript flush verification passed")
