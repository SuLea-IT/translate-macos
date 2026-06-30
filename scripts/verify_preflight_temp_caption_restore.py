#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

if "private var temporaryTestCaptionPreviousDraft: String?" not in text:
    errors.append("AppState must retain the previous caption draft while a temporary preflight subtitle is visible")

show_match = re.search(r"func showTemporaryTestCaption\(\) async \{(?P<body>[\s\S]*?)\n    \}\n\n    private func cancelPreflightTest", text)
if not show_match:
    errors.append("AppState.showTemporaryTestCaption() not found")
else:
    body = show_match.group("body")
    for token in [
        "temporaryTestCaptionTask?.cancel()",
        "temporaryTestCaptionTask = nil",
        "restoreTemporaryTestCaptionIfNeeded()",
        "let previousDraft = captionDraft",
        "temporaryTestCaptionPreviousDraft = previousDraft",
        "captionDraft = settings.interfaceLanguage.localized(.subtitleTestMessage)",
        "temporaryTestCaptionTask = Task",
        "guard !Task.isCancelled else { return }",
        "self.restoreTemporaryTestCaptionIfNeeded()",
        "temporaryTestCaptionTask = nil",
    ]:
        if token not in body:
            errors.append(f"showTemporaryTestCaption must snapshot and restore temporary subtitle state through {token}")
    cancel_idx = body.find("temporaryTestCaptionTask?.cancel()")
    restore_idx = body.find("restoreTemporaryTestCaptionIfNeeded()", cancel_idx)
    snapshot_idx = body.find("let previousDraft = captionDraft", restore_idx)
    assign_idx = body.find("temporaryTestCaptionPreviousDraft = previousDraft", snapshot_idx)
    message_idx = body.find("captionDraft = settings.interfaceLanguage.localized(.subtitleTestMessage)", assign_idx)
    natural_restore_idx = body.find("self.restoreTemporaryTestCaptionIfNeeded()", message_idx)
    if -1 in [cancel_idx, restore_idx, snapshot_idx, assign_idx, message_idx, natural_restore_idx] or not (cancel_idx < restore_idx < snapshot_idx < assign_idx < message_idx < natural_restore_idx):
        errors.append("showTemporaryTestCaption must restore any previous temporary subtitle before taking a new snapshot, then restore on natural completion")

cancel_match = re.search(r"private func cancelPreflightTest\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func openMicrophoneSettings", text)
if not cancel_match:
    errors.append("AppState.cancelPreflightTest() not found")
else:
    body = cancel_match.group("body")
    for token in [
        "temporaryTestCaptionTask?.cancel()",
        "temporaryTestCaptionTask = nil",
        "restoreTemporaryTestCaptionIfNeeded()",
        "isRunningPreflightTest = false",
    ]:
        if token not in body:
            errors.append(f"cancelPreflightTest must clear and restore temporary subtitle state through {token}")
    nil_idx = body.find("temporaryTestCaptionTask = nil")
    restore_idx = body.find("restoreTemporaryTestCaptionIfNeeded()", nil_idx)
    running_idx = body.find("isRunningPreflightTest = false", restore_idx)
    if -1 in [nil_idx, restore_idx, running_idx] or not (nil_idx < restore_idx < running_idx):
        errors.append("cancelPreflightTest must restore temporary subtitle state after cancelling its task and before finishing cancellation")

restore_match = re.search(r"private func restoreTemporaryTestCaptionIfNeeded\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func openMicrophoneSettings", text)
if not restore_match:
    errors.append("AppState.restoreTemporaryTestCaptionIfNeeded() not found before settings navigation helpers")
else:
    body = restore_match.group("body")
    for token in [
        "guard let previousDraft = temporaryTestCaptionPreviousDraft else { return }",
        "if !isRunning {",
        "captionDraft = previousDraft",
        "temporaryTestCaptionPreviousDraft = nil",
    ]:
        if token not in body:
            errors.append(f"restoreTemporaryTestCaptionIfNeeded must restore only non-running temporary subtitle drafts through {token}")

if errors:
    print("Preflight temporary caption restore verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Preflight temporary caption restore verification passed")
