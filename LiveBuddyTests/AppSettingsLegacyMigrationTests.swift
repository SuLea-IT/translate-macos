import Foundation
import Testing
@testable import LiveBuddy

struct AppSettingsLegacyMigrationTests {
    @Test func removedVirtualAudioSettingsDecodeButDoNotEncode() throws {
        let legacyJSON = #"{"activeProvider":"gemini","targetLanguageCode":"ja","virtualAudioIsolationEnabled":true,"virtualAudioInputDeviceUID":"LegacyVirtualInput_UID","translatedAudioOutputDeviceUID":"LegacyOutput_UID"}"#.data(using: .utf8)!

        let decoded = try JSONDecoder().decode(AppSettings.self, from: legacyJSON)
        let encoded = try JSONEncoder().encode(decoded)
        let encodedString = try #require(String(data: encoded, encoding: .utf8))

        #expect(!encodedString.contains("virtualAudioIsolationEnabled"))
        #expect(!encodedString.contains("virtualAudioInputDeviceUID"))
        #expect(!encodedString.contains("translatedAudioOutputDeviceUID"))
    }
}
