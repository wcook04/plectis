@preconcurrency import AVFoundation
import Foundation

struct NativeAudioCaptureTrack: Sendable {
    let device: CaptureDevice
    let relativePath: String
    let startedAt: Date
}

typealias NativeAudioLevelHandler = @MainActor @Sendable (Float, String) -> Void

@MainActor
protocol NativeAudioCaptureManaging: AnyObject {
    var isRecording: Bool { get }
    func start(
        takeRoot: URL,
        microphone: CaptureDevice?,
        segmentIndex: Int,
        onLevel: NativeAudioLevelHandler?
    ) async throws -> NativeAudioCaptureTrack?
    func stop() async throws
}

enum NativeAudioCaptureError: LocalizedError {
    case microphonePermissionMissing
    case deviceNotFound(String)
    case addInputFailed(String)
    case addOutputFailed
    case unsupportedM4AOutput
    case startFailed(String)
    case stopFailed(String)
    case outputMissing(String)
    case outputEmpty(String)

    var errorDescription: String? {
        switch self {
        case .microphonePermissionMissing:
            "Microphone permission is not granted for Demo Take Console."
        case .deviceNotFound(let name):
            "Could not find the selected microphone: \(name)."
        case .addInputFailed(let name):
            "Could not attach microphone input: \(name)."
        case .addOutputFailed:
            "Could not attach native microphone file output."
        case .unsupportedM4AOutput:
            "Native microphone capture cannot write AAC/M4A on this Mac."
        case .startFailed(let message):
            "Native microphone capture failed to start: \(message)"
        case .stopFailed(let message):
            "Native microphone capture failed to stop: \(message)"
        case .outputMissing(let path):
            "Native microphone capture did not write \(path)."
        case .outputEmpty(let path):
            "Native microphone capture wrote an empty file at \(path)."
        }
    }
}

@MainActor
final class NativeAudioCaptureManager: NativeAudioCaptureManaging {
    private var recorder: NativeAudioRecorder?

    var isRecording: Bool {
        recorder != nil
    }

    func start(
        takeRoot: URL,
        microphone: CaptureDevice?,
        segmentIndex: Int = 1,
        onLevel: NativeAudioLevelHandler? = nil
    ) async throws -> NativeAudioCaptureTrack? {
        guard let microphone else { return nil }
        if isRecording {
            try await stop()
        }

        let relativePath = Self.relativePath(segmentIndex: segmentIndex)
        let outputURL = takeRoot.appendingPathComponent(relativePath)
        let recorder = NativeAudioRecorder(
            deviceName: microphone.name,
            deviceUniqueID: microphone.uniqueID,
            outputURL: outputURL,
            onLevel: onLevel
        )
        do {
            try await recorder.start()
        } catch {
            try? await recorder.stop()
            throw error
        }
        self.recorder = recorder
        return NativeAudioCaptureTrack(device: microphone, relativePath: relativePath, startedAt: Date())
    }

    private static func relativePath(segmentIndex: Int) -> String {
        guard segmentIndex > 1 else {
            return "tracks/microphone.m4a"
        }
        return String(format: "tracks/segments/%04d/microphone.m4a", segmentIndex)
    }

    func stop() async throws {
        guard let recorder else { return }
        self.recorder = nil
        try await recorder.stop()
    }
}

final class AudioRecordingContinuationState: @unchecked Sendable {
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

private final class NativeAudioRecorder: NSObject, AVCaptureFileOutputRecordingDelegate, AVCaptureAudioDataOutputSampleBufferDelegate, @unchecked Sendable {
    private static let levelEmissionInterval: CFTimeInterval = 1.0 / 10.0
    private let deviceName: String
    private let deviceUniqueID: String?
    private let outputURL: URL
    private let onLevel: NativeAudioLevelHandler?
    private let session = AVCaptureSession()
    private let audioOutput = AVCaptureAudioFileOutput()
    private let meterOutput = AVCaptureAudioDataOutput()
    private let queue = DispatchQueue(label: "ai.workflow.demo-take-console.native-audio")
    private let lock = NSLock()
    private let continuationState = AudioRecordingContinuationState()
    private var terminalError: Error?
    private var lastLevelEmissionTime: CFAbsoluteTime = 0

    init(
        deviceName: String,
        deviceUniqueID: String?,
        outputURL: URL,
        onLevel: NativeAudioLevelHandler?
    ) {
        self.deviceName = deviceName
        self.deviceUniqueID = deviceUniqueID
        self.outputURL = outputURL
        self.onLevel = onLevel
    }

    @MainActor
    func start() async throws {
        guard AVCaptureDevice.authorizationStatus(for: .audio) == .authorized else {
            throw NativeAudioCaptureError.microphonePermissionMissing
        }
        guard AVCaptureAudioFileOutput.availableOutputFileTypes().contains(.m4a) else {
            throw NativeAudioCaptureError.unsupportedM4AOutput
        }
        guard let device = selectAudioDevice(uniqueID: deviceUniqueID, name: deviceName) else {
            throw NativeAudioCaptureError.deviceNotFound(
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
            guard session.canAddInput(input) else {
                session.commitConfiguration()
                throw NativeAudioCaptureError.addInputFailed(device.localizedName)
            }
            session.addInput(input)
            guard session.canAddOutput(audioOutput) else {
                session.removeInput(input)
                session.commitConfiguration()
                throw NativeAudioCaptureError.addOutputFailed
            }
            session.addOutput(audioOutput)
            if session.canAddOutput(meterOutput) {
                meterOutput.setSampleBufferDelegate(self, queue: queue)
                session.addOutput(meterOutput)
            } else {
                onLevel?(0, "Mic recording; live meter unavailable")
            }
            session.commitConfiguration()
        } catch {
            await stopSessionAndClearGraph()
            throw error
        }

        lastLevelEmissionTime = 0
        await startSession()
        guard session.isRunning else {
            await stopSessionAndClearGraph()
            throw NativeAudioCaptureError.startFailed("AVCaptureSession did not enter the running state.")
        }

        try await withCheckedThrowingContinuation { continuation in
            continuationState.setStart(continuation)
            audioOutput.startRecording(to: outputURL, outputFileType: .m4a, recordingDelegate: self)
            if audioOutput.isRecording {
                continuationState.finishStart(.success(()))
            }
            queue.asyncAfter(deadline: .now() + 2) { [weak self, continuationState] in
                guard let self else { return }
                let result: Result<Void, Error> = self.audioOutput.isRecording
                    ? .success(())
                    : .failure(NativeAudioCaptureError.startFailed("AVCaptureAudioFileOutput did not report recording start within 2 seconds."))
                continuationState.finishStart(result)
            }
        }
        guard audioOutput.isRecording else {
            await stopSessionAndClearGraph()
            throw NativeAudioCaptureError.startFailed("AVCaptureAudioFileOutput did not enter the recording state.")
        }
        onLevel?(0, "Recording mic input")
    }

    @MainActor
    func stop() async throws {
        var stopError: Error?
        if audioOutput.isRecording {
            do {
                try await withCheckedThrowingContinuation { continuation in
                    continuationState.setStop(continuation)
                    audioOutput.stopRecording()
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
            throw NativeAudioCaptureError.stopFailed(terminalError.localizedDescription)
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
            let captureError = NativeAudioCaptureError.stopFailed(error.localizedDescription)
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
        let now = CFAbsoluteTimeGetCurrent()
        guard now - lastLevelEmissionTime >= Self.levelEmissionInterval else { return }
        lastLevelEmissionTime = now

        let level = AudioSampleLevel.normalizedLevel(from: sampleBuffer)
        Task { @MainActor [onLevel] in
            onLevel?(level, "Recording mic input")
        }
    }

    private func selectAudioDevice(uniqueID: String?, name: String) -> AVCaptureDevice? {
        AVCaptureDeviceIdentityResolver.audioDevice(
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
        meterOutput.setSampleBufferDelegate(nil, queue: nil)
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
            throw NativeAudioCaptureError.outputMissing(outputURL.lastPathComponent)
        }
        let attributes = try FileManager.default.attributesOfItem(atPath: outputURL.path)
        let bytes = (attributes[.size] as? NSNumber)?.int64Value ?? 0
        guard bytes > 0 else {
            throw NativeAudioCaptureError.outputEmpty(outputURL.lastPathComponent)
        }
    }
}
