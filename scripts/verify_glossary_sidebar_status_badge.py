#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
settings_view_path = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
text = settings_view_path.read_text()
errors: list[str] = []

if "NavigationLink(value: NavigationItem.glossary) {\n                        glossarySidebarLabel" not in text:
    errors.append("Glossary sidebar row should render through a dedicated glossarySidebarLabel helper")

match = re.search(
    r"private var glossarySidebarLabel: some View \{(?P<body>[\s\S]*?)\n    \}\n\n    private var providerForm",
    text,
)
if not match:
    errors.append("SettingsView must define glossarySidebarLabel near the navigation helpers")
else:
    body = match.group("body")
    for token in [
        'Label(appState.t(.terminologyGlossary), systemImage: "text.book.closed")',
        "appState.isImportingGlossary",
        "ProgressView()",
        "appState.settings.glossaryEntries.count",
        'Text("\\(appState.settings.glossaryEntries.count)")',
        ".monospacedDigit()",
        "Capsule()",
    ]:
        if token not in body:
            errors.append(f"Glossary sidebar label must expose import/count status through {token}")
    if "appState.settings.glossaryEntries.isEmpty" not in body:
        errors.append("Glossary sidebar count badge should be hidden when the glossary is empty")
    if body.find("appState.isImportingGlossary") > body.find("appState.settings.glossaryEntries.count") >= 0:
        errors.append("Glossary sidebar should prioritize the active import indicator over the static count badge")

if errors:
    print("Glossary sidebar status badge verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Glossary sidebar status badge verification passed")
