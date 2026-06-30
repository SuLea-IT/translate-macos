#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

if "private var usageResumeGeneration = UUID()" not in text:
    errors.append("AppState must track usageResumeGeneration to isolate stale resume tasks")

schedule_match = re.search(r"private func scheduleUsageResume\(replayChunks: \[BufferedAudioChunk\]\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func resumeFromUsagePause", text)
if not schedule_match:
    errors.append("AppState.scheduleUsageResume(replayChunks:) not found")
else:
    body = schedule_match.group("body")
    for token in [
        "guard usageResumeTask == nil else { return }",
        "let generation = UUID()",
        "usageResumeGeneration = generation",
        "usageResumeTask = Task",
        "await self?.resumeFromUsagePause(replayChunks: replayChunks, generation: generation)",
    ]:
        if token not in body:
            errors.append(f"scheduleUsageResume must launch generation-scoped resume work through {token}")

resume_match = re.search(r"private func resumeFromUsagePause\(replayChunks: \[BufferedAudioChunk\], generation: UUID\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    private func runningUsageStatusMessage", text)
if not resume_match:
    errors.append("AppState.resumeFromUsagePause(replayChunks:generation:) not found")
else:
    body = resume_match.group("body")
    for token in [
        "guard usageResumeGeneration == generation else { return }",
        "usageResumeTask = nil",
        "usageResumeGeneration == generation",
        "client = newClient",
        "usageEngine.markResumed(now: Date())",
        "usageEngine.forcePause(.idle)",
    ]:
        if token not in body:
            errors.append(f"resumeFromUsagePause must guard stale resume state through {token}")
    if body.count("usageResumeTask = nil") < 5:
        errors.append("resumeFromUsagePause must release the task handle on all guarded exit paths")
    if "usageResumeTask = nil" in body and "usageResumeGeneration == generation" not in body:
        errors.append("resumeFromUsagePause must not clear usageResumeTask without checking generation")

for name, pattern in [
    ("start", r"func start\(\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func stop"),
    ("stop", r"private func stop\(cancelPendingRestart: Bool\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func requestStart"),
    ("stopRuntimeAfterConnectionFailure", r"private func stopRuntimeAfterConnectionFailure\(\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    private func connectionEvent"),
    ("enterUsagePause", r"private func enterUsagePause\(reason: UsageControlPauseReason\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func scheduleUsageResume"),
]:
    match = re.search(pattern, text)
    if not match:
        errors.append(f"AppState.{name} not found")
        continue
    body = match.group("body")
    if "usageResumeGeneration = UUID()" not in body:
        errors.append(f"AppState.{name} must invalidate stale usage resume tasks through usageResumeGeneration = UUID()")

if errors:
    print("Usage resume generation guard verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Usage resume generation guard verification passed")
