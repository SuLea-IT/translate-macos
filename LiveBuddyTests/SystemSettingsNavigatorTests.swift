import Foundation
import Testing
@testable import LiveBuddy

struct SystemSettingsNavigatorTests {
    @Test func microphoneSettingsURLTargetsPrivacyPane() {
        #expect(SystemSettingsDestination.microphone.url.absoluteString.contains("Privacy_Microphone"))
    }

    @Test func screenRecordingSettingsURLTargetsPrivacyPane() {
        #expect(SystemSettingsDestination.screenRecording.url.absoluteString.contains("Privacy_ScreenCapture"))
    }
}
