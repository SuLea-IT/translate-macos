#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
errors: list[str] = []

def read(rel: str) -> str:
    return (root / rel).read_text()

settings = read("LiveBuddy/Models/AppSettings.swift")
app_state = read("LiveBuddy/Models/AppState.swift")
audio_devices = read("LiveBuddy/Services/AudioDeviceManager.swift")
player = read("LiveBuddy/Utilities/PCM16AudioPlayer.swift")
settings_view = read("LiveBuddy/Views/Settings/SettingsView.swift")
language = read("LiveBuddy/Models/InterfaceLanguage.swift")

for token in [
    "enum AudioPlaybackMode: String, CaseIterable, Codable, Identifiable",
    "case mediaAndTranslation",
    "case mediaOnly",
    "case translationOnly",
    "var audioPlaybackMode: AudioPlaybackMode = .mediaAndTranslation",
    "var translationAudioOutputDeviceUID: String? = nil",
    "case audioPlaybackMode",
    "case translationAudioOutputDeviceUID",
    "audioPlaybackMode = try container.decodeIfPresent(AudioPlaybackMode.self, forKey: .audioPlaybackMode) ?? defaults.audioPlaybackMode",
    "translationAudioOutputDeviceUID = try container.decodeIfPresent(String.self, forKey: .translationAudioOutputDeviceUID)",
    "try container.encode(audioPlaybackMode, forKey: .audioPlaybackMode)",
    "try container.encodeIfPresent(translationAudioOutputDeviceUID, forKey: .translationAudioOutputDeviceUID)",
]:
    if token not in settings:
        errors.append(f"AppSettings must persist playback isolation through {token}")

for token in [
    "@Published private(set) var availableAudioOutputs: [AudioDevice] = []",
    "refreshAvailableAudioDevices()",
    "availableMicrophones = AudioDeviceManager.getInputDevices()",
    "availableAudioOutputs = AudioDeviceManager.getOutputDevices()",
    "oldValue.audioPlaybackMode != settings.audioPlaybackMode",
    "oldValue.translationAudioOutputDeviceUID != settings.translationAudioOutputDeviceUID",
    "audioPlayer.setOutputDeviceUID(settings.translationAudioOutputDeviceUID)",
    "settings.audioPlaybackMode.allowsTranslatedAudio",
    "settings.audioPlaybackMode == .translationOnly",
]:
    if token not in app_state:
        errors.append(f"AppState must wire playback isolation through {token}")

for token in [
    "static func getOutputDevices() -> [AudioDevice]",
    "getDevices(scope: kAudioDevicePropertyScopeOutput)",
    "static func getInputDeviceID(for uid: String) -> AudioDeviceID?",
    "static func getOutputDeviceID(for uid: String) -> AudioDeviceID?",
    "static func hasBlackHoleDevice(in devices: [AudioDevice]) -> Bool",
    "localizedCaseInsensitiveContains(\"BlackHole\")",
]:
    if token not in audio_devices:
        errors.append(f"AudioDeviceManager must support output routing and BlackHole detection through {token}")

for token in [
    "nonisolated func setOutputDeviceUID(_ uid: String?)",
    "private nonisolated func applyOutputDeviceIfNeeded() throws",
    "AudioDeviceManager.getOutputDeviceID(for: uid)",
    "kAudioOutputUnitProperty_CurrentDevice",
    "AudioUnitSetProperty",
    "engine.outputNode.audioUnit",
    "selectedOutputDeviceUID",
    "appliedOutputDeviceUID",
]:
    if token not in player:
        errors.append(f"PCM16AudioPlayer must route translated audio to a selected output device through {token}")

for token in [
    "Picker(appState.t(.audioPlaybackMode), selection: appState.binding(\\.audioPlaybackMode))",
    "ForEach(AudioPlaybackMode.allCases)",
    "Picker(appState.t(.translationAudioOutput), selection: appState.binding(\\.translationAudioOutputDeviceUID))",
    "ForEach(appState.availableAudioOutputs)",
    "appState.refreshAvailableAudioDevices()",
    "translationOnlySetupMessage",
]:
    if token not in settings_view:
        errors.append(f"SettingsView must expose playback isolation controls through {token}")

for token in [
    "case audioPlaybackMode",
    "case playbackMediaAndTranslation",
    "case playbackMediaOnly",
    "case playbackTranslationOnly",
    "case translationAudioOutput",
    "case systemDefaultOutput",
    "case translationOnlySetupMessage",
    "case blackHoleNotDetected",
    "case blackHoleDetected",
]:
    if token not in language:
        errors.append(f"InterfaceLanguage must localize playback isolation through {token}")

if errors:
    print("Audio playback isolation mode verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Audio playback isolation mode verification passed")
