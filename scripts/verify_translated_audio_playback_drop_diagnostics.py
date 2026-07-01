#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
errors: list[str] = []

def read(rel: str) -> str:
    return (root / rel).read_text()

player = read("LiveBuddy/Utilities/PCM16AudioPlayer.swift")
app_state = read("LiveBuddy/Models/AppState.swift")
language = read("LiveBuddy/Models/InterfaceLanguage.swift")

for token in [
    "enum PCM16AudioPlaybackDropReason: Sendable, CustomStringConvertible",
    "case backlogLimit(Int)",
    "case prepareFailed(String)",
    "nonisolated(unsafe) private var onPlaybackDrop: (@Sendable (PCM16AudioPlaybackDropReason) -> Void)?",
    "nonisolated func setPlaybackDropHandler(_ handler: (@Sendable (PCM16AudioPlaybackDropReason) -> Void)?)",
    "notifyPlaybackDrop(.backlogLimit(maxPendingPlaybackBuffers))",
    "notifyPlaybackDrop(.prepareFailed(error.localizedDescription))",
    "private nonisolated func notifyPlaybackDrop(_ reason: PCM16AudioPlaybackDropReason)",
]:
    if token not in player:
        errors.append(f"PCM16AudioPlayer must report translated audio playback drops through {token}")

for token in [
    "private var lastTranslatedAudioDropLogAt = Date.distantPast",
    "private var translatedAudioDropCount = 0",
    "configureAudioPlayerDiagnostics()",
    "audioPlayer.setPlaybackDropHandler",
    "handleTranslatedAudioPlaybackDrop(reason.description)",
    "handleTranslatedAudioPlaybackDrop(settings.interfaceLanguage.localized(.translatedAudioDropOutputDisabled))",
    "private func handleTranslatedAudioPlaybackDrop(_ reason: String)",
    "settings.interfaceLanguage.localized(.translatedAudioPlaybackDropped",
]:
    if token not in app_state:
        errors.append(f"AppState must surface translated audio drop diagnostics through {token}")

for token in [
    "case translatedAudioPlaybackDropped",
    "case translatedAudioDropOutputDisabled",
    ".translatedAudioPlaybackDropped: \"Translated audio playback skipped: %@ (total %d).\"",
    ".translatedAudioDropOutputDisabled: \"translated audio output is disabled\"",
    ".translatedAudioPlaybackDropped: \"翻译语音已跳过：%@（累计 %d 次）。\"",
    ".translatedAudioDropOutputDisabled: \"翻译语音输出已关闭\"",
]:
    if token not in language:
        errors.append(f"InterfaceLanguage must localize translated audio drop diagnostics through {token}")

if errors:
    print("Translated audio playback drop diagnostics verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Translated audio playback drop diagnostics verification passed")
