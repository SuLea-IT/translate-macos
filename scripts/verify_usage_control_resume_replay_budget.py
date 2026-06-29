#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
usage_path = root / "LiveBuddy" / "Models" / "UsageControl.swift"
text = usage_path.read_text()
errors = []

for token in [
    "private var replayBuffer: [BufferedAudioChunk]",
    "private var replayBufferDuration: TimeInterval",
    "let replayDuration = replayBufferDuration",
    "if let limitReason = limitReasonIfSending(replayDuration)",
    "private mutating func resumeReplayIfAllowed() -> UsageControlDecision",
]:
    if token not in text:
        errors.append(f"UsageControlEngine must evaluate the whole buffered replay budget through {token}")

reevaluate_match = re.search(r"mutating func reevaluatePauseAfterSettingsChange\(now: Date\) -> UsageControlDecision \{(?P<body>[\s\S]*?)\n    \}\n\n    mutating func resetSession", text)
if not reevaluate_match:
    errors.append("reevaluatePauseAfterSettingsChange body not found")
else:
    body = reevaluate_match.group("body")
    if "pausedBuffer.first?.duration" in body:
        errors.append("reevaluatePauseAfterSettingsChange must not resume based only on the first paused chunk")
    if "return resumeReplayIfAllowed()" not in body:
        errors.append("reevaluatePauseAfterSettingsChange must resume through the shared full replay budget gate")
    if "limitReasonIfSending(chunk.duration)" in body or "pausedBuffer.first?.duration" in body:
        errors.append("reevaluatePauseAfterSettingsChange must not decide resume safety from partial buffered audio")

resume_match = re.search(r"private mutating func resumeReplayIfAllowed\(\) -> UsageControlDecision \{(?P<body>[\s\S]*?)\n    \}\n\n    private var replayBuffer", text)
if not resume_match:
    errors.append("resumeReplayIfAllowed body not found")
else:
    body = resume_match.group("body")
    replay_duration_idx = body.find("let replayDuration = replayBufferDuration")
    limit_idx = body.find("if let limitReason = limitReasonIfSending(replayDuration)")
    paused_idx = body.find("pausedReason = limitReason", limit_idx)
    hold_idx = body.find("return .hold", paused_idx)
    replay_idx = body.find("let replay = replayBuffer", hold_idx)
    resume_idx = body.find("return .resume(replayChunks: replay)", replay_idx)
    if min(replay_duration_idx, limit_idx, paused_idx, hold_idx, replay_idx, resume_idx) != -1 and not (
        replay_duration_idx < limit_idx < paused_idx < hold_idx < replay_idx < resume_idx
    ):
        errors.append("resumeReplayIfAllowed must gate full replay duration before returning replay chunks")
    if "let replay = replayBuffer" not in body:
        errors.append("resumeReplayIfAllowed must use the same replayBuffer that budget checks use")

if errors:
    print("Usage control replay budget verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Usage control replay budget verification passed")
