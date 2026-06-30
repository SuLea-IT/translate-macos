#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
preflight_path = root / "LiveBuddy" / "Models" / "PreflightTest.swift"
runner_path = root / "LiveBuddy" / "Services" / "PreflightTestRunner.swift"
settings_path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
interface_path = root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift"
tests_path = root / "LiveBuddyTests" / "PreflightTestTests.swift"
preflight = preflight_path.read_text()
runner = runner_path.read_text()
settings = settings_path.read_text()
interface = interface_path.read_text()
tests = tests_path.read_text()
errors: list[str] = []

required_keys = [
    "preflightCheckingAPIKey",
    "preflightAPIKeyValid",
    "preflightAPIKeyMissing",
    "preflightAPIKeyNotVerified",
    "preflightCheckingPermissions",
    "preflightPermissionsAvailable",
    "preflightPermissionsMissing",
    "preflightNotNeededForAudioSource",
    "preflightSamplingAudio",
    "preflightNoAudioCaptured",
    "preflightShowingSubtitleTest",
    "preflightSubtitleWindowShown",
]

for key in required_keys:
    if f"case {key}" not in interface:
        errors.append(f"InterfaceText must include {key}")
    if interface.count(f".{key}:") < 8:
        errors.append(f"InterfaceText.{key} must be translated for every supported language")

for token in [
    "var messageKey: InterfaceText?",
    "messageKey: InterfaceText? = nil",
    "self.messageKey = messageKey",
    "func updating(_ id: PreflightTestStepID, state: PreflightTestStepState, messageKey: InterfaceText, audio: AudioLevelSummary? = nil)",
]:
    if token not in preflight:
        errors.append(f"PreflightTestStep/Report must carry localizable message keys through {token}")

for old in [
    'message: "Checking API key"',
    'message: "API key is valid"',
    'message: "API key is missing"',
    'message: "API key was not verified"',
    'message: "Checking permissions"',
    'message: "Required permissions are available"',
    'message: checklist.blockingIssues.map(\\.rawValue).joined(separator: ", ")',
    'message: "Not needed for selected audio source"',
    'message: "Sampling audio"',
    'message: "No audio samples were captured"',
    'message: "Audio clipping detected"',
    'message: "Audio is too quiet"',
    'message: "Audio detected"',
    'message: "Showing subtitle test"',
    'message: "Subtitle window test shown"',
]:
    if old in runner:
        errors.append(f"PreflightTestRunner must not hard-code fixed user-visible message {old}")

for token in [
    "messageKey: .preflightCheckingAPIKey",
    "messageKey: .preflightAPIKeyValid",
    "messageKey: .preflightAPIKeyMissing",
    "messageKey: .preflightAPIKeyNotVerified",
    "messageKey: .preflightCheckingPermissions",
    "messageKey: .preflightPermissionsAvailable",
    "messageKey: .preflightPermissionsMissing",
    "messageKey: .preflightNotNeededForAudioSource",
    "messageKey: .preflightSamplingAudio",
    "messageKey: .preflightNoAudioCaptured",
    "messageKey: .audioClippingDetected",
    "messageKey: .audioTooQuiet",
    "messageKey: .audioDetected",
    "messageKey: .preflightShowingSubtitleTest",
    "messageKey: .preflightSubtitleWindowShown",
]:
    if token not in runner:
        errors.append(f"PreflightTestRunner must publish localized fixed status through {token}")

row_match = re.search(r"private struct PreflightTestStepRow: View \{(?P<body>[\s\S]*?)\n\}", settings)
if not row_match:
    errors.append("PreflightTestStepRow not found")
else:
    body = row_match.group("body")
    for token in [
        "if !messageText.isEmpty {",
        "Text(messageText)",
        "private var messageText: String",
        "if let key = step.messageKey",
        "return language.localized(key)",
        "return step.message",
    ]:
        if token not in body:
            errors.append(f"PreflightTestStepRow must render localized message keys with fallback through {token}")
    if "Text(step.message)" in body:
        errors.append("PreflightTestStepRow must not render step.message directly when messageKey is available")

for token in [
    "runnerPublishesMessageKeysForFixedStatuses",
    "#expect(report.steps.first { $0.id == .apiKey }?.messageKey == .preflightAPIKeyValid)",
    "#expect(report.steps.first { $0.id == .microphoneAudio }?.messageKey == .audioDetected)",
]:
    if token not in tests:
        errors.append(f"PreflightTestTests must cover fixed message keys through {token}")

if errors:
    print("Preflight message localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Preflight message localization verification passed")
