#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
model_path = root / "LiveBuddy" / "Models" / "TranscriptSession.swift"
text = model_path.read_text()
errors: list[str] = []

if "func matchesSearch(_ query: String) -> Bool" not in text:
    errors.append("TranscriptSession must provide matchesSearch(_:) so list search can avoid allocating fullText")
else:
    match = re.search(r"func matchesSearch\(_ query: String\) -> Bool \{(?P<body>[\s\S]*?)\n    \}\n\n    var shareText", text)
    if not match:
        errors.append("TranscriptSession.matchesSearch(_:) must live before shareText for stable model search behavior")
    else:
        body = match.group("body")
        for token in [
            "let normalizedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)",
            "guard !normalizedQuery.isEmpty else { return true }",
            "targetLanguage.localizedCaseInsensitiveContains(normalizedQuery)",
            "lines.contains { line in",
            "line.text.localizedCaseInsensitiveContains(normalizedQuery)",
            "line.originalText?.localizedCaseInsensitiveContains(normalizedQuery) ?? false",
        ]:
            if token not in body:
                errors.append(f"matchesSearch(_:) must scan transcript fields directly through {token}")
        if "fullText" in body:
            errors.append("matchesSearch(_:) must not allocate fullText while searching")

list_match = re.search(r"struct TranscriptListDisplay \{(?P<body>[\s\S]*?)\n\}\n\nstruct TranscriptLine", text)
if not list_match:
    errors.append("TranscriptListDisplay not found before TranscriptLine")
else:
    body = list_match.group("body")
    if "session.matchesSearch(normalizedQuery)" not in body:
        errors.append("TranscriptListDisplay.filtered must delegate per-session search to matchesSearch(_:) without building fullText")
    if "session.fullText.localizedCaseInsensitiveContains" in body:
        errors.append("TranscriptListDisplay.filtered must not allocate session.fullText during search")
    target_idx = body.find("session.targetLanguage.localizedCaseInsensitiveContains(normalizedQuery)")
    matches_idx = body.find("session.matchesSearch(normalizedQuery)")
    if target_idx != -1 and (matches_idx == -1 or target_idx < matches_idx):
        errors.append("TranscriptListDisplay should keep all field search logic inside TranscriptSession.matchesSearch(_:)")

if errors:
    print("Transcript search allocation verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Transcript search allocation verification passed")
