#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Services" / "MicrophoneCapture.swift"
text = path.read_text()
errors: list[str] = []

start_match = re.search(r"func start\(selectedDeviceUID: String\?\) async throws \{(?P<body>[\s\S]*?)\n    \}\n\n    func stop", text)
if not start_match:
    errors.append("MicrophoneCapture.start(selectedDeviceUID:) not found")
else:
    body = start_match.group("body")
    if "print(\"Failed to set audio input device status:" in body:
        errors.append("MicrophoneCapture must not silently print and continue when selecting a microphone fails")
    for token in [
        "if let uid = selectedDeviceUID?.trimmingCharacters(in: .whitespacesAndNewlines), !uid.isEmpty {",
        "guard let deviceID = AudioDeviceManager.getDeviceID(for: uid) else {",
        "throw MicrophoneCaptureError.selectedDeviceUnavailable",
        "throw MicrophoneCaptureError.audioUnitUnavailable",
        "guard status == noErr else {",
        "throw MicrophoneCaptureError.deviceSelectionFailed(status)",
    ]:
        if token not in body:
            errors.append(f"MicrophoneCapture.start must fail closed for stale/unusable selected microphones through {token}")
    lookup_idx = body.find("guard let deviceID = AudioDeviceManager.getDeviceID(for: uid) else")
    set_idx = body.find("AudioUnitSetProperty", lookup_idx)
    status_guard_idx = body.find("guard status == noErr else", set_idx)
    tap_idx = body.find("input.installTap", status_guard_idx)
    if -1 in [lookup_idx, set_idx, status_guard_idx, tap_idx] or not (lookup_idx < set_idx < status_guard_idx < tap_idx):
        errors.append("MicrophoneCapture.start must validate selected device before installing the audio tap")

error_match = re.search(r"enum MicrophoneCaptureError: LocalizedError \{(?P<body>[\s\S]*?)\n\}", text)
if not error_match:
    errors.append("MicrophoneCaptureError enum not found")
else:
    body = error_match.group("body")
    for token in [
        "case selectedDeviceUnavailable",
        "case deviceSelectionFailed(OSStatus)",
        "case .selectedDeviceUnavailable:",
        "case .deviceSelectionFailed(let status):",
        "Selected microphone is no longer available.",
        "Failed to use the selected microphone",
    ]:
        if token not in body:
            errors.append(f"MicrophoneCaptureError must expose user-facing selected-device failures through {token}")

if errors:
    print("Microphone device selection failure verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Microphone device selection failure verification passed")
