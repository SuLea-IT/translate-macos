#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = app_state_path.read_text()
errors: list[str] = []

settings_match = re.search(r"@Published private\(set\) var settings: AppSettings \{(?P<body>[\s\S]*?)\n    \}", text)
if not settings_match:
    errors.append("AppState.settings didSet not found")
else:
    body = settings_match.group("body")
    if "configureGlobalShortcutsIfNeeded(oldValue: oldValue)" not in body:
        errors.append("AppState.settings didSet must be the single place that reconfigures global shortcuts when shortcut settings change")
    if "configureGlobalShortcuts()" in body:
        errors.append("AppState.settings didSet must call the diff-aware shortcut reconfiguration helper, not unconditional configureGlobalShortcuts()")

helper_match = re.search(r"private func configureGlobalShortcutsIfNeeded\(oldValue: AppSettings\) \{(?P<body>[\s\S]*?)\n    \}", text)
if not helper_match:
    errors.append("AppState.configureGlobalShortcutsIfNeeded(oldValue:) not found")
else:
    body = helper_match.group("body")
    for token in [
        "oldValue.globalShortcutsEnabled != settings.globalShortcutsEnabled",
        "oldValue.globalShortcuts != settings.globalShortcuts",
        "guard shortcutsChanged else { return }",
        "configureGlobalShortcuts()",
    ]:
        if token not in body:
            errors.append(f"configureGlobalShortcutsIfNeeded must be diff-aware through {token}")

for name in [
    "updateGlobalShortcutsEnabled",
    "updateGlobalShortcut",
    "clearGlobalShortcut",
    "resetGlobalShortcut",
    "resetAllGlobalShortcuts",
]:
    match = re.search(rf"func {name}\([^\)]*\)(?: -> [^\{{]+)? \{{(?P<body>[\s\S]*?)\n    \}}", text)
    if not match:
        errors.append(f"AppState.{name} not found")
        continue
    body = match.group("body")
    if "configureGlobalShortcuts()" in body:
        errors.append(f"AppState.{name} must not manually reconfigure shortcuts because settings didSet already handles it once")

if errors:
    print("Global shortcut reconfiguration verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Global shortcut reconfiguration verification passed")
