#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
usage_path = root / "LiveBuddy" / "Models" / "UsageControl.swift"
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
usage_text = usage_path.read_text()
app_state_text = app_state_path.read_text()
errors = []

for token in [
    "mutating func reevaluatePauseAfterSettingsChange(now: Date) -> UsageControlDecision",
    "guard let pausedReason else {",
    "case .idle:",
    "guard settings.idleAutoPauseEnabled else {",
    "return resumeFromSettingsChange()",
    "case .sessionLimit, .dailyLimit:",
    "limitReasonIfSending(nextBufferedDuration) == nil",
    "private mutating func resumeFromSettingsChange() -> UsageControlDecision",
    "let replay = prerollBuffer + pausedBuffer",
    "refreshSnapshot(runtimeState: .resuming)",
    "return .resume(replayChunks: replay)",
]:
    if token not in usage_text:
        errors.append(f"UsageControlEngine must resume paused sessions after settings changes through {token}")

method_match = re.search(r"private func updateUsageControlSettings\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func enterUsagePause", app_state_text)
if not method_match:
    errors.append("AppState.updateUsageControlSettings() not found")
else:
    body = method_match.group("body")
    for token in [
        "let now = Date()",
        "usageEngine.updateSettings(settings.usageControls, now: now)",
        "let decision = usageEngine.reevaluatePauseAfterSettingsChange(now: now)",
        "usageSnapshot = usageEngine.snapshot",
        "if isRunning, decision.shouldResume {",
        "scheduleUsageResume(replayChunks: decision.replayChunks)",
        "updateRunningUsageStatus(now: now, force: true)",
    ]:
        if token not in body:
            errors.append(f"AppState.updateUsageControlSettings must reconnect when changed settings lift a pause through {token}")
    update_idx = body.find("usageEngine.updateSettings(settings.usageControls, now: now)")
    reevaluate_idx = body.find("usageEngine.reevaluatePauseAfterSettingsChange(now: now)")
    snapshot_idx = body.find("usageSnapshot = usageEngine.snapshot")
    resume_idx = body.find("scheduleUsageResume(replayChunks: decision.replayChunks)")
    if min(update_idx, reevaluate_idx, snapshot_idx, resume_idx) != -1 and not (update_idx < reevaluate_idx < snapshot_idx < resume_idx):
        errors.append("AppState.updateUsageControlSettings must update settings, reevaluate pause, publish snapshot, then resume")

if errors:
    print("Usage control settings resume verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Usage control settings resume verification passed")
