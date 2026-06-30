#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
settings_path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
recorder_path = root / "LiveBuddy" / "Views" / "Settings" / "ShortcutRecorderField.swift"
settings = settings_path.read_text()
recorder = recorder_path.read_text()
errors: list[str] = []

if "@State private var recordingShortcutAction: GlobalShortcutAction?" not in settings:
    errors.append("SettingsView must own a single recordingShortcutAction state for all shortcut rows")
if "ShortcutRecorderField(action: action, recordingAction: $recordingShortcutAction)" not in settings:
    errors.append("SettingsView must pass the shared recording action binding into every ShortcutRecorderField")
if "recordingShortcutAction = nil" not in settings:
    errors.append("SettingsView must clear any active shortcut recording when leaving/closing settings")

if "@State private var isRecording" in recorder:
    errors.append("ShortcutRecorderField must not keep per-row recording state")
if "@Binding var recordingAction: GlobalShortcutAction?" not in recorder:
    errors.append("ShortcutRecorderField must receive the shared recording action binding")
if "private var isRecording: Bool" not in recorder:
    errors.append("ShortcutRecorderField must derive isRecording from recordingAction == action")

for token in [
    "recordingAction == action",
    "recordingAction = action",
    "recordingAction = nil",
    "ShortcutRecorderMonitor(isRecording: isRecordingBinding)",
    "private var isRecordingBinding: Binding<Bool>",
]:
    if token not in recorder:
        errors.append(f"ShortcutRecorderField must coordinate a single active recorder through {token}")

monitor_match = re.search(r"final class Coordinator \{(?P<body>[\s\S]*?)\n    \}\n\}", recorder)
if not monitor_match:
    errors.append("ShortcutRecorderMonitor.Coordinator not found")
else:
    body = monitor_match.group("body")
    for token in ["addLocalMonitorForEvents", "removeMonitor", "deinit"]:
        if token not in body:
            errors.append(f"ShortcutRecorderMonitor.Coordinator must still manage local monitor lifecycle through {token}")

if errors:
    print("Single shortcut recording verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Single shortcut recording verification passed")
