import AppKit
import AVFoundation
import Foundation
import UniformTypeIdentifiers

struct TakeSummary: Identifiable, Equatable {
    let id: String
    let url: URL
    let name: String
    let detailLine: String
    let sizeLine: String
    let storageLine: String
    let exportLine: String
    let exportReady: Bool
    let iconName: String
    let modifiedAt: Date
}

struct ImportCandidateSummary: Identifiable, Equatable {
    let id: String
    let url: URL
    let name: String
    let detailLine: String
    let sizeLine: String
    let modifiedAt: Date
}

private struct TakeManifestSummary: Decodable {
    let title: String?
    let takeTitle: String?
    let recordingState: String?
    let reviewVideo: String?
    let reviewAudio: String?
    let knownFailures: [String]?

    enum CodingKeys: String, CodingKey {
        case title
        case takeTitle = "take_title"
        case recordingState = "recording_state"
        case reviewVideo = "review_video"
        case reviewAudio = "review_audio"
        case knownFailures = "known_failures"
    }
}

private struct TakeSessionSummary: Decodable {
    struct Config: Decodable {
        let title: String?
        let takeTitle: String?

        enum CodingKeys: String, CodingKey {
            case title
            case takeTitle = "take_title"
        }
    }

    let config: Config?
    let tracks: [TrackRecord]?
}

private struct RenderReceiptSummary: Decodable {
    let status: String?
    let output: String?
    let knownFailures: [String]?

    enum CodingKeys: String, CodingKey {
        case status
        case output
        case knownFailures = "known_failures"
    }
}

private struct PostprocessProgressEvent: Decodable {
    let stage: String
    let status: String
    let message: String
}

private struct TranscriptSidecarSummary: Decodable {
    let status: String?
}

private struct StorageReceiptSummary: Decodable {
    let status: String?
    let storageProfile: String?
    let bytesSavedPhysical: Int64?
    let bytesAfterPhysical: Int64?

    enum CodingKeys: String, CodingKey {
        case status
        case storageProfile = "storage_profile"
        case bytesSavedPhysical = "bytes_saved_physical"
        case bytesAfterPhysical = "bytes_after_physical"
    }
}

private struct ExportReceiptSummary: Decodable {
    let status: String?
    let output: String?
    let outputPath: String?
    let method: String?
    let bytes: Int64?
    let videoStreamAction: String?

    enum CodingKeys: String, CodingKey {
        case status
        case output
        case outputPath = "output_path"
        case method
        case bytes
        case videoStreamAction = "video_stream_action"
    }
}

private struct ExportStatusSummary {
    let url: URL?
    let line: String
    let historyLine: String
    let ready: Bool
}

private struct PersistedRecorderConfig: Decodable {
    let selectedDisplayIndexes: [Int]?
    let selectedMicrophoneIndex: Int?
    let selectedMicrophoneName: String?
    let selectedMicrophoneUniqueID: String?
    let selectedWebcamIndex: Int?
    let screenshotIntervalSeconds: Int?
    let hideConsoleBeforeCapture: Bool?
    let transcribeModel: String?
    let webcamEnabled: Bool?

    enum CodingKeys: String, CodingKey {
        case selectedDisplayIndexes = "selected_display_indexes"
        case selectedMicrophoneIndex = "selected_microphone_index"
        case selectedMicrophoneName = "selected_microphone_name"
        case selectedMicrophoneUniqueID = "selected_microphone_unique_id"
        case selectedWebcamIndex = "selected_webcam_index"
        case screenshotIntervalSeconds = "screenshot_interval_seconds"
        case hideConsoleBeforeCapture = "hide_console_before_capture"
        case transcribeModel = "transcribe_model"
        case webcamEnabled = "webcam_enabled"
    }

    var microphonePreference: MicrophonePreference {
        MicrophonePreference(
            uniqueID: selectedMicrophoneUniqueID,
            name: selectedMicrophoneName,
            index: selectedMicrophoneIndex
        )
    }
}

private struct ScreenSnapshotTarget: Sendable {
    let deviceID: String
    let displayID: UInt32
    let displayName: String
}

private enum NativeRecordingStartError: LocalizedError {
    case noMediaWritersStarted

    var errorDescription: String? {
        switch self {
        case .noMediaWritersStarted:
            "No recording source started. Select a display, microphone, or camera and try again."
        }
    }
}

@MainActor
final class RecorderStore: ObservableObject {
    @Published var permissions = PermissionSnapshot()
    @Published var devices = DeviceInventory.empty
    @Published var ffmpegPath: String?
    @Published var selectedScreenIDs: Set<String> = []
    @Published var selectedAudioID: String?
    @Published var selectedWebcamID: String?
    @Published var webcamEnabled = false
    @Published var screenshotInterval = 5
    @Published var autoHideBeforeRecording = false
    @Published var transcribeModel: String = "openai_whisper-base"
    @Published var transcribeBinaryPath: String?
    @Published var recordingTitle: String = ""
    @Published var state: RecordingState = .idle
    @Published var elapsed: TimeInterval = 0
    @Published var activeTakeURL: URL?
    @Published var activeTakeTitle: String = ""
    @Published var takeTitleDraft: String = ""
    @Published var lastStartFailureLine: String?
    @Published var titleSaveInProgress = false
    @Published var importVideoInProgress = false
    @Published var recentImportCandidate: ImportCandidateSummary?
    @Published var recentImportCandidateLine: String = "No recent video import candidate found."
    @Published var storageOptimizeInProgress = false
    @Published var exportVideoInProgress = false
    @Published var lastExportedVideoURL: URL?
    @Published var activeTakeExportURL: URL?
    @Published var activeTakeExportLine: String = "No upload export yet."
    @Published var statusLines: [String] = []
    @Published var diskFreeBytes: Int64?
    @Published var microphoneLevel: Float = 0
    @Published var microphoneMeterStatus = "Meter idle"
    @Published var cameraPreviewSession: AVCaptureSession?
    @Published var cameraPreviewStatus = "Camera preview off"
    @Published var screenPreviewEnabled = false
    @Published var screenSnapshots: [String: NSImage] = [:]
    @Published var screenPreviewStatus: [String: String] = [:]
    @Published var countdownValue: Int?
    @Published var markers: [Marker] = []
    @Published var hudVisible: Bool = false
    @Published var hudExpanded: Bool = false
    @Published var scheduleState: RunMapScheduleState?
    @Published var scheduleStatus: String = "Run map idle"
    @Published var cameraCaptureStatusLine: String = "Camera capture idle"
    @Published var attentionStatusLine: String = "Attention telemetry idle"
    @Published var attentionDetailLine: String = "Recorded-screen focus will be written during recording."
    @Published var playbackPlayer: AVPlayer?
    @Published var playbackURL: URL?
    @Published var playbackTitle: String = "No playback loaded"
    @Published var playbackStatus: String = "Stop a recording to review it here."
    @Published var playbackSourceLabel: String = "No review asset"
    @Published var playbackSourceSystemImage: String = "play.rectangle"
    @Published var playbackCameraPlayer: AVPlayer?
    @Published var playbackCameraURL: URL?
    @Published var playbackCameraTitle: String = "Camera"
    @Published var playbackCameraOverlayLayout: CameraPIPLayout = .default
    @Published var playbackPosition: TimeInterval = 0
    @Published var playbackDuration: TimeInterval = 0
    @Published var playbackIsPlaying = false
    @Published var activeTakeReviewStatusLine: String = "No review asset yet."
    @Published var activeTakePostprocessStatusLine: String = "No package activity yet."
    @Published var activeTakePostprocessStage: String = ""
    @Published var activeTakePostprocessStatus: String = ""
    @Published var activeTakeSidecarRevision: Int = 0
    @Published var backgroundFinalizingTakeIDs: Set<String> = []
    @Published var backgroundBuildingTakeIDs: Set<String> = []
    @Published var recentTakes: [TakeSummary] = []
    @Published var pendingDeleteTake: TakeSummary?
    @Published var keyboardDeleteTargetTake: TakeSummary?

    private var discardedTakeIDsDuringStop: Set<String> = []
    private var timer: Timer?
    private var previewTimer: Timer?
    private var scheduleTimer: Timer?
    private var scheduleRefreshInFlight = false
    private var cameraHealthTimer: Timer?
    private var cameraHealthLastBytes: Int64?
    private var cameraHealthLastDurationSeconds: Double?
    private var cameraHealthLastFrameCount: Int?
    private var cameraHealthLastDistinctFrameCount: Int?
    private var cameraHealthLastGrowthAt: Date?
    private var cameraHealthLastVisualProgressAt: Date?
    private var cameraHealthWarningIssued = false
    private var cameraHealthRecoveryInFlight = false
    private var packageProgressTimer: Timer?
    private var playbackTimeObserver: Any?
    private var playbackEndObserver: NSObjectProtocol?
    private var hiddenConsoleWindows: [NSWindow] = []
    private var recordingStartedAt: Date?
    private var currentRecordingSegmentIndex = 0
    private var currentSegmentScreenTracks: [NativeScreenCaptureTrack] = []
    private var currentSegmentAudioTrack: NativeAudioCaptureTrack?
    private var currentSegmentCameraTrack: NativeCameraCaptureTrack?
    private var storageCheckpointTask: Task<Void, Never>?
    var storageCheckpointIntervalSeconds: TimeInterval = 10 * 60
    var cameraHealthPollIntervalSeconds: TimeInterval = 10
    var cameraHealthStallRecoverySeconds: TimeInterval = 60
    var cameraHealthVisualFreezeRecoverySeconds: TimeInterval = 120
    private var hasAppliedInitialDefaults = false
    private var webcamPreferenceChangedInCurrentRun = false
    private var savedMicrophonePreferenceIsUnavailable = false
    private var cachedSelectedAudioIsAvailable = true
    private var liveMicrophoneMonitorActive = false
    private let audioLevelMonitor: any AudioLevelMonitoring
    private let screenCaptureStatus: () -> CapabilityStatus
    private let requestScreenCaptureAccess: () -> CapabilityStatus
    private let microphonePermissionStatus: () -> CapabilityStatus
    private let audioDeviceAvailability: (CaptureDevice) -> Bool
    private let deviceInventoryCacheURL: URL
    private let recorderConfigURL: URL
    private let cameraPreviewService = CameraPreviewService()
    private let nativeScreenCaptureManager: any NativeScreenCaptureManaging
    private let nativeAudioCaptureManager: any NativeAudioCaptureManaging
    private let nativeCameraCaptureManager: any NativeCameraCaptureManaging
    private var screenRecordingRequestAlreadyIssued = false
    private lazy var attentionMonitor = RecordedScreenAttentionMonitor { [weak self] status in
        self?.attentionStatusLine = status.line
        self?.attentionDetailLine = status.detail
    }
    var onHudShouldShow: (() -> Void)?
    var onHudShouldHide: (() -> Void)?
    /// Recipient cue overlay binding (contract §7). Fired when a take starts /
    /// is about to stop so the overlay can bind the selected recipient + sidecar
    /// to the take. The overlay CANNOT start or stop recording; these are
    /// observation-only callbacks.
    var onTakeWillStart: (() async -> Bool)?
    var onTakeDidStart: ((_ takeID: String, _ takeRoot: URL) -> Void)?
    var onTakeWillStop: ((_ takeRoot: URL) -> Void)?
    // Mirror of the capture helper's LOCAL_STORAGE_HARD_FLOOR_BYTES in
    // support/demo_take_capture.py. The helper fail-closes a start below this
    // floor *before* it creates a take folder, so the UI must gate on the same
    // value — otherwise Start greenwashes ("Sources ready") and only fails after
    // the countdown with a cryptic "Start failed". Swift reads
    // volumeAvailableCapacityForImportantUsage (slightly higher than the helper's
    // statvfs free), so the helper remains the final authority on a borderline disk.
    private let minimumStartDiskBytes: Int64 = 10 * 1024 * 1024 * 1024

    init(
        audioLevelMonitor: any AudioLevelMonitoring = AudioLevelMonitor(),
        screenCaptureStatus: @escaping () -> CapabilityStatus = PermissionService.screenCaptureStatus,
        requestScreenCaptureAccess: @escaping () -> CapabilityStatus = PermissionService.requestScreenCaptureAccess,
        microphonePermissionStatus: @escaping () -> CapabilityStatus = PermissionService.microphoneStatus,
        audioDeviceAvailability: @escaping (CaptureDevice) -> Bool = AVCaptureDeviceIdentityResolver.isAudioDeviceAvailable,
        deviceInventoryCacheURL: URL = HostEnvironment.deviceInventoryCacheURL,
        recorderConfigURL: URL = HostEnvironment.recorderConfigURL,
        nativeScreenCaptureManager: any NativeScreenCaptureManaging = NativeScreenCaptureManager(),
        nativeAudioCaptureManager: any NativeAudioCaptureManaging = NativeAudioCaptureManager(),
        nativeCameraCaptureManager: any NativeCameraCaptureManaging = NativeCameraCaptureManager()
    ) {
        self.audioLevelMonitor = audioLevelMonitor
        self.screenCaptureStatus = screenCaptureStatus
        self.requestScreenCaptureAccess = requestScreenCaptureAccess
        self.microphonePermissionStatus = microphonePermissionStatus
        self.audioDeviceAvailability = audioDeviceAvailability
        self.deviceInventoryCacheURL = deviceInventoryCacheURL
        self.recorderConfigURL = recorderConfigURL
        self.nativeScreenCaptureManager = nativeScreenCaptureManager
        self.nativeAudioCaptureManager = nativeAudioCaptureManager
        self.nativeCameraCaptureManager = nativeCameraCaptureManager
        refreshTakeHistory()
        refreshRecentImportCandidate()
    }

    private var nativeCaptureWritersActive: Bool {
        nativeScreenCaptureManager.isRecording
            || nativeAudioCaptureManager.isRecording
            || nativeCameraCaptureManager.isRecording
    }

    private var preflightShouldPreserveCaptureState: Bool {
        if nativeCaptureWritersActive { return true }
        switch state {
        case .recording, .paused, .stopping, .postprocessing, .countingDown:
            return true
        default:
            return false
        }
    }

    var canMark: Bool {
        state == .recording || state == .paused || nativeCaptureWritersActive
    }

    var markerCount: Int { markers.count }

    var lastMarker: Marker? { markers.last }

    var canStart: Bool {
        canManageTakes && !nativeCaptureWritersActive && startBlockers.isEmpty
    }

    var canPauseOrResume: Bool {
        state == .recording || state == .paused || nativeCaptureWritersActive
    }

    var canStop: Bool {
        state == .recording || state == .paused || nativeCaptureWritersActive
    }

    var captureControlsActive: Bool {
        state == .recording || state == .paused || nativeCaptureWritersActive
    }

    var captureIsWriting: Bool {
        state == .recording || nativeCaptureWritersActive
    }

    var canDiscardTake: Bool {
        guard let activeTakeURL else { return false }
        return canDeleteTake(activeTakeURL)
    }

    var canRequestDeleteActiveTake: Bool {
        guard let activeTakeURL else { return false }
        return canDeleteTake(activeTakeURL)
    }

    var canRequestDeleteTargetTake: Bool {
        guard let targetURL = deleteTargetTakeURL else { return false }
        return canDeleteTake(targetURL)
    }

    func shouldRoutePlainDeleteToTake(textInputFocused: Bool) -> Bool {
        guard canRequestDeleteTargetTake, let targetURL = deleteTargetTakeURL else { return false }
        guard textInputFocused else { return true }
        guard let activeTakeURL else { return true }
        return !isSameTakeURL(targetURL, activeTakeURL)
    }

    private var deleteTargetTakeURL: URL? {
        if let keyboardDeleteTargetTake,
           recentTakes.contains(where: { isSameTakeURL($0.url, keyboardDeleteTargetTake.url) }) {
            return keyboardDeleteTargetTake.url
        }
        return activeTakeURL
    }

    var canManageTakes: Bool {
        if nativeCaptureWritersActive { return false }
        switch state {
        case .recording, .paused, .stopping, .postprocessing, .countingDown:
            return false
        default:
            return true
        }
    }

    var canBuildPackage: Bool {
        guard activeTakeURL != nil else { return false }
        return canManageTakes && !activeTakeHasBackgroundWork
    }

    var canPrepareActiveTakeReview: Bool {
        guard activeTakeURL != nil else { return false }
        return canManageTakes && !activeTakeHasBackgroundWork && activeTakeNeedsReviewPreparation
    }

    var canRenameActiveTake: Bool {
        guard activeTakeURL != nil, canManageTakes, !titleSaveInProgress, !activeTakeHasBackgroundWork else { return false }
        return normalizedTakeTitle(takeTitleDraft) != normalizedTakeTitle(activeTakeTitle)
    }

    var canImportVideo: Bool {
        canManageTakes && !importVideoInProgress
    }

    var canImportRecentVideoCandidate: Bool {
        canImportVideo && recentImportCandidate != nil
    }

    var canRevealRecentImportCandidate: Bool {
        guard let url = recentImportCandidate?.url else { return false }
        return FileManager.default.fileExists(atPath: url.path)
    }

    var canOptimizeStorage: Bool {
        activeTakeURL != nil && canManageTakes && !storageOptimizeInProgress && !activeTakeHasBackgroundWork
    }

    var canOptimizeAllStorage: Bool {
        canManageTakes && !storageOptimizeInProgress && recentTakes.contains { !isTakeBusy($0.url) }
    }

    var canExportVideo: Bool {
        guard let activeTakeURL else { return false }
        return canManageTakes
            && !exportVideoInProgress
            && !activeTakeHasBackgroundWork
            && videoAssetURL(for: activeTakeURL) != nil
    }

    var canOpenLastExport: Bool {
        guard let lastExportedVideoURL else { return false }
        return FileManager.default.fileExists(atPath: lastExportedVideoURL.path)
    }

    var canOpenActiveTakeExport: Bool {
        guard let activeTakeExportURL else { return false }
        return FileManager.default.fileExists(atPath: activeTakeExportURL.path)
    }

    var canPreviewActiveTakeExport: Bool {
        canOpenActiveTakeExport && isVideoAsset(activeTakeExportURL)
    }

    var canPreviewActiveTakeReview: Bool {
        guard let activeTakeURL else { return false }
        return !activeTakeNeedsReviewPreparation && playbackAssetURL(for: activeTakeURL) != nil
    }

    var canCopyActiveTakeExportPath: Bool {
        activeTakeExportURL != nil
    }

    var canRevealPlaybackAsset: Bool {
        guard let playbackURL else { return false }
        return FileManager.default.fileExists(atPath: playbackURL.path)
    }

    var canCopyPlaybackAssetPath: Bool {
        playbackURL != nil
    }

    var activeTakeDisplayName: String {
        let title = normalizedTakeTitle(activeTakeTitle)
        if !title.isEmpty {
            return title
        }
        return activeTakeURL?.lastPathComponent ?? "No take selected"
    }

    var playbackIsVideo: Bool {
        isVideoAsset(playbackURL)
    }

    var playbackHasCameraOverlay: Bool {
        playbackCameraPlayer != nil && playbackCameraURL != nil
    }

    var activeTakeIsFinalizing: Bool {
        guard let activeTakeURL else { return false }
        return backgroundFinalizingTakeIDs.contains(activeTakeURL.lastPathComponent)
    }

    var activeTakeIsBuildingPackage: Bool {
        guard let activeTakeURL else { return false }
        return backgroundBuildingTakeIDs.contains(activeTakeURL.lastPathComponent)
    }

    var activeTakeNeedsReviewPreparation: Bool {
        activeTakeManifestRecordingState() == "stopped"
    }

    var activeTakeHasBackgroundWork: Bool {
        activeTakeIsFinalizing || activeTakeIsBuildingPackage
    }

    var activeTakeReviewIsReady: Bool {
        if activeTakeNeedsReviewPreparation { return false }
        if playbackPlayer != nil { return true }
        guard let activeTakeURL else { return false }
        return playbackAssetURL(for: activeTakeURL) != nil
    }

    var activeTakePostprocessIsActive: Bool {
        activeTakePostprocessStatus == "running" || activeTakeIsFinalizing || activeTakeIsBuildingPackage || state == .postprocessing
    }

    var activeTakePostprocessIsComplete: Bool {
        activeTakePostprocessStage == "package_ready" && activeTakePostprocessStatus == "pass"
    }

    var activeTakePostprocessShortLabel: String {
        let label = progressStageLabel(activeTakePostprocessStage)
        return label == "Package" ? "building..." : label.lowercased()
    }

    var activeTakeBackgroundLine: String? {
        if activeTakeIsFinalizing {
            return "Replayable review is being prepared. New recording is still available."
        }
        if activeTakeIsBuildingPackage {
            return "Transcript/package sidecars are building in the background. New recording is still available."
        }
        return nil
    }

    var playbackFileLine: String {
        guard let playbackURL else { return "No playback file loaded." }
        let sizeSuffix = fileSize(at: playbackURL).map { " · \(HostEnvironment.byteString($0))" } ?? ""
        let cameraSuffix = playbackCameraURL.map { " · camera PiP: \($0.lastPathComponent)" } ?? ""
        return "\(playbackSourceLabel): \(playbackURL.lastPathComponent)\(sizeSuffix)\(cameraSuffix)"
    }

    var activeTakeStorageLine: String {
        guard let activeTakeURL else { return "" }
        return takeStorageLine(for: activeTakeURL)
    }

    var selectedScreens: [CaptureDevice] {
        Array(devices.videoDevices
            .filter { $0.isScreen && selectedScreenIDs.contains($0.id) }
            .sorted { $0.index < $1.index }
            .prefix(1))
    }

    var selectedAudio: CaptureDevice? {
        devices.audioDevices.first { $0.id == selectedAudioID }
    }

    var selectedAudioIsAvailable: Bool {
        cachedSelectedAudioIsAvailable
    }

    var selectedWebcam: CaptureDevice? {
        guard webcamEnabled else { return nil }
        return selectedWebcamCandidate
    }

    private var selectedWebcamCandidate: CaptureDevice? {
        return devices.videoDevices.first { $0.id == selectedWebcamID && $0.isLikelyWebcam }
    }

    var selectedScreenMetadata: [String: DisplayMetadata] {
        Dictionary(uniqueKeysWithValues: devices.videoDevices.filter(\.isScreen).map { device in
            (device.id, HostEnvironment.displayMetadata(forFFmpegScreenIndex: device.screenOrdinal))
        })
    }

    var displayPreviewIDs: [UInt32] {
        devices.videoDevices
            .filter(\.isScreen)
            .compactMap { selectedScreenMetadata[$0.id]?.displayID }
    }

    var setupTitle: String {
        if captureControlsActive {
            return state == .paused ? RecordingState.paused.label : RecordingState.recording.label
        }
        if activeTakeIsFinalizing { return "Preparing review" }
        if activeTakeIsBuildingPackage { return "Building package" }
        if state == .recording || state == .paused || state == .stopped || state == .postprocessing || state == .packageReady || state == .packageFailed {
            return state.label
        }
        if lastStartFailureLine != nil {
            return "Start failed"
        }
        return startBlockers.isEmpty ? "Ready to record" : "Setup needed"
    }

    var setupDetail: String {
        if captureControlsActive {
            return state == .paused
                ? "Recording paused; Resume or Stop controls this same take."
                : "Native capture is live; Stop controls this take."
        }
        if let activeTakeBackgroundLine {
            return activeTakeBackgroundLine
        }
        if let lastStartFailureLine {
            return lastStartFailureLine
        }
        if startBlockers.isEmpty {
            if selectedScreens.isEmpty {
                if selectedWebcam == nil {
                    return "Start records microphone audio only. No display or camera will be captured."
                }
                return "Start records the selected non-display sources. No display will be captured."
            }
            return autoHideBeforeRecording
                ? "Start runs a countdown, hides normal app windows only when they overlap the selected display, then starts native capture."
                : "Start records the selected display and microphone; private overlays are excluded while normal app windows remain visible."
        }
        return startBlockers.joined(separator: " · ")
    }

    var diskLine: String {
        "\(HostEnvironment.byteString(diskFreeBytes)) free"
    }

    var startDiskGateLine: String {
        guard let free = diskFreeBytes else {
            return "Start gate: unknown · \(HostEnvironment.byteString(minimumStartDiskBytes)) minimum"
        }
        let verdict = free >= minimumStartDiskBytes ? "OK" : "blocked"
        return "Start gate: \(verdict) · \(HostEnvironment.byteString(minimumStartDiskBytes)) minimum"
    }

    var pilotCapacityLine: String {
        guard let free = diskFreeBytes else { return "Pilot: unknown" }
        let pilot = estimatedBytes(seconds: 90)
        return "Pilot: \(free > pilot * 2 ? "OK" : "tight") · est. \(HostEnvironment.byteString(pilot))"
    }

    var longTakeCapacityLine: String {
        guard let free = diskFreeBytes else { return "Long take: unknown" }
        let long = estimatedBytes(seconds: 30 * 60)
        return "Long take: \(free > long * 2 ? "OK" : "tight") · est. \(HostEnvironment.byteString(long))"
    }

    var screenCaptureGateLine: String {
        if selectedScreens.isEmpty {
            return "macOS Screen Recording is not required without a selected display."
        }
        return permissions.screenCapture == .ready
            ? "macOS Screen Recording preflight is ready."
            : "macOS Screen Recording preflight denies this app bundle."
    }

    var screenCaptureGateDetail: String {
        "\(Bundle.main.bundleIdentifier ?? "unknown bundle") · \(Bundle.main.bundleURL.path)"
    }

    var needsScreenCapturePermission: Bool {
        !selectedScreens.isEmpty && permissions.screenCapture != .ready
    }

    var screenSourceStatus: CapabilityStatus {
        selectedScreens.isEmpty ? .notRequired : .ready
    }

    var microphoneSourceStatus: CapabilityStatus {
        guard selectedAudio != nil else { return .notRequired }
        guard permissions.microphone == .ready else { return .missing }
        return selectedAudioIsAvailable ? .ready : .missing
    }

    var cameraSourceStatus: CapabilityStatus {
        guard webcamEnabled else { return .notRequired }
        guard permissions.camera == .ready else { return .missing }
        return selectedWebcam == nil ? .missing : .ready
    }

    var startBlockers: [String] {
        var blockers: [String] = []
        if ffmpegPath == nil { blockers.append("FFmpeg not found") }
        if needsScreenCapturePermission { blockers.append(screenRecordingPreflightBlocker) }
        if selectedScreens.isEmpty && selectedAudio == nil && selectedWebcam == nil {
            blockers.append("Select at least one recording source")
        }
        if let selectedAudio {
            if permissions.microphone != .ready {
                blockers.append("Microphone permission needed")
            } else if !selectedAudioIsAvailable {
                blockers.append("\(selectedAudio.name) is not visible to macOS; reconnect it or Reload devices")
            }
        }
        if webcamEnabled {
            if permissions.camera != .ready {
                blockers.append("Camera permission needed")
            } else if selectedWebcam == nil {
                blockers.append("Select a camera or turn camera off")
            }
        }
        if permissions.disk == .low {
            blockers.append(
                "Free disk \(HostEnvironment.byteString(diskFreeBytes)) is below the "
                + "\(HostEnvironment.byteString(minimumStartDiskBytes)) recording floor — archive or prune takes first"
            )
        }
        return blockers
    }

    func reloadSetup() async {
        await refreshPreflight(probeDevices: true)
        appendStatus("Source list reloaded from FFmpeg. Start will run the real capture path without another device probe.")
    }

    func requestScreenRecordingPermission() async {
        if permissions.screenCapture == .ready {
            appendStatus("Screen Recording already passes preflight for \(screenCaptureGateDetail).")
            return
        }
        if screenRecordingRequestAlreadyIssued {
            appendStatus("Screen Recording request was already sent for this app run. Use Settings/Recheck instead of sending another macOS prompt.")
            await refreshPreflight()
            appendStatus(screenCaptureGateLine)
            return
        }
        screenRecordingRequestAlreadyIssued = true
        appendStatus("Requesting macOS Screen Recording permission for \(screenCaptureGateDetail).")
        permissions.screenCapture = requestScreenCaptureAccess()
        await refreshPreflight()
        appendStatus(screenCaptureGateLine)
    }

    func recheckScreenRecordingPermission() async {
        await refreshPreflight()
        appendStatus(screenCaptureGateLine)
    }

    func openScreenRecordingSettings() {
        let urls = [
            "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
            "x-apple.systempreferences:com.apple.SystemSettings.PrivacySecurity.extension?Privacy_ScreenCapture",
        ].compactMap(URL.init(string:))

        for url in urls where NSWorkspace.shared.open(url) {
            appendStatus("Opened Screen & System Audio Recording settings for \(screenCaptureGateDetail).")
            return
        }
        appendStatus("Could not open Screen Recording settings.")
    }

    func useSimpleDefaults() {
        applySimpleDefaults(announce: true)
        updateAudioMeter()
        updateCameraPreview()
        updateScreenPreviewPlaceholders()
    }

    func refreshPreflight(probeDevices: Bool = false) async {
        let preserveCaptureState = preflightShouldPreserveCaptureState
        ffmpegPath = HostEnvironment.findFFmpeg()
        permissions.ffmpeg = ffmpegPath == nil ? .missing : .ready
        transcribeBinaryPath = HostEnvironment.findTranscribeBinary()
        permissions.screenCapture = screenCaptureStatus()
        if permissions.screenCapture == .ready {
            screenRecordingRequestAlreadyIssued = false
        }
        permissions.microphone = microphonePermissionStatus()
        diskFreeBytes = HostEnvironment.availableDiskBytes(at: HostEnvironment.outputRoot)
        permissions.disk = diskStatus(bytes: diskFreeBytes)
        if !hasAppliedInitialDefaults {
            applyPersistedRecorderConfigIfAvailable()
        }

        if let ffmpegPath {
            if probeDevices {
                do {
                    devices = AVCaptureDeviceIdentityResolver.enrichInventory(
                        try await CaptureHelperClient.loadDevices(ffmpegPath: ffmpegPath)
                    )
                    persistDeviceInventory(devices)
                applyDefaultSelections()
            } catch {
                appendStatus("Could not enumerate FFmpeg AVFoundation devices: \(error.localizedDescription)")
                loadCachedOrPersistedDeviceInventoryIfNeeded()
            }
            } else {
                loadCachedOrPersistedDeviceInventoryIfNeeded()
                applyDefaultSelections()
            }
        }
        updateSelectedAudioAvailability()

        permissions.camera = PermissionService.cameraStatus(required: webcamEnabled)
        if nativeCaptureWritersActive {
            repairActiveNativeRecordingStateIfNeeded(reason: "Preflight refreshed while native capture writers were still active.")
        } else if !preserveCaptureState {
            state = startBlockers.isEmpty ? .ready : .setupNeeded
        }
        updateAudioMeter()
        updateCameraPreview()
        updateScreenPreviewPlaceholders()
        schedulePreviewTimer()
        refreshTakeHistory()
        refreshRecentImportCandidate()
    }

    func setScreen(_ device: CaptureDevice, enabled: Bool) {
        if enabled {
            selectedScreenIDs = [device.id]
        } else {
            selectedScreenIDs.remove(device.id)
        }
        persistDisplayPreference()
        updateScreenPreviewPlaceholders()
    }

    func selectAudio(_ id: String) {
        selectedAudioID = id.isEmpty ? nil : id
        savedMicrophonePreferenceIsUnavailable = false
        updateSelectedAudioAvailability()
        persistMicrophonePreference(selectedAudio)
        audioLevelMonitor.stop()
        liveMicrophoneMonitorActive = false
        microphoneLevel = 0
        updateAudioMeter()
    }

    func refreshMicrophoneMonitor() {
        guard let selectedAudio else {
            microphoneMeterStatus = "No microphone selected"
            microphoneLevel = 0
            return
        }
        permissions.microphone = microphonePermissionStatus()
        updateSelectedAudioAvailability()
        guard selectedAudioIsAvailable else {
            audioLevelMonitor.stop()
            liveMicrophoneMonitorActive = false
            microphoneLevel = 0
            microphoneMeterStatus = "\(selectedAudio.name) is not visible to macOS. Reconnect it, then Reload devices."
            return
        }
        microphoneLevel = 0
        microphoneMeterStatus = "Listening to \(selectedAudio.name)..."
        updateAudioMeter(forceRestart: true)
    }

    func setWebcamEnabled(_ enabled: Bool) {
        webcamPreferenceChangedInCurrentRun = true
        webcamEnabled = enabled
        if enabled, selectedWebcamCandidate == nil {
            selectedWebcamID = devices.videoDevices.first(where: { $0.isLikelyWebcam })?.id
        }
        permissions.camera = PermissionService.cameraStatus(required: webcamEnabled)
        persistWebcamPreference()
        updateCameraPreview()
    }

    func selectWebcam(_ id: String) {
        webcamPreferenceChangedInCurrentRun = true
        selectedWebcamID = id.isEmpty ? nil : id
        persistWebcamPreference()
        updateCameraPreview()
    }

    func identifyDisplay(_ device: CaptureDevice) {
        if DisplayIdentifyOverlay.flash(ffmpegScreenIndex: device.screenOrdinal) {
            let metadata = HostEnvironment.displayMetadata(forFFmpegScreenIndex: device.screenOrdinal)
            appendStatus("Identifying \(metadata.summary) for \(device.name) [\(device.index)].")
        } else {
            appendStatus("Could not map \(device.name) [\(device.index)] to an NSScreen for identify overlay.")
        }
    }

    func refreshScreenSnapshots() {
        screenPreviewEnabled = false
        screenSnapshots.removeAll()
        updateScreenPreviewPlaceholders(
            message: "Screenshot preview is disabled until the macOS permission loop is repaired."
        )
    }

    func startRecording() async {
        await refreshPreflight()
        lastStartFailureLine = nil
        let previousActiveTakeURL = activeTakeURL
        if needsScreenCapturePermission {
            state = .setupNeeded
            let line = "Start blocked: \(screenCaptureGateLine) Use Request once, grant the current /Applications bundle, quit/reopen if macOS asks, then Recheck."
            lastStartFailureLine = line
            appendPreStartAttempt("screen_capture_permission_blocked", detail: line)
            appendStatus(line)
            return
        }
        guard canStart, let ffmpegPath else {
            let reason = captureControlsActive
                ? "a recording is already active; use Stop before starting another take"
                : (startBlockers.isEmpty ? "recorder is busy" : startBlockers.joined(separator: ", "))
            let line = "Start blocked: \(reason)."
            lastStartFailureLine = line
            appendPreStartAttempt("start_blocked", detail: line)
            appendStatus(line)
            return
        }
        if let onTakeWillStart {
            let overlayReady = await onTakeWillStart()
            guard overlayReady else {
                state = startBlockers.isEmpty ? .ready : .setupNeeded
                let line = "Start blocked: cue overlay safety check did not pass; run Overlay > Run Safety Check before recording."
                lastStartFailureLine = line
                appendPreStartAttempt("cue_overlay_blocked", detail: line)
                appendStatus(line)
                return
            }
        }

        do {
            appendPreStartAttempt("countdown_begin", detail: "Start accepted; countdown begins.")
            state = .countingDown
            for value in stride(from: 3, through: 1, by: -1) {
                countdownValue = value
                try await Task.sleep(nanoseconds: 1_000_000_000)
            }
            countdownValue = nil
            stopConfidencePreviewForRecording()
            markers = []
            let hideConsole = shouldHideConsoleForRecording()
            showHud()
            if hideConsole {
                appendStatus("Console hidden because it overlaps the selected display; HUD remains available.")
                hideConsoleWindowsForRecording()
                try await Task.sleep(nanoseconds: 250_000_000)
            } else if autoHideBeforeRecording {
                appendStatus(autoHideSkipReasonForRecording())
            } else {
                appendStatus("Console remains visible; capture can include it while HUD and cue overlays stay excluded.")
            }

            let response = try await CaptureHelperClient.start(
                ffmpegPath: ffmpegPath,
                screens: selectedScreens,
                microphone: selectedAudio,
                webcam: nil,
                screenshotInterval: screenshotInterval,
                transcribeBinary: transcribeBinaryPath,
                transcribeModel: transcribeModel,
                takeTitle: recordingTitle,
                captureBackend: "screencapturekit"
            )
            let takeURL = URL(fileURLWithPath: response.rootPath, isDirectory: true)
            try await completeNativeStartAfterHelper(
                takeURL: takeURL,
                takeID: response.takeID,
                title: response.title ?? recordingTitle,
                helperStatusLines: response.statusLines
            )
        } catch {
            attentionMonitor.stop()
            try? await nativeCameraCaptureManager.stop()
            try? await nativeAudioCaptureManager.stop()
            try? await nativeScreenCaptureManager.stop()
            appendStartAttempt("start_failed", detail: error.localizedDescription)
            if let activeTakeURL, activeTakeURL.standardizedFileURL.path != previousActiveTakeURL?.standardizedFileURL.path {
                do {
                    let response = try await CaptureHelperClient.stopCapture(takeRoot: activeTakeURL)
                    for line in response.statusLines.reversed() {
                        appendStatus(line)
                    }
                    clearPlayback()
                    refreshActiveTakeProgress()
                    refreshActiveTakeExportStatus()
                    appendStatus("Partial take stopped without preparing review. Press Build to package it, or Prepare Review to inspect only.")
                } catch {
                    persistTakeKnownFailure("Partial take stop failed: \(error.localizedDescription).", to: activeTakeURL)
                    appendStatus("Partial take stop failed: \(error.localizedDescription).")
                }
            }
            let failureLine = "Recording start failed: \(error.localizedDescription)."
            if activeTakeURL == nil {
                appendPreStartAttempt("start_failed_before_take_root", detail: failureLine)
            }
            lastStartFailureLine = failureLine
            state = startBlockers.isEmpty ? .ready : .setupNeeded
            countdownValue = nil
            hideHud()
            restoreConsoleWindowsAfterRecording()
            appendStatus(failureLine)
            refreshTakeHistory()
            updateAudioMeter()
            updateCameraPreview()
            schedulePreviewTimer()
        }
    }

    func completeNativeStartAfterHelper(
        takeURL: URL,
        takeID: String,
        title: String,
        helperStatusLines: [String]
    ) async throws {
        activeTakeURL = takeURL
        appendStartAttempt("countdown_done", detail: "Countdown finished; helper package created.", takeURL: takeURL)
        appendStartAttempt("helper_start_ok", detail: takeID, takeURL: takeURL)
        let title = normalizedTakeTitle(title)
        activeTakeTitle = title
        takeTitleDraft = title
        recordingTitle = ""

        currentRecordingSegmentIndex = 1
        currentSegmentScreenTracks = []
        currentSegmentAudioTrack = nil
        currentSegmentCameraTrack = nil

        if selectedScreens.isEmpty {
            appendStatus("No display selected; skipping ScreenCaptureKit screen recording.")
            appendStartAttempt("screen_start_skipped", detail: "No display selected.", takeURL: takeURL)
        } else {
            appendStatus("Starting ScreenCaptureKit screen recording.")
            appendStartAttempt("screen_start_begin", takeURL: takeURL)
            let nativeTracks = try await nativeScreenCaptureManager.start(
                takeRoot: takeURL,
                screens: selectedScreens,
                segmentIndex: currentRecordingSegmentIndex
            )
            currentSegmentScreenTracks = nativeTracks
            appendStartAttempt(
                "screen_start_ok",
                detail: nativeTracks.map(\.relativePath).joined(separator: ", "),
                takeURL: takeURL
            )
            for track in nativeTracks {
                appendStatus("ScreenCaptureKit recording \(track.device.name) to \(track.relativePath).")
            }
        }

        if selectedWebcam == nil {
            appendStartAttempt("camera_start_skipped", detail: "No camera selected.", takeURL: takeURL)
        } else {
            appendStartAttempt("camera_start_begin", detail: selectedWebcam?.identityDescription, takeURL: takeURL)
            do {
                if let cameraTrack = try await nativeCameraCaptureManager.start(
                    takeRoot: takeURL,
                    webcam: selectedWebcam,
                    segmentIndex: currentRecordingSegmentIndex
                ) {
                    currentSegmentCameraTrack = cameraTrack
                    appendStatus("Native camera recording \(cameraTrack.device.name) to \(cameraTrack.relativePath).")
                    appendStartAttempt("camera_start_ok", detail: cameraTrack.relativePath, takeURL: takeURL)
                } else {
                    appendStartAttempt("camera_start_skipped", detail: "No camera selected.", takeURL: takeURL)
                }
            } catch {
                let warning = "Camera failed: \(error.localizedDescription); screen recording continues."
                persistTakeKnownFailure(warning, to: takeURL)
                appendStartAttempt("camera_start_failed", detail: error.localizedDescription, takeURL: takeURL)
                appendStatus(warning)
            }
        }

        if selectedAudio == nil {
            appendStartAttempt("audio_start_skipped", detail: "No microphone selected.", takeURL: takeURL)
            microphoneMeterStatus = "No microphone selected; screen recording continues."
        } else {
            appendStartAttempt("audio_start_begin", detail: selectedAudio?.identityDescription, takeURL: takeURL)
            audioLevelMonitor.stop()
            liveMicrophoneMonitorActive = false
            microphoneLevel = 0
            microphoneMeterStatus = "Starting microphone recorder..."
            do {
                if let audioTrack = try await nativeAudioCaptureManager.start(
                    takeRoot: takeURL,
                    microphone: selectedAudio,
                    segmentIndex: currentRecordingSegmentIndex,
                    onLevel: { [weak self] level, status in
                        self?.microphoneLevel = level
                        self?.microphoneMeterStatus = status
                    }
                ) {
                    currentSegmentAudioTrack = audioTrack
                    appendStatus("Native microphone recording \(audioTrack.device.name) to \(audioTrack.relativePath).")
                    appendStartAttempt("audio_start_ok", detail: audioTrack.relativePath, takeURL: takeURL)
                } else {
                    appendStartAttempt("audio_start_skipped", detail: "No microphone selected.", takeURL: takeURL)
                }
            } catch {
                let warning = "Mic failed: \(error.localizedDescription); screen recording continues."
                persistTakeKnownFailure(warning, to: takeURL)
                appendStartAttempt("audio_start_failed", detail: error.localizedDescription, takeURL: takeURL)
                appendStatus(warning)
                microphoneMeterStatus = warning
            }
        }
        try requireCurrentSegmentMedia(takeURL: takeURL, event: "media_start_empty")
        let timelineStartedAt = Date()
        state = .recording
        recordingStartedAt = timelineStartedAt
        startTimer()
        startScheduleTimer()
        scheduleStorageCheckpointTimer()
        appendStartAttempt("state_recording_set", detail: "Native media writers are live and synced to the take timeline.", takeURL: takeURL)
        persistOpenMediaSegment(
            index: currentRecordingSegmentIndex,
            screenTracks: currentSegmentScreenTracks,
            audioTrack: currentSegmentAudioTrack,
            cameraTrack: currentSegmentCameraTrack,
            timelineStartedAt: timelineStartedAt,
            to: takeURL
        )
        startCameraCaptureHealthMonitor()

        attentionMonitor.start(takeURL: takeURL, screen: selectedScreens.first)
        refreshTakeHistory()
        for line in helperStatusLines.reversed() {
            appendStatus(line)
        }
        appendStatus("Recording started: \(takeID).")
        onTakeDidStart?(takeID, takeURL)
    }

    func markClip(source: MarkerSource, label: String? = nil) {
        guard canMark, let activeTakeURL else { return }
        Task {
            do {
                let response = try await CaptureHelperClient.mark(
                    takeRoot: activeTakeURL,
                    source: source,
                    label: label
                )
                markers.append(response.marker)
                let labelPart = (label?.isEmpty == false) ? " \"\(label!)\"" : ""
                appendStatus("Marker [\(response.markerCount)] \(source.label) at \(String(format: "%.1f", response.marker.videoTSeconds))s\(labelPart).")
            } catch {
                appendStatus("Mark failed: \(error.localizedDescription).")
            }
        }
    }

    func togglePause() {
        repairActiveNativeRecordingStateIfNeeded(reason: "Pause/Resume was requested while native capture writers were still active.")
        guard state == .recording || state == .paused else { return }
        Task {
            if state == .recording {
                await pauseRecording()
            } else {
                await resumeRecording()
            }
        }
    }

    private func scheduleStorageCheckpointTimer() {
        storageCheckpointTask?.cancel()
        guard storageCheckpointIntervalSeconds > 0 else { return }
        let interval = UInt64(max(1.0, storageCheckpointIntervalSeconds) * 1_000_000_000)
        storageCheckpointTask = Task { [weak self] in
            while !Task.isCancelled {
                do {
                    try await Task.sleep(nanoseconds: interval)
                } catch {
                    return
                }
                guard !Task.isCancelled else { return }
                guard let self else { return }
                await self.checkpointRecordingSegmentForStorage(reason: "timer")
            }
        }
    }

    private func cancelStorageCheckpointTimer() {
        storageCheckpointTask?.cancel()
        storageCheckpointTask = nil
    }

    func pauseRecording() async {
        guard let activeTakeURL else { return }
        guard state == .recording else { return }
        cancelStorageCheckpointTimer()
        appendStartAttempt("pause_begin", detail: "Stopping native media writers.", takeURL: activeTakeURL)

        var pauseWarnings: [String] = []
        if let recordingStartedAt {
            elapsed = Date().timeIntervalSince(recordingStartedAt)
        }
        timer?.invalidate()
        scheduleTimer?.invalidate()
        stopCameraCaptureHealthMonitor("Camera capture paused")
        if nativeCameraCaptureManager.isRecording {
            do {
                try await nativeCameraCaptureManager.stop()
            } catch {
                pauseWarnings.append("Camera pause warning: \(error.localizedDescription)")
            }
        }
        if nativeAudioCaptureManager.isRecording {
            do {
                try await nativeAudioCaptureManager.stop()
            } catch {
                pauseWarnings.append("Microphone pause warning: \(error.localizedDescription)")
            }
        }
        if nativeScreenCaptureManager.isRecording {
            do {
                try await nativeScreenCaptureManager.stop()
            } catch {
                pauseWarnings.append("Screen pause warning: \(error.localizedDescription)")
            }
        }
        closeCurrentMediaSegment(status: "paused", in: activeTakeURL)
        let statusLines: [String]
        do {
            let response = try await CaptureHelperClient.pause(takeRoot: activeTakeURL)
            statusLines = response.statusLines
        } catch {
            let warning = "Pause bookkeeping warning: \(error.localizedDescription)"
            persistTakeKnownFailure(warning, to: activeTakeURL)
            appendStartAttempt("pause_helper_failed", detail: error.localizedDescription, takeURL: activeTakeURL)
            pauseWarnings.append(warning)
            statusLines = []
        }
        attentionMonitor.pause()
        state = .paused
        for warning in pauseWarnings {
            persistTakeKnownFailure(warning, to: activeTakeURL)
            appendStatus(warning)
        }
        for line in statusLines.reversed() { appendStatus(line) }
        appendStartAttempt(
            "pause_segment_closed",
            detail: String(format: "segment_%04d", currentRecordingSegmentIndex),
            takeURL: activeTakeURL
        )
        appendStatus("Recording paused. Native media writers stopped; the paused interval will be cut from review.")
    }

    func resumeRecording() async {
        guard let activeTakeURL else { return }
        guard state == .paused else { return }
        let nextSegment = max(currentRecordingSegmentIndex + 1, 2)
        appendStartAttempt(
            "resume_begin",
            detail: String(format: "Starting segment_%04d.", nextSegment),
            takeURL: activeTakeURL
        )

        do {
            var resumeWarnings: [String] = []
            currentRecordingSegmentIndex = nextSegment
            currentSegmentScreenTracks = []
            currentSegmentAudioTrack = nil
            currentSegmentCameraTrack = nil
            if selectedScreens.isEmpty {
                appendStartAttempt("resume_screen_start_skipped", detail: "No display selected.", takeURL: activeTakeURL)
            } else {
                let screenTracks = try await nativeScreenCaptureManager.start(
                    takeRoot: activeTakeURL,
                    screens: selectedScreens,
                    segmentIndex: nextSegment
                )
                currentSegmentScreenTracks = screenTracks
                appendStartAttempt(
                    "resume_screen_start_ok",
                    detail: screenTracks.map(\.relativePath).joined(separator: ", "),
                    takeURL: activeTakeURL
                )
            }

            if selectedWebcam == nil {
                appendStartAttempt("resume_camera_start_skipped", detail: "No camera selected.", takeURL: activeTakeURL)
            } else {
                appendStartAttempt("resume_camera_start_begin", detail: selectedWebcam?.identityDescription, takeURL: activeTakeURL)
                do {
                    if let cameraTrack = try await nativeCameraCaptureManager.start(
                        takeRoot: activeTakeURL,
                        webcam: selectedWebcam,
                        segmentIndex: nextSegment
                    ) {
                        currentSegmentCameraTrack = cameraTrack
                        appendStartAttempt("resume_camera_start_ok", detail: cameraTrack.relativePath, takeURL: activeTakeURL)
                    } else {
                        appendStartAttempt("resume_camera_start_skipped", detail: "No camera selected.", takeURL: activeTakeURL)
                    }
                } catch {
                    let warning = "Camera resume failed: \(error.localizedDescription); screen recording continues."
                    persistTakeKnownFailure(warning, to: activeTakeURL)
                    appendStartAttempt("resume_camera_start_failed", detail: error.localizedDescription, takeURL: activeTakeURL)
                    appendStatus(warning)
                    resumeWarnings.append(warning)
                }
            }

            if selectedAudio == nil {
                appendStartAttempt("resume_audio_start_skipped", detail: "No microphone selected.", takeURL: activeTakeURL)
            } else {
                appendStartAttempt("resume_audio_start_begin", detail: selectedAudio?.identityDescription, takeURL: activeTakeURL)
                audioLevelMonitor.stop()
                liveMicrophoneMonitorActive = false
                microphoneLevel = 0
                microphoneMeterStatus = "Resuming microphone recorder..."
                do {
                    if let audioTrack = try await nativeAudioCaptureManager.start(
                        takeRoot: activeTakeURL,
                        microphone: selectedAudio,
                        segmentIndex: nextSegment,
                        onLevel: { [weak self] level, status in
                            self?.microphoneLevel = level
                            self?.microphoneMeterStatus = status
                        }
                    ) {
                        currentSegmentAudioTrack = audioTrack
                        appendStartAttempt("resume_audio_start_ok", detail: audioTrack.relativePath, takeURL: activeTakeURL)
                    } else {
                        appendStartAttempt("resume_audio_start_skipped", detail: "No microphone selected.", takeURL: activeTakeURL)
                    }
                } catch {
                    let warning = "Mic resume failed: \(error.localizedDescription); screen recording continues."
                    persistTakeKnownFailure(warning, to: activeTakeURL)
                    appendStartAttempt("resume_audio_start_failed", detail: error.localizedDescription, takeURL: activeTakeURL)
                    appendStatus(warning)
                    microphoneMeterStatus = warning
                }
            }
            try requireCurrentSegmentMedia(takeURL: activeTakeURL, event: "resume_media_start_empty")
            let statusLines: [String]
            do {
                let response = try await CaptureHelperClient.resume(takeRoot: activeTakeURL)
                statusLines = response.statusLines
            } catch {
                let warning = "Resume bookkeeping warning: \(error.localizedDescription)"
                persistTakeKnownFailure(warning, to: activeTakeURL)
                appendStartAttempt("resume_helper_failed", detail: error.localizedDescription, takeURL: activeTakeURL)
                resumeWarnings.append(warning)
                statusLines = []
            }
            let timelineStartedAt = Date()
            persistOpenMediaSegment(
                index: currentRecordingSegmentIndex,
                screenTracks: currentSegmentScreenTracks,
                audioTrack: currentSegmentAudioTrack,
                cameraTrack: currentSegmentCameraTrack,
                timelineStartedAt: timelineStartedAt,
                to: activeTakeURL
            )
            startCameraCaptureHealthMonitor()
            attentionMonitor.resume()
            recordingStartedAt = timelineStartedAt.addingTimeInterval(-elapsed)
            startTimer()
            startScheduleTimer()
            scheduleStorageCheckpointTimer()
            state = .recording
            for warning in resumeWarnings {
                appendStatus(warning)
            }
            for line in statusLines.reversed() { appendStatus(line) }
            appendStatus(String(format: "Recording resumed: segment_%04d writing.", currentRecordingSegmentIndex))
        } catch {
            try? await nativeCameraCaptureManager.stop()
            try? await nativeAudioCaptureManager.stop()
            try? await nativeScreenCaptureManager.stop()
            appendStartAttempt("resume_failed", detail: error.localizedDescription, takeURL: activeTakeURL)
            appendStatus("Resume failed: \(error.localizedDescription). Recording remains paused.")
        }
    }

    func checkpointRecordingSegmentForStorage(reason: String = "manual") async {
        guard let activeTakeURL else { return }
        guard state == .recording else { return }
        cancelStorageCheckpointTimer()
        let closingSegment = currentRecordingSegmentIndex
        let nextSegment = max(currentRecordingSegmentIndex + 1, 2)
        let elapsedBeforeCheckpoint = recordingStartedAt.map { Date().timeIntervalSince($0) } ?? elapsed
        appendStartAttempt(
            "storage_checkpoint_begin",
            detail: String(format: "Closing segment_%04d; opening segment_%04d (%@).", closingSegment, nextSegment, reason),
            takeURL: activeTakeURL
        )
        stopCameraCaptureHealthMonitor("Camera checkpoint closing current segment")

        var checkpointWarnings: [String] = []
        if nativeCameraCaptureManager.isRecording {
            do {
                try await nativeCameraCaptureManager.stop()
            } catch {
                checkpointWarnings.append("Camera checkpoint stop warning: \(error.localizedDescription)")
            }
        }
        if nativeAudioCaptureManager.isRecording {
            do {
                try await nativeAudioCaptureManager.stop()
            } catch {
                checkpointWarnings.append("Microphone checkpoint stop warning: \(error.localizedDescription)")
            }
        }
        if nativeScreenCaptureManager.isRecording {
            do {
                try await nativeScreenCaptureManager.stop()
            } catch {
                checkpointWarnings.append("Screen checkpoint stop warning: \(error.localizedDescription)")
            }
        }
        closeCurrentMediaSegment(status: "checkpointed", in: activeTakeURL)

        do {
            currentRecordingSegmentIndex = nextSegment
            currentSegmentScreenTracks = []
            currentSegmentAudioTrack = nil
            currentSegmentCameraTrack = nil
            if selectedScreens.isEmpty {
                appendStartAttempt("storage_checkpoint_screen_start_skipped", detail: "No display selected.", takeURL: activeTakeURL)
            } else {
                let screenTracks = try await nativeScreenCaptureManager.start(
                    takeRoot: activeTakeURL,
                    screens: selectedScreens,
                    segmentIndex: nextSegment
                )
                currentSegmentScreenTracks = screenTracks
                appendStartAttempt(
                    "storage_checkpoint_screen_start_ok",
                    detail: screenTracks.map(\.relativePath).joined(separator: ", "),
                    takeURL: activeTakeURL
                )
            }

            if selectedWebcam == nil {
                appendStartAttempt("storage_checkpoint_camera_start_skipped", detail: "No camera selected.", takeURL: activeTakeURL)
            } else {
                do {
                    if let cameraTrack = try await nativeCameraCaptureManager.start(
                        takeRoot: activeTakeURL,
                        webcam: selectedWebcam,
                        segmentIndex: nextSegment
                    ) {
                        currentSegmentCameraTrack = cameraTrack
                        appendStartAttempt("storage_checkpoint_camera_start_ok", detail: cameraTrack.relativePath, takeURL: activeTakeURL)
                    } else {
                        appendStartAttempt("storage_checkpoint_camera_start_skipped", detail: "No camera selected.", takeURL: activeTakeURL)
                    }
                } catch {
                    let warning = "Camera checkpoint restart failed: \(error.localizedDescription); screen recording continues."
                    persistTakeKnownFailure(warning, to: activeTakeURL)
                    checkpointWarnings.append(warning)
                    appendStartAttempt("storage_checkpoint_camera_start_failed", detail: error.localizedDescription, takeURL: activeTakeURL)
                }
            }

            if selectedAudio == nil {
                appendStartAttempt("storage_checkpoint_audio_start_skipped", detail: "No microphone selected.", takeURL: activeTakeURL)
            } else {
                audioLevelMonitor.stop()
                liveMicrophoneMonitorActive = false
                microphoneLevel = 0
                microphoneMeterStatus = "Restarting microphone recorder for storage checkpoint..."
                do {
                    if let audioTrack = try await nativeAudioCaptureManager.start(
                        takeRoot: activeTakeURL,
                        microphone: selectedAudio,
                        segmentIndex: nextSegment,
                        onLevel: { [weak self] level, status in
                            self?.microphoneLevel = level
                            self?.microphoneMeterStatus = status
                        }
                    ) {
                        currentSegmentAudioTrack = audioTrack
                        appendStartAttempt("storage_checkpoint_audio_start_ok", detail: audioTrack.relativePath, takeURL: activeTakeURL)
                    } else {
                        appendStartAttempt("storage_checkpoint_audio_start_skipped", detail: "No microphone selected.", takeURL: activeTakeURL)
                    }
                } catch {
                    let warning = "Mic checkpoint restart failed: \(error.localizedDescription); screen recording continues."
                    persistTakeKnownFailure(warning, to: activeTakeURL)
                    checkpointWarnings.append(warning)
                    appendStartAttempt("storage_checkpoint_audio_start_failed", detail: error.localizedDescription, takeURL: activeTakeURL)
                    microphoneMeterStatus = warning
                }
            }
            try requireCurrentSegmentMedia(takeURL: activeTakeURL, event: "storage_checkpoint_media_start_empty")

            let timelineStartedAt = Date()
            persistOpenMediaSegment(
                index: currentRecordingSegmentIndex,
                screenTracks: currentSegmentScreenTracks,
                audioTrack: currentSegmentAudioTrack,
                cameraTrack: currentSegmentCameraTrack,
                timelineStartedAt: timelineStartedAt,
                to: activeTakeURL
            )
            startCameraCaptureHealthMonitor()
            recordingStartedAt = timelineStartedAt.addingTimeInterval(-elapsedBeforeCheckpoint)
            state = .recording
            for warning in checkpointWarnings {
                appendStatus(warning)
            }
            appendStartAttempt(
                "storage_checkpoint_segment_opened",
                detail: String(format: "segment_%04d", currentRecordingSegmentIndex),
                takeURL: activeTakeURL
            )
            appendStatus(String(format: "Storage checkpoint closed segment_%04d; segment_%04d is now writing.", closingSegment, currentRecordingSegmentIndex))
            scheduleStorageCheckpointTimer()
        } catch {
            try? await nativeCameraCaptureManager.stop()
            try? await nativeAudioCaptureManager.stop()
            try? await nativeScreenCaptureManager.stop()
            elapsed = elapsedBeforeCheckpoint
            timer?.invalidate()
            scheduleTimer?.invalidate()
            attentionMonitor.pause()
            state = .paused
            let warning = "Storage checkpoint restart failed: \(error.localizedDescription). Closed segment is recoverable; recording is paused."
            persistTakeKnownFailure(warning, to: activeTakeURL)
            appendStartAttempt("storage_checkpoint_restart_failed", detail: error.localizedDescription, takeURL: activeTakeURL)
            appendStatus(warning)
        }
    }

    func stopRecording() async {
        guard let activeTakeURL else { return }
        onTakeWillStop?(activeTakeURL)
        pausePlayback()
        cancelStorageCheckpointTimer()
        timer?.invalidate()
        scheduleTimer?.invalidate()
        stopCameraCaptureHealthMonitor("Camera capture stopping")
        attentionMonitor.stop()
        state = .stopping
        startPackageProgressTimer()
        appendStatus("Stopping capture processes.")

        var captureWarnings: [String] = []
        if nativeCameraCaptureManager.isRecording {
            appendStatus("Stopping native camera recorder.")
            do {
                try await nativeCameraCaptureManager.stop()
            } catch {
                captureWarnings.append("Camera capture warning: \(error.localizedDescription)")
            }
        }
        if nativeAudioCaptureManager.isRecording {
            appendStatus("Stopping native microphone recorder.")
            do {
                try await nativeAudioCaptureManager.stop()
            } catch {
                captureWarnings.append("Microphone capture warning: \(error.localizedDescription)")
            }
        }
        if nativeScreenCaptureManager.isRecording {
            appendStatus("Stopping ScreenCaptureKit screen recorder.")
            do {
                try await nativeScreenCaptureManager.stop()
            } catch {
                captureWarnings.append("Screen capture warning: \(error.localizedDescription)")
            }
        }
        closeCurrentMediaSegment(status: "stopped", in: activeTakeURL)
        for warning in captureWarnings.reversed() {
            persistTakeKnownFailure(warning, to: activeTakeURL)
            appendStatus(warning)
        }
        hideHud()
        restoreConsoleWindowsAfterRecording()
        let stoppedTakeURL = activeTakeURL
        let stoppedTakeID = stoppedTakeURL.lastPathComponent

        appendStatus("Stopping capture containers for \(stoppedTakeID); replayable review can be prepared later.")
        do {
            let response = try await CaptureHelperClient.stopCapture(takeRoot: stoppedTakeURL)
            if consumeStopDiscard(for: stoppedTakeID, takeURL: stoppedTakeURL) {
                appendStatus("Discarded \(stoppedTakeID); ignored late stop-cleanup result.")
            } else {
                for line in response.statusLines.reversed() {
                    appendStatus(line)
                }
                if self.activeTakeURL?.path == stoppedTakeURL.path {
                    clearPlayback()
                    refreshActiveTakeProgress()
                    refreshActiveTakeExportStatus()
                    state = .stopped
                    stopPackageProgressTimerIfIdle()
                }
                appendStatus("Capture stopped for \(stoppedTakeID). Press Build when you want review media, transcript, and package sidecars; Start is available for a new take.")
            }
        } catch {
            if consumeStopDiscard(for: stoppedTakeID, takeURL: stoppedTakeURL) {
                appendStatus("Discarded \(stoppedTakeID); ignored late stop-cleanup failure.")
            } else {
                persistTakeKnownFailure("Capture stop failed: \(error.localizedDescription).", to: stoppedTakeURL)
                if self.activeTakeURL?.path == stoppedTakeURL.path {
                    clearPlayback()
                    refreshActiveTakeProgress()
                    refreshActiveTakeExportStatus()
                    state = .packageFailed
                    stopPackageProgressTimerIfIdle()
                }
                appendStatus("Capture stop failed for \(stoppedTakeID): \(error.localizedDescription).")
            }
        }

        recordingStartedAt = nil
        elapsed = 0
        currentRecordingSegmentIndex = 0
        currentSegmentScreenTracks = []
        currentSegmentAudioTrack = nil
        currentSegmentCameraTrack = nil
        refreshTakeHistory()
        updateAudioMeter()
        updateCameraPreview()
        schedulePreviewTimer()
        scheduleState = nil
        scheduleStatus = "Run map idle"
    }

    func prepareActiveTakeReview() async {
        guard let targetTakeURL = activeTakeURL, canPrepareActiveTakeReview else { return }
        let takeID = targetTakeURL.lastPathComponent
        pausePlayback()
        backgroundFinalizingTakeIDs.insert(takeID)
        startPackageProgressTimer()
        appendStatus("Preparing replayable review for \(takeID); Start remains available for a new take.")
        defer {
            backgroundFinalizingTakeIDs.remove(takeID)
            refreshTakeHistory()
            refreshActiveTakeProgress()
            stopPackageProgressTimerIfIdle()
        }

        do {
            let response = try await CaptureHelperClient.finalize(takeRoot: targetTakeURL)
            for line in response.statusLines.reversed() {
                appendStatus(line)
            }
            let hasReviewVideo = videoAssetURL(for: targetTakeURL) != nil
            let stillSelected = activeTakeURL?.path == targetTakeURL.path
            if stillSelected {
                loadPlaybackAsset(from: targetTakeURL)
                refreshActiveTakeProgress()
                refreshActiveTakeExportStatus()
                state = hasReviewVideo ? .reviewReady : .packageFailed
            }
            if hasReviewVideo {
                appendStatus("Review prepared for \(takeID). Build remains available for transcript/package sidecars.")
                if stillSelected, let diagnosis = mediaDiagnosisLine(for: targetTakeURL) {
                    appendStatus(diagnosis)
                }
            } else {
                appendStatus("Review blocked for \(takeID): \(mediaDiagnosisLine(for: targetTakeURL) ?? "no usable screen video was found").")
            }
        } catch {
            persistTakeKnownFailure("Review preparation failed: \(error.localizedDescription).", to: targetTakeURL)
            if activeTakeURL?.path == targetTakeURL.path {
                loadPlaybackAsset(from: targetTakeURL)
                refreshActiveTakeProgress()
                refreshActiveTakeExportStatus()
                state = .packageFailed
            }
            appendStatus("Review preparation failed for \(takeID): \(error.localizedDescription).")
        }
    }

    func buildPackageSidecars() async {
        guard let targetTakeURL = activeTakeURL, canBuildPackage else { return }
        let takeID = targetTakeURL.lastPathComponent
        let needsFullPostprocess = activeTakeNeedsReviewPreparation
        guard !backgroundBuildingTakeIDs.contains(takeID) else {
            appendStatus("Package build already running for \(takeID).")
            return
        }
        pausePlayback()
        backgroundBuildingTakeIDs.insert(takeID)
        startPackageProgressTimer()
        appendStatus("Building package for \(takeID) in the background; Start remains available for a new take.")
        defer {
            backgroundBuildingTakeIDs.remove(takeID)
            refreshTakeHistory()
            refreshActiveTakeProgress()
            notifyActiveTakeSidecarsChanged(for: targetTakeURL)
            stopPackageProgressTimerIfIdle()
        }

        do {
            let response = needsFullPostprocess
                ? try await CaptureHelperClient.postprocess(takeRoot: targetTakeURL)
                : try await CaptureHelperClient.transcribe(takeRoot: targetTakeURL)
            for line in response.statusLines.reversed() {
                appendStatus(line)
            }
            let hasReviewVideo = videoAssetURL(for: targetTakeURL) != nil
            let knownFailures = response.knownFailures ?? []
            let transcriptReady = response.result?.status == "ready" || transcriptSidecarIsReady(for: targetTakeURL)
            let packageReady = transcriptReady || knownFailures.isEmpty || recordingState(for: targetTakeURL) == "package_ready"
            let stillSelected = activeTakeURL?.path == targetTakeURL.path
            if stillSelected {
                loadPlaybackAsset(from: targetTakeURL)
                refreshActiveTakeProgress()
                refreshActiveTakeExportStatus()
                state = packageReady ? .packageReady : (hasReviewVideo ? .reviewReady : .packageFailed)
            }
            if transcriptReady {
                appendStatus("Package build finished for \(takeID).")
            } else if packageReady {
                appendStatus("Package build finished for \(takeID); transcript is not ready.")
            } else if hasReviewVideo {
                appendStatus("Transcript unavailable for \(takeID); review video is still available.")
                if stillSelected, let diagnosis = mediaDiagnosisLine(for: targetTakeURL) {
                    appendStatus(diagnosis)
                }
            } else {
                appendStatus("Transcript build failed for \(takeID): \(mediaDiagnosisLine(for: targetTakeURL) ?? "no usable screen video was found").")
            }
        } catch {
            if activeTakeURL?.path == targetTakeURL.path {
                state = .packageFailed
                loadPlaybackAsset(from: targetTakeURL)
                refreshActiveTakeProgress()
                refreshActiveTakeExportStatus()
            }
            appendStatus("Package build failed for \(takeID): \(error.localizedDescription).")
        }
    }

    func notifyActiveTakeSidecarsChanged(for takeURL: URL) {
        guard activeTakeURL?.standardizedFileURL.path == takeURL.standardizedFileURL.path else { return }
        activeTakeSidecarRevision &+= 1
    }

    func saveActiveTakeTitle() async {
        guard let activeTakeURL, canRenameActiveTake else { return }
        let title = normalizedTakeTitle(takeTitleDraft)
        titleSaveInProgress = true
        defer { titleSaveInProgress = false }

        do {
            let response = try await CaptureHelperClient.setTitle(takeRoot: activeTakeURL, title: title)
            activeTakeTitle = normalizedTakeTitle(response.title ?? title)
            takeTitleDraft = activeTakeTitle
            for line in response.statusLines.reversed() {
                appendStatus(line)
            }
            refreshTakeHistory()
        } catch {
            appendStatus("Rename failed: \(error.localizedDescription).")
        }
    }

    func importVideoFromPanel() {
        guard canImportVideo else { return }
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        panel.allowedContentTypes = [
            UTType(filenameExtension: "mp4") ?? .movie,
            UTType(filenameExtension: "mov") ?? .movie,
            UTType(filenameExtension: "m4v") ?? .movie,
        ]
        panel.begin { [weak self] response in
            guard response == .OK, let url = panel.url else { return }
            Task { @MainActor in
                await self?.importVideo(sourceURL: url)
            }
        }
    }

    func refreshRecentImportCandidate(announce: Bool = false) {
        recentImportCandidate = newestImportCandidate()
        if let candidate = recentImportCandidate {
            recentImportCandidateLine = "\(candidate.name) · \(candidate.detailLine) · \(candidate.sizeLine)"
            if announce {
                appendStatus("Latest import candidate: \(candidate.name).")
            }
        } else {
            recentImportCandidateLine = "No MP4, MOV, or M4V found in Downloads, Desktop, or Movies."
            if announce {
                appendStatus(recentImportCandidateLine)
            }
        }
    }

    func importRecentVideoCandidate() async {
        guard canImportVideo else { return }
        refreshRecentImportCandidate()
        guard let candidate = recentImportCandidate else {
            appendStatus(recentImportCandidateLine)
            return
        }
        await importVideo(sourceURL: candidate.url)
    }

    func revealRecentImportCandidate() {
        refreshRecentImportCandidate()
        guard let url = recentImportCandidate?.url else {
            appendStatus(recentImportCandidateLine)
            return
        }
        guard FileManager.default.fileExists(atPath: url.path) else {
            appendStatus("Import candidate is missing: \(url.lastPathComponent).")
            refreshRecentImportCandidate()
            return
        }
        NSWorkspace.shared.activateFileViewerSelecting([url])
    }

    func copyRecentImportCandidatePath() {
        refreshRecentImportCandidate()
        guard let url = recentImportCandidate?.url else {
            appendStatus(recentImportCandidateLine)
            return
        }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(url.path, forType: .string)
        appendStatus("Copied import candidate path: \(url.lastPathComponent).")
    }

    func importVideoFromDropProviders(_ providers: [NSItemProvider]) -> Bool {
        guard canImportVideo else {
            appendStatus("Stop the current recording before importing dropped video.")
            return false
        }
        guard let provider = providers.first(where: { $0.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) }) else {
            appendStatus("Drop import ignored: no file URL was provided.")
            return false
        }
        provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { [weak self] item, error in
            if let error {
                Task { @MainActor in
                    self?.appendStatus("Drop import failed: \(error.localizedDescription).")
                }
                return
            }
            let url = Self.fileURL(fromProviderItem: item)
            Task { @MainActor in
                guard let self else { return }
                guard let url, self.isSupportedVideoURL(url) else {
                    self.appendStatus("Drop import ignored: use an MP4, MOV, or M4V file.")
                    return
                }
                let scoped = url.startAccessingSecurityScopedResource()
                defer {
                    if scoped {
                        url.stopAccessingSecurityScopedResource()
                    }
                }
                await self.importVideo(sourceURL: url)
            }
        }
        return true
    }

    func importVideo(sourceURL: URL) async {
        guard canImportVideo else { return }
        importVideoInProgress = true
        defer { importVideoInProgress = false }

        let title = normalizedTakeTitle(recordingTitle)
        do {
            let response = try await CaptureHelperClient.importVideo(sourceURL: sourceURL, title: title)
            pausePlayback()
            let takeURL = URL(fileURLWithPath: response.rootPath, isDirectory: true)
            activeTakeURL = takeURL
            let importedTitle = normalizedTakeTitle(response.title ?? title)
            activeTakeTitle = importedTitle
            takeTitleDraft = importedTitle
            recordingTitle = ""
            elapsed = 0
            markers = []
            recordingStartedAt = nil
            scheduleState = nil
            scheduleStatus = "Run map idle"
            loadPlaybackAsset(from: takeURL)
            state = .reviewReady
            refreshTakeHistory()
            refreshRecentImportCandidate()
            for line in response.statusLines.reversed() {
                appendStatus(line)
            }
            appendStatus("Imported video ready for review: \(response.asset ?? "rough cut").")
        } catch {
            appendStatus("Import failed: \(error.localizedDescription).")
        }
    }

    func optimizeActiveTakeStorage() async {
        guard let activeTakeURL, canOptimizeStorage else { return }
        pausePlayback()
        storageOptimizeInProgress = true
        defer { storageOptimizeInProgress = false }
        appendStatus("Optimizing storage without re-encoding video.")

        do {
            let response = try await CaptureHelperClient.compactStorage(takeRoot: activeTakeURL)
            for line in response.statusLines.reversed() {
                appendStatus(line)
            }
            loadPlaybackAsset(from: activeTakeURL)
            refreshTakeHistory()
            if let saved = response.bytesSaved, saved > 0 {
                appendStatus("Storage saved: \(HostEnvironment.byteString(saved)).")
            }
        } catch {
            appendStatus("Storage optimize failed: \(error.localizedDescription).")
            loadPlaybackAsset(from: activeTakeURL)
            refreshTakeHistory()
        }
    }

    func optimizeAllSavedTakeStorage() async {
        guard canOptimizeAllStorage else { return }
        pausePlayback()
        storageOptimizeInProgress = true
        defer { storageOptimizeInProgress = false }

        let targets = recentTakes.map(\.url).filter { !isTakeBusy($0) }
        guard !targets.isEmpty else {
            appendStatus("Storage optimize skipped: all visible takes are still finishing background work.")
            return
        }
        var savedTotal: Int64 = 0
        var completed = 0
        var failed = 0
        appendStatus("Optimizing \(targets.count) saved take package(s).")

        for takeURL in targets {
            do {
                let response = try await CaptureHelperClient.compactStorage(takeRoot: takeURL)
                savedTotal += response.bytesSaved ?? 0
                completed += 1
            } catch {
                failed += 1
                appendStatus("Storage optimize failed for \(takeURL.lastPathComponent): \(error.localizedDescription).")
            }
        }

        if let activeTakeURL {
            loadPlaybackAsset(from: activeTakeURL)
        }
        refreshTakeHistory()
        let failedSuffix = failed > 0 ? " · \(failed) failed" : ""
        appendStatus("Storage pass complete: \(completed)/\(targets.count) packages · \(HostEnvironment.byteString(savedTotal)) saved\(failedSuffix).")
    }

    func refreshActiveTakeStorageStatus() async {
        guard let activeTakeURL else { return }
        do {
            let response = try await CaptureHelperClient.storageStatus(takeRoot: activeTakeURL)
            if let storageLine = response.storageLine {
                appendStatus("Storage: \(storageLine).")
            }
            refreshTakeHistory()
        } catch {
            appendStatus("Storage status unavailable: \(error.localizedDescription).")
        }
    }

    func exportActiveTakeVideo() async {
        guard let activeTakeURL, canExportVideo else { return }
        pausePlayback()
        exportVideoInProgress = true
        defer { exportVideoInProgress = false }
        appendStatus("Exporting upload-ready video without re-encoding.")

        do {
            let response = try await CaptureHelperClient.exportVideo(takeRoot: activeTakeURL)
            for line in response.statusLines.reversed() {
                appendStatus(line)
            }
            let exportURL = URL(fileURLWithPath: response.exportPath)
            lastExportedVideoURL = exportURL
            refreshActiveTakeExportStatus()
            refreshTakeHistory()
            previewActiveTakeExport()
            appendStatus("Export ready: \(response.exportRelativePath ?? exportURL.lastPathComponent).")
        } catch {
            refreshActiveTakeExportStatus()
            appendStatus("Export failed: \(error.localizedDescription).")
        }
    }

    private func showHud() {
        hudExpanded = false
        hudVisible = true
        onHudShouldShow?()
    }

    func toggleHudExpanded() {
        hudExpanded.toggle()
    }

    private func hideHud() {
        hudVisible = false
        onHudShouldHide?()
    }

    private func shouldHideConsoleForRecording() -> Bool {
        guard autoHideBeforeRecording else { return false }
        let selectedDisplayIDs = selectedScreensDisplayIDs()
        guard !selectedDisplayIDs.isEmpty else { return false }
        return consoleWindowsForCapture().contains { window in
            HostEnvironment.window(window, intersectsAnyDisplayID: selectedDisplayIDs)
        }
    }

    private func autoHideSkipReasonForRecording() -> String {
        let selectedDisplayIDs = selectedScreensDisplayIDs()
        if selectedDisplayIDs.isEmpty {
            return "Console stays visible; selected display mapping is ambiguous."
        }
        if consoleWindowsForCapture().isEmpty {
            return "Console stays visible; no normal console window is on screen."
        }
        return "Console stays visible because it is on a different display from the capture target; private overlays stay excluded."
    }

    private func hideConsoleWindowsForRecording() {
        hiddenConsoleWindows = consoleWindowsForCapture()
        for window in hiddenConsoleWindows {
            window.orderOut(nil)
        }
    }

    private func restoreConsoleWindowsAfterRecording() {
        let windows = hiddenConsoleWindows
        hiddenConsoleWindows = []
        if windows.isEmpty {
            NSApp.unhide(nil)
            NSApp.activate(ignoringOtherApps: true)
            return
        }
        for window in windows where !window.isMiniaturized {
            window.makeKeyAndOrderFront(nil)
        }
        NSApp.unhide(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func consoleWindowsForCapture() -> [NSWindow] {
        NSApp.windows.filter { window in
            guard window.isVisible, !window.isMiniaturized else { return false }
            guard !(window is NSPanel) else { return false }
            guard window.level == .normal else { return false }
            return window.contentView != nil
        }
    }

    private func selectedScreensDisplayIDs() -> Set<UInt32> {
        Set(selectedScreens.compactMap { device in
            HostEnvironment.displayMetadata(forFFmpegScreenIndex: device.screenOrdinal).displayID
        })
    }

    func revealTakeFolder() {
        guard let activeTakeURL else { return }
        revealTakeFolder(activeTakeURL)
    }

    func revealTakeFolder(_ takeURL: URL) {
        guard FileManager.default.fileExists(atPath: takeURL.path) else {
            appendStatus("Take folder is missing: \(takeURL.lastPathComponent).")
            refreshTakeHistory()
            return
        }
        if !NSWorkspace.shared.open(takeURL) {
            appendStatus("Could not open take folder: \(takeURL.path)")
        }
    }

    func copyTakeFolderPath(_ takeURL: URL) {
        guard FileManager.default.fileExists(atPath: takeURL.path) else {
            appendStatus("Take folder is missing: \(takeURL.lastPathComponent).")
            refreshTakeHistory()
            return
        }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(takeURL.path, forType: .string)
        appendStatus("Copied take folder path: \(takeURL.lastPathComponent).")
    }

    func previewExport(for takeURL: URL) {
        guard canManageTakes else {
            appendStatus("Stop the current recording before switching takes.")
            return
        }
        guard selectTakeForReview(takeURL, announce: false) else { return }
        guard activeTakeURL?.path == takeURL.path else { return }
        previewActiveTakeExport()
    }

    func openPlaybackAsset() {
        guard let playbackURL else { return }
        guard FileManager.default.fileExists(atPath: playbackURL.path) else {
            appendStatus("Playback file is missing: \(playbackURL.lastPathComponent).")
            return
        }
        NSWorkspace.shared.open(playbackURL)
    }

    func revealPlaybackAsset() {
        guard let playbackURL else { return }
        guard FileManager.default.fileExists(atPath: playbackURL.path) else {
            appendStatus("Playback file is missing: \(playbackURL.lastPathComponent).")
            return
        }
        NSWorkspace.shared.activateFileViewerSelecting([playbackURL])
    }

    func copyPlaybackAssetPath() {
        guard let playbackURL else {
            appendStatus("No playback file path to copy.")
            return
        }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(playbackURL.path, forType: .string)
        appendStatus("Copied playback path: \(playbackURL.lastPathComponent).")
    }

    func playFromStart() {
        seekPlayback(to: 0)
        playPlayback()
    }

    func togglePlayback() {
        playbackIsPlaying ? pausePlayback() : playPlayback()
    }

    func playPlayback() {
        guard playbackPlayer != nil else { return }
        if playbackDuration > 0, playbackPosition >= max(0, playbackDuration - 0.25) {
            seekPlayback(to: 0)
        }
        playbackPlayer?.play()
        playbackCameraPlayer?.play()
        playbackIsPlaying = true
        playbackStatus = "Playing \(playbackTitle)"
    }

    func pausePlayback() {
        playbackPlayer?.pause()
        playbackCameraPlayer?.pause()
        playbackIsPlaying = false
        if playbackURL != nil {
            playbackStatus = "Paused \(playbackTitle)"
        }
    }

    func seekPlayback(to seconds: TimeInterval) {
        guard let player = playbackPlayer else { return }
        let bounded = min(max(seconds, 0), max(playbackDuration, 0))
        playbackPosition = bounded
        let time = CMTime(seconds: bounded, preferredTimescale: 600)
        player.seek(to: time, toleranceBefore: .zero, toleranceAfter: .zero)
        playbackCameraPlayer?.seek(to: time, toleranceBefore: .zero, toleranceAfter: .zero)
    }

    func skipPlayback(by seconds: TimeInterval) {
        seekPlayback(to: playbackPosition + seconds)
    }

    func refreshTakeHistory(selectLatestIfNone: Bool = false) {
        let fileManager = FileManager.default
        try? fileManager.createDirectory(
            at: HostEnvironment.outputRoot,
            withIntermediateDirectories: true
        )
        let urls = (try? fileManager.contentsOfDirectory(
            at: HostEnvironment.outputRoot,
            includingPropertiesForKeys: [.isDirectoryKey, .contentModificationDateKey],
            options: [.skipsHiddenFiles]
        )) ?? []

        recentTakes = urls
            .compactMap(takeSummary(for:))
            .sorted { left, right in
                left.modifiedAt > right.modifiedAt
            }
            .prefix(12)
            .map { $0 }

        if let target = keyboardDeleteTargetTake,
           !recentTakes.contains(where: { isSameTakeURL($0.url, target.url) }) {
            keyboardDeleteTargetTake = nil
        }

        if selectLatestIfNone, activeTakeURL == nil, let latest = recentTakes.first {
            selectTakeForReview(latest.url, announce: false)
            return
        }
        refreshActiveTakeExportStatus()
        refreshActiveTakeProgress()
    }

    @discardableResult
    func selectTakeForReview(_ takeURL: URL, announce: Bool = true) -> Bool {
        guard canManageTakes else {
            appendStatus("Stop the current recording before switching takes.")
            return false
        }
        guard FileManager.default.fileExists(atPath: takeURL.path) else {
            appendStatus("Take no longer exists: \(takeURL.lastPathComponent).")
            refreshTakeHistory()
            return false
        }

        pausePlayback()
        activeTakeURL = takeURL
        activeTakeTitle = titleForTake(takeURL) ?? ""
        takeTitleDraft = activeTakeTitle
        keyboardDeleteTargetTake = recentTakes.first(where: { isSameTakeURL($0.url, takeURL) }) ?? takeSummary(for: takeURL)
        elapsed = 0
        markers = []
        recordingStartedAt = nil
        scheduleState = nil
        scheduleStatus = "Run map idle"
        let recordingState = recordingState(for: takeURL)
        if recordingState == "stopped" {
            clearPlayback()
        } else {
            loadPlaybackAsset(from: takeURL)
        }
        refreshActiveTakeExportStatus()
        refreshActiveTakeProgress()
        if recordingState == "stopped" {
            state = .stopped
        } else {
            state = playbackURL == nil ? (startBlockers.isEmpty ? .ready : .setupNeeded) : .reviewReady
        }
        if shouldKeepPackageProgressTimerRunning() {
            startPackageProgressTimer()
        } else {
            stopPackageProgressTimerIfIdle()
        }
        if announce {
            appendStatus("Loaded \(activeTakeDisplayName) for review.")
        }
        return true
    }

    @discardableResult
    func prepareNewTakeForRecording() -> Bool {
        guard canManageTakes else {
            appendStatus("Stop the current recording before preparing a new take.")
            return false
        }

        pausePlayback()
        clearPlayback()
        activeTakeURL = nil
        activeTakeTitle = ""
        takeTitleDraft = ""
        clearActiveTakeExportStatus()
        clearActiveTakeProgressStatus()
        elapsed = 0
        markers = []
        recordingStartedAt = nil
        scheduleState = nil
        scheduleStatus = "Run map idle"
        lastStartFailureLine = nil
        state = startBlockers.isEmpty ? .ready : .setupNeeded
        refreshTakeHistory()
        updateAudioMeter()
        updateCameraPreview()
        schedulePreviewTimer()
        appendStatus("Ready for a new take.")
        return true
    }

    func updatePlaybackCameraOverlayLayout(offset: CGSize, scale: CGFloat) {
        guard playbackCameraURL != nil else { return }
        let layout = CameraPIPLayout(offset: offset, scale: scale)
        playbackCameraOverlayLayout = layout
        persistCameraPIPLayout(layout)
    }

    func deleteTake(_ takeURL: URL) {
        let targetURL = takeURL.standardizedFileURL
        guard !isTakeBusy(targetURL) else {
            appendStatus("Wait for \(targetURL.lastPathComponent) to finish background work before deleting it.")
            return
        }
        guard canDeleteTake(targetURL) else {
            appendStatus("Stop the current recording before deleting takes.")
            return
        }
        if isSameTakeURL(pendingDeleteTake?.url, targetURL) {
            pendingDeleteTake = nil
        }
        if isSameTakeURL(keyboardDeleteTargetTake?.url, targetURL) {
            keyboardDeleteTargetTake = nil
        }
        let fileManager = FileManager.default
        let isActive = isSameTakeURL(activeTakeURL, targetURL)
        let name = targetURL.lastPathComponent
        let activeStopDiscard = isActive && state == .stopping

        guard fileManager.fileExists(atPath: targetURL.path) else {
            if isActive {
                if activeStopDiscard {
                    discardedTakeIDsDuringStop.insert(name)
                }
                clearRemovedActiveTake()
            }
            recentTakes.removeAll { isSameTakeURL($0.url, targetURL) }
            refreshTakeHistory()
            appendStatus("Removed stale \(name) from the take list.")
            return
        }

        if isActive {
            if activeStopDiscard {
                discardedTakeIDsDuringStop.insert(name)
            }
            clearPlayback()
        }
        do {
            try fileManager.removeItem(at: targetURL)
            guard !fileManager.fileExists(atPath: targetURL.path) else {
                appendStatus("Delete failed for \(name): folder is still present on disk.")
                return
            }
            if isActive {
                clearRemovedActiveTake()
            }
            recentTakes.removeAll { isSameTakeURL($0.url, targetURL) }
            refreshTakeHistory()
            appendStatus("Deleted \(name).")
        } catch {
            appendStatus("Delete failed for \(name): \(error.localizedDescription).")
        }
    }

    func requestDeleteActiveTake() {
        guard let activeTakeURL else {
            appendStatus("Select a take before deleting.")
            return
        }
        requestDeleteTake(activeTakeURL)
    }

    func requestDeleteTargetTake() {
        guard let targetURL = deleteTargetTakeURL else {
            appendStatus("Select a take before deleting.")
            return
        }
        requestDeleteTake(targetURL)
    }

    func requestDeleteTake(_ takeURL: URL) {
        let targetURL = takeURL.standardizedFileURL
        guard !isTakeBusy(targetURL) else {
            appendStatus("Wait for \(targetURL.lastPathComponent) to finish background work before deleting it.")
            return
        }
        guard canDeleteTake(targetURL) else {
            appendStatus("Stop the current recording before deleting takes.")
            return
        }
        if let summary = recentTakes.first(where: { isSameTakeURL($0.url, targetURL) }) ?? takeSummary(for: targetURL) {
            pendingDeleteTake = summary
        } else {
            refreshTakeHistory()
            appendStatus("Take no longer exists: \(targetURL.lastPathComponent).")
        }
    }

    func confirmPendingDeleteTake() {
        guard let pending = pendingDeleteTake else { return }
        pendingDeleteTake = nil
        deleteTake(pending.url)
    }

    func discardTakeAndReset() {
        guard let activeTakeURL, canDiscardTake else { return }
        deleteTake(activeTakeURL)
    }

    private func canDeleteTake(_ takeURL: URL) -> Bool {
        if nativeCaptureWritersActive { return false }
        if isTakeBusy(takeURL) { return false }
        if canManageTakes { return true }
        return canDiscardActiveTakeDuringStop(takeURL)
    }

    private func canDiscardActiveTakeDuringStop(_ takeURL: URL) -> Bool {
        guard state == .stopping,
              let activeTakeURL,
              isSameTakeURL(activeTakeURL, takeURL)
        else {
            return false
        }
        return true
    }

    private func consumeStopDiscard(for takeID: String, takeURL: URL) -> Bool {
        if discardedTakeIDsDuringStop.remove(takeID) != nil {
            return true
        }
        return activeTakeURL == nil && !FileManager.default.fileExists(atPath: takeURL.path)
    }

    private func clearRemovedActiveTake() {
        clearPlayback()
        activeTakeURL = nil
        activeTakeTitle = ""
        takeTitleDraft = ""
        clearActiveTakeExportStatus()
        clearActiveTakeProgressStatus()
        elapsed = 0
        markers = []
        recordingStartedAt = nil
        scheduleState = nil
        scheduleStatus = "Run map idle"
        state = startBlockers.isEmpty ? .ready : .setupNeeded
    }

    func openOutputRoot() {
        NSWorkspace.shared.open(HostEnvironment.outputRoot)
    }

    func openExportsRoot() {
        let exportsRoot = exportsRootURL()
        try? FileManager.default.createDirectory(at: exportsRoot, withIntermediateDirectories: true)
        if !NSWorkspace.shared.open(exportsRoot) {
            appendStatus("Could not open export folder: \(exportsRoot.path)")
        }
    }

    func openLastExportedVideo() {
        guard let lastExportedVideoURL else { return }
        NSWorkspace.shared.activateFileViewerSelecting([lastExportedVideoURL])
    }

    func openActiveTakeExport() {
        refreshActiveTakeExportStatus()
        guard let activeTakeExportURL else {
            appendStatus("No upload export exists for the selected take yet.")
            return
        }
        guard FileManager.default.fileExists(atPath: activeTakeExportURL.path) else {
            appendStatus("Export file is missing: \(activeTakeExportURL.lastPathComponent).")
            return
        }
        NSWorkspace.shared.activateFileViewerSelecting([activeTakeExportURL])
    }

    func previewActiveTakeExport(autoPlay: Bool = false) {
        refreshActiveTakeExportStatus()
        guard let activeTakeExportURL else {
            appendStatus("No upload export exists for the selected take yet.")
            return
        }
        guard FileManager.default.fileExists(atPath: activeTakeExportURL.path) else {
            appendStatus("Export file is missing: \(activeTakeExportURL.lastPathComponent).")
            return
        }
        guard isVideoAsset(activeTakeExportURL) else {
            appendStatus("Export is not a playable video: \(activeTakeExportURL.lastPathComponent).")
            return
        }
        loadPlaybackFile(
            activeTakeExportURL,
            title: "upload export · \(activeTakeExportURL.lastPathComponent)",
            readyStatus: "Ready to review upload export",
            sourceLabel: "Upload export",
            sourceSystemImage: "square.and.arrow.up"
        )
        if autoPlay {
            playFromStart()
        }
        appendStatus("Previewing upload export: \(activeTakeExportURL.lastPathComponent).")
    }

    func previewActiveTakeReview(autoPlay: Bool = false) {
        guard let activeTakeURL else {
            appendStatus("No take selected for review.")
            return
        }
        guard playbackAssetURL(for: activeTakeURL) != nil else {
            appendStatus("No playable review asset found in this take.")
            loadPlaybackAsset(from: activeTakeURL)
            return
        }
        loadPlaybackAsset(from: activeTakeURL)
        if autoPlay {
            playFromStart()
        }
        appendStatus("Previewing take review: \(playbackTitle).")
    }

    func copyActiveTakeExportPath() {
        refreshActiveTakeExportStatus()
        guard let activeTakeExportURL else {
            appendStatus("No export path to copy for the selected take.")
            return
        }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(activeTakeExportURL.path, forType: .string)
        appendStatus("Copied export path: \(activeTakeExportURL.lastPathComponent).")
    }

    func relaunchApp() {
        let installed = URL(fileURLWithPath: "/Applications/Demo Take Console.app", isDirectory: true)
        NSWorkspace.shared.openApplication(
            at: installed,
            configuration: NSWorkspace.OpenConfiguration()
        ) { [weak self] _, error in
            Task { @MainActor in
                if let error {
                    self?.appendStatus("Relaunch request failed: \(error.localizedDescription)")
                } else {
                    NSApp.terminate(nil)
                }
            }
        }
    }

    private func applyDefaultSelections() {
        if !hasAppliedInitialDefaults {
            applySimpleDefaults(announce: false, preserveWebcamPreference: webcamPreferenceChangedInCurrentRun)
            applyPersistedRecorderConfigIfAvailable()
            applyPersistedDeviceSelectionsIfAvailable()
            hasAppliedInitialDefaults = true
            return
        }
        if selectedScreenIDs.isEmpty && !hasPersistedDisplayPreference {
            selectedScreenIDs = defaultScreenSelection()
        }
        if selectedAudioID == nil && !savedMicrophonePreferenceIsUnavailable {
            selectedAudioID = preferredAudioDevice()?.id
        }
        if selectedWebcamID == nil {
            selectedWebcamID = devices.videoDevices.first(where: { $0.isLikelyWebcam })?.id
        }
    }

    private func applyPersistedDeviceSelectionsIfAvailable() {
        guard let config = loadPersistedRecorderConfig() else { return }
        if let displayIndexes = config.selectedDisplayIndexes {
            if displayIndexes.isEmpty {
                selectedScreenIDs = []
            } else {
                let ids = devices.videoDevices
                    .filter { device in device.isScreen && displayIndexes.contains(device.index) }
                    .map(\.id)
                if !ids.isEmpty {
                    selectedScreenIDs = Set(ids.prefix(1))
                    if ids.count > 1 {
                        appendStatus("Saved display preference named multiple displays; using the first visible display only.")
                    }
                } else {
                    selectedScreenIDs = []
                    appendStatus("Saved display indexes no longer match screen devices. Reload Devices before recording.")
                }
            }
        }
        let microphonePreference = config.microphonePreference
        if microphonePreference.hasSelection {
            if let microphone = MicrophonePreferenceResolver.resolve(microphonePreference, in: devices.audioDevices) {
                selectedAudioID = microphone.id
                savedMicrophonePreferenceIsUnavailable = false
                if microphone.uniqueID != nil && config.selectedMicrophoneUniqueID == nil {
                    persistMicrophonePreference(microphone)
                }
            } else {
                selectedAudioID = nil
                savedMicrophonePreferenceIsUnavailable = true
                appendStatus("Preferred microphone unavailable: \(microphonePreference.displayLabel). Reconnect it or choose another mic; screen recording can continue without mic.")
            }
        }
        if !webcamPreferenceChangedInCurrentRun,
           let webcamIndex = config.selectedWebcamIndex,
           let webcam = devices.videoDevices.first(where: { $0.index == webcamIndex && $0.isLikelyWebcam }) {
            selectedWebcamID = webcam.id
        }
    }

    private func persistDeviceInventory(_ inventory: DeviceInventory) {
        do {
            let url = deviceInventoryCacheURL
            try FileManager.default.createDirectory(
                at: url.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            let data = try JSONEncoder().encode(inventory)
            try data.write(to: url, options: [.atomic])
        } catch {
            appendStatus("Could not save source inventory cache: \(error.localizedDescription)")
        }
    }

    private func persistDisplayPreference() {
        do {
            let url = recorderConfigURL
            try FileManager.default.createDirectory(
                at: url.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            var payload = loadRecorderConfigPayload()
            payload["selected_display_indexes"] = selectedScreens.map(\.index).sorted()

            guard JSONSerialization.isValidJSONObject(payload) else {
                appendStatus("Could not save display preference: recorder config is not valid JSON.")
                return
            }
            let data = try JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys])
            try data.write(to: url, options: [.atomic])
        } catch {
            appendStatus("Could not save display preference: \(error.localizedDescription)")
        }
    }

    private func loadCachedOrPersistedDeviceInventoryIfNeeded() {
        guard devices.videoDevices.isEmpty && devices.audioDevices.isEmpty else { return }
        if let cached = loadCachedDeviceInventory() {
            devices = cached
            appendStatus("Loaded cached source inventory. Use Reload Devices only when sources change.")
            return
        }
        if let fallback = deviceInventoryFromPersistedRecorderConfig() {
            devices = fallback
            appendStatus("Loaded saved audio index only. Reload Devices before recording a display.")
        } else {
            appendStatus("No cached source inventory yet. Use Reload Devices once before the next recording.")
        }
    }

    private func loadCachedDeviceInventory() -> DeviceInventory? {
        do {
            let data = try Data(contentsOf: deviceInventoryCacheURL)
            let inventory = AVCaptureDeviceIdentityResolver.enrichInventory(
                try JSONDecoder().decode(DeviceInventory.self, from: data)
            )
            guard !inventory.videoDevices.isEmpty || !inventory.audioDevices.isEmpty else { return nil }
            return inventory
        } catch {
            return nil
        }
    }

    private func applyPersistedRecorderConfigIfAvailable() {
        guard let config = loadPersistedRecorderConfig() else { return }
        if let seconds = config.screenshotIntervalSeconds {
            screenshotInterval = max(1, min(60, seconds))
        }
        if let hide = config.hideConsoleBeforeCapture {
            autoHideBeforeRecording = hide
        }
        if let model = config.transcribeModel, !model.isEmpty {
            transcribeModel = model
        }
        if !webcamPreferenceChangedInCurrentRun, let enabled = config.webcamEnabled {
            webcamEnabled = enabled
        }
    }

    private func loadPersistedRecorderConfig() -> PersistedRecorderConfig? {
        do {
            let data = try Data(contentsOf: recorderConfigURL)
            return try JSONDecoder().decode(PersistedRecorderConfig.self, from: data)
        } catch {
            return nil
        }
    }

    private var hasPersistedDisplayPreference: Bool {
        loadPersistedRecorderConfig()?.selectedDisplayIndexes != nil
    }

    private func persistMicrophonePreference(_ microphone: CaptureDevice?) {
        do {
            let url = recorderConfigURL
            try FileManager.default.createDirectory(
                at: url.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            var payload = loadRecorderConfigPayload()
            if let microphone {
                payload["selected_microphone_index"] = microphone.index
                payload["selected_microphone_name"] = microphone.name
                if let uniqueID = microphone.uniqueID, !uniqueID.isEmpty {
                    payload["selected_microphone_unique_id"] = uniqueID
                } else {
                    payload.removeValue(forKey: "selected_microphone_unique_id")
                }
                appendStatus("Saved microphone preference: \(microphone.identityDescription).")
            } else {
                payload.removeValue(forKey: "selected_microphone_index")
                payload.removeValue(forKey: "selected_microphone_name")
                payload.removeValue(forKey: "selected_microphone_unique_id")
                appendStatus("Cleared microphone preference; screen recording will continue without mic.")
            }

            guard JSONSerialization.isValidJSONObject(payload) else {
                appendStatus("Could not save microphone preference: recorder config is not valid JSON.")
                return
            }
            let data = try JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys])
            try data.write(to: url, options: [.atomic])
        } catch {
            appendStatus("Could not save microphone preference: \(error.localizedDescription)")
        }
    }

    private func loadRecorderConfigPayload() -> [String: Any] {
        guard let data = try? Data(contentsOf: recorderConfigURL),
              let payload = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            return [:]
        }
        return payload
    }

    private func persistWebcamPreference() {
        do {
            let url = recorderConfigURL
            try FileManager.default.createDirectory(
                at: url.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            var payload = loadRecorderConfigPayload()
            payload["webcam_enabled"] = webcamEnabled
            if let webcam = selectedWebcamCandidate {
                payload["selected_webcam_index"] = webcam.index
            } else {
                payload.removeValue(forKey: "selected_webcam_index")
            }

            guard JSONSerialization.isValidJSONObject(payload) else {
                appendStatus("Could not save webcam preference: recorder config is not valid JSON.")
                return
            }
            let data = try JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys])
            try data.write(to: url, options: [.atomic])
        } catch {
            appendStatus("Could not save webcam preference: \(error.localizedDescription)")
        }
    }

    private func deviceInventoryFromPersistedRecorderConfig() -> DeviceInventory? {
        guard let config = loadPersistedRecorderConfig() else { return nil }
        var inventory = DeviceInventory.empty
        let preference = config.microphonePreference
        if preference.hasSelection {
            let microphoneIndex = preference.index ?? -1
            let microphoneName = preference.name ?? "Saved microphone"
            inventory.audioDevices = [
                CaptureDevice(
                    id: "audio-\(microphoneIndex)-\(microphoneName)",
                    index: microphoneIndex,
                    name: microphoneName,
                    kind: .audio,
                    uniqueID: preference.uniqueID
                )
            ]
        }
        guard !inventory.audioDevices.isEmpty else { return nil }
        return inventory
    }

    private func applySimpleDefaults(announce: Bool, preserveWebcamPreference: Bool = false) {
        selectedScreenIDs = defaultScreenSelection()
        selectedAudioID = preferredAudioDevice()?.id
        if !preserveWebcamPreference {
            selectedWebcamID = devices.videoDevices.first(where: { $0.isLikelyWebcam })?.id
            webcamEnabled = false
        }
        autoHideBeforeRecording = false
        if announce {
            savedMicrophonePreferenceIsUnavailable = false
            persistDisplayPreference()
            persistMicrophonePreference(selectedAudio)
            let screenCount = selectedScreens.count
            let mic = selectedAudio?.name ?? "no microphone found"
            appendStatus("Simple mode: \(screenCount) display + \(mic); console stays visible.")
        }
    }

    private func defaultScreenSelection() -> Set<String> {
        let screens = devices.videoDevices
            .filter(\.isScreen)
            .sorted { $0.screenOrdinal < $1.screenOrdinal }
        if let mainIndex = HostEnvironment.mainFFmpegScreenIndex(),
           let main = screens.first(where: { $0.screenOrdinal == mainIndex }) {
            return [main.id]
        }
        return Set(screens.prefix(1).map(\.id))
    }

    private func preferredAudioDevice() -> CaptureDevice? {
        devices.audioDevices.first {
            $0.name.localizedCaseInsensitiveContains("Blue Snowball")
        } ?? devices.audioDevices.first
    }

    private func updateSelectedAudioAvailability() {
        guard let selectedAudio else {
            cachedSelectedAudioIsAvailable = true
            return
        }
        cachedSelectedAudioIsAvailable = audioDeviceAvailability(selectedAudio)
    }

    private func diskStatus(bytes: Int64?) -> CapabilityStatus {
        guard let bytes else {
            return .unknown
        }
        return bytes < minimumStartDiskBytes ? .low : .ready
    }

    private var screenRecordingPreflightBlocker: String {
        "macOS Screen Recording preflight denied this app"
    }

    private var currentSegmentHasMediaWriter: Bool {
        !currentSegmentScreenTracks.isEmpty || currentSegmentAudioTrack != nil || currentSegmentCameraTrack != nil
    }

    private func requireCurrentSegmentMedia(takeURL: URL, event: String) throws {
        guard currentSegmentHasMediaWriter else {
            let detail = NativeRecordingStartError.noMediaWritersStarted.localizedDescription
            appendStartAttempt(event, detail: detail, takeURL: takeURL)
            throw NativeRecordingStartError.noMediaWritersStarted
        }
    }

    private func estimatedBytes(seconds: Int64) -> Int64 {
        let screenBitsPerSecond = Int64(selectedScreens.count) * 3_500_000
        let webcamBitsPerSecond = selectedWebcam == nil ? 0 : 2_000_000
        let micBitsPerSecond = selectedAudio == nil ? 0 : 160_000
        let totalBits = (screenBitsPerSecond + Int64(webcamBitsPerSecond + micBitsPerSecond)) * seconds
        return totalBits / 8
    }

    @discardableResult
    private func repairActiveNativeRecordingStateIfNeeded(reason: String) -> Bool {
        guard nativeCaptureWritersActive else { return false }
        switch state {
        case .stopping, .postprocessing, .countingDown:
            return true
        default:
            break
        }

        if state != .recording {
            appendStartAttempt("state_recording_repaired", detail: reason, takeURL: activeTakeURL)
            appendStatus("Recording state repaired: native capture is still live; Stop remains available.")
        }
        state = .recording
        if recordingStartedAt == nil {
            recordingStartedAt = Date().addingTimeInterval(-elapsed)
        }
        startTimer()
        startScheduleTimer()
        if !hudVisible {
            showHud()
        }
        return true
    }

    private func startTimer() {
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self, let recordingStartedAt = self.recordingStartedAt else { return }
                self.elapsed = Date().timeIntervalSince(recordingStartedAt)
            }
        }
    }

    private func startScheduleTimer() {
        scheduleTimer?.invalidate()
        refreshScheduleState()
        scheduleTimer = Timer.scheduledTimer(withTimeInterval: 1.5, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.refreshScheduleState()
            }
        }
    }

    private func refreshScheduleState() {
        guard captureControlsActive else { return }
        guard !scheduleRefreshInFlight else { return }
        scheduleRefreshInFlight = true
        let takeURL = activeTakeURL
        Task {
            defer {
                Task { @MainActor in
                    self.scheduleRefreshInFlight = false
                }
            }
            do {
                let response = try await CaptureHelperClient.scheduleState(takeRoot: takeURL)
                await MainActor.run {
                    self.scheduleState = response
                    self.scheduleStatus = response.status == "ready"
                        ? "\(response.progressLabel) · \(response.currentTitle ?? response.currentStepID ?? "unknown")"
                        : response.status
                }
            } catch {
                await MainActor.run {
                    self.scheduleStatus = "Run map unavailable: \(error.localizedDescription)"
                }
            }
        }
    }

    private func startCameraCaptureHealthMonitor() {
        cameraHealthTimer?.invalidate()
        cameraHealthTimer = nil
        cameraHealthLastBytes = nil
        cameraHealthLastDurationSeconds = nil
        cameraHealthLastFrameCount = nil
        cameraHealthLastDistinctFrameCount = nil
        cameraHealthLastGrowthAt = nil
        cameraHealthLastVisualProgressAt = nil
        cameraHealthWarningIssued = false

        guard selectedWebcam != nil, currentSegmentCameraTrack != nil else {
            cameraCaptureStatusLine = webcamEnabled ? "Camera selected; no active camera track." : "Camera capture idle"
            return
        }
        cameraCaptureStatusLine = "Camera track starting..."
        refreshCameraCaptureHealth()
        cameraHealthTimer = Timer.scheduledTimer(withTimeInterval: max(0.05, cameraHealthPollIntervalSeconds), repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.refreshCameraCaptureHealth()
            }
        }
    }

    private func stopCameraCaptureHealthMonitor(_ status: String = "Camera capture idle") {
        cameraHealthTimer?.invalidate()
        cameraHealthTimer = nil
        cameraHealthLastBytes = nil
        cameraHealthLastDurationSeconds = nil
        cameraHealthLastFrameCount = nil
        cameraHealthLastDistinctFrameCount = nil
        cameraHealthLastGrowthAt = nil
        cameraHealthLastVisualProgressAt = nil
        cameraHealthWarningIssued = false
        cameraHealthRecoveryInFlight = false
        cameraCaptureStatusLine = status
    }

    private func refreshCameraCaptureHealth() {
        guard state == .recording, let activeTakeURL, let track = currentSegmentCameraTrack else { return }
        let url = activeTakeURL.appendingPathComponent(track.relativePath)
        let attributes = try? FileManager.default.attributesOfItem(atPath: url.path)
        let fileBytes = (attributes?[.size] as? NSNumber)?.int64Value ?? 0
        let stats = nativeCameraCaptureManager.activeRecordingStats
        let statsBytes = stats?.recordedFileSizeBytes ?? 0
        let bytes = max(fileBytes, statsBytes)
        let duration = stats?.recordedDurationSeconds ?? 0
        let frameCount = stats?.videoFrameCount ?? 0
        let distinctFrameCount = stats?.distinctFrameSignatureCount ?? 0
        let now = Date()

        let hasAnySignal = bytes > 0 || duration > 0 || frameCount > 0
        guard hasAnySignal else {
            if cameraHealthLastGrowthAt == nil {
                cameraHealthLastGrowthAt = now
            }
            let waitingSeconds = now.timeIntervalSince(cameraHealthLastGrowthAt ?? now)
            cameraCaptureStatusLine = String(format: "Camera track waiting for first frames %.0fs", waitingSeconds)
            if waitingSeconds >= cameraHealthStallRecoverySeconds {
                triggerCameraCaptureRecovery(
                    event: "camera_track_no_progress_recovery",
                    detail: "\(track.relativePath) no camera frames after \(Int(waitingSeconds))s",
                    takeURL: activeTakeURL,
                    message: "Camera track did not produce frames for \(Int(waitingSeconds))s"
                )
            }
            return
        }

        let durationAdvanced = cameraHealthLastDurationSeconds.map { duration > $0 + 0.25 } ?? (duration > 0)
        let bytesAdvanced = cameraHealthLastBytes.map { bytes > $0 } ?? (bytes > 0)
        let framesAdvanced = cameraHealthLastFrameCount.map { frameCount > $0 } ?? (frameCount > 0)
        let distinctAdvanced = cameraHealthLastDistinctFrameCount.map { distinctFrameCount > $0 } ?? (distinctFrameCount > 0)

        if durationAdvanced || bytesAdvanced || framesAdvanced {
            cameraHealthLastBytes = bytes
            cameraHealthLastDurationSeconds = duration
            cameraHealthLastFrameCount = frameCount
            cameraHealthLastDistinctFrameCount = distinctFrameCount
            cameraHealthLastGrowthAt = now
            cameraHealthWarningIssued = false
            if distinctAdvanced || cameraHealthLastVisualProgressAt == nil {
                cameraHealthLastVisualProgressAt = now
            }
            cameraCaptureStatusLine = cameraHealthStatusLine(
                bytes: bytes,
                duration: duration,
                frameCount: frameCount,
                distinctFrameCount: distinctFrameCount
            )
            if frameCount > 0, distinctFrameCount > 0, !distinctAdvanced {
                let visualStalledSeconds = now.timeIntervalSince(cameraHealthLastVisualProgressAt ?? now)
                if visualStalledSeconds >= cameraHealthVisualFreezeRecoverySeconds {
                    triggerCameraCaptureRecovery(
                        event: "camera_visual_freeze_recovery",
                        detail: "\(track.relativePath) visual signature unchanged for \(Int(visualStalledSeconds))s",
                        takeURL: activeTakeURL,
                        message: "Camera frames looked unchanged for \(Int(visualStalledSeconds))s"
                    )
                }
            }
            return
        }

        let stalledSeconds = now.timeIntervalSince(cameraHealthLastGrowthAt ?? now)
        cameraCaptureStatusLine = String(format: "Camera track unchanged for %.0fs", stalledSeconds)
        if stalledSeconds >= cameraHealthStallRecoverySeconds {
            triggerCameraCaptureRecovery(
                event: "camera_track_progress_stalled_recovery",
                detail: "\(track.relativePath) stalled after \(Int(stalledSeconds))s",
                takeURL: activeTakeURL,
                message: "Camera track stopped advancing for \(Int(stalledSeconds))s"
            )
            return
        }

        guard frameCount > 0, distinctFrameCount > 0 else { return }
        let visualStalledSeconds = now.timeIntervalSince(cameraHealthLastVisualProgressAt ?? now)
        if visualStalledSeconds >= cameraHealthVisualFreezeRecoverySeconds {
            triggerCameraCaptureRecovery(
                event: "camera_visual_freeze_recovery",
                detail: "\(track.relativePath) visual signature unchanged for \(Int(visualStalledSeconds))s",
                takeURL: activeTakeURL,
                message: "Camera frames looked unchanged for \(Int(visualStalledSeconds))s"
            )
        }
    }

    private func cameraHealthStatusLine(
        bytes: Int64,
        duration: Double,
        frameCount: Int,
        distinctFrameCount: Int
    ) -> String {
        if frameCount > 0 {
            return String(
                format: "Camera live %.0fs · %@ · %d frame checks · %d visual changes",
                duration,
                HostEnvironment.byteString(bytes),
                frameCount,
                distinctFrameCount
            )
        }
        if duration > 0 {
            return String(format: "Camera live %.0fs · %@", duration, HostEnvironment.byteString(bytes))
        }
        return "Camera writing \(HostEnvironment.byteString(bytes))"
    }

    private func triggerCameraCaptureRecovery(
        event: String,
        detail: String,
        takeURL: URL,
        message: String
    ) {
        guard !cameraHealthRecoveryInFlight, !cameraHealthWarningIssued else { return }
        cameraHealthRecoveryInFlight = true
        cameraHealthWarningIssued = true
        let warning = "\(message); rotating to a new synced media segment."
        persistTakeKnownFailure(warning, to: takeURL)
        appendStatus(warning)
        appendStartAttempt(event, detail: detail, takeURL: takeURL)
        cameraCaptureStatusLine = "Camera recovery rotating segment..."

        Task { @MainActor [weak self] in
            guard let self else { return }
            defer { self.cameraHealthRecoveryInFlight = false }
            await self.checkpointRecordingSegmentForStorage(reason: "camera_health_recovery")
        }
    }

    private func loadPlaybackAsset(from takeURL: URL) {
        clearPlayback()
        guard let asset = playbackAssetURL(for: takeURL) else {
            playbackStatus = "No playable review asset found in this take."
            playbackTitle = "No playback loaded"
            return
        }

        let title = playbackTitle(for: asset, takeURL: takeURL)
        let cameraOverlay = webcamTrackURL(for: takeURL, excluding: asset)
        let cameraOverlayLayout = cameraOverlay == nil ? .default : loadCameraPIPLayout(for: takeURL)
        let cameraIssue = cameraOverlay == nil ? cameraOverlayIssueLine(for: takeURL, excluding: asset) : nil
        configurePlayback(
            asset: asset,
            title: title,
            readyStatus: ["Ready to review \(title)", cameraIssue].compactMap { $0 }.joined(separator: " · "),
            sourceLabel: "Take review",
            sourceSystemImage: isVideoAsset(asset) ? "film" : "waveform",
            cameraOverlay: cameraOverlay,
            cameraOverlayLayout: cameraOverlayLayout
        )
    }

    private func loadPlaybackFile(
        _ asset: URL,
        title: String,
        readyStatus: String,
        sourceLabel: String,
        sourceSystemImage: String
    ) {
        clearPlayback()
        configurePlayback(
            asset: asset,
            title: title,
            readyStatus: readyStatus,
            sourceLabel: sourceLabel,
            sourceSystemImage: sourceSystemImage,
            cameraOverlay: nil,
            cameraOverlayLayout: .default
        )
    }

    private func configurePlayback(
        asset: URL,
        title: String,
        readyStatus: String,
        sourceLabel: String,
        sourceSystemImage: String,
        cameraOverlay: URL?,
        cameraOverlayLayout: CameraPIPLayout
    ) {
        let player = AVPlayer(url: asset)
        let cameraPlayer = cameraOverlay.map { overlayURL in
            let player = AVPlayer(url: overlayURL)
            player.isMuted = true
            return player
        }
        playbackPlayer = player
        playbackURL = asset
        playbackTitle = title
        playbackCameraPlayer = cameraPlayer
        playbackCameraURL = cameraOverlay
        playbackCameraTitle = cameraOverlay?.lastPathComponent ?? "Camera"
        playbackCameraOverlayLayout = cameraOverlay == nil ? .default : cameraOverlayLayout
        playbackDuration = 0
        playbackPosition = 0
        playbackIsPlaying = false
        playbackStatus = readyStatus
        playbackSourceLabel = sourceLabel
        playbackSourceSystemImage = sourceSystemImage
        refreshPlaybackDuration(for: asset)

        playbackTimeObserver = player.addPeriodicTimeObserver(
            forInterval: CMTime(seconds: 0.25, preferredTimescale: 600),
            queue: .main
        ) { [weak self] time in
            Task { @MainActor in
                let seconds = time.seconds.isFinite ? max(time.seconds, 0) : 0
                self?.playbackPosition = seconds
                self?.resyncCameraPlaybackIfNeeded(to: time)
            }
        }
        playbackEndObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: player.currentItem,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor in
                self?.playbackCameraPlayer?.pause()
                self?.playbackIsPlaying = false
                self?.playbackStatus = "Finished \(self?.playbackTitle ?? "playback")"
            }
        }
    }

    private func resyncCameraPlaybackIfNeeded(to time: CMTime) {
        guard let cameraPlayer = playbackCameraPlayer else { return }
        let cameraSeconds = cameraPlayer.currentTime().seconds
        let targetSeconds = time.seconds
        guard cameraSeconds.isFinite, targetSeconds.isFinite else { return }
        if abs(cameraSeconds - targetSeconds) > 0.35 {
            cameraPlayer.seek(to: time, toleranceBefore: .zero, toleranceAfter: .zero)
            if playbackIsPlaying {
                cameraPlayer.play()
            }
        }
    }

    private func startPackageProgressTimer() {
        refreshActiveTakeProgress()
        packageProgressTimer?.invalidate()
        packageProgressTimer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self else { return }
                self.refreshActiveTakeProgress()
                self.stopPackageProgressTimerIfIdle()
            }
        }
    }

    private func stopPackageProgressTimerIfIdle() {
        guard !shouldKeepPackageProgressTimerRunning() else { return }
        packageProgressTimer?.invalidate()
        packageProgressTimer = nil
    }

    private func shouldKeepPackageProgressTimerRunning() -> Bool {
        guard activeTakeURL != nil else { return false }
        return state == .stopping
            || state == .postprocessing
            || activeTakeHasBackgroundWork
            || activeTakeManifestRecordingState() == "postprocessing"
    }

    private func refreshActiveTakeProgress() {
        guard let activeTakeURL else {
            clearActiveTakeProgressStatus()
            return
        }

        activeTakeReviewStatusLine = reviewStatusLine(for: activeTakeURL)

        if let event = latestPostprocessProgressEvent(for: activeTakeURL) {
            let waitingForFullPostprocess = activeTakeIsBuildingPackage && !isFullPostprocessStage(event.stage)
            activeTakePostprocessStage = waitingForFullPostprocess ? "prepare_media_segments" : event.stage
            activeTakePostprocessStatus = waitingForFullPostprocess ? "running" : event.status
            activeTakePostprocessStatusLine = waitingForFullPostprocess
                ? "Preparing media segments for package sidecars..."
                : progressLine(for: event)
        } else if activeTakeIsBuildingPackage || state == .postprocessing {
            activeTakePostprocessStage = "postprocess"
            activeTakePostprocessStatus = "running"
            activeTakePostprocessStatusLine = "Building transcript/package sidecars..."
        } else {
            activeTakePostprocessStage = ""
            activeTakePostprocessStatus = ""
            activeTakePostprocessStatusLine = "No package activity yet."
        }

        if shouldAutoLoadReviewAssetDuringProgress(), playbackPlayer == nil {
            loadPlaybackAsset(from: activeTakeURL)
        }
    }

    private func clearActiveTakeProgressStatus() {
        activeTakeReviewStatusLine = "No review asset yet."
        activeTakePostprocessStatusLine = "No package activity yet."
        activeTakePostprocessStage = ""
        activeTakePostprocessStatus = ""
        packageProgressTimer?.invalidate()
        packageProgressTimer = nil
    }

    private func shouldAutoLoadReviewAssetDuringProgress() -> Bool {
        if activeTakeNeedsReviewPreparation { return false }
        guard let activeTakeURL, playbackAssetURL(for: activeTakeURL) != nil else { return false }
        switch state {
        case .stopping, .postprocessing, .reviewReady, .packageReady, .packageFailed:
            return true
        default:
            return activeTakeIsBuildingPackage
        }
    }

    private func reviewStatusLine(for takeURL: URL) -> String {
        if recordingState(for: takeURL) == "stopped" {
            return "Capture stopped; build package when ready."
        }
        if let video = videoAssetURL(for: takeURL) {
            return "Review ready: \(playbackTitle(for: video, takeURL: takeURL))\(sizeSuffix(for: video))"
        }
        if let asset = playbackAssetURL(for: takeURL) {
            return "Review ready: \(playbackTitle(for: asset, takeURL: takeURL))\(sizeSuffix(for: asset))"
        }
        if backgroundFinalizingTakeIDs.contains(takeURL.lastPathComponent) {
            return "Preparing replayable review..."
        }
        return mediaDiagnosisLine(for: takeURL) ?? "No review asset yet."
    }

    private func activeTakeManifestRecordingState() -> String? {
        guard let activeTakeURL else { return nil }
        return recordingState(for: activeTakeURL)
    }

    private func recordingState(for takeURL: URL) -> String? {
        readJSON(TakeManifestSummary.self, from: takeURL.appendingPathComponent("manifest.json"))?.recordingState
    }

    private func transcriptSidecarIsReady(for takeURL: URL) -> Bool {
        readJSON(TranscriptSidecarSummary.self, from: takeURL.appendingPathComponent("transcript/transcript.json"))?.status == "ready"
    }

    private func latestPostprocessProgressEvent(for takeURL: URL) -> PostprocessProgressEvent? {
        let url = takeURL.appendingPathComponent("postprocess_progress.jsonl")
        guard let data = try? Data(contentsOf: url),
              let text = String(data: data, encoding: .utf8)
        else {
            return nil
        }
        let decoder = JSONDecoder()
        for line in text.split(separator: "\n").reversed() {
            guard let lineData = String(line).data(using: .utf8),
                  let event = try? decoder.decode(PostprocessProgressEvent.self, from: lineData)
            else {
                continue
            }
            return event
        }
        return nil
    }

    private func progressLine(for event: PostprocessProgressEvent) -> String {
        let label = progressStageLabel(event.stage)
        let suffix = event.status == "running" ? "..." : ""
        return "\(label): \(event.message)\(suffix)"
    }

    private func progressStageLabel(_ stage: String) -> String {
        switch stage {
        case "stop_capture", "stop_ffmpeg": return "Stopping capture"
        case "quick_render": return "Playable review"
        case "review_audio": return "Audio review"
        case "active_timeline": return "Timeline"
        case "prepare_media_segments": return "Media segments"
        case "sample_frames": return "Frame thumbnails"
        case "transcribe": return "Transcript"
        case "voice_scan": return "Voice markers"
        case "view_timeline": return "View timeline"
        case "attention_spans": return "Attention spans"
        case "per_view_segments": return "View narration"
        case "intent_events": return "Intent events"
        case "speech_blocks": return "Speech blocks"
        case "edl": return "EDL"
        case "otio_export": return "OTIO"
        case "multimodal_index": return "Editor index"
        case "rough_render": return "Rough render"
        case "autoedit_cleanup": return "Auto-editor"
        case "semantic_proxy": return "Semantic proxy"
        case "manifest_ready": return "Manifest"
        case "cloud_archive": return "Cloud archive"
        case "package_ready": return "Package"
        case "", "postprocess": return "Package"
        default:
            return stage
                .split(separator: "_")
                .map { $0.prefix(1).uppercased() + $0.dropFirst() }
                .joined(separator: " ")
        }
    }

    private func isFullPostprocessStage(_ stage: String) -> Bool {
        switch stage {
        case "sample_frames", "transcribe", "voice_scan", "view_timeline", "attention_spans",
             "per_view_segments", "intent_events", "speech_blocks", "edl", "otio_export",
             "multimodal_index", "rough_render", "autoedit_cleanup", "semantic_proxy",
             "manifest_ready", "cloud_archive", "package_ready":
            return true
        default:
            return false
        }
    }

    private func takeSummary(for url: URL) -> TakeSummary? {
        var isDirectory: ObjCBool = false
        guard FileManager.default.fileExists(atPath: url.path, isDirectory: &isDirectory),
              isDirectory.boolValue,
              url.lastPathComponent.hasPrefix("take_")
        else {
            return nil
        }

        let values = try? url.resourceValues(forKeys: [.contentModificationDateKey])
        let modifiedAt = values?.contentModificationDate ?? .distantPast
        let stamp = DateFormatter.localizedString(from: modifiedAt, dateStyle: .short, timeStyle: .short)
        let asset = playbackAssetURL(for: url)
        let kind = playbackKind(for: asset)
        let physicalSize = directorySize(at: url)
        let sizeLine = HostEnvironment.byteString(physicalSize)
        let storageLine = storageDetailLine(for: url, physicalBytes: physicalSize)
        let exportStatus = exportStatus(for: url)
        let iconName = isVideoAsset(asset) ? "film" : (asset == nil ? "exclamationmark.triangle" : "waveform")
        let title = titleForTake(url)
        let name = title?.isEmpty == false ? title! : url.lastPathComponent
        let detailLine = title?.isEmpty == false
            ? "\(stamp) · \(kind) · \(url.lastPathComponent)"
            : "\(stamp) · \(kind)"

        return TakeSummary(
            id: url.path,
            url: url,
            name: name,
            detailLine: detailLine,
            sizeLine: sizeLine,
            storageLine: storageLine,
            exportLine: exportStatus.historyLine,
            exportReady: exportStatus.ready,
            iconName: iconName,
            modifiedAt: modifiedAt
        )
    }

    private func takeStorageLine(for url: URL) -> String {
        let physicalSize = directorySize(at: url)
        let detail = storageDetailLine(for: url, physicalBytes: physicalSize)
        let size = HostEnvironment.byteString(physicalSize)
        return detail.isEmpty ? "\(size) disk" : "\(size) disk · \(detail)"
    }

    private func refreshActiveTakeExportStatus() {
        guard let activeTakeURL else {
            clearActiveTakeExportStatus()
            return
        }
        let status = exportStatus(for: activeTakeURL)
        activeTakeExportURL = status.url
        activeTakeExportLine = status.ready ? status.line : (mediaDiagnosisLine(for: activeTakeURL) ?? status.line)
        if status.ready, let url = status.url {
            lastExportedVideoURL = url
        }
    }

    private func clearActiveTakeExportStatus() {
        activeTakeExportURL = nil
        activeTakeExportLine = "No upload export yet."
    }

    private func exportStatus(for takeURL: URL) -> ExportStatusSummary {
        guard let receipt = readJSON(ExportReceiptSummary.self, from: takeURL.appendingPathComponent("render/export_receipt.json")) else {
            return ExportStatusSummary(
                url: nil,
                line: "No upload export yet.",
                historyLine: "",
                ready: false
            )
        }

        let exportURL = exportURL(from: receipt)
        let exists = exportURL.map { FileManager.default.fileExists(atPath: $0.path) } ?? false
        let name = exportURL?.lastPathComponent
            ?? receipt.output.map { URL(fileURLWithPath: $0).lastPathComponent }
            ?? "upload export"
        let bytes = receipt.bytes ?? exportURL.flatMap { fileSize(at: $0) }
        let sizeSuffix = bytes.map { " · \(HostEnvironment.byteString($0))" } ?? ""
        let methodSuffix = exportMethodLine(for: receipt).map { " · \($0)" } ?? ""

        if exists {
            return ExportStatusSummary(
                url: exportURL,
                line: "Export ready: \(name)\(sizeSuffix)\(methodSuffix)",
                historyLine: "Exported \(name)",
                ready: true
            )
        }

        let missingLine = receipt.status == "ready" ? "Export missing" : "Export not ready"
        return ExportStatusSummary(
            url: exportURL,
            line: "\(missingLine): \(name)\(methodSuffix)",
            historyLine: "\(missingLine.lowercased()) \(name)",
            ready: false
        )
    }

    private func exportURL(from receipt: ExportReceiptSummary) -> URL? {
        for candidate in [receipt.outputPath, receipt.output] {
            guard let raw = candidate?.trimmingCharacters(in: .whitespacesAndNewlines),
                  !raw.isEmpty
            else {
                continue
            }
            if raw.hasPrefix("repo://") {
                let rel = String(raw.dropFirst("repo://".count))
                return HostEnvironment.repoRoot.appendingPathComponent(rel)
            }
            if raw.hasPrefix("/") {
                return URL(fileURLWithPath: raw)
            }
            if raw.contains("/") {
                return HostEnvironment.repoRoot.appendingPathComponent(raw)
            }
            return exportsRootURL().appendingPathComponent(raw)
        }
        return nil
    }

    private func mediaDiagnosisLine(for takeURL: URL) -> String? {
        let manifest = readJSON(TakeManifestSummary.self, from: takeURL.appendingPathComponent("manifest.json"))
        let session = readJSON(TakeSessionSummary.self, from: takeURL.appendingPathComponent("session.json"))
        let render = readJSON(RenderReceiptSummary.self, from: takeURL.appendingPathComponent("render/render_receipt.json"))
        let video = videoAssetURL(for: takeURL)
        let playback = playbackAssetURL(for: takeURL)
        let tracks = session?.tracks ?? []
        let screen = tracks.first { $0.role == "screen" || $0.role == "external_video" || $0.role == "webcam" }
        let webcam = tracks.first { $0.role == "webcam" }
        let microphone = tracks.first { $0.role == "microphone" }

        var parts: [String] = []
        if let video {
            parts.append("Review video: \(relativePath(video, in: takeURL))\(sizeSuffix(for: video))")
        } else if let playback, isAudioAsset(playback) {
            parts.append("Audio review: \(relativePath(playback, in: takeURL))\(sizeSuffix(for: playback))")
        } else if let screen {
            let screenURL = takeURL.appendingPathComponent(screen.relativePath)
            if FileManager.default.fileExists(atPath: screenURL.path) {
                parts.append("Screen track not playable: \(screen.relativePath)\(sizeSuffix(for: screenURL))")
            } else {
                parts.append("Missing screen track: \(screen.relativePath)")
            }
        } else if microphone != nil {
            parts.append("Audio-only take: no display was recorded")
        } else {
            parts.append("Missing screen track")
        }

        if let webcam, let cameraIssue = cameraTrackIssueLine(webcam, takeURL: takeURL, excluding: video) {
            parts.append(cameraIssue)
        }

        if let microphone {
            let micURL = takeURL.appendingPathComponent(microphone.relativePath)
            if !FileManager.default.fileExists(atPath: micURL.path) {
                parts.append("Mic missing: \(microphone.relativePath)")
            } else if (fileSize(at: micURL) ?? 0) <= 0 {
                parts.append("Mic empty: \(microphone.relativePath)")
            } else if manifest?.reviewAudio == nil {
                parts.append("MP3 not built")
            }
        } else {
            parts.append("No mic track")
        }

        if screen != nil,
           render?.status == "failed" || render?.status == "unavailable" || render?.status == "timeline_failed" {
            parts.append("Render \(render?.status ?? "unavailable")")
        }
        let failures = (manifest?.knownFailures ?? []) + (render?.knownFailures ?? [])
        if let firstFailure = failures.first, video == nil {
            parts.append(firstFailure)
        }
        return parts.isEmpty ? nil : parts.joined(separator: " · ")
    }

    private func relativePath(_ url: URL, in takeURL: URL) -> String {
        let prefix = takeURL.path + "/"
        if url.path.hasPrefix(prefix) {
            return String(url.path.dropFirst(prefix.count))
        }
        return url.lastPathComponent
    }

    private func sizeSuffix(for url: URL) -> String {
        fileSize(at: url).map { " · \(HostEnvironment.byteString($0))" } ?? ""
    }

    private func exportMethodLine(for receipt: ExportReceiptSummary) -> String? {
        if receipt.videoStreamAction == "no_reencode" {
            return "no re-encode"
        }
        switch receipt.method {
        case "hardlink_lossless_export":
            return "lossless hardlink"
        case "copy":
            return "lossless copy"
        case let method? where !method.isEmpty:
            return method.replacingOccurrences(of: "_", with: " ")
        default:
            return nil
        }
    }

    private func exportsRootURL() -> URL {
        HostEnvironment.repoRoot
            .appendingPathComponent("state", isDirectory: true)
            .appendingPathComponent("dissemination", isDirectory: true)
            .appendingPathComponent("demo_exports", isDirectory: true)
    }

    private func fileSize(at url: URL) -> Int64? {
        guard let attributes = try? FileManager.default.attributesOfItem(atPath: url.path),
              let size = attributes[.size] as? NSNumber
        else {
            return nil
        }
        return size.int64Value
    }

    private func playbackAssetURL(for takeURL: URL) -> URL? {
        var candidates: [URL] = []

        if let receipt = readJSON(RenderReceiptSummary.self, from: takeURL.appendingPathComponent("render/render_receipt.json")),
           let output = receipt.output,
           receipt.status != "failed" {
            candidates.append(takeURL.appendingPathComponent(output))
        }
        if let manifest = readJSON(TakeManifestSummary.self, from: takeURL.appendingPathComponent("manifest.json")),
           let reviewAudio = manifest.reviewAudio?.trimmingCharacters(in: .whitespacesAndNewlines),
           !reviewAudio.isEmpty {
            candidates.append(takeURL.appendingPathComponent(reviewAudio))
        }

        candidates += roughCutCandidates(for: takeURL)
        candidates += sessionTrackCandidates(for: takeURL, orderedRoles: ["external_video", "screen"])
        candidates += sessionTrackCandidates(for: takeURL, orderedRoles: ["webcam", "microphone"])
        candidates.append(takeURL.appendingPathComponent("tracks/microphone.m4a"))
        candidates.append(takeURL.appendingPathComponent("tracks/microphone.wav"))

        for candidate in candidates where isUsablePlaybackCandidate(candidate) {
            return candidate
        }

        return sessionTrackCandidates(for: takeURL, orderedRoles: ["external_video", "screen"])
            .sorted { $0.lastPathComponent < $1.lastPathComponent }
            .first { isUsablePlaybackCandidate($0) }
    }

    private func videoAssetURL(for takeURL: URL) -> URL? {
        var candidates: [URL] = []

        if let receipt = readJSON(RenderReceiptSummary.self, from: takeURL.appendingPathComponent("render/render_receipt.json")),
           let output = receipt.output,
           receipt.status != "failed" {
            candidates.append(takeURL.appendingPathComponent(output))
        }

        candidates += roughCutCandidates(for: takeURL)
        candidates += sessionTrackCandidates(for: takeURL, orderedRoles: ["external_video", "screen"])
        candidates += sessionTrackCandidates(for: takeURL, orderedRoles: ["webcam"])

        return candidates.first { isPlayableVideoFile($0) }
    }

    private func playbackTitle(for asset: URL, takeURL: URL) -> String {
        let relative = asset.path.replacingOccurrences(of: takeURL.path + "/", with: "")
        if relative.hasPrefix("render/rough_cut.") {
            return "rough cut"
        }
        if relative == "render/review_audio.mp3" {
            return "audio review"
        }
        if relative == "tracks/microphone.m4a" || relative == "tracks/microphone.wav" {
            return "microphone track"
        }
        return relative
    }

    private func playbackKind(for asset: URL?) -> String {
        guard let asset else { return "no playback" }
        if isVideoAsset(asset) {
            return asset.deletingPathExtension().lastPathComponent == "rough_cut" ? "video review" : "screen video"
        }
        return "audio review"
    }

    private func webcamTrackURL(for takeURL: URL, excluding asset: URL?) -> URL? {
        sessionTrackCandidates(for: takeURL, orderedRoles: ["webcam"])
            .first { candidate in
                isPlayableVideoFile(candidate)
                    && candidate.standardizedFileURL.path != asset?.standardizedFileURL.path
            }
    }

    private func cameraOverlayIssueLine(for takeURL: URL, excluding asset: URL?) -> String? {
        guard let session = readJSON(TakeSessionSummary.self, from: takeURL.appendingPathComponent("session.json")),
              let webcam = session.tracks?.first(where: { $0.role == "webcam" })
        else {
            return nil
        }
        return cameraTrackIssueLine(webcam, takeURL: takeURL, excluding: asset)
    }

    private func cameraTrackIssueLine(_ webcam: TrackRecord, takeURL: URL, excluding asset: URL?) -> String? {
        let url = takeURL.appendingPathComponent(webcam.relativePath)
        if url.standardizedFileURL.path == asset?.standardizedFileURL.path {
            return nil
        }
        if !FileManager.default.fileExists(atPath: url.path) {
            return "Camera track missing: \(webcam.relativePath)"
        }
        if !isPlayableVideoFile(url) {
            return "Camera track not playable: \(webcam.relativePath)\(sizeSuffix(for: url))"
        }
        return nil
    }

    private func loadCameraPIPLayout(for takeURL: URL) -> CameraPIPLayout {
        readJSON(CameraPIPLayout.self, from: cameraPIPLayoutURL(for: takeURL)) ?? .default
    }

    private func persistCameraPIPLayout(_ layout: CameraPIPLayout) {
        guard let activeTakeURL, playbackCameraURL != nil else { return }
        let url = cameraPIPLayoutURL(for: activeTakeURL)
        do {
            try FileManager.default.createDirectory(
                at: url.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            let data = try encoder.encode(layout)
            try data.write(to: url, options: [.atomic])
        } catch {
            appendStatus("Could not save camera preview layout: \(error.localizedDescription)")
        }
    }

    private func cameraPIPLayoutURL(for takeURL: URL) -> URL {
        takeURL
            .appendingPathComponent("review", isDirectory: true)
            .appendingPathComponent("camera_pip_layout.json")
    }

    private func roughCutCandidates(for takeURL: URL) -> [URL] {
        let renderURL = takeURL.appendingPathComponent("render", isDirectory: true)
        let urls = (try? FileManager.default.contentsOfDirectory(
            at: renderURL,
            includingPropertiesForKeys: nil,
            options: [.skipsHiddenFiles]
        )) ?? []
        return urls
            .filter { $0.deletingPathExtension().lastPathComponent == "rough_cut" && isVideoAsset($0) }
            .sorted { left, right in
                if left.pathExtension == "mp4" { return true }
                if right.pathExtension == "mp4" { return false }
                return left.lastPathComponent < right.lastPathComponent
            }
    }

    private func sessionTrackCandidates(for takeURL: URL, roles: Set<String>) -> [URL] {
        guard let session = readJSON(TakeSessionSummary.self, from: takeURL.appendingPathComponent("session.json")) else {
            return []
        }
        return (session.tracks ?? [])
            .filter { roles.contains($0.role) }
            .map { takeURL.appendingPathComponent($0.relativePath) }
            .filter { isVideoAsset($0) || isAudioAsset($0) }
    }

    private func sessionTrackCandidates(for takeURL: URL, orderedRoles roles: [String]) -> [URL] {
        roles.flatMap { role in
            sessionTrackCandidates(for: takeURL, roles: [role])
        }
    }

    private func isAudioAsset(_ url: URL?) -> Bool {
        guard let ext = url?.pathExtension.lowercased(), !ext.isEmpty else { return false }
        return ["m4a", "wav", "aac", "mp3"].contains(ext)
    }

    private func titleForTake(_ takeURL: URL) -> String? {
        if let manifest = readJSON(TakeManifestSummary.self, from: takeURL.appendingPathComponent("manifest.json")) {
            if let title = firstNonEmpty(manifest.title, manifest.takeTitle) {
                return title
            }
        }
        if let session = readJSON(TakeSessionSummary.self, from: takeURL.appendingPathComponent("session.json")),
           let config = session.config,
           let title = firstNonEmpty(config.takeTitle, config.title) {
            return title
        }
        return nil
    }

    private func firstNonEmpty(_ values: String?...) -> String? {
        for value in values {
            let cleaned = normalizedTakeTitle(value ?? "")
            if !cleaned.isEmpty {
                return cleaned
            }
        }
        return nil
    }

    private func normalizedTakeTitle(_ value: String) -> String {
        let words = value
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .components(separatedBy: .whitespacesAndNewlines)
            .filter { !$0.isEmpty }
        return String(words.joined(separator: " ").prefix(120))
    }

    private func newestImportCandidate() -> ImportCandidateSummary? {
        let fileManager = FileManager.default
        let home = fileManager.homeDirectoryForCurrentUser
        let roots: [(String, URL)] = [
            ("Downloads", home.appendingPathComponent("Downloads", isDirectory: true)),
            ("Desktop", home.appendingPathComponent("Desktop", isDirectory: true)),
            ("Movies", home.appendingPathComponent("Movies", isDirectory: true)),
        ]
        let keys: Set<URLResourceKey> = [.isRegularFileKey, .contentModificationDateKey, .fileSizeKey]

        var candidates: [ImportCandidateSummary] = []
        for (rootName, rootURL) in roots {
            let urls = (try? fileManager.contentsOfDirectory(
                at: rootURL,
                includingPropertiesForKeys: Array(keys),
                options: [.skipsHiddenFiles]
            )) ?? []

            for url in urls where isSupportedVideoURL(url) {
                guard let values = try? url.resourceValues(forKeys: keys),
                      values.isRegularFile == true
                else {
                    continue
                }
                let modifiedAt = values.contentModificationDate ?? .distantPast
                let stamp = DateFormatter.localizedString(
                    from: modifiedAt,
                    dateStyle: .short,
                    timeStyle: .short
                )
                let size = values.fileSize.map { Int64($0) }
                candidates.append(ImportCandidateSummary(
                    id: url.path,
                    url: url,
                    name: url.lastPathComponent,
                    detailLine: "\(rootName) · \(stamp)",
                    sizeLine: HostEnvironment.byteString(size),
                    modifiedAt: modifiedAt
                ))
            }
        }

        return candidates.sorted { left, right in
            left.modifiedAt > right.modifiedAt
        }.first
    }

    nonisolated private static func fileURL(fromProviderItem item: NSSecureCoding?) -> URL? {
        if let url = item as? URL {
            return url
        }
        if let data = item as? Data {
            return URL(dataRepresentation: data, relativeTo: nil)
        }
        if let string = item as? String {
            return URL(string: string) ?? URL(fileURLWithPath: string)
        }
        return nil
    }

    private func readJSON<T: Decodable>(_ type: T.Type, from url: URL) -> T? {
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(T.self, from: data)
    }

    private func isVideoAsset(_ asset: URL?) -> Bool {
        guard let ext = asset?.pathExtension.lowercased() else { return false }
        return ["mp4", "mov", "m4v"].contains(ext)
    }

    private func isUsablePlaybackCandidate(_ asset: URL) -> Bool {
        if isVideoAsset(asset) {
            return isPlayableVideoFile(asset)
        }
        if isAudioAsset(asset) {
            return FileManager.default.fileExists(atPath: asset.path) && (fileSize(at: asset) ?? 0) > 0
        }
        return false
    }

    private func isPlayableVideoFile(_ asset: URL) -> Bool {
        guard isVideoAsset(asset),
              FileManager.default.fileExists(atPath: asset.path),
              (fileSize(at: asset) ?? 0) > 0
        else {
            return false
        }
        return hasMovieHeaderAtom(asset)
    }

    private func hasMovieHeaderAtom(_ asset: URL) -> Bool {
        guard let size = fileSize(at: asset), size >= 8,
              let handle = try? FileHandle(forReadingFrom: asset)
        else {
            return false
        }
        defer { try? handle.close() }

        let fileSize = UInt64(size)
        var offset: UInt64 = 0
        while offset + 8 <= fileSize {
            do {
                try handle.seek(toOffset: offset)
            } catch {
                return false
            }
            guard let header = readBytes(8, from: handle) else {
                return false
            }
            let size32 = (UInt64(header[0]) << 24)
                | (UInt64(header[1]) << 16)
                | (UInt64(header[2]) << 8)
                | UInt64(header[3])
            let atom = String(bytes: header[4..<8], encoding: .ascii) ?? ""
            if atom == "moov" {
                return true
            }

            let headerSize: UInt64
            let atomSize: UInt64
            if size32 == 1 {
                guard let extended = readBytes(8, from: handle) else {
                    return false
                }
                atomSize = extended.reduce(UInt64(0)) { ($0 << 8) | UInt64($1) }
                headerSize = 16
            } else if size32 == 0 {
                return false
            } else {
                atomSize = size32
                headerSize = 8
            }

            if atomSize < headerSize {
                return false
            }
            offset += atomSize
        }
        return false
    }

    private func readBytes(_ count: Int, from handle: FileHandle) -> [UInt8]? {
        guard let data = try? handle.read(upToCount: count), data.count == count else {
            return nil
        }
        return Array(data)
    }

    private func isSupportedVideoURL(_ url: URL) -> Bool {
        isVideoAsset(url)
    }

    private func storageDetailLine(for takeURL: URL, physicalBytes: Int64?) -> String {
        let logicalBytes = directorySize(at: takeURL, countHardlinksOnce: false)
        let hardlinkSavings = max(0, (logicalBytes ?? 0) - (physicalBytes ?? 0))
        if hardlinkSavings > 0 {
            return "\(HostEnvironment.byteString(hardlinkSavings)) deduped"
        }
        if let receipt = readJSON(StorageReceiptSummary.self, from: takeURL.appendingPathComponent("render/storage_receipt.json")),
           receipt.status == "ready" || receipt.status == "partial" {
            let saved = receipt.bytesSavedPhysical ?? 0
            if saved > 0 {
                return "\(HostEnvironment.byteString(saved)) saved"
            }
            return receipt.storageProfile == "efficient" ? "optimized" : "source"
        }
        if hasSeparateScreenAndRoughCut(takeURL) {
            return "can optimize"
        }
        if sessionTrackCandidates(for: takeURL, roles: ["external_video"]).isEmpty == false {
            return "single imported asset"
        }
        return ""
    }

    private func hasSeparateScreenAndRoughCut(_ takeURL: URL) -> Bool {
        guard let screen = sessionTrackCandidates(for: takeURL, roles: ["screen"]).first,
              let roughCut = roughCutCandidates(for: takeURL).first,
              FileManager.default.fileExists(atPath: screen.path),
              FileManager.default.fileExists(atPath: roughCut.path)
        else {
            return false
        }
        return fileIdentity(for: screen) != fileIdentity(for: roughCut)
    }

    private func isTakeBusy(_ takeURL: URL) -> Bool {
        let takeID = takeURL.lastPathComponent
        return backgroundFinalizingTakeIDs.contains(takeID) || backgroundBuildingTakeIDs.contains(takeID)
    }

    private func isSameTakeURL(_ left: URL?, _ right: URL) -> Bool {
        left?.standardizedFileURL.path == right.standardizedFileURL.path
    }

    private func fileIdentity(for url: URL) -> String? {
        guard let attributes = try? FileManager.default.attributesOfItem(atPath: url.path),
              let device = attributes[.systemNumber] as? NSNumber,
              let inode = attributes[.systemFileNumber] as? NSNumber
        else {
            return nil
        }
        return "\(device.int64Value):\(inode.int64Value)"
    }

    private func directorySize(at url: URL, countHardlinksOnce: Bool = true) -> Int64? {
        let keys: [URLResourceKey] = [
            .isRegularFileKey,
            .fileAllocatedSizeKey,
            .totalFileAllocatedSizeKey,
        ]
        guard let enumerator = FileManager.default.enumerator(
            at: url,
            includingPropertiesForKeys: keys,
            options: [.skipsHiddenFiles]
        ) else {
            return nil
        }

        var total: Int64 = 0
        var seenFiles = Set<String>()
        for case let fileURL as URL in enumerator {
            guard let values = try? fileURL.resourceValues(forKeys: Set(keys)),
                  values.isRegularFile == true
            else {
                continue
            }
            if countHardlinksOnce, let identity = fileIdentity(for: fileURL) {
                if seenFiles.contains(identity) {
                    continue
                }
                seenFiles.insert(identity)
            }
            total += Int64(values.totalFileAllocatedSize ?? values.fileAllocatedSize ?? 0)
        }
        return total
    }

    private func refreshPlaybackDuration(for asset: URL) {
        let avAsset = AVURLAsset(url: asset)
        Task {
            let duration = try? await avAsset.load(.duration)
            let seconds = duration?.seconds ?? 0
            await MainActor.run {
                guard self.playbackURL == asset else { return }
                self.playbackDuration = seconds.isFinite && seconds > 0 ? seconds : 0
            }
        }
    }

    private func clearPlayback() {
        playbackPlayer?.pause()
        playbackCameraPlayer?.pause()
        if let playbackTimeObserver, let playbackPlayer {
            playbackPlayer.removeTimeObserver(playbackTimeObserver)
        }
        if let playbackEndObserver {
            NotificationCenter.default.removeObserver(playbackEndObserver)
        }
        playbackTimeObserver = nil
        playbackEndObserver = nil
        playbackPlayer = nil
        playbackCameraPlayer = nil
        playbackURL = nil
        playbackCameraURL = nil
        playbackTitle = "No playback loaded"
        playbackCameraTitle = "Camera"
        playbackCameraOverlayLayout = .default
        playbackStatus = "Stop a recording to review it here."
        playbackSourceLabel = "No review asset"
        playbackSourceSystemImage = "play.rectangle"
        playbackPosition = 0
        playbackDuration = 0
        playbackIsPlaying = false
    }

    private func schedulePreviewTimer() {
        previewTimer?.invalidate()
        previewTimer = nil
    }

    private func updateAudioMeter(forceRestart: Bool = false) {
        guard !captureControlsActive else { return }
        guard let selectedAudio else {
            audioLevelMonitor.stop()
            liveMicrophoneMonitorActive = false
            microphoneLevel = 0
            microphoneMeterStatus = "No microphone selected"
            return
        }
        guard selectedAudioIsAvailable else {
            audioLevelMonitor.stop()
            liveMicrophoneMonitorActive = false
            microphoneLevel = 0
            microphoneMeterStatus = "\(selectedAudio.name) is not visible to macOS. Reconnect it, then Reload devices."
            return
        }
        guard permissions.microphone == .ready else {
            audioLevelMonitor.stop()
            liveMicrophoneMonitorActive = false
            microphoneLevel = 0
            microphoneMeterStatus = "\(selectedAudio.name) selected; microphone permission needed for live level."
            return
        }
        guard forceRestart || liveMicrophoneMonitorActive else {
            microphoneLevel = 0
            microphoneMeterStatus = "\(selectedAudio.name) ready. Use Mic check for a live level."
            return
        }
        liveMicrophoneMonitorActive = true
        audioLevelMonitor.start(
            preferredDeviceName: selectedAudio.name,
            preferredDeviceUniqueID: selectedAudio.uniqueID
        ) { [weak self] level, status in
            Task { @MainActor in
                self?.microphoneLevel = level
                self?.microphoneMeterStatus = status
            }
        }
    }

    private func updateCameraPreview() {
        guard !captureControlsActive && state != .countingDown else { return }
        guard webcamEnabled, let selectedWebcam else {
            cameraPreviewService.stop()
            cameraPreviewSession = nil
            cameraPreviewStatus = "Webcam off; no camera track will be recorded."
            return
        }
        guard permissions.camera == .ready else {
            cameraPreviewService.stop()
            cameraPreviewSession = nil
            cameraPreviewStatus = permissions.camera == .missing
                ? "Camera permission needed before preview."
                : "Request camera access to enable preview."
            return
        }
        do {
            cameraPreviewSession = try cameraPreviewService.start(preferredDeviceName: selectedWebcam.name)
            cameraPreviewStatus = "Preview active; recorded as a separate webcam track."
        } catch {
            cameraPreviewSession = nil
            cameraPreviewStatus = error.localizedDescription
        }
    }

    private func stopConfidencePreviewForRecording() {
        previewTimer?.invalidate()
        cameraPreviewService.stop()
        cameraPreviewSession = nil
        cameraPreviewStatus = "Preview stopped while capture owns the camera track."
        microphoneMeterStatus = selectedAudio == nil
            ? "No microphone selected"
            : "Live mic monitor active during recording."
    }

    private func updateScreenPreviewPlaceholders(message: String? = nil) {
        for device in selectedScreens {
            screenPreviewStatus[device.id] = message ?? (screenPreviewEnabled
                ? "Snapshot preview disabled; Start records this display through FFmpeg."
                : "Selected for recording.")
        }
    }

    private func persistOpenMediaSegment(
        index: Int,
        screenTracks: [NativeScreenCaptureTrack],
        audioTrack: NativeAudioCaptureTrack?,
        cameraTrack: NativeCameraCaptureTrack?,
        timelineStartedAt: Date,
        to takeURL: URL
    ) {
        guard var session = loadSessionPayload(from: takeURL) else { return }
        let segmentID = String(format: "segment_%04d", index)
        let screenPayloads = screenTracks.map { screenTrackPayload($0, timelineStartedAt: timelineStartedAt) }
        let audioPayload = audioTrack.map { audioTrackPayload($0, timelineStartedAt: timelineStartedAt) }
        let cameraPayload = cameraTrack.map { cameraTrackPayload($0, timelineStartedAt: timelineStartedAt) }
        let isoFormatter = ISO8601DateFormatter()
        var segment: [String: Any] = [
            "schema": "demo_take_media_segment_v0",
            "id": segmentID,
            "index": index,
            "started_at": isoFormatter.string(from: timelineStartedAt),
            "timeline_started_at": isoFormatter.string(from: timelineStartedAt),
            "status": "recording",
            "screen_tracks": screenPayloads,
        ]
        if let audioPayload {
            segment["microphone_track"] = audioPayload
        } else {
            segment["microphone_track"] = NSNull()
        }
        if let cameraPayload {
            segment["webcam_track"] = cameraPayload
        } else {
            segment["webcam_track"] = NSNull()
        }

        var segments = session["media_segments"] as? [[String: Any]] ?? []
        if let existingIndex = segments.firstIndex(where: { $0["id"] as? String == segmentID }) {
            segments[existingIndex] = segment
        } else {
            segments.append(segment)
        }
        session["media_segments"] = segments.sorted { left, right in
            (left["index"] as? Int ?? 0) < (right["index"] as? Int ?? 0)
        }

        var tracks = session["tracks"] as? [[String: Any]] ?? []
        var segmentTracks = screenPayloads
        if let audioPayload {
            segmentTracks.append(audioPayload)
        }
        if let cameraPayload {
            segmentTracks.append(cameraPayload)
        }
        for track in segmentTracks {
            guard let relativePath = track["relative_path"] as? String else { continue }
            if !tracks.contains(where: { $0["relative_path"] as? String == relativePath }) {
                tracks.append(track)
            }
        }
        session["tracks"] = tracks
        writeSessionPayload(session, to: takeURL)
    }

    private func closeCurrentMediaSegment(status: String, in takeURL: URL) {
        guard currentRecordingSegmentIndex > 0 else { return }
        guard var session = loadSessionPayload(from: takeURL) else { return }
        let segmentID = String(format: "segment_%04d", currentRecordingSegmentIndex)
        var segments = session["media_segments"] as? [[String: Any]] ?? []
        guard let index = segments.firstIndex(where: { $0["id"] as? String == segmentID }) else { return }
        if segments[index]["ended_at"] == nil || segments[index]["ended_at"] is NSNull {
            segments[index]["ended_at"] = ISO8601DateFormatter().string(from: Date())
        }
        segments[index]["status"] = status
        session["media_segments"] = segments
        writeSessionPayload(session, to: takeURL)
    }

    private func screenTrackPayload(_ track: NativeScreenCaptureTrack, timelineStartedAt: Date) -> [String: Any] {
        var payload: [String: Any] = [
            "id": trackID(role: "screen", device: track.device, relativePath: track.relativePath),
            "role": "screen",
            "device_name": track.device.name,
            "device_index": track.device.index,
            "relative_path": track.relativePath,
            "capture_engine": "screencapturekit",
        ]
        payload.merge(trackTimelineFields(startedAt: track.startedAt, timelineStartedAt: timelineStartedAt)) { _, new in new }
        if let uniqueID = track.device.uniqueID, !uniqueID.isEmpty {
            payload["device_unique_id"] = uniqueID
        }
        return payload
    }

    private func audioTrackPayload(_ track: NativeAudioCaptureTrack, timelineStartedAt: Date) -> [String: Any] {
        var payload: [String: Any] = [
            "id": trackID(role: "microphone", device: track.device, relativePath: track.relativePath),
            "role": "microphone",
            "device_name": track.device.name,
            "device_index": track.device.index,
            "relative_path": track.relativePath,
            "capture_engine": "avfoundation_native",
        ]
        payload.merge(trackTimelineFields(startedAt: track.startedAt, timelineStartedAt: timelineStartedAt)) { _, new in new }
        if let uniqueID = track.device.uniqueID, !uniqueID.isEmpty {
            payload["device_unique_id"] = uniqueID
        }
        return payload
    }

    private func cameraTrackPayload(_ track: NativeCameraCaptureTrack, timelineStartedAt: Date) -> [String: Any] {
        var payload: [String: Any] = [
            "id": trackID(role: "webcam", device: track.device, relativePath: track.relativePath),
            "role": "webcam",
            "device_name": track.device.name,
            "device_index": track.device.index,
            "relative_path": track.relativePath,
            "capture_engine": "avfoundation_native_camera",
        ]
        payload.merge(trackTimelineFields(startedAt: track.startedAt, timelineStartedAt: timelineStartedAt)) { _, new in new }
        if let uniqueID = track.device.uniqueID, !uniqueID.isEmpty {
            payload["device_unique_id"] = uniqueID
        }
        return payload
    }

    private func trackTimelineFields(startedAt: Date, timelineStartedAt: Date) -> [String: Any] {
        let formatter = ISO8601DateFormatter()
        let offset = max(0, timelineStartedAt.timeIntervalSince(startedAt))
        return [
            "capture_started_at": formatter.string(from: startedAt),
            "timeline_offset_seconds": Double((offset * 1000).rounded() / 1000),
        ]
    }

    private func trackID(role: String, device: CaptureDevice, relativePath: String) -> String {
        let suffix = relativePath
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: ".", with: "_")
        return "\(role)_\(device.index)_\(suffix)"
    }

    private func loadSessionPayload(from takeURL: URL) -> [String: Any]? {
        let url = takeURL.appendingPathComponent("session.json")
        guard let data = try? Data(contentsOf: url) else { return nil }
        return (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
    }

    private func writeSessionPayload(_ payload: [String: Any], to takeURL: URL) {
        guard JSONSerialization.isValidJSONObject(payload),
              let output = try? JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys])
        else {
            return
        }
        try? output.write(to: takeURL.appendingPathComponent("session.json"), options: [.atomic])
    }

    private func appendStartAttempt(_ event: String, detail: String? = nil, takeURL: URL? = nil) {
        guard let takeURL = takeURL ?? activeTakeURL else { return }
        let url = takeURL.appendingPathComponent("start_attempt.jsonl")
        var payload: [String: Any] = [
            "schema": "demo_take_start_attempt_event_v0",
            "at": ISO8601DateFormatter().string(from: Date()),
            "event": event,
            "state": state.rawValue,
            "selected_screens": selectedScreens.map(\.name),
        ]
        if let detail, !detail.isEmpty {
            payload["detail"] = detail
        }
        if let selectedAudio {
            payload["selected_microphone"] = selectedAudio.name
            if let uniqueID = selectedAudio.uniqueID, !uniqueID.isEmpty {
                payload["selected_microphone_unique_id"] = uniqueID
            }
        }
        guard JSONSerialization.isValidJSONObject(payload),
              let data = try? JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys])
        else {
            return
        }

        var line = data
        line.append(0x0A)
        appendJSONLine(line, to: url)
    }

    private func appendPreStartAttempt(_ event: String, detail: String? = nil) {
        let url = recorderConfigURL
            .deletingLastPathComponent()
            .appendingPathComponent("demo_take_prestart_attempts.jsonl")
        var payload: [String: Any] = [
            "schema": "demo_take_prestart_attempt_event_v0",
            "at": ISO8601DateFormatter().string(from: Date()),
            "event": event,
            "state": state.rawValue,
            "selected_screens": selectedScreens.map(\.name),
            "start_blockers": startBlockers,
        ]
        if let detail, !detail.isEmpty {
            payload["detail"] = detail
        }
        if let selectedAudio {
            payload["selected_microphone"] = selectedAudio.name
            if let uniqueID = selectedAudio.uniqueID, !uniqueID.isEmpty {
                payload["selected_microphone_unique_id"] = uniqueID
            }
        }
        guard JSONSerialization.isValidJSONObject(payload),
              let data = try? JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys])
        else {
            return
        }

        var line = data
        line.append(0x0A)
        appendJSONLine(line, to: url)
    }

    private func appendJSONLine(_ line: Data, to url: URL) {
        if FileManager.default.fileExists(atPath: url.path),
           let handle = try? FileHandle(forWritingTo: url) {
            handle.seekToEndOfFile()
            handle.write(line)
            handle.closeFile()
        } else {
            try? FileManager.default.createDirectory(
                at: url.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            try? line.write(to: url, options: [.atomic])
        }
    }

    private func persistTakeKnownFailure(_ failure: String, to takeURL: URL) {
        let url = takeURL.appendingPathComponent("session.json")
        guard let data = try? Data(contentsOf: url),
              var payload = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
        else {
            return
        }
        var failures = payload["known_failures"] as? [String] ?? []
        if !failures.contains(failure) {
            failures.append(failure)
        }
        payload["known_failures"] = failures
        guard JSONSerialization.isValidJSONObject(payload),
              let output = try? JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys])
        else {
            return
        }
        try? output.write(to: url, options: [.atomic])
    }

    private func appendStatus(_ line: String) {
        statusLines.insert(line, at: 0)
        statusLines = Array(statusLines.prefix(12))
    }
}
