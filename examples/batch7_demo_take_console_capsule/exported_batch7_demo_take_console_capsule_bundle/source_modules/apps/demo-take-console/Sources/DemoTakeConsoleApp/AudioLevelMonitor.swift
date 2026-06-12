@preconcurrency import AVFoundation
import Foundation

final class AudioLevelMonitor: NSObject, AVCaptureAudioDataOutputSampleBufferDelegate, @unchecked Sendable {
    private let session = AVCaptureSession()
    private let queue = DispatchQueue(label: "ai.workflow.demo-take-console.audio-meter")
    private var onLevel: ((Float, String) -> Void)?

    func start(
        preferredDeviceName: String?,
        preferredDeviceUniqueID: String?,
        onLevel: @escaping (Float, String) -> Void
    ) {
        stop()
        self.onLevel = onLevel

        guard AVCaptureDevice.authorizationStatus(for: .audio) == .authorized else {
            onLevel(0, "Needs microphone permission")
            return
        }
        guard let device = selectAudioDevice(uniqueID: preferredDeviceUniqueID, name: preferredDeviceName) else {
            onLevel(0, "No microphone available")
            return
        }

        do {
            let input = try AVCaptureDeviceInput(device: device)
            let output = AVCaptureAudioDataOutput()
            output.setSampleBufferDelegate(self, queue: queue)

            session.beginConfiguration()
            session.inputs.forEach { session.removeInput($0) }
            session.outputs.forEach { session.removeOutput($0) }
            if session.canAddInput(input) {
                session.addInput(input)
            }
            if session.canAddOutput(output) {
                session.addOutput(output)
            }
            session.commitConfiguration()

            queue.async { [session] in
                session.startRunning()
            }
            onLevel(0, "Input active")
        } catch {
            onLevel(0, "Meter unavailable: \(error.localizedDescription)")
        }
    }

    func stop() {
        if session.isRunning {
            session.stopRunning()
        }
        session.beginConfiguration()
        session.inputs.forEach { session.removeInput($0) }
        session.outputs.forEach { session.removeOutput($0) }
        session.commitConfiguration()
        onLevel = nil
    }

    nonisolated func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        let level = Self.normalizedLevel(from: sampleBuffer)
        DispatchQueue.main.async { [weak self] in
            self?.onLevel?(level, "Input active")
        }
    }

    private func selectAudioDevice(uniqueID: String?, name: String?) -> AVCaptureDevice? {
        let hasSpecificDevice = [uniqueID, name].contains { value in
            value?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false
        }
        return AVCaptureDeviceIdentityResolver.audioDevice(
            uniqueID: uniqueID,
            name: name,
            allowFallback: !hasSpecificDevice
        )
    }

    private static func normalizedLevel(from sampleBuffer: CMSampleBuffer) -> Float {
        guard let format = CMSampleBufferGetFormatDescription(sampleBuffer),
              let streamDescription = CMAudioFormatDescriptionGetStreamBasicDescription(format)
        else {
            return 0
        }

        var blockBuffer: CMBlockBuffer?
        var audioBufferList = AudioBufferList()
        let status = CMSampleBufferGetAudioBufferListWithRetainedBlockBuffer(
            sampleBuffer,
            bufferListSizeNeededOut: nil,
            bufferListOut: &audioBufferList,
            bufferListSize: MemoryLayout<AudioBufferList>.size,
            blockBufferAllocator: nil,
            blockBufferMemoryAllocator: nil,
            flags: 0,
            blockBufferOut: &blockBuffer
        )
        guard status == noErr else { return 0 }

        let buffers = UnsafeMutableAudioBufferListPointer(&audioBufferList)
        var sum: Float = 0
        var sampleCount: Int = 0
        let flags = streamDescription.pointee.mFormatFlags
        let bytesPerFrame = Int(streamDescription.pointee.mBytesPerFrame)

        for buffer in buffers {
            guard let data = buffer.mData, bytesPerFrame > 0 else { continue }
            let byteCount = Int(buffer.mDataByteSize)
            if flags & kAudioFormatFlagIsFloat != 0 {
                let count = byteCount / MemoryLayout<Float>.size
                let samples = data.assumingMemoryBound(to: Float.self)
                for index in 0..<count {
                    let value = samples[index]
                    sum += value * value
                }
                sampleCount += count
            } else {
                let count = byteCount / MemoryLayout<Int16>.size
                let samples = data.assumingMemoryBound(to: Int16.self)
                for index in 0..<count {
                    let value = Float(samples[index]) / Float(Int16.max)
                    sum += value * value
                }
                sampleCount += count
            }
        }

        guard sampleCount > 0 else { return 0 }
        let rms = sqrt(sum / Float(sampleCount))
        return min(max(rms * 8, 0), 1)
    }
}
