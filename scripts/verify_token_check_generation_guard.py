#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
text = path.read_text()
errors: list[str] = []

if "@State private var tokenCheckGeneration = UUID()" not in text:
    errors.append("SettingsView must track tokenCheckGeneration to isolate stale API token checks")

start_match = re.search(r"private func startTokenCheck\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func cancelTokenCheck", text)
if not start_match:
    errors.append("SettingsView.startTokenCheck() not found")
else:
    body = start_match.group("body")
    for token in [
        "tokenCheckTask?.cancel()",
        "let generation = UUID()",
        "tokenCheckGeneration = generation",
        "tokenCheckTask = Task",
        "try await appState.verifyGeminiToken()",
        "guard tokenCheckGeneration == generation, !Task.isCancelled else { return }",
        "isTokenValid = true",
        "isTokenValid = false",
        "tokenCheckError = error.localizedDescription",
        "if tokenCheckGeneration == generation",
        "tokenCheckTask = nil",
    ]:
        if token not in body:
            errors.append(f"startTokenCheck must guard token-check lifecycle through {token}")
    verify_idx = body.find("try await appState.verifyGeminiToken()")
    success_guard_idx = body.find("guard tokenCheckGeneration == generation, !Task.isCancelled else { return }", verify_idx)
    success_idx = body.find("isTokenValid = true")
    catch_idx = body.find("} catch")
    catch_guard_idx = body.find("guard tokenCheckGeneration == generation, !Task.isCancelled else { return }", catch_idx)
    failure_idx = body.find("isTokenValid = false", catch_idx)
    clear_idx = body.rfind("tokenCheckTask = nil")
    if -1 in [verify_idx, success_guard_idx, success_idx] or not (verify_idx < success_guard_idx < success_idx):
        errors.append("startTokenCheck must check generation after provider verification before marking success")
    if -1 in [catch_idx, catch_guard_idx, failure_idx] or not (catch_idx < catch_guard_idx < failure_idx):
        errors.append("startTokenCheck must check generation before publishing failure state")
    if clear_idx != -1 and "tokenCheckGeneration == generation" not in body[:clear_idx + len("tokenCheckTask = nil")]:
        errors.append("startTokenCheck must not clear tokenCheckTask without checking generation")

cancel_match = re.search(r"private func cancelTokenCheck\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private var glossaryImportContentTypes", text)
if not cancel_match:
    errors.append("SettingsView.cancelTokenCheck() not found")
else:
    body = cancel_match.group("body")
    for token in [
        "tokenCheckGeneration = UUID()",
        "tokenCheckTask?.cancel()",
        "tokenCheckTask = nil",
        "isCheckingToken = false",
    ]:
        if token not in body:
            errors.append(f"cancelTokenCheck must invalidate stale token checks through {token}")

if errors:
    print("Token check generation guard verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Token check generation guard verification passed")
