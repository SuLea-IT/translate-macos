#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
settings_path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
text = settings_path.read_text()
errors: list[str] = []

helper = re.search(
    r"private func resetGlossaryListViewForImport\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func importSelectedGlossarySource",
    text,
)
if not helper:
    errors.append("SettingsView must define resetGlossaryListViewForImport() before importSelectedGlossarySource()")
else:
    body = helper.group("body")
    for token in [
        "glossarySearchText = \"\"",
        "isGlossaryListExpanded = false",
    ]:
        if token not in body:
            errors.append(f"resetGlossaryListViewForImport must clear stale list filters/expansion through {token}")

import_selected = re.search(
    r"private func importSelectedGlossarySource\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func handleGlossaryFileImporterResult",
    text,
)
if not import_selected:
    errors.append("SettingsView.importSelectedGlossarySource() not found")
else:
    body = import_selected.group("body")
    if body.count("resetGlossaryListViewForImport()") < 2:
        errors.append("Remote glossary imports must reset the list view for both built-in and validated custom URL sources")
    for start_token in [
        "appState.startGlossaryImport(from: url, sourceName: localizedGlossarySourceName(source), importLimit: glossaryImportLimit)",
    ]:
        search_from = 0
        while True:
            start_idx = body.find(start_token, search_from)
            if start_idx == -1:
                break
            reset_idx = body.rfind("resetGlossaryListViewForImport()", 0, start_idx)
            if reset_idx == -1:
                errors.append("importSelectedGlossarySource must reset list view before each remote import start")
                break
            search_from = start_idx + len(start_token)
    validation_idx = body.find("guard let url = GlossaryImportURLValidator.remoteURL")
    validation_error_idx = body.find("glossaryImportInputMessage = appState.t(.httpsLinksOnly)", validation_idx)
    custom_reset_idx = body.find("resetGlossaryListViewForImport()", validation_error_idx)
    custom_start_idx = body.find("appState.startGlossaryImport(from: url", custom_reset_idx)
    if -1 in [validation_idx, validation_error_idx, custom_reset_idx, custom_start_idx] or not (validation_idx < validation_error_idx < custom_reset_idx < custom_start_idx):
        errors.append("Custom URL import must reset list view only after URL validation succeeds and before starting import")

file_result = re.search(
    r"private func handleGlossaryFileImporterResult\(_ result: Result<\[URL\], Error>\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private var preflightTestForm",
    text,
)
if not file_result:
    errors.append("SettingsView.handleGlossaryFileImporterResult(_:) not found")
else:
    body = file_result.group("body")
    for token in [
        "guard let url = urls.first else { return }",
        "resetGlossaryListViewForImport()",
        "appState.startGlossaryImportFromLocalFile(url: url, sourceName: url.lastPathComponent, importLimit: glossaryImportLimit)",
    ]:
        if token not in body:
            errors.append(f"Local glossary file imports must reset list view after a file is selected through {token}")
    guard_idx = body.find("guard let url = urls.first else { return }")
    reset_idx = body.find("resetGlossaryListViewForImport()", guard_idx)
    start_idx = body.find("appState.startGlossaryImportFromLocalFile", reset_idx)
    failure_idx = body.find("case .failure")
    if -1 in [guard_idx, reset_idx, start_idx, failure_idx] or not (guard_idx < reset_idx < start_idx < failure_idx):
        errors.append("Local file import must reset list view after file selection, before import start, and never on picker cancellation")

if errors:
    print("Glossary import list-view reset verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Glossary import list-view reset verification passed")
