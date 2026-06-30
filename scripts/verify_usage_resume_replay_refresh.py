#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

if "private var pendingUsageResumeReplayChunks: [BufferedAudioChunk] = []" not in text:
    errors.append("AppState must keep the latest pending usage resume replay buffer")

schedule_match = re.search(r"private func scheduleUsageResume\(replayChunks: \[BufferedAudioChunk\]\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func resumeFromUsagePause", text)
if not schedule_match:
    errors.append("AppState.scheduleUsageResume(replayChunks:) not found")
else:
    body = schedule_match.group("body")
    for token in [
        "pendingUsageResumeReplayChunks = replayChunks",
        "guard usageResumeTask == nil else { return }",
        "await self?.resumeFromUsagePause(generation: generation)",
    ]:
        if token not in body:
            errors.append(f"scheduleUsageResume must refresh replay state through {token}")
    fixed_call = "resumeFromUsagePause(replayChunks: replayChunks, generation: generation)"
    if fixed_call in body:
        errors.append("scheduleUsageResume must not freeze the first replayChunks snapshot into the resume task")
    pending_idx = body.find("pendingUsageResumeReplayChunks = replayChunks")
    guard_idx = body.find("guard usageResumeTask == nil else { return }")
    if pending_idx == -1 or guard_idx == -1 or pending_idx > guard_idx:
        errors.append("scheduleUsageResume must update pendingUsageResumeReplayChunks before returning for an already-running resume task")

resume_match = re.search(r"private func resumeFromUsagePause\(generation: UUID\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    private func runningUsageStatusMessage", text)
if not resume_match:
    errors.append("AppState.resumeFromUsagePause(generation:) not found")
else:
    body = resume_match.group("body")
    for token in [
        "let replayChunks = pendingUsageResumeReplayChunks",
        "pendingUsageResumeReplayChunks.removeAll",
        "usageEngine.markResumed(now: Date())",
        "recordReplayedUsageChunk(chunk)",
    ]:
        if token not in body:
            errors.append(f"resumeFromUsagePause must use and clear the refreshed replay buffer through {token}")
    if "usageEngine.markReplaySent(replayChunks)" in body or "sentChunkCount += replayChunks.count" in body:
        errors.append("resumeFromUsagePause must not batch-account replay usage only after the full replay completes")
    connect_idx = body.find("try await newClient.connect()")
    assign_idx = body.find("client = newClient")
    capture_idx = body.find("let replayChunks = pendingUsageResumeReplayChunks")
    mark_resumed_idx = body.find("usageEngine.markResumed(now: Date())")
    loop_idx = body.find("for chunk in replayChunks")
    record_idx = body.find("recordReplayedUsageChunk(chunk)", loop_idx)
    if min(connect_idx, capture_idx, assign_idx, mark_resumed_idx, loop_idx, record_idx) != -1:
        if not (connect_idx < assign_idx < capture_idx < mark_resumed_idx < loop_idx < record_idx):
            errors.append("resumeFromUsagePause must connect, publish client, capture latest replay, mark active, send replay, then incrementally account replay")

for name, pattern in [
    ("start", r"func start\(\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func stop"),
    ("stop", r"private func stop\(cancelPendingRestart: Bool, saveTranscriptImmediately: Bool = true\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func requestStart"),
    ("stopRuntimeAfterConnectionFailure", r"private func stopRuntimeAfterConnectionFailure\(generation: UUID\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    private func connectionEvent"),
    ("enterUsagePause", r"private func enterUsagePause\(reason: UsageControlPauseReason\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func scheduleUsageResume"),
]:
    match = re.search(pattern, text)
    if not match:
        errors.append(f"AppState.{name} not found")
        continue
    if "pendingUsageResumeReplayChunks.removeAll" not in match.group("body"):
        errors.append(f"AppState.{name} must clear stale pending usage resume replay chunks")

if errors:
    print("Usage resume replay refresh verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Usage resume replay refresh verification passed")
