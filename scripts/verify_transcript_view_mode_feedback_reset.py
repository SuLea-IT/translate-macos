#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
text = path.read_text()
errors: list[str] = []

if "private func clearTranscriptOperationFeedback()" not in text:
    errors.append("TranscriptsView must centralize stale transcript copy/export feedback cleanup when view mode changes")
else:
    helper_match = re.search(r"private func clearTranscriptOperationFeedback\(\) \{(?P<body>[\s\S]*?)\n    \}", text)
    if not helper_match:
        errors.append("clearTranscriptOperationFeedback() body not found")
    else:
        body = helper_match.group("body")
        for token in [
            "exportDocument = nil",
            "exportErrorMessage = nil",
            "copyErrorMessage = nil",
            "copySuccessMessage = nil",
        ]:
            if token not in body:
                errors.append(f"clearTranscriptOperationFeedback must reset stale detail operation state through {token}")

view_mode_match = re.search(r"\.onChange\(of: viewMode\) \{ _, _ in(?P<body>[\s\S]*?)\n        \}", text)
if not view_mode_match:
    errors.append("TranscriptsView must handle viewMode changes")
else:
    body = view_mode_match.group("body")
    for token in ["clearTranscriptOperationFeedback()", "refreshMeetingNotesForCurrentMode()"]:
        if token not in body:
            errors.append(f"viewMode changes must clear stale operation feedback while refreshing notes through {token}")
    clear_idx = body.find("clearTranscriptOperationFeedback()")
    refresh_idx = body.find("refreshMeetingNotesForCurrentMode()")
    if -1 not in (clear_idx, refresh_idx) and not (clear_idx < refresh_idx):
        errors.append("viewMode changes should clear old copy/export feedback before refreshing generated notes")

selection_match = re.search(r"private func clearTranscriptDetailFeedbackForSelectionChange\(\) \{(?P<body>[\s\S]*?)\n    \}", text)
if not selection_match:
    errors.append("clearTranscriptDetailFeedbackForSelectionChange() not found")
else:
    body = selection_match.group("body")
    for token in [
        "generatedMeetingNotes = nil",
        "meetingNotesSessionID = nil",
        "exportErrorMessage = nil",
        "copyErrorMessage = nil",
        "copySuccessMessage = nil",
    ]:
        if token not in body:
            errors.append(f"Selection changes must keep clearing full detail state through {token}")

if errors:
    print("Transcript view-mode feedback reset verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Transcript view-mode feedback reset verification passed")
