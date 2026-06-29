#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = app_state_path.read_text()
errors: list[str] = []

for token in [
    "private var currentTranscriptLines: [TranscriptLine] = []",
    "currentTranscriptLines.removeAll()",
    "appendCurrentTranscriptLine(from: line)",
    "private func appendCurrentTranscriptLine(from line: CaptionLine)",
]:
    if token not in text:
        errors.append(f"AppState must keep full transcript history separately from caption display cache through {token}")

append_match = re.search(r"private func appendCaption\(_ text: String, language: String\?, kind: CaptionKind\) \{(?P<body>[\s\S]*?)\n    \}\n\n    var subtitleLines", text)
if not append_match:
    errors.append("AppState.appendCaption(_:language:kind:) not found")
else:
    body = append_match.group("body")
    if "let line = CaptionLine(" not in body:
        errors.append("appendCaption must create a CaptionLine value before appending so it can also feed transcript history")
    if "appendCurrentTranscriptLine(from: line)" not in body:
        errors.append("appendCaption must append completed output lines to full transcript history before trimming captions")
    trim_index = body.find("captions.removeFirst(captions.count - 80)")
    history_index = body.find("appendCurrentTranscriptLine(from: line)")
    if trim_index != -1 and history_index != -1 and history_index > trim_index:
        errors.append("appendCaption must record full transcript lines before trimming caption display cache")

history_match = re.search(r"private func appendCurrentTranscriptLine\(from line: CaptionLine\) \{(?P<body>[\s\S]*?)\n    \}\n\n    var subtitleLines", text)
if not history_match:
    errors.append("AppState.appendCurrentTranscriptLine(from:) not found")
else:
    body = history_match.group("body")
    for token in [
        "guard line.kind == .output else { return }",
        "currentTranscriptLines.append(TranscriptLine(",
        "text: line.text",
        "originalText: line.originalText",
        "languageCode: line.languageCode",
        "timestamp: line.timestamp",
    ]:
        if token not in body:
            errors.append(f"appendCurrentTranscriptLine must preserve transcript line data through {token}")

finish_match = re.search(r"private func finishTranscriptSession\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func deleteTranscriptSession", text)
if not finish_match:
    errors.append("AppState.finishTranscriptSession() not found")
else:
    body = finish_match.group("body")
    if "session.lines = currentTranscriptLines" not in body:
        errors.append("finishTranscriptSession must persist currentTranscriptLines instead of rebuilding from trimmed captions")
    if ".filter { $0.kind == .output }" in body and "captions" in body:
        errors.append("finishTranscriptSession must not rebuild transcript from the trimmed caption display cache")
    if "currentTranscriptLines.removeAll()" not in body:
        errors.append("finishTranscriptSession must clear full transcript history after saving")

clear_match = re.search(r"private func clearActiveTranscriptState\(\) \{(?P<body>[\s\S]*?)\n    \}", text)
if not clear_match:
    errors.append("AppState.clearActiveTranscriptState() not found")
else:
    body = clear_match.group("body")
    if "currentTranscriptLines.removeAll()" not in body:
        errors.append("clearActiveTranscriptState must clear full transcript history")

restart_match = re.search(r"private func restartTranscriptSessionIfRunning\(\) \{(?P<body>[\s\S]*?)\n    \}", text)
if not restart_match:
    errors.append("AppState.restartTranscriptSessionIfRunning() not found")
else:
    body = restart_match.group("body")
    if "currentTranscriptLines.removeAll()" not in body:
        errors.append("restartTranscriptSessionIfRunning must start with an empty full transcript history")

if errors:
    print("Transcript full history verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Transcript full history verification passed")
