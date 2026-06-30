#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
interface_path = root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift"
client_path = root / "LiveBuddy" / "Services" / "GeminiLiveTranslateClient.swift"
app_state = app_state_path.read_text()
interface = interface_path.read_text()
client = client_path.read_text()
errors: list[str] = []

keys = [
    "connectionSocketOpened",
    "connectionSessionReady",
    "connectionDisconnected",
    "connectionSocketClosed",
    "connectionSendFailed",
    "connectionServerError",
    "connectionParseFailed",
]
for key in keys:
    if f"case {key}" not in interface:
        errors.append(f"InterfaceText must include {key}")
    if interface.count(f".{key}:") < 8:
        errors.append(f"InterfaceText.{key} must be translated for every supported language")

helper_match = re.search(r"private func localizedConnectionEventStatus\(_ event: LiveConnectionEvent\) -> String \{(?P<body>[\s\S]*?)\n    \}\n\n    private func scheduleReconnect", app_state)
if not helper_match:
    errors.append("AppState.localizedConnectionEventStatus(_:) not found before scheduleReconnect")
else:
    body = helper_match.group("body")
    for token in [
        "case .socketOpened:",
        "return settings.interfaceLanguage.localized(.connectionSocketOpened)",
        "case .sessionReady:",
        "return settings.interfaceLanguage.localized(.connectionSessionReady)",
        "case .disconnected(let message):",
        "return settings.interfaceLanguage.localized(.connectionDisconnected, arguments: [message])",
        "case .socketClosed(let message):",
        "return settings.interfaceLanguage.localized(.connectionSocketClosed, arguments: [message])",
        "case .sendFailed(let message):",
        "return settings.interfaceLanguage.localized(.connectionSendFailed, arguments: [message])",
        "case .serverError(let message):",
        "return settings.interfaceLanguage.localized(.connectionServerError, arguments: [message])",
        "case .parseFailed(let message):",
        "return settings.interfaceLanguage.localized(.connectionParseFailed, arguments: [message])",
    ]:
        if token not in body:
            errors.append(f"localizedConnectionEventStatus must map connection event through {token}")

handle_match = re.search(r"private func handleConnectionEvent\(_ event: LiveConnectionEvent\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func localizedConnectionEventStatus", app_state)
if not handle_match:
    errors.append("AppState.handleConnectionEvent(_:) not found before localized helper")
else:
    body = handle_match.group("body")
    if "localizedConnectionEventStatus(event)" not in body:
        errors.append("handleConnectionEvent must publish localized connection event status")
    if "event.statusMessage" in body:
        errors.append("handleConnectionEvent must not publish raw event.statusMessage")

schedule_match = re.search(r"private func scheduleReconnect\(after event: LiveConnectionEvent\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func reconnectGeminiClient", app_state)
if not schedule_match:
    errors.append("AppState.scheduleReconnect(after:) not found")
else:
    body = schedule_match.group("body")
    if "appendLog(localizedConnectionEventStatus(event), level: .error)" not in body:
        errors.append("scheduleReconnect must log localized connection event status")
    if "appendLog(event.statusMessage" in body:
        errors.append("scheduleReconnect must not log raw event.statusMessage")

client_status_match = re.search(r"private func handleClientStatus\(_ message: String\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func localizedStatus", app_state)
if not client_status_match:
    errors.append("AppState.handleClientStatus(_:) not found")
else:
    body = client_status_match.group("body")
    if "updateStatus(message, level: .error, log: true)" in body:
        errors.append("handleClientStatus must not expose raw low-level Gemini error strings as visible status")

report_match = re.search(r"private func report\(_ event: LiveConnectionEvent\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func reportReceiveStatusIfNeeded", client)
if not report_match:
    errors.append("GeminiLiveTranslateClient.report(_:) not found")
else:
    body = report_match.group("body")
    if "case .socketOpened, .sessionReady:" not in body or "onStatus?(event.statusMessage)" not in body:
        errors.append("GeminiLiveTranslateClient should only send raw statusMessage for non-error connection progress")
    if "onStatus?(event.statusMessage)\n        onConnectionEvent?(event)" in body:
        errors.append("GeminiLiveTranslateClient must not send raw error event.statusMessage through onStatus")

if errors:
    print("Connection event status localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Connection event status localization verification passed")
