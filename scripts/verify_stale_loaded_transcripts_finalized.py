#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
session_path = root / "LiveBuddy" / "Models" / "TranscriptSession.swift"
tests_path = root / "LiveBuddyTests" / "TranscriptSessionTests.swift"
app_state = app_state_path.read_text()
session = session_path.read_text()
tests = tests_path.read_text() if tests_path.exists() else ""
errors: list[str] = []

helper_match = re.search(r"func finalizedIfNeeded\(\) -> TranscriptSession \{(?P<body>[\s\S]*?)\n    \}", session)
if not helper_match:
    errors.append("TranscriptSession.finalizedIfNeeded() must exist to close stale in-progress sessions loaded from disk")
else:
    body = helper_match.group("body")
    for token in [
        "guard endedAt == nil else { return self }",
        "var copy = self",
        "let lastLineTimestamp = lines.map(\\.timestamp).max()",
        "copy.endedAt = max(startedAt, lastLineTimestamp ?? startedAt)",
        "return copy",
    ]:
        if token not in body:
            errors.append(f"finalizedIfNeeded() must close only stale open sessions using a safe end time through {token}")

load_match = re.search(
    r"private func loadTranscriptSessions\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func refreshAvailableMicrophones",
    app_state,
)
if not load_match:
    errors.append("AppState.loadTranscriptSessions() not found")
else:
    body = load_match.group("body")
    for token in [
        "let finalized = decoded.map { $0.finalizedIfNeeded() }",
        "transcriptSessions = finalized",
        "if finalized != decoded {",
        "saveTranscriptSessionsImmediately()",
    ]:
        if token not in body:
            errors.append(f"loadTranscriptSessions() must finalize and persist stale in-progress sessions through {token}")
    map_idx = body.find("let finalized = decoded.map { $0.finalizedIfNeeded() }")
    assign_idx = body.find("transcriptSessions = finalized", map_idx)
    condition_idx = body.find("if finalized != decoded", assign_idx)
    save_idx = body.find("saveTranscriptSessionsImmediately()", condition_idx)
    if -1 in [map_idx, assign_idx, condition_idx, save_idx] or not (map_idx < assign_idx < condition_idx < save_idx):
        errors.append("loadTranscriptSessions() must map decoded sessions, assign finalized history, then persist only if recovery changed data")

for token in [
    "finalizedIfNeededClosesOpenSessionAtLastLineTimestamp",
    "finalizedIfNeededKeepsAlreadyClosedSessionUnchanged",
]:
    if token not in tests:
        errors.append(f"TranscriptSessionTests must cover stale transcript finalization through {token}")

if errors:
    print("Stale loaded transcript finalization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Stale loaded transcript finalization verification passed")
