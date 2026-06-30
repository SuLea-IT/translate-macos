#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state = (root / "LiveBuddy" / "Models" / "AppState.swift").read_text()
errors: list[str] = []

match = re.search(
    r"private func refreshStatusMessageLanguageIfNeeded\(oldValue: AppSettings\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func updateStatus",
    app_state,
)
if not match:
    errors.append("refreshStatusMessageLanguageIfNeeded(oldValue:) not found")
else:
    body = match.group("body")
    expected = "if isRunning && (statusLevel == .running || statusLevel == .connecting) {"
    if expected not in body:
        errors.append(f"language switching must only use runningUsageStatusMessage while runtime is active through: {expected}")
    stale = "if isRunning, statusLevel == .running || statusLevel == .connecting {"
    if stale in body:
        errors.append("language switching must not rely on comma/|| precedence for running status refresh")
    if "statusMessage = localizedStatus(localizedStatusKey)" not in body:
        errors.append("non-running localized statuses must refresh to the localized status key directly")

if errors:
    print("Language switch connecting status guard verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Language switch connecting status guard verification passed")
