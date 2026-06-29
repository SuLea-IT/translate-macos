#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
view_path = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
text = view_path.read_text()
errors: list[str] = []

if "@Binding var selectedSession: TranscriptSession?" not in text:
    errors.append("TranscriptsView must expose selectedSession binding")

body_match = re.search(r"var body: some View \{(?P<body>[\s\S]*?)\n    \}\n\n    // MARK: - List View", text)
if not body_match:
    errors.append("TranscriptsView.body not found")
else:
    body = body_match.group("body")
    if ".onChange(of: appState.transcriptSessions)" not in body:
        errors.append("TranscriptsView.body must reconcile selectedSession when appState.transcriptSessions changes")
    if "reconcileSelectedSession()" not in body:
        errors.append("TranscriptsView.body must call reconcileSelectedSession() from the transcriptSessions onChange")

sync_match = re.search(r"private func reconcileSelectedSession\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func prepareExport", text)
if not sync_match:
    errors.append("TranscriptsView.reconcileSelectedSession() not found")
else:
    body = sync_match.group("body")
    for token in [
        "guard let selectedSession else { return }",
        "appState.transcriptSessions.first(where: { $0.id == selectedSession.id })",
        "self.selectedSession = refreshedSession",
        "self.selectedSession = nil",
        "generatedMeetingNotes = nil",
        "meetingNotesSessionID = nil",
        "pendingDeleteSession = nil",
    ]:
        if token not in body:
            errors.append(f"reconcileSelectedSession must keep transcript detail state current through {token}")

if errors:
    print("Transcript selection sync verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Transcript selection sync verification passed")
