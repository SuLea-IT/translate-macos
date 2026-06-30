#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Utilities" / "PCM16AudioProcessor.swift"
text = path.read_text()
errors: list[str] = []

append_match = re.search(r"nonisolated func append\(_ data: Data\) \{(?P<body>[\s\S]*?)\n    \}\n\n    nonisolated func reset", text)
if not append_match:
    errors.append("PCM16Chunker.append(_:) not found")
else:
    body = append_match.group("body")
    for token in [
        "var chunks: [Data] = []",
        "lock.lock()",
        "lock.unlock()",
        "chunks.append(Data(chunk))",
        "for chunk in chunks {",
        "onChunk(chunk)",
    ]:
        if token not in body:
            errors.append(f"PCM16Chunker.append(_:) must collect chunks under lock and call callbacks after unlock through {token}")

    lock_idx = body.find("lock.lock()")
    unlock_idx = body.find("lock.unlock()")
    first_callback_idx = body.find("onChunk")
    if -1 in [lock_idx, unlock_idx, first_callback_idx] or not (lock_idx < unlock_idx < first_callback_idx):
        errors.append("PCM16Chunker.append(_:) must not call onChunk while holding the pending-buffer lock")

    if "defer { lock.unlock() }" in body:
        errors.append("PCM16Chunker.append(_:) must not use defer unlock around callback emission; callbacks must happen after an explicit unlock")

    while_match = re.search(r"while pending\.count >= chunkSize \{(?P<loop>[\s\S]*?)\n        \}", body)
    if not while_match:
        errors.append("PCM16Chunker.append(_:) must keep chunk extraction in a pending-size loop")
    else:
        loop = while_match.group("loop")
        if "onChunk" in loop:
            errors.append("PCM16Chunker.append(_:) must not call onChunk inside the locked extraction loop")
        for token in ["let chunk = pending.prefix(chunkSize)", "chunks.append(Data(chunk))", "pending.removeFirst(chunkSize)"]:
            if token not in loop:
                errors.append(f"PCM16Chunker.append(_:) must preserve chunking behavior through {token}")

reset_match = re.search(r"nonisolated func reset\(\) \{(?P<body>[\s\S]*?)\n    \}", text)
if not reset_match:
    errors.append("PCM16Chunker.reset() not found")
else:
    body = reset_match.group("body")
    for token in ["lock.lock()", "defer { lock.unlock() }", "pending.removeAll(keepingCapacity: true)"]:
        if token not in body:
            errors.append(f"PCM16Chunker.reset() must keep pending-buffer lock protection through {token}")

if errors:
    print("PCM16 chunker lock-scope verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("PCM16 chunker lock-scope verification passed")
