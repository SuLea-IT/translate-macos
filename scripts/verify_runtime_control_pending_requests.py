#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = app_state_path.read_text()
errors: list[str] = []

for token in [
    "private var runtimeControlTask: Task<Void, Never>?",
    "private var pendingRuntimeControlRequest: RuntimeControlRequest?",
    "private func performRuntimeControl(_ request: RuntimeControlRequest) async",
]:
    if token not in text:
        errors.append(f"AppState runtime controls must preserve busy-time requests through {token}")

schedule_match = re.search(r"private func scheduleRuntimeControl\(_ request: RuntimeControlRequest\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func performRuntimeControl", text)
if not schedule_match:
    errors.append("AppState.scheduleRuntimeControl(_:) not found")
else:
    body = schedule_match.group("body")
    if "guard runtimeControlTask == nil else { return }" in body:
        errors.append("scheduleRuntimeControl must not drop user requests while a runtime control task is already running")
    for token in [
        "if runtimeControlTask != nil",
        "pendingRuntimeControlRequest = request",
        "return",
        "var currentRequest = request",
        "runtimeControlTask = Task",
        "await self.performRuntimeControl(currentRequest)",
        "while let pendingRequest = self.pendingRuntimeControlRequest",
        "self.pendingRuntimeControlRequest = nil",
        "currentRequest = pendingRequest",
        "self.runtimeControlTask = nil",
    ]:
        if token not in body:
            errors.append(f"scheduleRuntimeControl must queue and drain pending runtime requests through {token}")

perform_match = re.search(r"private func performRuntimeControl\(_ request: RuntimeControlRequest\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func binding", text)
if not perform_match:
    errors.append("AppState.performRuntimeControl(_:) not found")
else:
    body = perform_match.group("body")
    for token in ["case .toggle", "case .start", "case .stop", "await stop()", "await start()"]:
        if token not in body:
            errors.append(f"performRuntimeControl must keep start/stop/toggle behavior through {token}")

deinit_match = re.search(r"deinit \{(?P<body>[\s\S]*?)\n    \}\n\}", text)
if not deinit_match:
    errors.append("AppState.deinit not found")
else:
    body = deinit_match.group("body")
    if "pendingRuntimeControlRequest = nil" not in body:
        errors.append("AppState.deinit must clear any pending runtime control request")

if errors:
    print("Runtime control pending request verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Runtime control pending request verification passed")
