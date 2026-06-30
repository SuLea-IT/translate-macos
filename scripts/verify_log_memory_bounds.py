#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = app_state_path.read_text()
errors: list[str] = []

for token in [
    "private static let maxLogEntries = 400",
    "private static let maxLogMessageCharacters = 2_000",
    "private static let truncatedLogSuffix",
    "private static func boundedLogMessage(_ message: String) -> String",
]:
    if token not in text:
        errors.append(f"AppState must define log memory bound through {token}")

match = re.search(r"private func appendLog\(_ message: String, level: LogLevel\) \{(?P<body>[\s\S]*?)\n    \}\n\n    // MARK: - Transcript Sessions", text)
if not match:
    errors.append("AppState.appendLog(_:level:) not found")
else:
    body = match.group("body")
    for token in [
        "let boundedMessage = Self.boundedLogMessage(message)",
        "guard !boundedMessage.isEmpty else { return }",
        "logs.append(LogEntry(message: boundedMessage, level: level))",
        "if logs.count > Self.maxLogEntries",
        "logs.removeFirst(logs.count - Self.maxLogEntries)",
    ]:
        if token not in body:
            errors.append(f"appendLog must enforce bounded entries/messages through {token}")
    for old in [
        "logs.append(LogEntry(message: trimmed, level: level))",
        "logs.count > 400",
        "logs.count - 400",
    ]:
        if old in body:
            errors.append(f"appendLog must not keep unbounded/magic log handling {old}")

bounded_match = re.search(r"private static func boundedLogMessage\(_ message: String\) -> String \{(?P<body>[\s\S]*?)\n    \}\n\n    private func appendLog", text)
if not bounded_match:
    errors.append("AppState.boundedLogMessage(_:) not found before appendLog")
else:
    body = bounded_match.group("body")
    for token in [
        "trimmingCharacters(in: .whitespacesAndNewlines)",
        "trimmed.count <= maxLogMessageCharacters",
        "maxLogMessageCharacters - truncatedLogSuffix.count",
        "trimmed.prefix(keepCount)",
        "+ truncatedLogSuffix",
    ]:
        if token not in body:
            errors.append(f"boundedLogMessage must trim and truncate oversized messages through {token}")

if errors:
    print("Log memory bounds verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Log memory bounds verification passed")
