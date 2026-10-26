import Foundation
import Testing
@testable import DemoTakeConsoleApp

@MainActor
struct RecordingStartPolicyTests {
    @Test
    func screenRecordingRequestIsOneShotUntilPreflightPasses() async throws {
        var requestCallCount = 0
        var screenStatus = CapabilityStatus.missing
        let store = RecorderStore(
            screenCaptureStatus: { screenStatus },
            requestScreenCaptureAccess: {
                requestCallCount += 1
                return .missing
            }
        )
        store.permissions.screenCapture = .missing

        await store.requestScreenRecordingPermission()
        await store.requestScreenRecordingPermission()

        #expect(requestCallCount == 1)
        #expect(store.statusLines.contains { $0.contains("already sent") && $0.contains("another macOS prompt") })

        screenStatus = .ready
        await store.recheckScreenRecordingPermission()
        await store.requestScreenRecordingPermission()

        #expect(requestCallCount == 1)
        #expect(store.permissions.screenCapture == .ready)
        #expect(store.statusLines.contains { $0.contains("already passes preflight") })
    }

    @Test
    func startBlockersUseCachedAudioAvailability() async throws {
        let screen = CaptureDevice(id: "screen-5", index: 5, name: "Capture screen 1", kind: .video)
        let microphone = CaptureDevice(id: "audio-3", index: 3, name: "USB Mic", kind: .audio, uniqueID: "mic-uid")
        var availabilityCallCount = 0
        let store = RecorderStore(
            screenCaptureStatus: { .ready },
            microphonePermissionStatus: { .ready },
            audioDeviceAvailability: { _ in
                availabilityCallCount += 1
                return false
            }
        )
        store.ffmpegPath = "/usr/bin/false"
        store.permissions.screenCapture = .ready
        store.permissions.microphone = .ready
        store.devices = DeviceInventory(videoDevices: [screen], audioDevices: [microphone])
        store.selectedScreenIDs = [screen.id]

        store.selectAudio(microphone.id)
        let callsAfterSelection = availabilityCallCount

        for _ in 0..<20 {
            _ = store.startBlockers
        }

        #expect(callsAfterSelection == 1)
        #expect(availabilityCallCount == callsAfterSelection)
        #expect(store.startBlockers.contains { $0.contains("is not visible") })
    }

    @Test
    func startConfigDefaultsToVerifiedReviewArchive() throws {
        let screen = CaptureDevice(id: "screen-5", index: 5, name: "Capture screen 1", kind: .video)

        let config = CaptureHelperClient.startConfigPayload(
            ffmpegPath: "/usr/bin/false",
            screens: [screen],
            microphone: nil,
            webcam: nil,
            screenshotInterval: 5,
            transcribeBinary: nil,
            transcribeModel: "openai_whisper-base",
            takeTitle: "  Custody test  ",
            captureBackend: "screencapturekit"
        )

        #expect(config["capture_backend"] as? String == "screencapturekit")
        #expect(config["cloud_archive_after_stop"] as? Bool == true)
        #expect(config["cloud_archive_local_retention"] as? String == "review")
        #expect(config["cloud_archive_remote"] as? String == "memeister_drive:aiw-cold-spillway/demo_takes")
        #expect(config["take_title"] as? String == "Custody test")
    }

    @Test
    func webcamToggleSurvivesInitialPreflightWithStaleSavedConfig() async throws {
        let screen = CaptureDevice(id: "screen-1", index: 1, name: "Capture screen 1", kind: .video)
        let webcam = CaptureDevice(id: "camera-8", index: 8, name: "FaceTime HD Camera", kind: .video)
        let paths = try makeTemporaryConfigPaths()
        try writeRecorderConfigPayload(
            ["webcam_enabled": false, "selected_webcam_index": 99],
            to: paths.config
        )
        let store = RecorderStore(
            screenCaptureStatus: { .ready },
            microphonePermissionStatus: { .ready },
            deviceInventoryCacheURL: paths.inventory,
            recorderConfigURL: paths.config
        )
        store.devices = DeviceInventory(videoDevices: [screen, webcam], audioDevices: [])
        store.selectedScreenIDs = [screen.id]

        store.selectWebcam(webcam.id)
        store.setWebcamEnabled(true)
        try writeRecorderConfigPayload(
            ["webcam_enabled": false, "selected_webcam_index": 99],
            to: paths.config
        )

        await store.refreshPreflight(probeDevices: false)

        #expect(store.webcamEnabled)
        #expect(store.selectedWebcamID == webcam.id)
        #expect(store.selectedWebcam?.id == webcam.id)
    }

    @Test
    func webcamEnabledWithoutSelectedCameraBlocksStart() async throws {
        let screen = CaptureDevice(id: "screen-1", index: 1, name: "Capture screen 1", kind: .video)
        let paths = try makeTemporaryConfigPaths()
        let store = RecorderStore(
            screenCaptureStatus: { .ready },
            microphonePermissionStatus: { .ready },
            deviceInventoryCacheURL: paths.inventory,
            recorderConfigURL: paths.config
        )
        store.ffmpegPath = "/usr/bin/false"
        store.permissions.screenCapture = .ready
        store.permissions.camera = .ready
        store.devices = DeviceInventory(videoDevices: [screen], audioDevices: [])
        store.selectedScreenIDs = [screen.id]
        store.webcamEnabled = true
        store.selectedWebcamID = nil

        #expect(store.cameraSourceStatus == .missing)
        #expect(store.startBlockers.contains("Select a camera or turn camera off"))
        #expect(!store.canStart)
    }

    @Test
    func audioOnlySelectionDoesNotRequireDisplayOrScreenPermission() async throws {
        let microphone = CaptureDevice(id: "audio-3", index: 3, name: "USB Mic", kind: .audio, uniqueID: "mic-uid")
        let store = RecorderStore(
            screenCaptureStatus: { .missing },
            microphonePermissionStatus: { .ready },
            audioDeviceAvailability: { _ in true }
        )
        store.ffmpegPath = "/usr/bin/false"
        store.permissions.screenCapture = .missing
        store.permissions.microphone = .ready
        store.devices = DeviceInventory(videoDevices: [], audioDevices: [microphone])
        store.selectedScreenIDs = []
        store.selectedAudioID = microphone.id
        store.webcamEnabled = false

        #expect(store.screenSourceStatus == .notRequired)
        #expect(!store.needsScreenCapturePermission)
        #expect(store.startBlockers.isEmpty)
        #expect(store.canStart)
        #expect(store.setupDetail.contains("microphone audio only"))
        #expect(!store.startBlockers.contains("Select at least one display"))
        #expect(!store.startBlockers.contains("macOS Screen Recording preflight denied this app"))
    }

    @Test
    func persistedEmptyDisplaySelectionSurvivesPreflightForAudioOnly() async throws {
        let screen = CaptureDevice(id: "screen-1", index: 1, name: "Capture screen 1", kind: .video)
        let microphone = CaptureDevice(id: "audio-3", index: 3, name: "USB Mic", kind: .audio, uniqueID: "mic-uid")
        let paths = try makeTemporaryConfigPaths()
        try writeRecorderConfigPayload(
            [
                "selected_display_indexes": [] as [Int],
                "selected_microphone_index": microphone.index,
                "selected_microphone_name": microphone.name,
                "selected_microphone_unique_id": "mic-uid",
                "webcam_enabled": false,
            ],
            to: paths.config
        )
        let store = RecorderStore(
            screenCaptureStatus: { .missing },
            microphonePermissionStatus: { .ready },
            audioDeviceAvailability: { _ in true },
            deviceInventoryCacheURL: paths.inventory,
            recorderConfigURL: paths.config
        )
        store.devices = DeviceInventory(videoDevices: [screen], audioDevices: [microphone])

        await store.refreshPreflight(probeDevices: false)
        store.ffmpegPath = "/usr/bin/false"

        #expect(store.selectedScreens.isEmpty)
        #expect(store.selectedAudio?.id == microphone.id)
        #expect(store.screenSourceStatus == .notRequired)
        #expect(!store.needsScreenCapturePermission)
        #expect(store.startBlockers.isEmpty)
        #expect(store.canStart)
    }

    @Test
    func preCountdownStartBlockerWritesDurableAttempt() async throws {
        let screen = CaptureDevice(id: "screen-1", index: 1, name: "Capture screen 1", kind: .video)
        let paths = try makeTemporaryConfigPaths()
        let store = RecorderStore(
            screenCaptureStatus: { .missing },
            deviceInventoryCacheURL: paths.inventory,
            recorderConfigURL: paths.config
        )
        store.devices = DeviceInventory(videoDevices: [screen], audioDevices: [])
        store.selectedScreenIDs = [screen.id]

        await store.startRecording()

        let prestartURL = paths.config
            .deletingLastPathComponent()
            .appendingPathComponent("demo_take_prestart_attempts.jsonl")
        let log = try String(contentsOf: prestartURL, encoding: .utf8)
        #expect(log.contains("\"schema\":\"demo_take_prestart_attempt_event_v0\""))
        #expect(log.contains("\"event\":\"screen_capture_permission_blocked\""))
        #expect(log.contains("Screen Recording preflight"))
        #expect(store.lastStartFailureLine?.contains("Start blocked") == true)
        #expect(store.statusLines.contains { $0.contains("Start blocked") })
    }

    @Test
    func displaySelectionPersistsToSharedRecorderConfig() throws {
        let first = CaptureDevice(id: "screen-1", index: 1, name: "Capture screen 1", kind: .video)
        let second = CaptureDevice(id: "screen-2", index: 2, name: "Capture screen 2", kind: .video)
        let paths = try makeTemporaryConfigPaths()
        let store = RecorderStore(
            deviceInventoryCacheURL: paths.inventory,
            recorderConfigURL: paths.config
        )
        store.devices = DeviceInventory(videoDevices: [first, second], audioDevices: [])

        store.setScreen(second, enabled: true)

        let data = try Data(contentsOf: paths.config)
        let payload = try #require(try JSONSerialization.jsonObject(with: data) as? [String: Any])
        #expect(payload["selected_display_indexes"] as? [Int] == [2])

        store.setScreen(second, enabled: false)

        let clearedData = try Data(contentsOf: paths.config)
        let clearedPayload = try #require(try JSONSerialization.jsonObject(with: clearedData) as? [String: Any])
        #expect(clearedPayload["selected_display_indexes"] as? [Int] == [])
    }

    @Test
    func displaySelectionIsSingleTarget() async throws {
        let first = CaptureDevice(id: "screen-1", index: 1, name: "Capture screen 1", kind: .video)
        let second = CaptureDevice(id: "screen-2", index: 2, name: "Capture screen 2", kind: .video)
        let store = RecorderStore()
        store.devices = DeviceInventory(videoDevices: [first, second], audioDevices: [])

        store.setScreen(first, enabled: true)
        #expect(store.selectedScreens.map(\.id) == [first.id])

        store.setScreen(second, enabled: true)
        #expect(store.selectedScreenIDs == [second.id])
        #expect(store.selectedScreens.map(\.id) == [second.id])

        store.setScreen(second, enabled: false)
        #expect(store.selectedScreens.isEmpty)
    }

    @Test
    func nativeStartUsesOnlyOneDisplayFromStaleMultiSelection() async throws {
        let first = CaptureDevice(id: "screen-1", index: 1, name: "Capture screen 1", kind: .video)
        let second = CaptureDevice(id: "screen-2", index: 2, name: "Capture screen 2", kind: .video)
        let screenManager = FakeScreenCaptureManager()
        let store = RecorderStore(nativeScreenCaptureManager: screenManager)
        store.devices = DeviceInventory(videoDevices: [first, second], audioDevices: [])
        store.selectedScreenIDs = [first.id, second.id]

        let takeURL = try makeTemporaryTakeRoot()
        try await store.completeNativeStartAfterHelper(
            takeURL: takeURL,
            takeID: "take_test_single_display",
            title: "Single display",
            helperStatusLines: []
        )

        #expect(screenManager.startScreenIndexes == [[1]])

        let sessionData = try Data(contentsOf: takeURL.appendingPathComponent("session.json"))
        let session = try #require(try JSONSerialization.jsonObject(with: sessionData) as? [String: Any])
        let tracks = try #require(session["tracks"] as? [[String: Any]])
        let relativePaths = Set(tracks.compactMap { $0["relative_path"] as? String })
        #expect(relativePaths.contains("tracks/screen_1.mp4"))
        #expect(!relativePaths.contains("tracks/screen_2.mp4"))
    }

    @Test
    func audioOnlyNativeStartSkipsScreenCaptureAndWritesMicrophoneTrack() async throws {
        let microphone = CaptureDevice(id: "audio-3", index: 3, name: "USB Mic", kind: .audio, uniqueID: "mic-uid")
        let screenManager = FakeScreenCaptureManager()
        let audioManager = FakeAudioCaptureManager()
        let store = RecorderStore(
            audioDeviceAvailability: { _ in true },
            nativeScreenCaptureManager: screenManager,
            nativeAudioCaptureManager: audioManager
        )
        store.devices = DeviceInventory(videoDevices: [], audioDevices: [microphone])
        store.selectedScreenIDs = []
        store.selectedAudioID = microphone.id

        let takeURL = try makeTemporaryTakeRoot()
        try await store.completeNativeStartAfterHelper(
            takeURL: takeURL,
            takeID: "take_test_audio_only",
            title: "Audio only",
            helperStatusLines: []
        )

        #expect(store.state == .recording)
        #expect(store.canStop)
        #expect(screenManager.startCallCount == 0)
        #expect(!screenManager.isRecording)
        #expect(audioManager.startCallCount == 1)
        #expect(audioManager.isRecording)

        let startAttemptLog = try String(
            contentsOf: takeURL.appendingPathComponent("start_attempt.jsonl"),
            encoding: .utf8
        )
        #expect(startAttemptLog.contains("\"event\":\"screen_start_skipped\""))
        #expect(startAttemptLog.contains("\"event\":\"audio_start_ok\""))
        #expect(startAttemptLog.contains("\"event\":\"state_recording_set\""))
        #expect(!startAttemptLog.contains("\"event\":\"screen_start_begin\""))

        let sessionData = try Data(contentsOf: takeURL.appendingPathComponent("session.json"))
        let session = try #require(try JSONSerialization.jsonObject(with: sessionData) as? [String: Any])
        let tracks = try #require(session["tracks"] as? [[String: Any]])
        let relativePaths = Set(tracks.compactMap { $0["relative_path"] as? String })
        #expect(relativePaths.contains("tracks/microphone.m4a"))
        #expect(!relativePaths.contains { $0.contains("screen_") })
    }

    @Test
    func screenStartSuccessAndAudioStartFailureStillCommitsRecording() async throws {
        let screen = CaptureDevice(id: "screen-5", index: 5, name: "Capture screen 1", kind: .video)
        let microphone = CaptureDevice(id: "audio-3", index: 3, name: "Broken Mic", kind: .audio)
        let screenManager = FakeScreenCaptureManager()
        let audioManager = FakeAudioCaptureManager(startError: FakeStartError.audio)
        let store = RecorderStore(
            audioDeviceAvailability: { _ in true },
            nativeScreenCaptureManager: screenManager,
            nativeAudioCaptureManager: audioManager
        )
        store.devices = DeviceInventory(videoDevices: [screen], audioDevices: [microphone])
        store.selectedScreenIDs = [screen.id]
        store.selectedAudioID = microphone.id

        let takeURL = try makeTemporaryTakeRoot()
        try await store.completeNativeStartAfterHelper(
            takeURL: takeURL,
            takeID: "take_test_audio_warning",
            title: "Audio warning",
            helperStatusLines: ["Helper package ready"]
        )

        #expect(store.state == .recording)
        #expect(store.canStop)
        #expect(screenManager.isRecording)
        #expect(audioManager.startCallCount == 1)
        #expect(store.statusLines.contains { $0.contains("Mic failed") && $0.contains("screen recording continues") })

        let startAttemptLog = try String(
            contentsOf: takeURL.appendingPathComponent("start_attempt.jsonl"),
            encoding: .utf8
        )
        #expect(startAttemptLog.contains("\"event\":\"state_recording_set\""))
        #expect(startAttemptLog.contains("\"event\":\"audio_start_failed\""))
        if let screenStart = startAttemptLog.range(of: "\"event\":\"screen_start_ok\""),
           let audioFailure = startAttemptLog.range(of: "\"event\":\"audio_start_failed\""),
           let stateCommit = startAttemptLog.range(of: "\"event\":\"state_recording_set\"") {
            #expect(screenStart.lowerBound < audioFailure.lowerBound)
            #expect(audioFailure.lowerBound < stateCommit.lowerBound)
        } else {
            Issue.record("Expected start attempt log to contain screen start, audio failure, and state commit events.")
        }

        let sessionData = try Data(contentsOf: takeURL.appendingPathComponent("session.json"))
        let session = try JSONSerialization.jsonObject(with: sessionData) as? [String: Any]
        let failures = session?["known_failures"] as? [String] ?? []
        #expect(failures.contains { $0.contains("Mic failed") && $0.contains("screen recording continues") })
    }

    @Test
    func screenStartFailureDoesNotCommitRecording() async throws {
        let screen = CaptureDevice(id: "screen-5", index: 5, name: "Capture screen 1", kind: .video)
        let screenManager = FakeScreenCaptureManager(startError: FakeStartError.screen)
        let audioManager = FakeAudioCaptureManager()
        let store = RecorderStore(
            audioDeviceAvailability: { _ in true },
            nativeScreenCaptureManager: screenManager,
            nativeAudioCaptureManager: audioManager
        )
        store.devices = DeviceInventory(videoDevices: [screen], audioDevices: [])
        store.selectedScreenIDs = [screen.id]

        let takeURL = try makeTemporaryTakeRoot()
        do {
            try await store.completeNativeStartAfterHelper(
                takeURL: takeURL,
                takeID: "take_test_screen_failure",
                title: "Screen failure",
                helperStatusLines: []
            )
            Issue.record("Expected screen start to fail.")
        } catch {
            #expect((error as? FakeStartError) == .screen)
        }

        #expect(store.state != .recording)
        #expect(!screenManager.isRecording)
        #expect(audioManager.startCallCount == 0)

        let startAttemptLog = try String(
            contentsOf: takeURL.appendingPathComponent("start_attempt.jsonl"),
            encoding: .utf8
        )
        #expect(startAttemptLog.contains("\"event\":\"screen_start_begin\""))
        #expect(!startAttemptLog.contains("\"event\":\"state_recording_set\""))
    }

    @Test
    func pauseResumeRotatesNativeWritersIntoMediaSegments() async throws {
        let screen = CaptureDevice(id: "screen-5", index: 5, name: "Capture screen 1", kind: .video)
        let webcam = CaptureDevice(id: "camera-8", index: 8, name: "FaceTime HD Camera", kind: .video, uniqueID: "camera-uid")
        let microphone = CaptureDevice(id: "audio-3", index: 3, name: "USB Mic", kind: .audio, uniqueID: "mic-uid")
        let screenManager = FakeScreenCaptureManager()
        let audioManager = FakeAudioCaptureManager()
        let cameraManager = FakeCameraCaptureManager()
        let store = RecorderStore(
            audioDeviceAvailability: { _ in true },
            nativeScreenCaptureManager: screenManager,
            nativeAudioCaptureManager: audioManager,
            nativeCameraCaptureManager: cameraManager
        )
        store.devices = DeviceInventory(videoDevices: [screen, webcam], audioDevices: [microphone])
        store.selectedScreenIDs = [screen.id]
        store.selectedAudioID = microphone.id
        store.webcamEnabled = true
        store.selectedWebcamID = webcam.id
        store.permissions.camera = .ready

        let takeURL = try makeTemporaryTakeRoot()
        try await store.completeNativeStartAfterHelper(
            takeURL: takeURL,
            takeID: "take_test_pause_resume",
            title: "Pause resume",
            helperStatusLines: []
        )

        await store.pauseRecording()
        #expect(store.state == .paused)
        #expect(!screenManager.isRecording)
        #expect(!audioManager.isRecording)
        #expect(!cameraManager.isRecording)
        #expect(screenManager.stopCallCount == 1)
        #expect(audioManager.stopCallCount == 1)
        #expect(cameraManager.stopCallCount == 1)

        await store.resumeRecording()
        #expect(store.state == .recording)
        #expect(screenManager.isRecording)
        #expect(audioManager.isRecording)
        #expect(cameraManager.isRecording)
        #expect(screenManager.startSegmentIndexes == [1, 2])
        #expect(audioManager.startSegmentIndexes == [1, 2])
        #expect(cameraManager.startSegmentIndexes == [1, 2])

        let sessionData = try Data(contentsOf: takeURL.appendingPathComponent("session.json"))
        let session = try #require(try JSONSerialization.jsonObject(with: sessionData) as? [String: Any])
        let segments = try #require(session["media_segments"] as? [[String: Any]])
        #expect(segments.count == 2)
        #expect(segments[0]["id"] as? String == "segment_0001")
        #expect(segments[0]["status"] as? String == "paused")
        #expect(segments[0]["ended_at"] != nil)
        #expect(segments[1]["id"] as? String == "segment_0002")
        #expect(segments[1]["status"] as? String == "recording")

        let tracks = try #require(session["tracks"] as? [[String: Any]])
        let relativePaths = Set(tracks.compactMap { $0["relative_path"] as? String })
        #expect(relativePaths.contains("tracks/screen_5.mp4"))
        #expect(relativePaths.contains("tracks/microphone.m4a"))
        #expect(relativePaths.contains("tracks/webcam.mov"))
        #expect(relativePaths.contains("tracks/segments/0002/screen_5.mp4"))
        #expect(relativePaths.contains("tracks/segments/0002/microphone.m4a"))
        #expect(relativePaths.contains("tracks/segments/0002/webcam.mov"))
        let firstScreenTrack = try #require(tracks.first { $0["relative_path"] as? String == "tracks/screen_5.mp4" })
        #expect(firstScreenTrack["capture_started_at"] != nil)
        #expect(firstScreenTrack["timeline_offset_seconds"] as? Double != nil)
    }

    @Test
    func audioOnlyPauseResumeRestartsMicrophoneWithoutScreen() async throws {
        let microphone = CaptureDevice(id: "audio-3", index: 3, name: "USB Mic", kind: .audio, uniqueID: "mic-uid")
        let screenManager = FakeScreenCaptureManager()
        let audioManager = FakeAudioCaptureManager()
        let store = RecorderStore(
            audioDeviceAvailability: { _ in true },
            nativeScreenCaptureManager: screenManager,
            nativeAudioCaptureManager: audioManager
        )
        store.devices = DeviceInventory(videoDevices: [], audioDevices: [microphone])
        store.selectedScreenIDs = []
        store.selectedAudioID = microphone.id

        let takeURL = try makeTemporaryTakeRoot()
        try await store.completeNativeStartAfterHelper(
            takeURL: takeURL,
            takeID: "take_test_audio_only_resume",
            title: "Audio only resume",
            helperStatusLines: []
        )

        await store.pauseRecording()
        #expect(store.state == .paused)
        #expect(!screenManager.isRecording)
        #expect(!audioManager.isRecording)

        await store.resumeRecording()
        #expect(store.state == .recording)
        #expect(screenManager.startCallCount == 0)
        #expect(!screenManager.isRecording)
        #expect(audioManager.startSegmentIndexes == [1, 2])
        #expect(audioManager.isRecording)

        let sessionData = try Data(contentsOf: takeURL.appendingPathComponent("session.json"))
        let session = try #require(try JSONSerialization.jsonObject(with: sessionData) as? [String: Any])
        let segments = try #require(session["media_segments"] as? [[String: Any]])
        #expect(segments.count == 2)
        #expect(segments[0]["status"] as? String == "paused")
        #expect(segments[1]["status"] as? String == "recording")

        let tracks = try #require(session["tracks"] as? [[String: Any]])
        let relativePaths = Set(tracks.compactMap { $0["relative_path"] as? String })
        #expect(relativePaths.contains("tracks/microphone.m4a"))
        #expect(relativePaths.contains("tracks/segments/0002/microphone.m4a"))
        #expect(!relativePaths.contains { $0.contains("screen_") })

        let startAttemptLog = try String(
            contentsOf: takeURL.appendingPathComponent("start_attempt.jsonl"),
            encoding: .utf8
        )
        #expect(startAttemptLog.contains("\"event\":\"resume_screen_start_skipped\""))
        #expect(startAttemptLog.contains("\"event\":\"resume_audio_start_ok\""))
        #expect(!startAttemptLog.contains("\"event\":\"resume_screen_start_ok\""))
    }

    @Test
    func storageCheckpointRotatesNativeWritersWithoutPausingTake() async throws {
        let screen = CaptureDevice(id: "screen-5", index: 5, name: "Capture screen 1", kind: .video)
        let webcam = CaptureDevice(id: "camera-8", index: 8, name: "FaceTime HD Camera", kind: .video, uniqueID: "camera-uid")
        let microphone = CaptureDevice(id: "audio-3", index: 3, name: "USB Mic", kind: .audio, uniqueID: "mic-uid")
        let screenManager = FakeScreenCaptureManager()
        let audioManager = FakeAudioCaptureManager()
        let cameraManager = FakeCameraCaptureManager()
        let store = RecorderStore(
            audioDeviceAvailability: { _ in true },
            nativeScreenCaptureManager: screenManager,
            nativeAudioCaptureManager: audioManager,
            nativeCameraCaptureManager: cameraManager
        )
        store.storageCheckpointIntervalSeconds = 0
        store.devices = DeviceInventory(videoDevices: [screen, webcam], audioDevices: [microphone])
        store.selectedScreenIDs = [screen.id]
        store.selectedAudioID = microphone.id
        store.webcamEnabled = true
        store.selectedWebcamID = webcam.id
        store.permissions.camera = .ready

        let takeURL = try makeTemporaryTakeRoot()
        try await store.completeNativeStartAfterHelper(
            takeURL: takeURL,
            takeID: "take_test_storage_checkpoint",
            title: "Storage checkpoint",
            helperStatusLines: []
        )

        await store.checkpointRecordingSegmentForStorage(reason: "test")

        #expect(store.state == .recording)
        #expect(screenManager.isRecording)
        #expect(audioManager.isRecording)
        #expect(cameraManager.isRecording)
        #expect(screenManager.stopCallCount == 1)
        #expect(audioManager.stopCallCount == 1)
        #expect(cameraManager.stopCallCount == 1)
        #expect(screenManager.startSegmentIndexes == [1, 2])
        #expect(audioManager.startSegmentIndexes == [1, 2])
        #expect(cameraManager.startSegmentIndexes == [1, 2])

        let sessionData = try Data(contentsOf: takeURL.appendingPathComponent("session.json"))
        let session = try #require(try JSONSerialization.jsonObject(with: sessionData) as? [String: Any])
        let segments = try #require(session["media_segments"] as? [[String: Any]])
        #expect(segments.count == 2)
        #expect(segments[0]["status"] as? String == "checkpointed")
        #expect(segments[0]["ended_at"] != nil)
        #expect(segments[1]["status"] as? String == "recording")
        #expect((session["pause_events"] as? [[String: Any]] ?? []).isEmpty)

        let tracks = try #require(session["tracks"] as? [[String: Any]])
        let relativePaths = Set(tracks.compactMap { $0["relative_path"] as? String })
        #expect(relativePaths.contains("tracks/segments/0002/screen_5.mp4"))
        #expect(relativePaths.contains("tracks/segments/0002/microphone.m4a"))
        #expect(relativePaths.contains("tracks/segments/0002/webcam.mov"))

        let startAttemptLog = try String(
            contentsOf: takeURL.appendingPathComponent("start_attempt.jsonl"),
            encoding: .utf8
        )
        #expect(startAttemptLog.contains("\"event\":\"storage_checkpoint_begin\""))
        #expect(startAttemptLog.contains("\"event\":\"storage_checkpoint_segment_opened\""))
    }

    @Test
    func stalledCameraHealthRotatesIntoNewSyncedSegment() async throws {
        let screen = CaptureDevice(id: "screen-5", index: 5, name: "Capture screen 1", kind: .video)
        let webcam = CaptureDevice(id: "camera-8", index: 8, name: "FaceTime HD Camera", kind: .video, uniqueID: "camera-uid")
        let microphone = CaptureDevice(id: "audio-3", index: 3, name: "USB Mic", kind: .audio, uniqueID: "mic-uid")
        let screenManager = FakeScreenCaptureManager()
        let audioManager = FakeAudioCaptureManager()
        let cameraManager = FakeCameraCaptureManager()
        cameraManager.recordingStats = NativeCameraRecordingStats(
            recordedDurationSeconds: 1,
            recordedFileSizeBytes: 8_192,
            videoFrameCount: 30,
            distinctFrameSignatureCount: 1,
            lastVideoFrameAt: Date(),
            lastDistinctFrameAt: Date()
        )
        let store = RecorderStore(
            audioDeviceAvailability: { _ in true },
            nativeScreenCaptureManager: screenManager,
            nativeAudioCaptureManager: audioManager,
            nativeCameraCaptureManager: cameraManager
        )
        store.storageCheckpointIntervalSeconds = 0
        store.cameraHealthPollIntervalSeconds = 0.02
        store.cameraHealthStallRecoverySeconds = 0.05
        store.cameraHealthVisualFreezeRecoverySeconds = 10
        store.devices = DeviceInventory(videoDevices: [screen, webcam], audioDevices: [microphone])
        store.selectedScreenIDs = [screen.id]
        store.selectedAudioID = microphone.id
        store.webcamEnabled = true
        store.selectedWebcamID = webcam.id
        store.permissions.camera = .ready

        let takeURL = try makeTemporaryTakeRoot()
        try await store.completeNativeStartAfterHelper(
            takeURL: takeURL,
            takeID: "take_test_camera_health_recovery",
            title: "Camera health recovery",
            helperStatusLines: []
        )

        try await waitUntil(timeout: 2) {
            cameraManager.startCallCount >= 2
        }
        await store.pauseRecording()

        #expect(store.state == .paused)
        #expect(Array(screenManager.startSegmentIndexes.prefix(2)) == [1, 2])
        #expect(Array(audioManager.startSegmentIndexes.prefix(2)) == [1, 2])
        #expect(Array(cameraManager.startSegmentIndexes.prefix(2)) == [1, 2])

        let sessionData = try Data(contentsOf: takeURL.appendingPathComponent("session.json"))
        let session = try #require(try JSONSerialization.jsonObject(with: sessionData) as? [String: Any])
        let segments = try #require(session["media_segments"] as? [[String: Any]])
        #expect(segments.count >= 2)
        #expect(segments[0]["status"] as? String == "checkpointed")
        let failures = session["known_failures"] as? [String] ?? []
        #expect(failures.contains { $0.contains("Camera track stopped advancing") })

        let startAttemptLog = try String(
            contentsOf: takeURL.appendingPathComponent("start_attempt.jsonl"),
            encoding: .utf8
        )
        #expect(startAttemptLog.contains("\"event\":\"camera_track_progress_stalled_recovery\""))
        #expect(startAttemptLog.contains("\"event\":\"storage_checkpoint_segment_opened\""))
    }

    @Test
    func nativeAudioRecorderDrivesLiveMeterDuringRecording() async throws {
        let screen = CaptureDevice(id: "screen-5", index: 5, name: "Capture screen 1", kind: .video)
        let microphone = CaptureDevice(id: "audio-3", index: 3, name: "USB Mic", kind: .audio, uniqueID: "mic-uid")
        let monitor = FakeAudioLevelMonitor()
        let screenManager = FakeScreenCaptureManager()
        let audioManager = FakeAudioCaptureManager(levelToEmitOnStart: 0.66)
        let store = RecorderStore(
            audioLevelMonitor: monitor,
            audioDeviceAvailability: { _ in true },
            nativeScreenCaptureManager: screenManager,
            nativeAudioCaptureManager: audioManager
        )
        store.devices = DeviceInventory(videoDevices: [screen], audioDevices: [microphone])
        store.selectedScreenIDs = [screen.id]
        store.selectedAudioID = microphone.id

        let takeURL = try makeTemporaryTakeRoot()
        try await store.completeNativeStartAfterHelper(
            takeURL: takeURL,
            takeID: "take_test_native_level",
            title: "Native level",
            helperStatusLines: []
        )

        #expect(monitor.stopCallCount == 1)
        #expect(audioManager.startCallCount == 1)
        #expect(store.microphoneLevel == 0.66)
        #expect(store.microphoneMeterStatus == "Recording mic input")
    }

    @Test
    func preflightRepairsReadyStateWhileNativeWritersAreLive() async throws {
        let screen = CaptureDevice(id: "screen-5", index: 5, name: "Capture screen 1", kind: .video)
        let microphone = CaptureDevice(id: "audio-3", index: 3, name: "USB Mic", kind: .audio, uniqueID: "mic-uid")
        let screenManager = FakeScreenCaptureManager()
        let audioManager = FakeAudioCaptureManager()
        let store = RecorderStore(
            screenCaptureStatus: { .ready },
            microphonePermissionStatus: { .ready },
            audioDeviceAvailability: { _ in true },
            nativeScreenCaptureManager: screenManager,
            nativeAudioCaptureManager: audioManager
        )
        store.devices = DeviceInventory(videoDevices: [screen], audioDevices: [microphone])
        store.selectedScreenIDs = [screen.id]
        store.selectedAudioID = microphone.id

        let takeURL = try makeTemporaryTakeRoot()
        try await store.completeNativeStartAfterHelper(
            takeURL: takeURL,
            takeID: "take_test_state_repair",
            title: "State repair",
            helperStatusLines: []
        )

        store.state = .ready
        await store.refreshPreflight()

        #expect(store.state == .recording)
        #expect(store.captureControlsActive)
        #expect(store.captureIsWriting)
        #expect(!store.canStart)
        #expect(store.canStop)
        #expect(screenManager.isRecording)
        #expect(audioManager.isRecording)
        #expect(store.statusLines.contains { $0.contains("Recording state repaired") })

        let startAttemptLog = try String(
            contentsOf: takeURL.appendingPathComponent("start_attempt.jsonl"),
            encoding: .utf8
        )
        #expect(startAttemptLog.contains("\"event\":\"state_recording_repaired\""))
    }

    private func makeTemporaryTakeRoot() throws -> URL {
        let takeURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("demo-take-start-policy-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: takeURL, withIntermediateDirectories: true)
        let session = """
        {
          "schema": "demo_take_session_v0",
          "take_id": "take_test",
          "config": {
            "repo_root": "\(FileManager.default.temporaryDirectory.path)",
            "ffmpeg_path": "/usr/bin/false",
            "screenshot_interval_seconds": 5
          },
          "known_failures": [],
          "markers": [],
          "pause_events": [],
          "processes": [],
          "tracks": []
        }
        """
        try Data(session.utf8)
            .write(to: takeURL.appendingPathComponent("session.json"), options: [.atomic])
        return takeURL
    }

    private func makeTemporaryConfigPaths() throws -> (config: URL, inventory: URL) {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("demo-take-start-policy-config-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        return (
            root.appendingPathComponent("recorder_config.json"),
            root.appendingPathComponent("device_inventory.json")
        )
    }

    private func writeRecorderConfigPayload(_ payload: [String: Any], to url: URL) throws {
        let data = try JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: url, options: [.atomic])
    }

    private func waitUntil(timeout: TimeInterval, _ condition: @escaping @MainActor () -> Bool) async throws {
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            if await MainActor.run(body: condition) {
                return
            }
            try await Task.sleep(nanoseconds: 20_000_000)
        }
        #expect(await MainActor.run(body: condition))
    }
}

private enum FakeStartError: LocalizedError, Equatable {
    case screen
    case audio
    case camera

    var errorDescription: String? {
        switch self {
        case .screen: "fake screen start failed"
        case .audio: "fake audio start failed"
        case .camera: "fake camera start failed"
        }
    }
}

@MainActor
private final class FakeScreenCaptureManager: NativeScreenCaptureManaging {
    private let startError: Error?
    private(set) var startCallCount = 0
    private(set) var startSegmentIndexes: [Int] = []
    private(set) var startScreenIndexes: [[Int]] = []
    private(set) var stopCallCount = 0
    private(set) var isRecording = false

    init(startError: Error? = nil) {
        self.startError = startError
    }

    func start(takeRoot: URL, screens: [CaptureDevice], segmentIndex: Int) async throws -> [NativeScreenCaptureTrack] {
        startCallCount += 1
        startSegmentIndexes.append(segmentIndex)
        startScreenIndexes.append(screens.map(\.index))
        if let startError {
            throw startError
        }
        isRecording = true
        return screens.map { screen in
            let relativePath = segmentIndex == 1
                ? "tracks/screen_\(screen.index).mp4"
                : String(format: "tracks/segments/%04d/screen_%d.mp4", segmentIndex, screen.index)
            return NativeScreenCaptureTrack(device: screen, relativePath: relativePath, startedAt: Date())
        }
    }

    func stop() async throws {
        stopCallCount += 1
        isRecording = false
    }
}

@MainActor
private final class FakeAudioCaptureManager: NativeAudioCaptureManaging {
    private let startError: Error?
    private let levelToEmitOnStart: Float?
    private(set) var startCallCount = 0
    private(set) var startSegmentIndexes: [Int] = []
    private(set) var stopCallCount = 0
    private(set) var isRecording = false

    init(startError: Error? = nil, levelToEmitOnStart: Float? = nil) {
        self.startError = startError
        self.levelToEmitOnStart = levelToEmitOnStart
    }

    func start(
        takeRoot: URL,
        microphone: CaptureDevice?,
        segmentIndex: Int,
        onLevel: NativeAudioLevelHandler?
    ) async throws -> NativeAudioCaptureTrack? {
        startCallCount += 1
        startSegmentIndexes.append(segmentIndex)
        if let startError {
            throw startError
        }
        guard let microphone else { return nil }
        isRecording = true
        if let levelToEmitOnStart {
            onLevel?(levelToEmitOnStart, "Recording mic input")
        }
        let relativePath = segmentIndex == 1
            ? "tracks/microphone.m4a"
            : String(format: "tracks/segments/%04d/microphone.m4a", segmentIndex)
        return NativeAudioCaptureTrack(device: microphone, relativePath: relativePath, startedAt: Date())
    }

    func stop() async throws {
        stopCallCount += 1
        isRecording = false
    }
}

@MainActor
private final class FakeCameraCaptureManager: NativeCameraCaptureManaging {
    private let startError: Error?
    var recordingStats: NativeCameraRecordingStats?
    private(set) var startCallCount = 0
    private(set) var startSegmentIndexes: [Int] = []
    private(set) var stopCallCount = 0
    private(set) var isRecording = false

    var activeRecordingStats: NativeCameraRecordingStats? {
        isRecording ? recordingStats : nil
    }

    init(startError: Error? = nil) {
        self.startError = startError
    }

    func start(takeRoot: URL, webcam: CaptureDevice?, segmentIndex: Int) async throws -> NativeCameraCaptureTrack? {
        startCallCount += 1
        startSegmentIndexes.append(segmentIndex)
        if let startError {
            throw startError
        }
        guard let webcam else { return nil }
        isRecording = true
        let relativePath = segmentIndex == 1
            ? "tracks/webcam.mov"
            : String(format: "tracks/segments/%04d/webcam.mov", segmentIndex)
        return NativeCameraCaptureTrack(device: webcam, relativePath: relativePath, startedAt: Date())
    }

    func stop() async throws {
        stopCallCount += 1
        isRecording = false
    }
}

private final class FakeAudioLevelMonitor: AudioLevelMonitoring {
    private(set) var stopCallCount = 0

    func start(
        preferredDeviceName: String?,
        preferredDeviceUniqueID: String?,
        onLevel: @escaping (Float, String) -> Void
    ) {}

    func stop() {
        stopCallCount += 1
    }
}
