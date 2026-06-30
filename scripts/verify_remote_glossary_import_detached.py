#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

match = re.search(
    r"func importGlossary\(from url: URL, sourceName: String, importLimit: Int\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func importGlossary\(fromLocalFile",
    text,
)
if not match:
    errors.append("AppState.importGlossary(from:sourceName:importLimit:) not found")
else:
    body = match.group("body")
    for token in [
        "let service = glossaryImportService",
        "let existingEntries = settings.glossaryEntries",
        "let options = glossaryImportOptions(importLimit: importLimit)",
        "let importTask = Task.detached(priority: .userInitiated)",
        "try await service.importRemote(",
        "progress: { @MainActor [weak self] progress in",
        "try await withTaskCancellationHandler",
        "try await importTask.value",
        "importTask.cancel()",
    ]:
        if token not in body:
            errors.append(f"Remote glossary import must run download+parse off MainActor with cancellation propagation through {token}")

    direct_call_index = body.find("let result = try await glossaryImportService.importRemote(")
    detached_index = body.find("let importTask = Task.detached(priority: .userInitiated)")
    if direct_call_index != -1:
        errors.append("Remote glossary import must not await glossaryImportService.importRemote directly on MainActor")
    if detached_index != -1:
        result_index = body.find("let result = try await withTaskCancellationHandler", detached_index)
        apply_index = body.find("applyGlossaryImportResult(result)")
        if min(result_index, apply_index) == -1 or not (detached_index < result_index < apply_index):
            errors.append("Remote glossary import must await the detached task result before applying it on MainActor")

local_match = re.search(
    r"func importGlossary\(fromLocalFile url: URL, sourceName: String, importLimit: Int\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    private func glossaryImportOptions",
    text,
)
if not local_match or "Task.detached(priority: .userInitiated)" not in local_match.group("body"):
    errors.append("Local glossary import should remain detached as the reference pattern")

if errors:
    print("Remote glossary import detached verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Remote glossary import detached verification passed")
