#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

for token in [
    "private static let transcriptSaveDebounceNanoseconds",
    "private var transcriptSaveTask: Task<Void, Never>?",
]:
    if token not in text:
        errors.append(f"AppState must coalesce transcript disk writes through {token}")

append_match = re.search(r"private func appendCurrentTranscriptLine\(from line: CaptionLine\) \{(?P<body>[\s\S]*?)\n    \}\n\n    var subtitleLines", text)
if not append_match:
    errors.append("AppState.appendCurrentTranscriptLine(from:) not found")
else:
    body = append_match.group("body")
    for token in [
        "currentTranscriptLines.append(transcriptLine)",
        "transcriptSessions[index].lines.append(transcriptLine)",
        "scheduleTranscriptSave()",
    ]:
        if token not in body:
            errors.append(f"appendCurrentTranscriptLine must update memory immediately and coalesce disk writes through {token}")
    if "transcriptSessions[index].lines = currentTranscriptLines" in body:
        errors.append("appendCurrentTranscriptLine must not rewrite the full active session line array for every sentence")
    if "saveTranscriptSessions()" in body:
        errors.append("appendCurrentTranscriptLine must not synchronously rewrite the full transcript archive for every sentence")
    sync_idx = body.find("transcriptSessions[index].lines.append(transcriptLine)")
    schedule_idx = body.find("scheduleTranscriptSave()")
    if min(sync_idx, schedule_idx) != -1 and not (sync_idx < schedule_idx):
        errors.append("appendCurrentTranscriptLine must schedule persistence after syncing the active session")

schedule_match = re.search(r"private func scheduleTranscriptSave\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func saveTranscriptSessionsImmediately", text)
if not schedule_match:
    errors.append("AppState.scheduleTranscriptSave() not found")
else:
    body = schedule_match.group("body")
    for token in [
        "guard transcriptSaveTask == nil else { return }",
        "Task { @MainActor [weak self] in",
        "try await Task.sleep(nanoseconds: Self.transcriptSaveDebounceNanoseconds)",
        "guard !Task.isCancelled else",
        "self.saveTranscriptSessions()",
        "self.transcriptSaveTask = nil",
    ]:
        if token not in body:
            errors.append(f"scheduleTranscriptSave must throttle saves and clear lifecycle state through {token}")

immediate_match = re.search(r"private func saveTranscriptSessionsImmediately\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func saveTranscriptSessions", text)
if not immediate_match:
    errors.append("AppState.saveTranscriptSessionsImmediately() not found")
else:
    body = immediate_match.group("body")
    for token in ["transcriptSaveTask?.cancel()", "transcriptSaveTask = nil", "saveTranscriptSessions()"]:
        if token not in body:
            errors.append(f"Immediate transcript saves must cancel pending throttled saves through {token}")

for name, pattern in [
    ("beginTranscriptSession", r"private func beginTranscriptSession\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func finishTranscriptSession"),
    ("finishTranscriptSession", r"private func finishTranscriptSession\(saveImmediately: Bool = true\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func deleteTranscriptSession"),
    ("deleteTranscriptSession", r"func deleteTranscriptSession\(_ session: TranscriptSession\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func deleteAllTranscriptSessions"),
    ("deleteAllTranscriptSessions", r"func deleteAllTranscriptSessions\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func restartTranscriptSessionIfRunning"),
]:
    match = re.search(pattern, text)
    if not match:
        errors.append(f"AppState.{name} not found")
    elif "saveTranscriptSessionsImmediately()" not in match.group("body"):
        errors.append(f"AppState.{name} must force transcript persistence at explicit lifecycle boundaries")

if "transcriptSaveTask?.cancel()" not in text[text.find("deinit {"):]:
    errors.append("AppState.deinit must cancel any pending transcript save task")

if errors:
    print("Transcript save coalescing verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Transcript save coalescing verification passed")
