import AppKit
import CoreGraphics
@preconcurrency import ScreenCaptureKit

// MARK: - Exclusion sentinel (contract §4 — THE gate, not a nicety)
//
// Capture exclusion must be PROVEN per session, not asserted by the window.
// Before enabling the overlay for a production take:
//   1. Render a high-contrast synthetic sentinel inside every cue panel.
//   2. Capture a frame through the EXACT production filter (and the preview +
//      snapshot filter paths) — all three sites share
//      RecipientOverlayCaptureExclusion.contentFilter, so capturing through that
//      filter via SCScreenshotManager faithfully proves the recorder filter too.
//   3. Assert the sentinel pixels are absent in every captured path.
//   4. Bind the receipt to the current panel set, display topology, filter
//      generation, app build, and deck hash; write it to the overlay sidecar.
//   5. Enable the overlay during production only while that receipt is current.
//
// A pass binds to the exact tuple; any change (topology, panel set, filter
// generation, recording config) invalidates it.

/// Result of one capture-path probe.
struct SentinelPathResult: Codable, Equatable {
    /// "production_filter" (must be clean) | "baseline_unfiltered" (must detect).
    var pathID: String
    var displayID: UInt32
    /// true == sentinel pixels were NOT found (the literal cleanliness reading).
    var clean: Bool
    /// max fraction of bright sentinel-colored pixels found (0 == perfectly clean).
    var sentinelPixelFraction: Double
    var note: String?
    /// Probe role. "exclusion" asserts the marker is ABSENT through the production
    /// filter; "baseline" asserts it is PRESENT without exclusion, so an exclusion
    /// pass is non-vacuous. Defaulted for receipt back-compatibility.
    var kind: String = "exclusion"
    /// Per-row verdict under the baseline-guarded logic. Defaulted (nil) so older
    /// receipts still decode.
    var pass: Bool? = nil
}

/// The per-session receipt. A pass enables the overlay for production.
struct ExclusionPreflightReceipt: Codable, Equatable {
    var schema: String = "exclusion_preflight_receipt_v0"
    var generatedAt: Date
    var passed: Bool
    var appBuildID: String
    var captureFilterGeneration: String
    var displayTopology: [UInt32]
    var overlayWindowNumbers: [Int]
    var deckSourceHash: String?
    var pathResults: [SentinelPathResult]
    var staleReason: String?

    enum CodingKeys: String, CodingKey {
        case schema
        case generatedAt = "generated_at"
        case passed
        case appBuildID = "app_build_id"
        case captureFilterGeneration = "capture_filter_generation"
        case displayTopology = "display_topology"
        case overlayWindowNumbers = "overlay_window_numbers"
        case deckSourceHash = "deck_source_hash"
        case pathResults = "path_results"
        case staleReason = "stale_reason"
    }
}

@MainActor
final class ExclusionSentinel {
    private struct WindowSharingSnapshot {
        weak var window: NSWindow?
        var sharingType: NSWindow.SharingType
    }

    private let session: OverlaySession
    private let panelManager: CueOverlayPanelManager

    /// The bright magenta sentinel color rendered into the panels and searched for
    /// in the captured frames. Deliberately unlike any normal desktop content.
    static let sentinelColor = NSColor(calibratedRed: 1.0, green: 0.0, blue: 1.0, alpha: 1.0)

    init(session: OverlaySession, panelManager: CueOverlayPanelManager) {
        self.session = session
        self.panelManager = panelManager
    }

    /// Run the full safety check. Renders the sentinel, captures through every
    /// shared-filter path, asserts absence, and returns the receipt. On pass it
    /// sets `session.exclusionReceiptCurrent = true`.
    func runSafetyCheck() async -> ExclusionPreflightReceipt {
        let topology = panelManager.activeDisplayIDs
        let windowNumbers = panelManager.overlayWindows.map(\.windowNumber)
        let publicWindowNumbers = RecipientOverlayCaptureExclusion.publicCaptureWindowIDs()
        let filterGeneration = Self.filterGeneration(
            topology: topology,
            windows: windowNumbers,
            publicWindows: Array(publicWindowNumbers)
        )

        // Force the full sheet visible (so a leak, if any, would be present and
        // would be caught), regardless of the prior state, then render the
        // sentinel into every cue sheet. Restore the prior state afterwards.
        let priorState = session.interactionState
        session.interactionState = .readThrough
        SentinelOverlayRenderer.shared.activate()
        panelManager.refresh()
        let sharingSnapshots = Self.makeOverlayWindowsProbeCaptureVisible(panelManager.overlayWindows)
        defer { Self.restoreOverlayWindowSharing(sharingSnapshots) }

        // Let the windows actually composite before capturing.
        try? await Task.sleep(nanoseconds: 350_000_000)

        var results: [SentinelPathResult] = []
        for displayID in topology {
            // BASELINE: capture with nothing excluded and require the marker to be
            // present. This proves the probe can actually see a leak, so an
            // "absent through the production filter" reading below means EXCLUDED,
            // not "the sentinel never rendered". Without it the check is vacuous.
            let baseline = await Self.captureFraction(displayID: displayID, exclude: false)
            results.append(Self.baselineResult(displayID: displayID, capture: baseline))
            // PRODUCTION: capture through the exact filter the recorder, preview, and
            // snapshot all share (RecipientOverlayCaptureExclusion.contentFilter) and
            // require the marker to be absent.
            let production = await Self.captureFraction(displayID: displayID, exclude: true)
            results.append(Self.productionResult(displayID: displayID, capture: production))
        }

        SentinelOverlayRenderer.shared.deactivate()
        session.interactionState = priorState
        panelManager.refresh()

        let (passed, staleReason) = Self.verdict(results: results, topology: topology)
        let receipt = ExclusionPreflightReceipt(
            generatedAt: Date(),
            passed: passed,
            appBuildID: Self.appBuildID,
            captureFilterGeneration: filterGeneration,
            displayTopology: topology,
            overlayWindowNumbers: windowNumbers,
            deckSourceHash: session.loadedDeckSourceHash,
            pathResults: results,
            staleReason: staleReason
        )
        session.exclusionReceiptCurrent = passed
        return receipt
    }

    /// Overlay panels normally use `sharingType = .none`, which is correct for
    /// production but would make the baseline probe vacuous. During the proof,
    /// make them capture-visible so baseline can see the marker and production
    /// has to prove the ScreenCaptureKit exclusion filter removes it.
    private static func makeOverlayWindowsProbeCaptureVisible(_ windows: [NSWindow]) -> [WindowSharingSnapshot] {
        windows.map { window in
            let snapshot = WindowSharingSnapshot(window: window, sharingType: window.sharingType)
            window.sharingType = .readOnly
            return snapshot
        }
    }

    private static func restoreOverlayWindowSharing(_ snapshots: [WindowSharingSnapshot]) {
        for snapshot in snapshots {
            snapshot.window?.sharingType = snapshot.sharingType
        }
    }

    // MARK: - Capture + analysis

    /// A production capture is "clean" when essentially no sentinel pixels remain.
    nonisolated static let cleanCeiling = 0.0005
    /// A baseline capture must contain at least this fraction of sentinel pixels, or
    /// the marker never rendered and the whole check would be vacuous → fail closed.
    /// The sentinel band fills the cue sheet, so a real baseline is far above this.
    nonisolated static let baselineFloor = 0.01

    /// Capture the sentinel-pixel fraction for `displayID`, either through the shared
    /// production exclusion filter (`exclude: true`) or a baseline filter that
    /// excludes nothing (`exclude: false`). Failures fail closed: a missing
    /// production capture reads as fully dirty (1.0), a missing baseline as
    /// undetected (0.0).
    nonisolated private static func captureFraction(
        displayID: CGDirectDisplayID,
        exclude: Bool
    ) async -> (fraction: Double, note: String?) {
        do {
            let content = try await SCShareableContent.current
            guard let display = content.displays.first(where: { $0.displayID == displayID }) else {
                return (exclude ? 1.0 : 0.0, "display_not_in_shareable_content")
            }
            let filter = exclude
                ? RecipientOverlayCaptureExclusion.contentFilter(display: display, content: content)
                : RecipientOverlayCaptureExclusion.baselineFilter(display: display)
            let config = SCStreamConfiguration()
            config.width = 480
            config.height = max(1, Int(480.0 * Double(display.height) / Double(max(display.width, 1))))
            config.showsCursor = false
            let image = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: config)
            return (sentinelPixelFraction(in: image), nil)
        } catch {
            return (exclude ? 1.0 : 0.0, "capture_failed: \(error.localizedDescription)")
        }
    }

    /// Pure verdict over the probe results: a pass requires a non-empty topology and
    /// every probe to pass — each baseline detected the marker AND each production
    /// capture was clean. Extracted (and `internal`) so the safety logic is unit
    /// testable without a live capture.
    nonisolated static func verdict(
        results: [SentinelPathResult],
        topology: [CGDirectDisplayID]
    ) -> (passed: Bool, staleReason: String?) {
        guard !topology.isEmpty else { return (false, "no_displays_to_probe") }
        let passed = !results.isEmpty && results.allSatisfy { $0.pass == true }
        if passed { return (true, nil) }
        let baselineFailed = results.contains { $0.kind == "baseline" && $0.pass != true }
        return (false, baselineFailed ? "sentinel_not_detectable_baseline" : "sentinel_pixels_present_in_capture")
    }

    /// Production probe: passes when the marker is absent through the exclusion filter.
    nonisolated static func productionResult(
        displayID: CGDirectDisplayID,
        capture: (fraction: Double, note: String?)
    ) -> SentinelPathResult {
        let clean = capture.note == nil && capture.fraction < cleanCeiling
        return SentinelPathResult(
            pathID: "production_filter", displayID: displayID, clean: clean,
            sentinelPixelFraction: capture.fraction,
            note: capture.note ?? (clean ? nil : "sentinel_pixels_present_in_capture"),
            kind: "exclusion", pass: clean
        )
    }

    /// Baseline probe: passes when the marker IS detected without exclusion, proving
    /// the production probe could have caught a leak.
    nonisolated static func baselineResult(
        displayID: CGDirectDisplayID,
        capture: (fraction: Double, note: String?)
    ) -> SentinelPathResult {
        let detected = capture.note == nil && capture.fraction >= baselineFloor
        return SentinelPathResult(
            pathID: "baseline_unfiltered", displayID: displayID,
            clean: capture.fraction < cleanCeiling,
            sentinelPixelFraction: capture.fraction,
            note: capture.note ?? (detected ? nil : "sentinel_not_detectable_in_baseline"),
            kind: "baseline", pass: detected
        )
    }

    /// Fraction of pixels matching the bright-magenta sentinel hue.
    nonisolated private static func sentinelPixelFraction(in cgImage: CGImage) -> Double {
        let width = cgImage.width
        let height = cgImage.height
        guard width > 0, height > 0 else { return 1.0 }
        let bytesPerPixel = 4
        let bytesPerRow = width * bytesPerPixel
        var buffer = [UInt8](repeating: 0, count: height * bytesPerRow)
        guard let colorSpace = CGColorSpace(name: CGColorSpace.sRGB),
              let ctx = CGContext(
                data: &buffer,
                width: width, height: height,
                bitsPerComponent: 8, bytesPerRow: bytesPerRow,
                space: colorSpace,
                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
              )
        else { return 1.0 }
        ctx.draw(cgImage, in: CGRect(x: 0, y: 0, width: width, height: height))

        var hits = 0
        let total = width * height
        var i = 0
        while i < buffer.count {
            let r = Int(buffer[i])
            let g = Int(buffer[i + 1])
            let b = Int(buffer[i + 2])
            // bright magenta: high R, low G, high B
            if r > 200, g < 70, b > 200 { hits += 1 }
            i += bytesPerPixel
        }
        return total > 0 ? Double(hits) / Double(total) : 1.0
    }

    // MARK: - Identity helpers

    static var appBuildID: String {
        let info = Bundle.main.infoDictionary
        let version = info?["CFBundleShortVersionString"] as? String ?? "dev"
        let build = info?["CFBundleVersion"] as? String ?? "0"
        return "\(Bundle.main.bundleIdentifier ?? "demo-take-console")@\(version)+\(build)"
    }

    nonisolated static func filterGeneration(
        topology: [CGDirectDisplayID],
        windows: [Int],
        publicWindows: [CGWindowID] = Array(RecipientOverlayCaptureExclusion.publicCaptureWindowIDs())
    ) -> String {
        let t = topology.sorted().map(String.init).joined(separator: ",")
        let w = windows.sorted().map(String.init).joined(separator: ",")
        let p = publicWindows.sorted().map(String.init).joined(separator: ",")
        return "topo[\(t)]/overlay[\(w)]/public[\(p)]"
    }
}

// MARK: - Sentinel overlay renderer
//
// A process-wide flag the cue sheet panels read to paint an unmistakable
// high-contrast sentinel band over their content during a safety check.

@MainActor
final class SentinelOverlayRenderer: ObservableObject {
    static let shared = SentinelOverlayRenderer()
    @Published private(set) var active = false
    private init() {}
    func activate() { active = true }
    func deactivate() { active = false }
}
