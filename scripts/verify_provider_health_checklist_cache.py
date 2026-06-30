#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
app_state = app_state_path.read_text()
errors: list[str] = []

for token in [
    "private var cachedProviderHealthAPIKey:",
    "private var cachedProviderHealthStatus:",
    "private func rememberProviderHealthStatus(_ status: ProviderHealthStatus, apiKey: String)",
    "private func invalidateCachedProviderHealthStatusIfNeeded(for apiKey: String)",
    "private func updateSetupChecklist(apiKeyStatus: ProviderHealthStatus)",
    "private func permissionStatus(from item: PermissionChecklistItem) -> PermissionStatus",
]:
    if token not in app_state:
        errors.append(f"AppState must keep manual provider verification connected to setup checklist through {token}")

provider_match = re.search(
    r"private var providerHealthStatusForCurrentKey: ProviderHealthStatus \{(?P<body>[\s\S]*?)\n    \}",
    app_state,
)
if not provider_match:
    errors.append("providerHealthStatusForCurrentKey not found")
else:
    body = provider_match.group("body")
    for token in [
        "let trimmed = settings.apiKey.trimmingCharacters(in: .whitespacesAndNewlines)",
        "guard !trimmed.isEmpty else { return .missing }",
        "cachedProviderHealthAPIKey == trimmed",
        "let cachedProviderHealthStatus",
        "return cachedProviderHealthStatus",
        "return .unchecked",
    ]:
        if token not in body:
            errors.append(f"providerHealthStatusForCurrentKey must reuse cached manual verification status through {token}")

verify_match = re.search(
    r"func verifyGeminiToken\(\) async throws \{(?P<body>[\s\S]*?)\n    \}\n\n",
    app_state,
)
if not verify_match:
    errors.append("verifyGeminiToken() not found")
else:
    body = verify_match.group("body")
    status_idx = body.find("let status = await providerHealthService.verify(apiKey: settings.apiKey)")
    remember_idx = body.find("rememberProviderHealthStatus(status, apiKey: settings.apiKey)")
    checklist_idx = body.find("updateSetupChecklist(apiKeyStatus: status)")
    switch_idx = body.find("switch status")
    if status_idx == -1:
        errors.append("verifyGeminiToken must still await provider health verification")
    if remember_idx == -1 or not (status_idx < remember_idx < switch_idx):
        errors.append("verifyGeminiToken must remember the provider status before branching on it")
    if checklist_idx == -1 or not (remember_idx < checklist_idx < switch_idx):
        errors.append("verifyGeminiToken must immediately update the setup checklist with the provider status")

update_key_match = re.search(
    r"func updateAPIKey\(_ apiKey: String\) \{(?P<body>[\s\S]*?)\n    \}",
    app_state,
)
if not update_key_match:
    errors.append("updateAPIKey(_:) not found")
else:
    body = update_key_match.group("body")
    if "invalidateCachedProviderHealthStatusIfNeeded(for: apiKey)" not in body:
        errors.append("Changing the API key must invalidate stale cached provider health")

refresh_match = re.search(
    r"func refreshSetupChecklist\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func runStartPreflight",
    app_state,
)
if not refresh_match:
    errors.append("refreshSetupChecklist() not found")
else:
    body = refresh_match.group("body")
    if "apiKey: self.providerHealthStatusForCurrentKey" not in body:
        errors.append("refreshSetupChecklist must use providerHealthStatusForCurrentKey so cached manual checks survive permission refreshes")

if errors:
    print("Provider health checklist cache verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Provider health checklist cache verification passed")
