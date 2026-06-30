#!/usr/bin/env python3
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
interface = (root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift").read_text()
app_state = (root / "LiveBuddy" / "Models" / "AppState.swift").read_text()
settings = (root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift").read_text()
tests = (root / "LiveBuddyTests" / "UsageControlTests.swift").read_text()

errors = []

if "case statusResumeBufferLimited" not in interface:
    errors.append("InterfaceText must include statusResumeBufferLimited")

translation_occurrences = interface.count(".statusResumeBufferLimited:")
if translation_occurrences != 8:
    errors.append(f"statusResumeBufferLimited must be translated for all 8 interface languages, found {translation_occurrences}")

running_match = re.search(r"private func runningUsageStatusMessage\(\) -> String \{(?P<body>[\s\S]*?)\n    \}\n\n    private func usagePauseLogMessage", app_state)
if not running_match:
    errors.append("AppState.runningUsageStatusMessage() not found")
else:
    body = running_match.group("body")
    if "usageSnapshot.resumeBufferOverflowed" not in body:
        errors.append("runningUsageStatusMessage must surface resumeBufferOverflowed")
    if ".statusResumeBufferLimited" not in body:
        errors.append("runningUsageStatusMessage must use localized statusResumeBufferLimited text")

usage_section_match = re.search(r"private var usageControlSection: some View \{(?P<body>[\s\S]*?)\n    \}\n\n    private func usageMetricRow", settings)
if not usage_section_match:
    errors.append("SettingsView.usageControlSection not found")
else:
    body = usage_section_match.group("body")
    if "appState.usageSnapshot.resumeBufferOverflowed" not in body:
        errors.append("Usage Control settings section must show a visible overflow warning")
    if ".statusResumeBufferLimited" not in body:
        errors.append("Usage Control overflow warning must use localized statusResumeBufferLimited text")
    if ".foregroundStyle(.orange)" not in body:
        errors.append("Usage Control overflow warning should be visually distinct")

if "pausedBufferOverflowIsReflectedInSnapshot" not in tests:
    errors.append("UsageControlTests must cover paused buffer overflow visibility")
if "resumeBufferOverflowed" not in tests:
    errors.append("UsageControlTests must assert resumeBufferOverflowed")

if errors:
    print("usage buffer overflow feedback verification failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("usage buffer overflow feedback verification passed")
