#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
session_path = root / "LiveBuddy" / "Models" / "TranscriptSession.swift"
view_path = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
export_path = root / "LiveBuddy" / "Models" / "TranscriptExport.swift"
notes_path = root / "LiveBuddy" / "Models" / "MeetingNotes.swift"
tests_path = root / "LiveBuddyTests" / "TranscriptSessionTests.swift"
session = session_path.read_text()
view = view_path.read_text()
export = export_path.read_text()
notes = notes_path.read_text()
tests = tests_path.read_text()
errors: list[str] = []

for token in [
    "func formattedDuration(language: InterfaceLanguage) -> String",
    "language.localized(.live)",
    "func textForMode(_ mode: TranscriptViewMode, language: InterfaceLanguage = .english) -> String",
    "language.localized(.transcriptExportTitle)",
    "language.localized(.meetingNotesSource)",
    "language.localized(.meetingNotesTargetLanguage)",
    "language.localized(.meetingNotesDuration)",
    "formattedDuration(language: language)",
    "language.localized(.transcriptExportMode)",
    "mode.localizedTitle(language: language)",
    "language.localized(.original)",
    "language.localized(.translated)",
]:
    if token not in session:
        errors.append(f"TranscriptSession copy/share text must localize through {token}")

for forbidden in [
    '"Transcript Session:',
    '"Source:',
    '"Target Language:',
    '"Duration:',
    '"Mode:',
    '"Original:',
    '"Translated:',
]:
    if forbidden in session:
        errors.append(f"TranscriptSession.textForMode must not hard-code English copy/share label: {forbidden}")

for token in [
    "session.textForMode(.both, language: appState.settings.interfaceLanguage)",
    "session.textForMode(viewMode, language: appState.settings.interfaceLanguage)",
    "ShareLink(item: session.textForMode(viewMode, language: appState.settings.interfaceLanguage))",
    "session.formattedDuration(language: appState.settings.interfaceLanguage)",
]:
    if token not in view:
        errors.append(f"TranscriptsView must use localized transcript copy/share/runtime text through {token}")

for token in [
    "session.formattedDuration(language: language)",
]:
    if token not in export:
        errors.append(f"Transcript markdown export must use localized duration through {token}")
    if token not in notes:
        errors.append(f"Meeting notes export must use localized duration through {token}")

for token in [
    "textForModeUsesSelectedInterfaceLanguageForCopyAndShareText",
    "activeDurationUsesSelectedInterfaceLanguage",
    "language: .simplifiedChinese",
    "转录记录:",
    "来源: Screen audio",
    "目标语言: English",
    "模式: 双语",
    "原文: 你好 世界",
    "译文: Hello world",
    "进行中",
    "Transcript Session:" ,
    "Original:",
    "Translated:",
]:
    if token not in tests:
        errors.append(f"TranscriptSessionTests must cover localized copy/share text through {token}")

if errors:
    print("Transcript copy/share localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Transcript copy/share localization verification passed")
