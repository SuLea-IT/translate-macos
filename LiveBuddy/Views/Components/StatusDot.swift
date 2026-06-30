import SwiftUI

struct StatusDot: View {
    let level: LiveStatusLevel
    let interfaceLanguage: InterfaceLanguage

    var body: some View {
        Circle()
            .fill(color)
            .frame(width: 9, height: 9)
            .shadow(color: color.opacity(0.55), radius: 4)
            .help(helpText)
    }

    private var color: Color {
        switch level {
        case .running: .green
        case .connecting: .yellow
        case .error, .stopped: .red
        }
    }

    private var helpText: String {
        switch level {
        case .running: interfaceLanguage.localized(.statusRunning)
        case .connecting: interfaceLanguage.localized(.statusConnecting)
        case .error: interfaceLanguage.localized(.statusError)
        case .stopped: interfaceLanguage.localized(.statusStopped)
        }
    }
}
