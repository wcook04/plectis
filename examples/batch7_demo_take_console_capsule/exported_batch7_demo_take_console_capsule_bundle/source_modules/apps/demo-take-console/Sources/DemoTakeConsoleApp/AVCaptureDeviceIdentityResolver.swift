@preconcurrency import AVFoundation
import Foundation

enum AVCaptureDeviceIdentityResolver {
    static func enrichInventory(_ inventory: DeviceInventory) -> DeviceInventory {
        DeviceInventory(
            videoDevices: inventory.videoDevices,
            audioDevices: enrichAudioDevices(inventory.audioDevices)
        )
    }

    static func enrichAudioDevices(_ captureDevices: [CaptureDevice]) -> [CaptureDevice] {
        let avDevices = audioDevices()
        var claimedUniqueIDs: Set<String> = []
        return captureDevices.map { captureDevice in
            guard captureDevice.kind == .audio, captureDevice.uniqueID == nil else {
                if let uniqueID = captureDevice.uniqueID {
                    claimedUniqueIDs.insert(uniqueID)
                }
                return captureDevice
            }
            guard let match = bestMatch(
                in: avDevices,
                name: captureDevice.name,
                claimedUniqueIDs: claimedUniqueIDs,
                allowFallback: false
            ) else {
                return captureDevice
            }
            claimedUniqueIDs.insert(match.uniqueID)
            return CaptureDevice(
                id: captureDevice.id,
                index: captureDevice.index,
                name: captureDevice.name,
                kind: captureDevice.kind,
                uniqueID: match.uniqueID
            )
        }
    }

    static func audioDevice(uniqueID: String?, name: String?, allowFallback: Bool) -> AVCaptureDevice? {
        let avDevices = audioDevices()
        if let uniqueID = clean(uniqueID),
           let match = avDevices.first(where: { $0.uniqueID == uniqueID }) {
            return match
        }
        if let name = clean(name) {
            return bestMatch(in: avDevices, name: name, claimedUniqueIDs: [], allowFallback: false)
        }
        return allowFallback ? avDevices.first : nil
    }

    static func videoDevice(uniqueID: String?, name: String?, allowFallback: Bool) -> AVCaptureDevice? {
        let avDevices = videoDevices()
        if let uniqueID = clean(uniqueID),
           let match = avDevices.first(where: { $0.uniqueID == uniqueID }) {
            return match
        }
        if let name = clean(name) {
            return bestMatch(in: avDevices, name: name, claimedUniqueIDs: [], allowFallback: false)
        }
        return allowFallback ? avDevices.first : nil
    }

    static func isAudioDeviceAvailable(_ captureDevice: CaptureDevice) -> Bool {
        audioDevice(
            uniqueID: captureDevice.uniqueID,
            name: captureDevice.name,
            allowFallback: false
        ) != nil
    }

    static func isVideoDeviceAvailable(_ captureDevice: CaptureDevice) -> Bool {
        videoDevice(
            uniqueID: captureDevice.uniqueID,
            name: captureDevice.name,
            allowFallback: false
        ) != nil
    }

    private static func audioDevices() -> [AVCaptureDevice] {
        AVCaptureDevice.DiscoverySession(
            deviceTypes: [.microphone, .external],
            mediaType: .audio,
            position: .unspecified
        ).devices
    }

    private static func videoDevices() -> [AVCaptureDevice] {
        AVCaptureDevice.DiscoverySession(
            deviceTypes: [.builtInWideAngleCamera, .external],
            mediaType: .video,
            position: .unspecified
        ).devices
    }

    private static func bestMatch(
        in avDevices: [AVCaptureDevice],
        name: String,
        claimedUniqueIDs: Set<String>,
        allowFallback: Bool
    ) -> AVCaptureDevice? {
        let available = avDevices.filter { !claimedUniqueIDs.contains($0.uniqueID) }
        if let exact = available.first(where: { $0.localizedName == name }) {
            return exact
        }
        if let caseInsensitive = available.first(where: { $0.localizedName.compare(name, options: [.caseInsensitive]) == .orderedSame }) {
            return caseInsensitive
        }
        if let contains = available.first(where: {
            $0.localizedName.localizedCaseInsensitiveContains(name)
                || name.localizedCaseInsensitiveContains($0.localizedName)
        }) {
            return contains
        }
        return allowFallback ? available.first : nil
    }

    private static func clean(_ value: String?) -> String? {
        let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return trimmed.isEmpty ? nil : trimmed
    }
}
