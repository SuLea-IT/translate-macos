#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
settings = (root / "LiveBuddy" / "Models" / "AppSettings.swift").read_text()
app_state = (root / "LiveBuddy" / "Models" / "AppState.swift").read_text()
settings_view = (root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift").read_text()
menu_view = (root / "LiveBuddy" / "Views" / "MenuBar" / "MenuBarView.swift").read_text()
tests = (root / "LiveBuddyTests" / "InterfaceLanguageTests.swift").read_text()
errors: list[str] = []

if "func localizedName(language: InterfaceLanguage)" not in settings:
    errors.append("TranslationLanguage must expose localizedName(language:)")
if "static func name(for code: String, language: InterfaceLanguage)" not in settings:
    errors.append("TranslationLanguage.name(for:language:) must support localized status/export names")
if ".localizedString(forLanguageCode: id)" not in settings:
    errors.append("localizedName must use the interface language Locale for language names")
if "TranslationLanguage.name(for: sourceLanguageCode, language: settings.interfaceLanguage)" not in app_state:
    errors.append("source language status must use localized language names")
if "TranslationLanguage.name(for: detectedSourceLanguageCode, language: settings.interfaceLanguage)" not in app_state:
    errors.append("detected language status must use localized language names")
if "TranslationLanguage.name(for: settings.targetLanguageCode, language: settings.interfaceLanguage)" not in app_state:
    errors.append("target language status/export must use localized language names")
if "language.localizedName(language: appState.settings.interfaceLanguage)" not in settings_view:
    errors.append("Settings language pickers must display localized language names")
if "language.localizedName(language: appState.settings.interfaceLanguage)" not in menu_view:
    errors.append("Menu bar language pickers must display localized language names")
if "localizesTranslationLanguageNamesForInterfaceLanguage" not in tests:
    errors.append("InterfaceLanguageTests must cover localized translation language names")

if errors:
    print("Translation language localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Translation language localization verification passed")
