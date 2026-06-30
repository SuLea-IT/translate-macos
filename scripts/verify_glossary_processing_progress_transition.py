#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
service_path = root / "LiveBuddy" / "Services" / "GlossaryImportService.swift"
service = service_path.read_text()
errors: list[str] = []

match = re.search(
    r"func importRemote\((?P<body>[\s\S]*?)\n    \}\n\n    private func download",
    service,
)
if not match:
    errors.append("GlossaryImportService.importRemote(...) not found")
else:
    body = match.group("body")
    download_idx = body.find("let (temporaryURL, _) = try await download(url: url, progress: progress)")
    processing_idx = body.find("await progress?(GlossaryImportProgress(fractionCompleted: 1).switchingToProcessing())")
    http_idx = body.find("if let httpResponse = response as? HTTPURLResponse")
    size_idx = body.find("try enforceFileSizeLimit(temporaryURL)")
    move_idx = body.find("try FileManager.default.moveItem(at: temporaryURL, to: destination)")
    parse_idx = body.find("let result = try parser.parse")
    for name, idx in [
        ("download", download_idx),
        ("processing progress", processing_idx),
        ("file size check", size_idx),
        ("cache move", move_idx),
        ("parse", parse_idx),
    ]:
        if idx == -1:
            errors.append(f"importRemote missing {name} step")
    if http_idx != -1:
        errors.append("importRemote must not handle HTTP failures after processing starts; download() should throw HTTP failures before returning")
    if -1 not in [download_idx, processing_idx, size_idx, move_idx, parse_idx]:
        if not (download_idx < processing_idx < size_idx < move_idx < parse_idx):
            errors.append("Remote glossary import must switch progress to processing only after a successful download, then validate file/cache/parse work")

if errors:
    print("Glossary processing progress transition verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Glossary processing progress transition verification passed")
