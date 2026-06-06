import AppKit
import Carbon
import Foundation

@MainActor
final class GlobalHotKeyCenter: ObservableObject {
    var onTrigger: (() -> Void)?

    private var hotKeyRef: EventHotKeyRef?
    private var eventHandler: EventHandlerRef?

    init() {
        register()
    }

    private func register() {
        let hotKeyID = EventHotKeyID(signature: FourCharCode(0x5A_45_4E_54), id: 1)
        let modifiers = UInt32(cmdKey) | UInt32(shiftKey)
        RegisterEventHotKey(UInt32(kVK_Space), modifiers, hotKeyID, GetApplicationEventTarget(), 0, &hotKeyRef)

        var eventSpec = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        InstallEventHandler(
            GetApplicationEventTarget(),
            { _, _, userData in
                guard let userData else { return noErr }
                let center = Unmanaged<GlobalHotKeyCenter>.fromOpaque(userData).takeUnretainedValue()
                center.handleHotKey()
                return noErr
            },
            1,
            &eventSpec,
            UnsafeMutableRawPointer(Unmanaged.passUnretained(self).toOpaque()),
            &eventHandler
        )
    }

    private func handleHotKey() {
        NSApp.activate(ignoringOtherApps: true)
        onTrigger?()
    }
}
