#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
interface = (root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift").read_text()
app_state = (root / "LiveBuddy" / "Models" / "AppState.swift").read_text()
errors: list[str] = []

for key in ["glossaryFileTooLarge", "glossaryImportFailed"]:
    if f"case {key}" not in interface:
        errors.append(f"InterfaceText must include {key}")
    if interface.count(f".{key}:") < 8:
        errors.append(f"InterfaceText.{key} must be translated for every supported language")

match = re.search(
    r"private func handleGlossaryImportFailure\(_ error: Error\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func configureGlobalShortcuts",
    app_state,
)
if not match:
    errors.append("AppState.handleGlossaryImportFailure(_:) not found")
else:
    body = match.group("body")
    for token in [
        "case .fileTooLarge:",
        "glossaryImportMessage = settings.interfaceLanguage.localized(.glossaryFileTooLarge)",
        "case .parseFailed(let message):",
        "let baseMessage = settings.interfaceLanguage.localized(.glossaryImportFailed)",
        'glossaryImportMessage = detail.isEmpty ? baseMessage : "\\(baseMessage): \\(detail)"',
    ]:
        if token not in body:
            errors.append(f"Glossary import failures must localize file-too-large/parse errors through {token}")
    if "case .fileTooLarge, .parseFailed:" in body:
        errors.append("file-too-large and parse failures must not fall back to raw localizedDescription")
    if "glossaryImportMessage = importError.localizedDescription" in body:
        errors.append("known GlossaryImportError cases must not expose raw English localizedDescription")

if errors:
    print("Glossary import error localization verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary import error localization passed")
