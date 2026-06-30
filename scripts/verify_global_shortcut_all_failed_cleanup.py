#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Services" / "CarbonGlobalShortcutRegistrar.swift"
text = path.read_text()
errors: list[str] = []

register_match = re.search(
    r"func register\(_ shortcuts: \[GlobalShortcut\], handler: @escaping \(GlobalShortcutAction\) -> Void\) -> \[GlobalShortcutRegistrationResult\] \{(?P<body>[\s\S]*?)\n    \}\n\n    func unregisterAll",
    text,
)
if not register_match:
    errors.append("CarbonGlobalShortcutRegistrar.register not found")
else:
    body = register_match.group("body")
    for token in [
        "let results = shortcuts.map { shortcut in",
        "if !results.contains(where: { $0.status == .registered }) {",
        "unregisterAll()",
        "return results",
    ]:
        if token not in body:
            errors.append(f"register must clean the Carbon handler when every hot key registration fails through {token}")
    map_idx = body.find("let results = shortcuts.map { shortcut in")
    cleanup_idx = body.find("if !results.contains(where: { $0.status == .registered }) {", map_idx)
    unregister_idx = body.find("unregisterAll()", cleanup_idx)
    return_idx = body.find("return results", unregister_idx)
    if -1 in [map_idx, cleanup_idx, unregister_idx, return_idx] or not (map_idx < cleanup_idx < unregister_idx < return_idx):
        errors.append("register must build all results, clean up no-success registrations, then return the original failures")
    if "return shortcuts.map { shortcut in\n            var hotKeyRef" in body:
        errors.append("register must not return directly from the hotkey registration map before checking whether any hotkey registered")


if errors:
    print("Global shortcut all-failed cleanup verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Global shortcut all-failed cleanup verification passed")
