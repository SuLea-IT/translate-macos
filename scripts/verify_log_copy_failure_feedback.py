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

for token in [
    "@State private var logCopyErrorMessage: String?",
    "if let logCopyErrorMessage",
    "Text(logCopyErrorMessage)",
]:
    if token not in settings_view:
        errors.append(f"SettingsView logs UI must render copy failures independently through {token}")

copy_match = re.search(r"private func copyLogsFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func exportLogsFromUI", settings_view)
if not copy_match:
    errors.append("SettingsView.copyLogsFromUI() not found")
else:
    body = copy_match.group("body")
    for token in [
        "let didCopy = NSPasteboard.general.setString(logText, forType: .string)",
        "guard didCopy else",
        "logCopyErrorMessage = appState.t(.copyFailed)",
        "logExportErrorMessage = nil",
        "return",
        "logCopyErrorMessage = nil",
    ]:
        if token not in body:
            errors.append(f"copyLogsFromUI() must handle pasteboard failure through {token}")
    if "logExportErrorMessage = appState.t(.copyFailed)" in body:
        errors.append("copyLogsFromUI() must not store copy failures in logExportErrorMessage")
    if "NSPasteboard.general.setString(logText, forType: .string)\n        logExportErrorMessage = nil" in body:
        errors.append("copyLogsFromUI() must not ignore NSPasteboard.setString return value")

for pattern_name, pattern in [
    ("exportLogsFromUI", r"private func exportLogsFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("clearLogsFromUI", r"private func clearLogsFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}"),
]:
    match = re.search(pattern, settings_view)
    if not match:
        errors.append(f"SettingsView.{pattern_name} not found")
    elif "logCopyErrorMessage = nil" not in match.group("body"):
        errors.append(f"SettingsView.{pattern_name} must clear stale log copy feedback")

logs_view_start = settings_view.find("private var logsView: some View")
log_file_exporter_start = settings_view.find(".fileExporter(", logs_view_start)
log_file_exporter_handler_start = settings_view.find(") { result in", log_file_exporter_start)
log_confirmation_start = settings_view.find("\n        .confirmationDialog", log_file_exporter_handler_start)
if (
    logs_view_start == -1
    or log_file_exporter_start == -1
    or log_file_exporter_handler_start == -1
    or log_confirmation_start == -1
):
    errors.append("SettingsView logs fileExporter completion handler not found")
else:
    body = settings_view[log_file_exporter_handler_start:log_confirmation_start]
    if "logCopyErrorMessage = nil" not in body:
        errors.append("Log fileExporter completion must clear stale log copy feedback")

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
