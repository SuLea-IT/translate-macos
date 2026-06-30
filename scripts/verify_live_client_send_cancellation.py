#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Services" / "GeminiLiveTranslateClient.swift"
text = path.read_text()
errors: list[str] = []

match = re.search(r"func sendAudio\(_ data: Data\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func close", text)
if not match:
    errors.append("GeminiLiveTranslateClient.sendAudio(_:) not found")
else:
    body = match.group("body")
    for token in [
        "catch is CancellationError",
        "Task.isCancelled",
        "NSURLErrorDomain",
        "NSURLErrorCancelled",
        "return",
        "report(.sendFailed(error.localizedDescription))",
    ]:
        if token not in body:
            errors.append(f"sendAudio(_:) must suppress cancellation without reporting sendFailed through {token}")

    cancellation_catch_index = body.find("catch is CancellationError")
    ns_error_index = body.find("let nsError = error as NSError")
    report_index = body.find("report(.sendFailed(error.localizedDescription))")
    if -1 in [cancellation_catch_index, ns_error_index, report_index]:
        errors.append("sendAudio(_:) cancellation suppression structure is incomplete")
    elif not (cancellation_catch_index < ns_error_index < report_index):
        errors.append("sendAudio(_:) must handle Swift/URLSession cancellation before reporting send failures")

if errors:
    print("Live client send cancellation verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Live client send cancellation verification passed")
