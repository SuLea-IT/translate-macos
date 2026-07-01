#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Utilities" / "PCM16AudioPlayer.swift"
text = path.read_text()
errors: list[str] = []

for token in [
    "private let maxPendingPlaybackBuffers",
    "private var pendingPlaybackBuffers",
    "private var playbackGeneration",
]:
    if token not in text:
        errors.append(f"PCM16AudioPlayer must bound queued playback state through {token}")

stop_match = re.search(r"nonisolated func stop\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    nonisolated func setVolume", text)
if not stop_match:
    errors.append("PCM16AudioPlayer.stop() not found")
else:
    body = stop_match.group("body")
    if "self.stopOnPlaybackQueue()" not in body:
        errors.append("PCM16AudioPlayer.stop() must clear queued playback through stopOnPlaybackQueue()")

stop_helper_match = re.search(r"private nonisolated func stopOnPlaybackQueue\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private nonisolated func teardownPlaybackResources", text)
if not stop_helper_match:
    errors.append("PCM16AudioPlayer.stopOnPlaybackQueue() not found")
else:
    body = stop_helper_match.group("body")
    for token in ["playbackGeneration = UUID()", "pendingPlaybackBuffers = 0", "player.reset()"]:
        if token not in body:
            errors.append(f"PCM16AudioPlayer.stopOnPlaybackQueue() must clear queued playback through {token}")

enqueue_match = re.search(r"private nonisolated func enqueue\(_ data: Data, sampleRate: Double\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private nonisolated func prepare", text)
if not enqueue_match:
    errors.append("PCM16AudioPlayer.enqueue(_:sampleRate:) not found")
else:
    body = enqueue_match.group("body")
    for token in [
        "guard pendingPlaybackBuffers < maxPendingPlaybackBuffers else {",
        "notifyPlaybackDrop(.backlogLimit(maxPendingPlaybackBuffers))",
        "pendingPlaybackBuffers += 1",
        "let generation = playbackGeneration",
        "player.scheduleBuffer(buffer, completionHandler:",
        "completionHandler:",
        "finishBufferPlayback(generation: generation)",
    ]:
        if token not in body:
            errors.append(f"PCM16AudioPlayer.enqueue must apply playback backpressure through {token}")
    guard_idx = body.find("guard pendingPlaybackBuffers < maxPendingPlaybackBuffers else {")
    increment_idx = body.find("pendingPlaybackBuffers += 1")
    schedule_idx = body.find("player.scheduleBuffer(buffer")
    if min(guard_idx, increment_idx, schedule_idx) != -1 and not (guard_idx < increment_idx < schedule_idx):
        errors.append("PCM16AudioPlayer.enqueue must check the playback queue before incrementing and scheduling")

finish_match = re.search(r"private nonisolated func finishBufferPlayback\(generation: UUID\) \{(?P<body>[\s\S]*?)\n    \}\n", text)
if not finish_match:
    errors.append("PCM16AudioPlayer must decrement queued buffer count from a finishBufferPlayback helper")
else:
    body = finish_match.group("body")
    for token in ["queue.async", "guard self.playbackGeneration == generation else { return }", "max(0, self.pendingPlaybackBuffers - 1)"]:
        if token not in body:
            errors.append(f"PCM16AudioPlayer.finishBufferPlayback must safely decrement pending buffers through {token}")

deinit_match = re.search(r"deinit \{(?P<body>[\s\S]*?)\n    \}\n\n    nonisolated func playPCM16", text)
if not deinit_match:
    errors.append("PCM16AudioPlayer.deinit not found")
else:
    body = deinit_match.group("body")
    if "teardownPlaybackResources()" not in body:
        errors.append("PCM16AudioPlayer.deinit must release queued playback through serialized teardownPlaybackResources()")

teardown_match = re.search(r"private nonisolated func teardownPlaybackResources\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private nonisolated func finishBufferPlayback", text)
if not teardown_match:
    errors.append("PCM16AudioPlayer.teardownPlaybackResources() not found")
else:
    body = teardown_match.group("body")
    for token in ["stopOnPlaybackQueue()", "isShuttingDown = true"]:
        if token not in body:
            errors.append(f"PCM16AudioPlayer.teardownPlaybackResources() must release queued playback through {token}")

if errors:
    print("Audio player backpressure verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Audio player backpressure verification passed")
