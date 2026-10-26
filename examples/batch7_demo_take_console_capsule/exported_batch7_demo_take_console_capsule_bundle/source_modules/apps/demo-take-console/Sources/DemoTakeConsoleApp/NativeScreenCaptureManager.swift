import AVFoundation
import CoreMedia
import Foundation
@preconcurrency import ScreenCaptureKit

struct NativeScreenCaptureTrack: Sendable {
    let device: CaptureDevice
    let relativePath: String
    let startedAt: Date
}

@MainActor
protocol NativeScreenCaptureManaging: AnyObject {
    var isRecording: Bool { get }
    func start(takeRoot: URL, screens: [CaptureDevice], segmentIndex: Int) async throws -> [NativeScreenCaptureTrack]
    func stop() async throws
}

enum NativeScreenCaptureError: LocalizedError {
    case noSelectedScreens
    case displayNotFound(String)
    case addRecordingOutputFailed
    case startFailed(String)
    case stopFailed(String)
    case outputMissing(String)
    case outputEmpty(String)
    case displaysUnavailable(String?)

    var errorDescription: String? {
        switch self {
        case .noSelectedScreens:
            "No display was selected for native screen capture."
        case .displaysUnavailable(let detail):
            if let detail, !detail.isEmpty {
                "ScreenCaptureKit found no capturable displays (\(detail)). Wake the display, confirm Screen Recording permission for this app, then try again."
            } else {
                "ScreenCaptureKit found no capturable displays. Wake the display, confirm Screen Recording permission for this app, then try again."
            }
        case .displayNotFound(let name):
            "Could not map \(name) to a ScreenCaptureKit display."
        case .addRecordingOutputFailed:
            "ScreenCaptureKit refused the recording output."
        case .startFailed(let message):
            "ScreenCaptureKit failed to start: \(message)"
        case .stopFailed(let message):
            "ScreenCaptureKit failed to stop: \(message)"
        case .outputMissing(let path):
            "ScreenCaptureKit did not write \(path)."
        case .outputEmpty(let path):
            "ScreenCaptureKit wrote an empty file at \(path)."
        }
    }
}

@MainActor
final class NativeScreenCaptureManager: NativeScreenCaptureManaging {
    private var recorders: [NativeScreenRecorder] = []

    var isRecording: Bool {
        !recorders.isEmpty
    }

    func start(takeRoot: URL, screens: [CaptureDevice], segmentIndex: Int = 1) async throws -> [NativeScreenCaptureTrack] {
        let targetScreens = Array(screens.prefix(1))
        guard !targetScreens.isEmpty else { throw NativeScreenCaptureError.noSelectedScreens }
        if isRecording {
            try await stop()
        }

        let content = try await Self.currentShareableContent()
        var startedRecorders: [NativeScreenRecorder] = []
        var tracks: [NativeScreenCaptureTrack] = []

        do {
            for screen in targetScreens {
                guard let display = display(for: screen, in: content) else {
                    throw NativeScreenCaptureError.displayNotFound(screen.name)
                }
                let relativePath = Self.relativePath(for: screen, segmentIndex: segmentIndex)
                let outputURL = takeRoot.appendingPathComponent(relativePath)
                // Exclude app-owned private overlays while re-including normal
                // visible app windows, so the console can be shown in the take.
                let filter = RecipientOverlayCaptureExclusion.contentFilter(
                    display: display,
                    content: content
                )
                let recorder = NativeScreenRecorder(
                    display: display,
                    filter: filter,
                    outputURL: outputURL
                )
                try await recorder.start()
                let startedAt = Date()
                startedRecorders.append(recorder)
                tracks.append(NativeScreenCaptureTrack(device: screen, relativePath: relativePath, startedAt: startedAt))
            }
        } catch {
            for recorder in startedRecorders {
                try? await recorder.stop()
            }
            throw error
        }

        recorders = startedRecorders
        return tracks
    }

    // SCShareableContent.current can throw "Failed to find any displays or
    // windows to capture" or return zero displays when the screen has just woken
    // from sleep — common when resuming a long, paused take. A short backoff lets
    // the window server re-enumerate displays before we give up with a clear error.
    private static func currentShareableContent(retries: Int = 3) async throws -> SCShareableContent {
        let attempts = max(1, retries)
        var lastError: Error?
        for attempt in 0..<attempts {
            do {
                let content = try await SCShareableContent.current
                if !content.displays.isEmpty {
                    return content
                }
            } catch {
                lastError = error
            }
            if attempt < attempts - 1 {
                try? await Task.sleep(nanoseconds: 400_000_000)
            }
        }
        throw NativeScreenCaptureError.displaysUnavailable(lastError?.localizedDescription)
    }

    private static func relativePath(for screen: CaptureDevice, segmentIndex: Int) -> String {
        guard segmentIndex > 1 else {
            return "tracks/screen_\(screen.index).mp4"
        }
        return String(format: "tracks/segments/%04d/screen_%d.mp4", segmentIndex, screen.index)
    }

    func stop() async throws {
        var firstError: Error?
        for recorder in recorders {
            do {
                try await recorder.stop()
            } catch {
                if firstError == nil {
                    firstError = error
                }
            }
        }
        recorders.removeAll()
        if let firstError {
            throw firstError
        }
    }

    private func display(for screen: CaptureDevice, in content: SCShareableContent) -> SCDisplay? {
        let metadata = HostEnvironment.displayMetadata(forFFmpegScreenIndex: screen.screenOrdinal)
        if let displayID = metadata.displayID,
           let display = content.displays.first(where: { $0.displayID == displayID }) {
            return display
        }

        let orderedDisplays = content.displays.sorted { left, right in
            if left.frame.minX == right.frame.minX {
                return left.frame.minY > right.frame.minY
            }
            return left.frame.minX < right.frame.minX
        }
        guard orderedDisplays.indices.contains(screen.screenOrdinal) else { return nil }
        return orderedDisplays[screen.screenOrdinal]
    }
}

final class ScreenCaptureContinuationState: @unchecked Sendable {
    private var startContinuation: CheckedContinuation<Void, Error>?
    private var stopContinuation: CheckedContinuation<Void, Error>?
    private let lock = NSLock()

    func setStart(_ continuation: CheckedContinuation<Void, Error>) {
        lock.lock()
        startContinuation = continuation
        lock.unlock()
    }

    func setStop(_ continuation: CheckedContinuation<Void, Error>) {
        lock.lock()
        stopContinuation = continuation
        lock.unlock()
    }

    func finishStart(_ result: Result<Void, Error>) {
        let continuation: CheckedContinuation<Void, Error>?
        lock.lock()
        continuation = startContinuation
        startContinuation = nil
        lock.unlock()
        resume(continuation, with: result)
    }

    func finishStop(_ result: Result<Void, Error>) {
        let continuation: CheckedContinuation<Void, Error>?
        lock.lock()
        continuation = stopContinuation
        stopContinuation = nil
        lock.unlock()
        resume(continuation, with: result)
    }

    private func resume(_ continuation: CheckedContinuation<Void, Error>?, with result: Result<Void, Error>) {
        guard let continuation else { return }
        switch result {
        case .success:
            continuation.resume()
        case .failure(let error):
            continuation.resume(throwing: error)
        }
    }
}

private final class NativeScreenRecorder: NSObject, @unchecked Sendable, SCRecordingOutputDelegate, SCStreamDelegate {
    private static let efficientMaxWidth = 1280
    private static let efficientMaxHeight = 720

    private let display: SCDisplay
    private let filter: SCContentFilter
    private let outputURL: URL
    private var stream: SCStream?
    private var recordingOutput: SCRecordingOutput?
    private let continuationState = ScreenCaptureContinuationState()

    init(display: SCDisplay, filter: SCContentFilter, outputURL: URL) {
        self.display = display
        self.filter = filter
        self.outputURL = outputURL
    }

    func start() async throws {
        try FileManager.default.createDirectory(
            at: outputURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try? FileManager.default.removeItem(at: outputURL)

        let filter = self.filter
        let outputSize = Self.efficientOutputSize(for: display)
        let config = SCStreamConfiguration()
        config.width = outputSize.width
        config.height = outputSize.height
        config.minimumFrameInterval = CMTime(value: 1, timescale: 30)
        config.queueDepth = 8
        config.showsCursor = true
        config.capturesAudio = false
        config.captureMicrophone = false
        config.captureDynamicRange = .SDR

        let stream = SCStream(filter: filter, configuration: config, delegate: self)
        let outputConfig = SCRecordingOutputConfiguration()
        outputConfig.outputURL = outputURL
        outputConfig.videoCodecType = .h264
        outputConfig.outputFileType = .mp4
        let recordingOutput = SCRecordingOutput(configuration: outputConfig, delegate: self)

        try stream.addRecordingOutput(recordingOutput)

        self.stream = stream
        self.recordingOutput = recordingOutput

        try await withCheckedThrowingContinuation { continuation in
            continuationState.setStart(continuation)
            stream.startCapture { [continuationState] error in
                if let error {
                    continuationState.finishStart(.failure(NativeScreenCaptureError.startFailed(error.localizedDescription)))
                }
            }
        }
    }

    func stop() async throws {
        guard let stream else { return }
        try await withCheckedThrowingContinuation { continuation in
            continuationState.setStop(continuation)
            stream.stopCapture { [continuationState] error in
                if let error {
                    continuationState.finishStop(.failure(NativeScreenCaptureError.stopFailed(error.localizedDescription)))
                }
            }
        }
        self.stream = nil
        self.recordingOutput = nil
        try validateOutputFile()
    }

    func recordingOutputDidStartRecording(_ recordingOutput: SCRecordingOutput) {
        continuationState.finishStart(.success(()))
    }

    func recordingOutput(_ recordingOutput: SCRecordingOutput, didFailWithError error: Error) {
        continuationState.finishStart(.failure(error))
        continuationState.finishStop(.failure(error))
    }

    func recordingOutputDidFinishRecording(_ recordingOutput: SCRecordingOutput) {
        continuationState.finishStop(.success(()))
    }

    func stream(_ stream: SCStream, didStopWithError error: Error) {
        continuationState.finishStart(.failure(error))
        continuationState.finishStop(.failure(error))
    }

    private static func efficientOutputSize(for display: SCDisplay) -> (width: Int, height: Int) {
        let sourceWidth = max(1, display.width)
        let sourceHeight = max(1, display.height)
        let scale = min(
            1.0,
            Double(efficientMaxWidth) / Double(sourceWidth),
            Double(efficientMaxHeight) / Double(sourceHeight)
        )
        return (
            width: evenDimension(Int((Double(sourceWidth) * scale).rounded(.down))),
            height: evenDimension(Int((Double(sourceHeight) * scale).rounded(.down)))
        )
    }

    private static func evenDimension(_ value: Int) -> Int {
        max(2, value - (value % 2))
    }

    private func validateOutputFile() throws {
        guard FileManager.default.fileExists(atPath: outputURL.path) else {
            throw NativeScreenCaptureError.outputMissing(outputURL.lastPathComponent)
        }
        let attributes = try FileManager.default.attributesOfItem(atPath: outputURL.path)
        let bytes = (attributes[.size] as? NSNumber)?.int64Value ?? 0
        guard bytes > 0 else {
            throw NativeScreenCaptureError.outputEmpty(outputURL.lastPathComponent)
        }
    }
}
