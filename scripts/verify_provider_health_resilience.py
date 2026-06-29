#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
provider = root / "LiveBuddy" / "Services" / "ProviderHealthService.swift"
text = provider.read_text()
errors: list[str] = []

for token in [
    "private static let requestTimeout",
    "URLSessionConfiguration.ephemeral",
    "configuration.timeoutIntervalForRequest = requestTimeout",
    "configuration.timeoutIntervalForResource = requestTimeout",
    "URLSession(configuration: configuration)",
    "session.invalidateAndCancel()",
]:
    if token not in text:
        errors.append(f"ProviderHealthService must use bounded API verification networking through {token}")

if "URLSession.shared.data(for:" in text:
    errors.append("ProviderHealthService must not use URLSession.shared for API key verification")

for token in [
    "catch let error as URLError where error.code == .timedOut",
    "Timed out after",
]:
    if token not in text:
        errors.append(f"ProviderHealthService must surface timeout failures through {token}")

if errors:
    print("Provider health resilience verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)
print("Provider health resilience verification passed")
