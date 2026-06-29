#!/usr/bin/env python3
from pathlib import Path
import re
import sys
from typing import Optional

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = app_state_path.read_text()
errors: list[str] = []

helper_match = re.search(r"private func shouldContinueRuntimeConnection\(\) -> Bool \{(?P<body>[\s\S]*?)\n    \}", text)
if not helper_match:
    errors.append("AppState must centralize async connection cancellation checks in shouldContinueRuntimeConnection()")
else:
    body = helper_match.group("body")
    for token in ["!Task.isCancelled", "isRunning", "!userInitiatedStop"]:
        if token not in body:
            errors.append(f"shouldContinueRuntimeConnection must check {token}")

discard_match = re.search(r"private func discardAsyncClient\(_ candidate: GeminiLiveTranslateClient\) \{(?P<body>[\s\S]*?)\n    \}", text)
if not discard_match:
    errors.append("AppState must close stale async clients through discardAsyncClient(_:)")
else:
    body = discard_match.group("body")
    for token in ["if client === candidate", "client = nil", "candidate.close()"]:
        if token not in body:
            errors.append(f"discardAsyncClient must release stale client through {token}")


def method_body(name: str, next_signature: str) -> Optional[str]:
    pattern = rf"private func {re.escape(name)}[\s\S]*?\{{(?P<body>[\s\S]*?)\n    \}}\n\n    {next_signature}"
    match = re.search(pattern, text)
    return match.group("body") if match else None

reconnect_body = method_body("reconnectGeminiClient", "private func scheduleStopRuntimeAfterConnectionFailure")
if reconnect_body is None:
    errors.append("AppState.reconnectGeminiClient() not found")
else:
    for token in ["try await newClient.connect()", "guard shouldContinueRuntimeConnection() else", "discardAsyncClient(newClient)", "client = newClient"]:
        if token not in reconnect_body:
            errors.append(f"reconnectGeminiClient must guard stale WebSocket clients through {token}")
    connect_idx = reconnect_body.find("try await newClient.connect()")
    guard_idx = reconnect_body.find("guard shouldContinueRuntimeConnection() else", connect_idx)
    assign_idx = reconnect_body.find("client = newClient")
    if min(connect_idx, guard_idx, assign_idx) != -1 and not (connect_idx < guard_idx < assign_idx):
        errors.append("reconnectGeminiClient must check cancellation after connect before assigning client")
    catch_idx = reconnect_body.find("} catch")
    handle_idx = reconnect_body.find("handleConnectionEvent", catch_idx)
    catch_guard_idx = reconnect_body.find("guard shouldContinueRuntimeConnection() else", catch_idx)
    if catch_idx != -1 and handle_idx != -1 and not (catch_idx < catch_guard_idx < handle_idx):
        errors.append("reconnectGeminiClient must ignore connection failures from canceled/stopped reconnect attempts")

resume_body = method_body("resumeFromUsagePause", "private func runningUsageStatusMessage")
if resume_body is None:
    errors.append("AppState.resumeFromUsagePause(replayChunks:) not found")
else:
    for token in ["try await newClient.connect()", "guard shouldContinueRuntimeConnection() else", "discardAsyncClient(newClient)", "client = newClient", "client === newClient"]:
        if token not in resume_body:
            errors.append(f"resumeFromUsagePause must guard stale resumed WebSocket clients through {token}")
    connect_idx = resume_body.find("try await newClient.connect()")
    guard_idx = resume_body.find("guard shouldContinueRuntimeConnection() else", connect_idx)
    assign_idx = resume_body.find("client = newClient")
    if min(connect_idx, guard_idx, assign_idx) != -1 and not (connect_idx < guard_idx < assign_idx):
        errors.append("resumeFromUsagePause must check cancellation after connect before assigning client")
    loop_idx = resume_body.find("for chunk in replayChunks")
    send_idx = resume_body.find("await newClient.sendAudio(chunk.data)", loop_idx)
    loop_guard_idx = resume_body.find("guard shouldContinueRuntimeConnection(), client === newClient else", loop_idx)
    if min(loop_idx, loop_guard_idx, send_idx) != -1 and not (loop_idx < loop_guard_idx < send_idx):
        errors.append("resumeFromUsagePause must guard before each replay send")
    mark_idx = resume_body.find("usageEngine.markReplaySent(replayChunks)")
    post_loop_guard_idx = resume_body.find("guard shouldContinueRuntimeConnection(), client === newClient else", send_idx + len("await newClient.sendAudio(chunk.data)") if send_idx != -1 else 0)
    if mark_idx != -1 and not (send_idx < post_loop_guard_idx < mark_idx):
        errors.append("resumeFromUsagePause must guard after replay sends before marking usage resumed")
    catch_idx = resume_body.find("} catch")
    diagnostic_idx = resume_body.find("DiagnosticClassifier.from", catch_idx)
    catch_guard_idx = resume_body.find("guard shouldContinueRuntimeConnection() else", catch_idx)
    if catch_idx != -1 and diagnostic_idx != -1 and not (catch_idx < catch_guard_idx < diagnostic_idx):
        errors.append("resumeFromUsagePause must ignore resume failures from canceled/stopped attempts")

if errors:
    print("Async client cancellation guard verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Async client cancellation guard verification passed")
