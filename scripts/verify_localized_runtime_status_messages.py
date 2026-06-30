#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
interface_path = root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift"
app_state = app_state_path.read_text()
interface = interface_path.read_text()
errors: list[str] = []

for key in ["statusReady", "statusConnecting", "statusListening", "statusStopped", "statusResumingReplay"]:
    if f"case {key}" not in interface:
        errors.append(f"InterfaceText must include {key}")
    if interface.count(f".{key}:") < 8:
        errors.append(f"InterfaceText.{key} must be translated for every supported language")

for token in [
    "@Published private(set) var statusMessage: String",
    "statusMessage = loadedSettings.interfaceLanguage.localized(.statusReady)",
    "private var localizedStatusKey: InterfaceText? = .statusReady",
    "private func localizedStatus(_ key: InterfaceText) -> String",
    "private func updateLocalizedStatus(_ key: InterfaceText, level: LiveStatusLevel, log: Bool)",
    "private func refreshStatusMessageLanguageIfNeeded(oldValue: AppSettings)",
    "refreshStatusMessageLanguageIfNeeded(oldValue: oldValue)",
]:
    if token not in app_state:
        errors.append(f"AppState must initialize/localize runtime status through {token}")

for old, expected in [
    ('updateStatus("Connecting", level: .connecting, log: true)', 'updateLocalizedStatus(.statusConnecting, level: .connecting, log: true)'),
    ('updateStatus("Listening", level: .running, log: true)', 'updateLocalizedStatus(.statusListening, level: .running, log: true)'),
    ('updateStatus("Stopped", level: .stopped, log: true)', 'updateLocalizedStatus(.statusStopped, level: .stopped, log: true)'),
    ('updateStatus("Resuming · replaying buffered audio", level: .connecting, log: true)', 'updateLocalizedStatus(.statusResumingReplay, level: .connecting, log: true)'),
]:
    if old in app_state:
        errors.append(f"AppState must not use hard-coded runtime status {old}")
    if expected not in app_state:
        errors.append(f"AppState must use localized runtime status through {expected}")

usage_match = re.search(r"private func runningUsageStatusMessage\(\) -> String \{(?P<body>[\s\S]*?)\n    \}\n\n    private func usagePauseLogMessage", app_state)
if not usage_match:
    errors.append("AppState.runningUsageStatusMessage() not found")
else:
    body = usage_match.group("body")
    for token in [
        "return \"\\(localizedStatus(.statusListening)) · \\(base)\"",
        "return \"\\(localizedStatus(.statusResumingReplay)) · \\(base)\"",
    ]:
        if token not in body:
            errors.append(f"usageStatusMessage must compose localized runtime status through {token}")
    for old in ["Listening ·", "Resuming · replaying buffered audio ·"]:
        if old in body:
            errors.append(f"usageStatusMessage must not use hard-coded prefix {old}")

client_status_match = re.search(r"private func handleClientStatus\(_ message: String\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func localizedStatus", app_state)
if not client_status_match:
    errors.append("AppState.handleClientStatus(_:) not found")
else:
    body = client_status_match.group("body")
    for token in [
        'lowered.contains("socket opened")',
        "updateLocalizedStatus(.statusConnecting, level: .connecting, log: false)",
        'lowered.contains("ready") || lowered.contains("listening")',
        "updateLocalizedStatus(.statusListening, level: .running, log: false)",
        'lowered.contains("receiving translated audio")',
        "statusLevel = .running",
    ]:
        if token not in body:
            errors.append(f"handleClientStatus must keep low-level client statuses localized through {token}")
    if 'updateStatus(message, level: .running, log: false)' in body:
        errors.append("handleClientStatus must not expose raw ready/listening/receiving client messages as the visible running status")

if errors:
    print("Localized runtime status verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Localized runtime status verification passed")
