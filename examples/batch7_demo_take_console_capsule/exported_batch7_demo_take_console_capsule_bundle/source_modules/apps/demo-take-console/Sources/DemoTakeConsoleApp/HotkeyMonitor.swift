import AppKit

@MainActor
final class HotkeyMonitor {
    static let defaultKey: UInt16 = 46
    static let defaultModifiers: NSEvent.ModifierFlags = [.control, .option, .command]

    private var globalMonitor: Any?
    private var localMonitor: Any?
    private let onTrigger: () -> Void

    init(onTrigger: @escaping () -> Void) {
        self.onTrigger = onTrigger
    }

    func start() {
        stop()
        globalMonitor = NSEvent.addGlobalMonitorForEvents(matching: .keyDown) { [weak self] event in
            self?.handle(event: event, local: false)
        }
        localMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
            let consumed = self?.handle(event: event, local: true) ?? false
            return consumed ? nil : event
        }
    }

    func stop() {
        if let globalMonitor {
            NSEvent.removeMonitor(globalMonitor)
            self.globalMonitor = nil
        }
        if let localMonitor {
            NSEvent.removeMonitor(localMonitor)
            self.localMonitor = nil
        }
    }

    @discardableResult
    private func handle(event: NSEvent, local: Bool) -> Bool {
        let required = HotkeyMonitor.defaultModifiers
        let active = event.modifierFlags.intersection(.deviceIndependentFlagsMask)
        guard active.contains(required) else { return false }
        guard event.keyCode == HotkeyMonitor.defaultKey else { return false }
        onTrigger()
        return true
    }
}
