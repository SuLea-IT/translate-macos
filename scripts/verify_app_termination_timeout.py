#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_delegate_path = root / "LiveBuddy" / "App" / "AppDelegate.swift"
text = app_delegate_path.read_text()
errors: list[str] = []

for token in [
    "private static let terminationStopTimeoutNanoseconds",
    "private enum TerminationStopResult",
    "private final class TerminationStopGate",
    "private var terminationStopTask: Task<Void, Never>?",
    "private var terminationTimeoutTask: Task<Void, Never>?",
    "private func waitForRuntimeStopBeforeTermination(_ appState: AppState) async -> TerminationStopResult",
]:
    if token not in text:
        errors.append(f"AppDelegate must bound quit-time runtime stop through {token}")

should_match = re.search(r"func applicationShouldTerminate\(_ sender: NSApplication\) -> NSApplication.TerminateReply \{(?P<body>[\s\S]*?)\n    \}", text)
if not should_match:
    errors.append("AppDelegate.applicationShouldTerminate(_:) not found")
else:
    body = should_match.group("body")
    for token in [
        "terminationTask = Task",
        "await self.waitForRuntimeStopBeforeTermination(appState)",
        "NSApp.reply(toApplicationShouldTerminate: true)",
        "terminationTask = nil",
    ]:
        if token not in body:
            errors.append(f"applicationShouldTerminate must coordinate bounded shutdown through {token}")
    if "await appState?.stop()" in body or "await appState.stop()" in body:
        errors.append("applicationShouldTerminate must not directly await AppState.stop() without a timeout race")

wait_match = re.search(r"private func waitForRuntimeStopBeforeTermination\(_ appState: AppState\) async -> TerminationStopResult \{(?P<body>[\s\S]*?)\n    \}", text)
if not wait_match:
    errors.append("waitForRuntimeStopBeforeTermination(_:) not found")
else:
    body = wait_match.group("body")
    for token in [
        "let gate = TerminationStopGate()",
        "let timeout = Self.terminationStopTimeoutNanoseconds",
        "terminationStopTask = Task { @MainActor [weak appState, gate] in",
        "await appState?.stopForTermination()",
        "gate.finish(.stopped)",
        "terminationTimeoutTask = Task { [gate, timeout] in",
        "try? await Task.sleep(nanoseconds: timeout)",
        "guard !Task.isCancelled else { return }",
        "gate.finish(.timedOut)",
        "let result = await gate.wait()",
        "clearTerminationStopTasks()",
        "return result",
    ]:
        if token not in body:
            errors.append(f"waitForRuntimeStopBeforeTermination must race stop with timeout through {token}")
    if "await appState?.stop()" in body or "await appState.stop()" in body:
        errors.append("waitForRuntimeStopBeforeTermination must use stopForTermination() so transcript persistence is deferred to applicationWillTerminate")

clear_match = re.search(r"private func clearTerminationStopTasks\(\) \{(?P<body>[\s\S]*?)\n    \}", text)
if not clear_match:
    errors.append("AppDelegate.clearTerminationStopTasks() not found")
else:
    body = clear_match.group("body")
    for token in [
        "terminationStopTask?.cancel()",
        "terminationStopTask = nil",
        "terminationTimeoutTask?.cancel()",
        "terminationTimeoutTask = nil",
    ]:
        if token not in body:
            errors.append(f"clearTerminationStopTasks must release quit helper tasks through {token}")

deinit_match = re.search(r"deinit \{(?P<body>[\s\S]*?)\n    \}", text)
if not deinit_match:
    errors.append("AppDelegate.deinit not found")
else:
    body = deinit_match.group("body")
    for token in ["terminationTask?.cancel()", "clearTerminationStopTasks()", "removeShowCaptionObserver()"]:
        if token not in body:
            errors.append(f"AppDelegate.deinit must release termination resources through {token}")

if errors:
    print("App termination timeout verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("App termination timeout verification passed")
