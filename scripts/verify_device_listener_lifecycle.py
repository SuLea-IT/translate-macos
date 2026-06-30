#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

if "private var propertyListenerBlock: AudioObjectPropertyListenerBlock?" not in text:
    errors.append("AppState must keep the CoreAudio listener block so it can be removed later")

if "private static func audioDevicePropertyAddress()" not in text:
    errors.append("AppState must centralize the CoreAudio device property address for add/remove symmetry")

start_match = re.search(r"private func startListeningForDeviceChanges\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func stopListeningForDeviceChanges", text)
if not start_match:
    errors.append("AppState.startListeningForDeviceChanges() must appear before stopListeningForDeviceChanges()")
else:
    body = start_match.group("body")
    for token in [
        "stopListeningForDeviceChanges()",
        "var propertyAddress = Self.audioDevicePropertyAddress()",
        "let block: AudioObjectPropertyListenerBlock = { [weak self] _, _ in",
        "Task { @MainActor [weak self] in",
        "self?.refreshAvailableMicrophones()",
        "let status = AudioObjectAddPropertyListenerBlock(",
        "guard status == noErr else {",
        "appendLog(\"Microphone device listener failed to start: \\(status)\", level: .error)",
        "propertyListenerBlock = block",
    ]:
        if token not in body:
            errors.append(f"startListeningForDeviceChanges must make listener registration idempotent through {token}")

    stop_idx = body.find("stopListeningForDeviceChanges()")
    add_idx = body.find("let status = AudioObjectAddPropertyListenerBlock(")
    guard_idx = body.find("guard status == noErr else {", add_idx)
    save_idx = body.find("propertyListenerBlock = block", guard_idx)
    if -1 in [stop_idx, add_idx, guard_idx, save_idx] or not (stop_idx < add_idx < guard_idx < save_idx):
        errors.append("startListeningForDeviceChanges must remove old listener, add the new listener, check status, then save the block")
    early_save_idx = body.find("propertyListenerBlock = block")
    if early_save_idx != save_idx:
        errors.append("startListeningForDeviceChanges must only save propertyListenerBlock after a successful CoreAudio registration")

stop_match = re.search(r"private func stopListeningForDeviceChanges\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    deinit", text)
if not stop_match:
    errors.append("AppState.stopListeningForDeviceChanges() not found before deinit")
else:
    body = stop_match.group("body")
    for token in [
        "guard let block = propertyListenerBlock else { return }",
        "var propertyAddress = Self.audioDevicePropertyAddress()",
        "AudioObjectRemovePropertyListenerBlock(",
        "propertyListenerBlock = nil",
    ]:
        if token not in body:
            errors.append(f"stopListeningForDeviceChanges must symmetrically remove listener through {token}")
    remove_idx = body.find("AudioObjectRemovePropertyListenerBlock(")
    nil_idx = body.find("propertyListenerBlock = nil", remove_idx)
    if -1 in [remove_idx, nil_idx] or remove_idx > nil_idx:
        errors.append("stopListeningForDeviceChanges must clear propertyListenerBlock after removing the listener")

deinit_match = re.search(r"deinit \{(?P<body>[\s\S]*?)\n    \}", text)
if not deinit_match:
    errors.append("AppState.deinit not found")
else:
    body = deinit_match.group("body")
    if "stopListeningForDeviceChanges()" not in body:
        errors.append("AppState.deinit must use stopListeningForDeviceChanges() instead of inlining CoreAudio cleanup")
    if "AudioObjectRemovePropertyListenerBlock(" in body:
        errors.append("AppState.deinit must not inline device-listener removal; keep cleanup centralized")

if errors:
    print("Device listener lifecycle verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Device listener lifecycle verification passed")
