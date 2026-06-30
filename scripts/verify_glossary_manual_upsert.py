#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
glossary_path = root / "LiveBuddy" / "Models" / "Glossary.swift"
tests_path = root / "LiveBuddyTests" / "GlossaryTests.swift"
glossary = glossary_path.read_text()
tests = tests_path.read_text()
errors: list[str] = []

add_match = re.search(r"func add\(sourceTerm: String, targetTerm: String, to entries: \[GlossaryEntry\]\) -> \[GlossaryEntry\] \{(?P<body>[\s\S]*?)\n    \}\n\n    func delete", glossary)
if not add_match:
    errors.append("GlossaryEntryEditor.add(...) not found")
else:
    body = add_match.group("body")
    required_tokens = [
        "let sourceKey = key(for: source)",
        "var updatedEntries: [GlossaryEntry] = []",
        "var didUpdate = false",
        "if key(for: entry.sourceTerm) == sourceKey",
        "if didUpdate {",
        "continue",
        "updated.targetTerm = target",
        "didUpdate = true",
        "return updatedEntries",
        "updatedEntries.append(GlossaryEntry(sourceTerm: source, targetTerm: target))",
    ]
    for token in required_tokens:
        if token not in body:
            errors.append(f"GlossaryEntryEditor.add must upsert/collapse duplicate manual terms through {token}")
    forbidden_tokens = [
        "return entries + [GlossaryEntry(sourceTerm: source, targetTerm: target)]",
        "entries + [GlossaryEntry",
    ]
    for token in forbidden_tokens:
        if token in body:
            errors.append(f"GlossaryEntryEditor.add must not blindly append duplicates through {token}")

for token in [
    "private func key(for value: String) -> String",
    "normalized(value).lowercased()",
]:
    if token not in glossary:
        errors.append(f"GlossaryEntryEditor must centralize duplicate keys through {token}")

for token in [
    "@Test func editorUpdatesExistingTermInsteadOfAddingDuplicate()",
    "#expect(updated.count == 1)",
    "#expect(updated[0].id == existing.id)",
    "#expect(updated[0].targetTerm == \"OpenAI API\")",
    "#expect(updated[0].note == \"keep note\")",
    "#expect(updated[0].isEnabled == false)",
    "@Test func editorCollapsesLegacyDuplicateSourceTermsWhenUpdating()",
    "#expect(updated.map(\\.sourceTerm) == [\"OpenAI\", \"Gemini\"])",
]:
    if token not in tests:
        errors.append(f"GlossaryTests must cover manual glossary upsert behavior through {token}")

if errors:
    print("Glossary manual upsert verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary manual upsert verification passed")
