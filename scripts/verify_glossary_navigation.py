#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
settings_view = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
text = settings_view.read_text()
errors: list[str] = []

if "case glossary" not in text:
    errors.append("NavigationItem must include a dedicated glossary case")
if "NavigationLink(value: NavigationItem.glossary)" not in text:
    errors.append("Settings sidebar must include a glossary NavigationLink")
if "Label(appState.t(.terminologyGlossary), systemImage:" not in text:
    errors.append("Glossary sidebar item must use the localized terminology label")
if "case .glossary:" not in text:
    errors.append("Detail switch must render a dedicated glossary page")
if "private var glossaryForm:" not in text:
    errors.append("Glossary UI should live in a dedicated glossaryForm")
caption_start = text.find("private var captionForm: some View")
glossary_start = text.find("private var glossaryForm: some View")
if caption_start == -1:
    errors.append("missing captionForm")
elif glossary_start == -1:
    errors.append("missing glossaryForm")
else:
    caption_body = text[caption_start:glossary_start]
    if "glossarySection" in caption_body or "terminologyGlossary" in caption_body:
        errors.append("Caption page must not render the glossary section")
if "GlossaryListDisplay(" not in text:
    errors.append("Glossary page must use GlossaryListDisplay to avoid showing all entries by default")
if "isGlossaryListExpanded" not in text:
    errors.append("Glossary page must have expand/collapse state")
if "glossarySearchText" not in text or ".searchGlossaryTerms" not in text:
    errors.append("Glossary page must provide a search field for large imported glossaries")
if "query: glossarySearchText" not in text:
    errors.append("GlossaryListDisplay must filter entries by the glossary search text")
if "GlossaryExportDocument" not in text:
    errors.append("Glossary page must prepare a FileDocument for CSV export")
if "prepareGlossaryExport()" not in text:
    errors.append("Glossary page must expose an export action")
if ".exportGlossary" not in text:
    errors.append("Glossary export button must use localized text")
if ".clearGlossary" not in text:
    errors.append("Glossary page must expose a localized bulk clear action")
if "isShowingClearGlossaryConfirmation" not in text or ".confirmationDialog(" not in text:
    errors.append("Bulk clearing the glossary must require confirmation")
if "clearGlossaryEntries()" not in text:
    errors.append("Glossary page must call AppState.clearGlossaryEntries() for bulk reset")

glossary_model = root / "LiveBuddy" / "Models" / "Glossary.swift"
model_text = glossary_model.read_text()
if "struct GlossaryExporter" not in model_text:
    errors.append("Glossary model must include a CSV exporter")
if "source,target,note,isEnabled" not in model_text:
    errors.append("Glossary exporter must include a stable CSV header")
if "deleteAll(from entries:" not in model_text:
    errors.append("Glossary editor must provide a bulk delete/reset helper")

app_state = root / "LiveBuddy" / "Models" / "AppState.swift"
app_state_text = app_state.read_text()
if "func clearGlossaryEntries()" not in app_state_text:
    errors.append("AppState must expose clearGlossaryEntries() for the glossary UI")

if errors:
    print("Glossary navigation verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)
print("Glossary navigation verification passed")
