#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
view_path = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
text = view_path.read_text()
errors: list[str] = []

for token in [
    "@State private var copyErrorMessage: String?",
    "copyTranscriptTextToPasteboard(session.textForMode(.both, language: appState.settings.interfaceLanguage))",
    "copyTranscriptTextToPasteboard(session.textForMode(viewMode, language: appState.settings.interfaceLanguage))",
    "copyTranscriptTextToPasteboard(meetingNotesGenerator.markdown(for: notes, session: session, language: appState.settings.interfaceLanguage))",
    "if let copyErrorMessage",
    "Text(copyErrorMessage)",
]:
    if token not in text:
        errors.append(f"TranscriptsView must surface transcript copy failure feedback through {token}")

helper_match = re.search(
    r"private func copyTranscriptTextToPasteboard\(_ text: String\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func exportMeetingNotes",
    text,
)
if not helper_match:
    errors.append("TranscriptsView.copyTranscriptTextToPasteboard(_:) not found")
else:
    body = helper_match.group("body")
    for token in [
        "let didCopy = NSPasteboard.general.setString(text, forType: .string)",
        "guard didCopy else",
        "copyErrorMessage = appState.t(.copyFailed)",
        "exportErrorMessage = nil",
        "return",
        "copyErrorMessage = nil\n        exportErrorMessage = nil",
    ]:
        if token not in body:
            errors.append(f"copyTranscriptTextToPasteboard(_:) must handle pasteboard failures through {token}")

for forbidden in [
    "NSPasteboard.general.setString(session.textForMode(.both, language: appState.settings.interfaceLanguage), forType: .string)",
    "NSPasteboard.general.setString(session.textForMode(viewMode, language: appState.settings.interfaceLanguage), forType: .string)",
    "NSPasteboard.general.setString(meetingNotesGenerator.markdown(for: notes, session: session, language: appState.settings.interfaceLanguage), forType: .string)",
]:
    if forbidden in text:
        errors.append(f"TranscriptsView must not ignore pasteboard copy result: {forbidden}")

for pattern_name, pattern in [
    ("clearTranscriptDetailFeedbackForSelectionChange", r"private func clearTranscriptDetailFeedbackForSelectionChange\(\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("clearAllTranscriptSessionsFromUI", r"private func clearAllTranscriptSessionsFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("deletePendingTranscriptSessionFromUI", r"private func deletePendingTranscriptSessionFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("prepareExport", r"private func prepareExport\(session: TranscriptSession, format: TranscriptExportFormat\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("exportAllTranscriptsFromUI", r"private func exportAllTranscriptsFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("exportMeetingNotes", r"private func exportMeetingNotes\(_ notes: MeetingNotes, session: TranscriptSession\) \{(?P<body>[\s\S]*?)\n    \}"),
]:
    match = re.search(pattern, text)
    if not match:
        errors.append(f"TranscriptsView.{pattern_name} not found")
    elif "copyErrorMessage = nil" not in match.group("body"):
        errors.append(f"TranscriptsView.{pattern_name} must clear stale copy feedback")

if errors:
    print("Transcript copy failure feedback verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Transcript copy failure feedback verification passed")
