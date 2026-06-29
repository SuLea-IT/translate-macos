import Carbon.HIToolbox
import Foundation

protocol GlobalShortcutRegistering: AnyObject {
    func register(_ shortcuts: [GlobalShortcut], handler: @escaping (GlobalShortcutAction) -> Void) -> [GlobalShortcutRegistrationResult]
    func unregisterAll()
}

final class CarbonGlobalShortcutRegistrar: GlobalShortcutRegistering {
    private let signature = OSType(0x4C425548) // LBUH
    private var hotKeys: [UInt32: EventHotKeyRef] = [:]
    private var handler: ((GlobalShortcutAction) -> Void)?
    private var eventHandler: EventHandlerRef?

    func register(_ shortcuts: [GlobalShortcut], handler: @escaping (GlobalShortcutAction) -> Void) -> [GlobalShortcutRegistrationResult] {
        unregisterAll()
        guard !shortcuts.isEmpty else { return [] }
        self.handler = handler
        let handlerStatus = installHandlerIfNeeded()
        guard handlerStatus == noErr else {
            self.handler = nil
            return shortcuts.map { shortcut in
                GlobalShortcutRegistrationResult(shortcut: shortcut, status: .failed(Int32(handlerStatus)))
            }
        }

        return shortcuts.map { shortcut in
            var hotKeyRef: EventHotKeyRef?
            let hotKeyID = EventHotKeyID(signature: signature, id: shortcut.action.rawValue)
            let status = RegisterEventHotKey(
                shortcut.keyCode,
                carbonModifiers(from: shortcut.modifiers),
                hotKeyID,
                GetApplicationEventTarget(),
                0,
                &hotKeyRef
            )
            if status == noErr, let hotKeyRef {
                hotKeys[shortcut.action.rawValue] = hotKeyRef
                return GlobalShortcutRegistrationResult(shortcut: shortcut, status: .registered)
            }
            return GlobalShortcutRegistrationResult(shortcut: shortcut, status: .failed(Int32(status)))
        }
    }

    func unregisterAll() {
        for hotKey in hotKeys.values {
            UnregisterEventHotKey(hotKey)
        }
        hotKeys.removeAll()
        handler = nil
        if let eventHandler {
            RemoveEventHandler(eventHandler)
            self.eventHandler = nil
        }
    }

    deinit {
        unregisterAll()
    }

    private func installHandlerIfNeeded() -> OSStatus {
        guard eventHandler == nil else { return noErr }
        var eventSpec = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        let status = InstallEventHandler(
            GetApplicationEventTarget(),
            { _, event, userData in
                guard let event, let userData else { return noErr }
                var hotKeyID = EventHotKeyID()
                let status = GetEventParameter(
                    event,
                    EventParamName(kEventParamDirectObject),
                    EventParamType(typeEventHotKeyID),
                    nil,
                    MemoryLayout<EventHotKeyID>.size,
                    nil,
                    &hotKeyID
                )
                guard status == noErr else { return status }
                let registrar = Unmanaged<CarbonGlobalShortcutRegistrar>.fromOpaque(userData).takeUnretainedValue()
                registrar.handle(id: hotKeyID.id)
                return noErr
            },
            1,
            &eventSpec,
            Unmanaged.passUnretained(self).toOpaque(),
            &eventHandler
        )
        guard status == noErr else { return status }
        return noErr
    }

    private func handle(id: UInt32) {
        guard let action = GlobalShortcutAction(rawValue: id) else { return }
        DispatchQueue.main.async { [weak self] in
            self?.handler?(action)
        }
    }

    private func carbonModifiers(from modifiers: ShortcutModifierSet) -> UInt32 {
        var flags: UInt32 = 0
        if modifiers.contains(.control) { flags |= UInt32(controlKey) }
        if modifiers.contains(.option) { flags |= UInt32(optionKey) }
        if modifiers.contains(.command) { flags |= UInt32(cmdKey) }
        if modifiers.contains(.shift) { flags |= UInt32(shiftKey) }
        return flags
    }
}
