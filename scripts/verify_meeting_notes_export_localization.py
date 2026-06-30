#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
model_path = root / "LiveBuddy" / "Models" / "MeetingNotes.swift"
view_path = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
interface_path = root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift"
tests_path = root / "LiveBuddyTests" / "MeetingNotesTests.swift"
model = model_path.read_text()
view = view_path.read_text()
interface = interface_path.read_text()
tests = tests_path.read_text()
errors: list[str] = []

required_keys = [
    "meetingNotesStarted",
    "meetingNotesSource",
    "meetingNotesTargetLanguage",
    "meetingNotesDuration",
    "noMeetingNotesContent",
]
for key in required_keys:
    if f"case {key}" not in interface:
        errors.append(f"InterfaceText must include {key}")
    if interface.count(f".{key}:") < 8:
        errors.append(f"InterfaceText.{key} must be translated for every supported language")

for token in [
    "func markdown(for notes: MeetingNotes, session: TranscriptSession, language: InterfaceLanguage = .english) -> String",
    "language.localized(.meetingNotes)",
    "language.localized(.meetingNotesStarted)",
    "language.localized(.meetingNotesSource)",
    "language.localized(.meetingNotesTargetLanguage)",
    "language.localized(.meetingNotesDuration)",
    "language.localized(.meetingSummary)",
    "language.localized(.meetingKeyPoints)",
    "language.localized(.meetingActionItems)",
    "language.localized(.meetingTimeline)",
    "language.localized(.noActionItemsFound)",
    "language.localized(.noMeetingNotesContent)",
]:
    if token not in model:
        errors.append(f"MeetingNotesGenerator.markdown must localize exported markdown through {token}")

for forbidden in [
    '"# Meeting Notes"',
    '"- Started:',
    '"- Source:',
    '"- Target Language:',
    '"- Duration:',
    '"## Summary"',
    '"## Key Points"',
    '"## Action Items"',
    '"## Timeline"',
    'emptyText: "No action items found."',
    'emptyText: String = "No content."',
]:
    if forbidden in model:
        errors.append(f"Meeting notes markdown must not hard-code English export text: {forbidden}")

for token in [
    "meetingNotesGenerator.markdown(for: notes, session: session, language: appState.settings.interfaceLanguage)",
    "meetingNotesGenerator.markdown(for: notes, session: session, language: appState.settings.interfaceLanguage)",
]:
    if token not in view:
        errors.append(f"TranscriptsView must copy/export meeting notes with current interface language through {token}")

for token in [
    "markdownUsesSelectedInterfaceLanguageForHeadingsAndEmptyText",
    "language: .simplifiedChinese",
    "# 会议纪要",
    "## 摘要",
    "## 重点",
    "## 待办事项",
    "- 未发现待办事项",
    "#expect(markdown.contains(\"# Meeting Notes\") == false)",
]:
    if token not in tests:
        errors.append(f"MeetingNotesTests must cover localized markdown through {token}")

if errors:
    print("Meeting notes export localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Meeting notes export localization verification passed")
