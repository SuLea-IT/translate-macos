#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

if "private var isTranslatedAudioOutputEnabled: Bool" not in text:
    errors.append("AppState must centralize translated audio output enabled state")

make_match = re.search(r"client\.onAudioChunk = \{ \[weak self, weak client, audioPlayer\] data in(?P<body>[\s\S]*?)\n        \}", text)
if not make_match:
    errors.append("AppState.makeGeminiClient() onAudioChunk handler not found")
else:
    body = make_match.group("body")
    for token in [
        "guard self.isTranslatedAudioOutputEnabled else { return }",
        "audioPlayer.playPCM16(data, sampleRate: 24_000)",
    ]:
        if token not in body:
            errors.append(f"onAudioChunk must drop translated audio while muted/zero-volume through {token}")
    guard_idx = body.find("guard self.isTranslatedAudioOutputEnabled else { return }")
    play_idx = body.find("audioPlayer.playPCM16(data, sampleRate: 24_000)")
    if -1 in [guard_idx, play_idx] or guard_idx > play_idx:
        errors.append("onAudioChunk must check translated audio output before enqueueing playback")

update_match = re.search(r"private func updateAudioPlayerVolume\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func handleClientStatus", text)
if not update_match:
    errors.append("AppState.updateAudioPlayerVolume() not found")
else:
    body = update_match.group("body")
    for token in [
        "let volume = settings.audioPlayerMuted ? 0.0 : settings.audioPlayerVolume",
        "if volume <= 0 {",
        "audioPlayer.stop()",
        "return",
        "audioPlayer.setVolume(Float(volume))",
    ]:
        if token not in body:
            errors.append(f"updateAudioPlayerVolume must clear queued translated audio when output is disabled through {token}")
    stop_idx = body.find("audioPlayer.stop()")
    set_idx = body.find("audioPlayer.setVolume(Float(volume))")
    if stop_idx == -1 or set_idx == -1 or stop_idx > set_idx:
        errors.append("updateAudioPlayerVolume must stop queued audio before any later nonzero setVolume path")

if errors:
    print("Muted audio playback drop verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Muted audio playback drop verification passed")
