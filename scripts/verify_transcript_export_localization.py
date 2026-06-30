#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
export_path = root / "LiveBuddy" / "Models" / "TranscriptExport.swift"
view_path = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
interface_path = root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift"
tests_path = root / "LiveBuddyTests" / "TranscriptExportTests.swift"
export = export_path.read_text()
view = view_path.read_text()
interface = interface_path.read_text()
tests = tests_path.read_text()
errors: list[str] = []

required_keys = [
    "transcriptExportTitle",
    "transcriptArchiveTitle",
    "transcriptSessionsCount",
    "transcriptExportMode",
]
for key in required_keys:
    if f"case {key}" not in interface:
        errors.append(f"InterfaceText must include {key}")
    if interface.count(f".{key}:") < 8:
        errors.append(f"InterfaceText.{key} must be translated for every supported language")

required_export_tokens = [
    "func export(session: TranscriptSession, mode: TranscriptViewMode, format: TranscriptExportFormat, language: InterfaceLanguage = .english) -> String",
    "composeMarkdown(session: session, mode: mode, language: language)",
    "private func composeMarkdown(session: TranscriptSession, mode: TranscriptViewMode, language: InterfaceLanguage) -> String",
    "language.localized(.transcriptExportTitle)",
    "language.localized(.meetingNotesStarted)",
    "language.localized(.meetingNotesSource)",
    "language.localized(.meetingNotesTargetLanguage)",
    "language.localized(.meetingNotesDuration)",
    "language.localized(.transcriptExportMode)",
    "mode.localizedTitle(language: language)",
    "func export(sessions: [TranscriptSession], mode: TranscriptViewMode, language: InterfaceLanguage = .english) -> String",
    "language.localized(.transcriptArchiveTitle)",
    "language.localized(.transcriptSessionsCount, arguments: [sessions.count])",
    "transcriptExporter.export(session: session, mode: mode, format: .markdown, language: language)",
]
for token in required_export_tokens:
    if token not in export:
        errors.append(f"Transcript export must localize markdown through {token}")

for forbidden in [
    '"# Transcript"',
    '"# LiveBuddy Transcript Archive"',
    '"- Started:',
    '"- Source:',
    '"- Target Language:',
    '"- Duration:',
    '"- Mode:',
    '"- Sessions:',
]:
    if forbidden in export:
        errors.append(f"Transcript markdown export must not hard-code English metadata: {forbidden}")

for token in [
    "transcriptExporter.export(session: session, mode: viewMode, format: format, language: appState.settings.interfaceLanguage)",
    "transcriptArchiveExporter.export(sessions: appState.transcriptSessions, mode: .both, language: appState.settings.interfaceLanguage)",
]:
    if token not in view:
        errors.append(f"TranscriptsView must export with current interface language through {token}")

for token in [
    "markdownUsesSelectedInterfaceLanguageForMetadata",
    "archiveExporterUsesSelectedInterfaceLanguageForMetadata",
    "language: .simplifiedChinese",
    "# 转录记录",
    "# 转录归档",
    "- 时长: 10s",
    "- 模式: 双语",
]:
    if token not in tests:
        errors.append(f"TranscriptExportTests must cover localized markdown through {token}")

if errors:
    print("Transcript export localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Transcript export localization verification passed")
