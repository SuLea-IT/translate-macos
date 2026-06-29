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
    "limitReasonIfSending(replayDuration) == nil",
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
    replay_idx = body.find("let replayDuration = replayBufferDuration")
    limit_idx = body.find("limitReasonIfSending(replayDuration) == nil")
    resume_idx = body.find("return resumeFromSettingsChange()", limit_idx)
    if min(replay_idx, limit_idx, resume_idx) != -1 and not (replay_idx < limit_idx < resume_idx):
        errors.append("reevaluatePauseAfterSettingsChange must compute full replay duration before deciding to resume")

resume_match = re.search(r"private mutating func resumeFromSettingsChange\(\) -> UsageControlDecision \{(?P<body>[\s\S]*?)\n    \}\n\n    private mutating func updateSpeechState", text)
if not resume_match:
    errors.append("resumeFromSettingsChange body not found")
else:
    body = resume_match.group("body")
    if "let replay = replayBuffer" not in body:
        errors.append("resumeFromSettingsChange must use the same replayBuffer that budget checks use")

if errors:
    print("Usage control replay budget verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Usage control replay budget verification passed")
