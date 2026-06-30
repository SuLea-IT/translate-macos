#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
text = path.read_text()
errors: list[str] = []

helper_match = re.search(
    r"private func clearGlossaryImportSelectionFeedback\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func clearGlossaryExportFeedback",
    text,
)
if not helper_match:
    errors.append("SettingsView.clearGlossaryImportSelectionFeedback() must centralize stale import form feedback cleanup before export feedback cleanup")
else:
    body = helper_match.group("body")
    for token in [
        "glossaryImportInputMessage = \"\"",
        "appState.clearGlossaryImportFeedback()",
    ]:
        if token not in body:
            errors.append(f"clearGlossaryImportSelectionFeedback must clear stale import feedback through {token}")
    if "cancelGlossaryImport" in body or "glossaryImportProgress" in body:
        errors.append("Editing import form inputs must not cancel active import work or directly mutate progress")

section_match = re.search(
    r"private var glossaryImportSection: some View \{(?P<body>[\s\S]*?)\n    \}\n\n    private var glossaryEntriesSection",
    text,
)
if not section_match:
    errors.append("SettingsView.glossaryImportSection not found")
else:
    body = section_match.group("body")
    for field in ["selectedGlossaryImportSourceID", "glossaryImportURLString", "glossaryImportLimit"]:
        pattern = rf"\.onChange\(of: {field}\) \{{ _, _ in\s+clearGlossaryImportSelectionFeedback\(\)\s+\}}"
        if not re.search(pattern, body):
            errors.append(f"glossaryImportSection must clear stale import feedback when {field} changes")
    if body.count("clearGlossaryImportSelectionFeedback()") < 3:
        errors.append("glossaryImportSection must wire feedback reset to source, URL, and limit input changes")

if errors:
    print("Glossary import input-change feedback reset verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary import input-change feedback reset verification passed")
