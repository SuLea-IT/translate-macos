#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

resume_match = re.search(
    r"private func resumeFromUsagePause\(generation: UUID\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    private func runningUsageStatusMessage",
    text,
)
if not resume_match:
    errors.append("AppState.resumeFromUsagePause(generation:) not found")
else:
    body = resume_match.group("body")
    for token in [
        "var replayUsageLedgerNeedsSave = false",
        "defer {",
        "if replayUsageLedgerNeedsSave {",
        "saveUsageLedger()",
        "recordReplayedUsageChunk(chunk)",
        "replayUsageLedgerNeedsSave = true",
    ]:
        if token not in body:
            errors.append(f"resumeFromUsagePause must account replay chunks incrementally and save partial sends through {token}")
    batch_tokens = ["sentChunkCount += replayChunks.count", "usageEngine.markReplaySent(replayChunks)"]
    for token in batch_tokens:
        if token in body:
            errors.append(f"resumeFromUsagePause must not wait until full replay completion to batch account usage through {token}")
    send_idx = body.find("await newClient.sendAudio(chunk.data)")
    record_idx = body.find("recordReplayedUsageChunk(chunk)", send_idx)
    flag_idx = body.find("replayUsageLedgerNeedsSave = true", record_idx)
    if -1 in [send_idx, record_idx, flag_idx] or not (send_idx < record_idx < flag_idx):
        errors.append("resumeFromUsagePause must record each replay chunk immediately after sending it")

helper_match = re.search(
    r"private func recordReplayedUsageChunk\(_ chunk: BufferedAudioChunk\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func runningUsageStatusMessage",
    text,
)
if not helper_match:
    errors.append("AppState.recordReplayedUsageChunk(_:) not found before runningUsageStatusMessage")
else:
    helper = helper_match.group("body")
    for token in [
        "sentChunkCount += 1",
        "usageEngine.markReplaySent([chunk])",
        "usageSnapshot = usageEngine.snapshot",
    ]:
        if token not in helper:
            errors.append(f"recordReplayedUsageChunk must update replay accounting through {token}")

if errors:
    print("Usage replay incremental accounting verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Usage replay incremental accounting verification passed")
