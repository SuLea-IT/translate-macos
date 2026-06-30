#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
settings_path = root / "LiveBuddy" / "Models" / "AppSettings.swift"
glossary_path = root / "LiveBuddy" / "Models" / "GlossaryImport.swift"
settings = settings_path.read_text()
glossary = glossary_path.read_text()
errors: list[str] = []

languages = re.findall(r'\.init\(id: "([^"]+)", name: "([^"]+)"\)', settings)
if not languages:
    errors.append("Could not parse TranslationLanguage.all entries")

alias_block_match = re.search(
    r"let aliases: \[String: \[String\]\] = \[(?P<body>[\s\S]*?)\n        \]",
    glossary,
)
if not alias_block_match:
    errors.append("Could not find ZIPGlossaryEntryPrioritizer.languageTokens alias table")
    alias_body = ""
else:
    alias_body = alias_block_match.group("body")

aliases: dict[str, set[str]] = {}
for code, values in re.findall(r'"([^"]+)": \[([^\]]*)\]', alias_body):
    aliases[code] = set(re.findall(r'"([^"]+)"', values))

missing: list[str] = []
for code, name in languages:
    normalized_name = name.lower().replace("_", "-")
    tokens = {code.lower(), code.lower().split("-")[0]}
    tokens.update(aliases.get(code.lower().split("-")[0], set()))
    if normalized_name not in tokens:
        missing.append(f"{code}:{name}")

if missing:
    errors.append(
        "ZIP language filename prioritizer must include aliases for every selectable language name; missing "
        + ", ".join(missing)
    )

if errors:
    print("Glossary ZIP language alias coverage verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary ZIP language alias coverage verification passed")
