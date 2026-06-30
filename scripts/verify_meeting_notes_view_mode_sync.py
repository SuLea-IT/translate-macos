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
        ".onChange(of: viewMode)",
        "refreshMeetingNotesForCurrentMode()",
    ]:
        if token not in body:
            errors.append(f"TranscriptsView.body must keep generated meeting notes in sync with the transcript view mode through {token}")

refresh_match = re.search(
    r"private func refreshMeetingNotesForCurrentMode\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func refreshMeetingNotesIfVisible",
    text,
)
if not refresh_match:
    errors.append("TranscriptsView.refreshMeetingNotesForCurrentMode() not found before shared refresh helper")
else:
    body = refresh_match.group("body")
    for token in [
        "guard generatedMeetingNotes != nil else { return }",
        "guard let selectedSession else {",
        "generatedMeetingNotes = nil",
        "meetingNotesSessionID = nil",
        "return",
        "refreshMeetingNotesIfVisible(for: selectedSession)",
    ]:
        if token not in body:
            errors.append(f"refreshMeetingNotesForCurrentMode() must refresh or clear stale notes through {token}")

helper_match = re.search(
    r"private func refreshMeetingNotesIfVisible\(for session: TranscriptSession\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func clearTranscriptDetailFeedbackForSelectionChange",
    text,
)
if not helper_match:
    errors.append("TranscriptsView.refreshMeetingNotesIfVisible(for:) not found")
else:
    body = helper_match.group("body")
    for token in [
        "guard generatedMeetingNotes != nil, meetingNotesSessionID == session.id else { return }",
        "generatedMeetingNotes = meetingNotesGenerator.generate(from: session, mode: viewMode)",
        "meetingNotesSessionID = session.id",
    ]:
        if token not in body:
            errors.append(f"refreshMeetingNotesIfVisible(for:) must regenerate visible notes through {token}")

if "generatedMeetingNotes = meetingNotesGenerator.generate(from: session, mode: viewMode)" not in text:
    errors.append("toggleMeetingNotes(for:) must still generate meeting notes from the active viewMode")

if errors:
    print("Meeting notes view-mode sync verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Meeting notes view-mode sync verification passed")
