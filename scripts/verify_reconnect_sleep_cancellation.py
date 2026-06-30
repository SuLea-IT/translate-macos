#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

match = re.search(
    r"private func scheduleReconnect\(after event: LiveConnectionEvent\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func shouldContinueRuntimeConnection",
    text,
)
if not match:
    errors.append("AppState.scheduleReconnect(after:) not found")
else:
    body = match.group("body")
    if "try? await Task.sleep(nanoseconds: nanoseconds)" in body:
        errors.append("scheduleReconnect must not ignore sleep cancellation with try? before reconnecting")
    for token in [
        "reconnectTask = Task { [weak self] in",
        "let nanoseconds = UInt64(max(delay, 0) * 1_000_000_000)",
        "do {",
        "try await Task.sleep(nanoseconds: nanoseconds)",
        "} catch {",
        "return",
        "guard !Task.isCancelled else { return }",
        "await self?.reconnectGeminiClient()",
    ]:
        if token not in body:
            errors.append(f"scheduleReconnect must stop cancelled reconnect sleeps before touching runtime state through {token}")
    task_idx = body.find("reconnectTask = Task { [weak self] in")
    sleep_idx = body.find("try await Task.sleep(nanoseconds: nanoseconds)", task_idx)
    catch_idx = body.find("} catch {", sleep_idx)
    guard_idx = body.find("guard !Task.isCancelled else { return }", catch_idx)
    reconnect_idx = body.find("await self?.reconnectGeminiClient()", guard_idx)
    if -1 in [task_idx, sleep_idx, catch_idx, guard_idx, reconnect_idx] or not (task_idx < sleep_idx < catch_idx < guard_idx < reconnect_idx):
        errors.append("scheduleReconnect must sleep, return on cancellation, then check cancellation before reconnectGeminiClient()")

if errors:
    print("Reconnect sleep cancellation verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Reconnect sleep cancellation verification passed")
