#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
settings_view_path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
app_state = app_state_path.read_text()
settings_view = settings_view_path.read_text()
errors: list[str] = []

if "func clearGlossaryImportFeedback()" not in app_state:
    errors.append("AppState must expose clearGlossaryImportFeedback() so the UI can clear stale import result messages before new attempts")
else:
    clear_match = re.search(r"func clearGlossaryImportFeedback\(\) \{(?P<body>[\s\S]*?)\n    \}", app_state)
    body = clear_match.group("body") if clear_match else ""
    if "glossaryImportMessage = \"\"" not in body:
        errors.append("clearGlossaryImportFeedback() must clear glossaryImportMessage")

for name, pattern in [
    ("startGlossaryImport", r"func startGlossaryImport\(from url: URL, sourceName: String, importLimit: Int\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("startGlossaryImportFromLocalFile", r"func startGlossaryImportFromLocalFile\(url: URL, sourceName: String, importLimit: Int\) \{(?P<body>[\s\S]*?)\n    \}"),
]:
    match = re.search(pattern, app_state)
    if not match:
        errors.append(f"AppState.{name} not found")
        continue
    body = match.group("body")
    if "clearGlossaryImportFeedback()" not in body:
        errors.append(f"AppState.{name} must clear stale import feedback through clearGlossaryImportFeedback()")

cancel_match = re.search(r"func cancelGlossaryImport\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func importGlossary", app_state)
if not cancel_match:
    errors.append("AppState.cancelGlossaryImport not found")
else:
    body = cancel_match.group("body")
    if "glossaryImportMessage = settings.interfaceLanguage.localized(.glossaryImportCanceled)" not in body:
        errors.append("AppState.cancelGlossaryImport must replace stale import feedback with localized cancellation feedback")

import_selected_match = re.search(r"private func importSelectedGlossarySource\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func handleGlossaryFileImporterResult", settings_view)
if not import_selected_match:
    errors.append("SettingsView.importSelectedGlossarySource() not found")
else:
    body = import_selected_match.group("body")
    for token in [
        "glossaryImportInputMessage = \"\"",
        "appState.clearGlossaryImportFeedback()",
        "glossaryImportInputMessage = appState.t(.httpsLinksOnly)",
    ]:
        if token not in body:
            errors.append(f"importSelectedGlossarySource() must reset stale feedback and still show validation errors through {token}")
    clear_idx = body.find("appState.clearGlossaryImportFeedback()")
    validation_idx = body.find("glossaryImportInputMessage = appState.t(.httpsLinksOnly)")
    if -1 not in (clear_idx, validation_idx) and not (clear_idx < validation_idx):
        errors.append("importSelectedGlossarySource() must clear stale app-level feedback before publishing URL validation errors")

file_result_match = re.search(r"private func handleGlossaryFileImporterResult\(_ result: Result<\[URL\], Error>\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private var preflightTestForm", settings_view)
if not file_result_match:
    errors.append("SettingsView.handleGlossaryFileImporterResult(_:) not found")
else:
    body = file_result_match.group("body")
    for token in [
        "glossaryImportInputMessage = \"\"",
        "appState.clearGlossaryImportFeedback()",
        "glossaryImportInputMessage = error.localizedDescription",
    ]:
        if token not in body:
            errors.append(f"handleGlossaryFileImporterResult(_:) must reset stale feedback and show picker errors through {token}")
    clear_idx = body.find("appState.clearGlossaryImportFeedback()")
    error_idx = body.find("glossaryImportInputMessage = error.localizedDescription")
    if -1 not in (clear_idx, error_idx) and not (clear_idx < error_idx):
        errors.append("handleGlossaryFileImporterResult(_:) must clear stale app-level feedback before publishing picker errors")

if errors:
    print("Glossary import feedback reset verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary import feedback reset verification passed")
