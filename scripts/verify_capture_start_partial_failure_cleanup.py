#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

match = re.search(r"private func startCapture\(\) async throws \{(?P<body>[\s\S]*?)\n    \}\n\n    private func audioSink", text)
if not match:
    errors.append("AppState.startCapture() not found")
else:
    body = match.group("body")
    for token in [
        "do {",
        "} catch {",
        "audioCaptureGeneration = UUID()",
        "microphoneCapture?.stop()",
        "microphoneCapture = nil",
        "await screenCapture?.stop()",
        "screenCapture = nil",
        "throw error",
    ]:
        if token not in body:
            errors.append(f"AppState.startCapture() must clean partially-started capture resources before rethrowing through {token}")

    do_index = body.find("do {")
    mic_assign_index = body.find("microphoneCapture = mic")
    screen_assign_index = body.find("screenCapture = screen")
    catch_index = body.find("} catch {")
    generation_index = body.find("audioCaptureGeneration = UUID()", catch_index)
    cleanup_index = body.find("microphoneCapture?.stop()", generation_index)
    throw_index = body.find("throw error", cleanup_index)
    if -1 in [do_index, mic_assign_index, screen_assign_index, catch_index, generation_index, cleanup_index, throw_index]:
        errors.append("AppState.startCapture() cleanup structure is incomplete")
    elif not (do_index < mic_assign_index < screen_assign_index < catch_index < generation_index < cleanup_index < throw_index):
        errors.append("AppState.startCapture() must wrap all capture startup assignments in one do/catch cleanup scope")

if errors:
    print("Capture partial-start cleanup verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Capture partial-start cleanup verification passed")
