#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
text = path.read_text()
errors: list[str] = []

match = re.search(
    r"private func reconcileSelectedSession\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func refreshMeetingNotesForCurrentMode",
    text,
)
if not match:
    errors.append("TranscriptsView.reconcileSelectedSession() not found before meeting-notes refresh helpers")
else:
    body = match.group("body")
    missing_selection_idx = body.find("self.selectedSession = nil")
    success_clear_idx = body.find("copySuccessMessage = nil", missing_selection_idx)
    for token in [
        "self.selectedSession = nil",
        "exportErrorMessage = nil",
        "copyErrorMessage = nil",
        "copySuccessMessage = nil",
    ]:
        if token not in body:
            errors.append(f"reconcileSelectedSession must clear stale transcript feedback when selection disappears through {token}")
    if missing_selection_idx == -1 or success_clear_idx == -1 or missing_selection_idx > success_clear_idx:
        errors.append("reconcileSelectedSession must clear copySuccessMessage after the selected session disappears")

if errors:
    print("Transcript reconcile copy-success cleanup verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Transcript reconcile copy-success cleanup verification passed")
