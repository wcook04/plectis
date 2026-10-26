import Foundation
import Testing
@testable import DemoTakeConsoleApp

@MainActor
struct MicrophoneMonitorTests {
    @Test
    func refreshMicrophoneMonitorStartsLiveMeterForSelectedMic() async throws {
        let microphone = CaptureDevice(
            id: "audio-2-blue",
            index: 2,
            name: "Blue Snowball",
            kind: .audio,
            uniqueID: "blue-snowball-uid"
        )
        let monitor = FakeAudioLevelMonitor(levelToEmit: 0.42)
        let store = RecorderStore(
            audioLevelMonitor: monitor,
            microphonePermissionStatus: { .ready },
            audioDeviceAvailability: { _ in true }
        )
        store.devices = DeviceInventory(audioDevices: [microphone])
        store.selectedAudioID = microphone.id
        store.microphoneLevel = 0.9
        store.microphoneMeterStatus = "Old status"

        store.refreshMicrophoneMonitor()
        await Task.yield()

        #expect(monitor.startCallCount == 1)
        #expect(monitor.lastPreferredDeviceName == "Blue Snowball")
        #expect(monitor.lastPreferredDeviceUniqueID == "blue-snowball-uid")
        #expect(store.microphoneLevel == 0.42)
        #expect(store.microphoneMeterStatus == "Input active")
    }

    @Test
    func selectingMicrophoneDoesNotAutoStartLiveMeter() {
        let microphone = CaptureDevice(
            id: "audio-2-blue",
            index: 2,
            name: "Blue Snowball",
            kind: .audio,
            uniqueID: "blue-snowball-uid"
        )
        let monitor = FakeAudioLevelMonitor(levelToEmit: 0.42)
        let store = RecorderStore(
            audioLevelMonitor: monitor,
            microphonePermissionStatus: { .ready },
            audioDeviceAvailability: { _ in true }
        )
        store.permissions.microphone = .ready
        store.devices = DeviceInventory(audioDevices: [microphone])

        store.selectAudio(microphone.id)

        #expect(monitor.startCallCount == 0)
        #expect(monitor.stopCallCount == 1)
        #expect(store.microphoneLevel == 0)
        #expect(store.microphoneMeterStatus.contains("Use Mic check"))
    }

    @Test
    func refreshMicrophoneMonitorStopsMeterWhenPermissionIsMissing() {
        let microphone = CaptureDevice(id: "audio-1-usb", index: 1, name: "USB Mic", kind: .audio)
        let monitor = FakeAudioLevelMonitor()
        let store = RecorderStore(
            audioLevelMonitor: monitor,
            microphonePermissionStatus: { .missing },
            audioDeviceAvailability: { _ in true }
        )
        store.devices = DeviceInventory(audioDevices: [microphone])
        store.selectedAudioID = microphone.id
        store.microphoneLevel = 0.5

        store.refreshMicrophoneMonitor()

        #expect(monitor.startCallCount == 0)
        #expect(monitor.stopCallCount == 1)
        #expect(store.microphoneLevel == 0)
        #expect(store.microphoneMeterStatus.contains("permission needed"))
    }

    @Test
    func refreshMicrophoneMonitorStopsMeterWhenSelectedMicIsUnavailable() {
        let microphone = CaptureDevice(id: "audio-2-blue", index: 2, name: "Blue Snowball", kind: .audio)
        let monitor = FakeAudioLevelMonitor()
        let store = RecorderStore(
            audioLevelMonitor: monitor,
            microphonePermissionStatus: { .ready },
            audioDeviceAvailability: { _ in false }
        )
        store.devices = DeviceInventory(audioDevices: [microphone])
        store.selectedAudioID = microphone.id
        store.microphoneLevel = 0.5

        store.refreshMicrophoneMonitor()

        #expect(monitor.startCallCount == 0)
        #expect(monitor.stopCallCount == 1)
        #expect(store.microphoneLevel == 0)
        #expect(store.microphoneMeterStatus.contains("not visible to macOS"))
        #expect(store.microphoneSourceStatus == .missing)
        #expect(store.startBlockers.contains { $0.contains("Blue Snowball") && $0.contains("not visible") })
    }
}

private final class FakeAudioLevelMonitor: AudioLevelMonitoring {
    private let levelToEmit: Float?
    private(set) var startCallCount = 0
    private(set) var stopCallCount = 0
    private(set) var lastPreferredDeviceName: String?
    private(set) var lastPreferredDeviceUniqueID: String?

    init(levelToEmit: Float? = nil) {
        self.levelToEmit = levelToEmit
    }

    func start(
        preferredDeviceName: String?,
        preferredDeviceUniqueID: String?,
        onLevel: @escaping (Float, String) -> Void
    ) {
        startCallCount += 1
        lastPreferredDeviceName = preferredDeviceName
        lastPreferredDeviceUniqueID = preferredDeviceUniqueID
        if let levelToEmit {
            onLevel(levelToEmit, "Input active")
        }
    }

    func stop() {
        stopCallCount += 1
    }
}
