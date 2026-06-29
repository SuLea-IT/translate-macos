#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
service = root / "LiveBuddy" / "Services" / "GlossaryImportService.swift"
app_state = root / "LiveBuddy" / "Models" / "AppState.swift"
errors: list[str] = []

service_text = service.read_text()
app_state_text = app_state.read_text()

for token in [
    "downloadTimeout: TimeInterval = 90",
    "URLSessionConfiguration.ephemeral",
    "configuration.timeoutIntervalForRequest = downloadTimeout",
    "configuration.timeoutIntervalForResource = downloadTimeout",
    "URLSession(configuration: configuration)",
]:
    if token not in service_text:
        errors.append(f"GlossaryImportService must use an explicit bounded URLSession timeout through {token}")

for token in [
    "var temporaryURL: URL?",
    "defer {",
    "if let temporaryURL",
    "FileManager.default.removeItem(at: temporaryURL)",
    "Task.checkCancellation()",
    "error as? CancellationError",
]:
    if token not in service_text:
        errors.append(f"GlossaryImportService must cancel safely and clean partial downloads through {token}")

if "NSURLErrorCancelled" not in service_text:
    errors.append("GlossaryImportService must map URL cancellation to CancellationError")
if "NSURLErrorTimedOut" not in service_text:
    errors.append("GlossaryImportService must turn URL timeout errors into explicit download failure messages")
if "case .downloadFailed(let message)" not in app_state_text or "localized(.glossaryDownloadFailed)" not in app_state_text:
    errors.append("AppState glossary import failure handling must surface timeout/download messages instead of a generic failure only")
if "error is CancellationError" not in app_state_text:
    errors.append("AppState glossary import failure handling must ignore explicit cancellation without showing a stale error")

if errors:
    print("Glossary import resilience verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)
print("Glossary import resilience verification passed")
