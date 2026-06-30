#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
transcripts_view = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
interface_file = root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift"
export_model = root / "LiveBuddy" / "Models" / "TranscriptExport.swift"
app_state_file = root / "LiveBuddy" / "Models" / "AppState.swift"
errors: list[str] = []

view_text = transcripts_view.read_text()
interface_text = interface_file.read_text()
export_text = export_model.read_text()
app_state_text = app_state_file.read_text()

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
    "private func clearActiveTranscriptState()",
    "private func restartTranscriptSessionIfRunning()",
    "private var currentTranscriptLines: [TranscriptLine] = []",
    "private func appendCurrentTranscriptLine(from line: CaptionLine)",
    "currentSessionID = nil",
    "captionDraft = \"\"",
    "originalDraft = \"\"",
    "completedOriginalSentences.removeAll()",
    "currentTranscriptLines.removeAll()",
    "captions.removeAll()",
    "beginTranscriptSession()",
]:
    if token not in app_state_text:
        errors.append(f"AppState must release active transcript state through {token}")

for context, pattern in [
    ("finishTranscriptSession", r"private func finishTranscriptSession\(saveImmediately: Bool = true\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func deleteTranscriptSession"),
    ("deleteTranscriptSession", r"func deleteTranscriptSession\(_ session: TranscriptSession\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func deleteAllTranscriptSessions"),
    ("deleteAllTranscriptSessions", r"func deleteAllTranscriptSessions\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func clearActiveTranscriptState"),
]:
    match = re.search(pattern, app_state_text)
    if not match:
        errors.append(f"AppState.{context} not found for active transcript cleanup")
    elif "clearActiveTranscriptState()" not in match.group("body"):
        errors.append(f"AppState.{context} must clear active transcript state when needed")

for context, pattern in [
    ("deleteTranscriptSession", r"func deleteTranscriptSession\(_ session: TranscriptSession\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func deleteAllTranscriptSessions"),
    ("deleteAllTranscriptSessions", r"func deleteAllTranscriptSessions\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func restartTranscriptSessionIfRunning"),
]:
    match = re.search(pattern, app_state_text)
    if not match:
        errors.append(f"AppState.{context} not found for live transcript continuity")
    elif "restartTranscriptSessionIfRunning()" not in match.group("body"):
        errors.append(f"AppState.{context} must start a fresh transcript session when clearing live history")

start_match = re.search(r"func start\(\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func stop", app_state_text)
if not start_match:
    errors.append("AppState.start() not found for transcript startup timing")
else:
    body = start_match.group("body")
    connect_index = body.find("try await client.connect()")
    capture_index = body.find("try await startCapture()")
    begin_index = body.find("beginTranscriptSession()")
    running_index = body.find("isRunning = true")
    if min(connect_index, capture_index, begin_index, running_index) == -1:
        errors.append("AppState.start() must connect, start capture, create transcript session, and mark running")
    elif not (connect_index < capture_index < begin_index < running_index):
        errors.append("AppState.start() must create transcript sessions only after connection and capture succeed, before isRunning = true")

append_caption_match = re.search(r"private func appendCaption\(_ text: String, language: String\?, kind: CaptionKind\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func appendCurrentTranscriptLine", app_state_text)
if not append_caption_match:
    errors.append("AppState.appendCaption(_:language:kind:) not found for full transcript history")
else:
    body = append_caption_match.group("body")
    for token in [
        "let line = CaptionLine(",
        "appendDisplayedCaption(line)",
        "appendCurrentTranscriptLine(from: line)",
    ]:
        if token not in body:
            errors.append(f"AppState.appendCaption must keep transcript history independent from display cache through {token}")
    if "captions.append(line)" in body:
        errors.append("AppState.appendCaption must not append directly to the trimmed display cache")
    if body.find("let line = CaptionLine(") > body.find("appendCurrentTranscriptLine(from: line)"):
        errors.append("AppState.appendCaption must persist the local line object into full transcript history")

append_display_match = re.search(r"private func appendDisplayedCaption\(_ line: CaptionLine\) -> CaptionLine \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not append_display_match:
    errors.append("AppState.appendDisplayedCaption(_:) not found for bounded display cache")
else:
    body = append_display_match.group("body")
    for token in [
        "captions.append(line)",
        "trimDisplayedCaptions()",
        "return line",
    ]:
        if token not in body:
            errors.append(f"AppState.appendDisplayedCaption(_:) must centralize live display trimming through {token}")

trim_display_match = re.search(r"private func trimDisplayedCaptions\(\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not trim_display_match:
    errors.append("AppState.trimDisplayedCaptions() not found for bounded display cache")
else:
    body = trim_display_match.group("body")
    for token in [
        "captions.count > Self.maxDisplayedCaptionLines",
        "captions.removeFirst(captions.count - Self.maxDisplayedCaptionLines)",
    ]:
        if token not in body:
            errors.append(f"AppState.trimDisplayedCaptions() must bound live display cache through {token}")

append_history_match = re.search(r"private func appendCurrentTranscriptLine\(from line: CaptionLine\) \{(?P<body>[\s\S]*?)\n    \}\n\n    var subtitleLines", app_state_text)
if not append_history_match:
    errors.append("AppState.appendCurrentTranscriptLine(from:) not found for live transcript persistence")
else:
    body = append_history_match.group("body")
    for token in [
        "let transcriptLine = TranscriptLine(",
        "currentTranscriptLines.append(transcriptLine)",
        "if let sessionID = currentSessionID",
        "transcriptSessions.firstIndex(where: { $0.id == sessionID })",
        "transcriptSessions[index].lines.append(transcriptLine)",
        "scheduleTranscriptSave()",
    ]:
        if token not in body:
            errors.append(f"AppState.appendCurrentTranscriptLine must keep running transcript detail current and schedule disk persistence through {token}")
    if "transcriptSessions[index].lines = currentTranscriptLines" in body:
        errors.append("AppState.appendCurrentTranscriptLine must append the new transcript line instead of rewriting the full active session array")
    if "saveTranscriptSessions()" in body:
        errors.append("AppState.appendCurrentTranscriptLine must coalesce transcript disk writes instead of saving every sentence")

finish_match = re.search(r"private func finishTranscriptSession\(saveImmediately: Bool = true\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func deleteTranscriptSession", app_state_text)
if finish_match:
    body = finish_match.group("body")
    if "session.lines = currentTranscriptLines" not in body:
        errors.append("AppState.finishTranscriptSession must persist full currentTranscriptLines")
    if "appendDisplayedCaption(line)" not in body or "appendCurrentTranscriptLine(from: line)" not in body:
        errors.append("AppState.finishTranscriptSession must flush the final draft through bounded display cache and full transcript history")
    if ".filter { $0.kind == .output }" in body and "captions" in body:
        errors.append("AppState.finishTranscriptSession must not rebuild transcript from trimmed caption display cache")

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
if "language.localized(.transcriptArchiveTitle)" not in export_text:
    errors.append("Bulk transcript export must use the localized Markdown archive header")
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
