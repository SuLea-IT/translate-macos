#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
settings_path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
transcripts_path = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
settings = settings_path.read_text()
transcripts = transcripts_path.read_text()
errors: list[str] = []

settings_body_match = re.search(r"var body: some View \{(?P<body>[\s\S]*?)\n    \}\n\n    private func applyProviderSettingsFocusRequest", settings)
if not settings_body_match:
    errors.append("SettingsView.body not found")
else:
    body = settings_body_match.group("body")
    if ".onChange(of: appState.settings.interfaceLanguage)" not in body:
        errors.append("SettingsView must clear stale localized transient feedback when interfaceLanguage changes")
    if "clearLocalizedTransientFeedback()" not in body:
        errors.append("SettingsView interfaceLanguage onChange must call clearLocalizedTransientFeedback()")

settings_helper_match = re.search(
    r"private func clearLocalizedTransientFeedback\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func applyProviderSettingsFocusRequest",
    settings,
)
if not settings_helper_match:
    errors.append("SettingsView.clearLocalizedTransientFeedback() not found before provider focus helper")
else:
    helper = settings_helper_match.group("body")
    for token in [
        "tokenCheckError = nil",
        "glossaryImportInputMessage = \"\"",
        "appState.clearGlossaryImportFeedback()",
        "clearGlossaryExportFeedback()",
        "logExportErrorMessage = nil",
        "logCopyErrorMessage = nil",
        "logCopySuccessMessage = nil",
    ]:
        if token not in helper:
            errors.append(f"SettingsView.clearLocalizedTransientFeedback must clear stale localized state through {token}")

transcripts_body_match = re.search(r"var body: some View \{(?P<body>[\s\S]*?)\n    \}\n\n    // MARK: - List View", transcripts)
if not transcripts_body_match:
    errors.append("TranscriptsView.body not found")
else:
    body = transcripts_body_match.group("body")
    if ".onChange(of: appState.settings.interfaceLanguage)" not in body:
        errors.append("TranscriptsView must clear stale localized operation feedback when interfaceLanguage changes")
    if "clearTranscriptOperationFeedback()" not in body:
        errors.append("TranscriptsView interfaceLanguage onChange must call clearTranscriptOperationFeedback()")

if errors:
    print("Interface-language feedback reset verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Interface-language feedback reset verification passed")
