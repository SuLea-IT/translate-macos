#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Views" / "Caption" / "CaptionView.swift"
text = path.read_text()
errors: list[str] = []

match = re.search(r"private var topControls: some View \{(?P<body>[\s\S]*?)\n    \}\n\n    private var closeButton", text)
if not match:
    errors.append("CaptionView.topControls not found")
else:
    body = match.group("body")
    for token in [
        "Picker(appState.t(.audioPlaybackMode), selection: appState.binding(\\.audioPlaybackMode))",
        "ForEach(AudioPlaybackMode.allCases)",
        "mode.localizedTitle(language: appState.settings.interfaceLanguage)",
        ".pickerStyle(.menu)",
        ".frame(width: 128)",
        ".help(appState.t(.audioPlaybackMode))",
    ]:
        if token not in body:
            errors.append(f"CaptionView top controls must expose playback mode picker through {token}")

    mode_idx = body.find("Picker(appState.t(.audioPlaybackMode), selection: appState.binding(\\.audioPlaybackMode))")
    speaker_idx = body.find("appState.updateSetting(\\.audioPlayerMuted")
    if mode_idx == -1 or speaker_idx == -1 or mode_idx > speaker_idx:
        errors.append("Playback mode picker should sit before mute/volume controls in the subtitle popup")

if errors:
    print("Caption playback mode picker verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Caption playback mode picker verification passed")
