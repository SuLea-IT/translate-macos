#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
diagnostic = root / "LiveBuddy" / "Models" / "DiagnosticIssue.swift"
tests = root / "LiveBuddyTests" / "DiagnosticIssueTests.swift"

diagnostic_text = diagnostic.read_text()
test_text = tests.read_text()
errors: list[str] = []

if "providerInvalidStatusFallsBackToAPIKeyDiagnostic" not in test_text:
    errors.append("Diagnostic tests must cover unrecognized invalid provider status fallback")
if "providerFailedStatusFallsBackToProviderDiagnostic" not in test_text:
    errors.append("Diagnostic tests must cover unrecognized failed provider status fallback")

expected_provider_switch_tokens = [
    "case .invalid(let message, _):",
    "fallbackCode: .apiKeyInvalid",
    "case .failed(let message, _):",
    "fallbackCode: .providerServerError",
]
for token in expected_provider_switch_tokens:
    if token not in diagnostic_text:
        errors.append(f"Provider status diagnostics must use explicit fallback through {token}")

fallback_switch_start = diagnostic_text.find("if let fallbackCode {")
fallback_switch = diagnostic_text[fallback_switch_start:] if fallback_switch_start != -1 else ""
if "case .apiKeyInvalid:" not in fallback_switch:
    errors.append("Diagnostic classifier fallback switch must map .apiKeyInvalid to the API key recovery issue")
if "return issue(.apiKeyInvalid" not in fallback_switch:
    errors.append("Diagnostic classifier must return a concrete API-key issue for invalid-status fallback")

if errors:
    print("Provider health diagnostic fallback verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)
print("Provider health diagnostic fallback verification passed")
