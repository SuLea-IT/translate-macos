#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
text = path.read_text()
errors: list[str] = []

helper_match = re.search(r"private func clearGlossaryExportFeedback\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func prepareGlossaryExport", text)
if not helper_match:
    errors.append("SettingsView.clearGlossaryExportFeedback() must centralize stale glossary export state cleanup before prepareGlossaryExport")
else:
    body = helper_match.group("body")
    for token in [
        "glossaryExportDocument = nil",
        "glossaryExportErrorMessage = nil",
    ]:
        if token not in body:
            errors.append(f"clearGlossaryExportFeedback must reset {token}")

for name, pattern, tokens in [
    (
        "addGlossaryEntryFromUI",
        r"private func addGlossaryEntryFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func deleteGlossaryEntryFromUI",
        ["appState.addGlossaryEntry", "newGlossarySourceTerm = \"\"", "newGlossaryTargetTerm = \"\"", "clearGlossaryExportFeedback()"],
    ),
    (
        "deleteGlossaryEntryFromUI",
        r"private func deleteGlossaryEntryFromUI\(_ entry: GlossaryEntry\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func clearGlossaryEntriesFromUI",
        ["appState.deleteGlossaryEntry(entry)", "clearGlossaryExportFeedback()"],
    ),
    (
        "clearGlossaryEntriesFromUI",
        r"private func clearGlossaryEntriesFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func localizedGlossarySourceName",
        ["appState.clearGlossaryEntries()", "glossarySearchText = \"\"", "isGlossaryListExpanded = false", "clearGlossaryExportFeedback()"],
    ),
    (
        "importSelectedGlossarySource",
        r"private func importSelectedGlossarySource\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func handleGlossaryFileImporterResult",
        ["glossaryImportInputMessage = \"\"", "appState.clearGlossaryImportFeedback()", "clearGlossaryExportFeedback()"],
    ),
    (
        "handleGlossaryFileImporterResult",
        r"private func handleGlossaryFileImporterResult\(_ result: Result<\[URL\], Error>\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private var preflightTestForm",
        ["glossaryImportInputMessage = \"\"", "appState.clearGlossaryImportFeedback()", "clearGlossaryExportFeedback()"],
    ),
]:
    match = re.search(pattern, text)
    if not match:
        errors.append(f"SettingsView.{name} not found")
        continue
    body = match.group("body")
    for token in tokens:
        if token not in body:
            errors.append(f"SettingsView.{name} must clear stale glossary export feedback through {token}")

if "Button(appState.t(.addTerm)) {\n                    addGlossaryEntryFromUI()\n                }" not in text:
    errors.append("Add term button must route through addGlossaryEntryFromUI()")
if "deleteGlossaryEntryFromUI(entry)" not in text:
    errors.append("Per-term delete button must route through deleteGlossaryEntryFromUI(entry)")
if "appState.deleteGlossaryEntry(entry)" in re.sub(r"private func deleteGlossaryEntryFromUI[\s\S]*?\n    \}\n", "", text):
    errors.append("Glossary row actions must not bypass deleteGlossaryEntryFromUI")

if errors:
    print("Glossary export feedback reset verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary export feedback reset verification passed")
