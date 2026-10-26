import AppKit
import Combine
import CoreGraphics
import SwiftUI

// MARK: - Per-display panel manager (contract §5)
//
// Native panels per display:
//   - Cue sheet:   see-through teleprompter, click-through (ignoresMouseEvents=true)
//                  by default, top band. Persistent (no auto-close). Command-scroll
//                  mutation is owned by OverlayArmingMonitor's local/global scroll
//                  monitors; arming only changes presentation and click-through state.
//   - Resize grabber: tiny, always interactive, bottom edge.
//
// Panels are keyed by CGDirectDisplayID (NOT NSScreen.main). The window shape reuses
// HudOverlayController's non-activating/floating recipe so showing the overlay never
// steals focus from the app being demonstrated. The per-display creation pattern
// mirrors DisplayIdentifyOverlay, but persistent + HUD material.
//
// These panels sit above normal layer 0 and are marked non-shareable, so
// RecipientOverlayCaptureExclusion omits them while still allowing deliberate
// normal app windows to remain visible. The sentinel is the per-session proof of it.
//
// The hosted CueSheetView observes the session directly (ObservedObject), so the
// manager never rebuilds rootView on state changes — that would reset the scroll
// position. It only toggles ignoresMouseEvents and orders panels in/out.

@MainActor
final class CueOverlaySheetPanel: NSPanel {
    var displayID: CGDirectDisplayID = 0

    override var canBecomeKey: Bool { false }
    override var canBecomeMain: Bool { false }

    override func constrainFrameRect(_ frameRect: NSRect, to screen: NSScreen?) -> NSRect {
        frameRect
    }
}

struct CueOverlayTopologyChangePolicy {
    static func nextInteractionStateAfterDisplayChange(
        currentState: OverlayInteractionState
    ) -> OverlayInteractionState {
        currentState
    }

    static func visibilityMessageAfterDisplayChange(
        isRecording: Bool,
        currentState: OverlayInteractionState
    ) -> String? {
        if isRecording {
            return "Display topology changed during recording. Cue overlay stayed visible for this take; run the safety check before the next take."
        }
        switch currentState {
        case .hidden, .peek:
            return nil
        case .readThrough, .armed, .arrange:
            return "Display topology changed. Cue overlay stayed visible; run the safety check before recording."
        }
    }
}

@MainActor
final class CueOverlayPanelManager {
    private struct DisplayPanels {
        var sheet: CueOverlaySheetPanel
        var sheetHost: NSHostingView<CueSheetView>
        var nodule: NSPanel
        var grabber: NSPanel
    }

    private let session: OverlaySession
    private var panels: [CGDirectDisplayID: DisplayPanels] = [:]
    private var cancellables: Set<AnyCancellable> = []
    private var didInitHeight = false

    /// Callbacks fired when a display-topology change is detected, so the controller
    /// can record that the exclusion receipt is stale for the current topology.
    var onTopologyChange: (() -> Void)?

    init(session: OverlaySession) {
        self.session = session
        observe()
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(screenParametersChanged),
            name: NSApplication.didChangeScreenParametersNotification,
            object: nil
        )
    }

    deinit {
        NotificationCenter.default.removeObserver(self)
    }

    // MARK: - Public surface

    func refresh() {
        reconcilePanels()
        applyState()
    }

    func hideAll() {
        for (_, dp) in panels {
            dp.sheet.orderOut(nil)
            dp.nodule.orderOut(nil)
            dp.grabber.orderOut(nil)
        }
    }

    /// The set of overlay windows. Our panels are NOT excepted from capture — they
    /// must stay excluded; this is here so the recorder could except a deliberately
    /// public window if ever needed.
    var overlayWindows: [NSWindow] {
        panels.values.flatMap { [$0.sheet, $0.nodule, $0.grabber] }
    }

    var activeDisplayIDs: [CGDirectDisplayID] {
        Array(panels.keys)
    }

    // MARK: - Observation

    private func observe() {
        session.$interactionState
            .sink { [weak self] _ in self?.applyState() }
            .store(in: &cancellables)
        session.$perDisplay
            .sink { [weak self] _ in self?.applyState() }
            .store(in: &cancellables)
        // Drag-to-resize: resize every sheet live and keep its grabber pinned to the
        // new bottom edge, so the handle stays under the cursor for the whole drag.
        // On release, re-settle all panels from the canonical geometry.
        session.$sheetHeight
            .sink { [weak self] _ in self?.applyResize() }
            .store(in: &cancellables)
        session.$sheetWidth
            .sink { [weak self] _ in self?.applyResize() }
            .store(in: &cancellables)
        session.$isResizing
            .sink { [weak self] resizing in if !resizing { self?.repositionAllPanels() } }
            .store(in: &cancellables)
        // Production gate: takes that did not pass the start proof remain fail-closed,
        // while an already-proven active take keeps its cue visibility if topology
        // churn stales the receipt mid-flight.
        session.$exclusionReceiptCurrent
            .sink { [weak self] _ in self?.applyState() }
            .store(in: &cancellables)
        session.$isRecording
            .sink { [weak self] _ in self?.applyState() }
            .store(in: &cancellables)
        session.$recordingCueVisibilityLocked
            .sink { [weak self] _ in self?.applyState() }
            .store(in: &cancellables)
    }

    /// Resize every sheet to the shared height (top-anchored) and keep each grabber
    /// reachable. When the sheet extends below the display, the grabber pins to the
    /// visible bottom edge instead of disappearing offscreen.
    private func applyResize() {
        for (id, dp) in panels {
            guard let screen = screen(for: id) else { continue }
            let rect = cueSheetRect(for: screen)
            dp.sheet.setFrame(rect, display: true)
            dp.sheetHost.frame = NSRect(origin: .zero, size: rect.size)
            session.setVisibleSheetHeight(visibleSheetHeight(sheetRect: rect, screen: screen), for: id)
            dp.grabber.setFrameOrigin(visibleGrabberOrigin(sheetRect: rect, screen: screen, size: dp.grabber.frame.size))
        }
    }

    private func repositionAllPanels() {
        for (id, screen) in currentDisplays() { positionPanels(displayID: id, screen: screen) }
    }

    private func screen(for id: CGDirectDisplayID) -> NSScreen? {
        currentDisplays().first { $0.id == id }?.screen
    }

    @objc private func screenParametersChanged() {
        // Topology changed: reconcile panels to the new display set, preserve
        // semantic position (it lives on the session), re-centre panels lacking
        // saved geometry, and invalidate the sentinel receipt.
        Task { @MainActor in
            self.reconcilePanels()
            self.session.exclusionReceiptCurrent = false
            let currentState = self.session.interactionState
            self.session.interactionState = CueOverlayTopologyChangePolicy.nextInteractionStateAfterDisplayChange(
                currentState: currentState
            )
            if let message = CueOverlayTopologyChangePolicy.visibilityMessageAfterDisplayChange(
                isRecording: self.session.isRecording,
                currentState: currentState
            ) {
                self.session.lastError = message
            }
            self.applyState()
            self.onTopologyChange?()
        }
    }

    // MARK: - Panel lifecycle

    private func currentDisplays() -> [(id: CGDirectDisplayID, screen: NSScreen)] {
        NSScreen.screens.compactMap { screen in
            guard let id = HostEnvironment.displayID(for: screen) else { return nil }
            return (id, screen)
        }
    }

    private func reconcilePanels() {
        let displays = currentDisplays()
        let currentIDs = displays.map(\.id)
        session.reconcileDisplays(currentIDs)

        // Keep the absolute drag ceiling explicit. This deliberately does not shrink
        // to the display height; oversized sheets rely on visible-viewport scrolling.
        updateSharedSizeCaps(displays: displays)

        // First time we see a screen, default the shared height to ~a top quarter.
        if !didInitHeight, let first = displays.first {
            session.setSheetHeight(first.screen.visibleFrame.height * 0.25)
            if session.sheetWidth <= 0 {
                session.setSheetWidth(defaultCueSheetWidth(for: first.screen))
            }
            didInitHeight = true
        }

        for (id, dp) in panels where !currentIDs.contains(id) {
            dp.sheet.orderOut(nil)
            dp.nodule.orderOut(nil)
            dp.grabber.orderOut(nil)
            panels.removeValue(forKey: id)
        }

        for (id, screen) in displays {
            if panels[id] == nil {
                panels[id] = buildPanels(displayID: id, screen: screen)
            }
            positionPanels(displayID: id, screen: screen)
        }
    }

    private func buildPanels(displayID: CGDirectDisplayID, screen: NSScreen) -> DisplayPanels {
        // --- Cue sheet (see-through, click-through, persistent) ---
        let sheetRect = cueSheetRect(for: screen)
        let host = NSHostingView(rootView: CueSheetView(session: session, displayID: displayID))
        host.frame = NSRect(origin: .zero, size: sheetRect.size)

        let sheet = CueOverlaySheetPanel(
            contentRect: sheetRect,
            styleMask: [.nonactivatingPanel, .fullSizeContentView, .hudWindow],
            backing: .buffered,
            defer: false,
            screen: screen
        )
        sheet.titleVisibility = .hidden
        sheet.titlebarAppearsTransparent = true
        sheet.isFloatingPanel = true
        sheet.level = .floating
        sheet.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary, .ignoresCycle]
        sheet.hidesOnDeactivate = false
        sheet.becomesKeyOnlyIfNeeded = true
        sheet.isOpaque = false
        sheet.hasShadow = false
        sheet.backgroundColor = .clear
        sheet.ignoresMouseEvents = true // click-through by default (read_through)
        sheet.displayID = displayID
        sheet.standardWindowButton(.closeButton)?.isHidden = true
        sheet.standardWindowButton(.miniaturizeButton)?.isHidden = true
        sheet.standardWindowButton(.zoomButton)?.isHidden = true
        sheet.contentView = host
        RecipientOverlayCaptureExclusion.protectOverlayWindow(sheet)

        // --- Retired handle nodule ---
        // The operator explicitly does not want a floating "Hide cues" control.
        // Keep the panel object only to avoid widening the DisplayPanels shape.
        let noduleSize = NSSize(width: 132, height: 30)
        let nodule = NSPanel(
            contentRect: NSRect(origin: .zero, size: noduleSize),
            styleMask: [.nonactivatingPanel, .fullSizeContentView, .hudWindow],
            backing: .buffered,
            defer: false,
            screen: screen
        )
        nodule.titleVisibility = .hidden
        nodule.titlebarAppearsTransparent = true
        nodule.isFloatingPanel = true
        nodule.level = .floating
        nodule.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary, .ignoresCycle]
        nodule.hidesOnDeactivate = false
        nodule.becomesKeyOnlyIfNeeded = true
        nodule.isOpaque = false
        nodule.hasShadow = false
        nodule.backgroundColor = .clear
        nodule.ignoresMouseEvents = true
        let noduleHost = NSHostingView(rootView: CueHandleNoduleView(session: session))
        noduleHost.frame = NSRect(origin: .zero, size: noduleSize)
        nodule.contentView = noduleHost
        RecipientOverlayCaptureExclusion.protectOverlayWindow(nodule)

        // --- Resize grabber (always interactive, bottom edge) ---
        // The interactive panel is a touch larger than the visible pill so the handle
        // is easy to grab without hunting for a 5pt sliver; the pill is centred inside.
        let grabberSize = NSSize(width: 174, height: 30)
        let grabber = NSPanel(
            contentRect: NSRect(origin: .zero, size: grabberSize),
            styleMask: [.nonactivatingPanel, .fullSizeContentView, .hudWindow],
            backing: .buffered,
            defer: false,
            screen: screen
        )
        grabber.titleVisibility = .hidden
        grabber.titlebarAppearsTransparent = true
        grabber.isFloatingPanel = true
        grabber.level = .floating
        grabber.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary, .ignoresCycle]
        grabber.hidesOnDeactivate = false
        grabber.becomesKeyOnlyIfNeeded = true
        grabber.isOpaque = false
        grabber.hasShadow = false
        grabber.backgroundColor = .clear
        grabber.ignoresMouseEvents = false // always interactive
        grabber.contentView = CueResizeGrabberNSView(session: session, size: grabberSize)
        RecipientOverlayCaptureExclusion.protectOverlayWindow(grabber)

        return DisplayPanels(sheet: sheet, sheetHost: host, nodule: nodule, grabber: grabber)
    }

    /// Cue-sheet rect: top teleprompter column, height = the SHARED
    /// dragged height (top-anchored, so resizing grows downward). Height may exceed
    /// the visible frame; scrolling then uses the visible intersection as viewport.
    private func cueSheetRect(for screen: NSScreen) -> CGRect {
        let vis = screen.visibleFrame
        let displayMaxWidth = max(OverlaySession.minSheetWidth, vis.width - 24)
        let desiredWidth = session.sheetWidth > 0 ? session.sheetWidth : defaultCueSheetWidth(for: screen)
        let width = min(max(desiredWidth, OverlaySession.minSheetWidth), min(session.maxSheetWidth, displayMaxWidth))
        let height = min(max(session.sheetHeight, OverlaySession.minSheetHeight), session.maxSheetHeight)
        let x = vis.minX + (vis.width - width) / 2
        let topPad = min(max(vis.height * 0.012, 8), 18)
        let y = vis.maxY - height - topPad
        return CGRect(x: x, y: y, width: width, height: height)
    }

    private func defaultCueSheetWidth(for screen: NSScreen) -> CGFloat {
        let vis = screen.visibleFrame
        return min(max(vis.width * 0.36, 420), 680)
    }

    private func updateSharedSizeCaps(displays: [(id: CGDirectDisplayID, screen: NSScreen)]) {
        session.setMaxSheetHeight(OverlaySession.defaultMaxSheetHeight)
        let narrowestUsableDisplay = displays
            .map { max(OverlaySession.minSheetWidth, $0.screen.visibleFrame.width - 24) }
            .min() ?? OverlaySession.defaultMaxSheetWidth
        session.setMaxSheetWidth(min(OverlaySession.defaultMaxSheetWidth, narrowestUsableDisplay))
    }

    private func visibleSheetHeight(sheetRect: CGRect, screen: NSScreen) -> CGFloat {
        let intersection = sheetRect.intersection(screen.visibleFrame)
        guard !intersection.isNull else { return 0 }
        return intersection.height
    }

    private func noduleOrigin(for screen: NSScreen, size: NSSize) -> CGPoint {
        let vis = screen.visibleFrame
        let x = vis.minX + (vis.width - size.width) / 2
        let y = vis.maxY - size.height - 6
        return CGPoint(x: x, y: y)
    }

    private func visibleGrabberOrigin(sheetRect: CGRect, screen: NSScreen, size: NSSize) -> CGPoint {
        let vis = screen.visibleFrame
        let x = sheetRect.midX - size.width / 2
        let bottomEdge = max(sheetRect.minY, vis.minY + size.height / 2)
        return CGPoint(x: x, y: bottomEdge - size.height / 2)
    }

    private func positionPanels(displayID: CGDirectDisplayID, screen: NSScreen) {
        guard let dp = panels[displayID] else { return }
        let presentation = session.presentation(for: displayID)
        let frame = presentation.savedFrame ?? cueSheetRect(for: screen)
        dp.sheet.setFrame(frame, display: false)
        dp.sheetHost.frame = NSRect(origin: .zero, size: frame.size)
        dp.nodule.setFrameOrigin(noduleOrigin(for: screen, size: dp.nodule.frame.size))
        session.setVisibleSheetHeight(visibleSheetHeight(sheetRect: frame, screen: screen), for: displayID)
        dp.grabber.setFrameOrigin(visibleGrabberOrigin(sheetRect: frame, screen: screen, size: dp.grabber.frame.size))
    }

    // MARK: - State application

    private func applyState() {
        let state = session.interactionState
        let productionBlocked = CueOverlayProductionGate.shouldHideCues(
            isRecording: session.isRecording,
            exclusionReceiptCurrent: session.exclusionReceiptCurrent,
            recordingCueVisibilityLocked: session.recordingCueVisibilityLocked
        )
        for (id, dp) in panels {
            let enabled = session.presentation(for: id).enabled
            switch state {
            case .hidden:
                dp.sheet.orderOut(nil)
                dp.nodule.orderOut(nil)
                dp.grabber.orderOut(nil)
            case .peek:
                dp.sheet.orderOut(nil)
                dp.grabber.orderOut(nil)
                dp.nodule.orderOut(nil)
            case .readThrough, .armed, .arrange:
                if enabled && productionBlocked {
                    dp.sheet.orderOut(nil)
                    dp.grabber.orderOut(nil)
                    dp.nodule.orderOut(nil)
                } else if enabled {
                    dp.sheet.alphaValue = 1
                    dp.sheet.orderFrontRegardless()
                    dp.nodule.orderOut(nil)
                    dp.grabber.orderFrontRegardless()
                    if state == .arrange {
                        dp.sheet.ignoresMouseEvents = false
                    } else if state == .readThrough {
                        dp.sheet.ignoresMouseEvents = true
                    }
                    // .armed: leave ignoresMouseEvents as the arming monitor set it.
                } else {
                    dp.sheet.orderOut(nil)
                    dp.nodule.orderOut(nil)
                    dp.grabber.orderOut(nil)
                }
            }
        }
    }

    // MARK: - Arming hooks (called by OverlayArmingMonitor)

    /// Make exactly the panel whose frame contains `globalPoint` the scroll target
    /// (mouse not ignored), so AppKit can deliver scrollWheel to that inactive
    /// panel. Returns the armed display id, if any.
    @discardableResult
    func armSheet(containing globalPoint: CGPoint) -> CGDirectDisplayID? {
        var armedID: CGDirectDisplayID?
        for (id, dp) in panels {
            let contains = dp.sheet.frame.contains(globalPoint)
            // Only touch the window flag on an actual change — this runs on every
            // scroll tick, and redundant writes were re-publishing session state and
            // re-ordering windows mid-scroll, which made the scroll judder.
            if dp.sheet.ignoresMouseEvents != !contains {
                dp.sheet.ignoresMouseEvents = !contains
            }
            if contains { armedID = id }
        }
        // Guarded publishes: @Published always fires on assignment, so assigning the
        // same value every tick would thrash applyState(). Write only on change.
        if session.armedDisplayID != armedID { session.armedDisplayID = armedID }
        if armedID != nil, session.interactionState != .armed {
            session.interactionState = .armed
        }
        return armedID
    }

    /// Restore all sheets to click-through immediately (read_through).
    func disarmAllSheets() {
        for (_, dp) in panels where !dp.sheet.ignoresMouseEvents {
            dp.sheet.ignoresMouseEvents = true
        }
        if session.armedDisplayID != nil { session.armedDisplayID = nil }
        if session.interactionState == .armed {
            session.interactionState = .readThrough
        }
    }

    /// Whether `globalPoint` is inside any cue-sheet frame (used by the monitor).
    func sheetFrameContains(_ globalPoint: CGPoint) -> Bool {
        displayID(containing: globalPoint) != nil
    }

    /// Resolve the cue sheet under a global screen point without changing
    /// targetability. Used by the scroll monitors; do not call armSheet just to
    /// discover the display.
    func displayID(containing globalPoint: CGPoint) -> CGDirectDisplayID? {
        for (id, dp) in panels {
            guard session.presentation(for: id).enabled else { continue }
            guard dp.sheet.isVisible else { continue }
            if dp.sheet.frame.contains(globalPoint) { return id }
        }
        return nil
    }

    func lineStepDisplayID(containing globalPoint: CGPoint) -> CGDirectDisplayID? {
        if let direct = displayID(containing: globalPoint) { return direct }
        if let armed = session.armedDisplayID { return armed }
        return panels
            .filter { entry in
                session.presentation(for: entry.key).enabled && entry.value.sheet.isVisible
            }
            .map(\.key)
            .sorted()
            .first
    }

    func sheetIgnoresMouseEvents(for displayID: CGDirectDisplayID) -> Bool? {
        panels[displayID]?.sheet.ignoresMouseEvents
    }
}

// MARK: - Handle nodule view

/// The tiny always-interactive restore control. Click-through sheets cannot host
/// their own controls, so this is a separate panel. Show / hide (peek) only — the
/// script itself is one continuous scroll, so there are no card chevrons.
struct CueHandleNoduleView: View {
    @ObservedObject var session: OverlaySession

    var body: some View {
        if productionBlocked {
            statusLabel
        } else {
            Button { toggleEye() } label: {
                HStack(spacing: 6) {
                    Image(systemName: eyeIcon)
                    Text(isHidden ? "Show cues" : "Hide cues")
                        .font(.system(size: 12, weight: .semibold))
                }
            }
            .buttonStyle(.plain)
            .font(.system(size: 13, weight: .bold))
            .foregroundStyle(.white)
            .padding(.horizontal, 12)
            .padding(.vertical, 5)
            .background(Capsule().fill(.ultraThinMaterial).environment(\.colorScheme, .dark))
            .overlay(Capsule().strokeBorder(Color.white.opacity(0.18), lineWidth: 1))
        }
    }

    /// Shown while a take is recording but capture exclusion is not currently proven:
    /// the cue sheet is force-hidden and the operator must run the safety check
    /// before cues will reappear. This nodule is itself app-excluded from capture.
    private var statusLabel: some View {
        HStack(spacing: 6) {
            Image(systemName: "exclamationmark.triangle.fill")
            Text("Cues hidden · run safety check")
                .font(.system(size: 12, weight: .semibold))
        }
        .font(.system(size: 13, weight: .bold))
        .foregroundStyle(.black)
        .padding(.horizontal, 12)
        .padding(.vertical, 5)
        .background(Capsule().fill(Color.orange))
        .overlay(Capsule().strokeBorder(Color.white.opacity(0.25), lineWidth: 1))
        .fixedSize(horizontal: true, vertical: false)
        .help("A take is recording but capture exclusion is not currently proven. Run Overlay > Run Safety Check to show cues.")
    }

    private var productionBlocked: Bool {
        CueOverlayProductionGate.shouldHideCues(
            isRecording: session.isRecording,
            exclusionReceiptCurrent: session.exclusionReceiptCurrent,
            recordingCueVisibilityLocked: session.recordingCueVisibilityLocked
        )
    }

    private var isHidden: Bool {
        session.interactionState == .peek || session.interactionState == .hidden
    }

    private var eyeIcon: String { isHidden ? "eye" : "eye.slash" }

    private func toggleEye() {
        if isHidden { session.show() } else { session.peek() }
    }
}

// MARK: - Resize grabber

/// The bottom-edge grab handle. Drag it vertically to set the SHARED panel height,
/// so both screens resize together. A separate interactive panel, because the cue
/// sheet itself is click-through.
///
/// The drag is tracked at the AppKit layer (`CueResizeGrabberNSView`), NOT with a
/// SwiftUI `DragGesture`. A SwiftUI drag inside this tiny non-activating panel was
/// unreliable: its view-local translation broke the instant the pointer slid off
/// the handle onto the sheet growing underneath it, so the height stuttered and
/// snapped back to its start. AppKit's mouse-down grab + absolute screen-position
/// tracking is immune to that, and lets the handle ride the edge under the cursor.

/// Pure resize math, kept free of AppKit so it can be unit-tested.
///
/// Height is anchored to where the drag began plus how far the cursor has moved
/// since, so it can never accumulate error. The one subtlety is the rails: when a
/// drag pushes past min or max, the anchor re-pins to the rail and the live pointer,
/// so the very next move in the opposite direction responds immediately instead of
/// first replaying the overshoot. That re-anchoring is what removes the dead zone
/// where dragging back up did nothing until the cursor returned to the cap — and the
/// shared cap means the rail sits exactly where the panel stops rendering, so the
/// handle never detaches from the cursor.
struct CueSheetResizeDrag {
    private(set) var anchorHeight: CGFloat
    private(set) var anchorPointerY: CGFloat
    let minHeight: CGFloat
    let maxHeight: CGFloat

    init(startHeight: CGFloat, startPointerY: CGFloat, minHeight: CGFloat, maxHeight: CGFloat) {
        self.minHeight = minHeight
        self.maxHeight = Swift.max(minHeight, maxHeight)
        self.anchorHeight = Swift.min(Swift.max(startHeight, minHeight), self.maxHeight)
        self.anchorPointerY = startPointerY
    }

    /// Resolve the new height for the live pointer Y (screen coords, bottom-left
    /// origin). Dragging DOWN (Y decreases) grows the top-anchored panel.
    mutating func resolve(pointerY: CGFloat) -> CGFloat {
        let grown = anchorPointerY - pointerY
        let proposed = anchorHeight + grown
        let clamped = Swift.min(Swift.max(proposed, minHeight), maxHeight)
        if clamped != proposed {
            anchorHeight = clamped
            anchorPointerY = pointerY
        }
        return clamped
    }
}

/// Horizontal resize math for the center-bound teleprompter width. Grabbing the
/// left half and dragging left grows; grabbing the right half and dragging right
/// grows. The panel manager keeps the sheet centered, so either side movement is
/// mirrored on the opposite side.
struct CueSheetWidthResizeDrag {
    private(set) var anchorWidth: CGFloat
    private(set) var anchorPointerX: CGFloat
    private let multiplier: CGFloat
    let minWidth: CGFloat
    let maxWidth: CGFloat

    init(
        startWidth: CGFloat,
        startPointerX: CGFloat,
        startLocalX: CGFloat,
        handleMidX: CGFloat,
        minWidth: CGFloat,
        maxWidth: CGFloat
    ) {
        self.minWidth = minWidth
        self.maxWidth = Swift.max(minWidth, maxWidth)
        self.anchorWidth = Swift.min(Swift.max(startWidth, minWidth), self.maxWidth)
        self.anchorPointerX = startPointerX
        self.multiplier = startLocalX < handleMidX ? -2 : 2
    }

    mutating func resolve(pointerX: CGFloat) -> CGFloat {
        let proposed = anchorWidth + (pointerX - anchorPointerX) * multiplier
        let clamped = Swift.min(Swift.max(proposed, minWidth), maxWidth)
        if clamped != proposed {
            anchorWidth = clamped
            anchorPointerX = pointerX
        }
        return clamped
    }
}

/// Pure decoration; the host NSView owns every click so this never hit-tests. The
/// center pill keeps its size while the interactive panel around it is larger, so
/// the pill is easy to grab and the text-size controls have real hit targets.
struct CueResizeGrabberView: View {
    var body: some View {
        HStack(spacing: 8) {
            textButton("-")
            Capsule()
                .fill(Color.white.opacity(0.34))
                .frame(width: 58, height: 5)
                .frame(width: 74, height: 18)
            textButton("+")
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(Capsule().fill(.ultraThinMaterial).environment(\.colorScheme, .dark))
        .overlay(Capsule().strokeBorder(Color.white.opacity(0.18), lineWidth: 1))
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .allowsHitTesting(false)
    }

    private func textButton(_ label: String) -> some View {
        Text(label)
            .font(.system(size: 15, weight: .heavy, design: .rounded))
            .foregroundStyle(.white.opacity(0.88))
            .frame(width: 28, height: 22)
            .background(Capsule().fill(Color.white.opacity(0.13)))
            .overlay(Capsule().strokeBorder(Color.white.opacity(0.16), lineWidth: 1))
    }
}

/// AppKit drag tracker for the resize handle. Hosts the SwiftUI capsule purely for
/// looks and drives `OverlaySession.sheetHeight` through `CueSheetResizeDrag`, which
/// reads the pointer's ABSOLUTE screen Y fresh each event. Because the height is
/// re-derived (not accumulated) and re-anchored at the rails, it cannot drift, snap
/// back, or open a dead zone — even as this handle follows the panel's edge.
final class CueResizeGrabberNSView: NSView {
    private let session: OverlaySession
    private var trackingAreaRef: NSTrackingArea?
    private let textButtonHitWidth: CGFloat = 40

    init(session: OverlaySession, size: NSSize) {
        self.session = session
        super.init(frame: NSRect(origin: .zero, size: size))
        toolTip = "Drag center to resize cues; use - / + for text size"
        let host = NSHostingView(rootView: CueResizeGrabberView())
        host.frame = bounds
        host.autoresizingMask = [.width, .height]
        addSubview(host)
    }

    required init?(coder: NSCoder) { nil }

    // The grabber lives in a non-activating panel that never becomes key, so the
    // first click would otherwise be swallowed to focus the window instead of
    // starting the drag. Accept it as a real mouse-down.
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }

    // Claim every click for this view; never let SwiftUI's internal hit-testing
    // inside a non-key panel swallow the drag.
    override func hitTest(_ point: NSPoint) -> NSView? {
        bounds.contains(convert(point, from: superview)) ? self : nil
    }

    // Track the whole drag with a SYNCHRONOUS local event loop instead of relying on
    // overridden mouseDragged/mouseUp. A floating, non-activating panel whose window
    // we move mid-drag is exactly the case where responder-chain delivery of follow-up
    // drag events is unreliable — events would arrive once or not at all and the handle
    // felt dead. `nextEvent(matching:)` pulls the events ourselves, so it cannot be
    // starved by the window moving or the panel never becoming key.
    override func mouseDown(with event: NSEvent) {
        let localPoint = convert(event.locationInWindow, from: nil)
        if localPoint.x <= textButtonHitWidth {
            session.adjustCueTextScale(by: -0.06)
            return
        }
        if localPoint.x >= bounds.width - textButtonHitWidth {
            session.adjustCueTextScale(by: 0.06)
            return
        }

        let startPointer = NSEvent.mouseLocation
        var heightDrag = CueSheetResizeDrag(
            startHeight: session.sheetHeight,
            startPointerY: startPointer.y,
            minHeight: OverlaySession.minSheetHeight,
            maxHeight: session.maxSheetHeight
        )
        var widthDrag = CueSheetWidthResizeDrag(
            startWidth: session.sheetWidth > 0 ? session.sheetWidth : (window?.frame.width ?? OverlaySession.minSheetWidth),
            startPointerX: startPointer.x,
            startLocalX: localPoint.x,
            handleMidX: bounds.midX,
            minWidth: OverlaySession.minSheetWidth,
            maxWidth: session.maxSheetWidth
        )
        session.isResizing = true
        logResize("down", pointer: startPointer, height: session.sheetHeight, width: session.sheetWidth)

        var dragCount = 0
        trackingLoop: while let next = NSApp.nextEvent(
            matching: [.leftMouseDragged, .leftMouseUp],
            until: .distantFuture,
            inMode: .eventTracking,
            dequeue: true
        ) {
            switch next.type {
            case .leftMouseDragged:
                let pointer = NSEvent.mouseLocation
                let height = heightDrag.resolve(pointerY: pointer.y)
                let width = widthDrag.resolve(pointerX: pointer.x)
                session.setSheetHeight(height)
                session.setSheetWidth(width)
                dragCount += 1
                if dragCount % 4 == 0 {
                    logResize("drag", pointer: pointer, height: session.sheetHeight, width: session.sheetWidth)
                }
            case .leftMouseUp:
                logResize("up", pointer: NSEvent.mouseLocation, height: session.sheetHeight, width: session.sheetWidth, drags: dragCount)
                break trackingLoop
            default:
                break
            }
        }
        session.isResizing = false
    }

    /// Append a one-line resize diagnostic so the drag can be verified from the shell
    /// without a screen recording (the overlay is capture-excluded and never shows in
    /// a screenshot). Best-effort only; never affects the drag.
    private func logResize(_ stage: String, pointer: CGPoint, height: CGFloat, width: CGFloat, drags: Int? = nil) {
        let url = URL(fileURLWithPath: "<host-temp>/demo-take-console-resize.jsonl")
        var line = "{\"stage\":\"\(stage)\",\"pointer_x\":\(Int(pointer.x)),\"pointer_y\":\(Int(pointer.y)),\"height\":\(Int(height)),\"width\":\(Int(width)),\"max_height\":\(Int(session.maxSheetHeight)),\"max_width\":\(Int(session.maxSheetWidth)),\"text_scale\":\(String(format: "%.2f", Double(session.cueTextScale)))"
        if let drags { line += ",\"drags\":\(drags)" }
        line += "}\n"
        guard let data = line.data(using: .utf8) else { return }
        if let handle = try? FileHandle(forWritingTo: url) {
            defer { try? handle.close() }
            _ = try? handle.seekToEnd()
            try? handle.write(contentsOf: data)
        } else {
            try? data.write(to: url, options: .atomic)
        }
    }

    // Show a vertical-resize cursor on hover (active even though the panel is never
    // key). Best-effort polish; the drag works regardless.
    override func updateTrackingAreas() {
        super.updateTrackingAreas()
        if let trackingAreaRef { removeTrackingArea(trackingAreaRef) }
        let area = NSTrackingArea(
            rect: bounds,
            options: [.mouseEnteredAndExited, .activeAlways, .inVisibleRect],
            owner: self,
            userInfo: nil
        )
        addTrackingArea(area)
        trackingAreaRef = area
    }

    override func mouseEntered(with event: NSEvent) { NSCursor.resizeUpDown.set() }
    override func mouseExited(with event: NSEvent) { NSCursor.arrow.set() }
}
