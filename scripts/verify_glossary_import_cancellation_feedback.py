#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
interface = (root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift").read_text()
app_state = (root / "LiveBuddy" / "Models" / "AppState.swift").read_text()
errors: list[str] = []

for token in ["case glossaryImportCanceled", ".glossaryImportCanceled:"]:
    if token not in interface:
        errors.append(f"InterfaceLanguage must define localized glossary import cancellation feedback through {token}")
if interface.count(".glossaryImportCanceled:") < 8:
    errors.append("InterfaceText.glossaryImportCanceled must be translated for every supported language")

cancel_match = re.search(r"func cancelGlossaryImport\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func importGlossary", app_state)
if not cancel_match:
    errors.append("AppState.cancelGlossaryImport() not found")
else:
    body = cancel_match.group("body")
    required = [
        "glossaryImportGeneration = UUID()",
        "glossaryImportTask?.cancel()",
        "glossaryImportTask = nil",
        "isImportingGlossary = false",
        "glossaryImportProgress = nil",
        "glossaryImportMessage = settings.interfaceLanguage.localized(.glossaryImportCanceled)",
        "updateStatus(glossaryImportMessage, level: isRunning ? .running : .stopped, log: true)",
    ]
    for token in required:
        if token not in body:
            errors.append(f"cancelGlossaryImport() must close cancellation feedback through {token}")
    if "clearGlossaryImportFeedback()" in body and body.find("clearGlossaryImportFeedback()") > body.find("glossaryImportMessage = settings.interfaceLanguage.localized(.glossaryImportCanceled)"):
        errors.append("cancelGlossaryImport() must not clear the localized cancellation message after setting it")
    cancel_idx = body.find("glossaryImportTask?.cancel()")
    progress_idx = body.find("glossaryImportProgress = nil")
    message_idx = body.find("glossaryImportMessage = settings.interfaceLanguage.localized(.glossaryImportCanceled)")
    status_idx = body.find("updateStatus(glossaryImportMessage, level: isRunning ? .running : .stopped, log: true)")
    if -1 not in [cancel_idx, progress_idx, message_idx, status_idx] and not (cancel_idx < progress_idx < message_idx < status_idx):
        errors.append("cancelGlossaryImport() must cancel work, hide progress, then publish cancellation status")

failure_match = re.search(
    r"private func handleGlossaryImportFailure\(_ error: Error\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func configureGlobalShortcuts",
    app_state,
)
if not failure_match:
    errors.append("AppState.handleGlossaryImportFailure(_:) not found")
else:
    body = failure_match.group("body")
    if 'if error is CancellationError {\n            glossaryImportMessage = ""' in body:
        errors.append("CancellationError handling must not silently clear glossary import feedback")

if errors:
    print("Glossary import cancellation feedback verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary import cancellation feedback verification passed")
