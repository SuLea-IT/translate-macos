#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
menu_bar = root / "LiveBuddy" / "Views" / "MenuBar" / "MenuBarView.swift"
text = menu_bar.read_text()
errors: list[str] = []

if "appState.openWindowAction = openWindow" not in text:
    errors.append("MenuBarView should still publish the SwiftUI openWindow action while visible")

on_disappear_match = re.search(r"\.onDisappear \{(?P<body>[\s\S]*?)\n        \}", text)
if not on_disappear_match:
    errors.append("MenuBarView must clear AppState.openWindowAction in onDisappear to avoid retaining a stale menu bar window environment")
else:
    body = on_disappear_match.group("body")
    if "appState.openWindowAction = nil" not in body:
        errors.append("MenuBarView.onDisappear must set appState.openWindowAction = nil")

if errors:
    print("Menu bar openWindow action lifecycle verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Menu bar openWindow action lifecycle verification passed")
