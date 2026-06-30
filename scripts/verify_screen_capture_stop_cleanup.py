#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Services" / "ScreenAudioCapture.swift"
text = path.read_text()
errors: list[str] = []

stop_match = re.search(r"func stop\(\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    private func cleanupFailedStart", text)
if not stop_match:
    errors.append("ScreenAudioCapture.stop() not found")
else:
    body = stop_match.group("body")
    for token in [
        "chunker.reset()",
        "guard let stream else { return }",
        "self.stream = nil",
        "try? stream.removeStreamOutput(self, type: .audio)",
        "try? stream.removeStreamOutput(self, type: .screen)",
        "try? await stream.stopCapture()",
    ]:
        if token not in body:
            errors.append(f"ScreenAudioCapture.stop() must release SCStream resources through {token}")
    clear_idx = body.find("self.stream = nil")
    stop_idx = body.find("try? await stream.stopCapture()")
    if clear_idx == -1 or stop_idx == -1 or clear_idx > stop_idx:
        errors.append("ScreenAudioCapture.stop() must clear its stream reference before awaiting stopCapture to avoid retaining stale streams")

for name, pattern in [
    ("cleanupFailedStart", r"private func cleanupFailedStart\(_ stream: SCStream\) async \{(?P<body>[\s\S]*?)\n    \}\n"),
]:
    match = re.search(pattern, text)
    if not match:
        errors.append(f"ScreenAudioCapture.{name} not found")
        continue
    body = match.group("body")
    for token in [
        "try? stream.removeStreamOutput(self, type: .audio)",
        "try? stream.removeStreamOutput(self, type: .screen)",
    ]:
        if token not in body:
            errors.append(f"ScreenAudioCapture.{name} must mirror normal stop output cleanup through {token}")

if errors:
    print("Screen capture stop cleanup verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Screen capture stop cleanup verification passed")
