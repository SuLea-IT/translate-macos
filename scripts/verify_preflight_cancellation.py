#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
runner_path = root / "LiveBuddy" / "Services" / "PreflightTestRunner.swift"
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
runner = runner_path.read_text()
app_state = app_state_path.read_text()
errors: list[str] = []

if "private var preflightTestTask: Task<Void, Never>?" not in app_state or "preflightTestTask?.cancel()" not in app_state:
    errors.append("AppState must retain and cancel preflightTestTask before runner cancellation can be reliable")

cancel_guard = "guard !Task.isCancelled else { return report }"
if runner.count(cancel_guard) < 8:
    errors.append("PreflightTestRunner must stop progressing between cancelled stages with repeated Task.isCancelled guards")

run_match = re.search(r"func run\(settings: AppSettings, update: @escaping ReportUpdate\) async -> PreflightTestReport \{(?P<body>[\s\S]*?)\n    \}\n\n    private func runProvider", runner)
if not run_match:
    errors.append("PreflightTestRunner.run(settings:update:) not found")
else:
    body = run_match.group("body")
    for step in ["runProvider", "runPermissions", "runAudioIfNeeded", "runSubtitle"]:
        idx = body.find(f"report = await {step}")
        guard_idx = body.find(cancel_guard, idx)
        if idx == -1 or guard_idx == -1:
            errors.append(f"PreflightTestRunner.run must check cancellation immediately after {step}")
    final_idx = body.find("report.finishedAt = Date()")
    last_guard_idx = body.rfind(cancel_guard, 0, final_idx)
    if final_idx == -1 or last_guard_idx == -1:
        errors.append("PreflightTestRunner.run must check cancellation before publishing finishedAt")

provider_match = re.search(r"private func runProvider\(.*?\) async -> PreflightTestReport \{(?P<body>[\s\S]*?)\n    \}\n\n    private func runPermissions", runner)
if not provider_match:
    errors.append("PreflightTestRunner.runProvider not found")
else:
    body = provider_match.group("body")
    status_idx = body.find("let status = await providerCheck()")
    guard_idx = body.find(cancel_guard, status_idx)
    if status_idx == -1 or guard_idx == -1:
        errors.append("PreflightTestRunner.runProvider must ignore provider results if the task was cancelled")

permissions_match = re.search(r"private func runPermissions\(.*?\) async -> PreflightTestReport \{(?P<body>[\s\S]*?)\n    \}\n\n    private func runAudioIfNeeded", runner)
if not permissions_match:
    errors.append("PreflightTestRunner.runPermissions not found")
else:
    body = permissions_match.group("body")
    permissions_idx = body.find("let permissions = await permissionCheck()")
    guard_idx = body.find(cancel_guard, permissions_idx)
    if permissions_idx == -1 or guard_idx == -1:
        errors.append("PreflightTestRunner.runPermissions must ignore permission results if the task was cancelled")

run_audio_match = re.search(r"private func runAudioIfNeeded\(.*?\) async -> PreflightTestReport \{(?P<body>[\s\S]*?)\n    \}\n\n    private func runAudioStep", runner)
if not run_audio_match:
    errors.append("PreflightTestRunner.runAudioIfNeeded not found")
else:
    body = run_audio_match.group("body")
    mic_idx = body.find(".microphoneAudio")
    screen_idx = body.find(".screenAudio")
    if mic_idx == -1 or body.find(cancel_guard, mic_idx, screen_idx if screen_idx != -1 else len(body)) == -1:
        errors.append("PreflightTestRunner.runAudioIfNeeded must check cancellation between microphone and screen sampling")

run_audio_step_match = re.search(r"private func runAudioStep\([\s\S]*?\) async -> PreflightTestReport \{(?P<body>[\s\S]*?)\n    \}\n\n    private func runSubtitle", runner)
if not run_audio_step_match:
    errors.append("PreflightTestRunner.runAudioStep not found")
else:
    body = run_audio_step_match.group("body")
    sampler_idx = body.find("try await sampler(&analyzer)")
    guard_before = body.rfind(cancel_guard, 0, sampler_idx)
    guard_after = body.find(cancel_guard, sampler_idx)
    if sampler_idx == -1 or guard_before == -1:
        errors.append("PreflightTestRunner.runAudioStep must check cancellation before starting a sampler")
    if sampler_idx == -1 or guard_after == -1:
        errors.append("PreflightTestRunner.runAudioStep must check cancellation after sampler completion")
    if "catch is CancellationError" not in body or "return report" not in body:
        errors.append("PreflightTestRunner.runAudioStep must treat CancellationError as cancellation, not as a failed audio test")

subtitle_match = re.search(r"private func runSubtitle\(.*?\) async -> PreflightTestReport \{(?P<body>[\s\S]*?)\n    \}\n\}", runner)
if not subtitle_match:
    errors.append("PreflightTestRunner.runSubtitle not found")
else:
    body = subtitle_match.group("body")
    subtitle_idx = body.find("await subtitleCheck()")
    if subtitle_idx == -1 or body.rfind(cancel_guard, 0, subtitle_idx) == -1 or body.find(cancel_guard, subtitle_idx) == -1:
        errors.append("PreflightTestRunner.runSubtitle must check cancellation before and after the subtitle test")

for name in ["sampleMicrophone", "sampleScreen"]:
    match = re.search(rf"private static func {name}\([\s\S]*?\) async throws \{{(?P<body>[\s\S]*?)\n    \}}", runner)
    if not match:
        errors.append(f"PreflightTestRunner.{name} not found")
        continue
    body = match.group("body")
    start_idx = body.find("try await capture.start")
    first_check = body.find("try Task.checkCancellation()")
    second_check = body.find("try Task.checkCancellation()", start_idx)
    if first_check == -1 or start_idx == -1 or first_check > start_idx:
        errors.append(f"PreflightTestRunner.{name} must check cancellation before starting capture")
    if start_idx == -1 or second_check == -1:
        errors.append(f"PreflightTestRunner.{name} must check cancellation after capture starts so cancellation stops the device immediately")
    if "catch" not in body or ("capture.stop()" not in body and "await capture.stop()" not in body):
        errors.append(f"PreflightTestRunner.{name} must stop capture when sleep/cancellation throws")

if errors:
    print("Preflight cancellation verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Preflight cancellation verification passed")
