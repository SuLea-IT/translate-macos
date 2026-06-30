#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

checks = [
    (
        "startGlossaryImport",
        r"func startGlossaryImport\(from url: URL, sourceName: String, importLimit: Int\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func startGlossaryImportFromLocalFile",
        "await self?.importGlossary(from: url",
    ),
    (
        "startGlossaryImportFromLocalFile",
        r"func startGlossaryImportFromLocalFile\(url: URL, sourceName: String, importLimit: Int\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func cancelGlossaryImport",
        "await self?.importGlossary(fromLocalFile: url",
    ),
]

for name, pattern, await_token in checks:
    match = re.search(pattern, text)
    if not match:
        errors.append(f"AppState.{name} not found")
        continue
    body = match.group("body")
    for token in ["glossaryImportTask = Task", "defer", "self?.glossaryImportTask = nil", await_token]:
        if token not in body:
            errors.append(f"AppState.{name} must release its task handle with defer around the import body through {token}")
    await_index = body.find(await_token)
    defer_index = body.find("defer")
    generation_guard_index = body.find("self?.glossaryImportGeneration == generation")
    cleanup_index = body.find("self?.glossaryImportTask = nil", generation_guard_index)
    if -1 in [defer_index, await_index, generation_guard_index, cleanup_index] or not (defer_index < generation_guard_index < cleanup_index < await_index):
        errors.append(f"AppState.{name} cleanup must be registered in a generation-guarded defer before awaiting import")
    if "guard !Task.isCancelled else { return }\n            self?.glossaryImportTask = nil" in body:
        errors.append(f"AppState.{name} must not skip task-handle cleanup on cancellation")

if errors:
    print("Glossary import task cleanup verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary import task cleanup verification passed")
