#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

if "private var preflightTestGeneration = UUID()" not in text:
    errors.append("AppState must track a preflightTestGeneration to isolate old cancelled tests from new ones")

run_match = re.search(r"func runPreflightTest\(generation: UUID\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func startPreflightTest", text)
if not run_match:
    errors.append("AppState.runPreflightTest(generation:) not found")
else:
    body = run_match.group("body")
    for token in [
        "guard preflightTestGeneration == generation else { return }",
        "defer {",
        "if preflightTestGeneration == generation {",
        "isRunningPreflightTest = false",
        "guard self?.preflightTestGeneration == generation else { return }",
        "self?.preflightTestReport = report",
        "guard preflightTestGeneration == generation else { return }",
        "refreshSetupChecklist()",
    ]:
        if token not in body:
            errors.append(f"runPreflightTest must guard UI state/report updates by generation through {token}")
    if "defer { isRunningPreflightTest = false }" in body:
        errors.append("runPreflightTest must not clear isRunningPreflightTest unconditionally in a stale task")

start_match = re.search(r"func startPreflightTest\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func showTemporaryTestCaption", text)
if not start_match:
    errors.append("AppState.startPreflightTest() not found")
else:
    body = start_match.group("body")
    for token in [
        "let generation = UUID()",
        "preflightTestGeneration = generation",
        "await self?.runPreflightTest(generation: generation)",
        "if self?.preflightTestGeneration == generation {",
        "self?.preflightTestTask = nil",
    ]:
        if token not in body:
            errors.append(f"startPreflightTest must launch a generation-scoped task through {token}")
    if "guard !Task.isCancelled else { return }\n            self?.preflightTestTask = nil" in body:
        errors.append("startPreflightTest must not skip task cleanup solely because the old task was cancelled")

cancel_match = re.search(r"private func cancelPreflightTest\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func openMicrophoneSettings", text)
if not cancel_match:
    errors.append("AppState.cancelPreflightTest() not found")
else:
    body = cancel_match.group("body")
    if "preflightTestGeneration = UUID()" not in body:
        errors.append("cancelPreflightTest must advance preflightTestGeneration before cancelled work can publish stale UI state")
    cancel_idx = body.find("preflightTestGeneration = UUID()")
    task_cancel_idx = body.find("preflightTestTask?.cancel()")
    if cancel_idx == -1 or task_cancel_idx == -1 or cancel_idx > task_cancel_idx:
        errors.append("cancelPreflightTest must advance generation before cancelling the old preflight task")

if errors:
    print("Preflight generation guard verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Preflight generation guard verification passed")
