import SwiftUI

@main
struct LiveBuddyApp: App {
    @StateObject private var appState = AppState()
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate

    var body: some Scene {
        Window("Settings", id: "settings") {
            SettingsView()
                .environmentObject(appState)
                .frame(minWidth: 560, minHeight: 520)
                .onAppear {
                    appDelegate.configure(with: appState)
                }
        }
        .windowStyle(.hiddenTitleBar)
        .windowResizability(.contentSize)

        MenuBarExtra {
            MenuBarView()
                .environmentObject(appState)
        } label: {
            Label("LiveBuddy", systemImage: appState.isRunning ? "captions.bubble.fill" : "captions.bubble")
                .background(
                    OpenWindowActionInstaller()
                        .environmentObject(appState)
                        .frame(width: 0, height: 0)
                )
        }
        .menuBarExtraStyle(.window)
    }
}

private struct OpenWindowActionInstaller: View {
    @Environment(\.openWindow) private var openWindow
    @EnvironmentObject private var appState: AppState

    var body: some View {
        Color.clear
            .accessibilityHidden(true)
            .onAppear {
                appState.openWindowAction = openWindow
            }
    }
}

extension Notification.Name {
    static let showCaptionWindow = Notification.Name("LiveBuddyShowCaptionWindow")
}
