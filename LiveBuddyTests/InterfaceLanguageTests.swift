import Foundation
import Testing
@testable import LiveBuddy

struct InterfaceLanguageTests {
    @Test func supportsMultipleInterfaceLanguages() {
        let languages = InterfaceLanguage.allCases.map(\.rawValue)

        #expect(languages.contains("en"))
        #expect(languages.contains("zh-Hans"))
        #expect(languages.contains("ja"))
        #expect(languages.contains("ko"))
        #expect(languages.contains("es"))
        #expect(languages.contains("fr"))
        #expect(languages.contains("de"))
        #expect(languages.contains("vi"))
    }

    @Test func localizesCoreInterfaceLabels() {
        #expect(InterfaceLanguage.english.localized(.interfaceLanguage) == "Interface Language")
        #expect(InterfaceLanguage.simplifiedChinese.localized(.interfaceLanguage) == "界面语言")
        #expect(InterfaceLanguage.simplifiedChinese.localized(.settings) == "设置")
        #expect(InterfaceLanguage.japanese.localized(.start) == "開始")
    }

    @Test func localizesGlossaryImportSourceDetails() {
        for language in InterfaceLanguage.allCases {
            #expect(language.localized(.microsoftTerminologyDetail) != InterfaceText.microsoftTerminologyDetail.rawValue)
            #expect(language.localized(.iateExportSourceDetail) != InterfaceText.iateExportSourceDetail.rawValue)
            #expect(language.localized(.customGlossaryLinkDetail) != InterfaceText.customGlossaryLinkDetail.rawValue)
        }
        #expect(InterfaceLanguage.simplifiedChinese.localized(.microsoftTerminologyDetail).contains("下载"))
        #expect(InterfaceLanguage.vietnamese.localized(.iateExportSourceDetail).contains("TXT"))
    }

    @Test func localizesGlossaryEmptyStates() {
        #expect(InterfaceLanguage.english.localized(.glossaryEmptyStateTitle) == "No glossary terms yet")
        #expect(InterfaceLanguage.simplifiedChinese.localized(.glossaryEmptyStateTitle) == "还没有术语")
        #expect(InterfaceLanguage.simplifiedChinese.localized(.glossaryEmptyStateMessage).contains("导入你自己的术语文件"))
        #expect(InterfaceLanguage.simplifiedChinese.localized(.glossaryNoSearchResults, arguments: ["API"]) == "没有匹配“API”的术语")
    }

    @Test func legacySettingsDefaultToEnglishInterface() throws {
        let legacyJSON = #"{"activeProvider":"gemini","apiKey":"test-key","targetLanguageCode":"ja"}"#.data(using: .utf8)!

        let settings = try JSONDecoder().decode(AppSettings.self, from: legacyJSON)

        #expect(settings.interfaceLanguage == .english)
        #expect(settings.apiKey == "test-key")
        #expect(settings.targetLanguageCode == "ja")
    }


    @Test func legacySettingsDefaultToAutoSourceLanguage() throws {
        let legacyJSON = #"{"activeProvider":"gemini","apiKey":"test-key","targetLanguageCode":"ja"}"#.data(using: .utf8)!

        let settings = try JSONDecoder().decode(AppSettings.self, from: legacyJSON)

        #expect(settings.sourceLanguageCode == nil)
    }

    @Test func changingSourceLanguageRestartsTranslationSession() {
        let oldSettings = AppSettings()
        var newSettings = oldSettings

        newSettings.sourceLanguageCode = "ja"

        #expect(newSettings.requiresSessionRestart(comparedTo: oldSettings) == true)
    }

    @Test func changingInterfaceLanguageDoesNotRestartTranslationSession() {
        let oldSettings = AppSettings()
        var newSettings = oldSettings

        newSettings.interfaceLanguage = .simplifiedChinese

        #expect(newSettings.requiresSessionRestart(comparedTo: oldSettings) == false)
    }

    @Test func globalShortcutsDefaultToEnabledAndDoNotRestartTranslationSession() {
        let oldSettings = AppSettings()
        var newSettings = oldSettings

        #expect(oldSettings.globalShortcutsEnabled == true)
        newSettings.globalShortcutsEnabled = false

        #expect(newSettings.requiresSessionRestart(comparedTo: oldSettings) == false)
    }

    @Test func globalShortcutActionsHaveLocalizedTitles() {
        #expect(GlobalShortcutAction.toggleTranslation.localizedTitle(language: .english) == "Start / Stop translation")
        #expect(GlobalShortcutAction.showCaptionWindow.localizedTitle(language: .simplifiedChinese) == "显示字幕窗口")
        #expect(GlobalShortcutAction.toggleMute.localizedTitle(language: .japanese) == "翻訳音声をミュート / 解除")
    }

    @Test func encodedSettingsDoNotContainApiKey() throws {
        var settings = AppSettings()
        settings.apiKey = "secret-key"

        let data = try JSONEncoder().encode(settings)
        let json = String(decoding: data, as: UTF8.self)

        #expect(json.contains("secret-key") == false)
        #expect(json.contains("apiKey") == false)
    }
}
