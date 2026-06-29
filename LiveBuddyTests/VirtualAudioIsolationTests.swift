import Foundation
import Testing
@testable import LiveBuddy

struct VirtualAudioIsolationTests {
    @Test func legacySettingsDisableVirtualIsolationByDefault() throws {
        let legacyJSON = #"{"activeProvider":"gemini","targetLanguageCode":"ja"}"#.data(using: .utf8)!

        let settings = try JSONDecoder().decode(AppSettings.self, from: legacyJSON)

        #expect(settings.virtualAudioIsolationEnabled == false)
        #expect(settings.virtualAudioInputDeviceUID == nil)
        #expect(settings.translatedAudioOutputDeviceUID == nil)
    }

    @Test func virtualIsolationSettingsRoundTrip() throws {
        var settings = AppSettings()
        settings.virtualAudioIsolationEnabled = true
        settings.virtualAudioInputDeviceUID = "BlackHole_UID"
        settings.translatedAudioOutputDeviceUID = "BuiltInSpeaker_UID"

        let data = try JSONEncoder().encode(settings)
        let decoded = try JSONDecoder().decode(AppSettings.self, from: data)

        #expect(decoded.virtualAudioIsolationEnabled)
        #expect(decoded.virtualAudioInputDeviceUID == "BlackHole_UID")
        #expect(decoded.translatedAudioOutputDeviceUID == "BuiltInSpeaker_UID")
    }

    @Test func virtualInputSelectionPrefersExplicitUID() {
        let devices = [
            AudioDevice(deviceID: 1, uid: "BlackHole_UID", name: "BlackHole 2ch"),
            AudioDevice(deviceID: 2, uid: "Loopback_UID", name: "Loopback Audio")
        ]

        let selected = AudioDeviceManager.preferredVirtualInputDevice(from: devices, selectedUID: "Loopback_UID")

        #expect(selected?.uid == "Loopback_UID")
    }

    @Test func virtualInputSelectionFindsBlackHoleByName() {
        let devices = [
            AudioDevice(deviceID: 1, uid: "BuiltInMic", name: "MacBook Pro Microphone"),
            AudioDevice(deviceID: 2, uid: "BH2", name: "BlackHole 2ch")
        ]

        let selected = AudioDeviceManager.preferredVirtualInputDevice(from: devices, selectedUID: nil)

        #expect(selected?.uid == "BH2")
    }

    @Test func virtualInputSelectionReturnsNilWithoutLoopbackDevice() {
        let devices = [AudioDevice(deviceID: 1, uid: "BuiltInMic", name: "MacBook Pro Microphone")]

        let selected = AudioDeviceManager.preferredVirtualInputDevice(from: devices, selectedUID: nil)

        #expect(selected == nil)
    }
}
