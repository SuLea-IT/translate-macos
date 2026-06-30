#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
text = path.read_text()
errors: list[str] = []

list_match = re.search(r"private var listView: some View \{(?P<body>[\s\S]*?)\n    \}\n\n    private var listHeader", text)
if not list_match:
    errors.append("TranscriptsView.listView not found")
else:
    list_body = list_match.group("body")
    if "transcriptListExportErrorFeedback" not in list_body:
        errors.append("Transcript list view must render export errors from bulk export/fileExporter failures")
    header_idx = list_body.find("listHeader")
    feedback_idx = list_body.find("transcriptListExportErrorFeedback")
    content_idx = min(
        idx for idx in [
            list_body.find("emptyState"),
            list_body.find("searchBar"),
        ] if idx != -1
    )
    if feedback_idx == -1 or not (header_idx < feedback_idx < content_idx):
        errors.append("Bulk transcript export error feedback should appear below the list header before list content")

feedback_match = re.search(r"private var transcriptListExportErrorFeedback: some View \{(?P<body>[\s\S]*?)\n    \}\n\n    private var searchBar", text)
if not feedback_match:
    errors.append("TranscriptsView must define transcriptListExportErrorFeedback")
else:
    body = feedback_match.group("body")
    for token in [
        "if let exportErrorMessage",
        "appState.t(.exportFailed, exportErrorMessage)",
        ".foregroundStyle(.red)",
        ".padding(.horizontal, 20)",
    ]:
        if token not in body:
            errors.append(f"Transcript list export error feedback must include {token}")

if errors:
    print("Transcript list export error feedback verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Transcript list export error feedback verification passed")
