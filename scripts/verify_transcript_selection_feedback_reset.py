#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
view_path = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
text = view_path.read_text()
errors: list[str] = []

body_match = re.search(r"var body: some View \{(?P<body>[\s\S]*?)\n    \}\n\n    // MARK: - List View", text)
if not body_match:
    errors.append("TranscriptsView.body not found")
else:
    body = body_match.group("body")
    for token in [
        ".onChange(of: selectedSession?.id)",
        "clearTranscriptDetailFeedbackForSelectionChange()",
    ]:
        if token not in body:
            errors.append(f"TranscriptsView.body must reset detail-only feedback when the selected transcript changes through {token}")

helper_match = re.search(
    r"private func clearTranscriptDetailFeedbackForSelectionChange\(\) \{(?P<body>[\s\S]*?)\n    \}",
    text,
)
if not helper_match:
    errors.append("TranscriptsView.clearTranscriptDetailFeedbackForSelectionChange() not found")
else:
    body = helper_match.group("body")
    for token in [
        "generatedMeetingNotes = nil",
        "meetingNotesSessionID = nil",
        "exportErrorMessage = nil",
    ]:
        if token not in body:
            errors.append(f"Selection changes must clear stale transcript-detail feedback through {token}")

for token in [
    "private func reconcileSelectedSession()",
    "self.selectedSession = refreshedSession",
    "generatedMeetingNotes = nil",
    "meetingNotesSessionID = nil",
    "exportErrorMessage = nil",
]:
    if token not in text:
        errors.append(f"Existing transcript selection reconciliation must remain intact through {token}")

if errors:
    print("Transcript selection feedback reset verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Transcript selection feedback reset verification passed")
