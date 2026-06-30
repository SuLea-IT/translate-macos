#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
text = path.read_text()
errors: list[str] = []

helper_match = re.search(
    r"private func clearResolvedStorageDiagnostic\(_ code: DiagnosticCode\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func updateSetting",
    text,
)
if not helper_match:
    errors.append("AppState.clearResolvedStorageDiagnostic(_:) must exist before updateSetting")
else:
    body = helper_match.group("body")
    for token in [
        "guard currentDiagnosticIssue?.code == code else { return }",
        "setDiagnosticIssue(nil)",
    ]:
        if token not in body:
            errors.append(f"clearResolvedStorageDiagnostic must clear only matching storage diagnostics through {token}")

save_api_match = re.search(
    r"private func savePendingAPIKeyToKeychain\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func clearResolvedStorageDiagnostic",
    text,
)
if not save_api_match:
    errors.append("AppState.savePendingAPIKeyToKeychain() not found before storage cleanup helper")
else:
    body = save_api_match.group("body")
    for token in [
        "try apiKeyStore.save(apiKey)",
        "pendingAPIKeyForKeychain = nil",
        "clearResolvedStorageDiagnostic(.settingsSaveFailed)",
    ]:
        if token not in body:
            errors.append(f"Successful API key save must clear stale settings storage diagnostics through {token}")
    save_idx = body.find("try apiKeyStore.save(apiKey)")
    pending_idx = body.find("pendingAPIKeyForKeychain = nil", save_idx)
    clear_idx = body.find("clearResolvedStorageDiagnostic(.settingsSaveFailed)", pending_idx)
    catch_idx = body.find("} catch", clear_idx)
    if -1 in [save_idx, pending_idx, clear_idx, catch_idx] or not (save_idx < pending_idx < clear_idx < catch_idx):
        errors.append("API key storage diagnostic cleanup must run only on successful Keychain save before the catch block")

save_settings_match = re.search(
    r"private func saveSettings\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private static func loadUsageLedger",
    text,
)
if not save_settings_match:
    errors.append("AppState.saveSettings() not found")
else:
    body = save_settings_match.group("body")
    for token in [
        "try data.write(to: settingsURL, options: [.atomic])",
        "clearResolvedStorageDiagnostic(.settingsSaveFailed)",
    ]:
        if token not in body:
            errors.append(f"Successful settings save must clear stale settings diagnostics through {token}")
    write_idx = body.find("try data.write(to: settingsURL, options: [.atomic])")
    clear_idx = body.find("clearResolvedStorageDiagnostic(.settingsSaveFailed)", write_idx)
    catch_idx = body.find("} catch", clear_idx)
    if -1 in [write_idx, clear_idx, catch_idx] or not (write_idx < clear_idx < catch_idx):
        errors.append("Settings storage diagnostic cleanup must run only after a successful settings file write")

save_transcripts_match = re.search(
    r"private func saveTranscriptSessions\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func loadTranscriptSessions",
    text,
)
if not save_transcripts_match:
    errors.append("AppState.saveTranscriptSessions() not found")
else:
    body = save_transcripts_match.group("body")
    for token in [
        "try data.write(to: transcriptsURL, options: [.atomic])",
        "clearResolvedStorageDiagnostic(.transcriptSaveFailed)",
    ]:
        if token not in body:
            errors.append(f"Successful transcript save must clear stale transcript diagnostics through {token}")
    write_idx = body.find("try data.write(to: transcriptsURL, options: [.atomic])")
    clear_idx = body.find("clearResolvedStorageDiagnostic(.transcriptSaveFailed)", write_idx)
    catch_idx = body.find("} catch", clear_idx)
    if -1 in [write_idx, clear_idx, catch_idx] or not (write_idx < clear_idx < catch_idx):
        errors.append("Transcript storage diagnostic cleanup must run only after a successful transcript file write")

if errors:
    print("Storage diagnostic success cleanup verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Storage diagnostic success cleanup verification passed")
