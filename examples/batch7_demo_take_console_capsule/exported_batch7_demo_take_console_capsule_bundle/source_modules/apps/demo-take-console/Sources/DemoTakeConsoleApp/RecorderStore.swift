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

    enum CodingKeys: String, CodingKey {
        case title
        case takeTitle = "take_title"
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
    @Published var microphoneTestInProgress = false
    @Published var cameraPreviewSession: AVCaptureSession?
    @Published var cameraPreviewStatus = "Camera preview off"
    @Published var screenPreviewEnabled = false
    @Published var screenSnapshots: [String: NSImage] = [:]
    @Published var screenPreviewStatus: [String: String] = [:]
    @Published var countdownValue: Int?
    @Published var markers: [Marker] = []
    @Published var hudVisible: Bool = false
    @Published var scheduleState: RunMapScheduleState?
    @Published var scheduleStatus: String = "Run map idle"
    @Published var playbackPlayer: AVPlayer?
    @Published var playbackURL: URL?
    @Published var playbackTitle: String = "No playback loaded"
    @Published var playbackStatus: String = "Stop a recording to review it here."
    @Published var playbackSourceLabel: String = "No review asset"
    @Published var playbackSourceSystemImage: String = "play.rectangle"
    @Published var playbackPosition: TimeInterval = 0
    @Published var playbackDuration: TimeInterval = 0
    @Published var playbackIsPlaying = false
    @Published var recentTakes: [TakeSummary] = []

    private var timer: Timer?
    private var previewTimer: Timer?
    private var scheduleTimer: Timer?
    private var playbackTimeObserver: Any?
    private var playbackEndObserver: NSObjectProtocol?
    private var recordingStartedAt: Date?
    private var hasAppliedInitialDefaults = false
    private let audioLevelMonitor = AudioLevelMonitor()
    private let cameraPreviewService = CameraPreviewService()
    var onHudShouldShow: (() -> Void)?
    var onHudShouldHide: (() -> Void)?
    private let minimumStartDiskBytes: Int64 = 1_000_000_000

    init() {
        refreshTakeHistory(selectLatestIfNone: true)
        refreshRecentImportCandidate()
    }

    var canMark: Bool {
        state == .recording || state == .paused
    }

    var markerCount: Int { markers.count }

    var lastMarker: Marker? { markers.last }

    var canStart: Bool {
        guard state == .ready || state == .idle || state == .reviewReady || state == .packageReady || state == .packageFailed else {
            return false
        }
        return startBlockers.isEmpty
    }

    var canPauseOrResume: Bool {
        state == .recording || state == .paused
    }

    var canStop: Bool {
        state == .recording || state == .paused
    }

    var canDiscardTake: Bool {
        guard activeTakeURL != nil else { return false }
        return canManageTakes
    }

    var canManageTakes: Bool {
        switch state {
        case .recording, .paused, .stopping, .postprocessing, .countingDown:
            return false
        default:
            return true
        }
    }

    var canBuildPackage: Bool {
        guard activeTakeURL != nil else { return false }
        return canManageTakes
    }

    var canRenameActiveTake: Bool {
        guard activeTakeURL != nil, canManageTakes, !titleSaveInProgress else { return false }
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
        activeTakeURL != nil && canManageTakes && !storageOptimizeInProgress
    }

    var canOptimizeAllStorage: Bool {
        canManageTakes && !storageOptimizeInProgress && !recentTakes.isEmpty
    }

    var canExportVideo: Bool {
        guard let activeTakeURL else { return false }
        return canManageTakes && !exportVideoInProgress && videoAssetURL(for: activeTakeURL) != nil
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
        return playbackAssetURL(for: activeTakeURL) != nil
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

    var playbackFileLine: String {
        guard let playbackURL else { return "No playback file loaded." }
        let sizeSuffix = fileSize(at: playbackURL).map { " · \(HostEnvironment.byteString($0))" } ?? ""
        return "\(playbackSourceLabel): \(playbackURL.lastPathComponent)\(sizeSuffix)"
    }

    var activeTakeStorageLine: String {
        guard let activeTakeURL else { return "" }
        return takeStorageLine(for: activeTakeURL)
    }

    var selectedScreens: [CaptureDevice] {
        devices.videoDevices
            .filter { $0.isScreen && selectedScreenIDs.contains($0.id) }
            .sorted { $0.index < $1.index }
    }

    var selectedAudio: CaptureDevice? {
        devices.audioDevices.first { $0.id == selectedAudioID }
    }

    var selectedWebcam: CaptureDevice? {
        guard webcamEnabled else { return nil }
        return devices.videoDevices.first { $0.id == selectedWebcamID }
    }

    var selectedScreenMetadata: [String: DisplayMetadata] {
        Dictionary(uniqueKeysWithValues: devices.videoDevices.filter(\.isScreen).map { device in
            (device.id, HostEnvironment.displayMetadata(forFFmpegScreenIndex: device.screenOrdinal))
        })
    }

    var setupTitle: String {
        if state == .recording || state == .paused || state == .postprocessing || state == .packageReady || state == .packageFailed {
            return state.label
        }
        return startBlockers.isEmpty ? "Ready to record" : "Setup needed"
    }

    var setupDetail: String {
        if startBlockers.isEmpty {
            return autoHideBeforeRecording
                ? "Start runs a countdown, hides the console, then starts FFmpeg."
                : "Start records the selected display and microphone with the console still visible."
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
        return "Long multi-screen take: \(free > long * 2 ? "OK" : "tight") · est. \(HostEnvironment.byteString(long))"
    }

    var screenSourceStatus: CapabilityStatus {
        selectedScreens.isEmpty ? .missing : .ready
    }

    var microphoneSourceStatus: CapabilityStatus {
        selectedAudio == nil ? .notRequired : .ready
    }

    var cameraSourceStatus: CapabilityStatus {
        guard webcamEnabled else { return .notRequired }
        return selectedWebcam == nil ? .unknown : .ready
    }

    var startBlockers: [String] {
        var blockers: [String] = []
        if ffmpegPath == nil { blockers.append("FFmpeg not found") }
        if selectedScreens.isEmpty { blockers.append("Select at least one display") }
        if permissions.disk == .low { blockers.append("Disk space is tight") }
        return blockers
    }

    func reloadSetup() async {
        await refreshPreflight()
        appendStatus("Source list reloaded. Start will run the real FFmpeg capture path.")
    }

    func useSimpleDefaults() {
        applySimpleDefaults(announce: true)
        updateAudioMeter()
        updateCameraPreview()
        updateScreenPreviewPlaceholders()
    }

    func refreshPreflight() async {
        ffmpegPath = HostEnvironment.findFFmpeg()
        permissions.ffmpeg = ffmpegPath == nil ? .missing : .ready
        transcribeBinaryPath = HostEnvironment.findTranscribeBinary()
        permissions.microphone = PermissionService.microphoneStatus()
        diskFreeBytes = HostEnvironment.availableDiskBytes(at: HostEnvironment.outputRoot)
        permissions.disk = diskStatus(bytes: diskFreeBytes)

        if let ffmpegPath {
            do {
                devices = try await CaptureHelperClient.loadDevices(ffmpegPath: ffmpegPath)
                applyDefaultSelections()
            } catch {
                appendStatus("Could not enumerate FFmpeg AVFoundation devices: \(error.localizedDescription)")
            }
        }

        permissions.camera = PermissionService.cameraStatus(required: webcamEnabled)
        state = startBlockers.isEmpty ? .ready : .setupNeeded
        updateAudioMeter()
        updateCameraPreview()
        updateScreenPreviewPlaceholders()
        schedulePreviewTimer()
        refreshTakeHistory(selectLatestIfNone: activeTakeURL == nil)
        refreshRecentImportCandidate()
    }

    func setScreen(_ device: CaptureDevice, enabled: Bool) {
        if enabled {
            selectedScreenIDs.insert(device.id)
        } else {
            selectedScreenIDs.remove(device.id)
        }
        if screenPreviewEnabled {
            refreshScreenSnapshots()
        } else {
            updateScreenPreviewPlaceholders()
        }
    }

    func selectAudio(_ id: String) {
        selectedAudioID = id.isEmpty ? nil : id
        microphoneLevel = 0
        updateAudioMeter()
    }

    func testMicrophone() async {
        guard !microphoneTestInProgress else { return }
        guard let selectedAudio else {
            microphoneMeterStatus = "No microphone selected"
            microphoneLevel = 0
            return
        }
        guard let ffmpegPath else {
            microphoneMeterStatus = "FFmpeg not found"
            microphoneLevel = 0
            return
        }

        microphoneTestInProgress = true
        microphoneLevel = 0.18
        microphoneMeterStatus = "Testing \(selectedAudio.name) with FFmpeg..."
        defer { microphoneTestInProgress = false }

        do {
            let response = try await CaptureHelperClient.testMicrophone(
                ffmpegPath: ffmpegPath,
                microphone: selectedAudio
            )
            for line in response.statusLines.reversed() {
                appendStatus(line)
            }
            if response.status == "ready" {
                microphoneLevel = 0.78
                microphoneMeterStatus = "Mic test passed: \(selectedAudio.name)"
            } else {
                microphoneLevel = 0
                microphoneMeterStatus = response.statusLines.last ?? "Mic test failed"
            }
        } catch {
            microphoneLevel = 0
            microphoneMeterStatus = "Mic test failed: \(error.localizedDescription)"
            appendStatus(microphoneMeterStatus)
        }
    }

    func setWebcamEnabled(_ enabled: Bool) {
        webcamEnabled = enabled
        permissions.camera = PermissionService.cameraStatus(required: webcamEnabled)
        updateCameraPreview()
    }

    func selectWebcam(_ id: String) {
        selectedWebcamID = id.isEmpty ? nil : id
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
        screenPreviewEnabled = true
        for device in selectedScreens {
            screenPreviewStatus[device.id] = "Snapshot preview is disabled so the console never opens macOS Screen Recording prompts."
        }
        schedulePreviewTimer()
    }

    func startRecording() async {
        await refreshPreflight()
        guard canStart, let ffmpegPath else {
            appendStatus("Start blocked: \(startBlockers.joined(separator: ", ")).")
            return
        }

        do {
            state = .countingDown
            for value in stride(from: 3, through: 1, by: -1) {
                countdownValue = value
                try await Task.sleep(nanoseconds: 1_000_000_000)
            }
            countdownValue = nil
            stopConfidencePreviewForRecording()
            markers = []
            showHud()
            if autoHideBeforeRecording {
                appendStatus("Console hidden; HUD floats over selected displays.")
                NSApp.hide(nil)
                try await Task.sleep(nanoseconds: 250_000_000)
            } else {
                appendStatus("Console remains visible; HUD floats over selected displays.")
            }

            let response = try await CaptureHelperClient.start(
                ffmpegPath: ffmpegPath,
                screens: selectedScreens,
                microphone: selectedAudio,
                webcam: selectedWebcam,
                screenshotInterval: screenshotInterval,
                transcribeBinary: transcribeBinaryPath,
                transcribeModel: transcribeModel,
                takeTitle: recordingTitle
            )
            activeTakeURL = URL(fileURLWithPath: response.rootPath, isDirectory: true)
            let title = normalizedTakeTitle(response.title ?? recordingTitle)
            activeTakeTitle = title
            takeTitleDraft = title
            recordingTitle = ""
            refreshTakeHistory()
            state = .recording
            recordingStartedAt = Date()
            startTimer()
            startScheduleTimer()
            for line in response.statusLines.reversed() {
                appendStatus(line)
            }
            appendStatus("Recording started: \(response.takeID).")
        } catch {
            state = .packageFailed
            countdownValue = nil
            hideHud()
            NSApp.unhide(nil)
            NSApp.activate(ignoringOtherApps: true)
            appendStatus("Recording start failed: \(error.localizedDescription).")
            updateAudioMeter()
            updateCameraPreview()
            schedulePreviewTimer()
        }
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
        guard let activeTakeURL else { return }
        switch state {
        case .recording:
            Task {
                do {
                    let response = try await CaptureHelperClient.pause(takeRoot: activeTakeURL)
                    timer?.invalidate()
                    scheduleTimer?.invalidate()
                    state = .paused
                    for line in response.statusLines.reversed() { appendStatus(line) }
                    appendStatus("Recording paused. Stop to finalize and review saved playback.")
                } catch {
                    appendStatus("Pause failed: \(error.localizedDescription).")
                }
            }
        case .paused:
            Task {
                do {
                    let response = try await CaptureHelperClient.resume(takeRoot: activeTakeURL)
                    startTimer()
                    startScheduleTimer()
                    state = .recording
                    for line in response.statusLines.reversed() { appendStatus(line) }
                    appendStatus("Recording resumed.")
                } catch {
                    appendStatus("Resume failed: \(error.localizedDescription).")
                }
            }
        default:
            break
        }
    }

    func stopRecording() async {
        guard let activeTakeURL else { return }
        pausePlayback()
        timer?.invalidate()
        scheduleTimer?.invalidate()
        state = .stopping
        appendStatus("Stopping capture processes.")

        do {
            state = .postprocessing
            appendStatus("Finalizing saved tracks for review.")
            let response = try await CaptureHelperClient.finalize(takeRoot: activeTakeURL)
            for line in response.statusLines.reversed() {
                appendStatus(line)
            }
            hideHud()
            NSApp.unhide(nil)
            NSApp.activate(ignoringOtherApps: true)
            loadPlaybackAsset(from: activeTakeURL)
            refreshTakeHistory()
            state = playbackURL == nil && !(response.knownFailures ?? []).isEmpty ? .packageFailed : .reviewReady
            appendStatus("Review ready: \(response.rootPath). \(markers.count) marker(s).")
            updateAudioMeter()
            updateCameraPreview()
            schedulePreviewTimer()
            scheduleState = nil
            scheduleStatus = "Run map idle"
        } catch {
            state = .packageFailed
            hideHud()
            NSApp.unhide(nil)
            NSApp.activate(ignoringOtherApps: true)
            appendStatus("Stop/postprocess failed: \(error.localizedDescription).")
            loadPlaybackAsset(from: activeTakeURL)
            refreshTakeHistory()
            updateAudioMeter()
            updateCameraPreview()
            schedulePreviewTimer()
            scheduleState = nil
            scheduleStatus = "Run map unavailable"
        }
    }

    func buildPackageSidecars() async {
        guard let activeTakeURL, canBuildPackage else { return }
        pausePlayback()
        state = .postprocessing
        appendStatus("Building full package sidecars.")

        do {
            let response = try await CaptureHelperClient.postprocess(takeRoot: activeTakeURL)
            state = (response.knownFailures ?? []).isEmpty ? .packageReady : .packageFailed
            for line in response.statusLines.reversed() {
                appendStatus(line)
            }
            loadPlaybackAsset(from: activeTakeURL)
            refreshTakeHistory()
            appendStatus("Full package build finished.")
        } catch {
            state = .packageFailed
            appendStatus("Package build failed: \(error.localizedDescription).")
            loadPlaybackAsset(from: activeTakeURL)
            refreshTakeHistory()
        }
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

        let targets = recentTakes.map(\.url)
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
        hudVisible = true
        onHudShouldShow?()
    }

    private func hideHud() {
        hudVisible = false
        onHudShouldHide?()
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
        selectTakeForReview(takeURL, announce: false)
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
        playbackPlayer?.play()
        playbackIsPlaying = true
        playbackStatus = "Playing \(playbackTitle)"
    }

    func pausePlayback() {
        playbackPlayer?.pause()
        playbackIsPlaying = false
        if playbackURL != nil {
            playbackStatus = "Paused \(playbackTitle)"
        }
    }

    func seekPlayback(to seconds: TimeInterval) {
        guard let player = playbackPlayer else { return }
        let bounded = min(max(seconds, 0), max(playbackDuration, 0))
        playbackPosition = bounded
        player.seek(to: CMTime(seconds: bounded, preferredTimescale: 600), toleranceBefore: .zero, toleranceAfter: .zero)
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

        if selectLatestIfNone, activeTakeURL == nil, let latest = recentTakes.first {
            selectTakeForReview(latest.url, announce: false)
            return
        }
        refreshActiveTakeExportStatus()
    }

    func selectTakeForReview(_ takeURL: URL, announce: Bool = true) {
        guard canManageTakes else {
            appendStatus("Stop the current recording before switching takes.")
            return
        }
        guard FileManager.default.fileExists(atPath: takeURL.path) else {
            appendStatus("Take no longer exists: \(takeURL.lastPathComponent).")
            refreshTakeHistory()
            return
        }

        pausePlayback()
        activeTakeURL = takeURL
        activeTakeTitle = titleForTake(takeURL) ?? ""
        takeTitleDraft = activeTakeTitle
        elapsed = 0
        markers = []
        recordingStartedAt = nil
        scheduleState = nil
        scheduleStatus = "Run map idle"
        loadPlaybackAsset(from: takeURL)
        refreshActiveTakeExportStatus()
        state = playbackURL == nil ? (startBlockers.isEmpty ? .ready : .setupNeeded) : .reviewReady
        if announce {
            appendStatus("Loaded \(activeTakeDisplayName) for review.")
        }
    }

    func deleteTake(_ takeURL: URL) {
        guard canManageTakes else {
            appendStatus("Stop the current recording before deleting takes.")
            return
        }
        let fileManager = FileManager.default
        let isActive = activeTakeURL?.path == takeURL.path
        let name = takeURL.lastPathComponent
        if isActive {
            clearPlayback()
        }
        do {
            try fileManager.removeItem(at: takeURL)
            if isActive {
                activeTakeURL = nil
                activeTakeTitle = ""
                takeTitleDraft = ""
                clearActiveTakeExportStatus()
                elapsed = 0
                markers = []
                recordingStartedAt = nil
                scheduleState = nil
                scheduleStatus = "Run map idle"
                state = startBlockers.isEmpty ? .ready : .setupNeeded
            }
            refreshTakeHistory(selectLatestIfNone: isActive)
            appendStatus("Deleted \(name).")
        } catch {
            appendStatus("Delete failed for \(name): \(error.localizedDescription).")
        }
    }

    func discardTakeAndReset() {
        guard let activeTakeURL, canDiscardTake else { return }
        deleteTake(activeTakeURL)
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
            applySimpleDefaults(announce: false)
            hasAppliedInitialDefaults = true
            return
        }
        if selectedScreenIDs.isEmpty {
            selectedScreenIDs = defaultScreenSelection()
        }
        if selectedAudioID == nil {
            selectedAudioID = preferredAudioDevice()?.id
        }
        if selectedWebcamID == nil {
            selectedWebcamID = devices.videoDevices.first(where: { $0.isLikelyWebcam })?.id
        }
    }

    private func applySimpleDefaults(announce: Bool) {
        selectedScreenIDs = defaultScreenSelection()
        selectedAudioID = preferredAudioDevice()?.id
        selectedWebcamID = devices.videoDevices.first(where: { $0.isLikelyWebcam })?.id
        webcamEnabled = false
        autoHideBeforeRecording = false
        if announce {
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

    private func diskStatus(bytes: Int64?) -> CapabilityStatus {
        guard let bytes else {
            return .unknown
        }
        return bytes < minimumStartDiskBytes ? .low : .ready
    }

    private func estimatedBytes(seconds: Int64) -> Int64 {
        let screenBitsPerSecond = Int64(selectedScreens.count) * 6_000_000
        let webcamBitsPerSecond = selectedWebcam == nil ? 0 : 3_500_000
        let micBitsPerSecond = selectedAudio == nil ? 0 : 192_000
        let totalBits = (screenBitsPerSecond + Int64(webcamBitsPerSecond + micBitsPerSecond)) * seconds
        return totalBits / 8
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
        guard state == .recording || state == .paused else { return }
        let takeURL = activeTakeURL
        Task {
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

    private func loadPlaybackAsset(from takeURL: URL) {
        clearPlayback()
        guard let asset = playbackAssetURL(for: takeURL) else {
            playbackStatus = "No playable review asset found in this take."
            playbackTitle = "No playback loaded"
            return
        }

        let title = playbackTitle(for: asset, takeURL: takeURL)
        configurePlayback(
            asset: asset,
            title: title,
            readyStatus: "Ready to review \(title)",
            sourceLabel: "Take review",
            sourceSystemImage: isVideoAsset(asset) ? "film" : "waveform"
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
            sourceSystemImage: sourceSystemImage
        )
    }

    private func configurePlayback(
        asset: URL,
        title: String,
        readyStatus: String,
        sourceLabel: String,
        sourceSystemImage: String
    ) {
        let player = AVPlayer(url: asset)
        playbackPlayer = player
        playbackURL = asset
        playbackTitle = title
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
                self?.playbackPosition = time.seconds.isFinite ? max(time.seconds, 0) : 0
            }
        }
        playbackEndObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: player.currentItem,
            queue: .main
        ) { [weak self] _ in
            Task { @MainActor in
                self?.playbackIsPlaying = false
                self?.playbackStatus = "Finished \(self?.playbackTitle ?? "playback")"
            }
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
        activeTakeExportLine = status.line
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

        candidates += roughCutCandidates(for: takeURL)
        candidates.append(takeURL.appendingPathComponent("tracks/microphone.m4a"))
        candidates += sessionTrackCandidates(for: takeURL, roles: ["external_video", "screen", "webcam", "microphone"])

        for candidate in candidates where FileManager.default.fileExists(atPath: candidate.path) {
            return candidate
        }

        return sessionTrackCandidates(for: takeURL, roles: ["screen", "external_video"])
            .sorted { $0.lastPathComponent < $1.lastPathComponent }
            .first { FileManager.default.fileExists(atPath: $0.path) }
    }

    private func videoAssetURL(for takeURL: URL) -> URL? {
        var candidates: [URL] = []

        if let receipt = readJSON(RenderReceiptSummary.self, from: takeURL.appendingPathComponent("render/render_receipt.json")),
           let output = receipt.output,
           receipt.status != "failed" {
            candidates.append(takeURL.appendingPathComponent(output))
        }

        candidates += roughCutCandidates(for: takeURL)
        candidates += sessionTrackCandidates(for: takeURL, roles: ["external_video", "screen", "webcam"])

        return candidates.first { candidate in
            isVideoAsset(candidate) && FileManager.default.fileExists(atPath: candidate.path)
        }
    }

    private func playbackTitle(for asset: URL, takeURL: URL) -> String {
        let relative = asset.path.replacingOccurrences(of: takeURL.path + "/", with: "")
        if relative.hasPrefix("render/rough_cut.") {
            return "rough cut"
        }
        if relative == "tracks/microphone.m4a" {
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
            .filter { isVideoAsset($0) || $0.pathExtension.lowercased() == "m4a" }
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
        if let playbackTimeObserver, let playbackPlayer {
            playbackPlayer.removeTimeObserver(playbackTimeObserver)
        }
        if let playbackEndObserver {
            NotificationCenter.default.removeObserver(playbackEndObserver)
        }
        playbackTimeObserver = nil
        playbackEndObserver = nil
        playbackPlayer = nil
        playbackURL = nil
        playbackTitle = "No playback loaded"
        playbackStatus = "Stop a recording to review it here."
        playbackSourceLabel = "No review asset"
        playbackSourceSystemImage = "play.rectangle"
        playbackPosition = 0
        playbackDuration = 0
        playbackIsPlaying = false
    }

    private func schedulePreviewTimer() {
        previewTimer?.invalidate()
        guard state != .recording && state != .paused && state != .countingDown else { return }
        guard screenPreviewEnabled else { return }
        previewTimer = Timer.scheduledTimer(withTimeInterval: 5, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.refreshScreenSnapshots()
            }
        }
    }

    private func updateAudioMeter() {
        guard state != .recording && state != .paused else { return }
        guard let selectedAudio else {
            audioLevelMonitor.stop()
            microphoneLevel = 0
            microphoneMeterStatus = "No microphone selected"
            return
        }
        guard permissions.microphone == .ready else {
            audioLevelMonitor.stop()
            microphoneLevel = 0
            microphoneMeterStatus = "\(selectedAudio.name) selected; use Test Mic for the FFmpeg check."
            return
        }
        audioLevelMonitor.start(preferredDeviceName: selectedAudio.name) { [weak self] level, status in
            Task { @MainActor in
                self?.microphoneLevel = level
                self?.microphoneMeterStatus = status
            }
        }
    }

    private func updateCameraPreview() {
        guard state != .recording && state != .paused && state != .countingDown else { return }
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
        cameraPreviewStatus = "Preview stopped while FFmpeg owns the camera track."
        microphoneMeterStatus = selectedAudio == nil
            ? "No microphone selected"
            : "Live mic monitor active during recording."
    }

    private func updateScreenPreviewPlaceholders() {
        for device in selectedScreens {
            screenPreviewStatus[device.id] = screenPreviewEnabled
                ? "Snapshot preview disabled; Start records this display through FFmpeg."
                : "Selected for recording."
        }
    }

    private func appendStatus(_ line: String) {
        statusLines.insert(line, at: 0)
        statusLines = Array(statusLines.prefix(12))
    }
}
