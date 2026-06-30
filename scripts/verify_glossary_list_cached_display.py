#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "Glossary.swift"
text = path.read_text()
errors: list[str] = []

struct_match = re.search(r"struct GlossaryListDisplay \{(?P<body>[\s\S]*?)\n\}", text)
if not struct_match:
    errors.append("GlossaryListDisplay struct not found")
else:
    body = struct_match.group("body")
    for token in [
        "let matchingEntries: [GlossaryEntry]",
        "let visibleEntries: [GlossaryEntry]",
        "let matches = Self.filtered(entries: entries, query: query)",
        "self.matchingEntries = matches",
        "self.visibleEntries = isExpanded ? matches : Array(matches.prefix(max(collapsedLimit, 0)))",
        "private static func filtered(entries: [GlossaryEntry], query: String) -> [GlossaryEntry]",
        "private static func normalized(_ value: String) -> String",
    ]:
        if token not in body:
            errors.append(f"GlossaryListDisplay must cache filtered/visible entries once per init through {token}")

    repeated_filter_tokens = [
        "var matchingEntries: [GlossaryEntry] {",
        "var visibleEntries: [GlossaryEntry] {",
        "let matches = matchingEntries",
    ]
    for token in repeated_filter_tokens:
        if token in body:
            errors.append(f"GlossaryListDisplay must not recompute large glossary filters from computed property path: {token}")

    init_idx = body.find("init(entries: [GlossaryEntry]")
    filter_idx = body.find("let matches = Self.filtered(entries: entries, query: query)", init_idx)
    matching_assign_idx = body.find("self.matchingEntries = matches", filter_idx)
    visible_assign_idx = body.find("self.visibleEntries = isExpanded ? matches : Array(matches.prefix(max(collapsedLimit, 0)))", matching_assign_idx)
    hidden_idx = body.find("var hiddenCount: Int", visible_assign_idx)
    if -1 in [init_idx, filter_idx, matching_assign_idx, visible_assign_idx, hidden_idx] or not (init_idx < filter_idx < matching_assign_idx < visible_assign_idx < hidden_idx):
        errors.append("GlossaryListDisplay must derive cached matchingEntries and visibleEntries during initialization before summary properties use them")

    hidden_match = re.search(r"var hiddenCount: Int \{(?P<body>[\s\S]*?)\n    \}", body)
    if not hidden_match:
        errors.append("GlossaryListDisplay.hiddenCount not found")
    else:
        hidden_body = hidden_match.group("body")
        if "max(matchingEntries.count - visibleEntries.count, 0)" not in hidden_body:
            errors.append("GlossaryListDisplay.hiddenCount must use cached matchingEntries and visibleEntries counts")

    toggle_match = re.search(r"var shouldShowToggle: Bool \{(?P<body>[\s\S]*?)\n    \}", body)
    if not toggle_match:
        errors.append("GlossaryListDisplay.shouldShowToggle not found")
    else:
        toggle_body = toggle_match.group("body")
        if "matchingEntries.count > max(collapsedLimit, 0)" not in toggle_body:
            errors.append("GlossaryListDisplay.shouldShowToggle must use cached matchingEntries count")

if errors:
    print("Glossary cached display verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary cached display verification passed")
