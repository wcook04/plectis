import AppKit
import Combine
import CoreGraphics
import Foundation
import SwiftUI

struct CueOverlayTakeStartPolicy {
    static func shouldRunSafetyCheck(
        bundleLoaded: Bool,
        interactionState: OverlayInteractionState,
        overlayProductionEnabled: Bool
    ) -> Bool {
        bundleLoaded
            && interactionState != .hidden
            && interactionState != .peek
            && !overlayProductionEnabled
    }

    static func visibilityWarning(for receipt: ExclusionPreflightReceipt?) -> String? {
        guard let receipt else {
            return "Cue overlay blocked recording: capture exclusion check did not return a receipt."
        }
        guard !receipt.passed else { return nil }
        return "Cue overlay blocked recording: \(receipt.staleReason ?? "capture exclusion was not proven")."
    }
}

struct CueOverlayProductionGate {
    static func shouldHideCues(
        isRecording: Bool,
        exclusionReceiptCurrent: Bool,
        recordingCueVisibilityLocked: Bool
    ) -> Bool {
        isRecording && !recordingCueVisibilityLocked && !exclusionReceiptCurrent
    }
}

// MARK: - Recipient cue overlay controller (contract §5–8 owner)
//
// The single object the AppDelegate instantiates. It owns the session, the
// per-display panel manager, the arming monitor, the sentinel, and the sidecar
// accumulator. It binds the overlay to the take lifecycle (start/stop) so the
// selected recipient is recorded and the sidecar is written.
//
// Do-not-mix boundaries (contract §8): the overlay CANNOT start or stop recording;
// it only observes take start/stop via callbacks. Capture exclusion proves visual
// omission only — it does not confer send or publication authority.

@MainActor
final class RecipientCueOverlayController: ObservableObject {
    let session = OverlaySession()
    private let panelManager: CueOverlayPanelManager
    private let armingMonitor: OverlayArmingMonitor
    private let sentinel: ExclusionSentinel
    private weak var store: RecorderStore?
    private var cancellables: Set<AnyCancellable> = []

    /// The recipient workbench snapshot for the picker. Primary source is the
    /// generated full overlay queue; the frozen tranche is compatibility fallback.
    @Published var recipientRows: [RecipientQueueRow] = []
    @Published var queueSnapshot: RecipientQueueSnapshot?
    @Published var lastReceipt: ExclusionPreflightReceipt?
    @Published var safetyCheckInProgress = false

    // Sidecar accumulation for the active take.
    private var sidecar = OverlaySidecar.empty()
    private var activeTakeRoot: URL?
    private var lastScrollSidecarEventAt = Date.distantPast
    private var lastScrollSidecarWriteAt = Date.distantPast

    // Picker window (presented from the private Overlay menu).
    private var pickerWindow: NSWindow?

    private var repoRoot: URL { HostEnvironment.repoRoot }

    init(store: RecorderStore) {
        self.store = store
        self.panelManager = CueOverlayPanelManager(session: session)
        self.armingMonitor = OverlayArmingMonitor(session: session, panelManager: panelManager)
        self.sentinel = ExclusionSentinel(session: session, panelManager: panelManager)

        panelManager.onTopologyChange = { [weak self] in
            self?.recordTopologyChange()
        }

        observeForSidecar()
        bindTakeLifecycle(store: store)
        observeAppActivationForQueueRefresh()
    }

    /// Keep the Select Recipient menu honest about what is on disk.
    ///
    /// The menu-bar list is built from `recipientRows`, which used to be loaded ONCE
    /// at `start()`. A run sheet added afterwards (e.g. a new general-deliverable
    /// theme overlay) would then stay invisible until the app was relaunched, which
    /// is the recurring "I added it but it is not in the console" annoyance. The
    /// menu bar is only usable while this app is frontmost, so reloading on every
    /// activation guarantees the list reflects the current disk state by the time
    /// the operator opens the menu. The load is cheap (one queue JSON plus a
    /// front-matter head-read per sidecar sheet).
    private func observeAppActivationForQueueRefresh() {
        NotificationCenter.default
            .publisher(for: NSApplication.didBecomeActiveNotification)
            .sink { [weak self] _ in self?.loadRecipientQueue() }
            .store(in: &cancellables)
    }

    func start() {
        loadRecipientQueue()
        panelManager.refresh()
        armingMonitor.start()
        // Re-show the persisted recipient deck, if any (still hidden until shown).
        session.reloadSelectedIfNeeded(repoRoot: repoRoot)
    }

    func stop() {
        armingMonitor.stop()
        panelManager.hideAll()
    }

    // MARK: - Picker data

    func loadRecipientQueue() {
        do {
            let snapshot = try RecipientQueueLoader.loadSnapshot(repoRoot: repoRoot)
            queueSnapshot = snapshot
            let queueIDs = Set(snapshot.rows.map(\.recipientID))
            let general = RecipientQueueLoader.discoverGeneralRunSheets(
                repoRoot: repoRoot,
                excludingIDs: queueIDs
            )
            recipientRows = snapshot.rows + general
        } catch {
            // Even when the outreach queue is unreadable, on-disk run sheets should
            // still be recordable, so a general deliverable never depends on the
            // outreach pipeline being healthy.
            let general = RecipientQueueLoader.discoverGeneralRunSheets(repoRoot: repoRoot, excludingIDs: [])
            queueSnapshot = nil
            recipientRows = general
            session.lastError = general.isEmpty
                ? "Recipient queue load failed: \(error)"
                : "Recipient queue load failed; showing \(general.count) on-disk run sheet(s): \(error)"
        }
    }

    var recipientMenuRows: [RecipientQueueRow] {
        recipientRows
    }

    // MARK: - Operator actions (wired to the CommandMenu)

    /// Present the recipient picker window (the richer browse surface).
    func showPicker() {
        loadRecipientQueue()
        if pickerWindow == nil {
            let host = NSHostingView(rootView: RecipientPickerView(controller: self))
            let window = NSWindow(
                contentRect: NSRect(x: 0, y: 0, width: 420, height: 520),
                styleMask: [.titled, .closable, .fullSizeContentView],
                backing: .buffered,
                defer: false
            )
            window.title = "Recipient Cue Plane"
            window.titlebarAppearsTransparent = true
            window.isReleasedWhenClosed = false
            window.contentView = host
            window.center()
            pickerWindow = window
        }
        pickerWindow?.makeKeyAndOrderFront(nil)
    }

    func selectRecipient(_ recipientID: String) {
        let ok = session.selectRecipient(recipientID, repoRoot: repoRoot)
        if ok {
            // New deck means the exclusion receipt's deck-hash binding is stale.
            session.exclusionReceiptCurrent = false
            lastReceipt = nil
            panelManager.refresh()
        }
    }

    func showOverlay() {
        session.show()
        panelManager.refresh()
    }

    func hideOverlay() {
        session.hide()
        panelManager.refresh()
    }

    func toggleArrange() {
        session.setArrange(session.interactionState != .arrange)
        panelManager.refresh()
    }

    /// Run the per-session capture-exclusion safety check. This gates cue
    /// visibility during production and the recorder start path when a cue deck is
    /// selected and visible.
    @discardableResult
    func runSafetyCheck() async -> ExclusionPreflightReceipt? {
        guard !safetyCheckInProgress else { return lastReceipt }
        safetyCheckInProgress = true
        panelManager.refresh()
        let receipt = await sentinel.runSafetyCheck()
        lastReceipt = receipt
        sidecar.exclusionPreflightReceipt = receipt
        sidecar.captureFilterGeneration = receipt.captureFilterGeneration
        safetyCheckInProgress = false
        return receipt
    }

    /// Whether the overlay may be enabled for a PRODUCTION take: only while a
    /// current passing receipt exists (contract §4 step 5).
    var overlayProductionEnabled: Bool {
        session.exclusionReceiptCurrent && (lastReceipt?.passed ?? false)
    }

    // MARK: - Take lifecycle binding (contract §7)

    private func bindTakeLifecycle(store: RecorderStore) {
        store.onTakeWillStart = { [weak self] in
            guard let self else { return true }
            return await self.prepareForTakeStart()
        }
        store.onTakeDidStart = { [weak self] takeID, takeRoot in
            self?.handleTakeStart(takeID: takeID, takeRoot: takeRoot)
        }
        store.onTakeWillStop = { [weak self] takeRoot in
            self?.handleTakeStop(takeRoot: takeRoot)
        }
    }

    private func prepareForTakeStart() async -> Bool {
        panelManager.refresh()
        guard CueOverlayTakeStartPolicy.shouldRunSafetyCheck(
            bundleLoaded: session.bundle != nil,
            interactionState: session.interactionState,
            overlayProductionEnabled: overlayProductionEnabled
        ) else {
            return true
        }
        let receipt = await runSafetyCheck()
        if let warning = CueOverlayTakeStartPolicy.visibilityWarning(for: receipt) {
            session.lastError = warning
            panelManager.refresh()
            return false
        }
        panelManager.refresh()
        return true
    }

    private func handleTakeStart(takeID: String, takeRoot: URL) {
        let overlayEnabledAtStart = overlayProductionEnabled
        activeTakeRoot = takeRoot
        sidecar = OverlaySidecar.empty()
        lastScrollSidecarEventAt = .distantPast
        lastScrollSidecarWriteAt = .distantPast
        sidecar.takeID = takeID
        sidecar.startedAt = Date()
        sidecar.selectedRecipient = session.selectedRecipientID
        sidecar.deckSourceHash = session.loadedDeckSourceHash
        sidecar.displayTopology = panelManager.activeDisplayIDs
        sidecar.captureFilterGeneration = ExclusionSentinel.filterGeneration(
            topology: panelManager.activeDisplayIDs,
            windows: panelManager.overlayWindows.map(\.windowNumber)
        )
        sidecar.exclusionPreflightReceipt = lastReceipt
        session.isRecording = true
        session.recordingCueVisibilityLocked = overlayEnabledAtStart
        if overlayEnabledAtStart,
           session.bundle != nil,
           session.interactionState == .hidden || session.interactionState == .peek {
            session.interactionState = .readThrough
        }
        // Fail-closed gate state at start: without a current passing receipt the
        // recorder should already have been blocked if cues were visible. If proof
        // stales mid-take, a visibility-locked cue sheet stays up for continuity.
        sidecar.cuesProductionGatedAtStart = session.bundle != nil && !overlayEnabledAtStart
        // Snapshot the initial visibility state.
        sidecar.visibilityTransitions.append(
            OverlayVisibilityTransition(at: Date(), state: session.interactionState.rawValue)
        )
        writeSidecar()
    }

    private func handleTakeStop(takeRoot: URL) {
        session.isRecording = false
        session.recordingCueVisibilityLocked = false
        sidecar.stoppedAt = Date()
        writeSidecar(forcedRoot: takeRoot)
        activeTakeRoot = nil
    }

    private func writeSidecar(forcedRoot: URL? = nil) {
        guard let root = forcedRoot ?? activeTakeRoot else { return }
        do {
            try OverlaySidecarWriter.write(sidecar, takeRoot: root)
        } catch {
            session.lastError = "Overlay sidecar write failed: \(error.localizedDescription)"
        }
    }

    // MARK: - Sidecar accumulation

    private func observeForSidecar() {
        var lastCardIndex = session.scrollPosition.cardIndex

        session.$scrollPosition
            .sink { [weak self] pos in
                guard let self, self.session.isRecording else {
                    lastCardIndex = pos.cardIndex
                    return
                }
                let now = Date()
                let cardChanged = pos.cardIndex != lastCardIndex
                if pos.cardIndex != lastCardIndex {
                    self.sidecar.viewTransitions.append(
                        OverlayViewTransition(
                            at: now,
                            fromCardIndex: lastCardIndex,
                            toCardIndex: pos.cardIndex,
                            sceneID: self.session.activeCard?.sceneID
                        )
                    )
                    lastCardIndex = pos.cardIndex
                }
                guard cardChanged || now.timeIntervalSince(self.lastScrollSidecarEventAt) >= 0.25 else {
                    return
                }
                self.lastScrollSidecarEventAt = now
                self.sidecar.scrollSyncEvents.append(
                    OverlayScrollSyncEvent(
                        at: now,
                        cardIndex: pos.cardIndex,
                        intraCardFraction: pos.intraCardFraction,
                        leaderDisplayID: self.panelManager.activeDisplayIDs.first
                    )
                )
                if cardChanged || now.timeIntervalSince(self.lastScrollSidecarWriteAt) >= 1 {
                    self.lastScrollSidecarWriteAt = now
                    self.writeSidecar()
                }
            }
            .store(in: &cancellables)

        session.$interactionState
            .sink { [weak self] state in
                guard let self, self.session.isRecording else { return }
                self.sidecar.visibilityTransitions.append(
                    OverlayVisibilityTransition(at: Date(), state: state.rawValue)
                )
                self.writeSidecar()
            }
            .store(in: &cancellables)
    }

    private func recordTopologyChange() {
        guard session.isRecording else { return }
        sidecar.displayTopology = panelManager.activeDisplayIDs
        // A topology change invalidates the exclusion receipt (already cleared by
        // the panel manager); record the geometry change for learning.
        for id in panelManager.activeDisplayIDs {
            let frame = session.presentation(for: id).savedFrame ?? .zero
            sidecar.geometryChanges.append(
                OverlayGeometryChange(
                    at: Date(),
                    displayID: id,
                    frame: [Double(frame.minX), Double(frame.minY), Double(frame.width), Double(frame.height)]
                )
            )
        }
        sidecar.exclusionPreflightReceipt?.staleReason = "display_topology_changed"
        writeSidecar()
    }
}
