#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Services" / "GlossaryImportService.swift"
text = path.read_text()
errors: list[str] = []

remote_match = re.search(
    r"func importRemote\([\s\S]*?\) async throws -> GlossaryImportResult \{(?P<body>[\s\S]*?)\n    \}\n\n    private func download",
    text,
)
if not remote_match:
    errors.append("GlossaryImportService.importRemote not found")
else:
    body = remote_match.group("body")
    for token in [
        "let destination = cacheURL(for: url, sourceID: sourceName)",
        "try FileManager.default.moveItem(at: temporaryURL, to: destination)",
        "do {",
        "let result = try parser.parse(fileURL: destination, sourceName: sourceName, existingEntries: existingEntries, options: options)",
        "throw GlossaryImportError.emptyImport",
        "} catch {",
        "try? FileManager.default.removeItem(at: destination)",
        "throw error",
    ]:
        if token not in body:
            errors.append(f"importRemote must clean cached downloads when parse/empty-import fails through {token}")
    move_idx = body.find("try FileManager.default.moveItem(at: temporaryURL, to: destination)")
    do_idx = body.find("do {", move_idx)
    parse_idx = body.find("let result = try parser.parse(fileURL: destination", do_idx)
    cleanup_idx = body.find("try? FileManager.default.removeItem(at: destination)", parse_idx)
    throw_idx = body.find("throw error", cleanup_idx)
    if -1 in [move_idx, do_idx, parse_idx, cleanup_idx, throw_idx] or not (move_idx < do_idx < parse_idx < cleanup_idx < throw_idx):
        errors.append("importRemote must wrap destination parsing after move and remove destination before rethrowing parse/empty-import failures")

if errors:
    print("Glossary cache cleanup verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary cache cleanup verification passed")
