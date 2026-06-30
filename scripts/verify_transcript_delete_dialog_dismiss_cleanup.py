#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
text = path.read_text()
errors: list[str] = []

if "@State private var pendingDeleteSession: TranscriptSession?" not in text:
    errors.append("TranscriptsView must track pendingDeleteSession for deferred destructive delete confirmation")

for token in [
    ".onChange(of: isShowingDeleteTranscriptConfirmation)",
    "if !isPresented {",
    "pendingDeleteSession = nil",
]:
    if token not in text:
        errors.append(f"Delete transcript confirmation must clear pending state after dialog dismissal through {token}")

change_match = re.search(
    r"\.onChange\(of: isShowingDeleteTranscriptConfirmation\) \{ _, isPresented in(?P<body>[\s\S]*?)\n        \}\n",
    text,
)
if not change_match:
    errors.append("TranscriptsView must observe isShowingDeleteTranscriptConfirmation dismissal")
else:
    body = change_match.group("body")
    dismiss_idx = body.find("if !isPresented {")
    clear_idx = body.find("pendingDeleteSession = nil", dismiss_idx)
    if dismiss_idx == -1 or clear_idx == -1 or dismiss_idx > clear_idx:
        errors.append("TranscriptsView must only clear pendingDeleteSession when delete dialog is dismissed")

request_match = re.search(r"private func requestDeleteTranscriptSession\(_ session: TranscriptSession\) \{(?P<body>[\s\S]*?)\n    \}", text)
if not request_match:
    errors.append("requestDeleteTranscriptSession(_:) not found")
else:
    body = request_match.group("body")
    for token in ["pendingDeleteSession = session", "isShowingDeleteTranscriptConfirmation = true"]:
        if token not in body:
            errors.append(f"requestDeleteTranscriptSession must still arm dialog through {token}")

if errors:
    print("Transcript delete dialog dismissal cleanup verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Transcript delete dialog dismissal cleanup verification passed")
