import AppKit
import AVFoundation
import Foundation

enum HostEnvironment {
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

    static func findFFmpeg() -> String? {
        let candidates = [
            "/opt/homebrew/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/usr/bin/ffmpeg",
        ]
        return candidates.first { FileManager.default.isExecutableFile(atPath: $0) }
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
                mappingConfidence: "mapping ambiguous"
            )
        }

        let scale = screen.backingScaleFactor
        let width = Int(screen.frame.width * scale)
        let height = Int(screen.frame.height * scale)
        let origin = "x \(Int(screen.frame.minX)), y \(Int(screen.frame.minY))"
        return DisplayMetadata(
            index: index,
            name: screen.localizedName,
            resolution: "\(width)x\(height)",
            origin: origin,
            mappingConfidence: "NSScreen order approximation"
        )
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

    private static func orderedScreens() -> [NSScreen] {
        NSScreen.screens.sorted { left, right in
            if left.frame.minX == right.frame.minX {
                return left.frame.minY > right.frame.minY
            }
            return left.frame.minX < right.frame.minX
        }
    }
}

enum PermissionService {
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
