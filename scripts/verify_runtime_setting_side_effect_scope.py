#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

did_set_match = re.search(r"@Published private\(set\) var settings: AppSettings \{\n        didSet \{(?P<body>[\s\S]*?)\n        \}\n    \}", text)
if not did_set_match:
    errors.append("AppState.settings didSet not found")
else:
    body = did_set_match.group("body")
    for token in [
        "updateAudioPlayerVolumeIfNeeded(oldValue: oldValue)",
        "updateUsageControlSettingsIfNeeded(oldValue: oldValue)",
        "refreshSetupChecklistIfNeeded(oldValue: oldValue)",
    ]:
        if token not in body:
            errors.append(f"settings didSet must scope runtime side effects through {token}")
    for token in ["updateAudioPlayerVolume()", "updateUsageControlSettings()"]:
        if token in body:
            errors.append(f"settings didSet must not run {token} for unrelated settings changes")

audio_match = re.search(r"private func updateAudioPlayerVolumeIfNeeded\(oldValue: AppSettings\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func updateAudioPlayerVolume", text)
if not audio_match:
    errors.append("AppState.updateAudioPlayerVolumeIfNeeded(oldValue:) not found")
else:
    body = audio_match.group("body")
    for token in [
        "oldValue.audioPlayerVolume != settings.audioPlayerVolume",
        "oldValue.audioPlayerMuted != settings.audioPlayerMuted",
        "oldValue.audioPlaybackMode != settings.audioPlaybackMode",
        "oldValue.translationAudioOutputDeviceUID != settings.translationAudioOutputDeviceUID",
        "guard audioOutputChanged else { return }",
        "updateAudioPlayerVolume()",
    ]:
        if token not in body:
            errors.append(f"audio player volume updates must be scoped through {token}")

usage_match = re.search(r"private func updateUsageControlSettingsIfNeeded\(oldValue: AppSettings\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func updateUsageControlSettings", text)
if not usage_match:
    errors.append("AppState.updateUsageControlSettingsIfNeeded(oldValue:) not found")
else:
    body = usage_match.group("body")
    for token in [
        "oldValue.usageControls != settings.usageControls",
        "guard usageControlsChanged else { return }",
        "updateUsageControlSettings()",
    ]:
        if token not in body:
            errors.append(f"usage control updates must be scoped through {token}")

# The actual effect methods should still exist for initialization and scoped helpers.
for token in [
    "private func updateAudioPlayerVolume()",
    "private func updateUsageControlSettings()",
    "usageEngine.updateSettings(settings.usageControls, now: now)",
    "let volume = settings.audioPlaybackMode.allowsTranslatedAudio && !settings.audioPlayerMuted ? settings.audioPlayerVolume : 0.0",
]:
    if token not in text:
        errors.append(f"AppState must keep runtime effect implementation through {token}")

if errors:
    print("Runtime setting side-effect scope verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Runtime setting side-effect scope verification passed")
