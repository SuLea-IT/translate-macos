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

if "case logAppReady" not in interface:
    errors.append("InterfaceText must include logAppReady for the first user-visible runtime log entry")
if interface.count(".logAppReady:") < 8:
    errors.append("InterfaceText.logAppReady must be translated for every supported interface language")

if 'appendLog("App ready", level: .info)' in app_state:
    errors.append("AppState.init must not append the first visible log entry as hard-coded English")
if "appendLog(loadedSettings.interfaceLanguage.localized(.logAppReady), level: .info)" not in app_state:
    errors.append("AppState.init must append the ready log in the current interface language")

# Ensure the translated key sits near other log/status language rather than only in a test fixture.
english_match = re.search(r"private static let englishText: \[InterfaceText: String\] = \[(?P<body>[\s\S]*?)\n    \]", interface)
if english_match and '.logAppReady: "App ready"' not in english_match.group('body'):
    errors.append("English localization must keep the existing App ready wording under logAppReady")

if errors:
    print("App ready log localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("App ready log localization verification passed")
