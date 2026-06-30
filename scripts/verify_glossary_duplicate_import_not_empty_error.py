#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
service_path = root / "LiveBuddy" / "Services" / "GlossaryImportService.swift"
app_state_path = root / "LiveBuddy" / "Models" / "AppState.swift"
service = service_path.read_text()
app_state = app_state_path.read_text()
errors: list[str] = []

if "private func shouldTreatImportAsEmpty(_ result: GlossaryImportResult) -> Bool" not in service:
    errors.append("GlossaryImportService must centralize empty-import detection so duplicate-only imports are not reported as empty")
else:
    helper_match = re.search(r"private func shouldTreatImportAsEmpty\(_ result: GlossaryImportResult\) -> Bool \{(?P<body>[\s\S]*?)\n    \}", service)
    if not helper_match:
        errors.append("GlossaryImportService.shouldTreatImportAsEmpty(_:) body not found")
    else:
        body = helper_match.group("body")
        for token in ["result.entries.isEmpty", "result.skippedDuplicate == 0"]:
            if token not in body:
                errors.append(f"Empty-import detection must allow duplicate-only imports through {token}")

if service.count("if shouldTreatImportAsEmpty(result) {") < 2:
    errors.append("Both remote and local glossary imports must use shouldTreatImportAsEmpty(result)")

if "if result.entries.isEmpty {\n                throw GlossaryImportError.emptyImport" in service:
    errors.append("Remote import must not throw emptyImport solely because result.entries is empty")

if "if result.entries.isEmpty {\n            throw GlossaryImportError.emptyImport" in service:
    errors.append("Local file import must not throw emptyImport solely because result.entries is empty")

apply_match = re.search(r"private func applyGlossaryImportResult\(_ result: GlossaryImportResult\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func handleGlossaryImportFailure", app_state)
if not apply_match:
    errors.append("AppState.applyGlossaryImportResult(_:) not found")
else:
    body = apply_match.group("body")
    for token in ["result.added", "result.skippedDuplicate", "settings.interfaceLanguage.localized"]:
        if token not in body:
            errors.append(f"Duplicate-only imports should still complete with a localized result message through {token}")

if errors:
    print("Glossary duplicate import empty-error verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Glossary duplicate import empty-error verification passed")
