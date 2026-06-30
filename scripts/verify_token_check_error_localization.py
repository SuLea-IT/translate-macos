#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
settings = (root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift").read_text()
errors: list[str] = []

if "private func localizedTokenCheckError(_ error: Error) -> String" not in settings:
    errors.append("SettingsView must localize app-owned API token check errors through localizedTokenCheckError(_:)")

helper = re.search(
    r"private func localizedTokenCheckError\(_ error: Error\) -> String \{(?P<body>[\s\S]*?)\n    \}\n\n    private var glossaryImportContentTypes",
    settings,
)
if not helper:
    errors.append("localizedTokenCheckError(_:) must live near token-check helpers")
else:
    body = helper.group("body")
    diagnostic_idx = body.find("if let issue = appState.currentDiagnosticIssue")
    message_idx = body.find("let message = error.localizedDescription.trimmingCharacters(in: .whitespacesAndNewlines)")
    if diagnostic_idx == -1:
        errors.append("localizedTokenCheckError(_:) must prefer the localized currentDiagnosticIssue from provider verification failures")
    elif message_idx == -1 or diagnostic_idx > message_idx:
        errors.append("localizedTokenCheckError(_:) must read currentDiagnosticIssue before falling back to raw error.localizedDescription")
    for token in [
        "issue.kind == .provider || issue.kind == .network",
        "return appState.t(issue.messageKey)",
        "let message = error.localizedDescription.trimmingCharacters(in: .whitespacesAndNewlines)",
        'message == "Verification failed"',
        "return appState.t(.verificationFailed)",
        'message == "API Key cannot be empty"',
        "return appState.t(.apiKeyMissingMessage)",
        "return message.isEmpty ? appState.t(.verificationFailed) : message",
    ]:
        if token not in body:
            errors.append(f"localizedTokenCheckError(_:) must map fixed app errors but preserve details through {token}")

start = re.search(
    r"private func startTokenCheck\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func cancelTokenCheck",
    settings,
)
if not start:
    errors.append("startTokenCheck() not found")
else:
    body = start.group("body")
    if "tokenCheckError = localizedTokenCheckError(error)" not in body:
        errors.append("startTokenCheck catch must publish localizedTokenCheckError(error)")
    if "tokenCheckError = error.localizedDescription" in body:
        errors.append("startTokenCheck catch must not publish raw localizedDescription directly")

if errors:
    print("Token check error localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Token check error localization verification passed")
