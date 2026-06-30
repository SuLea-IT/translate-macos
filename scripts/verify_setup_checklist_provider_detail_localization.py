#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
view_path = root / "LiveBuddy" / "Views" / "Settings" / "SetupChecklistView.swift"
text = view_path.read_text()
errors: list[str] = []

if "case .invalid(let message, _), .failed(let message, _):" in text and "return message" in text:
    errors.append("Setup checklist API-key detail must not show raw provider invalid/failed messages")

provider_detail = re.search(
    r"private var providerDetail: String \{(?P<body>[\s\S]*?)\n    \}\n\n    private func detail",
    text,
)
if not provider_detail:
    errors.append("SetupChecklistView.providerDetail not found")
else:
    body = provider_detail.group("body")
    for token in [
        "case .invalid, .failed:",
        "return localizedProviderIssueDetail(for: appState.setupChecklist.apiKey)",
    ]:
        if token not in body:
            errors.append(f"providerDetail must route invalid/failed provider statuses through localized diagnostics via {token}")

helper = re.search(
    r"private func localizedProviderIssueDetail\(for status: ProviderHealthStatus\) -> String \{(?P<body>[\s\S]*?)\n    \}\n\n    private func detail",
    text,
)
if not helper:
    errors.append("SetupChecklistView must define localizedProviderIssueDetail(for:) before generic permission detail")
else:
    body = helper.group("body")
    for token in [
        "DiagnosticClassifier.from(providerStatus: status)",
        "return appState.t(issue.messageKey)",
        "return appState.t(.verificationFailed)",
    ]:
        if token not in body:
            errors.append(f"localizedProviderIssueDetail(for:) must localize diagnostic text and fall back safely through {token}")

if errors:
    print("Setup checklist provider detail localization verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Setup checklist provider detail localization verification passed")
