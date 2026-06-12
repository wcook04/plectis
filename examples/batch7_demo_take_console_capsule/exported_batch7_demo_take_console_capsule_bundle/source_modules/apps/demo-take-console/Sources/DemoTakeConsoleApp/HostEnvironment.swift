import AppKit
import AVFoundation
import CoreGraphics
import Foundation
import ScreenCaptureKit

enum HostEnvironment {
    struct DisplaySnapshotFrame: @unchecked Sendable {
        let displayID: UInt32
        let image: CGImage
    }

    static var repoRoot: URL {
        if let configured = Bundle.main.object(forInfoDictionaryKey: "AIWorkflowRepoRoot") as? String,
           !configured.isEmpty {
            return URL(fileURLWithPath: configured, isDirectory: true)
        }
        return URL(fileURLWithPath: FileManager.default.currentDirectoryPath, isDirectory: true)
    }

    static var outputRoot: URL {
        repoRoot
            .appendingPathComponent("state", isDirectory: true)
            .appendingPathComponent("dissemination", isDirectory: true)
            .appendingPathComponent("demo_takes", isDirectory: true)
    }

    static var disseminationStateRoot: URL {
        repoRoot
            .appendingPathComponent("state", isDirectory: true)
            .appendingPathComponent("dissemination", isDirectory: true)
    }

    static var deviceInventoryCacheURL: URL {
        disseminationStateRoot.appendingPathComponent("demo_take_device_inventory.json")
    }

    static var recorderConfigURL: URL {
        disseminationStateRoot.appendingPathComponent("demo_take_config.json")
    }

    static func findFFmpeg() -> String? {
        let bundleFFmpeg = Bundle.main.resourceURL?
            .appendingPathComponent("ffmpeg")
        let candidates: [URL?] = [
            bundleFFmpeg,
            URL(fileURLWithPath: "/opt/homebrew/bin/ffmpeg"),
            URL(fileURLWithPath: "/usr/local/bin/ffmpeg"),
            URL(fileURLWithPath: "/usr/bin/ffmpeg"),
        ]
        return candidates.compactMap { $0 }.first {
            FileManager.default.isExecutableFile(atPath: $0.path)
        }?.path
    }

    static func findTranscribeBinary() -> String? {
        let fm = FileManager.default
        let bundleResources = Bundle.main.resourceURL?
            .appendingPathComponent("demo-take-transcribe")
        let candidates: [URL?] = [
            bundleResources,
            repoRoot.appendingPathComponent("apps/demo-take-console/dist/demo-take-transcribe"),
            repoRoot.appendingPathComponent("apps/demo-take-console/.build/release/demo-take-transcribe"),
            repoRoot.appendingPathComponent("apps/demo-take-console/.build/debug/demo-take-transcribe"),
            repoRoot.appendingPathComponent("apps/demo-take-console/.build/arm64-apple-macosx/release/demo-take-transcribe"),
            repoRoot.appendingPathComponent("apps/demo-take-console/.build/arm64-apple-macosx/debug/demo-take-transcribe"),
        ]
        for url in candidates.compactMap({ $0 }) {
            if fm.isExecutableFile(atPath: url.path) {
                return url.path
            }
        }
        return nil
    }

    static func availableDiskBytes(at url: URL) -> Int64? {
        let probeURL = FileManager.default.fileExists(atPath: url.path) ? url : repoRoot
        guard let values = try? probeURL.resourceValues(forKeys: [.volumeAvailableCapacityForImportantUsageKey]),
              let capacity = values.volumeAvailableCapacityForImportantUsage
        else {
            return nil
        }
        return Int64(capacity)
    }

    static func byteString(_ bytes: Int64?) -> String {
        guard let bytes else { return "Unknown" }
        let formatter = ByteCountFormatter()
        formatter.allowedUnits = [.useGB, .useMB]
        formatter.countStyle = .file
        formatter.includesUnit = true
        formatter.includesCount = true
        return formatter.string(fromByteCount: bytes)
    }

    static func displayMetadata(forFFmpegScreenIndex index: Int) -> DisplayMetadata {
        guard let screen = screen(forFFmpegScreenIndex: index) else {
            return DisplayMetadata(
                index: index,
                name: "Capture screen \(index)",
                resolution: "unmapped",
                origin: "No matching NSScreen",
                mappingConfidence: "mapping ambiguous",
                displayID: nil,
                bounds: nil,
                scaleFactor: 1.0
            )
        }

        let scale = screen.backingScaleFactor
        let width = Int(screen.frame.width * scale)
        let height = Int(screen.frame.height * scale)
        let origin = "x \(Int(screen.frame.minX)), y \(Int(screen.frame.minY))"
        let screenNumberKey = NSDeviceDescriptionKey("NSScreenNumber")
        let displayID = (screen.deviceDescription[screenNumberKey] as? NSNumber)?.uint32Value
        return DisplayMetadata(
            index: index,
            name: screen.localizedName,
            resolution: "\(width)x\(height)",
            origin: origin,
            mappingConfidence: "NSScreen order approximation",
            displayID: displayID,
            bounds: DisplayBounds(
                x: screen.frame.minX,
                y: screen.frame.minY,
                width: screen.frame.width,
                height: screen.frame.height
            ),
            scaleFactor: scale
        )
    }

    static func screenRecordingAccessGranted() -> Bool {
        CGPreflightScreenCaptureAccess()
    }

    @MainActor
    static func window(_ window: NSWindow, intersectsAnyDisplayID displayIDs: Set<UInt32>) -> Bool {
        guard !displayIDs.isEmpty else { return false }
        return orderedScreens().contains { screen in
            guard let displayID = displayID(for: screen), displayIDs.contains(displayID) else {
                return false
            }
            return window.frame.intersects(screen.frame)
        }
    }

    static func captureDisplaySnapshotFrame(displayID: UInt32, targetWidth: Int = 720) async -> DisplaySnapshotFrame? {
        await captureDisplaySnapshotImage(displayID: displayID, targetWidth: targetWidth)
    }

    static func mainFFmpegScreenIndex() -> Int? {
        guard let main = NSScreen.main else { return nil }
        return orderedScreens().firstIndex { screen in
            screen === main
                || (screen.localizedName == main.localizedName && screen.frame == main.frame)
        }
    }

    static func screen(forFFmpegScreenIndex index: Int) -> NSScreen? {
        let screens = orderedScreens()
        guard screens.indices.contains(index) else { return nil }
        return screens[index]
    }

    static func displayID(for screen: NSScreen) -> UInt32? {
        let screenNumberKey = NSDeviceDescriptionKey("NSScreenNumber")
        return (screen.deviceDescription[screenNumberKey] as? NSNumber)?.uint32Value
    }

    private static func orderedScreens() -> [NSScreen] {
        NSScreen.screens.sorted { left, right in
            if left.frame.minX == right.frame.minX {
                return left.frame.minY > right.frame.minY
            }
            return left.frame.minX < right.frame.minX
        }
    }

    nonisolated private static func captureDisplaySnapshotImage(displayID: UInt32, targetWidth: Int) async -> DisplaySnapshotFrame? {
        do {
            let content = try await SCShareableContent.current
            guard let display = content.displays.first(where: { $0.displayID == displayID }) else {
                return nil
            }
            let ownWindows = content.windows.filter {
                $0.owningApplication?.bundleIdentifier == Bundle.main.bundleIdentifier
            }
            let filter = SCContentFilter(display: display, excludingWindows: ownWindows)
            let config = SCStreamConfiguration()
            config.width = max(240, targetWidth)
            config.height = max(1, Int(Double(config.width) * Double(display.height) / Double(max(display.width, 1))))
            config.showsCursor = false
            let image = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: config)
            return DisplaySnapshotFrame(displayID: displayID, image: image)
        } catch {
            return nil
        }
    }
}

enum PermissionService {
    static func screenCaptureStatus() -> CapabilityStatus {
        CGPreflightScreenCaptureAccess() ? .ready : .missing
    }

    static func requestScreenCaptureAccess() -> CapabilityStatus {
        CGRequestScreenCaptureAccess() ? .ready : .missing
    }

    static func microphoneStatus() -> CapabilityStatus {
        switch AVCaptureDevice.authorizationStatus(for: .audio) {
        case .authorized: .ready
        case .notDetermined: .unknown
        default: .missing
        }
    }

    static func cameraStatus(required: Bool) -> CapabilityStatus {
        guard required else { return .notRequired }
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            return .ready
        case .notDetermined:
            return .unknown
        default:
            return .missing
        }
    }
}
