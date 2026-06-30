#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
settings_path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
transcripts_path = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
helper_path = root / "LiveBuddy" / "Utilities" / "FileExportCancellation.swift"
settings = settings_path.read_text()
transcripts = transcripts_path.read_text()
helper = helper_path.read_text() if helper_path.exists() else ""
errors: list[str] = []

for token in [
    "func isUserCancelledFileExport(_ error: Error) -> Bool",
    "error is CancellationError",
    "NSCocoaErrorDomain",
    "CocoaError.Code.userCancelled.rawValue",
]:
    if token not in helper:
        errors.append(f"File export cancellation helper must detect normal cancel paths through {token}")

checks = [
    (
        "glossary",
        settings,
        r"contentType: \.commaSeparatedText,[\s\S]*?\) \{ result in(?P<body>[\s\S]*?)\n        \}\n        \.confirmationDialog",
        "glossaryExportErrorMessage = nil",
    ),
    (
        "logs",
        settings,
        r"contentType: \.plainText,[\s\S]*?\) \{ result in(?P<body>[\s\S]*?)\n        \}\n        \.confirmationDialog",
        "logExportErrorMessage = nil",
    ),
    (
        "transcripts",
        transcripts,
        r"defaultFilename: exportFileName[\s\S]*?\) \{ result in(?P<body>[\s\S]*?)\n        \}\n        \.confirmationDialog",
        "exportErrorMessage = nil",
    ),
]

for name, text, pattern, clear_token in checks:
    match = re.search(pattern, text)
    if not match:
        errors.append(f"{name} fileExporter completion handler not found")
        continue
    body = match.group("body")
    for token in [
        "case .failure(let error):",
        "isUserCancelledFileExport(error)",
        clear_token,
        "return",
        "error.localizedDescription",
    ]:
        if token not in body:
            errors.append(f"{name} export failure handler must ignore user-cancelled exports through {token}")
    failure_idx = body.find("case .failure(let error):")
    cancel_idx = body.find("isUserCancelledFileExport(error)", failure_idx)
    clear_idx = body.find(clear_token, cancel_idx)
    return_idx = body.find("return", clear_idx)
    error_idx = body.find("error.localizedDescription", return_idx)
    if -1 in [failure_idx, cancel_idx, clear_idx, return_idx, error_idx] or not (failure_idx < cancel_idx < clear_idx < return_idx < error_idx):
        errors.append(f"{name} export cancellation must clear stale error and return before publishing localizedDescription")

if errors:
    print("File export cancellation feedback verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("File export cancellation feedback verification passed")
