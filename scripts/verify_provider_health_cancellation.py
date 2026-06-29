#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
provider_path = root / "LiveBuddy" / "Services" / "ProviderHealthService.swift"
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
provider = provider_path.read_text()
app_state = app_state_path.read_text()
errors: list[str] = []

verify_match = re.search(r"func verify\(apiKey: String, now: Date = Date\(\)\) async -> ProviderHealthStatus \{(?P<body>[\s\S]*?)\n    \}\n\}", provider)
if not verify_match:
    errors.append("ProviderHealthService.verify(apiKey:) not found")
else:
    body = verify_match.group("body")
    if body.count("Task.isCancelled") < 2:
        errors.append("ProviderHealthService.verify must check Task.isCancelled before and after awaiting ping")
    ping_idx = body.find("await ping(trimmed)")
    first_cancel = body.find("Task.isCancelled")
    second_cancel = body.find("Task.isCancelled", ping_idx)
    if ping_idx == -1:
        errors.append("ProviderHealthService.verify must still await ping(trimmed)")
    elif first_cancel == -1 or first_cancel > ping_idx:
        errors.append("ProviderHealthService.verify must avoid starting provider ping after cancellation")
    elif second_cancel == -1:
        errors.append("ProviderHealthService.verify must ignore provider ping results after cancellation")
    if "isCancellationError(error)" not in body or ".unchecked" not in body:
        errors.append("ProviderHealthService.verify must map explicit cancellation errors to an unchecked/no-diagnostic status")

if "private static func isCancellationError(_ error: Error) -> Bool" not in provider:
    errors.append("ProviderHealthService must centralize CancellationError / URLError.cancelled detection")
for token in ["error is CancellationError", "NSURLErrorCancelled", "URLError.Code.cancelled"]:
    if token not in provider:
        errors.append(f"ProviderHealthService cancellation detection must include {token}")

factory_match = re.search(r"static let geminiDefault = ProviderHealthService \{ apiKey in(?P<body>[\s\S]*?)\n    \}\n\n    private static func pingGeminiModel", provider)
if not factory_match:
    errors.append("ProviderHealthService.geminiDefault not found")
else:
    body = factory_match.group("body")
    for token in ["Task.isCancelled", "return .failure(CancellationError())", "isCancellationError(error)"]:
        if token not in body:
            errors.append(f"ProviderHealthService.geminiDefault must stop retrying cancelled checks through {token}")
    loop_idx = body.find("for model in modelsToTry")
    ping_idx = body.find("try await pingGeminiModel")
    cancel_idx = body.find("Task.isCancelled", loop_idx)
    if min(loop_idx, ping_idx, cancel_idx) != -1 and not (loop_idx < cancel_idx < ping_idx):
        errors.append("ProviderHealthService.geminiDefault must check cancellation before each model ping")

ping_match = re.search(r"private static func pingGeminiModel\([\s\S]*?\) async throws \{(?P<body>[\s\S]*?)\n    \}\n", provider)
if not ping_match:
    errors.append("ProviderHealthService.pingGeminiModel not found")
else:
    body = ping_match.group("body")
    if body.count("try Task.checkCancellation()") < 2:
        errors.append("ProviderHealthService.pingGeminiModel must check cancellation before and after URLSession.data(for:)")
    for token in ["catch is CancellationError", "error.code == .cancelled", "throw CancellationError()"]:
        if token not in body:
            errors.append(f"ProviderHealthService.pingGeminiModel must propagate URL cancellation through {token}")

app_match = re.search(r"func verifyGeminiToken\(\) async throws \{(?P<body>[\s\S]*?)\n    \}\n\n", app_state)
if not app_match:
    errors.append("AppState.verifyGeminiToken() not found")
else:
    body = app_match.group("body")
    verify_idx = body.find("await providerHealthService.verify(apiKey: settings.apiKey)")
    before = body.find("try Task.checkCancellation()")
    after = body.find("try Task.checkCancellation()", verify_idx)
    if verify_idx == -1:
        errors.append("AppState.verifyGeminiToken must still await providerHealthService.verify")
    elif before == -1 or before > verify_idx:
        errors.append("AppState.verifyGeminiToken must check cancellation before the provider request")
    elif after == -1:
        errors.append("AppState.verifyGeminiToken must check cancellation before mutating diagnostics after the provider request")

if errors:
    print("Provider health cancellation verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Provider health cancellation verification passed")
