#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
screen_path = root / "LiveBuddy" / "Services" / "ScreenAudioCapture.swift"
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
interface_path = root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift"
screen = screen_path.read_text()
app_state = app_state_path.read_text()
interface = interface_path.read_text()
errors: list[str] = []

for token in [
    "enum ScreenAudioCaptureStatus: Equatable, Sendable",
    "case stopped(String)",
    "case unsupportedFormat(flags: UInt32, bits: UInt32)",
    "private let onStatus: (@Sendable (ScreenAudioCaptureStatus) -> Void)?",
    "onStatus?(.stopped(error.localizedDescription))",
    "onStatus?(.unsupportedFormat(flags: UInt32(flags), bits: bits))",
]:
    if token not in screen:
        errors.append(f"ScreenAudioCapture must emit structured status through {token}")

for old in [
    'onStatus?("Screen audio stopped:',
    'onStatus?("Unsupported screen audio format:',
]:
    if old in screen:
        errors.append(f"ScreenAudioCapture must not emit hard-coded English status {old}")

for key in ["statusScreenAudioStopped", "statusScreenAudioUnsupportedFormat"]:
    if f"case {key}" not in interface:
        errors.append(f"InterfaceText must include {key}")
    if interface.count(f".{key}:") < 8:
        errors.append(f"InterfaceText.{key} must be translated for every supported language")

capture_match = re.search(r"let screen = ScreenAudioCapture\([\s\S]*?\n                \)\n", app_state)
if not capture_match:
    errors.append("AppState screen capture construction not found")
else:
    body = capture_match.group(0)
    for token in [
        "onStatus: { [weak self] status in",
        "self?.handleScreenAudioStatus(status, generation: generation)",
    ]:
        if token not in body:
            errors.append(f"AppState must localize screen audio status callback through {token}")
    if "onStatus: { [weak self] message in" in body:
        errors.append("AppState must not publish raw screen audio status strings")

handler_match = re.search(
    r"private func handleScreenAudioStatus\(_ status: ScreenAudioCaptureStatus, generation: UUID\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func localizedScreenAudioStatus",
    app_state,
)
if not handler_match:
    errors.append("AppState.handleScreenAudioStatus(_:generation:) not found")
else:
    body = handler_match.group("body")
    for token in [
        "let message = localizedScreenAudioStatus(status)",
        "updateStatus(message, level: .error, log: true)",
    ]:
        if token not in body:
            errors.append(f"AppState.handleScreenAudioStatus must publish localized screen audio status through {token}")

helper_match = re.search(r"private func localizedScreenAudioStatus\(_ status: ScreenAudioCaptureStatus\) -> String \{(?P<body>[\s\S]*?)\n    \}\n\n    private func audioSink", app_state)
if not helper_match:
    errors.append("AppState.localizedScreenAudioStatus(_:) not found")
else:
    body = helper_match.group("body")
    for token in [
        "case .stopped(let reason):",
        "return settings.interfaceLanguage.localized(.statusScreenAudioStopped, arguments: [reason])",
        "case .unsupportedFormat(let flags, let bits):",
        "return settings.interfaceLanguage.localized(.statusScreenAudioUnsupportedFormat, arguments: [flags, bits])",
    ]:
        if token not in body:
            errors.append(f"localizedScreenAudioStatus must map status to localized text through {token}")

if errors:
    print("Screen audio status localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Screen audio status localization verification passed")
