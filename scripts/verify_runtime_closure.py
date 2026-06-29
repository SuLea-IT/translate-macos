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
app_delegate = root / "LiveBuddy" / "App" / "AppDelegate.swift"
errors: list[str] = []

client_text = client.read_text()
settings_text = settings.read_text()
app_state_text = app_state.read_text()
microphone_text = microphone_capture.read_text()
screen_audio_text = screen_audio_capture.read_text()
audio_player_text = audio_player.read_text()
app_delegate_text = app_delegate.read_text()

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
        "setupChecklistRefreshTask?.cancel()",
        "audioSendTask?.cancel()",
        "preflightTestTask?.cancel()",
        "temporaryTestCaptionTask?.cancel()",
        "microphoneCapture?.stop()",
        "client?.close()",
        "audioPlayer.stop()",
        "globalShortcutRegistrar.unregisterAll()",
        "screenCaptureForDeinit",
        "await screenCaptureForDeinit.stop()",
    ]:
        if token not in body:
            errors.append(f"AppState.deinit must release runtime resource through {token}")


if "private var setupChecklistRefreshTask: Task<Void, Never>?" not in app_state_text:
    errors.append("AppState must retain setup checklist refresh task so stale refresh work can be cancelled")
refresh_match = re.search(r"func refreshSetupChecklist\(\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not refresh_match:
    errors.append("AppState.refreshSetupChecklist() not found")
else:
    body = refresh_match.group("body")
    for token in [
        "setupChecklistRefreshTask?.cancel()",
        "setupChecklistRefreshTask = Task",
        "guard !Task.isCancelled else { return }",
        "setupChecklistRefreshTask = nil",
    ]:
        if token not in body:
            errors.append(f"AppState.refreshSetupChecklist() must manage cancellable refresh work through {token}")


for token in [
    "private var audioSendTask: Task<Void, Never>?",
    "private var pendingAudioSendChunks = 0",
    "private let maxPendingAudioSendChunks",
    "private var audioSendGeneration = UUID()",
    "private var lastAudioSendBackpressureLogAt = Date.distantPast",
]:
    if token not in app_state_text:
        errors.append(f"AppState must bound and retain audio send work through {token}")

handle_audio_match = re.search(r"private func handleCapturedAudio\(_ data: Data, source: AudioSource, level: Float\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not handle_audio_match:
    errors.append("AppState.handleCapturedAudio() not found")
else:
    body = handle_audio_match.group("body")
    if "Task {" in body and "sendAudio" in body:
        errors.append("AppState.handleCapturedAudio() must not spawn one detached send task per audio chunk")
    if "enqueueAudioSend(data)" not in body:
        errors.append("AppState.handleCapturedAudio() must send audio through bounded enqueueAudioSend(data)")

enqueue_match = re.search(r"private func enqueueAudioSend\(_ data: Data\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not enqueue_match:
    errors.append("AppState.enqueueAudioSend(_:) must exist to serialize and bound live audio sends")
else:
    body = enqueue_match.group("body")
    for token in [
        "pendingAudioSendChunks < maxPendingAudioSendChunks",
        "pendingAudioSendChunks += 1",
        "let previousTask = audioSendTask",
        "await previousTask?.value",
        "guard !Task.isCancelled else { return }",
        "self.client === client",
        "await client.sendAudio(data)",
        "Date()",
        "timeIntervalSince(lastAudioSendBackpressureLogAt) >= 5",
        "lastAudioSendBackpressureLogAt = now",
    ]:
        if token not in body:
            errors.append(f"AppState.enqueueAudioSend(_:) must serialize/bound send work through {token}")

reset_audio_send_match = re.search(r"private func resetAudioSendPipeline\(\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not reset_audio_send_match:
    errors.append("AppState.resetAudioSendPipeline() must exist to cancel queued live audio sends")
else:
    body = reset_audio_send_match.group("body")
    for token in ["audioSendGeneration = UUID()", "audioSendTask?.cancel()", "audioSendTask = nil", "pendingAudioSendChunks = 0"]:
        if token not in body:
            errors.append(f"AppState.resetAudioSendPipeline() must release send work through {token}")

for context, pattern in [
    ("stop", r"func stop\(\) async \{(?P<body>[\s\S]*?)\n    \}"),
    ("stopRuntimeAfterConnectionFailure", r"private func stopRuntimeAfterConnectionFailure\(\) async \{(?P<body>[\s\S]*?)\n    \}"),
    ("enterUsagePause", r"private func enterUsagePause\(reason: UsageControlPauseReason\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("scheduleReconnect", r"private func scheduleReconnect\(after event: LiveConnectionEvent\) \{(?P<body>[\s\S]*?)\n    \}"),
]:
    match = re.search(pattern, app_state_text)
    if not match:
        errors.append(f"AppState.{context} not found for audio send cleanup")
    elif "resetAudioSendPipeline()" not in match.group("body"):
        errors.append(f"AppState.{context} must cancel queued audio sends through resetAudioSendPipeline()")


for token in [
    "private var preflightTestTask: Task<Void, Never>?",
    "private var temporaryTestCaptionTask: Task<Void, Never>?",
    "func startPreflightTest()",
]:
    if token not in app_state_text:
        errors.append(f"AppState must retain and control preflight work through {token}")

settings_preflight_match = re.search(r"Button\(appState.t\(\.runTest\)\) \{(?P<body>[\s\S]*?)\n                \}", settings_text)
if not settings_preflight_match:
    errors.append("SettingsView preflight run button not found")
elif "appState.startPreflightTest()" not in settings_preflight_match.group("body"):
    errors.append("SettingsView preflight button must call AppState.startPreflightTest() instead of spawning an untracked Task")

start_preflight_match = re.search(r"func startPreflightTest\(\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not start_preflight_match:
    errors.append("AppState.startPreflightTest() not found")
else:
    body = start_preflight_match.group("body")
    for token in ["guard preflightTestTask == nil", "preflightTestTask = Task", "await self?.runPreflightTest()", "preflightTestTask = nil"]:
        if token not in body:
            errors.append(f"AppState.startPreflightTest() must manage preflight lifecycle through {token}")

for context, pattern in [
    ("start", r"func start\(\) async \{(?P<body>[\s\S]*?)\n    \}"),
    ("stop", r"func stop\(\) async \{(?P<body>[\s\S]*?)\n    \}"),
]:
    match = re.search(pattern, app_state_text)
    if not match:
        errors.append(f"AppState.{context} not found for preflight cleanup")
    elif "cancelPreflightTest()" not in match.group("body"):
        errors.append(f"AppState.{context} must cancel preflight work through cancelPreflightTest()")

if "private func cancelPreflightTest()" not in app_state_text:
    errors.append("AppState must provide cancelPreflightTest() for lifecycle cleanup")
else:
    cancel_match = re.search(r"private func cancelPreflightTest\(\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
    body = cancel_match.group("body") if cancel_match else ""
    for token in ["preflightTestTask?.cancel()", "preflightTestTask = nil", "temporaryTestCaptionTask?.cancel()", "temporaryTestCaptionTask = nil", "isRunningPreflightTest = false"]:
        if token not in body:
            errors.append(f"AppState.cancelPreflightTest() must release preflight resource through {token}")


run_preflight_match = re.search(r"func runPreflightTest\(\) async \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not run_preflight_match:
    errors.append("AppState.runPreflightTest() not found")
else:
    body = run_preflight_match.group("body")
    for token in ["guard !Task.isCancelled else { return }", "self?.preflightTestReport = report"]:
        if token not in body:
            errors.append(f"AppState.runPreflightTest() must ignore cancelled preflight updates through {token}")

show_caption_match = re.search(r"func showTemporaryTestCaption\(\) async \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not show_caption_match:
    errors.append("AppState.showTemporaryTestCaption() not found")
else:
    body = show_caption_match.group("body")
    for token in ["temporaryTestCaptionTask?.cancel()", "temporaryTestCaptionTask = Task", "try? await Task.sleep", "guard !Task.isCancelled else { return }", "temporaryTestCaptionTask = nil"]:
        if token not in body:
            errors.append(f"AppState.showTemporaryTestCaption() must manage temporary caption restoration through {token}")


for token in [
    "@State private var tokenCheckTask: Task<Void, Never>?",
    "private func startTokenCheck()",
    "private func cancelTokenCheck()",
    ".onDisappear",
]:
    if token not in settings_text:
        errors.append(f"SettingsView must retain/cancel API token check work through {token}")

provider_section_match = re.search(r"Button\(appState.t\(\.check\)\) \{(?P<body>[\s\S]*?)\n                        \}", settings_text)
if not provider_section_match:
    errors.append("SettingsView API token check button not found")
elif "startTokenCheck()" not in provider_section_match.group("body"):
    errors.append("SettingsView API token check button must call startTokenCheck() instead of spawning an untracked Task")

start_token_match = re.search(r"private func startTokenCheck\(\) \{(?P<body>[\s\S]*?)\n    \}", settings_text)
if not start_token_match:
    errors.append("SettingsView.startTokenCheck() not found")
else:
    body = start_token_match.group("body")
    for token in ["tokenCheckTask?.cancel()", "tokenCheckTask = Task", "try await appState.verifyGeminiToken()", "guard !Task.isCancelled else { return }", "tokenCheckTask = nil"]:
        if token not in body:
            errors.append(f"SettingsView.startTokenCheck() must manage token check lifecycle through {token}")

cancel_token_match = re.search(r"private func cancelTokenCheck\(\) \{(?P<body>[\s\S]*?)\n    \}", settings_text)
if not cancel_token_match:
    errors.append("SettingsView.cancelTokenCheck() not found")
else:
    body = cancel_token_match.group("body")
    for token in ["tokenCheckTask?.cancel()", "tokenCheckTask = nil", "isCheckingToken = false"]:
        if token not in body:
            errors.append(f"SettingsView.cancelTokenCheck() must release token check state through {token}")

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


if "private func removeShowCaptionObserver()" not in app_delegate_text:
    errors.append("AppDelegate must centralize showCaptionObserver cleanup")
for context, pattern in [
    ("configure(with:)", r"func configure\(with appState: AppState\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("applicationWillTerminate", r"func applicationWillTerminate\(_ notification: Notification\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("deinit", r"deinit \{(?P<body>[\s\S]*?)\n    \}"),
]:
    match = re.search(pattern, app_delegate_text)
    if not match:
        errors.append(f"AppDelegate.{context} must exist for observer cleanup")
    elif "removeShowCaptionObserver()" not in match.group("body"):
        errors.append(f"AppDelegate.{context} must remove showCaptionObserver through removeShowCaptionObserver()")

if errors:
    print("Runtime closure verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)
print("Runtime closure verification passed")
