import AppKit

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var captionPanel: CaptionPanelController?
    private weak var appState: AppState?
    private var showCaptionObserver: NSObjectProtocol?
    private var terminationTask: Task<Void, Never>?

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
    }

    func configure(with appState: AppState) {
        guard self.appState !== appState else { return }
        removeShowCaptionObserver()
        self.appState = appState
        let panel = CaptionPanelController(appState: appState)
        captionPanel = panel
        if appState.isProviderConfigured {
            panel.show()
        } else {
            appState.openSettingsWindow()
            appState.showSetupSheet = true
        }
        showCaptionObserver = NotificationCenter.default.addObserver(
            forName: .showCaptionWindow,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor [weak self] in
                if self?.appState?.isProviderConfigured == true {
                    self?.captionPanel?.show()
                } else {
                    self?.appState?.openSettingsWindow()
                    self?.appState?.showSetupSheet = true
                }
            }
        }
    }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        guard terminationTask == nil else { return .terminateLater }
        guard let appState else {
            removeShowCaptionObserver()
            return .terminateNow
        }

        terminationTask = Task { @MainActor [weak self, weak appState] in
            await appState?.stop()
            guard !Task.isCancelled else { return }
            self?.terminationTask = nil
            NSApp.reply(toApplicationShouldTerminate: true)
        }
        return .terminateLater
    }

    func applicationWillTerminate(_ notification: Notification) {
        removeShowCaptionObserver()
    }

    deinit {
        MainActor.assumeIsolated {
            terminationTask?.cancel()
            removeShowCaptionObserver()
        }
    }

    private func removeShowCaptionObserver() {
        if let showCaptionObserver {
            NotificationCenter.default.removeObserver(showCaptionObserver)
            self.showCaptionObserver = nil
        }
    }
}
