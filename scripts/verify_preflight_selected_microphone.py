#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
runner_path = root / "LiveBuddy" / "Services" / "PreflightTestRunner.swift"
runner = runner_path.read_text()
tests_path = root / "LiveBuddyTests" / "PreflightTestTests.swift"
tests = tests_path.read_text()
errors: list[str] = []

if "typealias ProviderCheck = @Sendable (_ apiKey: String) async -> ProviderHealthStatus" not in runner:
    errors.append("Preflight provider checks must receive the apiKey from run(settings:) instead of a captured settings snapshot")

if "typealias AudioSampler = @Sendable (_ selectedDeviceUID: String?, _ analyzer: inout AudioLevelAnalyzer) async throws -> Void" not in runner:
    errors.append("Preflight audio samplers must receive the selected device UID from run(settings:)")

run_provider = re.search(
    r"private func runProvider\(settings: AppSettings, report: PreflightTestReport, update: ReportUpdate\) async -> PreflightTestReport \{(?P<body>[\s\S]*?)\n    \}\n\n    private func runPermissions",
    runner,
)
if not run_provider:
    errors.append("runProvider must accept AppSettings so providerCheck uses the same snapshot as the rest of preflight")
else:
    body = run_provider.group("body")
    if "await providerCheck(settings.apiKey)" not in body:
        errors.append("runProvider must call providerCheck(settings.apiKey)")

run_audio = re.search(
    r"private func runAudioIfNeeded\(settings: AppSettings, report: PreflightTestReport, update: ReportUpdate\) async -> PreflightTestReport \{(?P<body>[\s\S]*?)\n    \}\n\n    private func runAudioStep",
    runner,
)
if not run_audio:
    errors.append("runAudioIfNeeded not found")
else:
    body = run_audio.group("body")
    if "selectedDeviceUID: settings.selectedMicrophoneDeviceUID" not in body:
        errors.append("Microphone preflight must pass settings.selectedMicrophoneDeviceUID into runAudioStep")
    if "selectedDeviceUID: nil" not in body:
        errors.append("Screen preflight should pass nil selectedDeviceUID because it is not microphone-device scoped")

run_audio_step = re.search(
    r"private func runAudioStep\([\s\S]*?\) async -> PreflightTestReport \{(?P<body>[\s\S]*?)\n    \}\n\n    private func runSubtitle",
    runner,
)
if not run_audio_step:
    errors.append("runAudioStep not found")
else:
    body = run_audio_step.group("body")
    if "selectedDeviceUID: String?" not in runner:
        errors.append("runAudioStep must accept selectedDeviceUID")
    if "try await sampler(selectedDeviceUID, &analyzer)" not in body:
        errors.append("runAudioStep must pass selectedDeviceUID to the sampler")

if "providerCheck: { apiKey in" not in runner or "verify(apiKey: apiKey)" not in runner:
    errors.append("Live preflight provider check must use the apiKey supplied by run(settings:)")

if "microphoneSampler: { selectedDeviceUID, analyzer in" not in runner:
    errors.append("Live microphone sampler must accept selectedDeviceUID from the runner")
if "sampleMicrophone(selectedDeviceUID: selectedDeviceUID" not in runner:
    errors.append("Live microphone sampler must forward selectedDeviceUID to sampleMicrophone")
if "private static func sampleMicrophone(selectedDeviceUID: String?" not in runner:
    errors.append("sampleMicrophone must accept selectedDeviceUID directly")
if "try await capture.start(selectedDeviceUID: selectedDeviceUID)" not in runner:
    errors.append("sampleMicrophone must start MicrophoneCapture with the selectedDeviceUID")
if "sampleMicrophone(settings:" in runner:
    errors.append("sampleMicrophone must not capture the whole AppSettings snapshot")

if "runnerPassesSelectedMicrophoneUIDToMicrophoneSampler" not in tests:
    errors.append("PreflightTestTests must cover that the selected microphone UID reaches the sampler")

if errors:
    print("Preflight selected microphone verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Preflight selected microphone verification passed")
