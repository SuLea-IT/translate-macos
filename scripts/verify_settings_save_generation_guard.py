#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

if "private var settingsSaveGeneration = UUID()" not in text:
    errors.append("AppState must track settingsSaveGeneration to isolate stale debounced settings save tasks")

schedule_match = re.search(r"private func scheduleSettingsSave\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func saveSettingsImmediately", text)
if not schedule_match:
    errors.append("AppState.scheduleSettingsSave() not found")
else:
    body = schedule_match.group("body")
    for token in [
        "guard settingsSaveTask == nil else { return }",
        "let generation = UUID()",
        "settingsSaveGeneration = generation",
        "settingsSaveTask = Task",
        "guard self.settingsSaveGeneration == generation else { return }",
        "self.saveSettings()",
        "if self.settingsSaveGeneration == generation",
        "self.settingsSaveTask = nil",
    ]:
        if token not in body:
            errors.append(f"scheduleSettingsSave must guard debounced save lifecycle through {token}")
    if "settingsSaveTask = nil" in body and "settingsSaveGeneration == generation" not in body:
        errors.append("scheduleSettingsSave must not clear settingsSaveTask without checking generation")
    sleep_idx = body.find("try await Task.sleep")
    generation_guard_idx = body.find("guard self.settingsSaveGeneration == generation else { return }", sleep_idx)
    save_idx = body.find("self.saveSettings()")
    if -1 in [sleep_idx, generation_guard_idx, save_idx] or not (sleep_idx < generation_guard_idx < save_idx):
        errors.append("scheduleSettingsSave must re-check generation after debounce sleep before writing settings")

immediate_match = re.search(r"private func saveSettingsImmediately\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func saveSettings", text)
if not immediate_match:
    errors.append("AppState.saveSettingsImmediately() not found")
else:
    body = immediate_match.group("body")
    for token in [
        "settingsSaveGeneration = UUID()",
        "settingsSaveTask?.cancel()",
        "settingsSaveTask = nil",
        "saveSettings()",
    ]:
        if token not in body:
            errors.append(f"saveSettingsImmediately must invalidate stale debounced settings saves through {token}")

if errors:
    print("Settings save generation guard verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Settings save generation guard verification passed")
