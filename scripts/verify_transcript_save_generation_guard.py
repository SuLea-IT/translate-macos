#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

if "private var transcriptSaveGeneration = UUID()" not in text:
    errors.append("AppState must track transcriptSaveGeneration to isolate stale debounced transcript save tasks")

schedule_match = re.search(r"private func scheduleTranscriptSave\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func saveTranscriptSessionsImmediately", text)
if not schedule_match:
    errors.append("AppState.scheduleTranscriptSave() not found")
else:
    body = schedule_match.group("body")
    for token in [
        "guard transcriptSaveTask == nil else { return }",
        "let generation = UUID()",
        "transcriptSaveGeneration = generation",
        "transcriptSaveTask = Task",
        "guard self.transcriptSaveGeneration == generation else { return }",
        "self.saveTranscriptSessions()",
        "if self.transcriptSaveGeneration == generation",
        "self.transcriptSaveTask = nil",
    ]:
        if token not in body:
            errors.append(f"scheduleTranscriptSave must guard debounced save lifecycle through {token}")
    if "transcriptSaveTask = nil" in body and "transcriptSaveGeneration == generation" not in body:
        errors.append("scheduleTranscriptSave must not clear transcriptSaveTask without checking generation")
    sleep_idx = body.find("try await Task.sleep")
    generation_guard_idx = body.find("guard self.transcriptSaveGeneration == generation else { return }", sleep_idx)
    save_idx = body.find("self.saveTranscriptSessions()")
    if -1 in [sleep_idx, generation_guard_idx, save_idx] or not (sleep_idx < generation_guard_idx < save_idx):
        errors.append("scheduleTranscriptSave must re-check generation after debounce sleep before writing transcripts")

immediate_match = re.search(r"private func saveTranscriptSessionsImmediately\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func saveTranscriptSessions", text)
if not immediate_match:
    errors.append("AppState.saveTranscriptSessionsImmediately() not found")
else:
    body = immediate_match.group("body")
    for token in [
        "transcriptSaveGeneration = UUID()",
        "transcriptSaveTask?.cancel()",
        "transcriptSaveTask = nil",
        "saveTranscriptSessions()",
    ]:
        if token not in body:
            errors.append(f"saveTranscriptSessionsImmediately must invalidate stale debounced transcript saves through {token}")

if errors:
    print("Transcript save generation guard verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Transcript save generation guard verification passed")
