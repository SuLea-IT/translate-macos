#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
client = root / "LiveBuddy" / "Services" / "GeminiLiveTranslateClient.swift"
settings = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
errors: list[str] = []

client_text = client.read_text()
settings_text = settings.read_text()

for token in ["socketOpenTimeout", "setupMessageTimeout", "withLiveTimeout", "receiveMessage(timeout:"]:
    if token not in client_text:
        errors.append(f"GeminiLiveTranslateClient must use bounded websocket/setup waits through {token}")
if "if completion.resume(throwing: LiveTranslateError.setupTimedOut)" not in client_text:
    errors.append("Timeout cleanup must only run when the timeout wins the one-shot completion race")
if "@discardableResult\n    func resume(with result:" not in client_text:
    errors.append("Live timeout completion must report whether it actually resumed the continuation")

connect_match = re.search(r"func connect\(\) async throws \{(?P<body>[\s\S]*?)\n    \}", client_text)
if not connect_match:
    errors.append("GeminiLiveTranslateClient.connect() not found")
else:
    body = connect_match.group("body")
    if "do {" not in body or "catch" not in body or "close()" not in body:
        errors.append("GeminiLiveTranslateClient.connect() must close the socket/session when connect or setup fails")

close_match = re.search(r"func close\(\) \{(?P<body>[\s\S]*?)\n    \}", client_text)
if not close_match:
    errors.append("GeminiLiveTranslateClient.close() not found")
else:
    body = close_match.group("body")
    if "openContinuation?.resume(throwing:" not in body or "openContinuation = nil" not in body:
        errors.append("GeminiLiveTranslateClient.close() must resume and clear any pending open continuation")

file_import_match = re.search(r"private func handleGlossaryFileImporterResult[\s\S]*?case \.success\(let urls\):(?P<body>[\s\S]*?)case \.failure", settings_text)
if not file_import_match:
    errors.append("SettingsView.handleGlossaryFileImporterResult success branch not found")
else:
    body = file_import_match.group("body")
    if "defer" not in body or "stopAccessingSecurityScopedResource" not in body:
        errors.append("Local glossary import must release security-scoped resources via defer inside the import task")

if errors:
    print("Runtime closure verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)
print("Runtime closure verification passed")
