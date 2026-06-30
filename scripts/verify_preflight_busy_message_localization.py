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

key = "preflightStopTranslationBeforeDiagnostics"
if f"case {key}" not in interface:
    errors.append(f"InterfaceText must include {key}")
if interface.count(f".{key}:") < 8:
    errors.append(f"InterfaceText.{key} must be translated for every supported language")

run_match = re.search(r"func runPreflightTest\(generation: UUID\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func startPreflightTest", app_state)
if not run_match:
    errors.append("AppState.runPreflightTest(generation:) not found")
else:
    body = run_match.group("body")
    expected = "message: settings.interfaceLanguage.localized(.preflightStopTranslationBeforeDiagnostics)"
    if expected not in body:
        errors.append(f"runPreflightTest must localize busy diagnostic message through {expected}")
    if 'message: "Stop translation before running diagnostics"' in body:
        errors.append("runPreflightTest must not expose hard-coded English busy diagnostic message")

if errors:
    print("Preflight busy message localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Preflight busy message localization verification passed")
