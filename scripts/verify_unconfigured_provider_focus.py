#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_delegate_path = root / "LiveBuddy" / "App" / "AppDelegate.swift"
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
app_delegate = app_delegate_path.read_text()
app_state = app_state_path.read_text()
errors: list[str] = []

configure_match = re.search(
    r"func configure\(with appState: AppState\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func applicationShouldTerminate",
    app_delegate,
)
if not configure_match:
    errors.append("AppDelegate.configure(with:) not found")
else:
    body = configure_match.group("body")
    if body.count("openProviderSettings()") < 2:
        errors.append("AppDelegate must focus API Provider settings for both first launch and show-caption attempts when provider is not configured")
    for snippet in [
        "else {\n            appState.openSettingsWindow()",
        "else {\n                    self?.appState?.openSettingsWindow()",
    ]:
        if snippet in body:
            errors.append("AppDelegate must not use a generic settings open for unconfigured provider recovery")

start_match = re.search(
    r"func start\(\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func stop",
    app_state,
)
if not start_match:
    errors.append("AppState.start() not found")
else:
    body = start_match.group("body")
    blocked_idx = body.find("if case .blocked(let issue) = preflight")
    focus_idx = body.find("openProviderSettings()", blocked_idx)
    sheet_idx = body.find("showSetupSheet = true", blocked_idx)
    return_idx = body.find("return", blocked_idx)
    if blocked_idx == -1:
        errors.append("AppState.start() preflight blocked path not found")
    if focus_idx == -1:
        errors.append("AppState.start() must focus API Provider settings when preflight blocks startup")
    if -1 in [blocked_idx, focus_idx, sheet_idx, return_idx] or not (blocked_idx < focus_idx < sheet_idx < return_idx):
        errors.append("AppState.start() should focus provider settings before presenting setup sheet on preflight block")
    blocked_body = body[blocked_idx:return_idx if return_idx != -1 else len(body)]
    if "openSettingsWindow()" in blocked_body:
        errors.append("AppState.start() blocked preflight path must not bypass AppState.openProviderSettings()")

if errors:
    print("Unconfigured provider focus verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Unconfigured provider focus verification passed")
