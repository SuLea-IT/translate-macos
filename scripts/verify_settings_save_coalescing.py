#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
path = root / "LiveBuddy" / "Models" / "AppState.swift"
app_delegate_path = root / "LiveBuddy" / "App" / "AppDelegate.swift"
text = path.read_text()
app_delegate = app_delegate_path.read_text()
errors: list[str] = []

for token in [
    "private static let settingsSaveDebounceNanoseconds",
    "private var settingsSaveTask: Task<Void, Never>?",
]:
    if token not in text:
        errors.append(f"AppState must coalesce settings disk writes through {token}")

did_set_match = re.search(r"@Published private\(set\) var settings: AppSettings \{\n        didSet \{(?P<body>[\s\S]*?)\n        \}\n    \}", text)
if not did_set_match:
    errors.append("AppState.settings didSet not found")
else:
    body = did_set_match.group("body")
    for token in [
        "scheduleSettingsSave()",
        "rebuildRunningSessionIfNeeded(oldValue: oldValue)",
        "configureGlobalShortcutsIfNeeded(oldValue: oldValue)",
        "updateAudioPlayerVolumeIfNeeded(oldValue: oldValue)",
        "updateUsageControlSettingsIfNeeded(oldValue: oldValue)",
    ]:
        if token not in body:
            errors.append(f"settings didSet must keep side effects and coalesce persistence through {token}")
    if "saveSettings()" in body:
        errors.append("settings didSet must not synchronously write settings.json on every UI adjustment")

schedule_match = re.search(r"private func scheduleSettingsSave\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func saveSettingsImmediately", text)
if not schedule_match:
    errors.append("AppState.scheduleSettingsSave() not found")
else:
    body = schedule_match.group("body")
    for token in [
        "guard settingsSaveTask == nil else { return }",
        "Task { @MainActor [weak self] in",
        "try await Task.sleep(nanoseconds: Self.settingsSaveDebounceNanoseconds)",
        "guard !Task.isCancelled else",
        "self.saveSettings()",
        "self.settingsSaveTask = nil",
    ]:
        if token not in body:
            errors.append(f"scheduleSettingsSave must throttle saves and clear lifecycle state through {token}")

immediate_match = re.search(r"private func saveSettingsImmediately\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    private func saveSettings", text)
if not immediate_match:
    errors.append("AppState.saveSettingsImmediately() not found")
else:
    body = immediate_match.group("body")
    for token in ["settingsSaveTask?.cancel()", "settingsSaveTask = nil", "saveSettings()"]:
        if token not in body:
            errors.append(f"Immediate settings saves must cancel pending throttled saves through {token}")

init_match = re.search(r"if shouldRewriteSettings \{(?P<body>[\s\S]*?)\n        \}\n        updateAudioPlayerVolume", text)
if not init_match:
    errors.append("AppState legacy settings rewrite block not found")
elif "saveSettingsImmediately()" not in init_match.group("body"):
    errors.append("Legacy settings migration must rewrite settings immediately")

flush_match = re.search(r"func flushPendingStateBeforeTermination\(\) \{(?P<body>[\s\S]*?)\n    \}\n\n    func binding", text)
if not flush_match:
    errors.append("AppState.flushPendingStateBeforeTermination() not found")
else:
    body = flush_match.group("body")
    for token in ["saveSettingsImmediately()", "saveTranscriptSessionsImmediately()", "saveUsageLedger()"]:
        if token not in body:
            errors.append(f"AppState termination flush must persist pending state through {token}")

if "appState?.flushPendingStateBeforeTermination()" not in app_delegate:
    errors.append("AppDelegate.applicationWillTerminate must flush pending AppState saves before shutdown")

# Deinit cannot call actor-isolated save methods directly; it must only cancel pending work.
deinit_start = text.find("deinit {")
if deinit_start == -1:
    errors.append("AppState.deinit not found")
else:
    deinit_body = text[deinit_start:]
    for token in ["settingsSaveTask?.cancel()", "settingsSaveTask = nil"]:
        if token not in deinit_body:
            errors.append(f"AppState.deinit must cancel pending settings saves through {token}")
    if "saveSettings()" in deinit_body:
        errors.append("AppState.deinit must not directly call actor-isolated saveSettings(); termination flush handles final persistence")

if errors:
    print("Settings save coalescing verification failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

print("Settings save coalescing verification passed")
