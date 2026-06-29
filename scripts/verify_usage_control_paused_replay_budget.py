#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
usage_path = root / "LiveBuddy" / "Models" / "UsageControl.swift"
text = usage_path.read_text()
errors = []

helper_match = re.search(r"private mutating func resumeReplayIfAllowed\(\) -> UsageControlDecision \{(?P<body>[\s\S]*?)\n    \}\n\n    private var replayBuffer", text)
if not helper_match:
    errors.append("UsageControlEngine must centralize paused replay budget checks in resumeReplayIfAllowed()")
else:
    body = helper_match.group("body")
    for token in [
        "let replayDuration = replayBufferDuration",
        "if let limitReason = limitReasonIfSending(replayDuration)",
        "pausedReason = limitReason",
        "refreshSnapshot(runtimeState: .paused(reason: limitReason))",
        "return .hold",
        "let replay = replayBuffer",
        "refreshSnapshot(runtimeState: .resuming)",
        "return .resume(replayChunks: replay)",
    ]:
        if token not in body:
            errors.append(f"resumeReplayIfAllowed must enforce the full replay budget through {token}")

paused_match = re.search(r"if let pausedReason \{(?P<body>[\s\S]*?)\n        \}\n\n        appendPreroll", text)
if not paused_match:
    errors.append("UsageControlEngine.ingest paused branch not found")
else:
    body = paused_match.group("body")
    for token in [
        "appendPaused(chunk)",
        "if speechActive {",
        "return resumeReplayIfAllowed()",
        "refreshSnapshot(runtimeState: .paused(reason: pausedReason))",
        "return .hold",
    ]:
        if token not in body:
            errors.append(f"ingest paused branch must resume only through full replay budget checks via {token}")
    if "limitReasonIfSending(chunk.duration)" in body:
        errors.append("ingest paused branch must not decide resume safety from only the current chunk duration")
    if "pausedReason == .idle ||" in body:
        errors.append("ingest paused branch must not let idle resume bypass usage limits")
    resume_idx = body.find("return resumeReplayIfAllowed()")
    hold_idx = body.find("return .hold")
    if min(resume_idx, hold_idx) != -1 and not (resume_idx < hold_idx):
        errors.append("ingest paused branch must try budgeted resume before falling back to hold")

settings_match = re.search(r"mutating func reevaluatePauseAfterSettingsChange\(now: Date\) -> UsageControlDecision \{(?P<body>[\s\S]*?)\n    \}\n\n    mutating func resetSession", text)
if not settings_match:
    errors.append("reevaluatePauseAfterSettingsChange body not found")
else:
    body = settings_match.group("body")
    if "return resumeFromSettingsChange()" in body:
        errors.append("settings-change resume must use the same replay budget gate as speech resume")
    if body.count("return resumeReplayIfAllowed()") < 2:
        errors.append("settings-change resume must use resumeReplayIfAllowed() for lifted idle and lifted usage limits")

if errors:
    print("Usage control paused replay budget verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Usage control paused replay budget verification passed")
