#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

match = re.search(r"func clearLogs\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func saveSubtitleScreenFrame", text)
if not match:
    errors.append("AppState.clearLogs() not found")
else:
    body = match.group("body")
    if "logs.removeAll()" not in body:
        errors.append("clearLogs must remove all log entries")
    if "appendLog(" in body or "logs.append(" in body:
        errors.append("clearLogs must leave the log list empty; do not append a replacement entry after clearing")

settings_view = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
view_text = settings_view.read_text()
clear_match = re.search(r"private func clearLogsFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}\n\}", view_text)
if not clear_match:
    errors.append("SettingsView.clearLogsFromUI() not found")
else:
    body = clear_match.group("body")
    for token in ["appState.clearLogs()", "logExportErrorMessage = nil"]:
        if token not in body:
            errors.append(f"clearLogsFromUI must reset UI log state through {token}")

if errors:
    print("Log clear empty-state verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Log clear empty-state verification passed")
