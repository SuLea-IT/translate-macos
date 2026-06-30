#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
text = (root / "LiveBuddy" / "Models" / "AppState.swift").read_text()
errors: list[str] = []

match = re.search(
    r"private func finishTranscriptSession\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func deleteTranscriptSession",
    text,
)
if not match:
    errors.append("AppState.finishTranscriptSession() not found")
else:
    body = match.group("body")
    cleanup_block = '        captionDraft = ""\n        originalDraft = ""\n        completedOriginalSentences.removeAll()'
    cleanup_idx = body.find(cleanup_block)
    flush_idx = body.find("if !captionDraft.isEmpty")
    flush_end_idx = body.find("\n        }\n", flush_idx)
    session_idx = body.find("var session = transcriptSessions[index]")
    if cleanup_idx == -1:
        errors.append("finishTranscriptSession must clear captionDraft, originalDraft, and completedOriginalSentences together")
    elif flush_end_idx == -1 or not (flush_end_idx < cleanup_idx):
        errors.append("finishTranscriptSession must clear pending draft state outside the captionDraft-only flush branch")
    elif session_idx != -1 and cleanup_idx > session_idx:
        errors.append("finishTranscriptSession must clear pending draft state before persisting session")
    for token in ['captionDraft = ""', 'originalDraft = ""', "completedOriginalSentences.removeAll()"]:
        idx = body.rfind(token)
        if idx == -1:
            errors.append(f"finishTranscriptSession must clear pending draft state through {token}")
    if "currentTranscriptLines.removeAll()" not in body:
        errors.append("finishTranscriptSession must continue clearing currentTranscriptLines")

if errors:
    print("Finish transcript draft cleanup verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Finish transcript draft cleanup verification passed")
