#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Services" / "GlossaryImportService.swift"
text = path.read_text()
errors: list[str] = []

import_match = re.search(
    r"func importRemote\([\s\S]*?\) async throws -> GlossaryImportResult \{(?P<body>[\s\S]*?)\n    \}\n\n    private func download",
    text,
)
if not import_match:
    errors.append("GlossaryImportService.importRemote not found")
else:
    body = import_match.group("body")
    if "if let httpResponse = response as? HTTPURLResponse" in body:
        errors.append("importRemote must not handle HTTP failures after switching progress to processing; download() should throw them before returning")
    if "GlossaryImportProgress(fractionCompleted: 1).switchingToProcessing()" not in body:
        errors.append("importRemote should still switch to processing after a successful download")

download_match = re.search(
    r"private func download\([\s\S]*?\) async throws -> \(URL, URLResponse\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func shouldReportProgress",
    text,
)
if not download_match:
    errors.append("GlossaryImportService.download(...) not found")
else:
    body = download_match.group("body")
    for token in [
        "if let httpResponse = response as? HTTPURLResponse, !(200..<300).contains(httpResponse.statusCode) {",
        "throw GlossaryImportError.downloadFailed(\"HTTP \\(httpResponse.statusCode)\")",
    ]:
        if token not in body:
            errors.append(f"download must short-circuit HTTP failures through {token}")
    if "return (FileManager.default.temporaryDirectory, httpResponse)" in body:
        errors.append("download must not return temporaryDirectory as a fake downloaded file for HTTP failures")

if errors:
    print("Glossary HTTP error short-circuit verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary HTTP error short-circuit verification passed")
