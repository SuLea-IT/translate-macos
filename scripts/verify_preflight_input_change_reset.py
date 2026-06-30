#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

did_set_match = re.search(r"@Published private\(set\) var settings: AppSettings \{\n        didSet \{(?P<body>[\s\S]*?)\n        \}\n    \}", text)
if not did_set_match:
    errors.append("AppState.settings didSet not found")
else:
    body = did_set_match.group("body")
    if "resetPreflightTestReportIfNeeded(oldValue: oldValue)" not in body:
        errors.append("settings didSet must reset stale preflight reports when preflight inputs change")
    reset_idx = body.find("resetPreflightTestReportIfNeeded(oldValue: oldValue)")
    refresh_idx = body.find("refreshSetupChecklistIfNeeded(oldValue: oldValue)")
    if reset_idx == -1 or refresh_idx == -1 or reset_idx > refresh_idx:
        errors.append("settings didSet should invalidate stale preflight reports before refreshing setup checklist")

helper_match = re.search(
    r"private func resetPreflightTestReportIfNeeded\(oldValue: AppSettings\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func refreshSetupChecklistIfNeeded",
    text,
)
if not helper_match:
    errors.append("AppState.resetPreflightTestReportIfNeeded(oldValue:) not found before setup checklist refresh helper")
else:
    body = helper_match.group("body")
    for token in [
        "oldValue.activeProvider != settings.activeProvider",
        "oldValue.apiKey != settings.apiKey",
        "oldValue.audioSource != settings.audioSource",
        "oldValue.selectedMicrophoneDeviceUID != settings.selectedMicrophoneDeviceUID",
        "guard preflightInputsChanged else { return }",
        "cancelPreflightTest()",
        "preflightTestReport = .idle",
    ]:
        if token not in body:
            errors.append(f"preflight input changes must invalidate stale reports through {token}")
    guard_idx = body.find("guard preflightInputsChanged else { return }")
    cancel_idx = body.find("cancelPreflightTest()", guard_idx)
    reset_idx = body.find("preflightTestReport = .idle", cancel_idx)
    if -1 in [guard_idx, cancel_idx, reset_idx] or not (guard_idx < cancel_idx < reset_idx):
        errors.append("resetPreflightTestReportIfNeeded must guard input changes, cancel in-flight preflight, then reset the report")

cancel_match = re.search(
    r"private func cancelPreflightTest\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func restoreTemporaryTestCaptionIfNeeded",
    text,
)
if not cancel_match:
    errors.append("AppState.cancelPreflightTest() not found")
else:
    body = cancel_match.group("body")
    for token in [
        "preflightTestGeneration = UUID()",
        "preflightTestTask?.cancel()",
        "temporaryTestCaptionTask?.cancel()",
        "isRunningPreflightTest = false",
    ]:
        if token not in body:
            errors.append(f"cancelPreflightTest must still stop in-flight preflight work through {token}")

if errors:
    print("Preflight input-change reset verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Preflight input-change reset verification passed")
