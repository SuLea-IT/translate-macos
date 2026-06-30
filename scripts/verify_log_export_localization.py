#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
settings_view_path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
interface_path = root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift"
tests_path = root / "LiveBuddyTests" / "LogExportTests.swift"
app_state = app_state_path.read_text()
settings_view = settings_view_path.read_text()
interface = interface_path.read_text()
tests = tests_path.read_text()
errors: list[str] = []

if "case noLogEntries" not in interface:
    errors.append("InterfaceText must include noLogEntries")
if interface.count(".noLogEntries:") < 8:
    errors.append("InterfaceText.noLogEntries must be translated for every supported language")

for token in [
    "func export(entries: [LogEntry], language: InterfaceLanguage = .english) -> String",
    "language.localized(.runtimeLogs)",
    "language.localized(.noLogEntries)",
]:
    if token not in app_state:
        errors.append(f"LogExporter must localize exported text through {token}")

for forbidden in [
    '"# Runtime Logs',
    '"No log entries.',
]:
    if forbidden in app_state:
        errors.append(f"LogExporter must not hard-code English export text: {forbidden}")

for token in [
    "LogExporter().export(entries: appState.logs, language: appState.settings.interfaceLanguage)",
    "exporter.export(entries: appState.logs, language: appState.settings.interfaceLanguage)",
]:
    if token not in settings_view:
        errors.append(f"SettingsView must copy/export logs with the current interface language through {token}")

for token in [
    "exporterUsesSelectedInterfaceLanguageForTitleAndEmptyState",
    "language: .simplifiedChinese",
    "# 运行日志",
    "暂无日志。",
    "# Runtime Logs",
    "No log entries.",
]:
    if token not in tests:
        errors.append(f"LogExportTests must cover localized logs through {token}")

if errors:
    print("Log export localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Log export localization verification passed")
