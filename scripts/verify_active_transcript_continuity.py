#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = app_state_path.read_text()
errors: list[str] = []

for token in [
    "private func restartTranscriptSessionIfRunning()",
    "guard isRunning else { return }",
    "captions.removeAll()",
    "beginTranscriptSession()",
]:
    if token not in text:
        errors.append(f"AppState must preserve live transcript recording after deletion through {token}")

restart_match = re.search(r"private func restartTranscriptSessionIfRunning\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func clearActiveTranscriptState", text)
if not restart_match:
    errors.append("AppState.restartTranscriptSessionIfRunning() not found")
else:
    body = restart_match.group("body")
    for token in [
        "guard isRunning else { return }",
        "captionDraft = \"\"",
        "originalDraft = \"\"",
        "completedOriginalSentences.removeAll()",
        "captions.removeAll()",
        "beginTranscriptSession()",
    ]:
        if token not in body:
            errors.append(f"restartTranscriptSessionIfRunning must create a fresh live transcript session through {token}")

delete_match = re.search(r"func deleteTranscriptSession\(_ session: TranscriptSession\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func deleteAllTranscriptSessions", text)
if not delete_match:
    errors.append("AppState.deleteTranscriptSession(_:) not found")
else:
    body = delete_match.group("body")
    for token in [
        "let wasActiveSession = currentSessionID == session.id",
        "if wasActiveSession",
        "restartTranscriptSessionIfRunning()",
    ]:
        if token not in body:
            errors.append(f"deleteTranscriptSession must continue recording after deleting the active session through {token}")

delete_all_match = re.search(r"func deleteAllTranscriptSessions\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func restartTranscriptSessionIfRunning", text)
if not delete_all_match:
    errors.append("AppState.deleteAllTranscriptSessions() not found")
else:
    body = delete_all_match.group("body")
    for token in [
        "clearActiveTranscriptState()",
        "transcriptSessions.removeAll()",
        "restartTranscriptSessionIfRunning()",
        "saveTranscriptSessionsImmediately()",
    ]:
        if token not in body:
            errors.append(f"deleteAllTranscriptSessions must continue recording after clearing history through {token}")
    if body.find("restartTranscriptSessionIfRunning()") < body.find("transcriptSessions.removeAll()"):
        errors.append("deleteAllTranscriptSessions must remove old history before starting a fresh live transcript session")

if errors:
    print("Active transcript continuity verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Active transcript continuity verification passed")
