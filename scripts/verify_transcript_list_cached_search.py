#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
view_path = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"
model_path = root / "LiveBuddy" / "Models" / "TranscriptSession.swift"
view_text = view_path.read_text()
model_text = model_path.read_text()
errors: list[str] = []

if "struct TranscriptListDisplay" not in model_text:
    errors.append("TranscriptSession.swift must provide TranscriptListDisplay for cached transcript list filtering")
else:
    struct_match = re.search(r"struct TranscriptListDisplay \{(?P<body>[\s\S]*?)\n\}", model_text)
    if not struct_match:
        errors.append("TranscriptListDisplay struct body not found")
    else:
        body = struct_match.group("body")
        for token in [
            "var sessions: [TranscriptSession]",
            "var query: String",
            "let filteredSessions: [TranscriptSession]",
            "self.filteredSessions = Self.filtered(sessions: sessions, query: query)",
            "private static func filtered(sessions: [TranscriptSession], query: String) -> [TranscriptSession]",
            "session.matchesSearch(normalizedQuery)",
        ]:
            if token not in body:
                errors.append(f"TranscriptListDisplay must cache search results through {token}")
        if "var filteredSessions: [TranscriptSession] {" in body:
            errors.append("TranscriptListDisplay.filteredSessions must be cached in init, not recomputed as a property")
        if "session.fullText.localizedCaseInsensitiveContains" in body:
            errors.append("TranscriptListDisplay must not allocate fullText while filtering cached search results")

if "private var filteredSessions: [TranscriptSession]" in view_text:
    errors.append("TranscriptsView must not keep a computed filteredSessions property that can be evaluated multiple times per render")

session_list_match = re.search(r"private var sessionList: some View \{(?P<body>[\s\S]*?)\n    \}\n\n    private var emptyState", view_text)
if not session_list_match:
    errors.append("TranscriptsView.sessionList not found")
else:
    body = session_list_match.group("body")
    for token in [
        "let display = TranscriptListDisplay(sessions: appState.transcriptSessions, query: searchText)",
        "ForEach(display.filteredSessions)",
        "if display.filteredSessions.isEmpty && !searchText.isEmpty",
    ]:
        if token not in body:
            errors.append(f"TranscriptsView.sessionList must compute transcript search once and reuse it through {token}")
    if body.count("TranscriptListDisplay(sessions: appState.transcriptSessions, query: searchText)") != 1:
        errors.append("TranscriptsView.sessionList must instantiate TranscriptListDisplay exactly once")
    if "ForEach(filteredSessions)" in body or "if filteredSessions.isEmpty" in body:
        errors.append("TranscriptsView.sessionList must not read the old computed filteredSessions path")

if errors:
    print("Transcript cached search verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Transcript cached search verification passed")
