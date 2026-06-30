#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

if "private static let maxDisplayedCaptionLines" not in text:
    errors.append("AppState must bound live caption UI memory through maxDisplayedCaptionLines")
if "@discardableResult\n    private func appendDisplayedCaption" not in text:
    errors.append("appendDisplayedCaption(_:) must be @discardableResult so call sites stay warning-free")

helper_match = re.search(
    r"private func appendDisplayedCaption\(_ line: CaptionLine\) -> CaptionLine \{(?P<body>[\s\S]*?)\n    \}",
    text,
)
if not helper_match:
    errors.append("AppState must append visible captions through appendDisplayedCaption(_:) so trimming is centralized")
else:
    body = helper_match.group("body")
    for token in [
        "captions.append(line)",
        "trimDisplayedCaptions()",
        "return line",
    ]:
        if token not in body:
            errors.append(f"appendDisplayedCaption(_:) must include {token}")

trim_match = re.search(
    r"private func trimDisplayedCaptions\(\) \{(?P<body>[\s\S]*?)\n    \}",
    text,
)
if not trim_match:
    errors.append("AppState must provide trimDisplayedCaptions()")
else:
    body = trim_match.group("body")
    for token in [
        "captions.count > Self.maxDisplayedCaptionLines",
        "captions.removeFirst(captions.count - Self.maxDisplayedCaptionLines)",
    ]:
        if token not in body:
            errors.append(f"trimDisplayedCaptions() must drop oldest visible captions through {token}")

append_caption_match = re.search(
    r"private func appendCaption\(_ text: String, language: String\?, kind: CaptionKind\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func appendCurrentTranscriptLine",
    text,
)
if not append_caption_match:
    errors.append("AppState.appendCaption(_:language:kind:) not found")
else:
    body = append_caption_match.group("body")
    if "appendDisplayedCaption(line)" not in body:
        errors.append("appendCaption must use appendDisplayedCaption(line) before transcript persistence")
    if "captions.append(line)" in body:
        errors.append("appendCaption must not append directly to captions without trimming")
    if "appendCurrentTranscriptLine(from: line)" not in body:
        errors.append("appendCaption must continue to persist every completed line into the transcript history")

finish_match = re.search(
    r"private func finishTranscriptSession\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func deleteTranscriptSession",
    text,
)
if not finish_match:
    errors.append("AppState.finishTranscriptSession() not found")
else:
    body = finish_match.group("body")
    if "appendDisplayedCaption(line)" not in body:
        errors.append("finishTranscriptSession must use appendDisplayedCaption(line) when flushing the final draft")
    if "captions.append(CaptionLine(" in body:
        errors.append("finishTranscriptSession must not append final draft directly without trimming")
    if "appendCurrentTranscriptLine(from: line)" not in body:
        errors.append("finishTranscriptSession must continue to persist the final draft into the transcript history")

raw_appends = [
    (idx + 1, line.strip())
    for idx, line in enumerate(text.splitlines())
    if "captions.append(" in line and "captions.append(line)" not in line
]
if raw_appends:
    formatted = ", ".join(f"line {line_no}: {line}" for line_no, line in raw_appends[:5])
    errors.append(f"Visible captions must not be appended outside appendDisplayedCaption(_:): {formatted}")

if errors:
    print("Live caption display bounds verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Live caption display bounds verification passed")
