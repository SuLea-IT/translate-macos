#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
runner = (root / "LiveBuddy" / "Services" / "PreflightTestRunner.swift").read_text()
tests = (root / "LiveBuddyTests" / "PreflightTestTests.swift").read_text()
errors: list[str] = []

provider_match = re.search(
    r"private func runProvider\(settings: AppSettings, report: PreflightTestReport, update: ReportUpdate\) async -> PreflightTestReport \{(?P<body>[\s\S]*?)\n    \}\n\n    private func runPermissions",
    runner,
)
if not provider_match:
    errors.append("PreflightTestRunner.runProvider(...) not found")
else:
    body = provider_match.group("body")
    if "case .invalid(let message, _), .failed(let message, _):" in body or "message: message" in body:
        errors.append("runProvider must not expose raw provider messages for user-visible preflight failures")
    for token in [
        "case .invalid, .failed:",
        "let messageKey = providerFailureMessageKey(status)",
        "report = report.updating(.apiKey, state: .failed, messageKey: messageKey)",
    ]:
        if token not in body:
            errors.append(f"runProvider must localize provider failures through {token}")

helper_match = re.search(
    r"private func providerFailureMessageKey\(_ status: ProviderHealthStatus\) -> InterfaceText \{(?P<body>[\s\S]*?)\n    \}\n\n    private func runPermissions",
    runner,
)
if not helper_match:
    errors.append("PreflightTestRunner.providerFailureMessageKey(_:) not found")
else:
    body = helper_match.group("body")
    for token in [
        "if let issue = DiagnosticClassifier.from(providerStatus: status)",
        "return issue.titleKey",
        "case .invalid:",
        "return .diagnosticAPIKeyInvalidTitle",
        "case .failed:",
        "return .diagnosticProviderErrorTitle",
    ]:
        if token not in body:
            errors.append(f"providerFailureMessageKey must map provider failures through {token}")

for token in [
    "runnerLocalizesProviderFailureMessages",
    "ProviderHealthStatus.invalid(message: \"API_KEY_INVALID: bad key\", checkedAt: Date())",
    "#expect(apiKey?.messageKey == .diagnosticAPIKeyInvalidTitle)",
    "#expect(apiKey?.message.isEmpty == true)",
]:
    if token not in tests:
        errors.append(f"PreflightTestTests must cover provider failure localization through {token}")

if errors:
    print("Preflight provider failure localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Preflight provider failure localization verification passed")
