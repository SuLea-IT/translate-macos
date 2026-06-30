#!/usr/bin/env python3
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
app_state = (root / "LiveBuddy" / "Models" / "AppState.swift").read_text()
interface = (root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift").read_text()

errors = []

handle_match = re.search(r"private func handleCapturedAudio\(_ data: Data, source: AudioSource, level: Float\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func recordAudioChunk", app_state)
if not handle_match:
    errors.append("AppState.handleCapturedAudio(_:source:level:) not found")
else:
    body = handle_match.group("body")
    if "let previousUsageSnapshot = usageSnapshot" not in body:
        errors.append("handleCapturedAudio must capture the previous usage snapshot before ingesting audio")
    if "logUsageBufferOverflowIfNeeded(previousSnapshot: previousUsageSnapshot)" not in body:
        errors.append("handleCapturedAudio must log buffer overflow transitions after updating usageSnapshot")
    previous_idx = body.find("let previousUsageSnapshot = usageSnapshot")
    ingest_idx = body.find("let decision = usageEngine.ingest")
    log_idx = body.find("logUsageBufferOverflowIfNeeded(previousSnapshot: previousUsageSnapshot)")
    if previous_idx == -1 or ingest_idx == -1 or log_idx == -1 or not (previous_idx < ingest_idx < log_idx):
        errors.append("overflow logging must happen after ingest using a snapshot captured before ingest")

helper_match = re.search(r"private func logUsageBufferOverflowIfNeeded\(previousSnapshot: LiveUsageSnapshot\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func recordAudioChunk", app_state)
if not helper_match:
    errors.append("AppState.logUsageBufferOverflowIfNeeded(previousSnapshot:) not found")
else:
    body = helper_match.group("body")
    for token in [
        "guard !previousSnapshot.resumeBufferOverflowed, usageSnapshot.resumeBufferOverflowed else { return }",
        "appendLog(localizedStatus(.statusResumeBufferLimited), level: .error)",
    ]:
        if token not in body:
            errors.append(f"overflow logging helper must include {token}")

if "case statusResumeBufferLimited" not in interface or interface.count(".statusResumeBufferLimited:") != 8:
    errors.append("statusResumeBufferLimited must remain localized for all interface languages")

if errors:
    print("usage buffer overflow log verification failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("usage buffer overflow log verification passed")
