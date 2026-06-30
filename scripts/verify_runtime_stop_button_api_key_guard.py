#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
settings_view = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
text = settings_view.read_text()
errors: list[str] = []

if ".disabled(appState.settings.apiKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)" in text:
    errors.append("Toolbar runtime button must not be disabled solely because the API key field is empty; stop must remain available while running")

if ".disabled(!canUseRuntimeToolbarButton)" not in text:
    errors.append("Toolbar runtime button should use a dedicated canUseRuntimeToolbarButton guard")

helper = re.search(
    r"private var canUseRuntimeToolbarButton: Bool \{(?P<body>[\s\S]*?)\n    \}\n\n    private var providerForm",
    text,
)
if not helper:
    errors.append("SettingsView must expose canUseRuntimeToolbarButton before providerForm")
else:
    body = helper.group("body")
    for token in [
        "appState.isRunning",
        "appState.settings.apiKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty",
        "return appState.isRunning || !apiKeyIsEmpty",
    ]:
        if token not in body:
            errors.append(f"canUseRuntimeToolbarButton must allow stopping while running and only block empty-key starts through {token}")

if errors:
    print("Runtime stop button API-key guard verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Runtime stop button API-key guard verification passed")
