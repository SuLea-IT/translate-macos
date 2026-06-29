#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
errors: list[str] = []

required_files = [
    "LiveBuddy/Models/PermissionStatus.swift",
    "LiveBuddy/Models/ProviderHealthStatus.swift",
    "LiveBuddy/Models/UserFacingError.swift",
    "LiveBuddy/Services/SystemSettingsNavigator.swift",
    "LiveBuddy/Services/PermissionStatusService.swift",
    "LiveBuddy/Services/ProviderHealthService.swift",
    "LiveBuddy/Views/Settings/SetupChecklistView.swift",
    "LiveBuddy/Services/APIKeyStore.swift",
    "LiveBuddy/Services/KeychainSecretStore.swift",
    "LiveBuddy/Models/SubtitleDisplayMode.swift",
    "LiveBuddy/Models/GlobalShortcut.swift",
    "LiveBuddy/Services/CarbonGlobalShortcutRegistrar.swift",
    "LiveBuddy/Models/TranscriptExport.swift",
    "LiveBuddy/Services/TranscriptExportDocument.swift",
    "LiveBuddy/Models/ConnectionRecovery.swift",
    "LiveBuddy/Models/Glossary.swift",
    "LiveBuddy/Models/PreflightTest.swift",
    "LiveBuddy/Services/PreflightTestRunner.swift",
    "LiveBuddy/Models/DiagnosticIssue.swift",
]
for rel in required_files:
    if not (root / rel).exists():
        errors.append(f"missing {rel}")

permission_file = root / "LiveBuddy/Models/PermissionStatus.swift"
if permission_file.exists():
    text = permission_file.read_text()
    for token in [
        "enum PermissionRequirement",
        "enum PermissionGrantState",
        "struct PermissionStatus",
        "enum ChecklistRequirementState",
        "struct PermissionChecklistItem",
        "enum SetupBlockingIssue",
        "struct SetupChecklistState",
        "enum SetupPreflightResult",
    ]:
        if token not in text:
            errors.append(f"PermissionStatus.swift missing {token}")

provider_file = root / "LiveBuddy/Models/ProviderHealthStatus.swift"
if provider_file.exists():
    text = provider_file.read_text()
    for token in ["enum ProviderHealthStatus", "var blocksStart"]:
        if token not in text:
            errors.append(f"ProviderHealthStatus.swift missing {token}")


user_error_file = root / "LiveBuddy/Models/UserFacingError.swift"
if user_error_file.exists():
    text = user_error_file.read_text()
    for token in ["enum UserFacingErrorKind", "enum UserFacingErrorAction", "struct UserFacingError", "from(blockingIssues:"]:
        if token not in text:
            errors.append(f"UserFacingError.swift missing {token}")

diagnostic_file = root / "LiveBuddy/Models/DiagnosticIssue.swift"
if diagnostic_file.exists():
    text = diagnostic_file.read_text()
    for token in ["enum DiagnosticCode", "struct DiagnosticIssue", "struct DiagnosticClassifier", "quotaOrBilling", "networkTimeout"]:
        if token not in text:
            errors.append(f"DiagnosticIssue.swift missing {token}")
    for forbidden in ["GeminiLiveTranslateClient", "MicrophoneCapture(", "ScreenAudioCapture("]:
        if forbidden in text:
            errors.append(f"Diagnostic classifier must stay pure and not reference {forbidden}")

settings_navigator_file = root / "LiveBuddy/Services/SystemSettingsNavigator.swift"
if settings_navigator_file.exists():
    text = settings_navigator_file.read_text()
    for token in ["enum SystemSettingsDestination", "Privacy_Microphone", "Privacy_ScreenCapture", "struct SystemSettingsNavigator"]:
        if token not in text:
            errors.append(f"SystemSettingsNavigator.swift missing {token}")

permission_service_file = root / "LiveBuddy/Services/PermissionStatusService.swift"
if permission_service_file.exists():
    text = permission_service_file.read_text()
    for token in ["struct PermissionStatusService", "AVCaptureDevice.authorizationStatus", "CGPreflightScreenCaptureAccess", "CGRequestScreenCaptureAccess"]:
        if token not in text:
            errors.append(f"PermissionStatusService.swift missing {token}")
    for forbidden in ["SCStream", "SCShareableContent", "AVAudioEngine", "GeminiLiveTranslateClient"]:
        if forbidden in text:
            errors.append(f"PermissionStatusService.swift must not create or reference heavy runtime object {forbidden}")

provider_health_file = root / "LiveBuddy/Services/ProviderHealthService.swift"
if provider_health_file.exists():
    text = provider_health_file.read_text()
    for token in ["struct ProviderHealthService", "func verify(apiKey:", "geminiDefault", "gemini-3.1-flash-lite"]:
        if token not in text:
            errors.append(f"ProviderHealthService.swift missing {token}")

api_key_store_file = root / "LiveBuddy/Services/APIKeyStore.swift"
if api_key_store_file.exists():
    text = api_key_store_file.read_text()
    for token in ["protocol SecretStore", "struct APIKeyStore", "gemini-api-key", "func save(_ apiKey: String)"]:
        if token not in text:
            errors.append(f"APIKeyStore.swift missing {token}")

keychain_store_file = root / "LiveBuddy/Services/KeychainSecretStore.swift"
if keychain_store_file.exists():
    text = keychain_store_file.read_text()
    for token in ["import Security", "SecItemCopyMatching", "SecItemAdd", "SecItemUpdate", "SecItemDelete", "kSecAttrAccessibleWhenUnlockedThisDeviceOnly"]:
        if token not in text:
            errors.append(f"KeychainSecretStore.swift missing {token}")

app_state_file = root / "LiveBuddy/Models/AppState.swift"
if app_state_file.exists():
    text = app_state_file.read_text()
    if "providerHealthService.verify(apiKey:" not in text:
        errors.append("AppState.verifyGeminiToken must call ProviderHealthService")
    if "private func pingGeminiModel" in text:
        errors.append("AppState must not keep Gemini ping implementation inline")
    if "APIKeyStore" not in text or "apiKeyBinding()" not in text:
        errors.append("AppState must use APIKeyStore and expose apiKeyBinding()")
    for token in ["globalShortcutRegistrar", "configureGlobalShortcuts", "performGlobalShortcut"]:
        if token not in text:
            errors.append(f"AppState must wire global shortcuts through {token}")
    for token in ["settings.globalShortcuts.enabledShortcuts", "updateGlobalShortcut", "resetAllGlobalShortcuts"]:
        if token not in text:
            errors.append(f"AppState must support custom global shortcuts through {token}")
    for token in ["connectionRecoveryPolicy", "handleConnectionEvent", "scheduleReconnect", "reconnectGeminiClient", "onConnectionEvent"]:
        if token not in text:
            errors.append(f"AppState must wire connection recovery through {token}")
    for token in ["detectedSourceLanguageCode", "languagePairDisplayText", "sourceLanguageDisplayText"]:
        if token not in text:
            errors.append(f"AppState must expose source language display through {token}")
    for token in ["addGlossaryEntry", "deleteGlossaryEntry"]:
        if token not in text:
            errors.append(f"AppState must expose terminology glossary editing through {token}")
    for token in ["preflightTestReport", "isRunningPreflightTest", "runPreflightTest", "showTemporaryTestCaption"]:
        if token not in text:
            errors.append(f"AppState must expose preflight test support through {token}")
    for token in ["currentDiagnosticIssue", "clearDiagnosticIssue", "performDiagnosticRecoveryAction", "DiagnosticClassifier"]:
        if token not in text:
            errors.append(f"AppState must expose diagnostic guidance through {token}")
    if "func runStartPreflight() async -> SetupPreflightResult" not in text:
        errors.append("AppState must expose runStartPreflight()")
    start_index = text.find("func start() async")
    preflight_index = text.find("runStartPreflight()", start_index)
    client_index = text.find("GeminiLiveTranslateClient(settings:", start_index)
    capture_index = text.find("startCapture()", start_index)
    if min(start_index, preflight_index, client_index, capture_index) == -1:
        errors.append("AppState.start must contain preflight, Gemini client creation, and capture start")
    else:
        if not (preflight_index < client_index):
            errors.append("AppState.start must run preflight before creating GeminiLiveTranslateClient")
        if not (preflight_index < capture_index):
            errors.append("AppState.start must run preflight before startCapture()")

setup_checklist_view = root / "LiveBuddy/Views/Settings/SetupChecklistView.swift"
if setup_checklist_view.exists():
    text = setup_checklist_view.read_text()
    for token in ["struct SetupChecklistView", "refreshSetupChecklist()", "setupChecklist", "openMicrophoneSettings()", "openScreenRecordingSettings()"]:
        if token not in text:
            errors.append(f"SetupChecklistView.swift missing {token}")

settings_view = root / "LiveBuddy/Views/Settings/SettingsView.swift"
if settings_view.exists():
    text = settings_view.read_text()
    if text.count("SetupChecklistView()") < 2:
        errors.append("SettingsView and ProviderSetupSheet must render SetupChecklistView()")

menu_bar_view = root / "LiveBuddy/Views/MenuBar/MenuBarView.swift"
if menu_bar_view.exists():
    text = menu_bar_view.read_text()
    if "setupChecklist" not in text or "setupIncomplete" not in text:
        errors.append("MenuBarView must show setup incomplete state from setupChecklist")

settings_navigator_tests = root / "LiveBuddyTests/SystemSettingsNavigatorTests.swift"
if settings_navigator_tests.exists():
    text = settings_navigator_tests.read_text()
    if "import Foundation" not in text:
        errors.append("SystemSettingsNavigatorTests must import Foundation for URL.absoluteString")

app_settings_file = root / "LiveBuddy/Models/AppSettings.swift"
if app_settings_file.exists():
    text = app_settings_file.read_text()
    if "sourceLanguageCode" not in text:
        errors.append("AppSettings must persist optional sourceLanguageCode")
    if "glossaryEntries" not in text:
        errors.append("AppSettings must persist terminology glossary entries")
    if "func encode(to encoder: Encoder)" not in text:
        errors.append("AppSettings must define custom encode(to:) that omits apiKey")
    encode_body = text.split("func encode(to encoder: Encoder)", 1)[1].split("func requiresSessionRestart", 1)[0] if "func encode(to encoder: Encoder)" in text else ""
    if "forKey: .apiKey" in encode_body:
        errors.append("AppSettings.encode(to:) must not encode apiKey")

settings_view_file = root / "LiveBuddy/Views/Settings/SettingsView.swift"
if settings_view_file.exists():
    text = settings_view_file.read_text()
    if "apiKeyBinding()" not in text:
        errors.append("SettingsView must bind API key fields through apiKeyBinding()")
    if "binding(\\.apiKey)" in text:
        errors.append("SettingsView must not bind API key fields directly to AppSettings")
    if "subtitleDisplayMode" not in text:
        errors.append("SettingsView must expose subtitleDisplayMode picker")
    if "sourceLanguageCode" not in text or "translateFrom" not in text:
        errors.append("SettingsView must expose source language picker")
    if "terminologyGlossary" not in text or "addGlossaryEntry" not in text or "deleteGlossaryEntry" not in text:
        errors.append("SettingsView must expose terminology glossary editor")
    if "NavigationItem.test" not in text and "case test" not in text:
        errors.append("SettingsView must expose Test navigation item")
    if "preflightTestForm" not in text or "startPreflightTest" not in text:
        errors.append("SettingsView must expose preflight test form")
    if "DiagnosticIssueBanner" not in text or "currentDiagnosticIssue" not in text:
        errors.append("SettingsView must render diagnostic guidance banner")
    if "globalShortcutsEnabled" not in text or "ShortcutRecorderField" not in text or "resetAllGlobalShortcuts" not in text:
        errors.append("SettingsView must expose custom global shortcut recording and reset controls")

glossary_file = root / "LiveBuddy/Models/Glossary.swift"
if glossary_file.exists():
    text = glossary_file.read_text()
    for token in ["struct GlossaryEntry", "struct GlossaryPromptBuilder", "struct GlossaryEntryEditor"]:
        if token not in text:
            errors.append(f"Glossary.swift must include terminology glossary model {token}")
    for token in ["maxEntries", "isEnabled", "localizedCaseInsensitiveCompare"]:
        if token not in text:
            errors.append(f"Glossary.swift must keep glossary prompt lightweight and deterministic through {token}")

preflight_file = root / "LiveBuddy/Models/PreflightTest.swift"
if preflight_file.exists():
    text = preflight_file.read_text()
    for token in ["struct AudioLevelAnalyzer", "processPCM16", "retainedSampleCount", "summaryState"]:
        if token not in text:
            errors.append(f"PreflightTest.swift must include lightweight audio analysis through {token}")

preflight_runner_file = root / "LiveBuddy/Services/PreflightTestRunner.swift"
if preflight_runner_file.exists():
    text = preflight_runner_file.read_text()
    for token in ["struct PreflightTestRunner", "AudioLevelAnalyzer", "MicrophoneCapture", "ScreenAudioCapture"]:
        if token not in text:
            errors.append(f"PreflightTestRunner.swift missing {token}")
    if "GeminiLiveTranslateClient" in text:
        errors.append("PreflightTestRunner must not create a Gemini Live translation session")

subtitle_display_file = root / "LiveBuddy/Models/SubtitleDisplayMode.swift"
if subtitle_display_file.exists():
    text = subtitle_display_file.read_text()
    for token in ["enum SubtitleDisplayMode", "struct SubtitleDisplayLine", "struct SubtitleDisplayTextBuilder", "case bilingual"]:
        if token not in text:
            errors.append(f"SubtitleDisplayMode.swift missing {token}")

caption_view_file = root / "LiveBuddy/Views/Caption/CaptionView.swift"
if caption_view_file.exists():
    text = caption_view_file.read_text()
    if "CaptionScrollTextView(" not in text or "subtitleLines" not in text:
        errors.append("CaptionView must render appState.subtitleLines")

caption_scroll_file = root / "LiveBuddy/Views/Components/CaptionScrollTextView.swift"
if caption_scroll_file.exists():
    text = caption_scroll_file.read_text()
    if "SubtitleDisplayLine" not in text or "withAlphaComponent" not in text:
        errors.append("CaptionScrollTextView must render SubtitleDisplayLine roles with dimmed original styling")


global_shortcut_file = root / "LiveBuddy/Models/GlobalShortcut.swift"
if global_shortcut_file.exists():
    text = global_shortcut_file.read_text()
    for token in ["enum GlobalShortcutAction", "struct GlobalShortcut", "GlobalShortcutRegistrationResult", "toggleTranslation", "showCaptionWindow", "toggleMute"]:
        if token not in text:
            errors.append(f"GlobalShortcut.swift missing {token}")
    for token in ["struct GlobalShortcutSet", "struct GlobalShortcutValidator", "GlobalShortcutValidationResult", "defaultShortcut(for:"]:
        if token not in text:
            errors.append(f"GlobalShortcut.swift missing custom shortcut support {token}")

shortcut_recorder_file = root / "LiveBuddy/Views/Settings/ShortcutRecorderField.swift"
if not shortcut_recorder_file.exists():
    errors.append("missing ShortcutRecorderField.swift")
else:
    text = shortcut_recorder_file.read_text()
    for token in ["ShortcutRecorderField", "addLocalMonitorForEvents", "removeMonitor", "updateGlobalShortcut", "clearGlobalShortcut", "resetGlobalShortcut"]:
        if token not in text:
            errors.append(f"ShortcutRecorderField.swift missing {token}")
    if "CGEventTapCreate" in text:
        errors.append("Shortcut recorder must not create a global event tap")

carbon_registrar_file = root / "LiveBuddy/Services/CarbonGlobalShortcutRegistrar.swift"
if carbon_registrar_file.exists():
    text = carbon_registrar_file.read_text()
    for token in ["protocol GlobalShortcutRegistering", "RegisterEventHotKey", "UnregisterEventHotKey", "InstallEventHandler"]:
        if token not in text:
            errors.append(f"CarbonGlobalShortcutRegistrar.swift missing {token}")


transcript_export_file = root / "LiveBuddy/Models/TranscriptExport.swift"
if transcript_export_file.exists():
    text = transcript_export_file.read_text()
    for token in ["enum TranscriptExportFormat", "struct TranscriptExportCue", "struct TranscriptExporter", "func export(session:", "func defaultFileName"]:
        if token not in text:
            errors.append(f"TranscriptExport.swift missing {token}")

transcript_export_document_file = root / "LiveBuddy/Services/TranscriptExportDocument.swift"
if transcript_export_document_file.exists():
    text = transcript_export_document_file.read_text()
    for token in ["struct TranscriptExportDocument", "FileDocument", "fileWrapper", "readableContentTypes"]:
        if token not in text:
            errors.append(f"TranscriptExportDocument.swift missing {token}")



connection_recovery_file = root / "LiveBuddy/Models/ConnectionRecovery.swift"
if connection_recovery_file.exists():
    text = connection_recovery_file.read_text()
    for token in ["struct ConnectionRecoveryPolicy", "enum LiveConnectionEvent", "isRecoverable", "delay(forAttempt"]:
        if token not in text:
            errors.append(f"ConnectionRecovery.swift missing {token}")

transcripts_view_file = root / "LiveBuddy/Views/Settings/TranscriptsView.swift"
if transcripts_view_file.exists():
    text = transcripts_view_file.read_text()
    for token in ["fileExporter", "TranscriptExportDocument", "TranscriptExportFormat.allCases", "prepareExport"]:
        if token not in text:
            errors.append(f"TranscriptsView must expose transcript export through {token}")

menu_bar_file = root / "LiveBuddy/Views/MenuBar/MenuBarView.swift"
if menu_bar_file.exists():
    text = menu_bar_file.read_text()
    if "subtitleDisplayMode" not in text:
        errors.append("MenuBarView must expose subtitleDisplayMode picker")
    if "sourceLanguageCode" not in text or "translateFrom" not in text:
        errors.append("MenuBarView must expose source language picker")

readme_file = root / "README.md"
if readme_file.exists():
    text = readme_file.read_text().lower()
    if "setup checklist" not in text:
        errors.append("README must mention setup checklist")
    if "microphone permission" not in text or "screen recording permission" not in text:
        errors.append("README must mention microphone and screen recording permission checks")
    if "does not continuously poll" not in text and "no background polling" not in text:
        errors.append("README must document no continuous/background permission polling")

if errors:
    print("P0 onboarding verification failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("P0 onboarding verification passed")
