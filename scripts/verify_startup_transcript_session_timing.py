#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = app_state_path.read_text()
errors: list[str] = []

start_match = re.search(r"func start\(\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func stop", text)
if not start_match:
    errors.append("AppState.start() not found")
else:
    body = start_match.group("body")
    for token in ["try await client.connect()", "try await startCapture()", "beginTranscriptSession()", "isRunning = true"]:
        if token not in body:
            errors.append(f"AppState.start() must include {token}")
    connect_index = body.find("try await client.connect()")
    capture_index = body.find("try await startCapture()")
    begin_index = body.find("beginTranscriptSession()")
    running_index = body.find("isRunning = true")
    if begin_index != -1 and connect_index != -1 and begin_index < connect_index:
        errors.append("AppState.start() must not create a transcript session before the Gemini connection succeeds")
    if begin_index != -1 and capture_index != -1 and begin_index < capture_index:
        errors.append("AppState.start() must not create a transcript session before audio capture starts successfully")
    if begin_index != -1 and running_index != -1 and begin_index > running_index:
        errors.append("AppState.start() must create the transcript session before marking the app as running")
    catch_index = body.find("} catch {")
    if catch_index != -1 and begin_index != -1 and begin_index < catch_index and capture_index != -1 and begin_index < capture_index:
        errors.append("Startup failure path can still persist an empty transcript session")

finish_match = re.search(r"private func finishTranscriptSession\(saveImmediately: Bool = true\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func deleteTranscriptSession", text)
if not finish_match:
    errors.append("AppState.finishTranscriptSession(saveImmediately:) not found")
else:
    body = finish_match.group("body")
    if "guard let sessionID = currentSessionID else { return }" not in body:
        errors.append("finishTranscriptSession must be a no-op when startup failed before a transcript session was created")

if errors:
    print("Startup transcript timing verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Startup transcript timing verification passed")
