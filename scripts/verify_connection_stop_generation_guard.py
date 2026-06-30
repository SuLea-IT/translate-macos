#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

if "private var connectionStopGeneration = UUID()" not in text:
    errors.append("AppState must track connectionStopGeneration to isolate stale connection-failure stop tasks")

schedule_match = re.search(
    r"private func scheduleStopRuntimeAfterConnectionFailure\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func stopRuntimeAfterConnectionFailure",
    text,
)
if not schedule_match:
    errors.append("AppState.scheduleStopRuntimeAfterConnectionFailure() not found")
else:
    body = schedule_match.group("body")
    for token in [
        "guard connectionStopTask == nil else { return }",
        "let generation = UUID()",
        "connectionStopGeneration = generation",
        "connectionStopTask = Task",
        "await self?.stopRuntimeAfterConnectionFailure(generation: generation)",
        "if self?.connectionStopGeneration == generation",
        "self?.connectionStopTask = nil",
    ]:
        if token not in body:
            errors.append(f"scheduleStopRuntimeAfterConnectionFailure must launch generation-scoped stop work through {token}")
    if "connectionStopTask = nil" in body and "connectionStopGeneration == generation" not in body:
        errors.append("scheduleStopRuntimeAfterConnectionFailure must not clear connectionStopTask without checking generation")

stop_match = re.search(
    r"private func stopRuntimeAfterConnectionFailure\(generation: UUID\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    private func connectionEvent",
    text,
)
if not stop_match:
    errors.append("AppState.stopRuntimeAfterConnectionFailure(generation:) not found")
else:
    body = stop_match.group("body")
    for token in [
        "guard connectionStopGeneration == generation else { return }",
        "guard connectionStopGeneration == generation, !Task.isCancelled else { return }",
        "restartGeneration = UUID()",
        "usageResumeGeneration = UUID()",
        "resetAudioSendPipeline()",
        "audioCaptureGeneration = UUID()",
        "if connectionStopGeneration == generation",
        "connectionStopTask = nil",
    ]:
        if token not in body:
            errors.append(f"stopRuntimeAfterConnectionFailure(generation:) must guard stale stop state through {token}")
    destructive_tokens = [
        "userInitiatedStop = true",
        "reconnectTask?.cancel()",
        "restartTask?.cancel()",
        "usageResumeTask?.cancel()",
        "resetAudioSendPipeline()",
        "microphoneCapture?.stop()",
    ]
    first_guard_index = body.find("guard connectionStopGeneration == generation else { return }")
    if first_guard_index == -1:
        errors.append("stopRuntimeAfterConnectionFailure(generation:) must check generation before any destructive cleanup")
    else:
        for token in destructive_tokens:
            idx = body.find(token)
            if idx != -1 and idx < first_guard_index:
                errors.append(f"stopRuntimeAfterConnectionFailure(generation:) must not run {token} before checking generation")
    await_idx = body.find("await screenCapture?.stop()")
    post_await_guard_idx = body.find("guard connectionStopGeneration == generation, !Task.isCancelled else { return }", await_idx)
    clear_idx = body.find("screenCapture = nil", await_idx)
    if -1 in [await_idx, post_await_guard_idx, clear_idx] or not (await_idx < post_await_guard_idx < clear_idx):
        errors.append("stopRuntimeAfterConnectionFailure(generation:) must re-check generation/cancellation after awaited screen capture stop before clearing runtime state")
    if "connectionStopTask?.cancel()" in body:
        errors.append("stopRuntimeAfterConnectionFailure(generation:) must not self-cancel connectionStopTask; only generation-current task may clear its handle")

for name, pattern in [
    ("start", r"func start\(\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func stop"),
    ("stop(cancelPendingRestart:saveTranscriptImmediately:)", r"private func stop\(cancelPendingRestart: Bool, saveTranscriptImmediately: Bool = true\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func requestStart"),
]:
    match = re.search(pattern, text)
    if not match:
        errors.append(f"AppState.{name} not found")
        continue
    body = match.group("body")
    if "connectionStopGeneration = UUID()" not in body:
        errors.append(f"AppState.{name} must invalidate stale connection-failure stop tasks through connectionStopGeneration = UUID()")
    if "connectionStopTask?.cancel()" not in body:
        errors.append(f"AppState.{name} must cancel stale connection-failure stop tasks")

if errors:
    print("Connection stop generation guard verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Connection stop generation guard verification passed")
