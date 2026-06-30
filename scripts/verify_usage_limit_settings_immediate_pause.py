#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
usage_path = root / "LiveBuddy" / "Models" / "UsageControl.swift"
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
usage = usage_path.read_text()
app_state = app_state_path.read_text()
tests = (root / "LiveBuddyTests" / "UsageControlTests.swift").read_text()
errors: list[str] = []

if "private func currentLimitReason() -> UsageControlPauseReason?" not in usage:
    errors.append("UsageControlEngine must centralize already-over-limit detection in currentLimitReason()")

settings_match = re.search(
    r"mutating func reevaluatePauseAfterSettingsChange\(now: Date\) -> UsageControlDecision \{(?P<body>[\s\S]*?)\n    \}\n\n    mutating func resetSession",
    usage,
)
if not settings_match:
    errors.append("UsageControlEngine.reevaluatePauseAfterSettingsChange(now:) not found")
else:
    body = settings_match.group("body")
    for token in [
        "if let limitReason = currentLimitReason()",
        "pausedReason = limitReason",
        "refreshSnapshot(runtimeState: .paused(reason: limitReason))",
        "return .pause(limitReason)",
    ]:
        if token not in body:
            errors.append(f"Settings changes must immediately pause when the current usage already exceeds a new limit through {token}")
    guard_idx = body.find("guard let pausedReason else")
    limit_idx = body.find("if let limitReason = currentLimitReason()")
    if -1 in [guard_idx, limit_idx] or not (limit_idx < guard_idx):
        errors.append("Already-over-limit detection must run before the not-paused early return")

app_match = re.search(
    r"private func updateUsageControlSettings\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func enterUsagePause",
    app_state,
)
if not app_match:
    errors.append("AppState.updateUsageControlSettings() not found")
else:
    body = app_match.group("body")
    for token in [
        "if let pauseReason = decision.pauseReason",
        "enterUsagePause(reason: pauseReason)",
        "updateRunningUsageStatus(now: now, force: true)",
        "return",
    ]:
        if token not in body:
            errors.append(f"AppState must apply usage-limit pause decisions immediately after settings change through {token}")
    pause_idx = body.find("if let pauseReason = decision.pauseReason")
    resume_idx = body.find("if isRunning, decision.shouldResume")
    if -1 in [pause_idx, resume_idx] or not (pause_idx < resume_idx):
        errors.append("AppState must handle immediate pause decisions before resume decisions")


if "settingsChangePausesImmediatelyWhenCurrentSessionAlreadyExceedsNewLimit" not in tests:
    errors.append("UsageControlTests must cover immediate pause after lowering the active session limit below already-sent usage")

if errors:
    print("Usage limit settings immediate pause verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Usage limit settings immediate pause verification passed")
