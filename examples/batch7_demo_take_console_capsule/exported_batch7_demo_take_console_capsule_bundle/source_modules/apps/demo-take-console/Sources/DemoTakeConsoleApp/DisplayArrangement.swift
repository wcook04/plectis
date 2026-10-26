import AppKit
import ScreenCaptureKit
import SwiftUI

// MARK: - Live display preview service
//
// View-owned, on-demand screen thumbnails via ScreenCaptureKit. The app already
// holds Screen Recording permission (FFmpeg avfoundation capture uses it), so a
// cheap periodic `SCScreenshotManager.captureImage` gives live-enough previews
// without touching RecorderStore's deliberately-disabled snapshot path. Keyed by
// CGDirectDisplayID so it lines up with `DisplayMetadata.displayID`. Degrades to a
// clean status string if permission is missing.

struct DisplayPreviewFrame: @unchecked Sendable {
    let id: UInt32
    let image: CGImage
}

@MainActor
final class DisplayPreviewService: ObservableObject {
    @Published private(set) var thumbnails: [UInt32: NSImage] = [:]
    @Published private(set) var status: String = ""
    @Published private(set) var isRefreshing = false
    @Published private(set) var lastRefreshed: Date?

    private var timer: Timer?
    private var inFlight = false
    private var pendingRefreshIDs: Set<UInt32>?
    private let captureProvider: @Sendable (Set<UInt32>) async -> [DisplayPreviewFrame]?

    init(captureProvider: @escaping @Sendable (Set<UInt32>) async -> [DisplayPreviewFrame]? = DisplayPreviewService.captureThumbnails(displayIDs:)) {
        self.captureProvider = captureProvider
    }

    func start(displayIDs: [UInt32]) {
        timer?.invalidate()
        timer = nil
    }

    func stop() {
        timer?.invalidate()
        timer = nil
    }

    func refresh(displayIDs: [UInt32]) {
        let ids = Set(displayIDs)
        guard !inFlight else {
            pendingRefreshIDs = ids
            if ids.isEmpty {
                thumbnails.removeAll()
                status = "No display snapshots available yet. Reload devices to refresh display previews."
                lastRefreshed = nil
            }
            return
        }
        guard !ids.isEmpty else {
            thumbnails.removeAll()
            status = "No display snapshots available yet. Reload devices to refresh display previews."
            lastRefreshed = nil
            isRefreshing = false
            return
        }
        guard HostEnvironment.screenRecordingAccessGranted() else {
            thumbnails.removeAll()
            status = "Snapshot preview paused until Screen Recording permission is granted. Use Settings/Recheck, then refresh."
            lastRefreshed = nil
            return
        }
        inFlight = true
        isRefreshing = true
        Task {
            let frames = await captureProvider(ids)
            if let frames {
                if frames.isEmpty {
                    thumbnails.removeAll()
                    status = "No display snapshots matched current displays. Reload devices, then refresh."
                    lastRefreshed = nil
                } else {
                    var next = thumbnails.filter { ids.contains($0.key) }
                    for box in frames {
                        next[box.id] = NSImage(cgImage: box.image, size: NSSize(width: box.image.width, height: box.image.height))
                    }
                    thumbnails = next
                    status = ""
                    lastRefreshed = Date()
                }
            } else {
                thumbnails.removeAll()
                status = "Live preview needs Screen Recording permission (System Settings ▸ Privacy & Security)."
                lastRefreshed = nil
            }
            inFlight = false
            isRefreshing = false
            if let pending = pendingRefreshIDs {
                pendingRefreshIDs = nil
                refresh(displayIDs: Array(pending))
            }
        }
    }

    // Runs off the main actor so non-Sendable ScreenCaptureKit types never get
    // sent across an actor boundary; only Sendable frames come back.
    nonisolated private static func captureThumbnails(displayIDs: Set<UInt32>) async -> [DisplayPreviewFrame]? {
        do {
            let content = try await SCShareableContent.current
            var frames: [DisplayPreviewFrame] = []
            for display in content.displays where displayIDs.contains(display.displayID) {
                let filter = RecipientOverlayCaptureExclusion.contentFilter(display: display, content: content)
                let config = SCStreamConfiguration()
                let targetWidth = 520
                config.width = targetWidth
                config.height = max(1, Int(Double(targetWidth) * Double(display.height) / Double(max(display.width, 1))))
                config.showsCursor = false
                let image = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: config)
                frames.append(DisplayPreviewFrame(id: display.displayID, image: image))
            }
            return frames
        } catch {
            return nil
        }
    }
}

// MARK: - Display arrangement map
//
// System-Settings-style spatial map of connected displays driven by real NSScreen
// geometry, with live thumbnails, count, click-to-select, identify, and refresh.

struct DisplayArrangementMap: View {
    @ObservedObject var store: RecorderStore
    @ObservedObject var preview: DisplayPreviewService

    private var screens: [CaptureDevice] {
        store.devices.videoDevices.filter(\.isScreen)
    }
    private func meta(_ device: CaptureDevice) -> DisplayMetadata {
        store.selectedScreenMetadata[device.id]
            ?? HostEnvironment.displayMetadata(forFFmpegScreenIndex: device.screenOrdinal)
    }
    private var displayIDs: [UInt32] {
        screens.compactMap { meta($0).displayID }
    }
    private var selectedCount: Int {
        store.selectedScreens.count
    }

    var body: some View {
        VStack(spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: "rectangle.3.group").font(.system(size: 12)).foregroundStyle(DTC.textSecondary)
                Text("\(screens.count) display\(screens.count == 1 ? "" : "s") connected")
                    .font(.system(size: 13, weight: .semibold)).foregroundStyle(DTC.textPrimary)
                if selectedCount > 0 {
                    Text("· \(selectedCount) selected").font(.system(size: 11)).foregroundStyle(DTC.success)
                }
                if preview.isRefreshing { ProgressView().controlSize(.small).scaleEffect(0.55).frame(width: 14) }
                Spacer()
                if let at = preview.lastRefreshed {
                    Text("snapshot \(at.formatted(date: .omitted, time: .standard))")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(DTC.textTertiary)
                        .help("When these one-shot display snapshots were taken")
                }
                Button { preview.refresh(displayIDs: displayIDs) } label: {
                    Label("Refresh", systemImage: "arrow.clockwise").font(.system(size: 11))
                }
                .buttonStyle(DTCButtonStyle(kind: .ghost))
                .help("Take a fresh one-shot snapshot of each display — no continuous capture runs")
            }

            GeometryReader { geo in
                if screens.isEmpty {
                    emptyState.frame(width: geo.size.width, height: geo.size.height)
                } else {
                    arrangement(in: geo.size)
                }
            }

            Text(hintText)
                .font(.system(size: 10))
                .foregroundStyle(preview.status.isEmpty ? DTC.textTertiary : DTC.attention)
                .multilineTextAlignment(.center)
                .frame(maxWidth: .infinity)
        }
        // One-shot snapshot on entry (and on every return from review) so the
        // map is current without any continuous capture load.
        .onAppear { preview.refresh(displayIDs: displayIDs) }
        .onDisappear { preview.stop() }
    }

    private var hintText: String {
        if !preview.status.isEmpty { return preview.status }
        return "Click a display to select it for recording — the green outline is captured. Previews are one-shot snapshots, not a live stream."
    }

    private var emptyState: some View {
        VStack(spacing: 8) {
            Image(systemName: "display.trianglebadge.exclamationmark").font(.system(size: 30)).foregroundStyle(DTC.textTertiary)
            Text("No displays detected").font(.system(size: 12)).foregroundStyle(DTC.textTertiary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    @ViewBuilder private func arrangement(in size: CGSize) -> some View {
        let bounded = screens.compactMap { device -> (CaptureDevice, DisplayBounds)? in
            guard let bounds = meta(device).bounds else { return nil }
            return (device, bounds)
        }
        if bounded.count == screens.count, !bounded.isEmpty {
            spatial(bounded, in: size)
        } else {
            HStack(spacing: 12) {
                ForEach(screens) { device in
                    MonitorCell(device: device, meta: meta(device), store: store, preview: preview, aspect: 16.0 / 10.0)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private func spatial(_ items: [(CaptureDevice, DisplayBounds)], in size: CGSize) -> some View {
        let minX = items.map { $0.1.x }.min() ?? 0
        let maxX = items.map { $0.1.x + $0.1.width }.max() ?? 1
        let minY = items.map { $0.1.y }.min() ?? 0
        let maxY = items.map { $0.1.y + $0.1.height }.max() ?? 1
        let spanW = max(maxX - minX, 1)
        let spanH = max(maxY - minY, 1)
        let pad: CGFloat = 14
        let availW = max(size.width - pad * 2, 1)
        let availH = max(size.height - pad * 2, 1)
        let scale = min(availW / spanW, availH / spanH)
        let drawW = spanW * scale
        let drawH = spanH * scale
        let offX = (size.width - drawW) / 2
        let offY = (size.height - drawH) / 2

        return ZStack(alignment: .topLeading) {
            ForEach(items, id: \.0.id) { item in
                let bounds = item.1
                let w = max(bounds.width * scale, 64)
                let h = max(bounds.height * scale, 42)
                let x = (bounds.x - minX) * scale + offX
                // NSScreen frames are bottom-origin; flip so the top display sits up top.
                let y = (maxY - (bounds.y + bounds.height)) * scale + offY
                MonitorCell(device: item.0, meta: meta(item.0), store: store, preview: preview, aspect: nil)
                    .frame(width: w, height: h)
                    .position(x: x + w / 2, y: y + h / 2)
            }
        }
        .frame(width: size.width, height: size.height)
    }
}

struct MonitorCell: View {
    let device: CaptureDevice
    let meta: DisplayMetadata
    @ObservedObject var store: RecorderStore
    @ObservedObject var preview: DisplayPreviewService
    var aspect: CGFloat?
    @State private var hover = false

    private var selected: Bool {
        store.selectedScreens.contains { $0.id == device.id }
    }
    private var thumb: NSImage? { meta.displayID.flatMap { preview.thumbnails[$0] } }

    var body: some View {
        Button { store.setScreen(device, enabled: !selected) } label: {
            ZStack {
                RoundedRectangle(cornerRadius: 8, style: .continuous).fill(Color.black)
                if let thumb {
                    // Unselected displays recede so the captured one reads as the hero.
                    Image(nsImage: thumb).resizable().scaledToFill()
                        .opacity(selected ? 1 : (hover ? 0.8 : 0.55))
                        .saturation(selected ? 1 : 0.7)
                } else {
                    Image(systemName: "display").font(.system(size: 22)).foregroundStyle(DTC.textTertiary)
                }
                VStack {
                    Spacer()
                    HStack(spacing: 4) {
                        if selected {
                            Image(systemName: "checkmark.circle.fill").foregroundStyle(DTC.success).font(.system(size: 11))
                        }
                        Text(meta.name).font(.system(size: 10, weight: .semibold)).lineLimit(1)
                            .foregroundStyle(selected ? .white : .white.opacity(0.75))
                        Spacer()
                        Text(meta.resolution).font(.system(size: 9, design: .monospaced)).foregroundStyle(.white.opacity(0.7))
                    }
                    .foregroundStyle(.white)
                    .padding(.horizontal, 6).padding(.vertical, 3)
                    .background(Color.black.opacity(0.55))
                }
            }
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .strokeBorder(selected ? DTC.success : (hover ? DTC.strokeHi : DTC.stroke), lineWidth: selected ? 2 : 1)
            )
            .shadow(color: selected ? DTC.success.opacity(0.22) : .clear, radius: 12)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .aspectRatio(aspect, contentMode: .fit)
        .onHover { hover = $0 }
        .overlay(alignment: .topTrailing) {
            if hover {
                Button { store.identifyDisplay(device) } label: {
                    Image(systemName: "dot.viewfinder").font(.system(size: 11)).foregroundStyle(.white)
                        .padding(5).background(Circle().fill(Color.black.opacity(0.55)))
                }
                .buttonStyle(.plain)
                .padding(5)
                .help("Flash a red border on this physical display")
            }
        }
    }
}
