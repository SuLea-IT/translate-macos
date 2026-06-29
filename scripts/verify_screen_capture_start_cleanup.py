#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Services" / "ScreenAudioCapture.swift"
text = path.read_text()
errors: list[str] = []

start_match = re.search(r"func start\(\) async throws \{(?P<body>[\s\S]*?)\n    \}\n\n    func stop", text)
if not start_match:
    errors.append("ScreenAudioCapture.start() not found")
else:
    body = start_match.group("body")
    for token in ["do {", "} catch {", "cleanupFailedStart(stream)", "throw error"]:
        if token not in body:
            errors.append(f"ScreenAudioCapture.start() must clean up partially-started SCStream on failure through {token}")
    cleanup_idx = body.find("cleanupFailedStart(stream)")
    throw_idx = body.find("throw error", cleanup_idx)
    if cleanup_idx == -1 or throw_idx == -1:
        errors.append("ScreenAudioCapture.start() must run cleanup before rethrowing startup failures")
    success_idx = body.find("self.stream = stream")
    start_idx = body.find("try await stream.startCapture()")
    if start_idx == -1 or success_idx == -1 or success_idx < start_idx:
        errors.append("ScreenAudioCapture.start() must only publish stream after startCapture succeeds")

cleanup_match = re.search(r"private func cleanupFailedStart\(_ stream: SCStream\) async \{(?P<body>[\s\S]*?)\n    \}\n", text)
if not cleanup_match:
    errors.append("ScreenAudioCapture must provide cleanupFailedStart(_:) for failed startup cleanup")
else:
    body = cleanup_match.group("body")
    for token in [
        "chunker.reset()",
        "try? stream.removeStreamOutput(self, type: .audio)",
        "try? stream.removeStreamOutput(self, type: .screen)",
        "try? await stream.stopCapture()",
    ]:
        if token not in body:
            errors.append(f"ScreenAudioCapture failed-start cleanup must release resources through {token}")

if errors:
    print("Screen capture start cleanup verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Screen capture start cleanup verification passed")
