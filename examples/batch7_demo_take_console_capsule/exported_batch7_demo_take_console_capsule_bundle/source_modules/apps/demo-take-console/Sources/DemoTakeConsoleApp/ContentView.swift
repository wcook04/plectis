import AppKit
import AVFoundation
import SwiftUI
import UniformTypeIdentifiers

// MARK: - Root shell
//
// Stage-first capture cockpit. No root ScrollView: a fixed top Command Deck over
// a three-column body (Capture Rail · Stage · Take Shelf). The Stage is the main
// object — it shows the take before, during, and after capture, and carries
// playback + toggleable transcript subtitles for verification.

enum StageMode { case capture, review }

struct ContentView: View {
    @ObservedObject var store: RecorderStore
    @StateObject private var transcript = TranscriptController()
    @StateObject private var displayPreview = DisplayPreviewService()
    @State private var showSources = false
    @State private var markerToast: String?
    @State private var stageMode: StageMode = .capture
    @State private var escMonitor: Any?

    var body: some View {
        ZStack {
            DTC.base.ignoresSafeArea()

            VStack(spacing: 0) {
                CommandDeck(store: store)
                HLine()
                HStack(spacing: 0) {
                    CaptureRail(store: store, showSources: $showSources)
                        .frame(width: 296)
                    VLine()
                    StageColumn(store: store, transcript: transcript, displayPreview: displayPreview,
                                stageMode: stageMode,
                                onCapture: { stageMode = .capture },
                                onNewTake: prepareNewTake)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                    VLine()
                    TakeShelf(store: store, onEnterReview: { stageMode = .review }, onNewTake: prepareNewTake)
                        .frame(width: 340)
                }
                .frame(maxHeight: .infinity)
            }
            // Pull the deck up into the hidden-titlebar zone so the traffic
            // lights sit inside the deck band instead of floating in a dead strip.
            .ignoresSafeArea(.container, edges: .top)

            if let countdown = store.countdownValue {
                CountdownOverlay(value: countdown, hides: store.autoHideBeforeRecording)
            }

            if let markerToast {
                VStack {
                    Spacer()
                    Label(markerToast, systemImage: "flag.fill")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 14).padding(.vertical, 9)
                        .background(Capsule().fill(DTC.accent))
                        .padding(.bottom, 30)
                        .transition(.move(edge: .bottom).combined(with: .opacity))
                }
            }
        }
        .preferredColorScheme(.dark)
        // Esc anywhere returns review to the capture / display map (never
        // interrupts an active recording — that stays on the explicit Stop).
        .onExitCommand {
            if stageMode == .review, !store.captureControlsActive {
                stageMode = .capture
            }
        }
        .sheet(isPresented: $showSources) { SourcesSheet(store: store, preview: displayPreview) }
        .onChange(of: store.markerCount) { oldValue, newValue in
            guard newValue > oldValue else { return }
            let at = dtcClock(store.markers.last?.videoTSeconds ?? store.elapsed)
            withAnimation(.spring(response: 0.3)) { markerToast = "Marker added at \(at) · \(newValue) total" }
        }
        .task(id: markerToast) {
            guard markerToast != nil else { return }
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            withAnimation { markerToast = nil }
        }
        .onAppear {
            transcript.reload(takeRoot: store.activeTakeURL, mediaDuration: store.playbackDuration)
            // SwiftUI key commands only fire with view focus; a local monitor keeps
            // Esc-to-capture and Delete-to-remove consistent across the window.
            escMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { event in
                let textInputFocused = keyWindowHasTextFocus()
                if handlesPlainDelete(event),
                   !showSources,
                   store.shouldRoutePlainDeleteToTake(textInputFocused: textInputFocused) {
                    let hadPendingDelete = store.pendingDeleteTake != nil
                    store.requestDeleteTargetTake()
                    if !hadPendingDelete, store.pendingDeleteTake != nil {
                        return nil
                    }
                    return event
                }
                guard event.keyCode == 53, !showSources else { return event }
                // First Esc leaves a focused text field (SwiftUI won't resign
                // it on its own); the next Esc exits review.
                if textInputFocused, let window = NSApp.keyWindow {
                    window.makeFirstResponder(nil)
                    return nil
                }
                guard stageMode == .review,
                      !store.captureControlsActive else { return event }
                stageMode = .capture
                return nil
            }
        }
        .onDisappear {
            if let escMonitor { NSEvent.removeMonitor(escMonitor) }
            escMonitor = nil
        }
        .onChange(of: store.playbackURL) { _, _ in
            transcript.reload(takeRoot: store.activeTakeURL, mediaDuration: store.playbackDuration, force: true)
        }
        .onChange(of: store.activeTakeSidecarRevision) { _, _ in
            transcript.reload(takeRoot: store.activeTakeURL, mediaDuration: store.playbackDuration, force: true)
        }
        .onChange(of: store.state) { _, newState in
            if newState == .reviewReady || newState == .packageReady {
                transcript.reload(takeRoot: store.activeTakeURL, mediaDuration: store.playbackDuration, force: true)
            }
            if newState == .reviewReady || newState == .packageReady || newState == .packageFailed {
                stageMode = .review
            }
        }
    }

    private func prepareNewTake() {
        if store.prepareNewTakeForRecording() {
            stageMode = .capture
            displayPreview.refresh(displayIDs: store.displayPreviewIDs)
        }
    }

    private func handlesPlainDelete(_ event: NSEvent) -> Bool {
        guard event.keyCode == 51 || event.keyCode == 117 else { return false }
        let blockedModifiers = event.modifierFlags.intersection([.command, .control, .option, .shift])
        return blockedModifiers.isEmpty
    }

    private func keyWindowHasTextFocus() -> Bool {
        guard let responder = NSApp.keyWindow?.firstResponder else { return false }
        return responder is NSTextView || responder is NSTextField || responder is NSSearchField
    }
}

// MARK: - Command Deck

struct CommandDeck: View {
    @ObservedObject var store: RecorderStore

    private var isLive: Bool { store.captureControlsActive }

    // `state` lags selection changes until the next preflight, while `setupTitle`
    // recomputes live from blockers — mirror that condition so the pill's color
    // always agrees with its own text.
    private var pillState: RecordingState {
        if store.captureControlsActive {
            return store.state == .paused ? .paused : .recording
        }
        if store.state == .setupNeeded || store.state == .idle || store.state == .ready {
            if store.lastStartFailureLine != nil { return .setupNeeded }
            return store.startBlockers.isEmpty ? .ready : .setupNeeded
        }
        return store.state
    }

    var body: some View {
        HStack(spacing: 12) {
            StatePill(state: pillState, title: store.setupTitle)
            TimerView(elapsed: store.elapsed, recording: store.captureIsWriting)
            VLine().frame(height: 20)
            ReadinessCluster(store: store)
            Spacer(minLength: 12)
            if isLive, store.activeTakeURL != nil {
                InfoChip(icon: "shippingbox", text: store.activeTakeDisplayName)
                    .frame(maxWidth: 180)
            }
            InfoChip(icon: "internaldrive", text: store.diskLine)
            if !isLive {
                titleField
            }
            DeckControls(store: store)
        }
        // Leading gutter clears the floating traffic lights so the deck reads
        // as one continuous title-bar band rather than content shoved under them.
        .padding(.leading, 84)
        .padding(.trailing, 16)
        .frame(height: 58)
        .background(
            LinearGradient(colors: [DTC.deck, DTC.rail], startPoint: .top, endPoint: .bottom)
        )
    }

    private var titleField: some View {
        HStack(spacing: 8) {
            Image(systemName: "textformat").font(.system(size: 11)).foregroundStyle(DTC.textTertiary)
            TextField("Take title", text: $store.recordingTitle)
                .textFieldStyle(.plain)
                .font(.system(size: 13))
                .foregroundStyle(DTC.textPrimary)
                .disabled(!store.canManageTakes)
                .onSubmit { if store.canStart { Task { await store.startRecording() } } }
        }
        .frame(width: 200)
        .padding(.horizontal, 10)
        .padding(.vertical, 7)
        .background(RoundedRectangle(cornerRadius: 7).fill(DTC.card))
        .overlay(RoundedRectangle(cornerRadius: 7).strokeBorder(DTC.stroke, lineWidth: 1))
    }
}

/// Six per-source green dots collapse into one quiet "ready" affirmation;
/// individual chips only appear for sources that actually need attention.
struct ReadinessCluster: View {
    @ObservedObject var store: RecorderStore

    private var items: [(String, CapabilityStatus)] {
        [("Screen", screenCaptureStatus),
         ("Display", store.screenSourceStatus),
         ("Mic", store.microphoneSourceStatus),
         ("Camera", store.cameraSourceStatus),
         ("Disk", store.permissions.disk),
         ("FFmpeg", store.permissions.ffmpeg)]
    }
    private var screenCaptureStatus: CapabilityStatus {
        store.selectedScreens.isEmpty ? .notRequired : store.permissions.screenCapture
    }
    private var issues: [(String, CapabilityStatus)] {
        items.filter { $0.1 != .ready && $0.1 != .notRequired }
    }

    var body: some View {
        HStack(spacing: 6) {
            if issues.isEmpty {
                HStack(spacing: 5) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(DTC.success)
                    Text("Sources ready")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(DTC.textSecondary)
                }
                .padding(.horizontal, 9)
                .padding(.vertical, 4)
                .background(Capsule().fill(DTC.success.opacity(0.10)))
                .overlay(Capsule().strokeBorder(DTC.success.opacity(0.22), lineWidth: 1))
                .help(summaryHelp)
            } else {
                ForEach(issues, id: \.0) { item in
                    ReadinessChip(label: item.0, status: item.1)
                }
            }
        }
    }

    private var summaryHelp: String {
        items.map { "\($0.0): \($0.1.label)" }.joined(separator: " · ")
    }
}

struct StatePill: View {
    let state: RecordingState
    let title: String
    var body: some View {
        HStack(spacing: 7) {
            if state == .recording {
                PulsingDot(color: tone.color, size: 8)
            } else {
                Circle().fill(tone.color).frame(width: 8, height: 8)
            }
            Text(title).font(.system(size: 13, weight: .semibold)).foregroundStyle(tone.color).lineLimit(1)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 7)
        .background(Capsule().fill(tone.color.opacity(0.14)))
        .overlay(Capsule().strokeBorder(tone.color.opacity(0.3), lineWidth: 1))
    }
    private var tone: Tone {
        switch state {
        case .ready, .reviewReady, .packageReady: .success
        case .stopped:                            .neutral
        case .recording:                          .recording
        case .paused:                             .attention
        case .countingDown, .stopping, .postprocessing: .accent
        case .setupNeeded, .packageFailed:        .attention
        case .idle:                               .neutral
        }
    }
}

struct TimerView: View {
    let elapsed: TimeInterval
    let recording: Bool
    var body: some View {
        Text(dtcClock(elapsed))
            .font(.system(size: 26, weight: .semibold, design: .monospaced))
            .monospacedDigit()
            .foregroundStyle(recording ? DTC.recording : DTC.textPrimary)
    }
}

struct DeckControls: View {
    @ObservedObject var store: RecorderStore
    var body: some View {
        HStack(spacing: 8) {
            if store.captureControlsActive {
                Button { store.togglePause() } label: {
                    Label(store.state == .paused ? "Resume" : "Pause",
                          systemImage: store.state == .paused ? "play.fill" : "pause.fill")
                }
                .buttonStyle(DTCButtonStyle(kind: store.state == .paused ? .primary : .secondary, large: true))
                .disabled(!store.canPauseOrResume)

                Button { store.markClip(source: .button) } label: {
                    Label("Marker", systemImage: "flag.fill")
                }
                .buttonStyle(DTCButtonStyle(kind: .secondary, large: true))
                .disabled(!store.canMark)
                .help("Drop a marker at the current time (⌃⌥⌘M)")

                Button { Task { await store.stopRecording() } } label: {
                    Label("Stop", systemImage: "stop.fill")
                }
                .buttonStyle(DTCButtonStyle(kind: .danger, large: true))
                .disabled(!store.canStop)
            } else {
                Button { Task { await store.startRecording() } } label: {
                    Label("Start", systemImage: "record.circle")
                }
                .buttonStyle(DTCButtonStyle(kind: .primary, large: true))
                .disabled(!store.canStart)
            }
        }
    }
}

// MARK: - Capture Rail

struct CaptureRail: View {
    @ObservedObject var store: RecorderStore
    @Binding var showSources: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            SectionLabel("Sources")
            SourceHealthCard(store: store)

            if !store.startBlockers.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Label("Setup needed", systemImage: "exclamationmark.triangle.fill")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(DTC.attention)
                    Text(store.startBlockers.joined(separator: " · "))
                        .font(.system(size: 11))
                        .foregroundStyle(DTC.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                    if store.needsScreenCapturePermission {
                        Text(store.screenCaptureGateLine)
                            .font(.system(size: 10))
                            .foregroundStyle(DTC.textTertiary)
                            .fixedSize(horizontal: false, vertical: true)
                        ScreenPermissionActions(store: store)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .dtcCard(DTC.attention.opacity(0.10), padding: 12, stroke: DTC.attention.opacity(0.3))
            }

            Spacer()

            VStack(spacing: 8) {
                Button { showSources = true } label: {
                    Label("Configure Sources", systemImage: "slider.horizontal.3").frame(maxWidth: .infinity)
                }
                .buttonStyle(DTCButtonStyle(kind: .secondary))
                HStack(spacing: 8) {
                    Button { store.useSimpleDefaults() } label: {
                        Label("Main display + mic", systemImage: "wand.and.stars").frame(maxWidth: .infinity)
                    }
                    .buttonStyle(DTCButtonStyle(kind: .ghost))
                    .help("Select your primary display and default microphone")
                    Button { Task { await store.reloadSetup() } } label: {
                        Label("Reload", systemImage: "arrow.clockwise").frame(maxWidth: .infinity)
                    }
                    .buttonStyle(DTCButtonStyle(kind: .ghost))
                    .help("Re-enumerate displays, microphones, and cameras")
                }
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(DTC.rail)
    }
}

struct ScreenPermissionActions: View {
    @ObservedObject var store: RecorderStore

    var body: some View {
        HStack(spacing: 8) {
            Button { Task { await store.requestScreenRecordingPermission() } } label: {
                Label("Request", systemImage: "record.circle")
            }
            Button { store.openScreenRecordingSettings() } label: {
                Label("Settings", systemImage: "gearshape")
            }
            Button { Task { await store.recheckScreenRecordingPermission() } } label: {
                Label("Recheck", systemImage: "arrow.clockwise")
            }
        }
        .font(.system(size: 10, weight: .semibold))
        .buttonStyle(DTCButtonStyle(kind: .ghost))
    }
}

struct SourceHealthCard: View {
    @ObservedObject var store: RecorderStore
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 10) {
                    Image(systemName: "mic").font(.system(size: 13)).foregroundStyle(DTC.textSecondary).frame(width: 18)
                    VStack(alignment: .leading, spacing: 1) {
                        Text("Microphone").font(.system(size: 10, weight: .medium)).foregroundStyle(DTC.textTertiary)
                        Text(store.selectedAudio?.name ?? "None").font(.system(size: 12, weight: .semibold)).foregroundStyle(DTC.textPrimary).lineLimit(1)
                    }
                    Spacer()
                    Circle().fill(capabilityColor(store.microphoneSourceStatus)).frame(width: 7, height: 7)
                }
                LevelMeter(level: store.microphoneLevel)
                HStack {
                    Text("Live input level").font(.system(size: 9)).foregroundStyle(DTC.textTertiary)
                    Spacer()
                    Button { store.refreshMicrophoneMonitor() } label: {
                        Text("Mic check").font(.system(size: 10, weight: .semibold))
                    }
                    .buttonStyle(.plain).foregroundStyle(DTC.accent)
                    .disabled(store.selectedAudioID == nil)
                    .help("Restart live microphone level feedback")
                }
            }
            HLine()
            healthRow(icon: "camera", title: "Camera",
                      value: store.webcamEnabled ? (store.selectedWebcam?.name ?? "On") : "Off",
                      status: store.cameraSourceStatus)
            if store.captureIsWriting, store.webcamEnabled {
                Text(store.cameraCaptureStatusLine)
                    .font(.system(size: 10))
                    .foregroundStyle(DTC.textTertiary)
                    .lineLimit(2)
            }
            HLine()
            healthRow(icon: "rectangle.3.group", title: "Displays", value: displaySummary, status: store.screenSourceStatus)
            HLine()
            HStack {
                Label("Frames every \(store.screenshotInterval)s", systemImage: "timer")
                    .font(.system(size: 11)).foregroundStyle(DTC.textSecondary)
                Spacer()
                if store.autoHideBeforeRecording { InfoChip(icon: "eye.slash", text: "Auto-hide") }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .dtcCard()
    }
    private var displaySummary: String {
        let total = store.devices.videoDevices.filter(\.isScreen).count
        return "\(store.selectedScreens.count) of \(total) selected"
    }
    @ViewBuilder private func healthRow(icon: String, title: String, value: String, status: CapabilityStatus) -> some View {
        HStack(spacing: 10) {
            Image(systemName: icon).font(.system(size: 13)).foregroundStyle(DTC.textSecondary).frame(width: 18)
            VStack(alignment: .leading, spacing: 1) {
                Text(title).font(.system(size: 10, weight: .medium)).foregroundStyle(DTC.textTertiary)
                Text(value).font(.system(size: 12, weight: .semibold)).foregroundStyle(DTC.textPrimary).lineLimit(1)
            }
            Spacer()
            Circle().fill(capabilityColor(status)).frame(width: 7, height: 7)
        }
    }
}

struct CaptureTargetCard: View {
    @ObservedObject var store: RecorderStore
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            targetRow(icon: "display", title: "Display", value: displayValue, status: store.screenSourceStatus)
            HLine()
            VStack(alignment: .leading, spacing: 6) {
                targetRow(icon: "mic", title: "Microphone", value: store.selectedAudio?.name ?? "None", status: store.microphoneSourceStatus)
                LevelMeter(level: store.microphoneLevel)
            }
            HLine()
            targetRow(icon: "camera", title: "Camera",
                      value: store.webcamEnabled ? (store.selectedWebcam?.name ?? "On") : "Off",
                      status: store.cameraSourceStatus)
            if store.captureIsWriting, store.webcamEnabled {
                Text(store.cameraCaptureStatusLine)
                    .font(.system(size: 10))
                    .foregroundStyle(DTC.textTertiary)
                    .lineLimit(2)
            }
            HLine()
            HStack {
                Label("Frames every \(store.screenshotInterval)s", systemImage: "timer")
                    .font(.system(size: 11)).foregroundStyle(DTC.textSecondary)
                Spacer()
                if store.autoHideBeforeRecording {
                    InfoChip(icon: "eye.slash", text: "Auto-hide")
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .dtcCard()
    }

    private var displayValue: String {
        if store.selectedScreens.isEmpty { return "None selected" }
        if store.selectedScreens.count == 1 { return store.selectedScreens[0].name }
        return "\(store.selectedScreens.count) displays"
    }

    @ViewBuilder private func targetRow(icon: String, title: String, value: String, status: CapabilityStatus) -> some View {
        HStack(spacing: 10) {
            Image(systemName: icon).font(.system(size: 13)).foregroundStyle(DTC.textSecondary).frame(width: 18)
            VStack(alignment: .leading, spacing: 1) {
                Text(title).font(.system(size: 10, weight: .medium)).foregroundStyle(DTC.textTertiary)
                Text(value).font(.system(size: 12, weight: .semibold)).foregroundStyle(DTC.textPrimary).lineLimit(1)
            }
            Spacer()
            Circle().fill(capabilityColor(status)).frame(width: 7, height: 7)
        }
    }
}

struct RunCueCard: View {
    @ObservedObject var store: RecorderStore
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Label("Run map", systemImage: "map").font(.system(size: 11, weight: .semibold)).foregroundStyle(DTC.textSecondary)
                Spacer()
                if let s = store.scheduleState {
                    Text(s.progressLabel).font(.system(size: 10)).foregroundStyle(DTC.textTertiary)
                }
            }
            if let s = store.scheduleState {
                Text(s.currentTitle ?? s.currentStepID ?? "Waiting for route")
                    .font(.system(size: 12, weight: .semibold)).foregroundStyle(DTC.textPrimary).lineLimit(2)
                if let next = s.nextTitle ?? s.nextStepID {
                    Text("Next · \(next)").font(.system(size: 11)).foregroundStyle(DTC.textTertiary).lineLimit(1)
                }
            }
            if store.markerCount > 0 {
                InfoChip(icon: "flag.fill", text: "\(store.markerCount) marker\(store.markerCount == 1 ? "" : "s")", tone: .accent)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .dtcCard(DTC.card, padding: 12)
    }
}

// MARK: - Stage column

struct StageColumn: View {
    @ObservedObject var store: RecorderStore
    @ObservedObject var transcript: TranscriptController
    @ObservedObject var displayPreview: DisplayPreviewService
    var stageMode: StageMode
    var onCapture: () -> Void
    var onNewTake: () -> Void
    var body: some View {
        VStack(spacing: 12) {
            StageArea(store: store, transcript: transcript, displayPreview: displayPreview,
                      stageMode: stageMode, onCapture: onCapture, onNewTake: onNewTake)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            ConfidenceStrip(store: store, transcript: transcript)
        }
        .padding(16)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(DTC.base)
    }
}

struct StageArea: View {
    @ObservedObject var store: RecorderStore
    @ObservedObject var transcript: TranscriptController
    @ObservedObject var displayPreview: DisplayPreviewService
    var stageMode: StageMode
    var onCapture: () -> Void
    var onNewTake: () -> Void
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 14, style: .continuous).fill(DTC.stage)
            StageBackdrop().clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
            RoundedRectangle(cornerRadius: 14, style: .continuous).strokeBorder(DTC.stroke, lineWidth: 1)
            content
        }
    }
    @ViewBuilder private var content: some View {
        if store.captureControlsActive {
            RecordingStage(store: store)
        } else if (store.state == .stopping || store.state == .postprocessing) && !store.activeTakeReviewIsReady {
            FinalizingStage(store: store, transcript: transcript)
        } else if stageMode == .review, store.playbackPlayer != nil {
            ReviewStage(store: store, transcript: transcript, onCapture: onCapture, onNewTake: onNewTake)
        } else {
            PreflightStage(store: store, preview: displayPreview)
        }
    }
}

struct PreflightStage: View {
    @ObservedObject var store: RecorderStore
    @ObservedObject var preview: DisplayPreviewService
    var body: some View {
        VStack(spacing: 14) {
            DisplayArrangementMap(store: store, preview: preview)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            CaptureDock(store: store)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(18)
    }
}

/// One docked card that answers "what happens if I press Start?" — selected
/// display, mic, camera, and the Start action live together instead of
/// floating as separate text lines over the stage.
struct CaptureDock: View {
    @ObservedObject var store: RecorderStore

    var body: some View {
        VStack(spacing: 12) {
            HStack(spacing: 18) {
                dockItem(icon: "display", title: "Display", value: displayValue,
                         status: store.screenSourceStatus)
                VLine().frame(height: 26)
                dockItem(icon: "mic", title: "Microphone", value: store.selectedAudio?.name ?? "None",
                         status: store.microphoneSourceStatus)
                VLine().frame(height: 26)
                dockItem(icon: "camera", title: "Camera",
                         value: store.webcamEnabled ? (store.selectedWebcam?.name ?? "On") : "Off",
                         status: store.cameraSourceStatus)
            }

            if let line = store.lastStartFailureLine {
                Label(line, systemImage: "exclamationmark.triangle.fill")
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(DTC.attention)
                    .multilineTextAlignment(.center)
            }

            if store.canStart {
                Button { Task { await store.startRecording() } } label: {
                    Label("Start recording", systemImage: "record.circle").frame(minWidth: 200)
                }
                .buttonStyle(DTCButtonStyle(kind: .primary, large: true))
            } else if !store.startBlockers.isEmpty {
                VStack(spacing: 8) {
                    Label(store.startBlockers.joined(separator: " · "), systemImage: "exclamationmark.triangle.fill")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(DTC.attention)
                        .multilineTextAlignment(.center)
                    if store.needsScreenCapturePermission {
                        Text(store.screenCaptureGateLine)
                            .font(.system(size: 11))
                            .foregroundStyle(DTC.textSecondary)
                            .multilineTextAlignment(.center)
                        ScreenPermissionActions(store: store)
                    }
                }
            }
        }
        .padding(.horizontal, 22)
        .padding(.vertical, 16)
        .frame(maxWidth: 620)
        .background(RoundedRectangle(cornerRadius: 12, style: .continuous).fill(DTC.deck))
        .overlay(RoundedRectangle(cornerRadius: 12, style: .continuous).strokeBorder(DTC.stroke, lineWidth: 1))
    }

    private var displayValue: String {
        let screens = store.selectedScreens
        if screens.isEmpty { return "None selected" }
        if screens.count == 1 { return screens[0].name }
        return "\(screens.count) displays"
    }

    private func dockItem(icon: String, title: String, value: String, status: CapabilityStatus) -> some View {
        let ok = status == .ready || status == .notRequired
        return HStack(spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 13))
                .foregroundStyle(ok ? DTC.textSecondary : DTC.attention)
                .frame(width: 18)
            VStack(alignment: .leading, spacing: 1) {
                Text(title.uppercased())
                    .font(.system(size: 9, weight: .semibold)).tracking(0.6)
                    .foregroundStyle(DTC.textTertiary)
                Text(value)
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(ok ? DTC.textPrimary : DTC.attention)
                    .lineLimit(1)
            }
        }
        .frame(maxWidth: 170, alignment: .leading)
    }
}

struct RecordingStage: View {
    @ObservedObject var store: RecorderStore
    var body: some View {
        VStack(spacing: 16) {
            Spacer()
            HStack(spacing: 10) {
                PulsingDot(color: store.state == .paused ? DTC.attention : DTC.recording, size: 11)
                Text(store.state == .paused ? "PAUSED" : "RECORDING")
                    .font(.system(size: 14, weight: .bold)).tracking(2)
                    .foregroundStyle(store.state == .paused ? DTC.attention : DTC.recording)
            }
            Text(dtcClock(store.elapsed))
                .font(.system(size: 66, weight: .bold, design: .monospaced)).monospacedDigit()
                .foregroundStyle(DTC.textPrimary)
            if store.state == .paused {
                Text("Capture paused — Resume continues this same take.")
                    .font(.system(size: 12, weight: .medium)).foregroundStyle(DTC.attention)
            }
            HStack(spacing: 10) {
                Image(systemName: "mic.fill").foregroundStyle(DTC.textSecondary)
                LevelMeter(level: store.microphoneLevel).frame(width: 240)
            }
            HStack(spacing: 10) {
                trackChip("Screen", on: !store.selectedScreens.isEmpty)
                trackChip("Mic", on: store.selectedAudio != nil)
                trackChip("Camera", on: store.webcamEnabled)
            }
            if store.markerCount > 0 {
                Text(markerLine).font(.system(size: 11)).foregroundStyle(DTC.textTertiary)
            }
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(24)
    }
    private var markerLine: String {
        let count = "\(store.markerCount) marker\(store.markerCount == 1 ? "" : "s")"
        if let last = store.markers.last {
            return count + String(format: " · latest %@ at %@", last.source.label, dtcClock(last.videoTSeconds))
        }
        return count
    }
    private func trackChip(_ label: String, on: Bool) -> some View {
        HStack(spacing: 5) {
            Image(systemName: on ? "checkmark.circle.fill" : "minus.circle").font(.system(size: 11))
            Text(label).font(.system(size: 11, weight: .medium))
        }
        .foregroundStyle(on ? DTC.success : DTC.textTertiary)
        .padding(.horizontal, 9).padding(.vertical, 5)
        .background(Capsule().fill(on ? DTC.success.opacity(0.12) : Color.white.opacity(0.04)))
    }
}

struct FinalizingStage: View {
    @ObservedObject var store: RecorderStore
    @ObservedObject var transcript: TranscriptController

    private enum Step { case done, active, idle }

    var body: some View {
        VStack(spacing: 18) {
            Text(store.state == .stopping ? "Stopping capture" : "Building package")
                .font(.system(size: 16, weight: .semibold)).foregroundStyle(DTC.textPrimary)
            VStack(alignment: .leading, spacing: 16) {
                lane(title: "Media", rows: [
                    ("Tracks saved", .done),
                    store.activeTakeReviewIsReady
                        ? (store.activeTakeReviewStatusLine, .done)
                        : (store.activeTakeReviewStatusLine, .active)
                ])
                lane(title: "Package", rows: [packageRow])
                lane(title: "Transcript", rows: [transcriptRow])
            }
            .frame(width: 320)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(24)
    }

    private var transcriptRow: (String, Step) {
        if case .ready = transcript.status { return ("Transcript ready · \(transcript.cueCount) cues", .done) }
        if store.activeTakePostprocessStage == "transcribe" && store.activeTakePostprocessStatus == "running" {
            return ("Transcribing audio...", .active)
        }
        if store.activeTakePostprocessIsActive { return ("Transcript pending", .idle) }
        return ("Transcript pending", .idle)
    }

    private var packageRow: (String, Step) {
        if store.activeTakePostprocessIsComplete { return ("Package sidecars ready", .done) }
        if store.activeTakePostprocessIsActive { return (store.activeTakePostprocessStatusLine, .active) }
        return (store.activeTakePostprocessStatusLine, .idle)
    }

    @ViewBuilder private func lane(title: String, rows: [(String, Step)]) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            Text(title.uppercased()).font(.system(size: 10, weight: .semibold)).tracking(0.6).foregroundStyle(DTC.textTertiary)
            ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
                HStack(spacing: 9) {
                    stepIcon(row.1)
                    Text(row.0).font(.system(size: 12)).foregroundStyle(row.1 == .idle ? DTC.textTertiary : DTC.textSecondary)
                    Spacer()
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .dtcCard(DTC.card, padding: 12)
    }

    @ViewBuilder private func stepIcon(_ step: Step) -> some View {
        switch step {
        case .done:   Image(systemName: "checkmark.circle.fill").foregroundStyle(DTC.success).font(.system(size: 13))
        case .active: ProgressView().controlSize(.small).scaleEffect(0.7).frame(width: 16, height: 16)
        case .idle:   Image(systemName: "circle").foregroundStyle(DTC.textTertiary).font(.system(size: 13))
        }
    }
}

// MARK: - Review stage (player + subtitles + sync rail)

struct ReviewStage: View {
    @ObservedObject var store: RecorderStore
    @ObservedObject var transcript: TranscriptController
    @StateObject private var atlas = ObservationAtlasController()
    @State private var cameraPIPOffset: CGSize = .zero
    @State private var cameraPIPScale: CGFloat = 1
    var onCapture: () -> Void = {}
    var onNewTake: () -> Void = {}

    var body: some View {
        VStack(spacing: 10) {
            HStack(spacing: 8) {
                Button { onCapture() } label: { Label("Capture", systemImage: "chevron.backward") }
                    .buttonStyle(DTCButtonStyle(kind: .ghost))
                    .keyboardShortcut(.escape, modifiers: [])
                    .help("Back to the capture / display map (Esc)")
                Text("Reviewing \(store.activeTakeDisplayName)")
                    .font(.system(size: 11, weight: .medium)).foregroundStyle(DTC.textSecondary).lineLimit(1)
                Spacer()
                Button { onNewTake() } label: {
                    Label("New", systemImage: "plus")
                }
                .buttonStyle(DTCButtonStyle(kind: .secondary))
                .keyboardShortcut("n", modifiers: [.command])
                .disabled(!store.canManageTakes)
                .help("Clear the selected review take and return to display selection for a new recording")
            }
            ZStack {
                if store.playbackIsVideo, let player = store.playbackPlayer {
                    PlaybackVideoSurfaceView(player: player)
                } else {
                    audioPlaceholder
                }
                if store.playbackIsVideo,
                   let cameraPlayer = store.playbackCameraPlayer {
                    CameraPIPOverlay(
                        player: cameraPlayer,
                        title: store.playbackCameraTitle,
                        offset: $cameraPIPOffset,
                        scale: $cameraPIPScale,
                        bottomInset: 54,
                        onLayoutCommit: { offset, scale in
                            store.updatePlaybackCameraOverlayLayout(offset: offset, scale: scale)
                        }
                    )
                }
                PlaybackSurfaceScrubberOverlay(store: store)
                PlaybackSurfaceControlOverlay(store: store)
                if transcript.subtitlesEnabled,
                   let cue = transcript.activeCue(at: store.playbackPosition + transcript.offset) {
                    VStack {
                        Spacer()
                        SubtitleCaption(text: cue.text, large: transcript.largeCaptions).padding(.bottom, 68)
                    }
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Color.black)
            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous).strokeBorder(DTC.stroke, lineWidth: 1))

            TransportBar(store: store, transcript: transcript)
                .fixedSize(horizontal: false, vertical: true)

            ReviewInspectionRail(store: store, transcript: transcript, atlas: atlas)
                .frame(height: 198)
                .clipped()
        }
        .padding(12)
        .onAppear {
            applyCameraPIPLayout(store.playbackCameraOverlayLayout)
            atlas.reload(takeRoot: store.activeTakeURL)
        }
        .onChange(of: store.activeTakeURL) { _, takeRoot in
            atlas.reload(takeRoot: takeRoot, force: true)
        }
        .onChange(of: store.playbackCameraURL) { _, _ in
            applyCameraPIPLayout(store.playbackCameraOverlayLayout)
        }
        .onChange(of: store.playbackCameraOverlayLayout) { _, layout in
            applyCameraPIPLayout(layout)
        }
        .onChange(of: store.state) { _, newState in
            if newState == .reviewReady || newState == .packageReady || newState == .packageFailed {
                atlas.reload(takeRoot: store.activeTakeURL, force: true)
            }
        }
        .onChange(of: store.activeTakeSidecarRevision) { _, _ in
            atlas.reload(takeRoot: store.activeTakeURL, force: true)
        }
    }

    private var audioPlaceholder: some View {
        VStack(spacing: 10) {
            Image(systemName: "waveform").font(.system(size: 40)).foregroundStyle(DTC.textSecondary)
            Text(store.playbackTitle).font(.system(size: 13, weight: .semibold)).foregroundStyle(DTC.textPrimary)
            Text(store.playbackURL?.lastPathComponent ?? "").font(.system(size: 11)).foregroundStyle(DTC.textTertiary).lineLimit(1)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func applyCameraPIPLayout(_ layout: CameraPIPLayout) {
        cameraPIPOffset = layout.offset
        cameraPIPScale = layout.cgScale
    }
}

struct PlaybackSurfaceControlOverlay: View {
    @ObservedObject var store: RecorderStore

    var body: some View {
        if store.playbackPlayer != nil {
            VStack {
                Spacer()
                HStack {
                    Spacer()
                    Button {
                        store.togglePlayback()
                    } label: {
                        Image(systemName: store.playbackIsPlaying ? "pause.fill" : "play.fill")
                            .font(.system(size: 22, weight: .bold))
                            .foregroundStyle(.white)
                            .frame(width: 58, height: 58)
                            .background(Circle().fill(DTC.accent.opacity(0.88)))
                            .overlay(Circle().strokeBorder(.white.opacity(0.22), lineWidth: 1))
                            .shadow(color: .black.opacity(0.48), radius: 12, y: 5)
                    }
                    .buttonStyle(.plain)
                    .opacity(store.playbackIsPlaying ? 0.52 : 1)
                    .keyboardShortcut(.space, modifiers: [])
                    .help(store.playbackIsPlaying ? "Pause review playback" : "Play review playback")
                    .accessibilityLabel(store.playbackIsPlaying ? "Pause review playback" : "Play review playback")
                    Spacer()
                }
                Spacer()
            }
        }
    }
}

struct PlaybackSurfaceScrubberOverlay: View {
    @ObservedObject var store: RecorderStore

    var body: some View {
        if store.playbackPlayer != nil {
            VStack {
                Spacer()
                HStack(spacing: 9) {
                    Text(dtcClock(store.playbackPosition))
                        .font(.system(size: 10, design: .monospaced))
                        .monospacedDigit()
                        .foregroundStyle(.white.opacity(0.82))
                        .frame(width: 46, alignment: .leading)
                    Slider(
                        value: Binding(
                            get: { store.playbackPosition },
                            set: { store.seekPlayback(to: $0) }
                        ),
                        in: 0...max(store.playbackDuration, 1)
                    )
                    .controlSize(.small)
                    .tint(DTC.accent)
                    Text(dtcClock(store.playbackDuration))
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(.white.opacity(0.72))
                        .monospacedDigit()
                        .frame(width: 46, alignment: .trailing)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(
                    LinearGradient(
                        colors: [.black.opacity(0.76), .black.opacity(0.46), .clear],
                        startPoint: .bottom,
                        endPoint: .top
                    )
                )
            }
        }
    }
}

struct SubtitleCaption: View {
    let text: String
    var large: Bool
    var body: some View {
        Text(text)
            .font(.system(size: large ? 22 : 16, weight: .semibold))
            .foregroundStyle(.white)
            .multilineTextAlignment(.center)
            .lineLimit(2)
            .padding(.horizontal, 14).padding(.vertical, 8)
            .background(RoundedRectangle(cornerRadius: 8).fill(Color.black.opacity(0.62)))
            .padding(.horizontal, 24)
            .shadow(radius: 6)
    }
}

struct TransportBar: View {
    @ObservedObject var store: RecorderStore
    @ObservedObject var transcript: TranscriptController
    var body: some View {
        HStack(spacing: 8) {
            iconButton("backward.end.fill", help: "From start") { store.playFromStart() }
            iconButton("gobackward.10", help: "Back 10s") { store.skipPlayback(by: -10) }
            Button { store.togglePlayback() } label: {
                Image(systemName: store.playbackIsPlaying ? "pause.fill" : "play.fill")
                    .font(.system(size: 13, weight: .bold)).frame(width: 28)
            }
            .buttonStyle(DTCButtonStyle(kind: .primary))
            iconButton("goforward.10", help: "Forward 10s") { store.skipPlayback(by: 10) }

            Button { transcript.subtitlesEnabled.toggle() } label: {
                Label("Subtitles", systemImage: transcript.subtitlesEnabled ? "captions.bubble.fill" : "captions.bubble")
            }
            .buttonStyle(DTCButtonStyle(kind: transcript.subtitlesEnabled ? .secondary : .ghost))
            .help("Toggle transcript subtitles over the video")

            if transcript.subtitlesEnabled {
                Button { transcript.largeCaptions.toggle() } label: {
                    Image(systemName: "textformat.size").font(.system(size: 12)).frame(width: 22)
                }
                .buttonStyle(DTCButtonStyle(kind: .ghost))
                .help("Larger captions")
            }

            Spacer()

            Button { store.openPlaybackAsset() } label: {
                Label("Open", systemImage: "arrow.up.right.square")
            }
            .buttonStyle(DTCButtonStyle(kind: .ghost))
            .disabled(!store.canRevealPlaybackAsset)
        }
    }
    private func iconButton(_ name: String, help: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: name).font(.system(size: 12)).frame(width: 22)
        }
        .buttonStyle(DTCButtonStyle(kind: .secondary))
        .help(help)
    }
}

struct TranscriptSyncRail: View {
    @ObservedObject var store: RecorderStore
    @ObservedObject var transcript: TranscriptController

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                Text("TRANSCRIPT").font(.system(size: 10, weight: .semibold)).tracking(0.8).foregroundStyle(DTC.textTertiary)
                Text(transcript.coverageLine).font(.system(size: 10)).foregroundStyle(DTC.textTertiary)
                Spacer()
                offsetControls
            }
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 3) {
                        ForEach(transcript.cues) { cue in
                            cueRow(cue)
                        }
                    }
                    .padding(.vertical, 2)
                }
                .onChange(of: activeCueID) { _, id in
                    if let id { withAnimation(.easeInOut(duration: 0.2)) { proxy.scrollTo(id, anchor: .center) } }
                }
            }
        }
        .dtcCard(DTC.card, padding: 10)
    }

    private var activeCueID: String? {
        transcript.activeCue(at: store.playbackPosition + transcript.offset)?.id
    }

    @ViewBuilder private func cueRow(_ cue: TranscriptCue) -> some View {
        let active = transcript.isActive(cue, at: store.playbackPosition + transcript.offset)
        Button { store.seekPlayback(to: cue.start) } label: {
            HStack(alignment: .top, spacing: 8) {
                Text(dtcCueTime(cue.start))
                    .font(.system(size: 10, design: .monospaced)).monospacedDigit()
                    .foregroundStyle(active ? DTC.accent : DTC.textTertiary)
                    .frame(width: 52, alignment: .leading)
                Text(cue.text)
                    .font(.system(size: 12))
                    .foregroundStyle(active ? DTC.textPrimary : DTC.textSecondary)
                    .multilineTextAlignment(.leading)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding(.horizontal, 8).padding(.vertical, 5)
            .background(RoundedRectangle(cornerRadius: 6).fill(active ? DTC.accent.opacity(0.14) : Color.clear))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .id(cue.id)
    }

    private var offsetControls: some View {
        HStack(spacing: 4) {
            Text(String(format: "offset %+.1fs", transcript.offset))
                .font(.system(size: 10, design: .monospaced)).foregroundStyle(DTC.textTertiary)
            stepButton("minus") { transcript.offset -= 0.1 }
            stepButton("plus") { transcript.offset += 0.1 }
            Button { transcript.offset = 0 } label: {
                Text("Reset").font(.system(size: 10))
            }
            .buttonStyle(.plain).foregroundStyle(DTC.textSecondary)
        }
        .help("Nudge subtitle timing for visual alignment (session-only, never written to the package)")
    }

    private func stepButton(_ icon: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: icon).font(.system(size: 9, weight: .bold)).frame(width: 18, height: 16)
        }
        .buttonStyle(.plain)
        .foregroundStyle(DTC.textSecondary)
        .background(RoundedRectangle(cornerRadius: 4).fill(DTC.cardHi))
    }
}

struct TranscriptMissingBar: View {
    @ObservedObject var store: RecorderStore
    @ObservedObject var transcript: TranscriptController
    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: icon).foregroundStyle(tone.color).font(.system(size: 15))
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.system(size: 12, weight: .semibold)).foregroundStyle(DTC.textPrimary)
                Text(subtitle).font(.system(size: 11)).foregroundStyle(DTC.textSecondary).lineLimit(2)
            }
            Spacer()
            if store.canBuildPackage {
                Button { Task { await store.buildPackageSidecars() } } label: {
                    Label("Build Package", systemImage: "shippingbox")
                }
                .buttonStyle(DTCButtonStyle(kind: .secondary))
            }
        }
        .frame(height: 64)
        .dtcCard(tone.color.opacity(0.08), padding: 12, stroke: tone.color.opacity(0.25))
    }
    private var tone: Tone {
        switch transcript.status {
        case .failed: .danger
        default:      .attention
        }
    }
    private var icon: String {
        switch transcript.status {
        case .failed:       "xmark.octagon.fill"
        case .unavailable:  "exclamationmark.bubble.fill"
        default:            "text.bubble"
        }
    }
    private var title: String {
        switch transcript.status {
        case .failed:       "Transcript failed"
        case .unavailable:  "Transcript unavailable"
        default:            "Transcript not built yet"
        }
    }
    private var subtitle: String {
        switch transcript.status {
        case .failed(let r):       r
        case .unavailable(let r):  r
        default:
            store.activeTakeNeedsReviewPreparation
                ? "Build the package to prepare review media, transcript, and sidecars."
                : "Build the package to transcribe this take and verify subtitle alignment."
        }
    }
}

struct ConfidenceStrip: View {
    @ObservedObject var store: RecorderStore
    @ObservedObject var transcript: TranscriptController
    var body: some View {
        let transcriptDisplay = transcriptConfidenceDisplay(
            status: transcript.status,
            cueCount: transcript.cueCount,
            packageBuildActive: store.state == .postprocessing || store.activeTakeIsBuildingPackage
        )
        HStack(spacing: 16) {
            chip("Media", mediaText, mediaTone, "film")
            chip("Transcript", transcriptDisplay.text, transcriptDisplay.tone, "captions.bubble")
            chip("Export", exportText, exportTone, "square.and.arrow.up")
            chip("Package", packageText, packageTone, "shippingbox")
            Spacer()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 14).padding(.vertical, 9)
        .background(RoundedRectangle(cornerRadius: 10).fill(DTC.rail))
        .overlay(RoundedRectangle(cornerRadius: 10).strokeBorder(DTC.stroke, lineWidth: 1))
    }
    private func chip(_ label: String, _ value: String, _ tone: Tone, _ icon: String) -> some View {
        HStack(spacing: 6) {
            Image(systemName: icon).font(.system(size: 11)).foregroundStyle(tone.color)
            Text(label).font(.system(size: 10, weight: .semibold)).foregroundStyle(DTC.textTertiary)
            Text(value).font(.system(size: 11, weight: .medium)).foregroundStyle(DTC.textSecondary).lineLimit(1)
        }
    }
    private var mediaText: String { store.activeTakeReviewIsReady ? "ready" : "—" }
    private var mediaTone: Tone { store.activeTakeReviewIsReady ? .success : .neutral }
    private var exportText: String { store.canOpenActiveTakeExport ? "ready" : "not built" }
    private var exportTone: Tone { store.canOpenActiveTakeExport ? .success : .neutral }
    private var packageText: String {
        if store.activeTakeIsFinalizing { return "preparing review" }
        if store.activeTakeIsBuildingPackage { return store.activeTakePostprocessShortLabel }
        if store.activeTakeNeedsReviewPreparation { return "build package" }
        return switch store.state {
        case .packageReady: "ready"
        case .postprocessing: "building…"
        case .packageFailed: "failed"
        default: "pending"
        }
    }
    private var packageTone: Tone {
        if store.activeTakeIsFinalizing || store.activeTakeIsBuildingPackage { return .accent }
        return switch store.state {
        case .packageReady: .success
        case .postprocessing: .accent
        case .packageFailed: .danger
        default: .neutral
        }
    }
}

struct TranscriptConfidenceDisplay {
    let text: String
    let tone: Tone
}

func transcriptConfidenceDisplay(
    status: TranscriptStatus,
    cueCount: Int,
    packageBuildActive: Bool
) -> TranscriptConfidenceDisplay {
    switch status {
    case .ready:
        return TranscriptConfidenceDisplay(text: "\(cueCount) cues", tone: .success)
    case .unavailable:
        return TranscriptConfidenceDisplay(text: "unavailable", tone: .attention)
    case .failed:
        return TranscriptConfidenceDisplay(text: "failed", tone: .danger)
    case .missing, .notChecked:
        return packageBuildActive
            ? TranscriptConfidenceDisplay(text: "building…", tone: .accent)
            : TranscriptConfidenceDisplay(text: "not built", tone: .neutral)
    }
}

// MARK: - Take Shelf

struct TakeShelf: View {
    @ObservedObject var store: RecorderStore
    var onEnterReview: () -> Void = {}
    var onNewTake: () -> Void = {}
    @State private var confirmDiscard = false
    @State private var dropTargeted = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                SectionLabel("Current take")
                Spacer()
                if store.activeTakeURL != nil {
                    Button { onNewTake() } label: {
                        Label("New", systemImage: "plus")
                    }
                    .buttonStyle(DTCButtonStyle(kind: .secondary))
                    .disabled(!store.canManageTakes)
                    .help("Return to source selection for a new recording")
                }
            }
            CurrentTakeCard(store: store)
            PackageActionBar(store: store, confirmDiscard: $confirmDiscard)
            HLine()
            HStack {
                SectionLabel("Recent takes")
                Spacer()
                Button { store.refreshTakeHistory() } label: {
                    Image(systemName: "arrow.clockwise").font(.system(size: 11))
                }
                .buttonStyle(.plain).foregroundStyle(DTC.textSecondary)
                .help("Refresh take history")
            }
            RecentTakesList(store: store, onEnterReview: onEnterReview) { store.requestDeleteTake($0.url) }
                .frame(maxHeight: .infinity)
            ImportStrip(store: store, dropTargeted: $dropTargeted)
        }
        .padding(16)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .background(DTC.rail)
        .confirmationDialog("Discard this take and reset?", isPresented: $confirmDiscard, titleVisibility: .visible) {
            Button("Discard Take", role: .destructive) { store.discardTakeAndReset() }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This removes the current take folder and returns the recorder to a fresh ready state.")
        }
        .onDeleteCommand { store.requestDeleteTargetTake() }
        .confirmationDialog("Delete selected take?",
                            isPresented: Binding(get: { store.pendingDeleteTake != nil }, set: { if !$0 { store.pendingDeleteTake = nil } }),
                            titleVisibility: .visible) {
            if let pending = store.pendingDeleteTake {
                Button("Delete \(pending.name)", role: .destructive) {
                    store.confirmPendingDeleteTake()
                }
            }
            Button("Cancel", role: .cancel) { store.pendingDeleteTake = nil }
        } message: {
            Text("This removes the take folder from disk. It cannot be undone.")
        }
    }
}

struct CurrentTakeCard: View {
    @ObservedObject var store: RecorderStore
    var body: some View {
        Group {
            if store.activeTakeURL != nil {
                VStack(alignment: .leading, spacing: 8) {
                    HStack(spacing: 8) {
                        TextField("Take title", text: $store.takeTitleDraft)
                            .textFieldStyle(.plain)
                            .font(.system(size: 13, weight: .semibold))
                            .foregroundStyle(DTC.textPrimary)
                            .disabled(!store.canManageTakes)
                            .onSubmit { Task { await store.saveActiveTakeTitle() } }
                        Button { Task { await store.saveActiveTakeTitle() } } label: {
                            Image(systemName: "checkmark").font(.system(size: 11))
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(store.canRenameActiveTake ? DTC.accent : DTC.textTertiary)
                        .disabled(!store.canRenameActiveTake)
                    }
                    Text(store.activeTakeStorageLine).font(.system(size: 10)).foregroundStyle(DTC.textTertiary).lineLimit(1)
                    if let backgroundLine = store.activeTakeBackgroundLine {
                        Text(backgroundLine)
                            .font(.system(size: 10, weight: .medium))
                            .foregroundStyle(DTC.attention)
                            .lineLimit(2)
                    }
                    Text(store.activeTakeExportLine)
                        .font(.system(size: 10))
                        .foregroundStyle(store.canOpenActiveTakeExport ? DTC.textTertiary : DTC.attention)
                        .lineLimit(1)
                }
            } else {
                VStack(spacing: 5) {
                    Image(systemName: "rectangle.dashed").font(.system(size: 16)).foregroundStyle(DTC.textTertiary)
                    Text("No take selected").font(.system(size: 12, weight: .medium)).foregroundStyle(DTC.textSecondary)
                    Text("Record or pick a recent take").font(.system(size: 10)).foregroundStyle(DTC.textTertiary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 6)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .dtcCard(DTC.card, padding: 12)
    }
}

struct PackageActionBar: View {
    @ObservedObject var store: RecorderStore
    @Binding var confirmDiscard: Bool
    var body: some View {
        VStack(spacing: 8) {
            HStack(spacing: 8) {
                Button { Task { await runPrimaryBuildAction() } } label: {
                    Label(buildLabel, systemImage: buildIcon).frame(maxWidth: .infinity)
                }
                .buttonStyle(DTCButtonStyle(kind: .primary))
                .disabled(!canRunPrimaryBuildAction)
                Button { Task { await store.exportActiveTakeVideo() } } label: {
                    Label(store.exportVideoInProgress ? "Exporting" : "Export", systemImage: "square.and.arrow.up").frame(maxWidth: .infinity)
                }
                .buttonStyle(DTCButtonStyle(kind: .secondary))
                .disabled(!store.canExportVideo)
            }
            HStack(spacing: 8) {
                Button { store.importVideoFromPanel() } label: {
                    Label("Import", systemImage: "square.and.arrow.down").frame(maxWidth: .infinity)
                }
                .buttonStyle(DTCButtonStyle(kind: .secondary))
                .disabled(!store.canImportVideo)
                .help("Import a video file (or drag one onto the shelf below)")

                Menu {
                    Section("Input") {
                        Button { store.importVideoFromPanel() } label: { Label("Import Video…", systemImage: "square.and.arrow.down") }
                            .disabled(!store.canImportVideo)
                        Button { Task { await store.importRecentVideoCandidate() } } label: { Label("Import Latest Phone Video", systemImage: "iphone") }
                            .disabled(!store.canImportRecentVideoCandidate)
                    }
                    Section("Review") {
                        Button { Task { await store.prepareActiveTakeReview() } } label: { Label("Prepare Review", systemImage: "film") }
                            .disabled(!store.canPrepareActiveTakeReview)
                        Button { store.previewActiveTakeReview() } label: { Label("Preview Take Review", systemImage: "film") }
                            .disabled(!store.canPreviewActiveTakeReview)
                        Button { store.previewActiveTakeExport() } label: { Label("Preview Export", systemImage: "play.rectangle") }
                            .disabled(!store.canPreviewActiveTakeExport)
                        Button { store.openActiveTakeExport() } label: { Label("Reveal Export", systemImage: "magnifyingglass") }
                            .disabled(!store.canOpenActiveTakeExport)
                    }
                    Section("Storage") {
                        Button { Task { await store.optimizeActiveTakeStorage() } } label: { Label("Optimize Storage", systemImage: "internaldrive") }
                            .disabled(!store.canOptimizeStorage)
                        Button { Task { await store.refreshActiveTakeStorageStatus() } } label: { Label("Storage Status", systemImage: "info.circle") }
                            .disabled(store.activeTakeURL == nil)
                    }
                    Section("Folder") {
                        Button { store.revealTakeFolder() } label: { Label("Open Take Folder", systemImage: "folder") }
                            .disabled(store.activeTakeURL == nil)
                        Button { store.copyActiveTakeExportPath() } label: { Label("Copy Export Path", systemImage: "doc.on.doc") }
                            .disabled(!store.canCopyActiveTakeExportPath)
                    }
                } label: {
                    Label("More", systemImage: "ellipsis.circle").frame(maxWidth: .infinity)
                }
                .menuStyle(.borderlessButton)
                .padding(.vertical, 5)
                .frame(maxWidth: .infinity)
                .background(RoundedRectangle(cornerRadius: 8).fill(DTC.card))
                .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(DTC.strokeHi, lineWidth: 1))

                Button(role: .destructive) { confirmDiscard = true } label: {
                    Image(systemName: "trash").frame(width: 18)
                }
                .buttonStyle(DTCButtonStyle(kind: .secondary))
                .disabled(!store.canDiscardTake)
                .help("Discard current take")
            }
        }
    }

    private var buildLabel: String {
        if store.activeTakeIsFinalizing { return "Preparing" }
        if store.activeTakeIsBuildingPackage { return "Building" }
        return "Build"
    }

    private var buildIcon: String {
        store.activeTakeIsFinalizing ? "film" : "shippingbox"
    }

    private var canRunPrimaryBuildAction: Bool {
        store.canBuildPackage
    }

    private func runPrimaryBuildAction() async {
        await store.buildPackageSidecars()
    }
}

struct RecentTakesList: View {
    @ObservedObject var store: RecorderStore
    var onEnterReview: () -> Void = {}
    var onDelete: (TakeSummary) -> Void
    var body: some View {
        Group {
            if store.recentTakes.isEmpty {
                VStack(spacing: 6) {
                    Image(systemName: "tray").font(.system(size: 22)).foregroundStyle(DTC.textTertiary)
                    Text("No saved takes yet").font(.system(size: 11)).foregroundStyle(DTC.textTertiary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 5) {
                        ForEach(store.recentTakes) { take in
                            TakeRow(
                                take: take,
                                isSelected: store.activeTakeURL?.path == take.url.path,
                                select: {
                                    store.keyboardDeleteTargetTake = take
                                    if store.selectTakeForReview(take.url) {
                                        onEnterReview()
                                    }
                                },
                                reveal: { store.revealTakeFolder(take.url) },
                                delete: { onDelete(take) },
                                focusForKeyboardDelete: { focused in
                                    if focused {
                                        store.keyboardDeleteTargetTake = take
                                    } else if store.keyboardDeleteTargetTake == take {
                                        store.keyboardDeleteTargetTake = nil
                                    }
                                }
                            )
                        }
                    }
                    .padding(.vertical, 2)
                }
            }
        }
    }
}

struct TakeRow: View {
    let take: TakeSummary
    let isSelected: Bool
    var select: () -> Void
    var reveal: () -> Void
    var delete: () -> Void
    var focusForKeyboardDelete: (Bool) -> Void = { _ in }
    @State private var hover = false

    var body: some View {
        HStack(spacing: 8) {
            Button(action: select) {
                HStack(spacing: 8) {
                    Image(systemName: take.iconName).font(.system(size: 12))
                        .foregroundStyle(isSelected ? DTC.accent : DTC.textTertiary).frame(width: 16)
                    VStack(alignment: .leading, spacing: 1) {
                        Text(take.name).font(.system(size: 12, weight: .medium)).foregroundStyle(DTC.textPrimary).lineLimit(1)
                        Text(take.detailLine).font(.system(size: 10)).foregroundStyle(DTC.textTertiary).lineLimit(1)
                    }
                    Spacer()
                    if !hover {
                        Text(take.sizeLine).font(.system(size: 10, design: .monospaced)).foregroundStyle(DTC.textTertiary)
                    }
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            if hover {
                Button(action: reveal) { Image(systemName: "folder").font(.system(size: 11)) }
                    .buttonStyle(.plain).foregroundStyle(DTC.textSecondary).help("Open folder")
                Button(action: delete) { Image(systemName: "trash").font(.system(size: 11)) }
                    .buttonStyle(.plain).foregroundStyle(DTC.recording.opacity(0.85)).help("Delete take")
            }
        }
        .padding(.horizontal, 8).padding(.vertical, 6)
        .background(RoundedRectangle(cornerRadius: 7).fill(isSelected ? DTC.accent.opacity(0.16) : (hover ? DTC.cardHi : Color.clear)))
        .overlay(RoundedRectangle(cornerRadius: 7).strokeBorder(isSelected ? DTC.accent.opacity(0.4) : Color.clear, lineWidth: 1))
        .onHover {
            hover = $0
            focusForKeyboardDelete($0)
        }
    }
}

struct ImportStrip: View {
    @ObservedObject var store: RecorderStore
    @Binding var dropTargeted: Bool
    var body: some View {
        VStack(spacing: 4) {
            HStack(spacing: 8) {
                Image(systemName: dropTargeted ? "arrow.down.doc.fill" : "arrow.down.doc")
                    .foregroundStyle(dropTargeted ? DTC.accent : DTC.textTertiary)
                Text(store.importVideoInProgress ? "Importing…" : "Drop video or import")
                    .font(.system(size: 11)).foregroundStyle(DTC.textSecondary)
                Spacer()
                Button { store.importVideoFromPanel() } label: { Image(systemName: "plus").font(.system(size: 11)) }
                    .buttonStyle(.plain).foregroundStyle(DTC.textSecondary)
                    .disabled(!store.canImportVideo)
            }
            .padding(.horizontal, 10).padding(.vertical, 9)
            .frame(maxWidth: .infinity)
            .background(RoundedRectangle(cornerRadius: 8).fill(dropTargeted ? DTC.accent.opacity(0.10) : DTC.card))
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .strokeBorder(style: StrokeStyle(lineWidth: 1, dash: [4, 3]))
                    .foregroundStyle(dropTargeted ? DTC.accent : DTC.stroke)
            )
            .onDrop(of: [UTType.fileURL.identifier], isTargeted: $dropTargeted, perform: store.importVideoFromDropProviders)

            if let candidate = store.recentImportCandidate {
                HStack(spacing: 8) {
                    Image(systemName: "iphone").foregroundStyle(DTC.accent).font(.system(size: 11))
                    Text(candidate.name).font(.system(size: 10)).foregroundStyle(DTC.textSecondary).lineLimit(1)
                    Spacer()
                    Button { Task { await store.importRecentVideoCandidate() } } label: {
                        Text("Import").font(.system(size: 10, weight: .semibold))
                    }
                    .buttonStyle(.plain).foregroundStyle(DTC.accent)
                    .disabled(!store.canImportRecentVideoCandidate)
                }
                .padding(.horizontal, 10).padding(.vertical, 6)
                .background(RoundedRectangle(cornerRadius: 7).fill(DTC.card))
                .overlay(RoundedRectangle(cornerRadius: 7).strokeBorder(DTC.stroke, lineWidth: 1))
            }
        }
    }
}

// MARK: - Sources sheet (full device configuration, off the main path)

struct SourcesSheet: View {
    @ObservedObject var store: RecorderStore
    @ObservedObject var preview: DisplayPreviewService
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("Configure Sources").font(.system(size: 15, weight: .semibold)).foregroundStyle(DTC.textPrimary)
                Spacer()
                Button("Done") { dismiss() }.buttonStyle(DTCButtonStyle(kind: .primary))
            }
            .padding(16)
            HLine()
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    SectionLabel("Displays")
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 240), spacing: 12)], spacing: 12) {
                        ForEach(store.devices.videoDevices.filter(\.isScreen)) { device in
                            DisplayConfigCard(device: device, store: store, preview: preview)
                        }
                    }
                    HLine()
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 300), spacing: 12)], spacing: 12) {
                        MicConfigCard(store: store)
                        WebcamConfigCard(store: store)
                        FrameSamplingCard(store: store)
                    }
                    Toggle("Hide normal Demo Take windows after countdown when they overlap the capture display",
                           isOn: $store.autoHideBeforeRecording)
                        .toggleStyle(.checkbox).font(.system(size: 12)).foregroundStyle(DTC.textSecondary)
                    HStack {
                        Button { store.useSimpleDefaults() } label: { Label("Main Screen + Mic", systemImage: "wand.and.stars") }
                            .buttonStyle(DTCButtonStyle(kind: .secondary))
                        Button { Task { await store.reloadSetup() } } label: { Label("Reload Devices", systemImage: "arrow.clockwise") }
                            .buttonStyle(DTCButtonStyle(kind: .secondary))
                        Button { preview.refresh(displayIDs: store.displayPreviewIDs) } label: { Label("Refresh Snapshots", systemImage: "camera.viewfinder") }
                            .buttonStyle(DTCButtonStyle(kind: .secondary))
                        Spacer()
                    }
                }
                .padding(16)
            }
        }
        .frame(width: 720, height: 580)
        .background(DTC.base)
        .preferredColorScheme(.dark)
        .onAppear { preview.refresh(displayIDs: store.displayPreviewIDs) }
        .onChange(of: store.displayPreviewIDs) { _, ids in
            preview.refresh(displayIDs: ids)
        }
    }
}

struct DisplayConfigCard: View {
    let device: CaptureDevice
    @ObservedObject var store: RecorderStore
    @ObservedObject var preview: DisplayPreviewService
    private var metadata: DisplayMetadata {
        store.selectedScreenMetadata[device.id]
            ?? HostEnvironment.displayMetadata(forFFmpegScreenIndex: device.screenOrdinal)
    }
    private var selected: Bool {
        store.selectedScreens.contains { $0.id == device.id }
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top) {
                Toggle(isOn: Binding(
                    get: { selected },
                    set: { store.setScreen(device, enabled: $0) }
                )) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(metadata.summary).font(.system(size: 12, weight: .semibold)).foregroundStyle(DTC.textPrimary).lineLimit(1)
                        Text(metadata.detail).font(.system(size: 10)).foregroundStyle(DTC.textTertiary).lineLimit(2)
                    }
                }
                Spacer()
                Button { store.identifyDisplay(device) } label: {
                    Image(systemName: "rectangle.inset.filled.and.person.filled")
                }
                .buttonStyle(.plain).foregroundStyle(DTC.textSecondary)
                .help("Flash a red border on this physical display")
            }
            ScreenSnapshotView(device: device, store: store, preview: preview).frame(height: 116)
        }
        .dtcCard(DTC.card, padding: 12)
    }
}

struct MicConfigCard: View {
    @ObservedObject var store: RecorderStore
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Microphone").font(.system(size: 12, weight: .semibold)).foregroundStyle(DTC.textPrimary)
            Picker("Microphone", selection: Binding(get: { store.selectedAudioID ?? "" }, set: { store.selectAudio($0) })) {
                Text("No microphone").tag("")
                ForEach(store.devices.audioDevices) { device in
                    Text("\(device.name) [\(device.index)]").tag(device.id)
                }
            }
            .labelsHidden()
            HStack(spacing: 10) {
                LevelMeter(level: store.microphoneLevel)
                Button { store.refreshMicrophoneMonitor() } label: { Label("Live check", systemImage: "waveform") }
                    .buttonStyle(DTCButtonStyle(kind: .secondary))
                    .disabled(store.selectedAudioID == nil)
            }
            Text(store.microphoneMeterStatus).font(.system(size: 10)).foregroundStyle(DTC.textTertiary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .dtcCard(DTC.card, padding: 12)
    }
}

struct WebcamConfigCard: View {
    @ObservedObject var store: RecorderStore
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Webcam").font(.system(size: 12, weight: .semibold)).foregroundStyle(DTC.textPrimary)
                Spacer()
                Toggle("Track", isOn: Binding(get: { store.webcamEnabled }, set: { store.setWebcamEnabled($0) }))
                    .toggleStyle(.switch).labelsHidden()
            }
            Picker("Webcam", selection: Binding(get: { store.selectedWebcamID ?? "" }, set: { store.selectWebcam($0) })) {
                Text("No camera").tag("")
                ForEach(store.devices.videoDevices.filter(\.isLikelyWebcam)) { device in
                    Text("\(device.name) [\(device.index)]").tag(device.id)
                }
            }
            .labelsHidden()
            .disabled(!store.webcamEnabled)
            ZStack {
                RoundedRectangle(cornerRadius: 8).fill(Color.black.opacity(0.35))
                if let session = store.cameraPreviewSession {
                    CameraPreviewView(session: session).clipShape(RoundedRectangle(cornerRadius: 8))
                } else {
                    Text(store.cameraPreviewStatus).font(.system(size: 10)).foregroundStyle(DTC.textTertiary)
                        .multilineTextAlignment(.center).padding(8)
                }
            }
            .frame(height: 110)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .dtcCard(DTC.card, padding: 12)
    }
}

struct FrameSamplingCard: View {
    @ObservedObject var store: RecorderStore
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Frame Sampling").font(.system(size: 12, weight: .semibold)).foregroundStyle(DTC.textPrimary)
            Stepper(value: $store.screenshotInterval, in: 1...30) {
                Text("Every \(store.screenshotInterval)s").font(.system(size: 12)).foregroundStyle(DTC.textSecondary)
            }
            Text("Previews refresh while idle; package frame sampling uses this interval after Stop.")
                .font(.system(size: 10)).foregroundStyle(DTC.textTertiary).fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .dtcCard(DTC.card, padding: 12)
    }
}

// MARK: - Shared media + overlay views

struct ScreenSnapshotView: View {
    let device: CaptureDevice
    @ObservedObject var store: RecorderStore
    @ObservedObject var preview: DisplayPreviewService
    private var metadata: DisplayMetadata {
        store.selectedScreenMetadata[device.id]
            ?? HostEnvironment.displayMetadata(forFFmpegScreenIndex: device.screenOrdinal)
    }
    private var snapshot: NSImage? {
        metadata.displayID.flatMap { preview.thumbnails[$0] } ?? store.screenSnapshots[device.id]
    }
    private var statusText: String {
        if !preview.status.isEmpty { return preview.status }
        return store.screenPreviewStatus[device.id] ?? "Preview pending"
    }
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 8).fill(Color.black.opacity(0.4))
            if let image = snapshot {
                Image(nsImage: image)
                    .resizable()
                    .scaledToFill()
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            } else {
                VStack(spacing: 6) {
                    Image(systemName: "display").font(.system(size: 22)).foregroundStyle(DTC.textTertiary)
                    Text(statusText)
                        .font(.system(size: 10)).foregroundStyle(DTC.textTertiary)
                        .multilineTextAlignment(.center).lineLimit(3).padding(.horizontal, 10)
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .clipped()
        .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(DTC.stroke, lineWidth: 1))
    }
}

struct CountdownOverlay: View {
    let value: Int
    var hides: Bool
    var body: some View {
        ZStack {
            Rectangle().fill(.black.opacity(0.55)).ignoresSafeArea()
            VStack(spacing: 14) {
                Text("\(value)")
                    .font(.system(size: 140, weight: .bold, design: .rounded))
                    .foregroundStyle(.white).shadow(radius: 16)
                Text(hides ? "Recording starts — console will hide" : "Recording starts — console stays visible")
                    .font(.system(size: 14, weight: .medium)).foregroundStyle(.white.opacity(0.85))
            }
        }
    }
}

struct CameraPIPOverlay: View {
    let player: AVPlayer
    let title: String
    @Binding var offset: CGSize
    @Binding var scale: CGFloat
    var bottomInset: CGFloat = 0
    var onLayoutCommit: (CGSize, CGFloat) -> Void
    @GestureState private var dragTranslation: CGSize = .zero

    private let margin: CGFloat = 14

    var body: some View {
        GeometryReader { proxy in
            let baseWidth = min(max(proxy.size.width * 0.24, 150), 260)
            let pipSize = CGSize(width: baseWidth * scale, height: baseWidth * scale * 9 / 16)
            let safeOffset = clamped(
                CGSize(
                    width: offset.width + dragTranslation.width,
                    height: offset.height + dragTranslation.height
                ),
                container: proxy.size,
                pip: pipSize
            )
            let bottomMargin = margin + bottomInset

            ZStack(alignment: .topLeading) {
                PlaybackVideoSurfaceView(player: player)
                    .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
                LinearGradient(
                    colors: [.black.opacity(0.52), .clear],
                    startPoint: .top,
                    endPoint: .center
                )
                .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
                HStack(spacing: 5) {
                    Image(systemName: "camera.fill")
                        .font(.system(size: 9, weight: .semibold))
                    Text(title)
                        .font(.system(size: 10, weight: .semibold))
                        .lineLimit(1)
                }
                .foregroundStyle(.white)
                .padding(.horizontal, 8)
                .padding(.vertical, 5)
                .background(Capsule().fill(.black.opacity(0.48)))
                .padding(8)

                VStack {
                    Spacer()
                    HStack(spacing: 5) {
                        pipButton("minus.magnifyingglass", help: "Smaller camera preview") {
                            commitScaledLayout(
                                max(0.72, scale - 0.1),
                                baseWidth: baseWidth,
                                container: proxy.size
                            )
                        }
                        pipButton("plus.magnifyingglass", help: "Larger camera preview") {
                            commitScaledLayout(
                                min(1.45, scale + 0.1),
                                baseWidth: baseWidth,
                                container: proxy.size
                            )
                        }
                        pipButton("arrow.counterclockwise", help: "Reset camera preview placement") {
                            scale = 1
                            offset = .zero
                            onLayoutCommit(.zero, 1)
                        }
                    }
                    .padding(8)
                }
            }
            .frame(width: pipSize.width, height: pipSize.height)
            .background(Color.black)
            .clipShape(RoundedRectangle(cornerRadius: 9, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 9, style: .continuous).strokeBorder(.white.opacity(0.24), lineWidth: 1))
            .shadow(color: .black.opacity(0.35), radius: 12, y: 5)
            .position(
                x: proxy.size.width - margin - pipSize.width / 2 + safeOffset.width,
                y: proxy.size.height - bottomMargin - pipSize.height / 2 + safeOffset.height
            )
            .contentShape(Rectangle())
            .gesture(
                DragGesture(minimumDistance: 2)
                    .updating($dragTranslation) { value, state, _ in
                        state = value.translation
                    }
                    .onEnded { value in
                        let committed = clamped(
                            CGSize(
                                width: offset.width + value.translation.width,
                                height: offset.height + value.translation.height
                            ),
                            container: proxy.size,
                            pip: pipSize
                        )
                        offset = committed
                        onLayoutCommit(committed, scale)
                    }
            )
            .onAppear {
                offset = clamped(offset, container: proxy.size, pip: pipSize)
            }
            .onChange(of: scale) { _, _ in
                offset = clamped(offset, container: proxy.size, pip: pipSize)
            }
        }
    }

    private func pipButton(_ systemImage: String, help: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(.system(size: 10, weight: .semibold))
                .frame(width: 22, height: 20)
        }
        .buttonStyle(.plain)
        .foregroundStyle(.white)
        .background(RoundedRectangle(cornerRadius: 5, style: .continuous).fill(.black.opacity(0.46)))
        .help(help)
    }

    private func clamped(_ value: CGSize, container: CGSize, pip: CGSize) -> CGSize {
        let minX = min(0, -(container.width - pip.width - margin * 2))
        let minY = min(0, -(container.height - pip.height - margin - (margin + bottomInset)))
        return CGSize(
            width: min(0, max(minX, value.width)),
            height: min(0, max(minY, value.height))
        )
    }

    private func commitScaledLayout(_ nextScale: CGFloat, baseWidth: CGFloat, container: CGSize) {
        let nextSize = CGSize(width: baseWidth * nextScale, height: baseWidth * nextScale * 9 / 16)
        let nextOffset = clamped(offset, container: container, pip: nextSize)
        scale = nextScale
        offset = nextOffset
        onLayoutCommit(nextOffset, nextScale)
    }
}

struct PlaybackVideoSurfaceView: NSViewRepresentable {
    let player: AVPlayer

    func makeNSView(context: Context) -> PlayerLayerHostView {
        let view = PlayerLayerHostView()
        view.setPlayer(player)
        return view
    }

    func updateNSView(_ nsView: PlayerLayerHostView, context: Context) {
        nsView.setPlayer(player)
    }

    static func dismantleNSView(_ nsView: PlayerLayerHostView, coordinator: ()) {
        nsView.setPlayer(nil)
    }
}

final class PlayerLayerHostView: NSView {
    private let rootLayer = CALayer()
    private let playerLayer = AVPlayerLayer()

    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        wantsLayer = true
        layer = rootLayer
        rootLayer.backgroundColor = NSColor.black.cgColor
        rootLayer.addSublayer(playerLayer)
        playerLayer.videoGravity = .resizeAspect
    }

    required init?(coder: NSCoder) {
        nil
    }

    override func layout() {
        super.layout()
        playerLayer.frame = bounds
    }

    func setPlayer(_ player: AVPlayer?) {
        if playerLayer.player !== player {
            playerLayer.player = player
        }
    }
}
