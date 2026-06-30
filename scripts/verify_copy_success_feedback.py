#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
settings = (root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift").read_text()
transcripts = (root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift").read_text()
language = (root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift").read_text()
errors: list[str] = []

for token in ["case copiedToClipboard", ".copiedToClipboard:"]:
    if token not in language:
        errors.append(f"InterfaceLanguage must define localized copy-success feedback through {token}")
if language.count(".copiedToClipboard:") < 8:
    errors.append("InterfaceText.copiedToClipboard must be translated for every supported language")

for token in [
    "@State private var logCopySuccessMessage: String?",
    "if let logCopySuccessMessage",
    "Text(logCopySuccessMessage)",
    "logCopySuccessMessage = appState.t(.copiedToClipboard)",
]:
    if token not in settings:
        errors.append(f"SettingsView logs UI must surface copy success through {token}")

copy_logs_match = re.search(r"private func copyLogsFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func exportLogsFromUI", settings)
if not copy_logs_match:
    errors.append("SettingsView.copyLogsFromUI() not found")
else:
    body = copy_logs_match.group("body")
    required = [
        "guard didCopy else",
        "logCopyErrorMessage = appState.t(.copyFailed)",
        "logCopySuccessMessage = nil",
        "return",
        "logCopyErrorMessage = nil",
        "logCopySuccessMessage = appState.t(.copiedToClipboard)",
        "logExportErrorMessage = nil",
    ]
    for token in required:
        if token not in body:
            errors.append(f"copyLogsFromUI() must set copy success/failure feedback through {token}")
    fail_idx = body.find("logCopyErrorMessage = appState.t(.copyFailed)")
    clear_success_idx = body.find("logCopySuccessMessage = nil", fail_idx)
    success_idx = body.find("logCopySuccessMessage = appState.t(.copiedToClipboard)")
    if -1 in [fail_idx, clear_success_idx, success_idx] or not (fail_idx < clear_success_idx < success_idx):
        errors.append("copyLogsFromUI() must clear success on failure and set success only after pasteboard succeeds")

for pattern_name, pattern in [
    ("exportLogsFromUI", r"private func exportLogsFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("clearLogsFromUI", r"private func clearLogsFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}"),
]:
    match = re.search(pattern, settings)
    if not match:
        errors.append(f"SettingsView.{pattern_name} not found")
    elif "logCopySuccessMessage = nil" not in match.group("body"):
        errors.append(f"SettingsView.{pattern_name} must clear stale log copy success feedback")

for token in [
    "@State private var copySuccessMessage: String?",
    "if let copySuccessMessage",
    "Text(copySuccessMessage)",
    "copySuccessMessage = appState.t(.copiedToClipboard)",
]:
    if token not in transcripts:
        errors.append(f"TranscriptsView must surface copy success through {token}")

copy_transcript_match = re.search(
    r"private func copyTranscriptTextToPasteboard\(_ text: String\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func exportMeetingNotes",
    transcripts,
)
if not copy_transcript_match:
    errors.append("TranscriptsView.copyTranscriptTextToPasteboard(_:) not found")
else:
    body = copy_transcript_match.group("body")
    required = [
        "guard didCopy else",
        "copyErrorMessage = appState.t(.copyFailed)",
        "copySuccessMessage = nil",
        "return",
        "copyErrorMessage = nil",
        "copySuccessMessage = appState.t(.copiedToClipboard)",
        "exportErrorMessage = nil",
    ]
    for token in required:
        if token not in body:
            errors.append(f"copyTranscriptTextToPasteboard(_:) must set copy success/failure feedback through {token}")
    fail_idx = body.find("copyErrorMessage = appState.t(.copyFailed)")
    clear_success_idx = body.find("copySuccessMessage = nil", fail_idx)
    success_idx = body.find("copySuccessMessage = appState.t(.copiedToClipboard)")
    if -1 in [fail_idx, clear_success_idx, success_idx] or not (fail_idx < clear_success_idx < success_idx):
        errors.append("copyTranscriptTextToPasteboard(_:) must clear success on failure and set success only after pasteboard succeeds")

for pattern_name, pattern in [
    ("clearTranscriptDetailFeedbackForSelectionChange", r"private func clearTranscriptDetailFeedbackForSelectionChange\(\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("clearAllTranscriptSessionsFromUI", r"private func clearAllTranscriptSessionsFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("deletePendingTranscriptSessionFromUI", r"private func deletePendingTranscriptSessionFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("prepareExport", r"private func prepareExport\(session: TranscriptSession, format: TranscriptExportFormat\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("exportAllTranscriptsFromUI", r"private func exportAllTranscriptsFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("exportMeetingNotes", r"private func exportMeetingNotes\(_ notes: MeetingNotes, session: TranscriptSession\) \{(?P<body>[\s\S]*?)\n    \}"),
]:
    match = re.search(pattern, transcripts)
    if not match:
        errors.append(f"TranscriptsView.{pattern_name} not found")
    elif "copySuccessMessage = nil" not in match.group("body"):
        errors.append(f"TranscriptsView.{pattern_name} must clear stale copy success feedback")

if errors:
    print("Copy success feedback verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Copy success feedback verification passed")
