#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
settings_model = root / "LiveBuddy" / "Models" / "AppSettings.swift"
settings_view = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
menu_view = root / "LiveBuddy" / "Views" / "MenuBar" / "MenuBarView.swift"
interface_file = root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift"

model_text = settings_model.read_text()
settings_text = settings_view.read_text()
menu_text = menu_view.read_text()
interface_text = interface_file.read_text()
errors: list[str] = []

keys = [
    "subtitleColorWhite",
    "subtitleColorYellow",
    "subtitleColorCyan",
    "subtitleColorGreen",
    "subtitleColorOrange",
    "subtitleColorPink",
]
for key in keys:
    if f"case {key}" not in interface_text:
        errors.append(f"InterfaceText must include {key}")
    if interface_text.count(f".{key}:") < 8:
        errors.append(f"InterfaceText.{key} must be translated for every supported language")
    if f".{key}" not in model_text:
        errors.append(f"SubtitleColor.presets must reference InterfaceText.{key}")

for token in [
    "static let presets: [(id: String, titleKey: InterfaceText, color: SubtitleColor)]",
    '("white", .subtitleColorWhite, .white)',
    '("yellow", .subtitleColorYellow, .yellow)',
    '("cyan", .subtitleColorCyan, .cyan)',
    '("green", .subtitleColorGreen, .green)',
    '("orange", .subtitleColorOrange, .orange)',
    '("pink", .subtitleColorPink, .pink)',
]:
    if token not in model_text:
        errors.append(f"SubtitleColor.presets must expose stable ids and localized title keys through {token}")

for view_name, text in [("SettingsView", settings_text), ("MenuBarView", menu_text)]:
    if "ForEach(SubtitleColor.presets, id: \\.id)" not in text:
        errors.append(f"{view_name} must identify subtitle color presets by stable id")
    if ".help(appState.t(preset.titleKey))" not in text:
        errors.append(f"{view_name} must localize subtitle color hover text")
    if ".help(preset.name)" in text:
        errors.append(f"{view_name} must not expose hard-coded preset.name in hover text")

if "static let presets: [(name: String, color: SubtitleColor)]" in model_text:
    errors.append("SubtitleColor.presets must not store English names as the user-facing label")
for old_name in ['("White", .white)', '("Yellow", .yellow)', '("Cyan", .cyan)', '("Green", .green)', '("Orange", .orange)', '("Pink", .pink)']:
    if old_name in model_text:
        errors.append(f"SubtitleColor.presets must not hard-code English color label {old_name}")

if errors:
    print("Subtitle color preset localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Subtitle color preset localization verification passed")
