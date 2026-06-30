#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Services" / "ScreenAudioCapture.swift"
text = path.read_text()
errors: list[str] = []

deinit_match = re.search(r"deinit \{(?P<body>[\s\S]*?)\n    \}\n\n    func start", text)
if not deinit_match:
    errors.append("ScreenAudioCapture.deinit not found")
else:
    body = deinit_match.group("body")
    for token in [
        "chunker.reset()",
        "if let screenStreamForDeinit = stream",
        "try? screenStreamForDeinit.removeStreamOutput(self, type: .audio)",
        "try? screenStreamForDeinit.removeStreamOutput(self, type: .screen)",
        "Task {",
        "try? await screenStreamForDeinit.stopCapture()",
    ]:
        if token not in body:
            errors.append(f"ScreenAudioCapture.deinit must mirror stop cleanup without retaining self through {token}")
    remove_audio_idx = body.find("try? screenStreamForDeinit.removeStreamOutput(self, type: .audio)")
    remove_screen_idx = body.find("try? screenStreamForDeinit.removeStreamOutput(self, type: .screen)")
    task_idx = body.find("Task {")
    if -1 in [remove_audio_idx, remove_screen_idx, task_idx] or not (remove_audio_idx < task_idx and remove_screen_idx < task_idx):
        errors.append("ScreenAudioCapture.deinit must remove stream outputs before launching the async stopCapture task")
    if "await self" in body or "self.stop()" in body:
        errors.append("ScreenAudioCapture.deinit must not capture self in async cleanup")

if errors:
    print("Screen capture deinit cleanup verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Screen capture deinit cleanup verification passed")
