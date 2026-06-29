#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
usage_path = root / "LiveBuddy" / "Models" / "UsageControl.swift"
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
usage_text = usage_path.read_text()
app_state_text = app_state_path.read_text()
errors = []

ingest_match = re.search(
    r"mutating func ingest\(chunk: BufferedAudioChunk, level: Float, now: Date\) -> UsageControlDecision \{(?P<body>[\s\S]*?)\n    \}\n\n    mutating func markResumed",
    usage_text,
)
if not ingest_match:
    errors.append("UsageControlEngine.ingest body not found")
else:
    body = ingest_match.group("body")
    if "countSent(chunk.duration)" in body:
        errors.append("UsageControlEngine.ingest must not count live audio before AppState confirms the chunk entered the send queue")
    if body.count("return .send") < 2:
        errors.append("UsageControlEngine.ingest should still decide live chunks are sendable without accounting them early")

mark_sent_match = re.search(
    r"mutating func markSent\(_ chunk: BufferedAudioChunk\) \{(?P<body>[\s\S]*?)\n    \}\n\n    mutating func markReplaySent",
    usage_text,
)
if not mark_sent_match:
    errors.append("UsageControlEngine must expose markSent(_:) so AppState can account only queued live chunks")
else:
    body = mark_sent_match.group("body")
    for token in [
        "countSent(chunk.duration)",
        "refreshSnapshot(runtimeState: snapshot.runtimeState)",
    ]:
        if token not in body:
            errors.append(f"UsageControlEngine.markSent(_:) must update live-send accounting through {token}")

handle_match = re.search(
    r"private func handleCapturedAudio\(_ data: Data, source: AudioSource, level: Float\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func recordAudioChunk",
    app_state_text,
)
if not handle_match:
    errors.append("AppState.handleCapturedAudio() not found")
else:
    body = handle_match.group("body")
    send_match = re.search(r"if decision\.shouldSend \{(?P<body>[\s\S]*?)\n        \}", body)
    if not send_match:
        errors.append("AppState.handleCapturedAudio must handle decision.shouldSend")
    else:
        send_body = send_match.group("body")
        for token in [
            "if enqueueAudioSend(data) {",
            "sentChunkCount += 1",
            "usageEngine.markSent(chunk)",
            "usageSnapshot = usageEngine.snapshot",
            "saveUsageLedger()",
        ]:
            if token not in send_body:
                errors.append(f"AppState.handleCapturedAudio must account a live chunk only after enqueue success through {token}")
        enqueue_idx = send_body.find("if enqueueAudioSend(data) {")
        count_idx = send_body.find("sentChunkCount += 1")
        mark_idx = send_body.find("usageEngine.markSent(chunk)")
        snapshot_idx = send_body.find("usageSnapshot = usageEngine.snapshot")
        save_idx = send_body.find("saveUsageLedger()")
        if min(enqueue_idx, count_idx, mark_idx, snapshot_idx, save_idx) != -1 and not (
            enqueue_idx < count_idx < mark_idx < snapshot_idx < save_idx
        ):
            errors.append("AppState.handleCapturedAudio must enqueue first, then increment sent count, mark usage, publish snapshot, and save ledger")
        prefix = send_body[:enqueue_idx] if enqueue_idx != -1 else send_body
        if "sentChunkCount += 1" in prefix or "saveUsageLedger()" in prefix or "usageEngine.markSent" in prefix:
            errors.append("AppState.handleCapturedAudio must not update sent accounting before enqueueAudioSend(data) succeeds")

enqueue_match = re.search(
    r"private func enqueueAudioSend\(_ data: Data\) -> Bool \{(?P<body>[\s\S]*?)\n    \}\n\n    private func resetAudioSendPipeline",
    app_state_text,
)
if not enqueue_match:
    errors.append("AppState.enqueueAudioSend(_:) must return Bool so callers can avoid counting dropped chunks")
else:
    body = enqueue_match.group("body")
    for token in [
        "guard !data.isEmpty, let client else { return false }",
        "guard pendingAudioSendChunks < maxPendingAudioSendChunks else {",
        "return false",
        "audioSendTask = Task",
        "return true",
    ]:
        if token not in body:
            errors.append(f"AppState.enqueueAudioSend(_:) must report enqueue success/failure through {token}")
    task_idx = body.find("audioSendTask = Task")
    true_idx = body.rfind("return true")
    if min(task_idx, true_idx) != -1 and not (task_idx < true_idx):
        errors.append("AppState.enqueueAudioSend(_:) must return true only after the send task is installed")

if errors:
    print("Usage control sent accounting verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Usage control sent accounting verification passed")
