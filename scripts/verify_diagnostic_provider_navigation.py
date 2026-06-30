#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
settings_path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
app_state = app_state_path.read_text()
settings = settings_path.read_text()
errors: list[str] = []

for token in [
    "@Published private(set) var providerSettingsFocusRequest: UUID?",
    "func openProviderSettings()",
    "func clearProviderSettingsFocusRequest()",
]:
    if token not in app_state:
        errors.append(f"AppState must expose a consumable API-provider focus request through {token}")

perform_match = re.search(
    r"func performDiagnosticRecoveryAction\(_ action: DiagnosticRecoveryAction\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func updateAPIKey",
    app_state,
)
if not perform_match:
    errors.append("AppState.performDiagnosticRecoveryAction(_:) not found")
else:
    body = perform_match.group("body")
    provider_case = body.find("case .openProviderSettings:")
    focus_call = body.find("openProviderSettings()", provider_case)
    if provider_case == -1 or focus_call == -1:
        errors.append("Diagnostic provider recovery must call openProviderSettings()")
    if "case .openProviderSettings:\n            openSettingsWindow()" in body:
        errors.append("Diagnostic provider recovery must not only open the settings window without selecting the provider page")

open_provider = re.search(
    r"func openProviderSettings\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func openMicrophoneSettings",
    app_state,
)
if not open_provider:
    errors.append("AppState.openProviderSettings() must live before openMicrophoneSettings()")
else:
    body = open_provider.group("body")
    for token in [
        "providerSettingsFocusRequest = UUID()",
        "openSettingsWindow()",
    ]:
        if token not in body:
            errors.append(f"openProviderSettings() must publish navigation request and open the window through {token}")
    request_idx = body.find("providerSettingsFocusRequest = UUID()")
    open_idx = body.find("openSettingsWindow()")
    if -1 in [request_idx, open_idx] or not (request_idx < open_idx):
        errors.append("openProviderSettings() should publish the focus request before opening the settings window")

clear_provider = re.search(
    r"func clearProviderSettingsFocusRequest\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func openProviderSettings",
    app_state,
)
if not clear_provider:
    errors.append("AppState.clearProviderSettingsFocusRequest() must live before openProviderSettings()")
else:
    body = clear_provider.group("body")
    if "providerSettingsFocusRequest = nil" not in body:
        errors.append("clearProviderSettingsFocusRequest() must consume the focus request by clearing it")

for token in [
    ".onAppear {",
    "applyProviderSettingsFocusRequest()",
    ".onChange(of: appState.providerSettingsFocusRequest)",
    "private func applyProviderSettingsFocusRequest()",
]:
    if token not in settings:
        errors.append(f"SettingsView must consume provider focus requests through {token}")

apply_match = re.search(
    r"private func applyProviderSettingsFocusRequest\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private var canUseRuntimeToolbarButton",
    settings,
)
if not apply_match:
    errors.append("SettingsView.applyProviderSettingsFocusRequest() must live before toolbar state helper")
else:
    body = apply_match.group("body")
    for token in [
        "guard appState.providerSettingsFocusRequest != nil else { return }",
        "selectedItem = .provider",
        "appState.clearProviderSettingsFocusRequest()",
    ]:
        if token not in body:
            errors.append(f"applyProviderSettingsFocusRequest() must select and consume the provider request through {token}")
    guard_idx = body.find("guard appState.providerSettingsFocusRequest != nil else { return }")
    select_idx = body.find("selectedItem = .provider")
    clear_idx = body.find("appState.clearProviderSettingsFocusRequest()")
    if -1 in [guard_idx, select_idx, clear_idx] or not (guard_idx < select_idx < clear_idx):
        errors.append("SettingsView must select provider before consuming the focus request")

if errors:
    print("Diagnostic provider navigation verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Diagnostic provider navigation verification passed")
