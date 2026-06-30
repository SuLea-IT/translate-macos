#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

start_match = re.search(r"func start\(\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func stop", text)
if not start_match:
    errors.append("AppState.start() not found")
else:
    body = start_match.group("body")
    cancel_idx = body.find("cancelPreflightTest()")
    reset_idx = body.find("preflightTestReport = .idle", cancel_idx)
    preflight_idx = body.find("let preflight = await runStartPreflight()")
    if -1 in [cancel_idx, reset_idx, preflight_idx] or not (cancel_idx < reset_idx < preflight_idx):
        errors.append("AppState.start() must reset visible preflight rows to idle immediately after canceling a running diagnostics test")

stop_match = re.search(r"private func stop\(cancelPendingRestart: Bool, saveTranscriptImmediately: Bool = true\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func requestStart", text)
if not stop_match:
    errors.append("AppState.stop(cancelPendingRestart:saveTranscriptImmediately:) not found")
else:
    body = stop_match.group("body")
    cancel_idx = body.find("cancelPreflightTest()")
    reset_idx = body.find("preflightTestReport = .idle", cancel_idx)
    reset_pipeline_idx = body.find("resetAudioSendPipeline()")
    if -1 in [cancel_idx, reset_idx, reset_pipeline_idx] or not (cancel_idx < reset_idx < reset_pipeline_idx):
        errors.append("AppState.stop() must reset visible preflight rows to idle when runtime shutdown cancels diagnostics")

if errors:
    print("Preflight runtime cancel report reset verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Preflight runtime cancel report reset verification passed")
