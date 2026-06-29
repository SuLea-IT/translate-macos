#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
transcripts_view = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
interface_file = root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift"
export_model = root / "LiveBuddy" / "Models" / "TranscriptExport.swift"
errors: list[str] = []

view_text = transcripts_view.read_text()
interface_text = interface_file.read_text()
export_text = export_model.read_text()

for token in [
    "isShowingClearTranscriptsConfirmation",
    ".confirmationDialog(",
    ".clearTranscriptsConfirmationTitle",
    ".clearTranscriptsConfirmationMessage",
    "clearAllTranscriptSessionsFromUI()",
]:
    if token not in view_text:
        errors.append(f"TranscriptsView must protect bulk transcript deletion through {token}")

for token in [
    "pendingDeleteSession",
    "isShowingDeleteTranscriptConfirmation",
    ".deleteTranscriptConfirmationTitle",
    ".deleteTranscriptConfirmationMessage",
    "requestDeleteTranscriptSession(session)",
    "deletePendingTranscriptSessionFromUI()",
]:
    if token not in view_text:
        errors.append(f"TranscriptsView must protect single transcript deletion through {token}")

if "appState.deleteAllTranscriptSessions()" not in view_text:
    errors.append("TranscriptsView must still call AppState.deleteAllTranscriptSessions() after confirmation")
if "appState.deleteTranscriptSession(session)" not in view_text:
    errors.append("TranscriptsView must still delete the pending transcript after confirmation")
context_menu_start = view_text.find(".contextMenu {")
context_menu_end = view_text.find("if filteredSessions.isEmpty", context_menu_start)
context_menu_body = view_text[context_menu_start:context_menu_end] if context_menu_start != -1 and context_menu_end != -1 else ""
if "appState.deleteTranscriptSession(session)" in context_menu_body:
    errors.append("TranscriptsView must not delete a single transcript directly from the context menu")

for token in [
    ".onChange(of: appState.transcriptSessions)",
    "reconcileSelectedSession()",
    "private func reconcileSelectedSession()",
    "appState.transcriptSessions.first(where: { $0.id == selectedSession.id })",
    "self.selectedSession = refreshedSession",
    "self.selectedSession = nil",
    "generatedMeetingNotes = nil",
    "meetingNotesSessionID = nil",
    "pendingDeleteSession = nil",
]:
    if token not in view_text:
        errors.append(f"TranscriptsView must keep selected transcript detail synchronized through {token}")

for token in [
    "TranscriptArchiveExporter",
    "exportAllTranscriptsFromUI()",
    ".exportAllTranscripts",
    "TranscriptExportDocument(text: archiveText",
]:
    if token not in view_text:
        errors.append(f"TranscriptsView must expose bulk transcript export through {token}")

if "struct TranscriptArchiveExporter" not in export_text:
    errors.append("TranscriptExport.swift must provide TranscriptArchiveExporter for bulk backup")
if "LiveBuddy Transcript Archive" not in export_text:
    errors.append("Bulk transcript export must use a stable Markdown archive header")
if "func defaultFileName(date:" not in export_text:
    errors.append("Bulk transcript export must provide a deterministic default file name")

for key in ["clearTranscriptsConfirmationTitle", "clearTranscriptsConfirmationMessage", "deleteTranscriptConfirmationTitle", "deleteTranscriptConfirmationMessage", "exportAllTranscripts"]:
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
