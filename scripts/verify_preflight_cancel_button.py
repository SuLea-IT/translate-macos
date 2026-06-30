#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
settings_path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
app_state = app_state_path.read_text()
settings = settings_path.read_text()
errors: list[str] = []

cancel_match = re.search(
    r"func cancelRunningPreflightTest\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func cancelPreflightTest",
    app_state,
)
if not cancel_match:
    errors.append("AppState must expose cancelRunningPreflightTest() before the private cancellation helper")
else:
    body = cancel_match.group("body")
    for token in ["cancelPreflightTest()", "preflightTestReport = .idle"]:
        if token not in body:
            errors.append(f"cancelRunningPreflightTest() must stop work and clear stale running rows through {token}")
    cancel_idx = body.find("cancelPreflightTest()")
    reset_idx = body.find("preflightTestReport = .idle")
    if -1 in [cancel_idx, reset_idx] or not (cancel_idx < reset_idx):
        errors.append("cancelRunningPreflightTest() should cancel work before resetting the visible report")

form_match = re.search(
    r"private var preflightTestForm: some View \{(?P<body>[\s\S]*?)\n    \}\n\n    private var logsView",
    settings,
)
if not form_match:
    errors.append("SettingsView.preflightTestForm not found")
else:
    body = form_match.group("body")
    for token in [
        "Button(appState.isRunningPreflightTest ? appState.t(.cancel) : appState.t(.runTest))",
        "if appState.isRunningPreflightTest",
        "appState.cancelRunningPreflightTest()",
        "appState.startPreflightTest()",
    ]:
        if token not in body:
            errors.append(f"preflightTestForm must make the test button toggle run/cancel through {token}")
    if ".disabled(appState.isRunning || appState.isRunningPreflightTest)" in body:
        errors.append("preflight test button must remain enabled while a preflight test is running so the user can cancel it")
    if ".disabled(appState.isRunning)" not in body:
        errors.append("preflight test button should still be disabled while translation is running")
    branch_idx = body.find("if appState.isRunningPreflightTest")
    cancel_idx = body.find("appState.cancelRunningPreflightTest()", branch_idx)
    start_idx = body.find("appState.startPreflightTest()", branch_idx)
    if -1 in [branch_idx, cancel_idx, start_idx] or not (branch_idx < cancel_idx < start_idx):
        errors.append("preflight test button action should cancel the active test, otherwise start a new test")

if errors:
    print("Preflight cancel button verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Preflight cancel button verification passed")
