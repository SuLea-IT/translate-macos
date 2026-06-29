#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
settings_path = root / "LiveBuddy" / "Models" / "AppSettings.swift"
app_state = app_state_path.read_text()
settings = settings_path.read_text()
errors: list[str] = []

settings_did_set = re.search(
    r"@Published private\(set\) var settings: AppSettings \{\n        didSet \{(?P<body>[\s\S]*?)\n        \}\n    \}",
    app_state,
)
if not settings_did_set:
    errors.append("AppState.settings didSet not found")
else:
    body = settings_did_set.group("body")
    if "scheduleSettingsSaveIfNeeded(oldValue: oldValue)" not in body:
        errors.append("settings didSet must gate settings.json writes through scheduleSettingsSaveIfNeeded(oldValue: oldValue)")
    direct_calls = re.findall(r"(?<!IfNeeded\()\bscheduleSettingsSave\(\)", body)
    if direct_calls:
        errors.append("settings didSet must not call scheduleSettingsSave() directly for keychain-only API key edits")

save_if_needed = re.search(
    r"private func scheduleSettingsSaveIfNeeded\(oldValue: AppSettings\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func scheduleSettingsSave\(\)",
    app_state,
)
if not save_if_needed:
    errors.append("AppState.scheduleSettingsSaveIfNeeded(oldValue:) not found before scheduleSettingsSave()")
else:
    body = save_if_needed.group("body")
    for token in [
        "guard settings.requiresSettingsFileSave(comparedTo: oldValue) else { return }",
        "scheduleSettingsSave()",
    ]:
        if token not in body:
            errors.append(f"scheduleSettingsSaveIfNeeded must use {token}")

persist_helper = re.search(
    r"func requiresSettingsFileSave\(comparedTo other: AppSettings\) -> Bool \{(?P<body>[\s\S]*?)\n    \}\n\n    func requiresSessionRestart",
    settings,
)
if not persist_helper:
    errors.append("AppSettings.requiresSettingsFileSave(comparedTo:) not found before requiresSessionRestart")
else:
    body = persist_helper.group("body")
    for token in [
        "var current = self",
        "var comparison = other",
        "current.apiKey = \"\"",
        "comparison.apiKey = \"\"",
        "return current != comparison",
    ]:
        if token not in body:
            errors.append(f"requiresSettingsFileSave must ignore keychain-only API keys via {token}")

encode_match = re.search(
    r"func encode\(to encoder: Encoder\) throws \{(?P<body>[\s\S]*?)\n    \}\n\n    func requiresSettingsFileSave",
    settings,
)
if not encode_match:
    errors.append("AppSettings.encode(to:) block not found before requiresSettingsFileSave")
else:
    body = encode_match.group("body")
    if "apiKey" in body:
        errors.append("AppSettings.encode(to:) must continue to omit apiKey from settings.json")

if errors:
    print("Settings file save scope verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Settings file save scope verification passed")
