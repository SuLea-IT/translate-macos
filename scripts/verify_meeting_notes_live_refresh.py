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
        ".onChange(of: appState.transcriptSessions)",
        "reconcileSelectedSession()",
    ]:
        if token not in body:
            errors.append(f"TranscriptsView.body must reconcile selected transcript as transcriptSessions changes through {token}")

reconcile_match = re.search(
    r"private func reconcileSelectedSession\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func refreshMeetingNotesForCurrentMode",
    text,
)
if not reconcile_match:
    errors.append("TranscriptsView.reconcileSelectedSession() not found before meeting-note refresh helpers")
else:
    body = reconcile_match.group("body")
    for token in [
        "self.selectedSession = refreshedSession",
        "refreshMeetingNotesIfVisible(for: refreshedSession)",
        "return",
    ]:
        if token not in body:
            errors.append(f"reconcileSelectedSession() must update visible meeting notes for the refreshed live transcript through {token}")
    assignment_index = body.find("self.selectedSession = refreshedSession")
    refresh_index = body.find("refreshMeetingNotesIfVisible(for: refreshedSession)")
    return_index = body.find("return", refresh_index if refresh_index != -1 else 0)
    if assignment_index == -1 or refresh_index == -1 or return_index == -1 or not (assignment_index < refresh_index < return_index):
        errors.append("reconcileSelectedSession() must refresh visible notes after assigning refreshedSession and before returning")

helper_match = re.search(
    r"private func refreshMeetingNotesIfVisible\(for session: TranscriptSession\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func clearTranscriptDetailFeedbackForSelectionChange",
    text,
)
if not helper_match:
    errors.append("TranscriptsView.refreshMeetingNotesIfVisible(for:) helper not found")
else:
    body = helper_match.group("body")
    for token in [
        "guard generatedMeetingNotes != nil, meetingNotesSessionID == session.id else { return }",
        "generatedMeetingNotes = meetingNotesGenerator.generate(from: session, mode: viewMode)",
        "meetingNotesSessionID = session.id",
    ]:
        if token not in body:
            errors.append(f"refreshMeetingNotesIfVisible(for:) must refresh only the currently visible notes through {token}")

mode_refresh_match = re.search(
    r"private func refreshMeetingNotesForCurrentMode\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func refreshMeetingNotesIfVisible",
    text,
)
if not mode_refresh_match:
    errors.append("TranscriptsView.refreshMeetingNotesForCurrentMode() not found before shared helper")
else:
    body = mode_refresh_match.group("body")
    for token in [
        "guard generatedMeetingNotes != nil else { return }",
        "guard let selectedSession else {",
        "generatedMeetingNotes = nil",
        "meetingNotesSessionID = nil",
        "refreshMeetingNotesIfVisible(for: selectedSession)",
    ]:
        if token not in body:
            errors.append(f"refreshMeetingNotesForCurrentMode() must reuse the live-refresh helper through {token}")

if errors:
    print("Meeting notes live refresh verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Meeting notes live refresh verification passed")
