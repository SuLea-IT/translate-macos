#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
app_path = root / "LiveBuddy" / "App" / "LiveBuddyApp.swift"
menu_path = root / "LiveBuddy" / "Views" / "MenuBar" / "MenuBarView.swift"
app_text = app_path.read_text()
menu_text = menu_path.read_text()
errors: list[str] = []

for token in [
    "OpenWindowActionInstaller()",
    "@Environment(\\.openWindow) private var openWindow",
    "@EnvironmentObject private var appState: AppState",
    "appState.openWindowAction = openWindow",
]:
    if token not in app_text:
        errors.append(f"LiveBuddyApp must publish a stable settings openWindow action from the persistent MenuBarExtra scene through {token}")

if 'MenuBarExtra {' not in app_text or '} label: {' not in app_text:
    errors.append("LiveBuddyApp should use the MenuBarExtra content/label initializer so the persistent label can install openWindowAction")

if "appState.openWindowAction = openWindow" in menu_text:
    errors.append("MenuBarView must not publish openWindowAction from the transient menu popover content")
if "appState.openWindowAction = nil" in menu_text:
    errors.append("MenuBarView must not clear the stable app-level openWindowAction when the transient popover disappears")

if "Button {\n                        openWindow(id: \"settings\")" not in menu_text:
    errors.append("The menu gear button should still open settings directly with its local openWindow action")

if errors:
    print("Stable settings window action verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Stable settings window action verification passed")
