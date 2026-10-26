import AppKit

@MainActor
enum DisplayIdentifyOverlay {
    private static var windows: [NSWindow] = []

    static func flash(ffmpegScreenIndex index: Int) -> Bool {
        guard let screen = HostEnvironment.screen(forFFmpegScreenIndex: index) else {
            return false
        }

        let window = NSWindow(
            contentRect: screen.frame,
            styleMask: [.borderless],
            backing: .buffered,
            defer: false,
            screen: screen
        )
        window.backgroundColor = .clear
        window.isOpaque = false
        window.hasShadow = false
        window.ignoresMouseEvents = true
        window.level = .screenSaver
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]
        window.contentView = DisplayIdentifyBorderView(frame: NSRect(origin: .zero, size: screen.frame.size))
        RecipientOverlayCaptureExclusion.protectOverlayWindow(window)
        window.orderFrontRegardless()
        windows.append(window)

        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            window.close()
            windows.removeAll { $0 === window }
        }
        return true
    }
}

final class DisplayIdentifyBorderView: NSView {
    override var isOpaque: Bool { false }

    override func draw(_ dirtyRect: NSRect) {
        super.draw(dirtyRect)
        NSColor.systemRed.setStroke()
        let inset: CGFloat = 10
        let path = NSBezierPath(rect: bounds.insetBy(dx: inset, dy: inset))
        path.lineWidth = 12
        path.stroke()
    }
}
