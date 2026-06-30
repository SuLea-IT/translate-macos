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
global_shortcut_registrar = root / "LiveBuddy" / "Services" / "CarbonGlobalShortcutRegistrar.swift"
errors: list[str] = []

client_text = client.read_text()
settings_text = settings.read_text()
app_state_text = app_state.read_text()
microphone_text = microphone_capture.read_text()
screen_audio_text = screen_audio_capture.read_text()
audio_player_text = audio_player.read_text()
app_delegate_text = app_delegate.read_text()
global_shortcut_text = global_shortcut_registrar.read_text()

public_stop_match = re.search(r"func stop\(\) async \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
internal_stop_match = re.search(r"private func stop\(cancelPendingRestart: Bool\) async \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if internal_stop_match:
    stop_cleanup_body = internal_stop_match.group("body")
    if not public_stop_match or "await stop(cancelPendingRestart: true)" not in public_stop_match.group("body"):
        errors.append("AppState.stop() must delegate to stop(cancelPendingRestart: true)")
else:
    stop_cleanup_body = public_stop_match.group("body") if public_stop_match else ""
    if not public_stop_match:
        errors.append("AppState.stop() not found")

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
    if "appState.startGlossaryImportFromLocalFile(url:" not in body:
        errors.append("SettingsView local glossary importer must delegate security-scoped work to AppState.startGlossaryImportFromLocalFile")

file_import_lifecycle_match = re.search(r"func startGlossaryImportFromLocalFile\(url: URL, sourceName: String, importLimit: Int\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not file_import_lifecycle_match:
    errors.append("AppState.startGlossaryImportFromLocalFile(url:) not found for security-scoped cleanup")
else:
    body = file_import_lifecycle_match.group("body")
    for token in ["startAccessingSecurityScopedResource()", "defer", "stopAccessingSecurityScopedResource()"]:
        if token not in body:
            errors.append(f"Local glossary import must release security-scoped resources via {token} inside the AppState import task")

deinit_match = re.search(r"deinit \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not deinit_match:
    errors.append("AppState.deinit not found")
else:
    body = deinit_match.group("body")
    for token in [
        "restartTask?.cancel()",
        "reconnectTask?.cancel()",
        "connectionStopTask?.cancel()",
        "usageResumeTask?.cancel()",
        "setupChecklistRefreshTask?.cancel()",
        "audioSendTask?.cancel()",
        "preflightTestTask?.cancel()",
        "temporaryTestCaptionTask?.cancel()",
        "glossaryImportTask?.cancel()",
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

settings_did_set_match = re.search(r"@Published private\(set\) var settings: AppSettings \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not settings_did_set_match:
    errors.append("AppState.settings didSet not found")
else:
    body = settings_did_set_match.group("body")
    if "configureGlobalShortcutsIfNeeded(oldValue: oldValue)" not in body:
        errors.append("AppState.settings didSet must perform diff-aware global shortcut reconfiguration")

shortcut_reconfigure_match = re.search(r"private func configureGlobalShortcutsIfNeeded\(oldValue: AppSettings\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not shortcut_reconfigure_match:
    errors.append("AppState.configureGlobalShortcutsIfNeeded(oldValue:) not found")
else:
    body = shortcut_reconfigure_match.group("body")
    for token in [
        "oldValue.globalShortcutsEnabled != settings.globalShortcutsEnabled",
        "oldValue.globalShortcuts != settings.globalShortcuts",
        "guard shortcutsChanged else { return }",
        "configureGlobalShortcuts()",
    ]:
        if token not in body:
            errors.append(f"AppState.configureGlobalShortcutsIfNeeded(oldValue:) must avoid duplicate shortcut registration through {token}")

for shortcut_method in [
    "updateGlobalShortcutsEnabled",
    "updateGlobalShortcut",
    "clearGlobalShortcut",
    "resetGlobalShortcut",
    "resetAllGlobalShortcuts",
]:
    method_match = re.search(rf"func {shortcut_method}\([^\)]*\)(?: -> [^\{{]+)? \{{(?P<body>[\s\S]*?)\n    \}}", app_state_text)
    if method_match and "configureGlobalShortcuts()" in method_match.group("body"):
        errors.append(f"AppState.{shortcut_method} must not manually reconfigure shortcuts because settings didSet already handles it once")

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
    "private var audioCaptureGeneration = UUID()",
    "private var lastAudioSendBackpressureLogAt = Date.distantPast",
]:
    if token not in app_state_text:
        errors.append(f"AppState must bound and retain audio send/capture work through {token}")

start_capture_match = re.search(r"private func startCapture\(\) async throws \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not start_capture_match:
    errors.append("AppState.startCapture() not found")
else:
    body = start_capture_match.group("body")
    for token in ["let generation = audioCaptureGeneration", "audioSink(source: .microphone, generation: generation)", "audioSink(source: .screen, generation: generation)", "guard self?.audioCaptureGeneration == generation"]:
        if token not in body:
            errors.append(f"AppState.startCapture() must bind capture callbacks to the current capture generation through {token}")

audio_sink_match = re.search(r"private func audioSink\(source: AudioSource, generation: UUID\) -> @Sendable \(Data\) -> Void \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not audio_sink_match:
    errors.append("AppState.audioSink(source:generation:) must exist to tag capture callbacks")
else:
    body = audio_sink_match.group("body")
    for token in ["guard let self, self.audioCaptureGeneration == generation else { return }", "handleCapturedAudio(data, source: source, level: level)"]:
        if token not in body:
            errors.append(f"AppState.audioSink(source:generation:) must ignore stale capture callbacks through {token}")

handle_audio_match = re.search(r"private func handleCapturedAudio\(_ data: Data, source: AudioSource, level: Float\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not handle_audio_match:
    errors.append("AppState.handleCapturedAudio() not found")
else:
    body = handle_audio_match.group("body")
    if "Task {" in body and "sendAudio" in body:
        errors.append("AppState.handleCapturedAudio() must not spawn one detached send task per audio chunk")
    if "enqueueAudioSend(data)" not in body:
        errors.append("AppState.handleCapturedAudio() must send audio through bounded enqueueAudioSend(data)")

for context, pattern in [
    ("start", r"func start\(\) async \{(?P<body>[\s\S]*?)\n    \}"),
    ("stop(cancelPendingRestart:)", r"private func stop\(cancelPendingRestart: Bool\) async \{(?P<body>[\s\S]*?)\n    \}"),
    ("stopRuntimeAfterConnectionFailure", r"private func stopRuntimeAfterConnectionFailure\(generation: UUID\) async \{(?P<body>[\s\S]*?)\n    \}"),
]:
    match = re.search(pattern, app_state_text)
    if not match:
        errors.append(f"AppState.{context} not found for audio capture generation cleanup")
    elif "audioCaptureGeneration = UUID()" not in match.group("body"):
        errors.append(f"AppState.{context} must rotate audioCaptureGeneration to reject stale capture callbacks")

enqueue_match = re.search(r"private func enqueueAudioSend\(_ data: Data\) -> Bool \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not enqueue_match:
    errors.append("AppState.enqueueAudioSend(_:) must exist to serialize, bound, and report live audio send enqueue status")
else:
    body = enqueue_match.group("body")
    for token in [
        "pendingAudioSendChunks < maxPendingAudioSendChunks",
        "return false",
        "pendingAudioSendChunks += 1",
        "let previousTask = audioSendTask",
        "await previousTask.value",
        "await withTaskCancellationHandler",
        "previousTask.cancel()",
        "guard !Task.isCancelled else { return }",
        "self.client === client",
        "await client.sendAudio(data)",
        "return true",
        "Date()",
        "reportAudioSendBackpressure(now: now)",
    ]:
        if token not in body:
            errors.append(f"AppState.enqueueAudioSend(_:) must serialize/bound send work through {token}")

backpressure_match = re.search(r"private func reportAudioSendBackpressure\(now: Date\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not backpressure_match:
    errors.append("AppState.reportAudioSendBackpressure(now:) must exist to throttle and localize dropped-audio feedback")
else:
    body = backpressure_match.group("body")
    for token in [
        "timeIntervalSince(lastAudioSendBackpressureLogAt) >= 5",
        "lastAudioSendBackpressureLogAt = now",
        "localizedStatus(.statusAudioSendBackpressure)",
        "updateStatus(message, level: .error, log: true)",
        "lastAudioStatusAt = now",
    ]:
        if token not in body:
            errors.append(f"AppState.reportAudioSendBackpressure(now:) must throttle/localize dropped-audio feedback through {token}")

reset_audio_send_match = re.search(r"private func resetAudioSendPipeline\(\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not reset_audio_send_match:
    errors.append("AppState.resetAudioSendPipeline() must exist to cancel queued live audio sends")
else:
    body = reset_audio_send_match.group("body")
    for token in ["audioSendGeneration = UUID()", "audioSendTask?.cancel()", "audioSendTask = nil", "pendingAudioSendChunks = 0"]:
        if token not in body:
            errors.append(f"AppState.resetAudioSendPipeline() must release send work through {token}")

if "resetAudioSendPipeline()" not in stop_cleanup_body:
    errors.append("AppState.stop must cancel queued audio sends through resetAudioSendPipeline()")
for context, pattern in [
    ("stopRuntimeAfterConnectionFailure", r"private func stopRuntimeAfterConnectionFailure\(generation: UUID\) async \{(?P<body>[\s\S]*?)\n    \}"),
    ("enterUsagePause", r"private func enterUsagePause\(reason: UsageControlPauseReason\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("scheduleReconnect", r"private func scheduleReconnect\(after event: LiveConnectionEvent\) \{(?P<body>[\s\S]*?)\n    \}"),
]:
    match = re.search(pattern, app_state_text)
    if not match:
        errors.append(f"AppState.{context} not found for audio send cleanup")
    elif "resetAudioSendPipeline()" not in match.group("body"):
        errors.append(f"AppState.{context} must cancel queued audio sends through resetAudioSendPipeline()")


for token in [
    "private var connectionStopTask: Task<Void, Never>?",
    "private func scheduleStopRuntimeAfterConnectionFailure()",
]:
    if token not in app_state_text:
        errors.append(f"AppState must retain connection-failure stop work through {token}")

schedule_stop_match = re.search(r"private func scheduleStopRuntimeAfterConnectionFailure\(\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not schedule_stop_match:
    errors.append("AppState.scheduleStopRuntimeAfterConnectionFailure() not found")
else:
    body = schedule_stop_match.group("body")
    for token in [
        "guard connectionStopTask == nil",
        "let generation = UUID()",
        "connectionStopGeneration = generation",
        "connectionStopTask = Task",
        "await self?.stopRuntimeAfterConnectionFailure(generation: generation)",
        "guard !Task.isCancelled else { return }",
        "connectionStopGeneration == generation",
        "connectionStopTask = nil",
    ]:
        if token not in body:
            errors.append(f"AppState.scheduleStopRuntimeAfterConnectionFailure() must manage stop lifecycle through {token}")

if "Task { await stopRuntimeAfterConnectionFailure() }" in app_state_text or "await self?.stopRuntimeAfterConnectionFailure()" in app_state_text:
    errors.append("AppState must not spawn untracked or generation-unscoped connection failure stop tasks")

make_client_match = re.search(r"private func makeGeminiClient\(\) -> GeminiLiveTranslateClient \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not make_client_match:
    errors.append("AppState.makeGeminiClient() not found")
else:
    body = make_client_match.group("body")
    for token in [
        "client.onInputTranscript = { [weak self, weak client]",
        "client.onOutputTranscript = { [weak self, weak client]",
        "client.onAudioChunk = { [weak self, weak client, audioPlayer]",
        "client.onStatus = { [weak self, weak client]",
        "client.onConnectionEvent = { [weak self, weak client]",
    ]:
        if token not in body:
            errors.append(f"AppState.makeGeminiClient() must capture the callback source client weakly through {token}")
    if body.count("guard let self, let client, self.client === client else { return }") < 5:
        errors.append("AppState.makeGeminiClient() callbacks must ignore stale client events before mutating UI/audio state")
    for token in [
        "appendOriginalText(text)",
        "appendCaption(text, language: language, kind: .output)",
        "audioPlayer.playPCM16(data",
        "handleClientStatus(message)",
        "handleConnectionEvent(event)",
    ]:
        index = body.find(token)
        guard_index = body.rfind("guard let self, let client, self.client === client else { return }", 0, index)
        if index == -1 or guard_index == -1:
            errors.append(f"AppState.makeGeminiClient() must guard stale client callbacks before {token}")

start_match = re.search(r"func start\(\) async \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not start_match:
    errors.append("AppState.start not found for connection stop cleanup")
elif "connectionStopTask?.cancel()" not in start_match.group("body"):
    errors.append("AppState.start must cancel stale connection stop work")
if "connectionStopTask?.cancel()" not in stop_cleanup_body:
    errors.append("AppState.stop must cancel stale connection stop work")

stop_failure_match = re.search(r"private func stopRuntimeAfterConnectionFailure\(generation: UUID\) async \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if stop_failure_match:
    body = stop_failure_match.group("body")
    if "guard connectionStopGeneration == generation else { return }" not in body:
        errors.append("AppState.stopRuntimeAfterConnectionFailure() must reject stale generation before runtime cleanup")
    stop_index = body.find("await screenCapture?.stop()")
    guard_index = body.find("guard connectionStopGeneration == generation, !Task.isCancelled else { return }", stop_index)
    if stop_index == -1 or guard_index == -1:
        errors.append("AppState.stopRuntimeAfterConnectionFailure() must check Task cancellation after awaited screen capture stop before clearing runtime state")
    if "connectionStopTask?.cancel()" in body:
        errors.append("AppState.stopRuntimeAfterConnectionFailure() must not self-cancel the tracked connection stop task")


if internal_stop_match:
    if "if cancelPendingRestart" not in stop_cleanup_body or "restartTask?.cancel()" not in stop_cleanup_body:
        errors.append("AppState.stop(cancelPendingRestart:) must only cancel scheduled restarts when requested")
if stop_failure_match and "restartTask?.cancel()" not in stop_failure_match.group("body"):
    errors.append("AppState.stopRuntimeAfterConnectionFailure() must cancel scheduled restart work")


restart_match = re.search(r"private func rebuildRunningSessionIfNeeded\(oldValue: AppSettings\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not restart_match:
    errors.append("AppState.rebuildRunningSessionIfNeeded(oldValue:) not found")
else:
    body = restart_match.group("body")
    for token in [
        "restartTask?.cancel()",
        "restartTask = Task",
        "try await Task.sleep",
        "guard !Task.isCancelled else { return }",
        "await self.stop(cancelPendingRestart: false)",
        "guard !Task.isCancelled else { return }",
        "await self.start()",
        "restartTask = nil",
    ]:
        if token not in body:
            errors.append(f"AppState.rebuildRunningSessionIfNeeded(oldValue:) must make delayed restarts cancellable through {token}")
    if "try? await Task.sleep" in body:
        errors.append("AppState.rebuildRunningSessionIfNeeded(oldValue:) must not swallow Task.sleep cancellation")


for token in [
    "private var runtimeControlTask: Task<Void, Never>?",
    "private var pendingRuntimeControlRequest: RuntimeControlRequest?",
    "private enum RuntimeControlRequest",
    "func requestStart()",
    "func requestStop()",
    "private func scheduleRuntimeControl(_ request: RuntimeControlRequest)",
    "private func performRuntimeControl(_ request: RuntimeControlRequest) async",
]:
    if token not in app_state_text:
        errors.append(f"AppState must serialize user-driven runtime controls through {token}")

toggle_match = re.search(r"func toggle\(\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not toggle_match:
    errors.append("AppState.toggle() not found")
elif "scheduleRuntimeControl(.toggle)" not in toggle_match.group("body") or "Task {" in toggle_match.group("body"):
    errors.append("AppState.toggle() must schedule serialized runtime control instead of spawning an untracked Task")

recovery_match = re.search(r"func performDiagnosticRecoveryAction\(_ action: DiagnosticRecoveryAction\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not recovery_match:
    errors.append("AppState.performDiagnosticRecoveryAction(_:) not found")
elif "requestStart()" not in recovery_match.group("body") or "Task { await start() }" in recovery_match.group("body"):
    errors.append("Diagnostic retry must reuse AppState.requestStart() instead of spawning an untracked start Task")

schedule_runtime_match = re.search(r"private func scheduleRuntimeControl\(_ request: RuntimeControlRequest\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not schedule_runtime_match:
    errors.append("AppState.scheduleRuntimeControl(_:) not found")
else:
    body = schedule_runtime_match.group("body")
    for token in [
        "if runtimeControlTask != nil",
        "pendingRuntimeControlRequest = request",
        "runtimeControlTask = Task",
        "await self.performRuntimeControl(currentRequest)",
        "while let pendingRequest = self.pendingRuntimeControlRequest",
        "self.pendingRuntimeControlRequest = nil",
        "guard !Task.isCancelled else { return }",
        "runtimeControlTask = nil",
    ]:
        if token not in body:
            errors.append(f"AppState.scheduleRuntimeControl(_:) must serialize and preserve runtime controls through {token}")
    if "guard runtimeControlTask == nil else { return }" in body:
        errors.append("AppState.scheduleRuntimeControl(_:) must not drop busy-time runtime control requests")

perform_runtime_match = re.search(r"private func performRuntimeControl\(_ request: RuntimeControlRequest\) async \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not perform_runtime_match:
    errors.append("AppState.performRuntimeControl(_:) not found")
else:
    body = perform_runtime_match.group("body")
    for token in ["case .toggle", "case .start", "case .stop", "await start()", "await stop()"]:
        if token not in body:
            errors.append(f"AppState.performRuntimeControl(_:) must preserve runtime action behavior through {token}")

if deinit_match and "runtimeControlTask?.cancel()" not in deinit_match.group("body"):
    errors.append("AppState.deinit must cancel runtimeControlTask")
if deinit_match and "pendingRuntimeControlRequest = nil" not in deinit_match.group("body"):
    errors.append("AppState.deinit must clear pendingRuntimeControlRequest")

menu_bar_text = (root / "LiveBuddy" / "Views" / "MenuBar" / "MenuBarView.swift").read_text()
caption_panel_text = (root / "LiveBuddy" / "Views" / "Caption" / "CaptionPanelController.swift").read_text()
if "Task { await appState.stop() }" in menu_bar_text:
    errors.append("MenuBarView quit action must not spawn an untracked stop Task before termination")
if "NSApp.terminate(nil)" not in menu_bar_text:
    errors.append("MenuBarView quit action must request normal app termination")
if "appState?.requestStop()" not in caption_panel_text or "await appState?.stop()" in caption_panel_text:
    errors.append("Caption panel close must use AppState.requestStop() instead of an untracked stop Task")


for token in [
    "private var preflightTestTask: Task<Void, Never>?",
    "private var preflightTestGeneration = UUID()",
    "private var temporaryTestCaptionTask: Task<Void, Never>?",
    "private var temporaryTestCaptionGeneration = UUID()",
    "func startPreflightTest()",
]:
    if token not in app_state_text:
        errors.append(f"AppState must retain and control preflight work through {token}")

settings_preflight_match = re.search(
    r"private var preflightTestForm: some View \{(?P<body>[\s\S]*?)\n    \}\n\n    private var logsView",
    settings_text,
)
if not settings_preflight_match:
    errors.append("SettingsView preflight test form not found")
else:
    body = settings_preflight_match.group("body")
    if "appState.startPreflightTest()" not in body:
        errors.append("SettingsView preflight button must call AppState.startPreflightTest() instead of spawning an untracked Task")
    if "appState.isRunningPreflightTest" in body and "appState.cancelRunningPreflightTest()" not in body:
        errors.append("SettingsView preflight cancel state must call AppState.cancelRunningPreflightTest() instead of spawning an untracked Task")
    if "Task {" in body:
        errors.append("SettingsView preflight form must not spawn untracked Tasks")


start_preflight_match = re.search(r"func startPreflightTest\(\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not start_preflight_match:
    errors.append("AppState.startPreflightTest() not found")
else:
    body = start_preflight_match.group("body")
    for token in ["guard preflightTestTask == nil", "let generation = UUID()", "preflightTestGeneration = generation", "preflightTestTask = Task", "await self?.runPreflightTest(generation: generation)", "preflightTestTask = nil"]:
        if token not in body:
            errors.append(f"AppState.startPreflightTest() must manage generation-scoped preflight lifecycle through {token}")

start_cleanup_match = re.search(r"func start\(\) async \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not start_cleanup_match:
    errors.append("AppState.start not found for preflight cleanup")
elif "cancelPreflightTest()" not in start_cleanup_match.group("body"):
    errors.append("AppState.start must cancel preflight work through cancelPreflightTest()")
if "cancelPreflightTest()" not in stop_cleanup_body:
    errors.append("AppState.stop must cancel preflight work through cancelPreflightTest()")

if "private func cancelPreflightTest()" not in app_state_text:
    errors.append("AppState must provide cancelPreflightTest() for lifecycle cleanup")
else:
    cancel_match = re.search(r"private func cancelPreflightTest\(\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
    body = cancel_match.group("body") if cancel_match else ""
    for token in ["preflightTestGeneration = UUID()", "preflightTestTask?.cancel()", "preflightTestTask = nil", "temporaryTestCaptionGeneration = UUID()", "temporaryTestCaptionTask?.cancel()", "temporaryTestCaptionTask = nil", "isRunningPreflightTest = false"]:
        if token not in body:
            errors.append(f"AppState.cancelPreflightTest() must release preflight resource through {token}")


run_preflight_match = re.search(r"func runPreflightTest\(generation: UUID\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func startPreflightTest", app_state_text)
if not run_preflight_match:
    errors.append("AppState.runPreflightTest(generation:) not found")
else:
    body = run_preflight_match.group("body")
    for token in ["guard !Task.isCancelled else { return }", "guard self?.preflightTestGeneration == generation else { return }", "self?.preflightTestReport = report", "if preflightTestGeneration == generation", "isRunningPreflightTest = false"]:
        if token not in body:
            errors.append(f"AppState.runPreflightTest(generation:) must ignore cancelled or stale preflight updates through {token}")

show_caption_match = re.search(r"func showTemporaryTestCaption\(\) async \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not show_caption_match:
    errors.append("AppState.showTemporaryTestCaption() not found")
else:
    body = show_caption_match.group("body")
    for token in ["temporaryTestCaptionTask?.cancel()", "let generation = UUID()", "temporaryTestCaptionGeneration = generation", "temporaryTestCaptionTask = Task", "try? await Task.sleep", "guard !Task.isCancelled else { return }", "guard self.temporaryTestCaptionGeneration == generation else { return }", "temporaryTestCaptionTask = nil"]:
        if token not in body:
            errors.append(f"AppState.showTemporaryTestCaption() must manage temporary caption restoration through {token}")



for token in [
    "private var glossaryImportTask: Task<Void, Never>?",
    "func startGlossaryImport(from url: URL, sourceName: String, importLimit: Int)",
    "func startGlossaryImportFromLocalFile(url: URL, sourceName: String, importLimit: Int)",
    "func cancelGlossaryImport()",
]:
    if token not in app_state_text:
        errors.append(f"AppState must retain/cancel glossary import work through {token}")

start_remote_import_match = re.search(r"func startGlossaryImport\(from url: URL, sourceName: String, importLimit: Int\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not start_remote_import_match:
    errors.append("AppState.startGlossaryImport(from:) not found")
else:
    body = start_remote_import_match.group("body")
    for token in ["guard glossaryImportTask == nil", "glossaryImportTask = Task", "await self?.importGlossary(from: url", "glossaryImportTask = nil"]:
        if token not in body:
            errors.append(f"AppState.startGlossaryImport(from:) must manage remote import lifecycle through {token}")

start_file_import_match = re.search(r"func startGlossaryImportFromLocalFile\(url: URL, sourceName: String, importLimit: Int\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not start_file_import_match:
    errors.append("AppState.startGlossaryImportFromLocalFile(url:) not found")
else:
    body = start_file_import_match.group("body")
    for token in ["guard glossaryImportTask == nil", "glossaryImportTask = Task", "await self?.importGlossary(fromLocalFile: url", "glossaryImportTask = nil"]:
        if token not in body:
            errors.append(f"AppState.startGlossaryImportFromLocalFile(url:) must manage file import lifecycle through {token}")

cancel_import_match = re.search(r"func cancelGlossaryImport\(\) \{(?P<body>[\s\S]*?)\n    \}", app_state_text)
if not cancel_import_match:
    errors.append("AppState.cancelGlossaryImport() not found")
else:
    body = cancel_import_match.group("body")
    for token in ["glossaryImportTask?.cancel()", "glossaryImportTask = nil", "isImportingGlossary = false", "glossaryImportProgress = nil"]:
        if token not in body:
            errors.append(f"AppState.cancelGlossaryImport() must release import state through {token}")

for token in [
    "appState.startGlossaryImport(from:",
    "appState.startGlossaryImportFromLocalFile(url:",
    "appState.cancelGlossaryImport()",
    "Button(appState.t(.cancel))",
]:
    if token not in settings_text:
        errors.append(f"SettingsView must start/cancel glossary imports through {token}")

if "Task { await importSelectedGlossarySource() }" in settings_text:
    errors.append("SettingsView must not spawn an untracked remote glossary import Task")
if "Task {" in settings_text and "importGlossary(fromLocalFile" in settings_text:
    errors.append("SettingsView must not spawn an untracked file glossary import Task")


for token in [
    "private var glossaryImportGeneration = UUID()",
    "glossaryImportGeneration = UUID()",
    "glossaryImportGeneration == generation",
    "guard !Task.isCancelled else { return }",
]:
    if token not in app_state_text:
        errors.append(f"AppState glossary import lifecycle must guard stale import results through {token}")

for context, pattern in [
    ("importGlossary(from:)", r"func importGlossary\(from url: URL, sourceName: String, importLimit: Int\) async \{(?P<body>[\s\S]*?)\n    \}"),
    ("importGlossary(fromLocalFile:)", r"func importGlossary\(fromLocalFile url: URL, sourceName: String, importLimit: Int\) async \{(?P<body>[\s\S]*?)\n    \}"),
]:
    match = re.search(pattern, app_state_text)
    if not match:
        errors.append(f"AppState.{context} not found for stale import guard")
    else:
        body = match.group("body")
        for token in ["let generation = glossaryImportGeneration", "glossaryImportGeneration == generation", "guard !Task.isCancelled else { return }"]:
            if token not in body:
                errors.append(f"AppState.{context} must ignore stale/cancelled import results through {token}")

for token in [
    "@State private var tokenCheckTask: Task<Void, Never>?",
    "private func startTokenCheck()",
    "private func cancelTokenCheck()",
    ".onDisappear",
]:
    if token not in settings_text:
        errors.append(f"SettingsView must retain/cancel API token check work through {token}")

api_key_change_match = re.search(r"\.onChange\(of: appState.settings.apiKey\) \{ _, _ in(?P<body>[\s\S]*?)\n        \}", settings_text)
if not api_key_change_match:
    errors.append("SettingsView must reset API token verification state when the key changes")
else:
    body = api_key_change_match.group("body")
    for token in ["cancelTokenCheck()", "isTokenValid = nil", "tokenCheckError = nil"]:
        if token not in body:
            errors.append(f"SettingsView API key change handler must clear stale token check state through {token}")

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
    for token in ["tokenCheckTask?.cancel()", "tokenCheckTask = Task", "try await appState.verifyGeminiToken()", "guard tokenCheckGeneration == generation, !Task.isCancelled else { return }", "tokenCheckTask = nil"]:
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


for token in [
    "private var terminationTask: Task<Void, Never>?",
    "private static let terminationStopTimeoutNanoseconds",
    "private var terminationStopTask: Task<Void, Never>?",
    "private var terminationTimeoutTask: Task<Void, Never>?",
    "private func waitForRuntimeStopBeforeTermination(_ appState: AppState) async -> TerminationStopResult",
    "func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply",
]:
    if token not in app_delegate_text:
        errors.append(f"AppDelegate must support graceful async termination through {token}")

should_terminate_match = re.search(r"func applicationShouldTerminate\(_ sender: NSApplication\) -> NSApplication.TerminateReply \{(?P<body>[\s\S]*?)\n    \}", app_delegate_text)
if not should_terminate_match:
    errors.append("AppDelegate.applicationShouldTerminate(_:) not found")
else:
    body = should_terminate_match.group("body")
    for token in [
        ".terminateLater",
        "terminationTask = Task",
        "await self.waitForRuntimeStopBeforeTermination(appState)",
        "NSApp.reply(toApplicationShouldTerminate: true)",
        "terminationTask = nil",
    ]:
        if token not in body:
            errors.append(f"AppDelegate.applicationShouldTerminate(_:) must wait for runtime stop through {token}")
    if "await appState?.stop()" in body or "await appState.stop()" in body:
        errors.append("AppDelegate.applicationShouldTerminate(_:) must not directly await AppState.stop() without a timeout race")

will_terminate_match = re.search(r"func applicationWillTerminate\(_ notification: Notification\) \{(?P<body>[\s\S]*?)\n    \}", app_delegate_text)
if will_terminate_match and "Task { await appState?.stop() }" in will_terminate_match.group("body"):
    errors.append("AppDelegate.applicationWillTerminate must not spawn an untracked stop Task after termination has started")

delegate_deinit_match = re.search(r"deinit \{(?P<body>[\s\S]*?)\n    \}", app_delegate_text)
if delegate_deinit_match and "terminationTask?.cancel()" not in delegate_deinit_match.group("body"):
    errors.append("AppDelegate.deinit must cancel terminationTask")
if delegate_deinit_match and "clearTerminationStopTasks()" not in delegate_deinit_match.group("body"):
    errors.append("AppDelegate.deinit must cancel termination stop helper tasks")

clear_termination_match = re.search(r"private func clearTerminationStopTasks\(\) \{(?P<body>[\s\S]*?)\n    \}", app_delegate_text)
if not clear_termination_match:
    errors.append("AppDelegate.clearTerminationStopTasks() not found")
else:
    body = clear_termination_match.group("body")
    for token in [
        "terminationStopTask?.cancel()",
        "terminationStopTask = nil",
        "terminationTimeoutTask?.cancel()",
        "terminationTimeoutTask = nil",
    ]:
        if token not in body:
            errors.append(f"AppDelegate.clearTerminationStopTasks() must release termination helper task through {token}")

unregister_shortcuts_match = re.search(r"func unregisterAll\(\) \{(?P<body>[\s\S]*?)\n    \}", global_shortcut_text)
if not unregister_shortcuts_match:
    errors.append("CarbonGlobalShortcutRegistrar.unregisterAll() not found")
else:
    body = unregister_shortcuts_match.group("body")
    for token in ["UnregisterEventHotKey", "hotKeys.removeAll()", "handler = nil", "RemoveEventHandler(eventHandler)", "eventHandler = nil"]:
        if token not in body:
            errors.append(f"CarbonGlobalShortcutRegistrar.unregisterAll() must release global shortcut resource through {token}")

shortcut_register_match = re.search(r"func register\(_ shortcuts: \[GlobalShortcut\], handler: @escaping \(GlobalShortcutAction\) -> Void\) -> \[GlobalShortcutRegistrationResult\] \{(?P<body>[\s\S]*?)\n    \}\n\n    func unregisterAll", global_shortcut_text)
if not shortcut_register_match:
    errors.append("CarbonGlobalShortcutRegistrar.register not found")
else:
    body = shortcut_register_match.group("body")
    for token in [
        "guard !shortcuts.isEmpty else { return [] }",
        "let handlerStatus = installHandlerIfNeeded()",
        "guard handlerStatus == noErr else",
        "self.handler = nil",
        "GlobalShortcutRegistrationResult(shortcut: shortcut, status: .failed(Int32(handlerStatus)))",
    ]:
        if token not in body:
            errors.append(f"CarbonGlobalShortcutRegistrar.register must avoid phantom shortcut handlers through {token}")

shortcut_install_match = re.search(r"private func installHandlerIfNeeded\(\) -> OSStatus \{(?P<body>[\s\S]*?)\n    \}\n\n    private func handle", global_shortcut_text)
if not shortcut_install_match:
    errors.append("CarbonGlobalShortcutRegistrar.installHandlerIfNeeded() must return OSStatus")
else:
    body = shortcut_install_match.group("body")
    for token in [
        "guard eventHandler == nil else { return noErr }",
        "let status = InstallEventHandler(",
        "guard status == noErr else { return status }",
        "return noErr",
    ]:
        if token not in body:
            errors.append(f"CarbonGlobalShortcutRegistrar.installHandlerIfNeeded must surface Carbon install status through {token}")
if "private func installHandlerIfNeeded() {" in global_shortcut_text:
    errors.append("CarbonGlobalShortcutRegistrar.installHandlerIfNeeded must not ignore InstallEventHandler status")

shortcut_handle_match = re.search(r"private func handle\(id: UInt32\) \{(?P<body>[\s\S]*?)\n    \}", global_shortcut_text)
if not shortcut_handle_match:
    errors.append("CarbonGlobalShortcutRegistrar.handle(id:) not found")
else:
    body = shortcut_handle_match.group("body")
    if "DispatchQueue.main.async { [weak self] in" not in body or "self?.handler?(action)" not in body:
        errors.append("CarbonGlobalShortcutRegistrar.handle(id:) must resolve handler at execution time so disabled shortcuts cannot fire queued stale actions")
    if "[handler]" in body:
        errors.append("CarbonGlobalShortcutRegistrar.handle(id:) must not capture a stale handler closure")

shortcut_callback_match = re.search(r"let results = globalShortcutRegistrar\.register\([\s\S]*?\) \{ \[weak self\] action in(?P<body>[\s\S]*?)\n        \}", app_state_text)
if not shortcut_callback_match:
    errors.append("AppState global shortcut callback not found")
else:
    body = shortcut_callback_match.group("body")
    if "Task { @MainActor [weak self] in" not in body or "self?.performGlobalShortcut(action)" not in body:
        errors.append("AppState global shortcut callback must weakly capture self inside nested MainActor Task")
    if "Task { @MainActor in" in body:
        errors.append("AppState global shortcut callback must not use an unqualified nested MainActor Task")

device_listener_match = re.search(r"let block: AudioObjectPropertyListenerBlock = \{ \[weak self\] _, _ in(?P<body>[\s\S]*?)\n        \}", app_state_text)
if not device_listener_match:
    errors.append("AppState CoreAudio device-change listener block not found")
else:
    body = device_listener_match.group("body")
    if "Task { @MainActor [weak self] in" not in body or "self?.refreshAvailableMicrophones()" not in body:
        errors.append("AppState CoreAudio device-change callback must weakly capture self inside nested MainActor Task")
    if "Task { @MainActor in" in body:
        errors.append("AppState CoreAudio device-change callback must not use an unqualified nested MainActor Task")

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
