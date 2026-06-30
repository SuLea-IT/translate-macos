#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
settings_view_path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
language_path = root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift"
settings_view = settings_view_path.read_text()
language = language_path.read_text()
errors: list[str] = []

copy_match = re.search(r"private func copyLogsFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func exportLogsFromUI", settings_view)
if not copy_match:
    errors.append("SettingsView.copyLogsFromUI() not found")
else:
    body = copy_match.group("body")
    for token in [
        "let didCopy = NSPasteboard.general.setString(logText, forType: .string)",
        "guard didCopy else",
        "logExportErrorMessage = appState.t(.copyFailed)",
        "return",
        "logExportErrorMessage = nil",
    ]:
        if token not in body:
            errors.append(f"copyLogsFromUI() must handle pasteboard failure through {token}")
    if "NSPasteboard.general.setString(logText, forType: .string)\n        logExportErrorMessage = nil" in body:
        errors.append("copyLogsFromUI() must not ignore NSPasteboard.setString return value")

for token in [
    "case copyFailed",
    ".copyFailed: \"Copy failed. Please try again.\"",
    ".copyFailed: \"复制失败，请重试。\"",
]:
    if token not in language:
        errors.append(f"InterfaceLanguage must localize copy failure feedback through {token}")

if errors:
    print("Log copy failure feedback verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Log copy failure feedback verification passed")
