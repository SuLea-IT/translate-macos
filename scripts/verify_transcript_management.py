#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
transcripts_view = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
interface_file = root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift"
errors: list[str] = []

view_text = transcripts_view.read_text()
interface_text = interface_file.read_text()

for token in [
    "isShowingClearTranscriptsConfirmation",
    ".confirmationDialog(",
    ".clearTranscriptsConfirmationTitle",
    ".clearTranscriptsConfirmationMessage",
    "clearAllTranscriptSessionsFromUI()",
]:
    if token not in view_text:
        errors.append(f"TranscriptsView must protect bulk transcript deletion through {token}")

if "appState.deleteAllTranscriptSessions()" not in view_text:
    errors.append("TranscriptsView must still call AppState.deleteAllTranscriptSessions() after confirmation")

for key in ["clearTranscriptsConfirmationTitle", "clearTranscriptsConfirmationMessage"]:
    if f"case {key}" not in interface_text:
        errors.append(f"missing InterfaceText.{key}")
    if interface_text.count(f".{key}:") < 8:
        errors.append(f"InterfaceText.{key} must be translated for every supported language")

if errors:
    print("Transcript management verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)
print("Transcript management verification passed")
