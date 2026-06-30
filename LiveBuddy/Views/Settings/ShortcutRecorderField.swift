import AppKit
import SwiftUI

struct ShortcutRecorderField: View {
    @EnvironmentObject private var appState: AppState
    let action: GlobalShortcutAction
    @Binding var recordingAction: GlobalShortcutAction?
    @State private var validationResult: GlobalShortcutValidationResult = .valid

    private var shortcut: GlobalShortcut? {
        appState.settings.globalShortcuts.shortcut(for: action)
    }

    private var isRecording: Bool {
        recordingAction == action
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 8) {
                Text(action.localizedTitle(language: appState.settings.interfaceLanguage))
                Spacer()
                Text(isRecording ? appState.t(.recordingShortcut) : (shortcut?.displayText ?? "—"))
                    .monospaced()
                    .foregroundStyle(isRecording ? Color.accentColor : Color.secondary)
                    .frame(minWidth: 96, alignment: .trailing)

                Button(appState.t(.recordShortcut)) {
                    validationResult = .valid
                    recordingAction = action
                }
                .controlSize(.small)

                Button(appState.t(.clearShortcut)) {
                    appState.clearGlobalShortcut(action)
                    validationResult = .valid
                }
                .controlSize(.small)

                Button(appState.t(.resetShortcut)) {
                    appState.resetGlobalShortcut(action)
                    validationResult = .valid
                }
                .controlSize(.small)
            }
            .background(
                ShortcutRecorderMonitor(isRecording: isRecordingBinding) { event in
                    handle(event)
                }
                .frame(width: 0, height: 0)
            )

            if validationResult != .valid {
                Text(message(for: validationResult))
                    .font(.caption)
                    .foregroundStyle(.red)
            }
        }
    }

    private var isRecordingBinding: Binding<Bool> {
        Binding(
            get: { recordingAction == action },
            set: { isRecording in
                if isRecording {
                    recordingAction = action
                } else if recordingAction == action {
                    recordingAction = nil
                }
            }
        )
    }

    private func handle(_ event: NSEvent) {
        if event.keyCode == 53 {
            recordingAction = nil
            return
        }
        if event.keyCode == 51 || event.keyCode == 117 {
            appState.clearGlobalShortcut(action)
            validationResult = .valid
            recordingAction = nil
            return
        }

        let shortcut = GlobalShortcut(
            action: action,
            keyCode: UInt32(event.keyCode),
            keyEquivalent: GlobalShortcut.keyEquivalent(forKeyCode: UInt32(event.keyCode), characters: event.charactersIgnoringModifiers),
            modifiers: ShortcutModifierSet(eventModifierFlags: event.modifierFlags)
        )
        validationResult = appState.updateGlobalShortcut(shortcut)
        if validationResult == .valid {
            recordingAction = nil
        }
    }

    private func message(for result: GlobalShortcutValidationResult) -> String {
        switch result {
        case .valid:
            ""
        case .duplicateLiveBuddyShortcut:
            appState.t(.shortcutDuplicate)
        case .emptyKey, .missingRequiredModifier, .systemConflict, .menuConflict:
            appState.t(.shortcutInvalid)
        }
    }
}

private struct ShortcutRecorderMonitor: NSViewRepresentable {
    @Binding var isRecording: Bool
    let onEvent: (NSEvent) -> Void

    func makeNSView(context: Context) -> NSView { NSView() }

    func updateNSView(_ nsView: NSView, context: Context) {
        context.coordinator.update(isRecording: isRecording, onEvent: onEvent)
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    final class Coordinator {
        private var monitor: Any?

        func update(isRecording: Bool, onEvent: @escaping (NSEvent) -> Void) {
            if isRecording, monitor == nil {
                monitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { event in
                    onEvent(event)
                    return nil
                }
            } else if !isRecording, let monitor {
                NSEvent.removeMonitor(monitor)
                self.monitor = nil
            }
        }

        deinit {
            if let monitor {
                NSEvent.removeMonitor(monitor)
            }
        }
    }
}
