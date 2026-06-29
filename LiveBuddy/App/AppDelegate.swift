import AppKit

private enum TerminationStopResult {
    case stopped
    case timedOut
}

private final class TerminationStopGate: @unchecked Sendable {
    private let lock = NSLock()
    private var continuation: CheckedContinuation<TerminationStopResult, Never>?
    private var result: TerminationStopResult?

    func wait() async -> TerminationStopResult {
        await withCheckedContinuation { continuation in
            lock.lock()
            if let result {
                lock.unlock()
                continuation.resume(returning: result)
            } else {
                self.continuation = continuation
                lock.unlock()
            }
        }
    }

    func finish(_ result: TerminationStopResult) {
        var continuationToResume: CheckedContinuation<TerminationStopResult, Never>?
        lock.lock()
        if self.result == nil {
            self.result = result
            continuationToResume = continuation
            continuation = nil
        }
        lock.unlock()
        continuationToResume?.resume(returning: result)
    }
}

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    private static let terminationStopTimeoutNanoseconds: UInt64 = 5_000_000_000

    private var captionPanel: CaptionPanelController?
    private weak var appState: AppState?
    private var showCaptionObserver: NSObjectProtocol?
    private var terminationTask: Task<Void, Never>?
    private var terminationStopTask: Task<Void, Never>?
    private var terminationTimeoutTask: Task<Void, Never>?

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

        terminationTask = Task { @MainActor [weak self, appState] in
            guard let self else { return }
            _ = await self.waitForRuntimeStopBeforeTermination(appState)
            guard !Task.isCancelled else { return }
            self.terminationTask = nil
            NSApp.reply(toApplicationShouldTerminate: true)
        }
        return .terminateLater
    }

    func applicationWillTerminate(_ notification: Notification) {
        terminationTask?.cancel()
        terminationTask = nil
        clearTerminationStopTasks()
        removeShowCaptionObserver()
    }

    deinit {
        MainActor.assumeIsolated {
            terminationTask?.cancel()
            clearTerminationStopTasks()
            removeShowCaptionObserver()
        }
    }

    private func waitForRuntimeStopBeforeTermination(_ appState: AppState) async -> TerminationStopResult {
        clearTerminationStopTasks()
        let gate = TerminationStopGate()
        let timeout = Self.terminationStopTimeoutNanoseconds

        terminationStopTask = Task { @MainActor [weak appState, gate] in
            await appState?.stop()
            guard !Task.isCancelled else { return }
            gate.finish(.stopped)
        }

        terminationTimeoutTask = Task { [gate, timeout] in
            try? await Task.sleep(nanoseconds: timeout)
            guard !Task.isCancelled else { return }
            gate.finish(.timedOut)
        }

        let result = await gate.wait()
        clearTerminationStopTasks()
        return result
    }

    private func clearTerminationStopTasks() {
        terminationStopTask?.cancel()
        terminationStopTask = nil
        terminationTimeoutTask?.cancel()
        terminationTimeoutTask = nil
    }

    private func removeShowCaptionObserver() {
        if let showCaptionObserver {
            NotificationCenter.default.removeObserver(showCaptionObserver)
            self.showCaptionObserver = nil
        }
    }
}
