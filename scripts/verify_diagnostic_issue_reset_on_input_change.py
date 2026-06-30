#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

did_set_match = re.search(r"@Published private\(set\) var settings: AppSettings \{\n        didSet \{(?P<body>[\s\S]*?)\n        \}\n    \}", text)
if not did_set_match:
    errors.append("AppState.settings didSet not found")
else:
    body = did_set_match.group("body")
    for token in [
        "resetDiagnosticIssueIfNeeded(oldValue: oldValue)",
        "resetPreflightTestReportIfNeeded(oldValue: oldValue)",
    ]:
        if token not in body:
            errors.append(f"settings didSet must reset stale user-visible setup feedback through {token}")
    diagnostic_idx = body.find("resetDiagnosticIssueIfNeeded(oldValue: oldValue)")
    preflight_idx = body.find("resetPreflightTestReportIfNeeded(oldValue: oldValue)")
    if -1 in [diagnostic_idx, preflight_idx] or diagnostic_idx > preflight_idx:
        errors.append("settings didSet should clear stale diagnostic banners before resetting stale preflight reports")

helper_match = re.search(
    r"private func resetDiagnosticIssueIfNeeded\(oldValue: AppSettings\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func resetPreflightTestReportIfNeeded",
    text,
)
if not helper_match:
    errors.append("AppState.resetDiagnosticIssueIfNeeded(oldValue:) not found before preflight reset helper")
else:
    body = helper_match.group("body")
    for token in [
        "guard let issue = currentDiagnosticIssue else { return }",
        "let providerInputsChanged =",
        "oldValue.activeProvider != settings.activeProvider",
        "oldValue.apiKey != settings.apiKey",
        "let captureInputsChanged =",
        "oldValue.audioSource != settings.audioSource",
        "oldValue.selectedMicrophoneDeviceUID != settings.selectedMicrophoneDeviceUID",
        "switch issue.kind",
        "case .provider:",
        "guard providerInputsChanged else { return }",
        "case .permission, .capture:",
        "guard captureInputsChanged else { return }",
        "default:",
        "return",
        "setDiagnosticIssue(nil)",
    ]:
        if token not in body:
            errors.append(f"resetDiagnosticIssueIfNeeded must clear only diagnostics made stale by relevant setting changes through {token}")
    provider_idx = body.find("case .provider:")
    provider_guard_idx = body.find("guard providerInputsChanged else { return }", provider_idx)
    capture_idx = body.find("case .permission, .capture:")
    capture_guard_idx = body.find("guard captureInputsChanged else { return }", capture_idx)
    clear_idx = body.rfind("setDiagnosticIssue(nil)")
    if -1 in [provider_idx, provider_guard_idx, capture_idx, capture_guard_idx, clear_idx] or not (provider_idx < provider_guard_idx < capture_idx < capture_guard_idx < clear_idx):
        errors.append("resetDiagnosticIssueIfNeeded must gate provider and capture diagnostics before clearing the banner")

if errors:
    print("Diagnostic issue input-change reset verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Diagnostic issue input-change reset verification passed")
