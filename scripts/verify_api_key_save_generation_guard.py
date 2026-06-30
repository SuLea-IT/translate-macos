#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

if "private var apiKeySaveGeneration = UUID()" not in text:
    errors.append("AppState must track apiKeySaveGeneration to isolate stale debounced API key save tasks")

schedule_match = re.search(r"private func scheduleAPIKeySave\(_ apiKey: String\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func saveAPIKeyImmediately", text)
if not schedule_match:
    errors.append("AppState.scheduleAPIKeySave(_:) not found")
else:
    body = schedule_match.group("body")
    for token in [
        "pendingAPIKeyForKeychain = apiKey",
        "apiKeySaveTask?.cancel()",
        "let generation = UUID()",
        "apiKeySaveGeneration = generation",
        "apiKeySaveTask = Task",
        "guard self.apiKeySaveGeneration == generation else { return }",
        "self.savePendingAPIKeyToKeychain()",
        "if self.apiKeySaveGeneration == generation",
        "self.apiKeySaveTask = nil",
    ]:
        if token not in body:
            errors.append(f"scheduleAPIKeySave must guard debounced save lifecycle through {token}")
    if "apiKeySaveTask = nil" in body and "apiKeySaveGeneration == generation" not in body:
        errors.append("scheduleAPIKeySave must not clear apiKeySaveTask without checking generation")
    sleep_idx = body.find("try await Task.sleep")
    generation_guard_idx = body.find("guard self.apiKeySaveGeneration == generation else { return }", sleep_idx)
    save_idx = body.find("self.savePendingAPIKeyToKeychain()")
    if -1 in [sleep_idx, generation_guard_idx, save_idx] or not (sleep_idx < generation_guard_idx < save_idx):
        errors.append("scheduleAPIKeySave must re-check generation after debounce sleep before saving")

immediate_match = re.search(r"private func saveAPIKeyImmediately\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func savePendingAPIKeyToKeychain", text)
if not immediate_match:
    errors.append("AppState.saveAPIKeyImmediately() not found")
else:
    body = immediate_match.group("body")
    for token in [
        "pendingAPIKeyForKeychain = settings.apiKey",
        "apiKeySaveGeneration = UUID()",
        "apiKeySaveTask?.cancel()",
        "apiKeySaveTask = nil",
        "savePendingAPIKeyToKeychain()",
    ]:
        if token not in body:
            errors.append(f"saveAPIKeyImmediately must invalidate stale debounced saves through {token}")

if errors:
    print("API key save generation guard verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("API key save generation guard verification passed")
