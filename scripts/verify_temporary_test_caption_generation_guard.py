#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

if "private var temporaryTestCaptionGeneration = UUID()" not in text:
    errors.append("AppState must track temporaryTestCaptionGeneration to isolate stale delayed subtitle tasks")

show_match = re.search(r"func showTemporaryTestCaption\(\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    private func cancelPreflightTest", text)
if not show_match:
    errors.append("AppState.showTemporaryTestCaption() not found")
else:
    body = show_match.group("body")
    for token in [
        "temporaryTestCaptionTask?.cancel()",
        "temporaryTestCaptionTask = nil",
        "restoreTemporaryTestCaptionIfNeeded()",
        "let generation = UUID()",
        "temporaryTestCaptionGeneration = generation",
        "temporaryTestCaptionPreviousDraft = previousDraft",
        "temporaryTestCaptionTask = Task",
        "guard !Task.isCancelled else { return }",
        "guard self.temporaryTestCaptionGeneration == generation else { return }",
        "self.restoreTemporaryTestCaptionIfNeeded()",
        "if self.temporaryTestCaptionGeneration == generation {",
        "self.temporaryTestCaptionTask = nil",
    ]:
        if token not in body:
            errors.append(f"showTemporaryTestCaption must guard delayed subtitle state through {token}")

    restore_idx = body.find("restoreTemporaryTestCaptionIfNeeded()")
    generation_idx = body.find("let generation = UUID()", restore_idx)
    assign_generation_idx = body.find("temporaryTestCaptionGeneration = generation", generation_idx)
    snapshot_idx = body.find("let previousDraft = captionDraft", assign_generation_idx)
    task_idx = body.find("temporaryTestCaptionTask = Task", snapshot_idx)
    cancel_guard_idx = body.find("guard !Task.isCancelled else { return }", task_idx)
    generation_guard_idx = body.find("guard self.temporaryTestCaptionGeneration == generation else { return }", cancel_guard_idx)
    restore_task_idx = body.find("self.restoreTemporaryTestCaptionIfNeeded()", generation_guard_idx)
    nil_guard_idx = body.find("if self.temporaryTestCaptionGeneration == generation {", restore_task_idx)
    nil_idx = body.find("self.temporaryTestCaptionTask = nil", nil_guard_idx)
    if -1 in [restore_idx, generation_idx, assign_generation_idx, snapshot_idx, task_idx, cancel_guard_idx, generation_guard_idx, restore_task_idx, nil_guard_idx, nil_idx] or not (restore_idx < generation_idx < assign_generation_idx < snapshot_idx < task_idx < cancel_guard_idx < generation_guard_idx < restore_task_idx < nil_guard_idx < nil_idx):
        errors.append("showTemporaryTestCaption must create a new generation before snapshotting state and only restore/clear state for that same generation")

cancel_match = re.search(r"private func cancelPreflightTest\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func openMicrophoneSettings", text)
if not cancel_match:
    errors.append("AppState.cancelPreflightTest() not found")
else:
    body = cancel_match.group("body")
    for token in [
        "temporaryTestCaptionGeneration = UUID()",
        "temporaryTestCaptionTask?.cancel()",
        "temporaryTestCaptionTask = nil",
        "restoreTemporaryTestCaptionIfNeeded()",
    ]:
        if token not in body:
            errors.append(f"cancelPreflightTest must invalidate delayed subtitle state through {token}")
    generation_idx = body.find("temporaryTestCaptionGeneration = UUID()")
    cancel_idx = body.find("temporaryTestCaptionTask?.cancel()", generation_idx)
    nil_idx = body.find("temporaryTestCaptionTask = nil", cancel_idx)
    restore_idx = body.find("restoreTemporaryTestCaptionIfNeeded()", nil_idx)
    if -1 in [generation_idx, cancel_idx, nil_idx, restore_idx] or not (generation_idx < cancel_idx < nil_idx < restore_idx):
        errors.append("cancelPreflightTest must advance temporary caption generation before cancelling/restoring stale delayed state")

if errors:
    print("Temporary test caption generation guard verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Temporary test caption generation guard verification passed")
