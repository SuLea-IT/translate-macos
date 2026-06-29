#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
client = root / "LiveBuddy" / "Services" / "GeminiLiveTranslateClient.swift"
settings = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
app_state = root / "LiveBuddy" / "Models" / "AppState.swift"
microphone_capture = root / "LiveBuddy" / "Services" / "MicrophoneCapture.swift"
screen_audio_capture = root / "LiveBuddy" / "Services" / "ScreenAudioCapture.swift"
audio_player = root / "LiveBuddy" / "Utilities" / "PCM16AudioPlayer.swift"
errors: list[str] = []

client_text = client.read_text()
settings_text = settings.read_text()
app_state_text = app_state.read_text()
microphone_text = microphone_capture.read_text()
screen_audio_text = screen_audio_capture.read_text()
audio_player_text = audio_player.read_text()

for token in ["socketOpenTimeout", "setupMessageTimeout", "withLiveTimeout", "receiveMessage(timeout:"]:
    if token not in client_text:
        errors.append(f"GeminiLiveTranslateClient must use bounded websocket/setup waits through {token}")
if "if completion.resume(throwing: LiveTranslateError.setupTimedOut)" not in client_text:
    errors.append("Timeout cleanup must only run when the timeout wins the one-shot completion race")
if "@discardableResult\n    func resume(with result:" not in client_text:
    errors.append("Live timeout completion must report whether it actually resumed the continuation")

connect_match = re.search(r"func connect\(\) async throws \{(?P<body>[\s\S]*?)\n    \}", client_text)
if not connect_match:
    errors.append("GeminiLiveTranslateClient.connect() not found")
else:
    body = connect_match.group("body")
    if "do {" not in body or "catch" not in body or "close()" not in body:
        errors.append("GeminiLiveTranslateClient.connect() must close the socket/session when connect or setup fails")

close_match = re.search(r"func close\(\) \{(?P<body>[\s\S]*?)\n    \}", client_text)
if not close_match:
    errors.append("GeminiLiveTranslateClient.close() not found")
else:
    body = close_match.group("body")
    if "openContinuation?.resume(throwing:" not in body or "openContinuation = nil" not in body:
        errors.append("GeminiLiveTranslateClient.close() must resume and clear any pending open continuation")

file_import_match = re.search(r"private func handleGlossaryFileImporterResult[\s\S]*?case \.success\(let urls\):(?P<body>[\s\S]*?)case \.failure", settings_text)
if not file_import_match:
    errors.append("SettingsView.handleGlossaryFileImporterResult success branch not found")
else:
    body = file_import_match.group("body")
    if "defer" not in body or "stopAccessingSecurityScopedResource" not in body:
        errors.append("Local glossary import must release security-scoped resources via defer inside the import task")

deinit_match = re.search(r"deinit \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not deinit_match:
    errors.append("AppState.deinit not found")
else:
    body = deinit_match.group("body")
    for token in [
        "restartTask?.cancel()",
        "reconnectTask?.cancel()",
        "usageResumeTask?.cancel()",
        "microphoneCapture?.stop()",
        "client?.close()",
        "audioPlayer.stop()",
        "globalShortcutRegistrar.unregisterAll()",
        "screenCaptureForDeinit",
        "await screenCaptureForDeinit.stop()",
    ]:
        if token not in body:
            errors.append(f"AppState.deinit must release runtime resource through {token}")

mic_deinit_match = re.search(r"deinit \{(?P<body>[\s\S]*?)\n    \}", microphone_text)
if not mic_deinit_match:
    errors.append("MicrophoneCapture.deinit must stop the capture engine")
else:
    body = mic_deinit_match.group("body")
    if "stop()" not in body:
        errors.append("MicrophoneCapture.deinit must call stop()")

player_deinit_match = re.search(r"deinit \{(?P<body>[\s\S]*?)\n    \}", audio_player_text)
if not player_deinit_match:
    errors.append("PCM16AudioPlayer.deinit must stop AVAudio playback resources")
else:
    body = player_deinit_match.group("body")
    for token in ["player.stop()", "engine.stop()", "isPrepared = false"]:
        if token not in body:
            errors.append(f"PCM16AudioPlayer.deinit must release playback resource through {token}")

screen_deinit_match = re.search(r"deinit \{(?P<body>[\s\S]*?)\n    \}", screen_audio_text)
if not screen_deinit_match:
    errors.append("ScreenAudioCapture.deinit must stop the ScreenCaptureKit stream")
else:
    body = screen_deinit_match.group("body")
    for token in ["chunker.reset()", "screenStreamForDeinit", "try? await screenStreamForDeinit.stopCapture()"]:
        if token not in body:
            errors.append(f"ScreenAudioCapture.deinit must release capture resource through {token}")

if errors:
    print("Runtime closure verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)
print("Runtime closure verification passed")
