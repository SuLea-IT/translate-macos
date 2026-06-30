#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
view_path = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
text = view_path.read_text()
errors: list[str] = []

match = re.search(r"private func exportAllTranscriptsFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}", text)
if not match:
    errors.append("TranscriptsView.exportAllTranscriptsFromUI() not found")
else:
    body = match.group("body")
    if "transcriptArchiveExporter.export(sessions: appState.transcriptSessions, mode: .both)" not in body:
        errors.append("Bulk transcript export must always export .both so the list-level backup is complete and not affected by the hidden detail viewMode")
    if "mode: viewMode" in body:
        errors.append("Bulk transcript export must not use the mutable detail viewMode from the selected transcript page")
    if "TranscriptExportDocument(text: archiveText" not in body:
        errors.append("Bulk transcript export must still prepare the archive export document")

if errors:
    print("Transcript bulk export mode verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)
print("Transcript bulk export mode verification passed")
