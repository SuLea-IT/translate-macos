#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
registrar_path = root / "LiveBuddy" / "Services" / "CarbonGlobalShortcutRegistrar.swift"
text = registrar_path.read_text()
errors = []

register_match = re.search(r"func register\(_ shortcuts: \[GlobalShortcut\], handler: @escaping \(GlobalShortcutAction\) -> Void\) -> \[GlobalShortcutRegistrationResult\] \{(?P<body>[\s\S]*?)\n    \}\n\n    func unregisterAll", text)
if not register_match:
    errors.append("CarbonGlobalShortcutRegistrar.register not found")
else:
    body = register_match.group("body")
    for token in [
        "unregisterAll()",
        "guard !shortcuts.isEmpty else { return [] }",
        "self.handler = handler",
        "let handlerStatus = installHandlerIfNeeded()",
        "guard handlerStatus == noErr else",
        "self.handler = nil",
        "return shortcuts.map { shortcut in",
        "GlobalShortcutRegistrationResult(shortcut: shortcut, status: .failed(Int32(handlerStatus)))",
    ]:
        if token not in body:
            errors.append(f"register must avoid stale/phantom global shortcut handlers through {token}")
    unregister_idx = body.find("unregisterAll()")
    empty_idx = body.find("guard !shortcuts.isEmpty else { return [] }")
    assign_idx = body.find("self.handler = handler")
    install_idx = body.find("let handlerStatus = installHandlerIfNeeded()")
    guard_idx = body.find("guard handlerStatus == noErr else")
    map_idx = body.find("return shortcuts.map { shortcut in")
    if min(unregister_idx, empty_idx, assign_idx, install_idx, guard_idx, map_idx) != -1 and not (unregister_idx < empty_idx < assign_idx < install_idx < guard_idx < map_idx):
        errors.append("register must unregister, skip empty shortcuts, install handler, check status, then register hotkeys in order")

install_match = re.search(r"private func installHandlerIfNeeded\(\) -> OSStatus \{(?P<body>[\s\S]*?)\n    \}\n\n    private func handle", text)
if not install_match:
    errors.append("installHandlerIfNeeded must return OSStatus")
else:
    body = install_match.group("body")
    for token in [
        "guard eventHandler == nil else { return noErr }",
        "let status = InstallEventHandler(",
        "guard status == noErr else { return status }",
        "return noErr",
    ]:
        if token not in body:
            errors.append(f"installHandlerIfNeeded must surface Carbon handler install status through {token}")

if "private func installHandlerIfNeeded() {" in text:
    errors.append("installHandlerIfNeeded must not ignore InstallEventHandler status")

if errors:
    print("Global shortcut handler install verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Global shortcut handler install verification passed")
