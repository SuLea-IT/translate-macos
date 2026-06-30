#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
app_delegate_path = root / "LiveBuddy" / "App" / "AppDelegate.swift"
app_state = app_state_path.read_text()
app_delegate = app_delegate_path.read_text()
errors: list[str] = []

flush_match = re.search(
    r"func flushPendingStateBeforeTermination\(\) \{(?P<body>[\s\S]*?)\n    \}",
    app_state,
)
if not flush_match:
    errors.append("AppState.flushPendingStateBeforeTermination() not found")
else:
    body = flush_match.group("body")
    for token in [
        "finishTranscriptSession()",
        "saveAPIKeyImmediately()",
        "saveSettingsImmediately()",
        "saveTranscriptSessionsImmediately()",
        "saveUsageLedger()",
    ]:
        if token not in body:
            errors.append(f"Termination flush must persist pending state through {token}")
    finish_idx = body.find("finishTranscriptSession()")
    transcript_save_idx = body.find("saveTranscriptSessionsImmediately()")
    if -1 not in (finish_idx, transcript_save_idx) and not (finish_idx < transcript_save_idx):
        errors.append("Termination flush must finalize the active transcript session before saving transcripts")

finish_match = re.search(
    r"private func finishTranscriptSession\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func deleteTranscriptSession",
    app_state,
)
if not finish_match:
    errors.append("AppState.finishTranscriptSession() not found")
else:
    body = finish_match.group("body")
    for token in [
        "if !captionDraft.isEmpty",
        "appendDisplayedCaption(line)",
        "appendCurrentTranscriptLine(from: line)",
        "session.endedAt = Date()",
        "saveTranscriptSessionsImmediately()",
    ]:
        if token not in body:
            errors.append(f"finishTranscriptSession() must close out live transcript drafts through {token}")

will_terminate_match = re.search(
    r"func applicationWillTerminate\(_ notification: Notification\) \{(?P<body>[\s\S]*?)\n    \}",
    app_delegate,
)
if not will_terminate_match:
    errors.append("AppDelegate.applicationWillTerminate(_:) not found")
else:
    body = will_terminate_match.group("body")
    if "appState?.flushPendingStateBeforeTermination()" not in body:
        errors.append("AppDelegate must flush pending state during applicationWillTerminate")

deinit_match = re.search(r"deinit \{(?P<body>[\s\S]*?)\n    \}", app_state)
if not deinit_match:
    errors.append("AppState.deinit not found")
else:
    body = deinit_match.group("body")
    if "flushPendingStateBeforeTermination()" not in body:
        errors.append("AppState.deinit must flush pending debounced saves before cancelling save tasks")
    flush_idx = body.find("flushPendingStateBeforeTermination()")
    cancel_idx = min((idx for idx in [body.find("apiKeySaveTask?.cancel()"), body.find("settingsSaveTask?.cancel()"), body.find("transcriptSaveTask?.cancel()")] if idx != -1), default=-1)
    if -1 not in (flush_idx, cancel_idx) and not (flush_idx < cancel_idx):
        errors.append("AppState.deinit must flush pending state before cancelling debounced save tasks")

if errors:
    print("Termination state flush verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Termination state flush verification passed")
