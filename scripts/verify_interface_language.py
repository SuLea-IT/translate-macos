#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
interface_file = root / "LiveBuddy" / "Models" / "InterfaceLanguage.swift"
settings_file = root / "LiveBuddy" / "Models" / "AppSettings.swift"
settings_view = root / "LiveBuddy" / "Views" / "Settings" / "SettingsView.swift"
menu_bar_view = root / "LiveBuddy" / "Views" / "MenuBar" / "MenuBarView.swift"
transcripts_view = root / "LiveBuddy" / "Views" / "Settings" / "TranscriptsView.swift"

errors: list[str] = []
if not interface_file.exists():
    errors.append("missing LiveBuddy/Models/InterfaceLanguage.swift")
else:
    text = interface_file.read_text()
    required_languages = ["english", "simplifiedChinese", "japanese", "korean", "spanish", "french", "german", "vietnamese"]
    for language in required_languages:
        if f"case {language}" not in text:
            errors.append(f"missing InterfaceLanguage.{language}")
    required_keys = [
        "interfaceLanguage",
        "settings",
        "start",
        "translationAndAudio",
        "terminologyGlossary",
        "sourceTerm",
        "preferredTranslation",
        "preserveOriginalTerm",
        "addTerm",
        "deleteTerm",
        "test",
        "runTest",
        "preflightTest",
        "preflightTestDescription",
        "apiKeyTest",
        "permissionsTest",
        "microphoneAudioTest",
        "screenAudioTest",
        "subtitleWindowTest",
        "testPassed",
        "testWarning",
        "testFailed",
        "testRunning",
        "audioDetected",
        "audioTooQuiet",
        "audioClippingDetected",
        "subtitleTestMessage",
        "translateFrom",
        "autoDetectLanguage",
        "detectedSourceLanguage",
        "transcripts",
        "runtimeLogs",
        "subtitleDisplayMode",
        "exportGlossary",
        "exportTranscript",
        "exportAsSRT",
        "exportAsWebVTT",
        "exportAsMarkdown",
        "exportAsPlainText",
        "exportFailed",
        "connectionInterrupted",
        "connectionReconnecting",
        "connectionRecovered",
        "connectionReconnectFailed",
        "connectionProviderError",
        "globalShortcuts",
        "enableGlobalShortcuts",
        "shortcutToggleTranslation",
        "shortcutShowCaptionWindow",
        "shortcutToggleMute",
        "customizeShortcuts",
        "recordShortcut",
        "recordingShortcut",
        "clearShortcut",
        "resetShortcut",
        "resetAllShortcuts",
        "shortcutInvalid",
        "shortcutDuplicate",
        "apiKeyMissingTitle",
        "apiKeyMissingMessage",
        "apiKeyMissingRecovery",
        "diagnosticAPIKeyMissingTitle",
        "diagnosticAPIKeyMissingMessage",
        "diagnosticAPIKeyInvalidTitle",
        "diagnosticAPIKeyInvalidMessage",
        "diagnosticQuotaTitle",
        "diagnosticQuotaMessage",
        "diagnosticQuotaRecovery",
        "diagnosticModelUnavailableTitle",
        "diagnosticModelUnavailableMessage",
        "diagnosticProviderErrorTitle",
        "diagnosticProviderErrorMessage",
        "diagnosticNetworkUnavailableTitle",
        "diagnosticNetworkUnavailableMessage",
        "diagnosticNetworkTimeoutTitle",
        "diagnosticNetworkTimeoutMessage",
        "diagnosticConnectionLostTitle",
        "diagnosticConnectionLostMessage",
        "diagnosticMicrophonePermissionTitle",
        "diagnosticMicrophonePermissionMessage",
        "diagnosticScreenRecordingPermissionTitle",
        "diagnosticScreenRecordingPermissionMessage",
        "diagnosticMicrophoneUnavailableTitle",
        "diagnosticMicrophoneUnavailableMessage",
        "diagnosticScreenAudioUnavailableTitle",
        "diagnosticScreenAudioUnavailableMessage",
        "diagnosticSettingsSaveFailedTitle",
        "diagnosticSettingsSaveFailedMessage",
        "diagnosticTranscriptSaveFailedTitle",
        "diagnosticTranscriptSaveFailedMessage",
        "diagnosticUnknownTitle",
        "diagnosticUnknownMessage",
        "diagnosticOpenProviderRecovery",
        "diagnosticOpenMicrophoneRecovery",
        "diagnosticOpenScreenRecordingRecovery",
        "diagnosticRetryRecovery",
        "diagnosticCheckDiskRecovery",
        "diagnosticDetails",
        "diagnosticDismiss",
        "microphonePermissionRequired",
        "microphonePermissionRequiredMessage",
        "screenRecordingPermissionRequired",
        "screenRecordingPermissionRequiredMessage",
        "openMicrophoneSettings",
        "openScreenRecordingSettings",
        "cannotStart",
        "setupChecklist",
        "refreshStatus",
        "microphonePermission",
        "screenRecordingPermission",
        "granted",
        "missing",
        "notNeeded",
        "unknown",
        "checking",
        "apiKeyUnchecked",
        "apiKeyValid",
        "setupIncomplete",
    ]
    for key in required_keys:
        if f"case {key}" not in text:
            errors.append(f"missing InterfaceText.{key}")
    for key in required_keys[6:]:
        if text.count(f".{key}:") < len(required_languages):
            errors.append(f"InterfaceText.{key} must be translated for every supported language")
    for expected in [
        "界面语言",
        "设置",
        "開始",
        "한국어",
        "Español",
        "Tiếng Việt",
        "需要 API 密钥",
        "API キーが必要です",
        "마이크 권한 필요",
        "Se requiere clave API",
        "Clé API requise",
        "API-Schlüssel erforderlich",
        "Cần khóa API",
    ]:
        if expected not in text:
            errors.append(f"missing localized text {expected!r}")

settings_text = settings_file.read_text()
if "var interfaceLanguage: InterfaceLanguage = .english" not in settings_text:
    errors.append("AppSettings must persist interfaceLanguage with English default")
if "interfaceLanguage" not in settings_text or "decodeIfPresent" not in settings_text:
    errors.append("AppSettings must decode legacy settings without resetting existing preferences")
if re.search(r"requiresSessionRestart[\s\S]*interfaceLanguage", settings_text):
    errors.append("interfaceLanguage must not require a Gemini session restart")

settings_view_text = settings_view.read_text()
menu_bar_text = menu_bar_view.read_text()
transcripts_text = transcripts_view.read_text()
if "Picker(appState.t(.interfaceLanguage), selection: appState.binding(\\.interfaceLanguage))" not in settings_view_text:
    errors.append("SettingsView must expose an Interface Language picker")
if "Picker(appState.t(.interfaceLanguage), selection: appState.binding(\\.interfaceLanguage))" not in menu_bar_text:
    errors.append("MenuBarView must expose an Interface Language picker")
for file_name, text in [
    ("SettingsView", settings_view_text),
    ("MenuBarView", menu_bar_text),
    ("TranscriptsView", transcripts_text),
]:
    if "appState.t(" not in text:
        errors.append(f"{file_name} must render localized interface text via appState.t(...)")

if errors:
    print("Interface language verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("Interface language verification passed")
