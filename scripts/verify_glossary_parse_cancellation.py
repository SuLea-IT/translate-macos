#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
parser_path = root / "LiveBuddy" / "Models" / "GlossaryImport.swift"
service_path = root / "LiveBuddy" / "Services" / "GlossaryImportService.swift"
parser_text = parser_path.read_text()
service_text = service_path.read_text()
errors = []

for token in [
    "let data = try Data(contentsOf: fileURL)",
    "try Task.checkCancellation()",
    "candidates = try parseTSV(data: data)",
    "candidates = try parseCSV(data: data)",
    "return try buildResult(",
]:
    if token not in parser_text:
        errors.append(f"GlossaryImportParser must propagate cancellation through {token}")

for signature in [
    "private func parseTSV(data: Data) throws -> [GlossaryImportCandidate]",
    "private func parseCSV(data: Data) throws -> [GlossaryImportCandidate]",
    "private func buildResult(",
    ") throws -> GlossaryImportResult",
    "func parse(_ text: String) throws -> [[String]]",
]:
    if signature not in parser_text:
        errors.append(f"Glossary parsing helpers must be throwing/cancellable through {signature}")

checks = [
    ("parseTSV", r"private func parseTSV\(data: Data\) throws -> \[GlossaryImportCandidate\] \{(?P<body>[\s\S]*?)\n    \}\n\n    private func parseCSV"),
    ("parseCSV", r"private func parseCSV\(data: Data\) throws -> \[GlossaryImportCandidate\] \{(?P<body>[\s\S]*?)\n    \}\n\n    private func parseTBX"),
    ("parseZIP", r"private func parseZIP\([\s\S]*?\) throws -> GlossaryImportResult \{(?P<body>[\s\S]*?)\n    \}\n\n    private func buildResult"),
    ("buildResult", r"private func buildResult\([\s\S]*?\) throws -> GlossaryImportResult \{(?P<body>[\s\S]*?)\n    \}\n\n    private func looksLikeXML"),
    ("CSVRowParser.parse", r"func parse\(_ text: String\) throws -> \[\[String\]\] \{(?P<body>[\s\S]*?)\n    \}\n\n    private func consumeUnquoted"),
    ("ZIPGlossaryArchive.runUnzipData", r"private func runUnzipData\(arguments: \[String\]\) throws -> Data \{(?P<body>[\s\S]*?)\n    \}\n\}")
]
for name, pattern in checks:
    match = re.search(pattern, parser_text)
    if not match:
        errors.append(f"{name} body not found for cancellation verification")
        continue
    body = match.group("body")
    if "Task.checkCancellation()" not in body:
        errors.append(f"{name} must call Task.checkCancellation() during potentially long work")

run_unzip_match = re.search(r"private func runUnzipData\(arguments: \[String\]\) throws -> Data \{(?P<body>[\s\S]*?)\n    \}\n\}", parser_text)
if run_unzip_match:
    body = run_unzip_match.group("body")
    for token in ["while process.isRunning", "process.terminate()", "throw CancellationError()", "Thread.sleep"]:
        if token not in body:
            errors.append(f"ZIP unzip subprocess must be cancellable through {token}")
    wait_index = body.find("process.waitUntilExit()")
    loop_index = body.find("while process.isRunning")
    if wait_index != -1 and (loop_index == -1 or wait_index < loop_index):
        errors.append("ZIP unzip subprocess must not block only on waitUntilExit before checking cancellation")

for token in [
    "let result = try parser.parse(fileURL: destination",
    "let result = try parser.parse(fileURL: url",
]:
    if token not in service_text:
        errors.append(f"GlossaryImportService must continue using throwing parser parse through {token}")

if errors:
    print("Glossary parse cancellation verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary parse cancellation verification passed")
