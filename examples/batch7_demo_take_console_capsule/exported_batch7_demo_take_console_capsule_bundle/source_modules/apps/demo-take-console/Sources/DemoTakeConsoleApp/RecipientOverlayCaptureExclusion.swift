import AppKit
import CoreGraphics
import Foundation
@preconcurrency import ScreenCaptureKit

/// Single owner of the Demo Take Console capture-exclusion filter.
///
/// The recorder, the live preview, and the display snapshot each build their own
/// `SCContentFilter`.
///
/// The normal Demo Take Console window is a valid proof surface and must remain
/// visible in a recording when the operator leaves it on the captured display.
/// Private HUD/cue/identify overlays are the only app-owned windows excluded.
/// Current overlay windows are excluded through the shared ScreenCaptureKit filter;
/// newly-created overlay windows are also marked `sharingType = .none` at creation.
///
/// This proves visual omission only for artifacts produced by this app's capture
/// pipeline. It is not a universal-invisibility claim, and it does not assert the
/// sentinel has passed — that is a separate per-session proof.
enum RecipientOverlayCaptureExclusion {
    private static let publicWindowMinimumDimension: Double = 40

    /// Build a content filter for `display` that excludes private app overlay
    /// windows only. Normal visible layer-0 app windows remain capturable.
    static func contentFilter(
        display: SCDisplay,
        content: SCShareableContent,
        excludingWindows additionalExcludedWindows: [SCWindow] = []
    ) -> SCContentFilter {
        let excludedWindowIDs = overlayCaptureWindowIDs()
        let overlayWindows = content.windows.filter { window in
            excludedWindowIDs.contains(window.windowID)
        }
        return SCContentFilter(display: display, excludingWindows: additionalExcludedWindows + overlayWindows)
    }

    /// A baseline filter that excludes NOTHING on `display`. The sentinel captures
    /// through this to prove the magenta marker is actually detectable, so that an
    /// "absent through the production filter" result means EXCLUDED rather than
    /// merely "never rendered". Used only by the safety check — never the recorder.
    static func baselineFilter(display: SCDisplay) -> SCContentFilter {
        SCContentFilter(display: display, excludingWindows: [])
    }

    /// Mark an overlay window as private to capture. This protects panels created
    /// after a ScreenCaptureKit filter has already been built.
    @MainActor
    static func protectOverlayWindow(_ window: NSWindow) {
        window.sharingType = .none
    }

    /// Window ids for private app windows that must not appear in a demo take.
    /// Normal layer-0 app windows are deliberately excluded from this set.
    nonisolated static func overlayCaptureWindowIDs(
        rows: [[String: Any]]? = nil,
        ownerPID: pid_t = getpid()
    ) -> Set<CGWindowID> {
        let windowRows = captureWindowRows(rows)
        return Set(windowRows.compactMap { overlayCaptureWindowID(from: $0, ownerPID: ownerPID) })
    }

    nonisolated static func overlayCaptureWindowID(
        from row: [String: Any],
        ownerPID: pid_t = getpid()
    ) -> CGWindowID? {
        guard intValue(row[kCGWindowOwnerPID as String]) == Int(ownerPID) else { return nil }
        if let isOnscreen = boolValue(row[kCGWindowIsOnscreen as String]), !isOnscreen {
            return nil
        }
        guard (doubleValue(row[kCGWindowAlpha as String]) ?? 1) > 0.01 else { return nil }
        guard let number = uint32Value(row[kCGWindowNumber as String]) else { return nil }
        if publicCaptureWindowID(from: row, ownerPID: ownerPID) != nil {
            return nil
        }
        return CGWindowID(number)
    }

    /// Window ids for normal app windows that are allowed to remain visible in a
    /// demo take. Overlay/HUD panels sit on non-zero window layers, so they are
    /// excluded by `overlayCaptureWindowIDs`.
    nonisolated static func publicCaptureWindowIDs(
        rows: [[String: Any]]? = nil,
        ownerPID: pid_t = getpid()
    ) -> Set<CGWindowID> {
        let windowRows = captureWindowRows(rows)
        return Set(windowRows.compactMap { publicCaptureWindowID(from: $0, ownerPID: ownerPID) })
    }

    nonisolated static func publicCaptureWindowID(
        from row: [String: Any],
        ownerPID: pid_t = getpid()
    ) -> CGWindowID? {
        guard intValue(row[kCGWindowOwnerPID as String]) == Int(ownerPID) else { return nil }
        guard intValue(row[kCGWindowLayer as String]) == 0 else { return nil }
        if let isOnscreen = boolValue(row[kCGWindowIsOnscreen as String]), !isOnscreen {
            return nil
        }
        guard (doubleValue(row[kCGWindowAlpha as String]) ?? 1) > 0.01 else { return nil }
        guard let number = uint32Value(row[kCGWindowNumber as String]) else { return nil }
        guard let bounds = row[kCGWindowBounds as String] as? [String: Any] else { return nil }
        guard (doubleValue(bounds["Width"]) ?? 0) >= publicWindowMinimumDimension else { return nil }
        guard (doubleValue(bounds["Height"]) ?? 0) >= publicWindowMinimumDimension else { return nil }
        return CGWindowID(number)
    }

    private nonisolated static func captureWindowRows(_ rows: [[String: Any]]?) -> [[String: Any]] {
        if let rows {
            return rows
        }
        let options: CGWindowListOption = [.optionOnScreenOnly, .excludeDesktopElements]
        return CGWindowListCopyWindowInfo(options, kCGNullWindowID) as? [[String: Any]] ?? []
    }

    private nonisolated static func intValue(_ value: Any?) -> Int? {
        if let value = value as? Int { return value }
        if let value = value as? NSNumber { return value.intValue }
        return nil
    }

    private nonisolated static func uint32Value(_ value: Any?) -> UInt32? {
        if let value = value as? UInt32 { return value }
        if let value = value as? Int, value >= 0 { return UInt32(value) }
        if let value = value as? NSNumber { return value.uint32Value }
        return nil
    }

    private nonisolated static func doubleValue(_ value: Any?) -> Double? {
        if let value = value as? Double { return value }
        if let value = value as? CGFloat { return Double(value) }
        if let value = value as? NSNumber { return value.doubleValue }
        return nil
    }

    private nonisolated static func boolValue(_ value: Any?) -> Bool? {
        if let value = value as? Bool { return value }
        if let value = value as? NSNumber { return value.boolValue }
        return nil
    }
}
