#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

for context, pattern in [
    ("refreshSetupChecklist", r"func refreshSetupChecklist\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func runStartPreflight"),
    ("runStartPreflight", r"func runStartPreflight\(\) async -> SetupPreflightResult \{(?P<body>[\s\S]*?)\n    \}\n\n    func runPreflightTest"),
]:
    match = re.search(pattern, text)
    if not match:
        errors.append(f"AppState.{context} not found")
        continue
    body = match.group("body")
    if "publishSetupChecklist(checklist)" not in body:
        errors.append(f"AppState.{context} must publish checklist through publishSetupChecklist(checklist) so resolved setup feedback is cleared")
    if "setupChecklist = checklist" in body:
        errors.append(f"AppState.{context} must not assign setupChecklist directly and skip feedback cleanup")

api_status_match = re.search(
    r"private func updateSetupChecklist\(apiKeyStatus: ProviderHealthStatus\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func permissionStatus",
    text,
)
if not api_status_match:
    errors.append("AppState.updateSetupChecklist(apiKeyStatus:) not found")
else:
    body = api_status_match.group("body")
    for token in [
        "publishSetupChecklist(",
        "SetupChecklistState.derive(",
        "apiKey: apiKeyStatus",
    ]:
        if token not in body:
            errors.append(f"updateSetupChecklist(apiKeyStatus:) must publish derived checklist through {token}")
    if "setupChecklist = SetupChecklistState.derive" in body:
        errors.append("updateSetupChecklist(apiKeyStatus:) must not assign setupChecklist directly")

publish_match = re.search(
    r"private func publishSetupChecklist\(_ checklist: SetupChecklistState\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func clearResolvedSetupFeedback",
    text,
)
if not publish_match:
    errors.append("AppState.publishSetupChecklist(_:) not found before feedback cleanup helper")
else:
    body = publish_match.group("body")
    for token in [
        "setupChecklist = checklist",
        "clearResolvedSetupFeedback(using: checklist)",
    ]:
        if token not in body:
            errors.append(f"publishSetupChecklist must update checklist and clear resolved stale feedback through {token}")
    assign_idx = body.find("setupChecklist = checklist")
    clear_idx = body.find("clearResolvedSetupFeedback(using: checklist)")
    if -1 in [assign_idx, clear_idx] or not (assign_idx < clear_idx):
        errors.append("publishSetupChecklist must publish the current checklist before clearing resolved feedback")

clear_match = re.search(
    r"private func clearResolvedSetupFeedback\(using checklist: SetupChecklistState\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func setupIssueIsResolved",
    text,
)
if not clear_match:
    errors.append("AppState.clearResolvedSetupFeedback(using:) not found before setup resolution helper")
else:
    body = clear_match.group("body")
    for token in [
        "if let currentUserFacingError, setupErrorIsResolved(currentUserFacingError, by: checklist)",
        "self.currentUserFacingError = nil",
        "if let currentDiagnosticIssue, setupIssueIsResolved(currentDiagnosticIssue, by: checklist)",
        "setDiagnosticIssue(nil)",
    ]:
        if token not in body:
            errors.append(f"clearResolvedSetupFeedback must clear stale user-facing and diagnostic feedback through {token}")

issue_match = re.search(
    r"private func setupIssueIsResolved\(_ issue: DiagnosticIssue, by checklist: SetupChecklistState\) -> Bool \{(?P<body>[\s\S]*?)\n    \}\n\n    private func setupErrorIsResolved",
    text,
)
if not issue_match:
    errors.append("AppState.setupIssueIsResolved(_:by:) not found")
else:
    body = issue_match.group("body")
    for token in [
        "case .apiKeyMissing, .apiKeyInvalid:",
        "return !checklist.blockingIssues.contains(.apiKeyMissing) && !checklist.blockingIssues.contains(.apiKeyInvalid)",
        "case .microphonePermissionMissing:",
        "return !checklist.blockingIssues.contains(.microphonePermissionMissing)",
        "case .screenRecordingPermissionMissing:",
        "return !checklist.blockingIssues.contains(.screenRecordingPermissionMissing)",
        "return false",
    ]:
        if token not in body:
            errors.append(f"setupIssueIsResolved must clear only resolved setup diagnostics through {token}")

error_match = re.search(
    r"private func setupErrorIsResolved\(_ error: UserFacingError, by checklist: SetupChecklistState\) -> Bool \{(?P<body>[\s\S]*?)\n    \}\n\n    private func permissionStatus",
    text,
)
if not error_match:
    errors.append("AppState.setupErrorIsResolved(_:by:) not found")
else:
    body = error_match.group("body")
    for token in [
        "case .provider:",
        "return !checklist.blockingIssues.contains(.apiKeyMissing) && !checklist.blockingIssues.contains(.apiKeyInvalid)",
        "case .permission:",
        "return !checklist.blockingIssues.contains(.microphonePermissionMissing) && !checklist.blockingIssues.contains(.screenRecordingPermissionMissing)",
        "return false",
    ]:
        if token not in body:
            errors.append(f"setupErrorIsResolved must clear only resolved setup user errors through {token}")

if errors:
    print("Setup feedback resolution verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Setup feedback resolution verification passed")
