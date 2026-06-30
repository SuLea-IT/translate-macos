#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

if "private var restartGeneration = UUID()" not in text:
    errors.append("AppState must track restartGeneration to isolate stale delayed restart tasks")

restart_match = re.search(r"private func rebuildRunningSessionIfNeeded\(oldValue: AppSettings\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func updateAudioPlayerVolumeIfNeeded", text)
if not restart_match:
    errors.append("AppState.rebuildRunningSessionIfNeeded(oldValue:) not found")
else:
    body = restart_match.group("body")
    for token in [
        "let generation = UUID()",
        "restartGeneration = generation",
        "restartTask?.cancel()",
        "restartTask = Task",
        "guard self.restartGeneration == generation else { return }",
        "await self.stop(cancelPendingRestart: false)",
        "await self.start()",
        "if self.restartGeneration == generation {",
        "self.restartTask = nil",
    ]:
        if token not in body:
            errors.append(f"rebuildRunningSessionIfNeeded must guard delayed restart lifecycle through {token}")
    sleep_idx = body.find("try await Task.sleep")
    generation_guard_idx = body.find("guard self.restartGeneration == generation else { return }", sleep_idx)
    stop_idx = body.find("await self.stop(cancelPendingRestart: false)")
    start_idx = body.find("await self.start()")
    cleanup_guard_idx = body.find("if self.restartGeneration == generation {", start_idx)
    cleanup_idx = body.find("self.restartTask = nil", cleanup_guard_idx)
    if -1 in [sleep_idx, generation_guard_idx, stop_idx, start_idx, cleanup_guard_idx, cleanup_idx] or not (sleep_idx < generation_guard_idx < stop_idx < start_idx < cleanup_guard_idx < cleanup_idx):
        errors.append("delayed restart must check generation before stopping, then only the current generation may clear restartTask")
    if "self.restartTask = nil" in body and "if self.restartGeneration == generation" not in body:
        errors.append("rebuildRunningSessionIfNeeded must not clear restartTask unconditionally")

for name, pattern in [
    ("stop(cancelPendingRestart:saveTranscriptImmediately:)", r"private func stop\(cancelPendingRestart: Bool, saveTranscriptImmediately: Bool = true\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    func requestStart"),
    ("stopRuntimeAfterConnectionFailure", r"private func stopRuntimeAfterConnectionFailure\(generation: UUID\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    private func connectionEvent"),
]:
    match = re.search(pattern, text)
    if not match:
        errors.append(f"AppState.{name} not found")
        continue
    body = match.group("body")
    if "restartGeneration = UUID()" not in body:
        errors.append(f"AppState.{name} must invalidate stale restart tasks through restartGeneration = UUID()")

if errors:
    print("Restart task generation guard verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Restart task generation guard verification passed")
