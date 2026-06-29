#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
caption_view = root / "LiveBuddy" / "Views" / "Caption" / "CaptionView.swift"
text = caption_view.read_text()
errors: list[str] = []

if "@State private var isPlaying" in text:
    errors.append("CaptionView must not keep a local optimistic isPlaying state; it can drift after start failure")

for token in [
    "Image(systemName: appState.isRunning ? \"pause.fill\" : \"play.fill\")",
    ".help(appState.isRunning ? appState.t(.pause) : appState.t(.play))",
]:
    if token not in text:
        errors.append(f"CaptionView play control must reflect real AppState runtime through {token}")

top_controls_match = re.search(r"private var topControls: some View \{(?P<body>[\s\S]*?)\n    \}\n\n    private var closeButton", text)
if not top_controls_match:
    errors.append("CaptionView.topControls not found")
else:
    body = top_controls_match.group("body")
    if "isPlaying.toggle()" in body:
        errors.append("CaptionView play button must not optimistically toggle local UI state before runtime control completes")
    if "appState.toggle()" not in body:
        errors.append("CaptionView play button must still request runtime toggle through appState.toggle()")

for token in [
    ".onAppear {\n            isPlaying = appState.isRunning\n        }",
    ".onChange(of: appState.isRunning)",
]:
    if token in text:
        errors.append(f"CaptionView must not synchronize removed local play state through {token}")

if errors:
    print("Caption control runtime state verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Caption control runtime state verification passed")
