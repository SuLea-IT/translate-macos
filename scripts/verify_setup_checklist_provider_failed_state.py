#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
view_path = root / "LiveBuddy" / "Views" / "Settings" / "SetupChecklistView.swift"
model_path = root / "LiveBuddy" / "Models" / "PermissionStatus.swift"
tests_path = root / "LiveBuddyTests" / "SetupChecklistTests.swift"

view = view_path.read_text()
model = model_path.read_text()
tests = tests_path.read_text()
errors: list[str] = []

if "transientProviderFailureDoesNotBlockStart" not in tests:
    errors.append("SetupChecklistTests must document that transient provider failures do not block start")
if "case .unchecked, .checking, .valid, .failed:" not in model:
    errors.append("SetupChecklistState must continue treating provider .failed as non-blocking")

provider_state = re.search(
    r"private var providerState: ChecklistRequirementState \{(?P<body>[\s\S]*?)\n    \}\n\n    private var providerDetail",
    view,
)
if not provider_state:
    errors.append("SetupChecklistView.providerState not found")
else:
    body = provider_state.group("body")
    if "case .missing, .invalid, .failed:" in body:
        errors.append("SetupChecklistView.providerState must not render transient provider .failed as blocked")
    for token in [
        "case .missing, .invalid:",
        "return .blocked",
        "case .failed:",
        "return .unknown",
    ]:
        if token not in body:
            errors.append(f"providerState must mirror non-blocking provider-failed semantics through {token}")

if errors:
    print("Setup checklist provider failed-state verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Setup checklist provider failed-state verification passed")
