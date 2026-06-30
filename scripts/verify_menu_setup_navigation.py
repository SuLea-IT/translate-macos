#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
menu_path = root / "LiveBuddy" / "Views" / "MenuBar" / "MenuBarView.swift"
menu = menu_path.read_text()
errors: list[str] = []

setup_match = re.search(
    r"if !appState\.setupChecklist\.canStart \{(?P<body>[\s\S]*?)\n\s*Divider\(\)\n\s*\}",
    menu,
)
if not setup_match:
    errors.append("MenuBarView setup-incomplete block not found")
else:
    body = setup_match.group("body")
    if "appState.openProviderSettings()" not in body:
        errors.append("Menu bar setup-incomplete action must open settings focused on the API Provider page")
    if "openWindow(id: \"settings\")" in body or "NSApp.activate(ignoringOtherApps: true)" in body:
        errors.append("Menu bar setup-incomplete action must not bypass AppState.openProviderSettings() with a generic settings open")

if errors:
    print("Menu setup navigation verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Menu setup navigation verification passed")
