#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
text = path.read_text()
errors: list[str] = []

if "private func transcriptHasContent(_ session: TranscriptSession) -> Bool" not in text:
    errors.append("TranscriptsView must centralize empty-transcript action gating in transcriptHasContent(_:)")
else:
    helper_match = re.search(r"private func transcriptHasContent\(_ session: TranscriptSession\) -> Bool \{(?P<body>[\s\S]*?)\n    \}\n\n    private func reconcileSelectedSession", text)
    if not helper_match:
        errors.append("transcriptHasContent(_:) should live near transcript detail helpers before reconcileSelectedSession")
    elif "!session.lines.isEmpty" not in helper_match.group("body"):
        errors.append("transcriptHasContent(_:) must require at least one captured transcript line")

detail_match = re.search(r"private func detailContent\(_ session: TranscriptSession\) -> some View \{(?P<body>[\s\S]*?)\n    \}\n\n    private func transcriptHasContent", text)
if not detail_match:
    errors.append("TranscriptsView.detailContent(_:) not found before transcriptHasContent helper")
else:
    body = detail_match.group("body")
    if "let hasTranscriptContent = transcriptHasContent(session)" not in body:
        errors.append("detailContent must compute hasTranscriptContent once for action gating")
    for label, token in [
        ("copy all", "Label(appState.t(.copyAll), systemImage: \"doc.on.doc\")"),
        ("share", "Label(appState.t(.share), systemImage: \"square.and.arrow.up\")"),
        ("export", "Label(appState.t(.exportTranscript), systemImage: \"square.and.arrow.down\")"),
    ]:
        idx = body.find(token)
        if idx == -1:
            errors.append(f"{label} action label not found")
            continue
        disabled_idx = body.find(".disabled(!hasTranscriptContent)", idx)
        if disabled_idx == -1:
            errors.append(f"{label} action must be disabled when the selected transcript has no captured lines")

context_match = re.search(r"\.contextMenu \{(?P<body>[\s\S]*?)\n                        \}\n", text)
if not context_match:
    errors.append("Transcript session context menu not found")
else:
    body = context_match.group("body")
    copy_idx = body.find("Button(appState.t(.copyTranscript))")
    disabled_idx = body.find(".disabled(!transcriptHasContent(session))", copy_idx)
    if copy_idx == -1 or disabled_idx == -1:
        errors.append("Transcript list context-menu copy action must be disabled for empty sessions")

if errors:
    print("Transcript empty actions disabled verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Transcript empty actions disabled verification passed")
