#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
menu_bar = root / "LiveBuddy" / "Views" / "MenuBar" / "MenuBarView.swift"
text = menu_bar.read_text()
errors: list[str] = []

if "appState.openWindowAction = openWindow" in text:
    errors.append("MenuBarView must not publish AppState.openWindowAction from the transient popover content")

if "appState.openWindowAction = nil" in text:
    errors.append("MenuBarView must not clear the stable app-level openWindowAction when the transient popover disappears")

if "appState.refreshAvailableMicrophones()" not in text:
    errors.append("MenuBarView should still refresh microphone options when the popover appears")

if "openWindow(id: \"settings\")" not in text:
    errors.append("MenuBarView gear button should still open settings directly with its local openWindow action")

if errors:
    print("Menu bar openWindow action lifecycle verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Menu bar openWindow action lifecycle verification passed")
