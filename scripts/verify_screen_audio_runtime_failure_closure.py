#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state = (root / "LiveBuddy" / "Models" / "AppState.swift").read_text()
diagnostic = (root / "LiveBuddy" / "Models" / "DiagnosticIssue.swift").read_text()
errors: list[str] = []

capture_match = re.search(r"let screen = ScreenAudioCapture\([\s\S]*?\n                \)\n", app_state)
if not capture_match:
    errors.append("AppState screen capture construction not found")
else:
    body = capture_match.group(0)
    if "self?.handleScreenAudioStatus(status, generation: generation)" not in body:
        errors.append("Screen audio status callback must delegate to handleScreenAudioStatus(status:generation:) so runtime failures close the loop")
    for old in [
        "let message = self?.localizedScreenAudioStatus(status) ?? \"\"",
        "self?.updateStatus(message, level: .error, log: true)",
    ]:
        if old in body:
            errors.append(f"Screen audio status callback must not only publish a status message without runtime failure handling: {old}")

handler_match = re.search(
    r"private func handleScreenAudioStatus\(_ status: ScreenAudioCaptureStatus, generation: UUID\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func localizedScreenAudioStatus",
    app_state,
)
if not handler_match:
    errors.append("AppState.handleScreenAudioStatus(_:generation:) not found")
else:
    body = handler_match.group("body")
    required = [
        "guard audioCaptureGeneration == generation else { return }",
        "let message = localizedScreenAudioStatus(status)",
        "updateStatus(message, level: .error, log: true)",
        "setDiagnosticIssue(DiagnosticClassifier.screenAudioRuntimeFailure(underlyingMessage: message))",
        "guard isRunning else { return }",
        "scheduleStopRuntimeAfterCaptureFailure()",
    ]
    for token in required:
        if token not in body:
            errors.append(f"handleScreenAudioStatus must close failed capture state through {token}")
    guard_idx = body.find("guard audioCaptureGeneration == generation else { return }")
    status_idx = body.find("updateStatus(message, level: .error, log: true)")
    diagnostic_idx = body.find("setDiagnosticIssue(DiagnosticClassifier.screenAudioRuntimeFailure(underlyingMessage: message))")
    running_idx = body.find("guard isRunning else { return }")
    stop_idx = body.find("scheduleStopRuntimeAfterCaptureFailure()")
    if -1 not in [guard_idx, status_idx, diagnostic_idx, running_idx, stop_idx] and not (guard_idx < status_idx < diagnostic_idx < running_idx < stop_idx):
        errors.append("handleScreenAudioStatus must guard stale callbacks, publish error, set diagnostics, then stop active runtime")

stop_match = re.search(
    r"private func scheduleStopRuntimeAfterCaptureFailure\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func scheduleStopRuntimeAfterConnectionFailure",
    app_state,
)
if not stop_match:
    errors.append("AppState.scheduleStopRuntimeAfterCaptureFailure() not found")
else:
    body = stop_match.group("body")
    if "scheduleStopRuntimeAfterConnectionFailure()" not in body:
        errors.append("Capture failure stop helper must reuse the existing guarded runtime stop path")

if "static func screenAudioRuntimeFailure(underlyingMessage: String) -> DiagnosticIssue" not in diagnostic:
    errors.append("DiagnosticClassifier must expose screenAudioRuntimeFailure(underlyingMessage:) for runtime capture failures")
else:
    helper_match = re.search(
        r"static func screenAudioRuntimeFailure\(underlyingMessage: String\) -> DiagnosticIssue \{(?P<body>[\s\S]*?)\n    \}",
        diagnostic,
    )
    if not helper_match:
        errors.append("screenAudioRuntimeFailure helper body not found")
    else:
        body = helper_match.group("body")
        for token in [
            ".screenAudioUnavailable",
            "kind: .capture",
            "title: .diagnosticScreenAudioUnavailableTitle",
            "message: .diagnosticScreenAudioUnavailableMessage",
            "recovery: .diagnosticOpenScreenRecordingRecovery",
            "underlying: underlyingMessage",
            "action: .openScreenRecordingSettings",
        ]:
            if token not in body:
                errors.append(f"screenAudioRuntimeFailure must map runtime capture failure diagnostics through {token}")

if errors:
    print("Screen audio runtime failure closure verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Screen audio runtime failure closure verification passed")
