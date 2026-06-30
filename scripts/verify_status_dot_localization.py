#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
status_dot_path = root / "LiveBuddy" / "Views" / "Components" / "StatusDot.swift"
settings_path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
caption_path = root / "LiveBuddy" / "Views" / "Caption" / "CaptionView.swift"
interface_path = root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift"

status_dot = status_dot_path.read_text()
settings = settings_path.read_text()
caption = caption_path.read_text()
interface = interface_path.read_text()
errors: list[str] = []

for key in ["statusRunning", "statusError"]:
    if f"case {key}" not in interface:
        errors.append(f"InterfaceText must include {key}")
    if interface.count(f".{key}:") < 8:
        errors.append(f"InterfaceText.{key} must be translated for every supported language")

for token in [
    "let interfaceLanguage: InterfaceLanguage",
    "interfaceLanguage.localized(.statusRunning)",
    "interfaceLanguage.localized(.statusConnecting)",
    "interfaceLanguage.localized(.statusError)",
    "interfaceLanguage.localized(.statusStopped)",
]:
    if token not in status_dot:
        errors.append(f"StatusDot must localize hover text through {token}")

for old in ['"Running"', '"Connecting"', '"Error"', '"Stopped"']:
    if old in status_dot:
        errors.append(f"StatusDot must not hard-code hover label {old}")

for view_name, text in [("SettingsView", settings), ("CaptionView", caption)]:
    expected = "StatusDot(level: appState.statusLevel, interfaceLanguage: appState.settings.interfaceLanguage)"
    if expected not in text:
        errors.append(f"{view_name} must pass the active interface language into StatusDot")
    if "StatusDot(level: appState.statusLevel)" in text:
        errors.append(f"{view_name} must not instantiate StatusDot without interfaceLanguage")

if errors:
    print("Status dot localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Status dot localization verification passed")
