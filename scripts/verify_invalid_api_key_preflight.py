#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
permission = (root / "LiveBuddy" / "Models" / "PermissionStatus.swift").read_text()
provider = (root / "LiveBuddy" / "Models" / "ProviderHealthStatus.swift").read_text()
user_error = (root / "LiveBuddy" / "Models" / "UserFacingError.swift").read_text()
diagnostic = (root / "LiveBuddy" / "Models" / "DiagnosticIssue.swift").read_text()
setup_tests = (root / "LiveBuddyTests" / "SetupChecklistTests.swift").read_text()
error_tests = (root / "LiveBuddyTests" / "UserFacingErrorTests.swift").read_text()
errors: list[str] = []

if "case apiKeyInvalid" not in permission:
    errors.append("SetupBlockingIssue must include apiKeyInvalid for known-bad keys")

for token in [
    "case .missing:",
    "issues.append(.apiKeyMissing)",
    "case .invalid:",
    "issues.append(.apiKeyInvalid)",
]:
    if token not in permission:
        errors.append(f"SetupChecklistState.derive must distinguish missing and invalid API keys through {token}")

if "case .missing, .invalid:" not in provider:
    errors.append("ProviderHealthStatus.blocksStart must block known invalid keys as well as missing keys")
if "case .unchecked, .checking, .valid, .failed:" not in provider:
    errors.append("ProviderHealthStatus.blocksStart must not block unchecked/checking/valid/transient failed states")

for token in [
    "static let apiKeyInvalid = UserFacingError(",
    "titleKey: .diagnosticAPIKeyInvalidTitle",
    "messageKey: .diagnosticAPIKeyInvalidMessage",
    "recoveryKey: .diagnosticOpenProviderRecovery",
    "case .apiKeyInvalid:",
    "return .apiKeyInvalid",
]:
    if token not in user_error:
        errors.append(f"UserFacingError must map known invalid API keys to provider recovery through {token}")

if "case .apiKeyInvalid:" not in diagnostic or "diagnosticAPIKeyInvalidTitle" not in diagnostic:
    errors.append("DiagnosticClassifier.from(blockingIssue:) must map apiKeyInvalid to the invalid-key diagnostic")

for token in [
    "invalidApiKeyBlocksStartAfterManualVerification",
    "apiKey: .invalid(message:",
    "#expect(state.blockingIssues.contains(.apiKeyInvalid))",
    "preflightBlocksWhenApiKeyIsKnownInvalid",
    "#expect(result == .blocked(.apiKeyInvalid))",
    "transientProviderFailureDoesNotBlockStart",
    "apiKey: .failed(message:",
    "#expect(state.blockingIssues.contains(.apiKeyInvalid) == false)",
]:
    if token not in setup_tests:
        errors.append(f"SetupChecklistTests must cover invalid-vs-transient provider status through {token}")

for token in [
    "invalidApiKeyMapsToProviderRecovery",
    "UserFacingError.apiKeyInvalid",
    "#expect(error.kind == .provider)",
    "#expect(error.action == .openProviderSettings)",
    "#expect(error.titleKey == .diagnosticAPIKeyInvalidTitle)",
]:
    if token not in error_tests:
        errors.append(f"UserFacingErrorTests must cover invalid API key recovery through {token}")

if errors:
    print("Invalid API key preflight verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Invalid API key preflight verification passed")
