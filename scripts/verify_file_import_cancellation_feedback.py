#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
settings_path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
helper_path = root / "LiveBuddy" / "Utilities" / "FileExportCancellation.swift"
settings = settings_path.read_text()
helper = helper_path.read_text() if helper_path.exists() else ""
errors: list[str] = []

for token in [
    "func isUserCancelledFileDialog(_ error: Error) -> Bool",
    "error is CancellationError",
    "NSCocoaErrorDomain",
    "CocoaError.Code.userCancelled.rawValue",
]:
    if token not in helper:
        errors.append(f"File dialog cancellation helper must detect normal cancel paths through {token}")

match = re.search(
    r"private func handleGlossaryFileImporterResult\(_ result: Result<\[URL\], Error>\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private var preflightTestForm",
    settings,
)
if not match:
    errors.append("SettingsView.handleGlossaryFileImporterResult(_:) not found")
else:
    body = match.group("body")
    for token in [
        "case .failure(let error):",
        "isUserCancelledFileDialog(error)",
        "return",
        "glossaryImportInputMessage = error.localizedDescription",
    ]:
        if token not in body:
            errors.append(f"Glossary file importer must ignore user-cancelled picker results through {token}")
    failure_idx = body.find("case .failure(let error):")
    cancel_idx = body.find("isUserCancelledFileDialog(error)", failure_idx)
    return_idx = body.find("return", cancel_idx)
    error_idx = body.find("glossaryImportInputMessage = error.localizedDescription", return_idx)
    if -1 in [failure_idx, cancel_idx, return_idx, error_idx] or not (failure_idx < cancel_idx < return_idx < error_idx):
        errors.append("Glossary file importer must return on cancellation before publishing localizedDescription")

if errors:
    print("File import cancellation feedback verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("File import cancellation feedback verification passed")
