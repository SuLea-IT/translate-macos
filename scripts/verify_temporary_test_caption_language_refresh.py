#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = app_state_path.read_text()
errors: list[str] = []

if "private func refreshTemporaryTestCaptionLanguageIfNeeded()" not in text:
    errors.append("AppState must refresh an in-flight temporary test caption when interface language changes")
else:
    helper_match = re.search(
        r"private func refreshTemporaryTestCaptionLanguageIfNeeded\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func refreshStatusMessageLanguageIfNeeded",
        text,
    )
    if not helper_match:
        errors.append("refreshTemporaryTestCaptionLanguageIfNeeded() should live immediately before refreshStatusMessageLanguageIfNeeded(oldValue:)")
    else:
        body = helper_match.group("body")
        for token in [
            "guard temporaryTestCaptionPreviousDraft != nil else { return }",
            "guard temporaryTestCaptionTask != nil else { return }",
            "captionDraft = settings.interfaceLanguage.localized(.subtitleTestMessage)",
        ]:
            if token not in body:
                errors.append(f"refreshTemporaryTestCaptionLanguageIfNeeded must use {token}")

status_match = re.search(
    r"private func refreshStatusMessageLanguageIfNeeded\(oldValue: AppSettings\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func updateStatus",
    text,
)
if not status_match:
    errors.append("refreshStatusMessageLanguageIfNeeded(oldValue:) not found")
else:
    body = status_match.group("body")
    guard_token = "guard oldValue.interfaceLanguage != settings.interfaceLanguage else { return }"
    refresh_token = "refreshTemporaryTestCaptionLanguageIfNeeded()"
    if refresh_token not in body:
        errors.append("Interface language changes must refresh any visible temporary test caption")
    else:
        guard_idx = body.find(guard_token)
        refresh_idx = body.find(refresh_token)
        status_idx = body.find("switch statusLevel")
        if guard_idx == -1 or refresh_idx < guard_idx:
            errors.append("Temporary test caption refresh must run after confirming interfaceLanguage changed")
        if status_idx != -1 and refresh_idx > status_idx:
            errors.append("Temporary test caption refresh should run before status message relocalization branches")

if errors:
    print("Temporary test caption language refresh verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Temporary test caption language refresh verification passed")
