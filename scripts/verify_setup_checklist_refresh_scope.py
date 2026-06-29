#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

did_set_match = re.search(r"@Published private\(set\) var settings: AppSettings \{\n        didSet \{(?P<body>[\s\S]*?)\n        \}\n    \}", text)
if not did_set_match:
    errors.append("AppState.settings didSet not found")
else:
    body = did_set_match.group("body")
    if "refreshSetupChecklistIfNeeded(oldValue: oldValue)" not in body:
        errors.append("settings didSet must diff setup-related fields before refreshing the checklist")

helper_match = re.search(r"private func refreshSetupChecklistIfNeeded\(oldValue: AppSettings\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func refreshSetupChecklist", text)
if not helper_match:
    errors.append("AppState.refreshSetupChecklistIfNeeded(oldValue:) not found")
else:
    body = helper_match.group("body")
    for token in [
        "oldValue.apiKey != settings.apiKey",
        "oldValue.audioSource != settings.audioSource",
        "guard setupInputsChanged else { return }",
        "refreshSetupChecklist()",
    ]:
        if token not in body:
            errors.append(f"setup checklist refresh diff must include {token}")

for name, pattern in [
    ("updateGlobalShortcutsEnabled", r"func updateGlobalShortcutsEnabled\(_ value: Bool\) \{(?P<body>[\s\S]*?)\n    \}"),
    ("updateAPIKey", r"func updateAPIKey\(_ apiKey: String\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func updateSetting"),
    ("updateSetting", r"func updateSetting<Value>\(_ keyPath: WritableKeyPath<AppSettings, Value>, to value: Value\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func addGlossaryEntry"),
    ("addGlossaryEntry", r"func addGlossaryEntry\(sourceTerm: String, targetTerm: String\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func deleteGlossaryEntry"),
    ("deleteGlossaryEntry", r"func deleteGlossaryEntry\(_ entry: GlossaryEntry\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func clearGlossaryEntries"),
    ("clearGlossaryEntries", r"func clearGlossaryEntries\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func startGlossaryImport"),
]:
    match = re.search(pattern, text)
    if not match:
        errors.append(f"AppState.{name} not found")
        continue
    if "refreshSetupChecklist()" in match.group("body"):
        errors.append(f"AppState.{name} must not manually refresh setup checklist; settings didSet diff handles relevant changes")

# Explicit user/system refresh entry points should remain.
for token in [
    "refreshAvailableMicrophones()",
    "refreshSetupChecklist()",
    "func runStartPreflight() async",
]:
    if token not in text:
        errors.append(f"AppState must keep explicit setup/preflight refresh capability through {token}")

if errors:
    print("Setup checklist refresh scope verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Setup checklist refresh scope verification passed")
