import Foundation
import Testing
@testable import LiveBuddy

struct AppSettingsPersistenceTests {
    @Test func apiKeyChangeDoesNotRequireSettingsFileSave() {
        let oldSettings = AppSettings()
        var newSettings = oldSettings

        newSettings.apiKey = "secret-key"

        #expect(newSettings.requiresSettingsFileSave(comparedTo: oldSettings) == false)
    }

    @Test func persistedFieldChangeRequiresSettingsFileSave() {
        let oldSettings = AppSettings()
        var newSettings = oldSettings

        newSettings.targetLanguageCode = "ja"

        #expect(newSettings.requiresSettingsFileSave(comparedTo: oldSettings) == true)
    }

    @Test func encodedSettingsStillOmitApiKey() throws {
        var settings = AppSettings()
        settings.apiKey = "secret-key"

        let data = try JSONEncoder().encode(settings)
        let json = String(decoding: data, as: UTF8.self)

        #expect(json.contains("secret-key") == false)
        #expect(json.contains("apiKey") == false)
    }
}
