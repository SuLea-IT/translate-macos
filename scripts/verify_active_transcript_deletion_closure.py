#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = app_state_path.read_text()
errors: list[str] = []

finish_match = re.search(r"private func finishTranscriptSession\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func deleteTranscriptSession", text)
if not finish_match:
    errors.append("AppState.finishTranscriptSession() not found")
else:
    body = finish_match.group("body")
    if "guard let sessionID = currentSessionID else { return }" not in body:
        errors.append("finishTranscriptSession must separate missing currentSessionID from missing stored session")
    if "guard let index = transcriptSessions.firstIndex(where: { $0.id == sessionID }) else" not in body:
        errors.append("finishTranscriptSession must explicitly handle a missing stored current session")
    if "clearActiveTranscriptState()" not in body:
        errors.append("finishTranscriptSession must clean dangling active transcript state through clearActiveTranscriptState()")

delete_match = re.search(r"func deleteTranscriptSession\(_ session: TranscriptSession\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func deleteAllTranscriptSessions", text)
if not delete_match:
    errors.append("AppState.deleteTranscriptSession(_:) not found")
else:
    body = delete_match.group("body")
    for token in [
        "let wasActiveSession = currentSessionID == session.id",
        "if wasActiveSession",
        "clearActiveTranscriptState()",
    ]:
        if token not in body:
            errors.append(f"deleteTranscriptSession must clear active transcript state when deleting the live session through {token}")

delete_all_match = re.search(r"func deleteAllTranscriptSessions\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func saveTranscriptSessions", text)
if not delete_all_match:
    errors.append("AppState.deleteAllTranscriptSessions() not found")
else:
    body = delete_all_match.group("body")
    if "clearActiveTranscriptState()" not in body:
        errors.append("deleteAllTranscriptSessions must clear active transcript state through clearActiveTranscriptState()")

clear_match = re.search(r"private func clearActiveTranscriptState\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func saveTranscriptSessions", text)
if not clear_match:
    errors.append("AppState.clearActiveTranscriptState() not found")
else:
    body = clear_match.group("body")
    for token in [
        "currentSessionID = nil",
        "captionDraft = \"\"",
        "originalDraft = \"\"",
        "completedOriginalSentences.removeAll()",
    ]:
        if token not in body:
            errors.append(f"clearActiveTranscriptState must release active transcript state through {token}")

if errors:
    print("Active transcript deletion closure verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Active transcript deletion closure verification passed")
