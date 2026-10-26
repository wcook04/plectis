import AppKit
import ApplicationServices
import CoreGraphics
import Foundation

struct RecordedScreenAttentionStatus: Sendable {
    let line: String
    let detail: String
}

@MainActor
final class RecordedScreenAttentionMonitor {
    private let interval: TimeInterval
    private let heartbeatInterval: TimeInterval
    private let debounceInterval: TimeInterval
    private let statusHandler: @MainActor (RecordedScreenAttentionStatus) -> Void
    private var timer: Timer?
    private var outputURL: URL?
    private var startedAt: Date?
    private var pausedAt: Date?
    private var pausedDuration: TimeInterval = 0
    private var selectedScreen: CaptureDevice?
    private var displayMetadata: DisplayMetadata?
    private var eventCount = 0
    private var lastSignature: AttentionSignature?
    private var pendingSample: PendingAttentionSample?
    private var lastEmittedAt: Date?

    init(
        interval: TimeInterval = 0.2,
        heartbeatInterval: TimeInterval = 2.0,
        debounceInterval: TimeInterval = 0.35,
        statusHandler: @escaping @MainActor (RecordedScreenAttentionStatus) -> Void
    ) {
        self.interval = interval
        self.heartbeatInterval = heartbeatInterval
        self.debounceInterval = debounceInterval
        self.statusHandler = statusHandler
    }

    func start(takeURL: URL, screen: CaptureDevice?) {
        stop()
        selectedScreen = screen
        displayMetadata = screen.map { HostEnvironment.displayMetadata(forFFmpegScreenIndex: $0.screenOrdinal) }
        outputURL = takeURL.appendingPathComponent("attention_events.jsonl")
        startedAt = Date()
        pausedAt = nil
        pausedDuration = 0
        eventCount = 0
        lastSignature = nil
        pendingSample = nil
        lastEmittedAt = nil
        FileManager.default.createFile(atPath: outputURL?.path ?? "", contents: nil)
        sample(force: true, reason: "start")
        schedule()
        emitStatus("Attention telemetry writing", detail: displayMetadata?.summary ?? "No selected display")
    }

    func pause() {
        guard timer != nil else { return }
        sample(force: true, reason: "pause")
        pausedAt = Date()
        timer?.invalidate()
        timer = nil
        emitStatus("Attention telemetry paused", detail: "\(eventCount) event(s) captured")
    }

    func resume() {
        if let pausedAt {
            pausedDuration += Date().timeIntervalSince(pausedAt)
        }
        pausedAt = nil
        sample(force: true, reason: "resume")
        schedule()
        emitStatus("Attention telemetry writing", detail: "\(eventCount) event(s) captured")
    }

    func stop() {
        timer?.invalidate()
        timer = nil
        if outputURL != nil {
            sample(force: true, reason: "stop")
        }
        emitStatus(eventCount > 0 ? "Attention telemetry saved" : "Attention telemetry idle", detail: "\(eventCount) event(s) captured")
        outputURL = nil
        startedAt = nil
        pausedAt = nil
        selectedScreen = nil
        displayMetadata = nil
        pausedDuration = 0
        lastSignature = nil
        pendingSample = nil
        lastEmittedAt = nil
    }

    private func schedule() {
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.sample()
            }
        }
    }

    private func sample(force: Bool = false, reason: String = "sample") {
        guard let outputURL, let startedAt else { return }
        let now = Date()
        let current = makeSample(now: now, startedAt: startedAt, reason: reason)
        if force || eventCount == 0 {
            append(current, to: outputURL)
            pendingSample = nil
            return
        }
        if current.signature != lastSignature {
            if pendingSample?.signature != current.signature {
                pendingSample = PendingAttentionSample(sample: current, firstSeenAt: now)
                return
            }
            if let pendingSample, now.timeIntervalSince(pendingSample.firstSeenAt) >= debounceInterval {
                append(pendingSample.sample, to: outputURL)
                self.pendingSample = nil
            }
            return
        }
        pendingSample = nil
        if let lastEmittedAt, now.timeIntervalSince(lastEmittedAt) >= heartbeatInterval {
            append(makeSample(now: now, startedAt: startedAt, reason: "heartbeat"), to: outputURL)
        }
    }

    private func makeSample(now: Date, startedAt: Date, reason: String) -> AttentionSample {
        let videoT = max(0, now.timeIntervalSince(startedAt) - pausedDuration)
        let frontmost = NSWorkspace.shared.frontmostApplication
        let window = bestWindow(for: frontmost, targetBounds: displayMetadata?.bounds?.cgRect)
        let overlap = window?.overlap ?? 0
        let stationTitle = publicStationTitle(window?.title)
        let displayID = displayMetadata?.displayID.map(String.init)
        let frontmostPayload: [String: Any] = [
            "localized_name": frontmost?.localizedName ?? "Unknown",
            "bundle_identifier": frontmost?.bundleIdentifier ?? "",
            "process_identifier": frontmost.map { Int($0.processIdentifier) } ?? NSNull(),
        ]
        let windowPayload: [String: Any] = [
            "window_id": window?.windowID ?? NSNull(),
            "owner_name": window?.ownerName ?? NSNull(),
            "owner_pid": window?.ownerPID ?? NSNull(),
            "public_safe_title": stationTitle ?? NSNull(),
            "recorded_display_overlap": overlap,
            "bounds": window?.bounds.dictionary ?? NSNull(),
        ]
        let accessibilityPayload: [String: Any] = [
            "trusted": AXIsProcessTrusted(),
        ]
        let event: [String: Any] = [
            "schema": "demo_take_attention_event_v0",
            "source": "macos_attention_monitor",
            "event_kind": reason,
            "at_iso": Self.isoString(now),
            "video_t_seconds": round(videoT * 1000) / 1000,
            "wall_t_seconds": round(now.timeIntervalSince(startedAt) * 1000) / 1000,
            "monotonic_seconds": ProcessInfo.processInfo.systemUptime,
            "capture_target_id": displayID.map { "display:\($0)" } ?? NSNull(),
            "display_id": displayID ?? NSNull(),
            "display_bounds": displayMetadata?.bounds?.dictionary ?? NSNull(),
            "is_on_recorded_display": overlap > 0,
            "confidence": overlap > 0 ? "recorded_display_window" : "frontmost_app_only",
            "public_safe_label": stationTitle ?? frontmost?.localizedName ?? "Unknown app",
            "accessibility": accessibilityPayload,
            "frontmost_app": frontmostPayload,
            "window": windowPayload,
        ]
        let signature = AttentionSignature(
            bundleIdentifier: frontmost?.bundleIdentifier ?? "",
            localizedName: frontmost?.localizedName ?? "Unknown",
            windowID: window?.windowID,
            publicSafeTitle: stationTitle,
            overlapBucket: Int((overlap * 100).rounded()),
            isOnRecordedDisplay: overlap > 0
        )
        return AttentionSample(event: event, signature: signature, label: stationTitle ?? frontmost?.localizedName ?? "Unknown app", at: now)
    }

    private func append(_ sample: AttentionSample, to url: URL) {
        append(sample.event, to: url)
        eventCount += 1
        lastSignature = sample.signature
        lastEmittedAt = sample.at
        emitStatus("Attention telemetry writing", detail: "\(eventCount) event(s) · \(sample.label)")
    }

    private func bestWindow(for app: NSRunningApplication?, targetBounds: CGRect?) -> WindowCandidate? {
        let options: CGWindowListOption = [.optionOnScreenOnly, .excludeDesktopElements]
        guard let rows = CGWindowListCopyWindowInfo(options, kCGNullWindowID) as? [[String: Any]] else {
            return nil
        }
        let appPID = app?.processIdentifier
        var candidates: [WindowCandidate] = []
        for row in rows {
            let layer = row[kCGWindowLayer as String] as? Int ?? 0
            guard layer == 0 else { continue }
            let ownerPID = row[kCGWindowOwnerPID as String] as? Int32
            if let appPID, let ownerPID, ownerPID != appPID {
                continue
            }
            guard let bounds = Self.windowBounds(from: row), bounds.width > 40, bounds.height > 40 else {
                continue
            }
            let overlap: Double
            if let targetBounds {
                let intersection = bounds.intersection(targetBounds)
                if intersection.isNull || targetBounds.width <= 0 || targetBounds.height <= 0 {
                    overlap = 0
                } else {
                    overlap = max(0, min(1, (intersection.width * intersection.height) / (targetBounds.width * targetBounds.height)))
                }
            } else {
                overlap = 1
            }
            let candidate = WindowCandidate(
                windowID: row[kCGWindowNumber as String] as? Int,
                ownerName: row[kCGWindowOwnerName as String] as? String,
                ownerPID: ownerPID.map(Int.init),
                title: row[kCGWindowName as String] as? String,
                bounds: DisplayBounds(x: bounds.minX, y: bounds.minY, width: bounds.width, height: bounds.height),
                overlap: overlap
            )
            candidates.append(candidate)
        }
        return candidates.sorted { left, right in
            if left.overlap == right.overlap {
                return left.bounds.width * left.bounds.height > right.bounds.width * right.bounds.height
            }
            return left.overlap > right.overlap
        }.first
    }

    private func publicStationTitle(_ title: String?) -> String? {
        guard let title, !title.isEmpty else { return nil }
        let lower = title.lowercased()
        let hints = ["station", "ai workflow", "localhost", "127.0.0.1", "root navigator", "system atlas", "codemap", "demo take"]
        return hints.contains(where: { lower.contains($0) }) ? title : nil
    }

    private func append(_ event: [String: Any], to url: URL) {
        guard JSONSerialization.isValidJSONObject(event),
              let data = try? JSONSerialization.data(withJSONObject: event, options: [.sortedKeys])
        else {
            return
        }
        guard let handle = try? FileHandle(forWritingTo: url) else { return }
        defer { try? handle.close() }
        do {
            try handle.seekToEnd()
            handle.write(data)
            handle.write(Data("\n".utf8))
        } catch {
            emitStatus("Attention telemetry write failed", detail: error.localizedDescription)
        }
    }

    private func emitStatus(_ line: String, detail: String) {
        statusHandler(RecordedScreenAttentionStatus(line: line, detail: detail))
    }

    private static func windowBounds(from row: [String: Any]) -> CGRect? {
        guard let bounds = row[kCGWindowBounds as String] as? [String: Any],
              let x = Self.cgFloat(bounds["X"]) ?? Self.cgFloat(bounds["x"]),
              let y = Self.cgFloat(bounds["Y"]) ?? Self.cgFloat(bounds["y"]),
              let width = Self.cgFloat(bounds["Width"]) ?? Self.cgFloat(bounds["width"]),
              let height = Self.cgFloat(bounds["Height"]) ?? Self.cgFloat(bounds["height"])
        else {
            return nil
        }
        return CGRect(x: x, y: y, width: width, height: height)
    }

    private static func cgFloat(_ value: Any?) -> CGFloat? {
        if let value = value as? CGFloat {
            return value
        }
        if let value = value as? Double {
            return CGFloat(value)
        }
        if let value = value as? NSNumber {
            return CGFloat(truncating: value)
        }
        return nil
    }

    private static func isoString(_ date: Date) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.string(from: date)
    }

    private struct WindowCandidate {
        let windowID: Int?
        let ownerName: String?
        let ownerPID: Int?
        let title: String?
        let bounds: DisplayBounds
        let overlap: Double
    }

    private struct AttentionSignature: Equatable {
        let bundleIdentifier: String
        let localizedName: String
        let windowID: Int?
        let publicSafeTitle: String?
        let overlapBucket: Int
        let isOnRecordedDisplay: Bool
    }

    private struct AttentionSample {
        let event: [String: Any]
        let signature: AttentionSignature
        let label: String
        let at: Date
    }

    private struct PendingAttentionSample {
        let sample: AttentionSample
        let firstSeenAt: Date

        var signature: AttentionSignature {
            sample.signature
        }
    }
}
