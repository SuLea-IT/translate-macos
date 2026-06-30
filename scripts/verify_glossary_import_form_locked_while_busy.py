#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
text = path.read_text()
errors: list[str] = []

section_match = re.search(
    r"private var glossaryImportSection: some View \{(?P<body>[\s\S]*?)\n    \}\n\n    private var glossaryEntriesSection",
    text,
)
if not section_match:
    errors.append("SettingsView.glossaryImportSection not found")
else:
    body = section_match.group("body")
    controls = [
        (
            "glossary source picker",
            r"Picker\(appState\.t\(\.glossaryImportSource\), selection: \$selectedGlossaryImportSourceID\)(?P<chunk>[\s\S]*?)\n\s*Text\(localizedGlossarySourceDetail\(selectedGlossaryImportSource\)\)",
        ),
        (
            "custom glossary link field",
            r"TextField\(appState\.t\(\.glossaryImportLinkPlaceholder\), text: \$glossaryImportURLString\)(?P<chunk>[\s\S]*?)\n\s*}\n\n\s*Stepper",
        ),
        (
            "glossary import limit stepper",
            r"Stepper\(\"\\\(appState\.t\(\.importLimit\)\): \\\(glossaryImportLimit\)\", value: \$glossaryImportLimit, in: 1\.\.\.2_000, step: 50\)(?P<chunk>[\s\S]*?)\n\s*HStack \{",
        ),
    ]
    for label, pattern in controls:
        match = re.search(pattern, body)
        if not match:
            errors.append(f"Could not find {label} in glossary import section")
            continue
        chunk = match.group("chunk")
        if ".disabled(appState.isImportingGlossary)" not in chunk:
            errors.append(f"{label} must be disabled while a glossary import is running")

if errors:
    print("Glossary import busy form lock verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary import busy form lock verification passed")
