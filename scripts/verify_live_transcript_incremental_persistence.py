#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = app_state_path.read_text()
errors: list[str] = []

history_match = re.search(r"private func appendCurrentTranscriptLine\(from line: CaptionLine\) \{(?P<body>[\s\S]*?)\n    \}\n\n    var subtitleLines", text)
if not history_match:
    errors.append("AppState.appendCurrentTranscriptLine(from:) not found")
else:
    body = history_match.group("body")
    required_tokens = [
        "guard line.kind == .output else { return }",
        "let transcriptLine = TranscriptLine(",
        "id: line.id",
        "text: line.text",
        "originalText: line.originalText",
        "languageCode: line.languageCode",
        "timestamp: line.timestamp",
        "currentTranscriptLines.append(transcriptLine)",
        "if let sessionID = currentSessionID",
        "transcriptSessions.firstIndex(where: { $0.id == sessionID })",
        "transcriptSessions[index].lines = currentTranscriptLines",
        "scheduleTranscriptSave()",
    ]
    for token in required_tokens:
        if token not in body:
            errors.append(f"appendCurrentTranscriptLine must incrementally sync and persist live transcript history through {token}")

    append_index = body.find("currentTranscriptLines.append(transcriptLine)")
    sync_index = body.find("transcriptSessions[index].lines = currentTranscriptLines")
    save_index = body.find("scheduleTranscriptSave()")
    if min(append_index, sync_index, save_index) != -1 and not (append_index < sync_index < save_index):
        errors.append("appendCurrentTranscriptLine must append, sync the active session, then schedule persistence in that order")
    if "saveTranscriptSessions()" in body:
        errors.append("appendCurrentTranscriptLine must coalesce disk writes instead of synchronously saving every sentence")

begin_match = re.search(r"private func beginTranscriptSession\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func finishTranscriptSession", text)
if not begin_match:
    errors.append("AppState.beginTranscriptSession() not found")
else:
    body = begin_match.group("body")
    if "saveTranscriptSessionsImmediately()" not in body:
        errors.append("beginTranscriptSession must persist the empty live session immediately so it survives app termination")

if errors:
    print("Live transcript incremental persistence verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Live transcript incremental persistence verification passed")
