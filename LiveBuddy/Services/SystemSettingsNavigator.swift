import AppKit
import Foundation

enum SystemSettingsDestination: Equatable {
    case microphone
    case screenRecording
    case privacy

    var url: URL {
        switch self {
        case .microphone:
            URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone")!
        case .screenRecording:
            URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture")!
        case .privacy:
            URL(string: "x-apple.systempreferences:com.apple.preference.security")!
        }
    }
}

protocol SystemSettingsOpening {
    @discardableResult
    func open(_ url: URL) -> Bool
}

extension NSWorkspace: SystemSettingsOpening {}

struct SystemSettingsNavigator {
    var opener: SystemSettingsOpening = NSWorkspace.shared

    @discardableResult
    func open(_ destination: SystemSettingsDestination) -> Bool {
        if opener.open(destination.url) {
            return true
        }
        return opener.open(SystemSettingsDestination.privacy.url)
    }
}
