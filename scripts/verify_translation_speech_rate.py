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
player = read("LiveBuddy/Utilities/PCM16AudioPlayer.swift")
settings_view = read("LiveBuddy/Views/Settings/SettingsView.swift")
caption_view = read("LiveBuddy/Views/Caption/CaptionView.swift")
language = read("LiveBuddy/Models/InterfaceLanguage.swift")

for token in [
    "static let translationSpeechRateRange: ClosedRange<Double> = 1.0...1.6",
    "static let defaultTranslationSpeechRate = 1.0",
    "var translationSpeechRate: Double = Self.defaultTranslationSpeechRate",
    "case translationSpeechRate",
    "translationSpeechRate = Self.clampedTranslationSpeechRate(try container.decodeIfPresent(Double.self, forKey: .translationSpeechRate) ?? defaults.translationSpeechRate)",
    "try container.encode(translationSpeechRate, forKey: .translationSpeechRate)",
    "static func clampedTranslationSpeechRate(_ rate: Double) -> Double",
]:
    if token not in settings:
        errors.append(f"AppSettings must persist and clamp translated speech rate through {token}")

for token in [
    "oldValue.translationSpeechRate != settings.translationSpeechRate",
    "audioPlayer.setPlaybackRate(Float(settings.translationSpeechRate))",
]:
    if token not in app_state:
        errors.append(f"AppState must apply speech rate changes through {token}")

for token in [
    "nonisolated(unsafe) private let timePitch = AVAudioUnitTimePitch()",
    "nonisolated(unsafe) private var playbackRate: Float = Float(AppSettings.defaultTranslationSpeechRate)",
    "nonisolated func setPlaybackRate(_ rate: Float)",
    "timePitch.rate = playbackRate",
    "engine.attach(timePitch)",
    "engine.connect(player, to: timePitch, format: format)",
    "engine.connect(timePitch, to: engine.mainMixerNode, format: format)",
    "engine.detach(timePitch)",
]:
    if token not in player:
        errors.append(f"PCM16AudioPlayer must speed translated audio without pitch shift through {token}")

for token in [
    "Text(appState.t(.translationSpeechRate))",
    "Slider(value: appState.binding(\\.translationSpeechRate), in: AppSettings.translationSpeechRateRange, step: 0.05)",
    "appState.formattedTranslationSpeechRate",
]:
    if token not in settings_view:
        errors.append(f"SettingsView must expose translated speech rate through {token}")

for token in [
    "Image(systemName: \"speedometer\")",
    "Slider(value: appState.binding(\\.translationSpeechRate), in: AppSettings.translationSpeechRateRange, step: 0.05)",
    "appState.formattedTranslationSpeechRate",
]:
    if token not in caption_view:
        errors.append(f"Caption popup must expose quick speech rate control through {token}")

for token in [
    "case translationSpeechRate",
    ".translationSpeechRate: \"Translated voice speed\"",
    ".translationSpeechRate: \"翻译语音语速\"",
]:
    if token not in language:
        errors.append(f"InterfaceLanguage must localize speech rate through {token}")

if "var formattedTranslationSpeechRate: String" not in app_state:
    errors.append("AppState must expose formattedTranslationSpeechRate for compact UI labels")

if errors:
    print("Translation speech rate verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Translation speech rate verification passed")
