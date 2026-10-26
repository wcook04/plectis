import Foundation
import Testing
@testable import DemoTakeConsoleApp

struct MicrophonePreferenceResolverTests {
    @Test
    func uniqueIDWinsOverNameAndLegacyIndex() {
        let saved = MicrophonePreference(uniqueID: "stable-blue", name: "Blue Snowball", index: 7)
        let staleName = CaptureDevice(id: "audio-7-blackhole", index: 7, name: "Blue Snowball", kind: .audio, uniqueID: "wrong")
        let stable = CaptureDevice(id: "audio-2-blue", index: 2, name: "Blue Snowball", kind: .audio, uniqueID: "stable-blue")

        let resolved = MicrophonePreferenceResolver.resolve(saved, in: [staleName, stable])

        #expect(resolved == stable)
    }

    @Test
    func nameMigratesLegacyConfigBeforeIndexFallback() {
        let saved = MicrophonePreference(uniqueID: nil, name: "Blue Snowball", index: 3)
        let indexCollision = CaptureDevice(id: "audio-3-blackhole", index: 3, name: "BlackHole 2ch", kind: .audio, uniqueID: "blackhole")
        let named = CaptureDevice(id: "audio-8-blue", index: 8, name: "Blue Snowball", kind: .audio, uniqueID: "blue")

        let resolved = MicrophonePreferenceResolver.resolve(saved, in: [indexCollision, named])

        #expect(resolved == named)
    }

    @Test
    func missingSavedMicrophoneDoesNotFallbackToFirstDevice() {
        let saved = MicrophonePreference(uniqueID: "missing", name: "Blue Snowball", index: 9)
        let available = CaptureDevice(id: "audio-0-macbook", index: 0, name: "MacBook Microphone", kind: .audio, uniqueID: "macbook")

        let resolved = MicrophonePreferenceResolver.resolve(saved, in: [available])

        #expect(resolved == nil)
    }
}
