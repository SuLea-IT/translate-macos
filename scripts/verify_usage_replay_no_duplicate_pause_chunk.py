#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
usage_path = root / "LiveBuddy" / "Models" / "UsageControl.swift"
tests_path = root / "LiveBuddyTests" / "UsageControlTests.swift"
usage = usage_path.read_text()
tests = tests_path.read_text()
errors: list[str] = []

append_match = re.search(
    r"private mutating func appendPaused\(_ chunk: BufferedAudioChunk\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func limitReasonIfSending",
    usage,
)
if not append_match:
    errors.append("UsageControlEngine.appendPaused(_:) not found")
else:
    body = append_match.group("body")
    for token in [
        "if prerollBuffer.last == chunk {",
        "prerollBuffer.removeLast()",
        "pausedBuffer.append(chunk)",
    ]:
        if token not in body:
            errors.append(f"appendPaused must move the pause-triggering chunk out of preroll before buffering it through {token}")
    remove_idx = body.find("prerollBuffer.removeLast()")
    append_idx = body.find("pausedBuffer.append(chunk)")
    if -1 in [remove_idx, append_idx] or not (remove_idx < append_idx):
        errors.append("appendPaused must remove a duplicate preroll tail before appending to pausedBuffer")

if "pauseTriggeringChunkIsNotDuplicatedInReplayBuffer" not in tests:
    errors.append("UsageControlTests must cover that the chunk triggering pause is not duplicated in replay")
if "Set(replayTimes).count == replayTimes.count" not in tests:
    errors.append("UsageControlTests must assert replay chunks have unique capturedAt values")
if "replayTimes.contains(start.addingTimeInterval(7))" not in tests:
    errors.append("UsageControlTests must assert the pause-triggering chunk is still replayed once")

if errors:
    print("Usage replay duplicate pause-chunk verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Usage replay duplicate pause-chunk verification passed")
