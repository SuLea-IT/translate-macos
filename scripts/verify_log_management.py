#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
settings_view = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
app_state = root / "LiveBuddy" / "Models" / "AppState.swift"
interface_file = root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift"
errors: list[str] = []

view_text = settings_view.read_text()
app_state_text = app_state.read_text()
interface_text = interface_file.read_text()

for token in [
    "LogExporter",
    "exportLogsFromUI()",
    "copyLogsFromUI()",
    ".exportLogs",
    ".copyLogs",
    "TranscriptExportDocument(text: logText",
]:
    if token not in view_text:
        errors.append(f"Logs view must expose diagnostic log sharing through {token}")

for token in [
    "isShowingClearLogsConfirmation",
    ".confirmationDialog(",
    ".clearLogsConfirmationTitle",
    ".clearLogsConfirmationMessage",
    "clearLogsFromUI()",
]:
    if token not in view_text:
        errors.append(f"Logs view must confirm destructive log clearing through {token}")

if "appState.clearLogs()" in view_text and "private func clearLogsFromUI()" not in view_text:
    errors.append("Logs clear action must route through a UI helper used by the confirmation dialog")

if "struct LogExporter" not in app_state_text:
    errors.append("AppState.swift must provide LogExporter for reusable log formatting")
for token in ["func export(entries:", "func defaultFileName(date:", "language.localized(.runtimeLogs)", "ERROR", "INFO"]:
    if token not in app_state_text:
        errors.append(f"LogExporter must include {token}")

for key in ["exportLogs", "copyLogs", "clearLogsConfirmationTitle", "clearLogsConfirmationMessage"]:
    if f"case {key}" not in interface_text:
        errors.append(f"missing InterfaceText.{key}")
    if interface_text.count(f".{key}:") < 8:
        errors.append(f"InterfaceText.{key} must be translated for every supported language")

if errors:
    print("Log management verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)
print("Log management verification passed")
