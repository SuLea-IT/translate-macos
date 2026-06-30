#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Views" / "Caption" / "CaptionPanelController.swift"
text = path.read_text()
errors: list[str] = []

match = re.search(r"deinit \{(?P<body>[\s\S]*?)\n    \}\n\n    func show", text)
if not match:
    errors.append("CaptionPanelController must explicitly clean up its panel, delegate, content view, and Combine subscription in deinit")
else:
    body = match.group("body")
    for token in [
        "titleCancellable?.cancel()",
        "titleCancellable = nil",
        "MainActor.assumeIsolated {",
        "panel.delegate = nil",
        "panel.contentView = nil",
        "panel.orderOut(nil)",
    ]:
        if token not in body:
            errors.append(f"CaptionPanelController.deinit must release window lifecycle state through {token}")
    order_idx = body.find("panel.orderOut(nil)")
    content_idx = body.find("panel.contentView = nil")
    delegate_idx = body.find("panel.delegate = nil")
    if -1 not in [order_idx, content_idx, delegate_idx] and not (order_idx < content_idx < delegate_idx):
        errors.append("CaptionPanelController.deinit should hide the panel before tearing down hosting content and delegate")

if errors:
    print("Caption panel deinit cleanup verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Caption panel deinit cleanup verification passed")
