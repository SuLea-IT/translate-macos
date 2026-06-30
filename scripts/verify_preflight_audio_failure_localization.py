#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
runner = (root / "LiveBuddy" / "Services" / "PreflightTestRunner.swift").read_text()
errors: list[str] = []

step_match = re.search(
    r"private func runAudioStep\([\s\S]*?\n    \) async -> PreflightTestReport \{(?P<body>[\s\S]*?)\n    \}\n\n    private func runSubtitle",
    runner,
)
if not step_match:
    errors.append("PreflightTestRunner.runAudioStep(...) not found")
else:
    body = step_match.group("body")
    if "message: error.localizedDescription" in body:
        errors.append("runAudioStep must not expose raw localizedDescription for user-visible audio sampling failures")
    for token in [
        "let messageKey = audioFailureMessageKey(id: id, error: error)",
        "report = report.updating(id, state: .failed, messageKey: messageKey)",
    ]:
        if token not in body:
            errors.append(f"runAudioStep must localize audio sampling failures through {token}")

helper_match = re.search(
    r"private func audioFailureMessageKey\(id: PreflightTestStepID, error: Error\) -> InterfaceText \{(?P<body>[\s\S]*?)\n    \}",
    runner,
)
if not helper_match:
    errors.append("PreflightTestRunner.audioFailureMessageKey(id:error:) not found")
else:
    body = helper_match.group("body")
    for token in [
        "if error is MicrophoneCaptureError",
        "return .diagnosticMicrophoneUnavailableTitle",
        "if error is ScreenAudioCaptureError",
        "return .diagnosticScreenAudioUnavailableTitle",
        "switch id",
        "case .microphoneAudio:",
        "case .screenAudio:",
        "return .diagnosticMicrophoneUnavailableTitle",
        "return .diagnosticScreenAudioUnavailableTitle",
    ]:
        if token not in body:
            errors.append(f"audioFailureMessageKey must map known audio failures to localized diagnostics through {token}")

if errors:
    print("Preflight audio failure localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Preflight audio failure localization verification passed")
