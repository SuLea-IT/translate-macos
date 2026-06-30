#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
app_delegate_path = root / "LiveBuddy" / "App" / "AppDelegate.swift"
app_state = app_state_path.read_text()
app_delegate = app_delegate_path.read_text()
errors: list[str] = []

if "func stopForTermination() async" not in app_state:
    errors.append("AppState must expose stopForTermination() so quit-time stop can defer transcript persistence to the final flush")

stop_for_termination_match = re.search(
    r"func stopForTermination\(\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    private func stop",
    app_state,
)
if not stop_for_termination_match:
    errors.append("AppState.stopForTermination() not found")
else:
    body = stop_for_termination_match.group("body")
    if "await stop(cancelPendingRestart: true, saveTranscriptImmediately: false)" not in body:
        errors.append("stopForTermination() must stop runtime without immediately saving transcript sessions")

stop_match = re.search(
    r"private func stop\(cancelPendingRestart: Bool, saveTranscriptImmediately: Bool = true\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func requestStart",
    app_state,
)
if not stop_match:
    errors.append("AppState.stop(cancelPendingRestart:saveTranscriptImmediately:) not found")
else:
    body = stop_match.group("body")
    for token in [
        "finishTranscriptSession(saveImmediately: saveTranscriptImmediately)",
        "saveUsageLedger()",
        "updateLocalizedStatus(.statusStopped, level: .stopped, log: true)",
    ]:
        if token not in body:
            errors.append(f"stop(cancelPendingRestart:saveTranscriptImmediately:) must preserve stop behavior through {token}")
    if "finishTranscriptSession()" in body:
        errors.append("stop(cancelPendingRestart:saveTranscriptImmediately:) must not force immediate transcript save")

wait_match = re.search(
    r"private func waitForRuntimeStopBeforeTermination\(_ appState: AppState\) async -> TerminationStopResult \{(?P<body>[\s\S]*?)\n    \}\n\n    private func clearTerminationStopTasks",
    app_delegate,
)
if not wait_match:
    errors.append("AppDelegate.waitForRuntimeStopBeforeTermination(_:) not found")
else:
    body = wait_match.group("body")
    if "await appState?.stopForTermination()" not in body:
        errors.append("AppDelegate must use AppState.stopForTermination() during quit")
    if "await appState?.stop()" in body or "await appState.stop()" in body:
        errors.append("AppDelegate quit path must not call stop() because stop() persists transcripts before applicationWillTerminate flush")

if errors:
    print("Termination stop deferred transcript save verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Termination stop deferred transcript save verification passed")
