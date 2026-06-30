#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
settings_path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
language_path = root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift"
settings = settings_path.read_text()
language = language_path.read_text()
errors: list[str] = []

if "case preflightAudioLevelReadout" not in language:
    errors.append("InterfaceText must include preflightAudioLevelReadout for localized audio meter labels")

translation_count = language.count(".preflightAudioLevelReadout:")
if translation_count != 8:
    errors.append(f"preflightAudioLevelReadout must be translated for all 8 interface languages; found {translation_count}")

if 'Text("RMS ' in settings or "Peak \\(" in settings:
    errors.append("PreflightTestStepRow must not hard-code RMS/Peak text in the SwiftUI view")

row_match = re.search(
    r"private struct PreflightTestStepRow: View \{(?P<body>[\s\S]*?)\n\}\n\n#Preview",
    settings,
)
if not row_match:
    errors.append("PreflightTestStepRow not found")
else:
    body = row_match.group("body")
    for token in [
        "audioLevelText(audio)",
        "private func audioLevelText(_ audio: AudioLevelSummary) -> String",
        "language.localized(",
        ".preflightAudioLevelReadout",
        "Int(audio.rms * 100)",
        "Int(audio.peak * 100)",
    ]:
        if token not in body:
            errors.append(f"Preflight audio level readout must be localized through {token}")

if errors:
    print("Preflight audio level readout localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Preflight audio level readout localization verification passed")
