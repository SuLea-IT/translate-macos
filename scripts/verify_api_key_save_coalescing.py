#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

for token in [
    "private static let apiKeySaveDebounceNanoseconds",
    "private var apiKeySaveTask: Task<Void, Never>?",
    "private var pendingAPIKeyForKeychain",
]:
    if token not in text:
        errors.append(f"AppState must coalesce Keychain writes through {token}")

update_match = re.search(r"func updateAPIKey\(_ apiKey: String\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func scheduleAPIKeySave", text)
if not update_match:
    errors.append("AppState.updateAPIKey(_:) not found")
else:
    body = update_match.group("body")
    for token in ["settings.apiKey = apiKey", "scheduleAPIKeySave(apiKey)"]:
        if token not in body:
            errors.append(f"updateAPIKey must update UI state immediately and defer Keychain writes through {token}")
    if "apiKeyStore.save" in body:
        errors.append("updateAPIKey must not synchronously write Keychain on every keystroke")

schedule_match = re.search(r"private func scheduleAPIKeySave\(_ apiKey: String\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func saveAPIKeyImmediately", text)
if not schedule_match:
    errors.append("AppState.scheduleAPIKeySave(_:) not found")
else:
    body = schedule_match.group("body")
    for token in [
        "pendingAPIKeyForKeychain = apiKey",
        "apiKeySaveTask?.cancel()",
        "Task { @MainActor [weak self] in",
        "try await Task.sleep(nanoseconds: Self.apiKeySaveDebounceNanoseconds)",
        "guard !Task.isCancelled else",
        "self.savePendingAPIKeyToKeychain()",
        "self.apiKeySaveTask = nil",
    ]:
        if token not in body:
            errors.append(f"scheduleAPIKeySave must debounce Keychain writes through {token}")

immediate_match = re.search(r"private func saveAPIKeyImmediately\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func savePendingAPIKeyToKeychain", text)
if not immediate_match:
    errors.append("AppState.saveAPIKeyImmediately() not found")
else:
    body = immediate_match.group("body")
    for token in [
        "pendingAPIKeyForKeychain = settings.apiKey",
        "apiKeySaveTask?.cancel()",
        "apiKeySaveTask = nil",
        "savePendingAPIKeyToKeychain()",
    ]:
        if token not in body:
            errors.append(f"Immediate API key saves must flush the latest value through {token}")

save_pending_match = re.search(r"private func savePendingAPIKeyToKeychain\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func updateSetting", text)
if not save_pending_match:
    errors.append("AppState.savePendingAPIKeyToKeychain() not found")
else:
    body = save_pending_match.group("body")
    for token in [
        "guard let apiKey = pendingAPIKeyForKeychain else { return }",
        "try apiKeyStore.save(apiKey)",
        "pendingAPIKeyForKeychain = nil",
        "DiagnosticClassifier.storage(.settingsSaveFailed",
    ]:
        if token not in body:
            errors.append(f"Pending API key save must handle success/failure through {token}")

flush_match = re.search(r"func flushPendingStateBeforeTermination\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func binding", text)
if not flush_match:
    errors.append("AppState.flushPendingStateBeforeTermination() not found")
elif "saveAPIKeyImmediately()" not in flush_match.group("body"):
    errors.append("Termination flush must save the latest API key before exit")

deinit_start = text.find("deinit {")
if deinit_start == -1:
    errors.append("AppState.deinit not found")
else:
    deinit_body = text[deinit_start:]
    for token in ["apiKeySaveTask?.cancel()", "apiKeySaveTask = nil"]:
        if token not in deinit_body:
            errors.append(f"AppState.deinit must cancel pending API key save through {token}")

if errors:
    print("API key save coalescing verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("API key save coalescing verification passed")
