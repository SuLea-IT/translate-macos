#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
service_path = root / "LiveBuddy" / "Services" / "GlossaryImportService.swift"
text = service_path.read_text()
errors: list[str] = []

if "final class GlossaryImportService" not in text:
    errors.append("GlossaryImportService must remain a reference type so its URLSession lifecycle is explicit")
if "private let session: URLSession" not in text:
    errors.append("GlossaryImportService must own the URLSession it needs to release")

deinit_match = re.search(r"deinit \{(?P<body>[\s\S]*?)\n    \}\n\n    private static func makeDownloadSession", text)
if not deinit_match:
    errors.append("GlossaryImportService.deinit not found")
else:
    body = deinit_match.group("body")
    if "session.invalidateAndCancel()" not in body:
        errors.append("GlossaryImportService.deinit must invalidateAndCancel its URLSession")

if "session.finishTasksAndInvalidate()" in text:
    errors.append("GlossaryImportService must not wait for long-running downloads during deinit; use invalidateAndCancel")

if errors:
    print("Glossary session lifecycle verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary session lifecycle verification passed")
