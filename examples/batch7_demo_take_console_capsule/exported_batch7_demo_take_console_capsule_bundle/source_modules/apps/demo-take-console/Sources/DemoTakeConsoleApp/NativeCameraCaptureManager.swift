@preconcurrency import AVFoundation
import CoreMedia
import Foundation

struct NativeCameraCaptureTrack: Sendable {
    let device: CaptureDevice
    let relativePath: String
    let startedAt: Date
}

struct NativeCameraRecordingStats: Sendable {
    let recordedDurationSeconds: Double
    let recordedFileSizeBytes: Int64
    let videoFrameCount: Int
    let distinctFrameSignatureCount: Int
    let lastVideoFrameAt: Date?
    let lastDistinctFrameAt: Date?
}

@MainActor
protocol NativeCameraCaptureManaging: AnyObject {
    var isRecording: Bool { get }
    var activeRecordingStats: NativeCameraRecordingStats? { get }
    func start(
        takeRoot: URL,
        webcam: CaptureDevice?,
        segmentIndex: Int
    ) async throws -> NativeCameraCaptureTrack?
    func stop() async throws
}

enum NativeCameraCaptureError: LocalizedError {
    case cameraPermissionMissing
    case deviceNotFound(String)
    case addInputFailed(String)
    case addOutputFailed
    case startFailed(String)
    case stopFailed(String)
    case outputMissing(String)
    case outputEmpty(String)

    var errorDescription: String? {
        switch self {
        case .cameraPermissionMissing:
            "Camera permission is not granted for Demo Take Console."
        case .deviceNotFound(let name):
            "Could not find the selected camera: \(name)."
        case .addInputFailed(let name):
            "Could not attach camera input: \(name)."
        case .addOutputFailed:
            "Could not attach native camera movie output."
        case .startFailed(let message):
            "Native camera capture failed to start: \(message)"
        case .stopFailed(let message):
            "Native camera capture failed to stop: \(message)"
        case .outputMissing(let path):
            "Native camera capture did not write \(path)."
        case .outputEmpty(let path):
            "Native camera capture wrote an empty file at \(path)."
        }
    }
}

@MainActor
final class NativeCameraCaptureManager: NativeCameraCaptureManaging {
    private var recorder: NativeCameraRecorder?

    var isRecording: Bool {
        recorder != nil
    }

    var activeRecordingStats: NativeCameraRecordingStats? {
        recorder?.recordingStats()
    }

    func start(
        takeRoot: URL,
        webcam: CaptureDevice?,
        segmentIndex: Int = 1
    ) async throws -> NativeCameraCaptureTrack? {
        guard let webcam else { return nil }
        if isRecording {
            try await stop()
        }

        let relativePath = Self.relativePath(segmentIndex: segmentIndex)
        let outputURL = takeRoot.appendingPathComponent(relativePath)
        let recorder = NativeCameraRecorder(
            deviceName: webcam.name,
            deviceUniqueID: webcam.uniqueID,
            outputURL: outputURL
        )
        do {
            try await recorder.start()
        } catch {
            try? await recorder.stop()
            throw error
        }
        self.recorder = recorder
        return NativeCameraCaptureTrack(device: webcam, relativePath: relativePath, startedAt: Date())
    }

    private static func relativePath(segmentIndex: Int) -> String {
        guard segmentIndex > 1 else {
            return "tracks/webcam.mov"
        }
        return String(format: "tracks/segments/%04d/webcam.mov", segmentIndex)
    }

    func stop() async throws {
        guard let recorder else { return }
        self.recorder = nil
        try await recorder.stop()
    }
}

final class CameraRecordingContinuationState: @unchecked Sendable {
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

private final class NativeCameraRecorder: NSObject, AVCaptureFileOutputRecordingDelegate, AVCaptureVideoDataOutputSampleBufferDelegate, @unchecked Sendable {
    private let deviceName: String
    private let deviceUniqueID: String?
    private let outputURL: URL
    private let session = AVCaptureSession()
    private let movieOutput = AVCaptureMovieFileOutput()
    private let videoSampleOutput = AVCaptureVideoDataOutput()
    private let queue = DispatchQueue(label: "ai.workflow.demo-take-console.native-camera")
    private let lock = NSLock()
    private let continuationState = CameraRecordingContinuationState()
    private var terminalError: Error?
    private var videoFrameCount = 0
    private var distinctFrameSignatureCount = 0
    private var lastFrameSignature: UInt64?
    private var lastVideoFrameAt: Date?
    private var lastDistinctFrameAt: Date?
    private static let targetWidth: Int32 = 1_280
    private static let targetHeight: Int32 = 720
    private static let targetFrameRate: Double = 30
    private static let targetBitRate = 2_000_000

    init(deviceName: String, deviceUniqueID: String?, outputURL: URL) {
        self.deviceName = deviceName
        self.deviceUniqueID = deviceUniqueID
        self.outputURL = outputURL
    }

    @MainActor
    func start() async throws {
        guard AVCaptureDevice.authorizationStatus(for: .video) == .authorized else {
            throw NativeCameraCaptureError.cameraPermissionMissing
        }
        guard let device = selectVideoDevice(uniqueID: deviceUniqueID, name: deviceName) else {
            throw NativeCameraCaptureError.deviceNotFound(
                deviceUniqueID.map { "\(deviceName) [\($0)]" } ?? deviceName
            )
        }

        try FileManager.default.createDirectory(
            at: outputURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try? FileManager.default.removeItem(at: outputURL)

        do {
            let input = try AVCaptureDeviceInput(device: device)
            session.beginConfiguration()
            session.inputs.forEach { session.removeInput($0) }
            session.outputs.forEach { session.removeOutput($0) }
            if session.canSetSessionPreset(.hd1280x720) {
                session.sessionPreset = .hd1280x720
            } else if session.canSetSessionPreset(.high) {
                session.sessionPreset = .high
            }
            configureVideoFormat(device)
            guard session.canAddInput(input) else {
                session.commitConfiguration()
                throw NativeCameraCaptureError.addInputFailed(device.localizedName)
            }
            session.addInput(input)
            guard session.canAddOutput(movieOutput) else {
                session.removeInput(input)
                session.commitConfiguration()
                throw NativeCameraCaptureError.addOutputFailed
            }
            session.addOutput(movieOutput)
            if session.canAddOutput(videoSampleOutput) {
                videoSampleOutput.alwaysDiscardsLateVideoFrames = true
                videoSampleOutput.videoSettings = [
                    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
                ]
                videoSampleOutput.setSampleBufferDelegate(self, queue: queue)
                session.addOutput(videoSampleOutput)
            }
            if let connection = movieOutput.connection(with: .video),
               connection.isVideoMirroringSupported {
                connection.isVideoMirrored = false
            }
            configureMovieOutput()
            session.commitConfiguration()
        } catch {
            await stopSessionAndClearGraph()
            throw error
        }

        await startSession()
        guard session.isRunning else {
            await stopSessionAndClearGraph()
            throw NativeCameraCaptureError.startFailed("AVCaptureSession did not enter the running state.")
        }

        try await withCheckedThrowingContinuation { continuation in
            continuationState.setStart(continuation)
            movieOutput.startRecording(to: outputURL, recordingDelegate: self)
            if movieOutput.isRecording {
                continuationState.finishStart(.success(()))
            }
            queue.asyncAfter(deadline: .now() + 2) { [weak self, continuationState] in
                guard let self else { return }
                let result: Result<Void, Error> = self.movieOutput.isRecording
                    ? .success(())
                    : .failure(NativeCameraCaptureError.startFailed("AVCaptureMovieFileOutput did not report recording start within 2 seconds."))
                continuationState.finishStart(result)
            }
        }
        guard movieOutput.isRecording else {
            await stopSessionAndClearGraph()
            throw NativeCameraCaptureError.startFailed("AVCaptureMovieFileOutput did not enter the recording state.")
        }
    }

    private func configureVideoFormat(_ device: AVCaptureDevice) {
        let targetFrameDuration = CMTime(value: 1, timescale: Int32(Self.targetFrameRate))
        do {
            try device.lockForConfiguration()
            if let format = Self.preferredEfficientFormat(for: device) {
                device.activeFormat = format
            }
            let supportsTargetFrameRate = device.activeFormat.videoSupportedFrameRateRanges.contains { range in
                range.minFrameRate <= Self.targetFrameRate && range.maxFrameRate >= Self.targetFrameRate
            }
            if supportsTargetFrameRate {
                device.activeVideoMinFrameDuration = targetFrameDuration
                device.activeVideoMaxFrameDuration = targetFrameDuration
            }
            device.unlockForConfiguration()
        } catch {
            return
        }
    }

    private func configureMovieOutput() {
        guard let connection = movieOutput.connection(with: .video) else { return }
        movieOutput.setOutputSettings([
            AVVideoCodecKey: AVVideoCodecType.h264,
            AVVideoWidthKey: Int(Self.targetWidth),
            AVVideoHeightKey: Int(Self.targetHeight),
            AVVideoCompressionPropertiesKey: [
                AVVideoAverageBitRateKey: Self.targetBitRate,
                AVVideoMaxKeyFrameIntervalKey: Int(Self.targetFrameRate),
            ],
        ], for: connection)
    }

    private static func preferredEfficientFormat(for device: AVCaptureDevice) -> AVCaptureDevice.Format? {
        device.formats
            .filter { format in
                let dimensions = CMVideoFormatDescriptionGetDimensions(format.formatDescription)
                guard dimensions.width > 0, dimensions.height > 0 else { return false }
                return format.videoSupportedFrameRateRanges.contains { range in
                    range.minFrameRate <= targetFrameRate && range.maxFrameRate >= targetFrameRate
                }
            }
            .min { left, right in
                Self.formatSortKey(left) < Self.formatSortKey(right)
            }
    }

    private static func formatSortKey(_ format: AVCaptureDevice.Format) -> (Int, Int64, Double) {
        let dimensions = CMVideoFormatDescriptionGetDimensions(format.formatDescription)
        let exceedsTarget = dimensions.width > targetWidth || dimensions.height > targetHeight ? 1 : 0
        let targetPixels = Int64(targetWidth) * Int64(targetHeight)
        let pixels = Int64(dimensions.width) * Int64(dimensions.height)
        let pixelDelta = abs(pixels - targetPixels)
        let aspect = Double(dimensions.width) / max(1.0, Double(dimensions.height))
        let aspectDelta = abs(aspect - (16.0 / 9.0))
        return (exceedsTarget, pixelDelta, aspectDelta)
    }

    @MainActor
    func stop() async throws {
        var stopError: Error?
        if movieOutput.isRecording {
            do {
                try await withCheckedThrowingContinuation { continuation in
                    continuationState.setStop(continuation)
                    movieOutput.stopRecording()
                    queue.asyncAfter(deadline: .now() + 5) { [continuationState] in
                        continuationState.finishStop(.failure(
                            NativeCameraCaptureError.stopFailed("AVCaptureMovieFileOutput did not finish stopping within 5 seconds.")
                        ))
                    }
                }
            } catch {
                stopError = error
            }
        }

        await stopSessionAndClearGraph()

        if let stopError {
            throw stopError
        }
        if let terminalError {
            throw NativeCameraCaptureError.stopFailed(terminalError.localizedDescription)
        }
        try validateOutputFile()
    }

    func fileOutput(
        _ output: AVCaptureFileOutput,
        didStartRecordingTo fileURL: URL,
        from connections: [AVCaptureConnection]
    ) {
        continuationState.finishStart(.success(()))
    }

    func fileOutput(
        _ output: AVCaptureFileOutput,
        didFinishRecordingTo outputFileURL: URL,
        from connections: [AVCaptureConnection],
        error: Error?
    ) {
        if let error {
            setTerminalError(error)
            let captureError = NativeCameraCaptureError.stopFailed(error.localizedDescription)
            continuationState.finishStart(.failure(captureError))
            continuationState.finishStop(.failure(captureError))
        } else {
            continuationState.finishStop(.success(()))
        }
    }

    func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        guard let signature = Self.frameSignature(from: sampleBuffer) else { return }
        let now = Date()
        lock.lock()
        videoFrameCount += 1
        lastVideoFrameAt = now
        if signature != lastFrameSignature {
            lastFrameSignature = signature
            distinctFrameSignatureCount += 1
            lastDistinctFrameAt = now
        }
        lock.unlock()
    }

    func recordingStats() -> NativeCameraRecordingStats {
        lock.lock()
        let frameCount = videoFrameCount
        let distinctCount = distinctFrameSignatureCount
        let lastFrameAt = lastVideoFrameAt
        let lastDistinctAt = lastDistinctFrameAt
        lock.unlock()
        let duration = movieOutput.recordedDuration
        return NativeCameraRecordingStats(
            recordedDurationSeconds: duration.isValid ? CMTimeGetSeconds(duration) : 0,
            recordedFileSizeBytes: movieOutput.recordedFileSize,
            videoFrameCount: frameCount,
            distinctFrameSignatureCount: distinctCount,
            lastVideoFrameAt: lastFrameAt,
            lastDistinctFrameAt: lastDistinctAt
        )
    }

    private func selectVideoDevice(uniqueID: String?, name: String) -> AVCaptureDevice? {
        AVCaptureDeviceIdentityResolver.videoDevice(
            uniqueID: uniqueID,
            name: name,
            allowFallback: false
        )
    }

    private func startSession() async {
        await withCheckedContinuation { continuation in
            queue.async { [session] in
                session.startRunning()
                continuation.resume()
            }
        }
    }

    @MainActor
    private func stopSessionAndClearGraph() async {
        await withCheckedContinuation { continuation in
            queue.async { [session] in
                if session.isRunning {
                    session.stopRunning()
                }
                continuation.resume()
            }
        }

        session.beginConfiguration()
        session.inputs.forEach { session.removeInput($0) }
        session.outputs.forEach { session.removeOutput($0) }
        session.commitConfiguration()
    }

    private func setTerminalError(_ error: Error) {
        lock.lock()
        terminalError = error
        lock.unlock()
    }

    private func validateOutputFile() throws {
        guard FileManager.default.fileExists(atPath: outputURL.path) else {
            throw NativeCameraCaptureError.outputMissing(outputURL.lastPathComponent)
        }
        let attributes = try FileManager.default.attributesOfItem(atPath: outputURL.path)
        let bytes = (attributes[.size] as? NSNumber)?.int64Value ?? 0
        guard bytes > 0 else {
            throw NativeCameraCaptureError.outputEmpty(outputURL.lastPathComponent)
        }
    }

    private static func frameSignature(from sampleBuffer: CMSampleBuffer) -> UInt64? {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return nil }
        CVPixelBufferLockBaseAddress(pixelBuffer, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(pixelBuffer, .readOnly) }
        guard CVPixelBufferGetPixelFormatType(pixelBuffer) == kCVPixelFormatType_32BGRA,
              let baseAddress = CVPixelBufferGetBaseAddress(pixelBuffer)
        else {
            return nil
        }
        let width = CVPixelBufferGetWidth(pixelBuffer)
        let height = CVPixelBufferGetHeight(pixelBuffer)
        let bytesPerRow = CVPixelBufferGetBytesPerRow(pixelBuffer)
        guard width > 0, height > 0, bytesPerRow >= width * 4 else { return nil }

        let bytes = baseAddress.assumingMemoryBound(to: UInt8.self)
        var hash: UInt64 = 1_469_598_103_934_665_603
        let xStep = max(width / 8, 1)
        let yStep = max(height / 8, 1)
        var y = yStep / 2
        while y < height {
            var x = xStep / 2
            while x < width {
                let offset = y * bytesPerRow + x * 4
                hash = (hash ^ UInt64(bytes[offset])) &* 1_099_511_628_211
                hash = (hash ^ UInt64(bytes[offset + 1])) &* 1_099_511_628_211
                hash = (hash ^ UInt64(bytes[offset + 2])) &* 1_099_511_628_211
                x += xStep
            }
            y += yStep
        }
        return hash
    }
}
