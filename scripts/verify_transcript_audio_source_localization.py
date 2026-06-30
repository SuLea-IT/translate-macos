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
    "func localizedAudioSource(language: InterfaceLanguage) -> String",
    "case AudioSource.screen.title",
    "case AudioSource.microphone.title",
    "case AudioSource.both.title",
    "AudioSource.screen.localizedTitle(language: language)",
    "AudioSource.microphone.localizedTitle(language: language)",
    "AudioSource.both.localizedTitle(language: language)",
    "return audioSource",
]:
    if token not in session:
        errors.append(f"TranscriptSession must localize known stored audio source labels through {token}")

for token in [
    "localizedAudioSource(language: language)",
]:
    if token not in session:
        errors.append(f"TranscriptSession.textForMode must use {token}")
    if token not in export:
        errors.append(f"TranscriptExporter markdown must use {token}")
    if token not in notes:
        errors.append(f"MeetingNotes markdown must use {token}")

for token in [
    "session.localizedAudioSource(language: appState.settings.interfaceLanguage)",
]:
    if view.count(token) < 2:
        errors.append("TranscriptsView must localize audio source in both detail header and session cards")

for forbidden in [
    "Label(session.audioSource, systemImage: \"waveform\")",
    "- \\(language.localized(.meetingNotesSource)): \\(session.audioSource)",
    "\\(language.localized(.meetingNotesSource)): \\(audioSource)",
]:
    if forbidden in view or forbidden in export or forbidden in notes or forbidden in session:
        errors.append(f"User-visible audio source must not render the stored English label directly: {forbidden}")

for token in [
    "localizedAudioSourceMapsKnownLegacyAudioSourceTitles",
    "textForModeLocalizesStoredAudioSource",
    "language: .simplifiedChinese",
    "屏幕音频",
    "麦克风",
    "屏幕 + 麦克风",
    "Custom Aggregate Device",
]:
    if token not in tests:
        errors.append(f"TranscriptSessionTests must cover localized audio source through {token}")

if errors:
    print("Transcript audio source localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Transcript audio source localization verification passed")
