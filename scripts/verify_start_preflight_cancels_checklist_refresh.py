#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

match = re.search(
    r"func runStartPreflight\(\) async -> SetupPreflightResult \{(?P<body>[\s\S]*?)\n    \}\n\n    func runPreflightTest",
    text,
)
if not match:
    errors.append("AppState.runStartPreflight() not found")
else:
    body = match.group("body")
    for token in [
        "setupChecklistRefreshGeneration = UUID()",
        "setupChecklistRefreshTask?.cancel()",
        "setupChecklistRefreshTask = nil",
        "let permissions = await permissionStatusService.refreshStatuses()",
        "publishSetupChecklist(checklist)",
    ]:
        if token not in body:
            errors.append(f"runStartPreflight must cancel and clear stale async checklist refresh work before publishing through {token}")
    generation_idx = body.find("setupChecklistRefreshGeneration = UUID()")
    cancel_idx = body.find("setupChecklistRefreshTask?.cancel()")
    nil_idx = body.find("setupChecklistRefreshTask = nil")
    await_idx = body.find("let permissions = await permissionStatusService.refreshStatuses()")
    publish_idx = body.find("publishSetupChecklist(checklist)")
    if -1 in [generation_idx, cancel_idx, nil_idx, await_idx, publish_idx] or not (generation_idx < cancel_idx < nil_idx < await_idx < publish_idx):
        errors.append("runStartPreflight must invalidate generation, cancel and clear the stale refresh task before awaiting permission refresh")

if errors:
    print("Start preflight checklist refresh cancellation verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Start preflight checklist refresh cancellation verification passed")
