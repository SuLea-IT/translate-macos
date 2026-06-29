#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = app_state_path.read_text()
errors: list[str] = []

shortcut_match = re.search(r"let results = globalShortcutRegistrar\.register\([\s\S]*?\) \{ \[weak self\] action in(?P<body>[\s\S]*?)\n        \}", text)
if not shortcut_match:
    errors.append("AppState global shortcut callback not found")
else:
    body = shortcut_match.group("body")
    if "Task { @MainActor [weak self] in" not in body:
        errors.append("Global shortcut callback must weakly capture self again inside the nested MainActor Task")
    if "self?.performGlobalShortcut(action)" not in body:
        errors.append("Global shortcut callback must still dispatch the requested action")

device_match = re.search(r"let block: AudioObjectPropertyListenerBlock = \{ \[weak self\] _, _ in(?P<body>[\s\S]*?)\n        \}", text)
if not device_match:
    errors.append("AppState CoreAudio device-change listener block not found")
else:
    body = device_match.group("body")
    if "Task { @MainActor [weak self] in" not in body:
        errors.append("CoreAudio device-change callback must weakly capture self again inside the nested MainActor Task")
    if "self?.refreshAvailableMicrophones()" not in body:
        errors.append("CoreAudio device-change callback must still refresh the microphone list")

# Guard against reintroducing broad nested MainActor tasks in these external callback zones.
for context, match in [("global shortcut", shortcut_match), ("device listener", device_match)]:
    if match and "Task { @MainActor in" in match.group("body"):
        errors.append(f"AppState {context} callback must not use an unqualified nested MainActor Task")

if errors:
    print("Nested callback weak-capture verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Nested callback weak-capture verification passed")
