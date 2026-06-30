#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Utilities" / "PCM16AudioPlayer.swift"
text = path.read_text()
errors: list[str] = []

for token in [
    "private static let playbackQueueKey = DispatchSpecificKey<Bool>()",
    "private static let playbackQueueValue = true",
    "nonisolated(unsafe) private var isShuttingDown = false",
    "init() {",
    "queue.setSpecific(key: Self.playbackQueueKey, value: Self.playbackQueueValue)",
]:
    if token not in text:
        errors.append(f"PCM16AudioPlayer must mark its serial queue and shutdown state through {token}")

deinit_match = re.search(r"deinit \{(?P<body>[\s\S]*?)\n    \}\n\n    nonisolated func playPCM16", text)
if not deinit_match:
    errors.append("PCM16AudioPlayer.deinit not found")
else:
    body = deinit_match.group("body")
    for token in [
        "DispatchQueue.getSpecific(key: Self.playbackQueueKey) == Self.playbackQueueValue",
        "teardownPlaybackResources()",
        "queue.sync",
    ]:
        if token not in body:
            errors.append(f"PCM16AudioPlayer.deinit must serialize teardown with queued playback work through {token}")
    if "player.stop()" in body or "engine.stop()" in body:
        errors.append("PCM16AudioPlayer.deinit must not bypass the serialized teardown helper")

for name, pattern, required in [
    (
        "stopOnPlaybackQueue",
        r"private nonisolated func stopOnPlaybackQueue\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private nonisolated func teardownPlaybackResources",
        ["playbackGeneration = UUID()", "pendingPlaybackBuffers = 0", "player.stop()", "player.reset()", "engine.stop()", "isPrepared = false"],
    ),
    (
        "teardownPlaybackResources",
        r"private nonisolated func teardownPlaybackResources\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private nonisolated func finishBufferPlayback",
        ["isShuttingDown = true", "stopOnPlaybackQueue()", "if isAttached", "engine.detach(player)", "isAttached = false"],
    ),
]:
    match = re.search(pattern, text)
    if not match:
        errors.append(f"PCM16AudioPlayer.{name}() not found")
    else:
        body = match.group("body")
        for token in required:
            if token not in body:
                errors.append(f"PCM16AudioPlayer.{name} must close playback lifecycle through {token}")

stop_match = re.search(r"nonisolated func stop\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    nonisolated func setVolume", text)
if not stop_match:
    errors.append("PCM16AudioPlayer.stop() not found")
else:
    body = stop_match.group("body")
    if "self.stopOnPlaybackQueue()" not in body:
        errors.append("PCM16AudioPlayer.stop() should reuse the queue-confined stop helper")

for method_name, pattern in [
    ("enqueue", r"private nonisolated func enqueue\(_ data: Data, sampleRate: Double\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private nonisolated func prepare"),
    ("setVolume", r"nonisolated func setVolume\(_ volume: Float\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private nonisolated func enqueue"),
]:
    match = re.search(pattern, text)
    if not match:
        errors.append(f"PCM16AudioPlayer.{method_name} not found")
    elif "guard !isShuttingDown else { return }" not in match.group("body"):
        errors.append(f"PCM16AudioPlayer.{method_name} must ignore queued work after teardown starts")

if errors:
    print("Audio player shutdown serialization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Audio player shutdown serialization verification passed")
