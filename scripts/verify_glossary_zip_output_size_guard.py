#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "GlossaryImport.swift"
text = path.read_text()
errors: list[str] = []

archive_match = re.search(r"private struct ZIPGlossaryArchive \{(?P<body>[\s\S]*?)\n\}\n\nprivate struct ZIPGlossaryEntryPrioritizer", text)
if not archive_match:
    errors.append("ZIPGlossaryArchive not found")
else:
    archive = archive_match.group("body")
    for token in [
        "let maxEntryBytes: Int",
        "guard size <= maxEntryBytes else { return false }",
    ]:
        if token not in archive:
            errors.append(f"ZIPGlossaryArchive must keep central-directory size filtering through {token}")

    data_match = re.search(r"func data\(for entry: String\) throws -> Data \{(?P<body>[\s\S]*?)\n    \}", archive)
    if not data_match:
        errors.append("ZIPGlossaryArchive.data(for:) not found")
    else:
        body = data_match.group("body")
        for token in [
            "runUnzipData(arguments: [\"-p\", fileURL.path, entry], maxOutputBytes: maxEntryBytes)",
            "!entry.contains(\"../\")",
            "!entry.hasPrefix(\"/\")",
        ]:
            if token not in body:
                errors.append(f"ZIPGlossaryArchive.data(for:) must enforce path and real output bounds through {token}")

    signature = "private func runUnzipData(arguments: [String], maxOutputBytes: Int? = nil) throws -> Data"
    if signature not in archive:
        errors.append(f"ZIPGlossaryArchive.runUnzipData must accept an optional output size guard: {signature}")

    run_match = re.search(r"private func runUnzipData\(arguments: \[String\], maxOutputBytes: Int\? = nil\) throws -> Data \{(?P<body>[\s\S]*?)\n    \}", archive)
    if not run_match:
        errors.append("ZIPGlossaryArchive.runUnzipData(arguments:maxOutputBytes:) body not found")
    else:
        body = run_match.group("body")
        for token in [
            "let outputSize = try fileSize(at: stdoutURL)",
            "if let maxOutputBytes, outputSize > maxOutputBytes",
            "throw GlossaryImportError.fileTooLarge",
            "let output = try Data(contentsOf: stdoutURL)",
        ]:
            if token not in body:
                errors.append(f"runUnzipData must check stdout file size before loading Data through {token}")
        size_idx = body.find("let outputSize = try fileSize(at: stdoutURL)")
        data_idx = body.find("let output = try Data(contentsOf: stdoutURL)")
        if -1 not in (size_idx, data_idx) and not (size_idx < data_idx):
            errors.append("runUnzipData must check output file size before reading stdout into memory")

    helper_match = re.search(r"private func fileSize\(at url: URL\) throws -> Int \{(?P<body>[\s\S]*?)\n    \}", archive)
    if not helper_match:
        errors.append("ZIPGlossaryArchive must provide fileSize(at:) helper")
    else:
        body = helper_match.group("body")
        for token in [
            "FileManager.default.attributesOfItem(atPath: url.path)",
            "attributes[.size]",
            "NSNumber",
            "intValue",
        ]:
            if token not in body:
                errors.append(f"fileSize(at:) must use filesystem attributes through {token}")

if errors:
    print("Glossary ZIP output size guard verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary ZIP output size guard verification passed")
