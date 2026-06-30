#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

if "private var setupChecklistRefreshGeneration = UUID()" not in text:
    errors.append("AppState must track setupChecklistRefreshGeneration to isolate stale async checklist refreshes")

match = re.search(r"func refreshSetupChecklist\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func runStartPreflight", text)
if not match:
    errors.append("AppState.refreshSetupChecklist() not found")
else:
    body = match.group("body")
    for token in [
        "let generation = UUID()",
        "setupChecklistRefreshGeneration = generation",
        "setupChecklistRefreshTask?.cancel()",
        "setupChecklistRefreshTask = Task",
        "guard self.setupChecklistRefreshGeneration == generation else { return }",
        "guard !Task.isCancelled else { return }",
        "self.setupChecklist = SetupChecklistState.derive",
        "if self.setupChecklistRefreshGeneration == generation {",
        "self.setupChecklistRefreshTask = nil",
    ]:
        if token not in body:
            errors.append(f"refreshSetupChecklist must guard stale async results through {token}")
    result_guard = body.find("guard self.setupChecklistRefreshGeneration == generation else { return }")
    assign_idx = body.find("self.setupChecklist = SetupChecklistState.derive")
    cleanup_guard = body.find("if self.setupChecklistRefreshGeneration == generation {", assign_idx)
    cleanup_idx = body.find("self.setupChecklistRefreshTask = nil", cleanup_guard)
    if -1 in [result_guard, assign_idx, cleanup_guard, cleanup_idx] or not (result_guard < assign_idx < cleanup_guard < cleanup_idx):
        errors.append("refreshSetupChecklist must check generation before publishing and before clearing the task handle")

start_preflight_match = re.search(r"func runStartPreflight\(\) async -> SetupPreflightResult \{(?P<body>[\s\S]*?)\n    \}\n\n    func runPreflightTest", text)
if not start_preflight_match:
    errors.append("AppState.runStartPreflight() not found")
else:
    body = start_preflight_match.group("body")
    if "setupChecklistRefreshGeneration = UUID()" not in body:
        errors.append("runStartPreflight must invalidate pending async checklist refreshes before publishing its authoritative preflight result")
    assign_idx = body.find("setupChecklistRefreshGeneration = UUID()")
    checklist_idx = body.find("setupChecklist = checklist")
    if assign_idx == -1 or checklist_idx == -1 or assign_idx > checklist_idx:
        errors.append("runStartPreflight must invalidate stale refresh generation before assigning setupChecklist")

if errors:
    print("Setup checklist generation guard verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Setup checklist generation guard verification passed")
