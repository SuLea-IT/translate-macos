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
        "let (temporaryURL, response) = try await download(url: url, progress: progress)",
        "var downloadedURL: URL? = temporaryURL",
        "defer {",
        "if let downloadedURL {",
        "try? FileManager.default.removeItem(at: downloadedURL)",
        "downloadedURL = nil",
        "try enforceFileSizeLimit(temporaryURL)",
        "try FileManager.default.moveItem(at: temporaryURL, to: destination)",
    ]:
        if token not in body:
            errors.append(f"importRemote must clean downloaded temp files on post-download failures through {token}")

    response_check_idx = body.find("if let httpResponse = response as? HTTPURLResponse")
    temp_guard_idx = body.find("var downloadedURL: URL? = temporaryURL", response_check_idx)
    defer_idx = body.find("defer {", temp_guard_idx)
    size_idx = body.find("try enforceFileSizeLimit(temporaryURL)", defer_idx)
    move_idx = body.find("try FileManager.default.moveItem(at: temporaryURL, to: destination)", size_idx)
    clear_idx = body.find("downloadedURL = nil", move_idx)
    parse_idx = body.find("let result = try parser.parse", clear_idx)
    if -1 in [response_check_idx, temp_guard_idx, defer_idx, size_idx, move_idx, clear_idx, parse_idx] or not (response_check_idx < temp_guard_idx < defer_idx < size_idx < move_idx < clear_idx < parse_idx):
        errors.append("importRemote must install temp cleanup after HTTP status validation, keep it active through file-size/move failures, and clear it only after a successful move")

    if body.find("var downloadedURL: URL? = temporaryURL") < body.find("if let httpResponse = response as? HTTPURLResponse"):
        errors.append("importRemote must not register the HTTP error placeholder URL as a downloaded temp file")

download_match = re.search(r"private func download\([\s\S]*?\) async throws -> \(URL, URLResponse\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func shouldReportProgress", text)
if not download_match:
    errors.append("GlossaryImportService.download not found")
else:
    body = download_match.group("body")
    for token in [
        "var temporaryURL: URL?",
        "temporaryURL = downloadURL",
        "temporaryURL = nil",
        "if let temporaryURL {",
        "try? FileManager.default.removeItem(at: temporaryURL)",
    ]:
        if token not in body:
            errors.append(f"download must keep cleaning partial files created during the byte stream through {token}")

if errors:
    print("Glossary remote temp cleanup verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary remote temp cleanup verification passed")
