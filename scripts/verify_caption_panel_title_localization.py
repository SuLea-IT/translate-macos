#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
controller = (root / "LiveBuddy" / "Views" / "Caption" / "CaptionPanelController.swift").read_text()
errors: list[str] = []

for token in [
    "import Combine",
    "private var titleCancellable: AnyCancellable?",
    "updateTitle(language: appState.settings.interfaceLanguage)",
    "appState.$settings",
    ".map(\\.interfaceLanguage)",
    ".removeDuplicates()",
    ".sink { [weak self] language in",
    "self?.updateTitle(language: language)",
    "private func updateTitle(language: InterfaceLanguage)",
    "panel.title = language.localized(.captionWindow)",
]:
    if token not in controller:
        errors.append(f"CaptionPanelController must localize/update title through: {token}")

for forbidden in [
    'panel.title = "Subtitle Screen"',
    ".sink { language in",
    ".sink { [self] language in",
]:
    if forbidden in controller:
        errors.append(f"CaptionPanelController must not keep stale/strong title handling: {forbidden}")

if errors:
    print("Caption panel title localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Caption panel title localization verification passed")
