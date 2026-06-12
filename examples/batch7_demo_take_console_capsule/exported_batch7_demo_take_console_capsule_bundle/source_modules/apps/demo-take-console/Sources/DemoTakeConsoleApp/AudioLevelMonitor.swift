@preconcurrency import AVFoundation
import Foundation

protocol AudioLevelMonitoring: AnyObject {
    func start(
        preferredDeviceName: String?,
        preferredDeviceUniqueID: String?,
        onLevel: @escaping (Float, String) -> Void
    )
    func stop()
}

final class AudioLevelMonitor: NSObject, AudioLevelMonitoring, AVCaptureAudioDataOutputSampleBufferDelegate, @unchecked Sendable {
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
            if let preferredDeviceName, !preferredDeviceName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                onLevel(0, "\(preferredDeviceName) is not visible to macOS")
            } else {
                onLevel(0, "No microphone available")
            }
            return
        }

        do {
            let input = try AVCaptureDeviceInput(device: device)
            let output = AVCaptureAudioDataOutput()
            output.setSampleBufferDelegate(self, queue: queue)

            session.beginConfiguration()
            session.inputs.forEach { session.removeInput($0) }
            session.outputs.forEach { session.removeOutput($0) }
            guard session.canAddInput(input) else {
                session.commitConfiguration()
                onLevel(0, "Meter unavailable: \(device.localizedName) cannot be attached")
                return
            }
            session.addInput(input)
            guard session.canAddOutput(output) else {
                session.removeInput(input)
                session.commitConfiguration()
                onLevel(0, "Meter unavailable: audio samples cannot be read")
                return
            }
            session.addOutput(output)
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
        let level = AudioSampleLevel.normalizedLevel(from: sampleBuffer)
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
}

enum AudioSampleLevel {
    static func normalizedLevel(from sampleBuffer: CMSampleBuffer) -> Float {
        guard let format = CMSampleBufferGetFormatDescription(sampleBuffer),
              let streamDescription = CMAudioFormatDescriptionGetStreamBasicDescription(format)
        else {
            return 0
        }

        var blockBuffer: CMBlockBuffer?
        var bufferListSize = 0
        var status = CMSampleBufferGetAudioBufferListWithRetainedBlockBuffer(
            sampleBuffer,
            bufferListSizeNeededOut: &bufferListSize,
            bufferListOut: nil,
            bufferListSize: 0,
            blockBufferAllocator: nil,
            blockBufferMemoryAllocator: nil,
            flags: 0,
            blockBufferOut: &blockBuffer
        )
        guard status == noErr, bufferListSize > 0 else { return 0 }

        let rawBufferList = UnsafeMutableRawPointer.allocate(
            byteCount: bufferListSize,
            alignment: MemoryLayout<AudioBufferList>.alignment
        )
        defer { rawBufferList.deallocate() }
        let audioBufferList = rawBufferList.bindMemory(to: AudioBufferList.self, capacity: 1)

        status = CMSampleBufferGetAudioBufferListWithRetainedBlockBuffer(
            sampleBuffer,
            bufferListSizeNeededOut: &bufferListSize,
            bufferListOut: audioBufferList,
            bufferListSize: bufferListSize,
            blockBufferAllocator: nil,
            blockBufferMemoryAllocator: nil,
            flags: 0,
            blockBufferOut: &blockBuffer
        )
        guard status == noErr else { return 0 }

        let buffers = UnsafeMutableAudioBufferListPointer(audioBufferList)
        var sum: Float = 0
        var sampleCount: Int = 0
        let flags = streamDescription.pointee.mFormatFlags
        let bitsPerChannel = Int(streamDescription.pointee.mBitsPerChannel)

        for buffer in buffers {
            guard let data = buffer.mData else { continue }
            let byteCount = Int(buffer.mDataByteSize)
            if flags & kAudioFormatFlagIsFloat != 0 {
                let partial = floatSum(data: data, byteCount: byteCount, bitsPerChannel: bitsPerChannel)
                sum += partial.sum
                sampleCount += partial.count
            } else if flags & kAudioFormatFlagIsSignedInteger != 0 {
                let partial = signedIntegerSum(data: data, byteCount: byteCount, bitsPerChannel: bitsPerChannel)
                sum += partial.sum
                sampleCount += partial.count
            } else {
                let partial = unsignedIntegerSum(data: data, byteCount: byteCount, bitsPerChannel: bitsPerChannel)
                sum += partial.sum
                sampleCount += partial.count
            }
        }

        guard sampleCount > 0 else { return 0 }
        let rms = sqrt(sum / Float(sampleCount))
        return min(max(rms * 8, 0), 1)
    }

    private static func floatSum(data: UnsafeMutableRawPointer, byteCount: Int, bitsPerChannel: Int) -> (sum: Float, count: Int) {
        if bitsPerChannel == 64 {
            let count = byteCount / MemoryLayout<Double>.size
            let samples = data.assumingMemoryBound(to: Double.self)
            var sum: Float = 0
            for index in 0..<count {
                let value = Float(samples[index])
                sum += value * value
            }
            return (sum, count)
        }

        let count = byteCount / MemoryLayout<Float>.size
        let samples = data.assumingMemoryBound(to: Float.self)
        var sum: Float = 0
        for index in 0..<count {
            let value = samples[index]
            sum += value * value
        }
        return (sum, count)
    }

    private static func signedIntegerSum(data: UnsafeMutableRawPointer, byteCount: Int, bitsPerChannel: Int) -> (sum: Float, count: Int) {
        if bitsPerChannel == 32 {
            let count = byteCount / MemoryLayout<Int32>.size
            let samples = data.assumingMemoryBound(to: Int32.self)
            var sum: Float = 0
            for index in 0..<count {
                let value = Float(samples[index]) / Float(Int32.max)
                sum += value * value
            }
            return (sum, count)
        }

        let count = byteCount / MemoryLayout<Int16>.size
        let samples = data.assumingMemoryBound(to: Int16.self)
        var sum: Float = 0
        for index in 0..<count {
            let value = Float(samples[index]) / Float(Int16.max)
            sum += value * value
        }
        return (sum, count)
    }

    private static func unsignedIntegerSum(data: UnsafeMutableRawPointer, byteCount: Int, bitsPerChannel: Int) -> (sum: Float, count: Int) {
        if bitsPerChannel == 8 {
            let count = byteCount / MemoryLayout<UInt8>.size
            let samples = data.assumingMemoryBound(to: UInt8.self)
            var sum: Float = 0
            for index in 0..<count {
                let value = (Float(samples[index]) - 128) / 128
                sum += value * value
            }
            return (sum, count)
        }

        let count = byteCount / MemoryLayout<UInt16>.size
        let samples = data.assumingMemoryBound(to: UInt16.self)
        var sum: Float = 0
        for index in 0..<count {
            let value = (Float(samples[index]) - 32_768) / 32_768
            sum += value * value
        }
        return (sum, count)
    }
}
