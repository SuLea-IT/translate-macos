#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
text = path.read_text()
errors: list[str] = []

if "private var canMutateGlossaryEntries: Bool" not in text or "!appState.isImportingGlossary" not in text:
    errors.append("SettingsView must centralize glossary edit locking while imports are running")

for token in [
    ".disabled(!canMutateGlossaryEntries || newGlossarySourceTerm.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)",
    ".disabled(appState.settings.glossaryEntries.isEmpty || !canMutateGlossaryEntries)",
    ".disabled(!canMutateGlossaryEntries)",
]:
    if token not in text:
        errors.append(f"Glossary UI must disable mutating controls during import through {token}")

for name, pattern in [
    ("addGlossaryEntryFromUI", r"private func addGlossaryEntryFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func deleteGlossaryEntryFromUI"),
    ("deleteGlossaryEntryFromUI", r"private func deleteGlossaryEntryFromUI\(_ entry: GlossaryEntry\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func clearGlossaryEntriesFromUI"),
    ("clearGlossaryEntriesFromUI", r"private func clearGlossaryEntriesFromUI\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func localizedGlossarySourceName"),
]:
    match = re.search(pattern, text)
    if not match:
        errors.append(f"SettingsView.{name} not found")
        continue
    body = match.group("body")
    if "guard canMutateGlossaryEntries else { return }" not in body:
        errors.append(f"SettingsView.{name} must guard against stale import-time mutations")

if errors:
    print("Glossary import mutation lock verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary import mutation lock verification passed")
