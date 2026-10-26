import AppKit
import Combine
import SwiftUI

@MainActor
final class HudOverlayController {
    private var panel: NSPanel?
    private var cancellables: Set<AnyCancellable> = []
    private let store: RecorderStore

    init(store: RecorderStore) {
        self.store = store
        store.$hudExpanded
            .sink { [weak self] expanded in
                self?.resizePanel(expanded: expanded)
            }
            .store(in: &cancellables)
    }

    func show() {
        if panel == nil {
            buildPanel()
        }
        resizePanel(expanded: store.hudExpanded)
        panel?.setIsVisible(true)
        panel?.orderFrontRegardless()
    }

    func hide() {
        panel?.orderOut(nil)
    }

    private func buildPanel() {
        let size = Self.panelSize(expanded: store.hudExpanded)
        let hostingView = NSHostingView(rootView: HudOverlayView(store: store))
        hostingView.translatesAutoresizingMaskIntoConstraints = false
        hostingView.frame = NSRect(origin: .zero, size: size)

        let p = NSPanel(
            contentRect: NSRect(origin: .zero, size: size),
            styleMask: [.nonactivatingPanel, .titled, .fullSizeContentView, .hudWindow],
            backing: .buffered,
            defer: false
        )
        p.titlebarAppearsTransparent = true
        p.titleVisibility = .hidden
        p.isFloatingPanel = true
        p.level = .floating
        p.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary, .ignoresCycle]
        p.isMovableByWindowBackground = true
        p.hidesOnDeactivate = false
        p.becomesKeyOnlyIfNeeded = true
        p.hasShadow = true
        p.isOpaque = false
        p.backgroundColor = .clear
        p.standardWindowButton(.closeButton)?.isHidden = true
        p.standardWindowButton(.miniaturizeButton)?.isHidden = true
        p.standardWindowButton(.zoomButton)?.isHidden = true
        p.contentView = hostingView
        RecipientOverlayCaptureExclusion.protectOverlayWindow(p)

        if let screen = NSScreen.main {
            let frame = screen.visibleFrame
            p.setFrameOrigin(NSPoint(x: frame.maxX - size.width - 20, y: frame.maxY - size.height - 20))
        }
        panel = p
    }

    private func resizePanel(expanded: Bool) {
        guard let panel else { return }
        let previousTopRight = NSPoint(x: panel.frame.maxX, y: panel.frame.maxY)
        let size = Self.panelSize(expanded: expanded)
        panel.setContentSize(size)
        panel.contentView?.frame = NSRect(origin: .zero, size: size)
        panel.setFrameOrigin(NSPoint(x: previousTopRight.x - panel.frame.width, y: previousTopRight.y - panel.frame.height))
    }

    private static func panelSize(expanded: Bool) -> NSSize {
        expanded ? NSSize(width: 520, height: 96) : NSSize(width: 336, height: 56)
    }
}

struct HudOverlayView: View {
    @ObservedObject var store: RecorderStore

    var body: some View {
        Group {
            if store.hudExpanded {
                expandedBody
            } else {
                compactBody
            }
        }
        .padding(.horizontal, store.hudExpanded ? 14 : 10)
        .padding(.vertical, store.hudExpanded ? 10 : 8)
        .frame(
            width: store.hudExpanded ? 520 : 336,
            height: store.hudExpanded ? 96 : 56,
            alignment: .leading
        )
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(.regularMaterial)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(.white.opacity(0.08), lineWidth: 1)
        )
    }

    private var compactBody: some View {
        HStack(spacing: 10) {
            recordingDot
            Text(elapsedText)
                .font(.system(.body, design: .monospaced).weight(.semibold))
                .foregroundStyle(.primary)
                .frame(minWidth: 54, alignment: .leading)
            Text("\(store.markerCount)")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
                .help("\(store.markerCount) marker\(store.markerCount == 1 ? "" : "s")")

            Spacer(minLength: 6)
            hudButtons(iconSize: 24, includeLabels: false)
        }
    }

    private var expandedBody: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 14) {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 8) {
                        recordingDot
                        Text(elapsedText)
                            .font(.system(.title3, design: .monospaced).weight(.semibold))
                            .foregroundStyle(.primary)
                    }
                    Text("\(store.markerCount) marker\(store.markerCount == 1 ? "" : "s")")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Spacer(minLength: 8)
                hudButtons(iconSize: 32, includeLabels: true)
            }

            HudScheduleBlock(store: store)
        }
    }

    private var recordingDot: some View {
        Circle()
            .fill(store.captureIsWriting ? Color.red : Color.orange)
            .frame(width: 10, height: 10)
            .opacity(store.captureIsWriting ? recordingPulse : 0.85)
    }

    private func hudButtons(iconSize: CGFloat, includeLabels: Bool) -> some View {
        HStack(spacing: 6) {
            Button {
                store.toggleHudExpanded()
            } label: {
                Image(systemName: store.hudExpanded ? "arrow.down.right.and.arrow.up.left" : "arrow.up.left.and.arrow.down.right")
                    .frame(width: iconSize, height: 24)
            }
            .help(store.hudExpanded ? "Collapse HUD" : "Expand HUD")

            Button {
                store.togglePause()
            } label: {
                Image(systemName: store.state == .paused ? "play.fill" : "pause.fill")
                    .frame(width: iconSize, height: 24)
            }
            .help(store.state == .paused ? "Resume" : "Pause")
            .keyboardShortcut("p", modifiers: [.command])

            Button {
                store.markClip(source: .button)
            } label: {
                Image(systemName: "flag.fill")
                    .frame(width: iconSize, height: 24)
            }
            .help("Mark Clip (⌃⌥⌘M)")
            .keyboardShortcut("m", modifiers: [.command, .option])
            .disabled(!store.canMark)

            Button(role: .destructive) {
                Task { await store.stopRecording() }
            } label: {
                Image(systemName: "stop.fill")
                    .frame(width: iconSize, height: 24)
            }
            .help("Stop")
            .keyboardShortcut(".", modifiers: [.command])
        }
        .buttonStyle(.borderedProminent)
        .controlSize(includeLabels ? .small : .mini)
    }

    private var elapsedText: String {
        let whole = Int(store.elapsed)
        let minutes = whole / 60
        let seconds = whole % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }

    private var recordingPulse: Double {
        let phase = Date().timeIntervalSince1970.truncatingRemainder(dividingBy: 1.4)
        return 0.55 + 0.45 * abs(sin(phase * .pi))
    }
}

struct HudScheduleBlock: View {
    @ObservedObject var store: RecorderStore

    // Teleprompter prose intentionally removed from the recording HUD — Obsidian
    // is the operator's teleprompter. The HUD stays QuickTime-minimal.
    var body: some View {
        EmptyView()
    }

    @ViewBuilder private var legacyScheduleBody: some View {
        if let schedule = store.scheduleState {
            VStack(alignment: .leading, spacing: 5) {
                HStack(spacing: 8) {
                    Text(schedule.progressLabel)
                        .font(.caption.weight(.semibold))
                    Text(schedule.currentTitle ?? schedule.currentStepID ?? "Waiting for route")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                    Spacer()
                    if let next = schedule.nextTitle ?? schedule.nextStepID {
                        Text("Next: \(next)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }
                }

                if !schedule.currentFlashSay.isEmpty {
                    Text(schedule.currentFlashSay)
                        .font(.callout.weight(.semibold))
                        .lineLimit(2)
                } else if !schedule.operatorCue.isEmpty {
                    Text(schedule.operatorCue)
                        .font(.callout.weight(.semibold))
                        .lineLimit(2)
                }

                if !schedule.currentShortSay.isEmpty {
                    Text(schedule.currentShortSay)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }

                if !schedule.publicClaimBoundary.isEmpty {
                    Text("Boundary: \(schedule.publicClaimBoundary)")
                        .font(.caption2)
                        .foregroundStyle(.orange)
                        .lineLimit(2)
                }

                if !schedule.controls.isEmpty {
                    Text(schedule.controls.joined(separator: " / "))
                        .font(.system(.caption2, design: .monospaced))
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }
        } else {
            VStack(alignment: .leading, spacing: 5) {
                Text("Run map waiting")
                    .font(.caption.weight(.semibold))
                Text(store.scheduleStatus)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                Text("Start recording, then navigate FE routes to sync current_step → next_step.")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
        }
    }
}
