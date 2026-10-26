import CoreGraphics
import Foundation
import Testing
@testable import DemoTakeConsoleApp

@MainActor
struct ReviewPlaybackMediaTests {
    @Test
    func reviewUsesScreenAsPrimaryAndWebcamAsPiPWhenBothTracksExist() throws {
        let takeURL = try makeTakeRoot()
        try writeTrack("tracks/webcam.mp4", in: takeURL)
        try writeTrack("tracks/screen_1.mp4", in: takeURL)
        try writeTrack("tracks/microphone.m4a", in: takeURL)
        try writeSession(
            to: takeURL,
            tracks: [
                track(id: "webcam", role: "webcam", relativePath: "tracks/webcam.mp4"),
                track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4"),
                track(id: "microphone", role: "microphone", relativePath: "tracks/microphone.m4a"),
            ]
        )

        let store = RecorderStore()
        store.selectTakeForReview(takeURL, announce: false)

        #expect(store.playbackURL?.lastPathComponent == "screen_1.mp4")
        #expect(store.playbackCameraURL?.lastPathComponent == "webcam.mp4")
        #expect(store.playbackCameraTitle == "webcam.mp4")
        #expect(store.playbackHasCameraOverlay)
        #expect(store.playbackCameraPlayer != nil)
    }

    @Test
    func renderedRoughCutStaysPrimaryAndWebcamStillBecomesPiP() throws {
        let takeURL = try makeTakeRoot()
        try writeTrack("render/rough_cut.mp4", in: takeURL)
        try writeTrack("tracks/webcam.mp4", in: takeURL)
        try writeSession(
            to: takeURL,
            tracks: [
                track(id: "webcam", role: "webcam", relativePath: "tracks/webcam.mp4"),
            ]
        )

        let store = RecorderStore()
        store.selectTakeForReview(takeURL, announce: false)

        #expect(store.playbackURL?.path.hasSuffix("render/rough_cut.mp4") == true)
        #expect(store.playbackCameraURL?.path.hasSuffix("tracks/webcam.mp4") == true)
        #expect(store.playbackHasCameraOverlay)
    }

    @Test
    func audioOnlyPackageUsesReviewAudioWithoutScreenWarning() throws {
        let takeURL = try makeTakeRoot()
        try writeTrack("tracks/microphone.wav", in: takeURL)
        try writeTrack("render/review_audio.mp3", in: takeURL)
        try writeSession(
            to: takeURL,
            tracks: [
                track(id: "microphone", role: "microphone", relativePath: "tracks/microphone.wav"),
            ]
        )
        try writeJSON(
            [
                "schema": "demo_take_render_receipt_v0",
                "status": "unavailable",
                "output": NSNull(),
                "known_failures": ["No screen track was available for rough render."],
            ],
            to: takeURL.appendingPathComponent("render/render_receipt.json")
        )
        try writeJSON(
            [
                "schema": "demo_take_manifest_v0",
                "take_id": takeURL.lastPathComponent,
                "recording_state": "package_ready",
                "review_audio": "render/review_audio.mp3",
                "review_video": NSNull(),
                "known_failures": [],
            ],
            to: takeURL.appendingPathComponent("manifest.json")
        )

        let store = RecorderStore()
        #expect(store.selectTakeForReview(takeURL, announce: false))

        #expect(store.activeTakeReviewIsReady)
        #expect(store.playbackURL?.path.hasSuffix("render/review_audio.mp3") == true)
        #expect(store.activeTakeReviewStatusLine.contains("audio review"))
        #expect(!store.activeTakeReviewStatusLine.contains("Missing screen track"))
        #expect(!store.activeTakeReviewStatusLine.contains("MP3 not built"))
    }

    @Test
    func corruptWebcamTrackDoesNotBecomeBlackPiPOverlay() throws {
        let takeURL = try makeTakeRoot()
        try writeCorruptTrack("tracks/webcam.mp4", in: takeURL)
        try writeTrack("tracks/screen_1.mp4", in: takeURL)
        try writeSession(
            to: takeURL,
            tracks: [
                track(id: "webcam", role: "webcam", relativePath: "tracks/webcam.mp4"),
                track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4"),
            ]
        )

        let store = RecorderStore()
        store.selectTakeForReview(takeURL, announce: false)

        #expect(store.playbackURL?.lastPathComponent == "screen_1.mp4")
        #expect(store.playbackCameraURL == nil)
        #expect(store.playbackCameraPlayer == nil)
        #expect(!store.playbackHasCameraOverlay)
        #expect(store.playbackStatus.contains("Camera track not playable"))
    }

    @Test
    func preparingNewTakeClearsReviewSelectionAndPlayback() throws {
        let takeURL = try makeTakeRoot()
        try writeTrack("tracks/webcam.mp4", in: takeURL)
        try writeTrack("tracks/screen_1.mp4", in: takeURL)
        try writeSession(
            to: takeURL,
            tracks: [
                track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4"),
                track(id: "webcam", role: "webcam", relativePath: "tracks/webcam.mp4"),
            ]
        )

        let store = RecorderStore()
        store.selectTakeForReview(takeURL, announce: false)
        #expect(store.activeTakeURL == takeURL)
        #expect(store.playbackURL != nil)

        let prepared = store.prepareNewTakeForRecording()

        #expect(prepared)
        #expect(store.activeTakeURL == nil)
        #expect(store.playbackURL == nil)
        #expect(store.playbackCameraURL == nil)
        #expect(store.activeTakeExportURL == nil)
        #expect(store.state != .reviewReady)
    }

    @Test
    func deletingSelectedTakeRemovesFolderAndClearsReviewState() throws {
        let takeURL = try makeTakeRoot()
        try writeTrack("tracks/screen_1.mp4", in: takeURL)
        try writeSession(
            to: takeURL,
            tracks: [
                track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4"),
            ]
        )

        let store = RecorderStore()
        #expect(store.selectTakeForReview(takeURL, announce: false))
        store.recentTakes = [summary(for: takeURL)]
        #expect(FileManager.default.fileExists(atPath: takeURL.path))

        store.deleteTake(takeURL)

        #expect(!FileManager.default.fileExists(atPath: takeURL.path))
        #expect(store.activeTakeURL == nil)
        #expect(store.playbackURL == nil)
        #expect(store.playbackCameraURL == nil)
        #expect(!store.recentTakes.contains { $0.url.standardizedFileURL.path == takeURL.standardizedFileURL.path })
        #expect(store.statusLines.contains { $0.contains("Deleted \(takeURL.lastPathComponent)") })
    }

    @Test
    func deleteKeyRequestQueuesConfirmationBeforeRemovingSelectedTake() throws {
        let takeURL = try makeTakeRoot()
        try writeTrack("tracks/screen_1.mp4", in: takeURL)
        try writeSession(
            to: takeURL,
            tracks: [
                track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4"),
            ]
        )

        let store = RecorderStore()
        #expect(store.selectTakeForReview(takeURL, announce: false))
        store.recentTakes = [summary(for: takeURL)]

        store.requestDeleteActiveTake()

        #expect(FileManager.default.fileExists(atPath: takeURL.path))
        #expect(store.pendingDeleteTake?.url.standardizedFileURL.path == takeURL.standardizedFileURL.path)

        store.confirmPendingDeleteTake()

        #expect(store.pendingDeleteTake == nil)
        #expect(!FileManager.default.fileExists(atPath: takeURL.path))
        #expect(store.activeTakeURL == nil)
    }

    @Test
    func deleteKeyRequestUsesKeyboardTargetBeforeActiveTake() throws {
        let activeURL = try makeTakeRoot()
        let targetURL = try makeTakeRoot()
        try writeTrack("tracks/screen_1.mp4", in: activeURL)
        try writeTrack("tracks/screen_1.mp4", in: targetURL)
        try writeSession(
            to: activeURL,
            tracks: [track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4")]
        )
        try writeSession(
            to: targetURL,
            tracks: [track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4")]
        )

        let store = RecorderStore()
        #expect(store.selectTakeForReview(activeURL, announce: false))
        store.recentTakes = [summary(for: activeURL), summary(for: targetURL)]
        store.keyboardDeleteTargetTake = summary(for: targetURL)

        store.requestDeleteTargetTake()

        #expect(FileManager.default.fileExists(atPath: activeURL.path))
        #expect(FileManager.default.fileExists(atPath: targetURL.path))
        #expect(store.pendingDeleteTake?.url.standardizedFileURL.path == targetURL.standardizedFileURL.path)

        store.confirmPendingDeleteTake()

        #expect(FileManager.default.fileExists(atPath: activeURL.path))
        #expect(!FileManager.default.fileExists(atPath: targetURL.path))
        #expect(store.activeTakeURL?.standardizedFileURL.path == activeURL.standardizedFileURL.path)
    }

    @Test
    func plainDeletePolicyKeepsActiveTitleEditingButAllowsTargetedRecentTake() throws {
        let activeURL = try makeTakeRoot()
        let targetURL = try makeTakeRoot()
        try writeTrack("tracks/screen_1.mp4", in: activeURL)
        try writeTrack("tracks/screen_1.mp4", in: targetURL)
        try writeSession(
            to: activeURL,
            tracks: [track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4")]
        )
        try writeSession(
            to: targetURL,
            tracks: [track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4")]
        )

        let store = RecorderStore()
        #expect(store.selectTakeForReview(activeURL, announce: false))
        store.recentTakes = [summary(for: activeURL), summary(for: targetURL)]

        store.keyboardDeleteTargetTake = summary(for: activeURL)
        #expect(!store.shouldRoutePlainDeleteToTake(textInputFocused: true))
        #expect(store.shouldRoutePlainDeleteToTake(textInputFocused: false))

        store.keyboardDeleteTargetTake = summary(for: targetURL)
        #expect(store.shouldRoutePlainDeleteToTake(textInputFocused: true))
        #expect(store.shouldRoutePlainDeleteToTake(textInputFocused: false))
    }

    @Test
    func stoppedTakeCanBuildPackageDirectlyAndStillPrepareReviewOnly() throws {
        let takeURL = try makeTakeRoot()
        try writeTrack("tracks/screen_1.mp4", in: takeURL)
        try writeSession(
            to: takeURL,
            tracks: [track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4")]
        )
        try writeManifest(to: takeURL, recordingState: "stopped")

        let store = RecorderStore()
        #expect(store.selectTakeForReview(takeURL, announce: false))

        #expect(store.state == .stopped)
        #expect(store.playbackURL == nil)
        #expect(!store.activeTakeReviewIsReady)
        #expect(store.canPrepareActiveTakeReview)
        #expect(store.canBuildPackage)
        #expect(store.canDiscardTake)
        #expect(store.canRequestDeleteActiveTake)
        #expect(store.activeTakeReviewStatusLine == "Capture stopped; build package when ready.")
    }

    @Test
    func stoppingTakeCanBeDiscardedAfterCaptureIsMarkedStopped() throws {
        let takeURL = try makeTakeRoot()
        try writeTrack("tracks/screen_1.mp4", in: takeURL)
        try writeSession(
            to: takeURL,
            tracks: [track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4")]
        )
        try writeManifest(to: takeURL, recordingState: "stopped")

        let store = RecorderStore()
        #expect(store.selectTakeForReview(takeURL, announce: false))
        store.recentTakes = [summary(for: takeURL)]
        store.state = .stopping

        #expect(store.canDiscardTake)
        store.requestDeleteActiveTake()
        #expect(store.pendingDeleteTake?.url.standardizedFileURL.path == takeURL.standardizedFileURL.path)

        store.confirmPendingDeleteTake()

        #expect(!FileManager.default.fileExists(atPath: takeURL.path))
        #expect(store.pendingDeleteTake == nil)
        #expect(store.activeTakeURL == nil)
        #expect(store.playbackURL == nil)
        #expect(!store.recentTakes.contains { $0.url.standardizedFileURL.path == takeURL.standardizedFileURL.path })
    }

    @Test
    func stoppingTakeCanBeDiscardedBeforeCaptureIsMarkedStoppedAfterWritersStop() throws {
        let takeURL = try makeTakeRoot()
        try writeTrack("tracks/screen_1.mp4", in: takeURL)
        try writeSession(
            to: takeURL,
            tracks: [track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4")]
        )
        try writeManifest(to: takeURL, recordingState: "recording")

        let store = RecorderStore()
        store.activeTakeURL = takeURL
        store.state = .stopping

        #expect(store.canDiscardTake)
        store.discardTakeAndReset()

        #expect(!FileManager.default.fileExists(atPath: takeURL.path))
        #expect(store.activeTakeURL == nil)
    }

    @Test
    func stoppingTakeCannotBeDiscardedWhileCaptureWritersAreActive() throws {
        let takeURL = try makeTakeRoot()
        try writeTrack("tracks/screen_1.mp4", in: takeURL)
        try writeSession(
            to: takeURL,
            tracks: [track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4")]
        )
        try writeManifest(to: takeURL, recordingState: "recording")

        let store = RecorderStore(
            nativeScreenCaptureManager: ReviewFakeScreenCaptureManager(isRecording: true),
            nativeAudioCaptureManager: ReviewFakeAudioCaptureManager(),
            nativeCameraCaptureManager: ReviewFakeCameraCaptureManager()
        )
        store.activeTakeURL = takeURL
        store.state = .stopping

        #expect(!store.canDiscardTake)
        store.discardTakeAndReset()

        #expect(FileManager.default.fileExists(atPath: takeURL.path))
        #expect(store.activeTakeURL == takeURL)
    }

    @Test
    func sidecarRevisionOnlyBumpsForSelectedTake() throws {
        let selectedURL = try makeTakeRoot()
        let otherURL = try makeTakeRoot()
        try writeTrack("tracks/screen_1.mp4", in: selectedURL)
        try writeSession(
            to: selectedURL,
            tracks: [track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4")]
        )

        let store = RecorderStore()
        #expect(store.selectTakeForReview(selectedURL, announce: false))
        #expect(store.activeTakeSidecarRevision == 0)

        store.notifyActiveTakeSidecarsChanged(for: otherURL)
        #expect(store.activeTakeSidecarRevision == 0)

        store.notifyActiveTakeSidecarsChanged(for: selectedURL)
        #expect(store.activeTakeSidecarRevision == 1)
    }

    @Test
    func playAtEndRestartsReviewPlayback() throws {
        let takeURL = try makeTakeRoot()
        try writeTrack("tracks/screen_1.mp4", in: takeURL)
        try writeSession(
            to: takeURL,
            tracks: [track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4")]
        )

        let store = RecorderStore()
        #expect(store.selectTakeForReview(takeURL, announce: false))
        store.playbackDuration = 10
        store.playbackPosition = 9.9

        store.playPlayback()

        #expect(store.playbackPosition == 0)
        #expect(store.playbackIsPlaying)
    }

    @Test
    func transcriptForceReloadReplacesUnavailableStatusWithReadyCues() throws {
        let takeURL = try makeTakeRoot()
        try writeTranscriptUnavailable(to: takeURL, reason: "Transcript provider unavailable: timeout, model_missing.")

        let transcript = TranscriptController()
        transcript.reload(takeRoot: takeURL, mediaDuration: 12, force: true)
        #expect(transcript.status == .unavailable("Transcript provider unavailable: timeout, model_missing."))
        #expect(transcript.cueCount == 0)

        try writeTranscriptReady(to: takeURL)
        transcript.reload(takeRoot: takeURL, mediaDuration: 12, force: true)

        #expect(transcript.status == .ready)
        #expect(transcript.cueCount == 1)
        #expect(transcript.cues[0].text == "Transcript is ready now.")
    }

    @Test
    func transcriptConfidencePrefersReadyTranscriptOverPackageBuildState() throws {
        let ready = transcriptConfidenceDisplay(status: .ready, cueCount: 10373, packageBuildActive: true)
        #expect(ready.text == "10373 cues")
        #expect(ready.tone == .success)

        let stillWaiting = transcriptConfidenceDisplay(status: .missing, cueCount: 0, packageBuildActive: true)
        #expect(stillWaiting.text == "building…")
        #expect(stillWaiting.tone == .accent)
    }

    @Test
    func deletingMissingTakePrunesStaleHistoryRowAndSelection() throws {
        let takeURL = try makeTakeRoot()
        let store = RecorderStore()
        store.activeTakeURL = takeURL
        store.recentTakes = [summary(for: takeURL)]
        try FileManager.default.removeItem(at: takeURL)

        store.deleteTake(takeURL)

        #expect(store.activeTakeURL == nil)
        #expect(store.playbackURL == nil)
        #expect(!store.recentTakes.contains { $0.url.standardizedFileURL.path == takeURL.standardizedFileURL.path })
        #expect(store.statusLines.contains { $0.contains("Removed stale \(takeURL.lastPathComponent)") })
    }

    @Test
    func backgroundTakeWorkBlocksPackageMutationsButNotNextStart() throws {
        let screen = CaptureDevice(id: "screen-1", index: 1, name: "Capture screen 1", kind: .video)
        let takeURL = try makeTakeRoot()
        try writeTrack("tracks/screen_1.mp4", in: takeURL)
        try writeSession(
            to: takeURL,
            tracks: [
                track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4"),
            ]
        )

        let store = RecorderStore()
        store.ffmpegPath = "/usr/bin/false"
        store.permissions.screenCapture = .ready
        store.devices = DeviceInventory(videoDevices: [screen], audioDevices: [])
        store.selectedScreenIDs = [screen.id]
        store.selectTakeForReview(takeURL, announce: false)
        store.takeTitleDraft = "New title"

        store.backgroundFinalizingTakeIDs.insert(takeURL.lastPathComponent)
        #expect(store.canStart)
        #expect(!store.canBuildPackage)
        #expect(!store.canDiscardTake)
        #expect(!store.canRenameActiveTake)
        #expect(store.activeTakeBackgroundLine?.contains("Replayable review") == true)

        store.backgroundFinalizingTakeIDs.removeAll()
        store.backgroundBuildingTakeIDs.insert(takeURL.lastPathComponent)
        #expect(store.canStart)
        #expect(!store.canBuildPackage)
        #expect(!store.canDiscardTake)
        #expect(!store.canRenameActiveTake)
        #expect(store.activeTakeIsBuildingPackage)
    }

    @Test
    func selectTakeForReviewReportsFailureWithoutChangingSelection() throws {
        let takeURL = try makeTakeRoot()
        let missingURL = takeURL.deletingLastPathComponent()
            .appendingPathComponent("take_missing_\(UUID().uuidString)", isDirectory: true)
        try writeTrack("tracks/screen_1.mp4", in: takeURL)
        try writeSession(
            to: takeURL,
            tracks: [
                track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4"),
            ]
        )

        let store = RecorderStore()
        #expect(store.selectTakeForReview(takeURL, announce: false))
        #expect(!store.selectTakeForReview(missingURL, announce: false))
        #expect(store.activeTakeURL == takeURL)
        #expect(store.playbackURL?.lastPathComponent == "screen_1.mp4")
    }

    @Test
    func cameraPiPLayoutPersistsAsEditableReviewSidecar() throws {
        let takeURL = try makeTakeRoot()
        try writeTrack("tracks/webcam.mp4", in: takeURL)
        try writeTrack("tracks/screen_1.mp4", in: takeURL)
        try writeSession(
            to: takeURL,
            tracks: [
                track(id: "screen", role: "screen", relativePath: "tracks/screen_1.mp4"),
                track(id: "webcam", role: "webcam", relativePath: "tracks/webcam.mp4"),
            ]
        )

        let store = RecorderStore()
        store.selectTakeForReview(takeURL, announce: false)
        store.updatePlaybackCameraOverlayLayout(offset: CGSize(width: -48, height: -24), scale: 1.24)

        let layoutURL = takeURL.appendingPathComponent("review/camera_pip_layout.json")
        let data = try Data(contentsOf: layoutURL)
        let saved = try JSONDecoder().decode(CameraPIPLayout.self, from: data)
        #expect(saved.schema == CameraPIPLayout.schemaName)
        #expect(saved.offsetX == -48)
        #expect(saved.offsetY == -24)
        #expect(abs(saved.scale - 1.24) < 0.0001)

        let reloaded = RecorderStore()
        reloaded.selectTakeForReview(takeURL, announce: false)
        #expect(reloaded.playbackCameraOverlayLayout == saved)
    }

    @Test
    func cameraPiPLayoutDecodesLegacySidecarAndClampsScale() throws {
        let data = Data("""
        {
          "offset_x": -32.5,
          "offset_y": -18.25,
          "scale": 4.0
        }
        """.utf8)

        let decoded = try JSONDecoder().decode(CameraPIPLayout.self, from: data)

        #expect(decoded.schema == CameraPIPLayout.schemaName)
        #expect(decoded.anchor == "bottomTrailing")
        #expect(decoded.offsetX == -32.5)
        #expect(decoded.offsetY == -18.25)
        #expect(decoded.scale == 1.45)
    }

    private func makeTakeRoot() throws -> URL {
        let takeURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("take_review_media_\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: takeURL, withIntermediateDirectories: true)
        return takeURL
    }

    private func writeTrack(_ relativePath: String, in takeURL: URL) throws {
        let url = takeURL.appendingPathComponent(relativePath)
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        if ["mp4", "mov", "m4v"].contains(url.pathExtension.lowercased()) {
            try minimalMovieData().write(to: url, options: [.atomic])
        } else {
            try Data("placeholder media".utf8).write(to: url, options: [.atomic])
        }
    }

    private func writeCorruptTrack(_ relativePath: String, in takeURL: URL) throws {
        let url = takeURL.appendingPathComponent(relativePath)
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try Data("mdat without a movie header".utf8).write(to: url, options: [.atomic])
    }

    private func writeJSON(_ payload: [String: Any], to url: URL) throws {
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        let data = try JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: url, options: [.atomic])
    }

    private func minimalMovieData() -> Data {
        var data = Data()
        data.append(atom("ftyp", payload: Data("isom\0\0\0\u{1}isomavc1".utf8)))
        data.append(atom("moov"))
        return data
    }

    private func atom(_ type: String, payload: Data = Data()) -> Data {
        var data = Data()
        var size = UInt32(8 + payload.count).bigEndian
        withUnsafeBytes(of: &size) { data.append(contentsOf: $0) }
        data.append(Data(type.utf8.prefix(4)))
        data.append(payload)
        return data
    }

    private func writeSession(to takeURL: URL, tracks: [[String: Any]]) throws {
        let session: [String: Any] = [
            "schema": "demo_take_session_v0",
            "take_id": takeURL.lastPathComponent,
            "config": [:],
            "known_failures": [],
            "tracks": tracks,
        ]
        let data = try JSONSerialization.data(withJSONObject: session, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: takeURL.appendingPathComponent("session.json"), options: [.atomic])
    }

    private func writeManifest(to takeURL: URL, recordingState: String) throws {
        let manifest: [String: Any] = [
            "schema": "demo_take_manifest_v0",
            "take_id": takeURL.lastPathComponent,
            "recording_state": recordingState,
            "known_failures": [],
        ]
        let data = try JSONSerialization.data(withJSONObject: manifest, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: takeURL.appendingPathComponent("manifest.json"), options: [.atomic])
    }

    private func writeTranscriptUnavailable(to takeURL: URL, reason: String) throws {
        let transcript: [String: Any] = [
            "schema": "demo_take_transcript_v0",
            "status": "unavailable",
            "reason": reason,
            "segments": [],
        ]
        let url = takeURL.appendingPathComponent("transcript/transcript.json")
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        let data = try JSONSerialization.data(withJSONObject: transcript, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: url, options: [.atomic])
    }

    private func writeTranscriptReady(to takeURL: URL) throws {
        let transcript: [String: Any] = [
            "schema": "demo_take_transcript_v0",
            "status": "ready",
            "model": "openai_whisper-base",
            "language": "en",
            "duration_seconds": 1.4,
            "segments": [
                [
                    "id": "seg_0001",
                    "start": 0.0,
                    "end": 1.4,
                    "text": "Transcript is ready now.",
                ],
            ],
        ]
        let url = takeURL.appendingPathComponent("transcript/transcript.json")
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        let data = try JSONSerialization.data(withJSONObject: transcript, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: url, options: [.atomic])
    }

    private func track(id: String, role: String, relativePath: String) -> [String: Any] {
        [
            "id": id,
            "role": role,
            "device_name": role,
            "device_index": 0,
            "relative_path": relativePath,
        ]
    }

    private func summary(for takeURL: URL) -> TakeSummary {
        TakeSummary(
            id: takeURL.path,
            url: takeURL,
            name: takeURL.lastPathComponent,
            detailLine: "test",
            sizeLine: "0 MB",
            storageLine: "",
            exportLine: "",
            exportReady: false,
            iconName: "film",
            modifiedAt: Date()
        )
    }
}

@MainActor
private final class ReviewFakeScreenCaptureManager: NativeScreenCaptureManaging {
    var isRecording: Bool

    init(isRecording: Bool = false) {
        self.isRecording = isRecording
    }

    func start(takeRoot: URL, screens: [CaptureDevice], segmentIndex: Int) async throws -> [NativeScreenCaptureTrack] {
        isRecording = true
        return []
    }

    func stop() async throws {
        isRecording = false
    }
}

@MainActor
private final class ReviewFakeAudioCaptureManager: NativeAudioCaptureManaging {
    var isRecording: Bool

    init(isRecording: Bool = false) {
        self.isRecording = isRecording
    }

    func start(
        takeRoot: URL,
        microphone: CaptureDevice?,
        segmentIndex: Int,
        onLevel: NativeAudioLevelHandler?
    ) async throws -> NativeAudioCaptureTrack? {
        isRecording = true
        return nil
    }

    func stop() async throws {
        isRecording = false
    }
}

@MainActor
private final class ReviewFakeCameraCaptureManager: NativeCameraCaptureManaging {
    var isRecording: Bool
    var activeRecordingStats: NativeCameraRecordingStats? { nil }

    init(isRecording: Bool = false) {
        self.isRecording = isRecording
    }

    func start(
        takeRoot: URL,
        webcam: CaptureDevice?,
        segmentIndex: Int
    ) async throws -> NativeCameraCaptureTrack? {
        isRecording = true
        return nil
    }

    func stop() async throws {
        isRecording = false
    }
}
