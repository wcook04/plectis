import AppKit
import Combine
import CoreGraphics
import Foundation

// MARK: - Interaction state machine (contract §6)

enum OverlayInteractionState: String, Equatable {
    /// nothing visible; normal mouse
    case hidden
    /// nodule only; restore without the console
    case peek
    /// full sheet, click-through; normal recording state
    case readThrough = "read_through"
    /// sheet + private border; Command held, pointer over sheet
    case armed
    /// full controls, fully interactive; pre-recording layout
    case arrange
}

/// Shared semantic scroll position across displays: which card is active and how
/// far through it (normalized 0..1). Mirrored as view + fraction, never raw pixels.
struct SemanticScrollPosition: Equatable {
    var cardIndex: Int
    var intraCardFraction: Double // 0..1

    static let start = SemanticScrollPosition(cardIndex: 0, intraCardFraction: 0)
}

/// Per-display presentation state. Geometry/opacity/enabled are per-display; the
/// semantic state (card, scroll, recipient) is shared and lives on the session.
struct PerDisplayPresentation: Equatable {
    var displayID: CGDirectDisplayID
    var enabled: Bool = true
    var opacity: Double = 0.30
    /// Saved cue-sheet frame; nil means "re-centre on the current display".
    var savedFrame: CGRect?
}

/// Per-display cue-sheet scroll geometry. Each screen measures independently;
/// the session keeps one canonical reading progress and projects it through the
/// local range for each display.
struct CueScrollMetrics: Equatable {
    var contentHeight: CGFloat
    var viewportHeight: CGFloat

    var maxOffset: CGFloat {
        max(0, contentHeight - viewportHeight)
    }
}

struct CueScrollRangeEstimator {
    static func estimatedContentHeight(
        compressedScript: [BeatCue],
        scriptBlocks: [ScriptBlock],
        verbatimLineCount: Int,
        textScale: CGFloat = 1
    ) -> CGFloat {
        let scale = textScale.clamped(OverlaySession.minCueTextScale, OverlaySession.maxCueTextScale)
        if !scriptBlocks.isEmpty {
            return 54 + CGFloat(scriptBlocks.count) * 48 * scale
        }

        if !compressedScript.isEmpty {
            var total: CGFloat = 54 // scroll padding and top breathing room
            total += 92 // made-for band
            if verbatimLineCount > 0 {
                total += 44 + CGFloat(verbatimLineCount) * 38 * scale
            }
            for beat in compressedScript {
                total += 36 // beat header
                total += CGFloat(max(beat.land.count, 1)) * 34 * scale
                total += CGFloat(beat.show.count) * 25 * scale
                if beat.limit != nil { total += 24 * scale }
                if beat.next != nil { total += 29 }
                total += 12 // stack spacing between beats
            }
            return total
        }

        return 0
    }
}

struct CueScrollMutationReceipt: Equatable {
    var displayID: CGDirectDisplayID
    var localMaxOffset: CGFloat
    var offsetBefore: CGFloat
    var offsetAfter: CGFloat
    var progressBefore: CGFloat
    var progressAfter: CGFloat
}

struct CueLineStepMutationReceipt: Equatable {
    var displayID: CGDirectDisplayID
    var localMaxOffset: CGFloat
    var lineHeight: CGFloat
    var measuredAnchorCount: Int
    var usedMeasuredAnchors: Bool
    var offsetBefore: CGFloat
    var offsetAfter: CGFloat
    var progressBefore: CGFloat
    var progressAfter: CGFloat
}

struct CueScrollEventReceipt: Codable, Equatable {
    var schema: String = "cue_scroll_event_receipt_v1"
    var stage: String
    var eventSource: String
    var physicalCommandDown: Bool
    var pointerInsideSheet: Bool
    var targetPanelID: UInt32?
    var targetPanelIgnoresMouseEvents: Bool?
    var eventEnteredPanelDispatch: Bool
    var consumedLocalEvent: Bool
    var eventWindowNumber: Int
    var eventModifiersRaw: UInt
    var rawDeltaY: Double
    var precise: Bool
    var directionInverted: Bool
    var localMaxOffset: Double
    var contentHeight: Double?
    var viewportHeight: Double?
    var scrollProgress: Double
    var offsetBefore: Double
    var offsetAfter: Double
    var renderedOffset: Double

    enum CodingKeys: String, CodingKey {
        case schema
        case stage
        case eventSource = "event_source"
        case physicalCommandDown = "physical_command_down"
        case pointerInsideSheet = "pointer_inside_sheet"
        case targetPanelID = "target_panel_id"
        case targetPanelIgnoresMouseEvents = "target_panel_ignores_mouse_events"
        case eventEnteredPanelDispatch = "event_entered_panel_dispatch"
        case consumedLocalEvent = "consumed_local_event"
        case eventWindowNumber = "event_window_number"
        case eventModifiersRaw = "event_modifiers_raw"
        case rawDeltaY = "raw_delta_y"
        case precise
        case directionInverted = "direction_inverted"
        case localMaxOffset = "local_max_offset"
        case contentHeight = "content_height"
        case viewportHeight = "viewport_height"
        case scrollProgress = "scroll_progress"
        case offsetBefore = "offset_before"
        case offsetAfter = "offset_after"
        case renderedOffset = "rendered_offset"
    }
}

struct CueScrollMonitorReceipt: Codable, Equatable {
    var schema: String = "cue_scroll_monitor_receipt_v0"
    var stage: String = "monitor_started"
    var globalRegistered: Bool
    var localRegistered: Bool

    enum CodingKeys: String, CodingKey {
        case schema
        case stage
        case globalRegistered = "global_registered"
        case localRegistered = "local_registered"
    }
}

struct CueScrollMetricsReceipt: Codable, Equatable {
    var schema: String = "cue_scroll_metrics_receipt_v0"
    var displayID: UInt32
    var contentHeight: Double
    var viewportHeight: Double
    var measuredMaxOffset: Double
    var fallbackMaxOffset: Double
    var effectiveMaxOffset: Double
    var selectedRecipientID: String?
    var compressedBeatCount: Int
    var scriptBlockCount: Int

    enum CodingKeys: String, CodingKey {
        case schema
        case displayID = "display_id"
        case contentHeight = "content_height"
        case viewportHeight = "viewport_height"
        case measuredMaxOffset = "measured_max_offset"
        case fallbackMaxOffset = "fallback_max_offset"
        case effectiveMaxOffset = "effective_max_offset"
        case selectedRecipientID = "selected_recipient_id"
        case compressedBeatCount = "compressed_beat_count"
        case scriptBlockCount = "script_block_count"
    }
}

/// The overlay session: the single owner of semantic + per-display state. All
/// panels observe this; geometry is independent, semantics are shared.
@MainActor
final class OverlaySession: ObservableObject {
    // Semantic state (shared across displays)
    @Published private(set) var bundle: RecipientCueBundle?
    @Published private(set) var selectedRecipientID: String?
    @Published var interactionState: OverlayInteractionState = .hidden
    @Published var scrollPosition: SemanticScrollPosition = .start
    /// When true, the overlay shows the compact glance card (a few cue words).
    /// The default is false because recipient recording needs the full scrollable
    /// run sheet, not just WHO / OPEN / ASK metadata.
    @Published var glanceMode: Bool = false

    // Per-display presentation
    @Published var perDisplay: [CGDirectDisplayID: PerDisplayPresentation] = [:]
    /// The display whose sheet is currently the armed scroll target (Command held,
    /// pointer over it), or nil. Read by CueSheetView to show the armed border.
    @Published var armedDisplayID: CGDirectDisplayID?

    // MARK: - Shared reading position + size
    //
    // Scrolling is driven by one canonical progress value, not each panel's native
    // gesture and not a single raw point range. Each display projects that progress
    // through its own measured content/viewport range. Height is shared too, so
    // dragging one panel's edge resizes both.

    /// Canonical reading position through the cue script, normalized 0...1.
    @Published private(set) var scrollProgress: CGFloat = 0
    /// Per-display measured scroll ranges. A transient zero on one display must not
    /// erase another display's ability to scroll.
    @Published private(set) var scrollMetricsByDisplay: [CGDirectDisplayID: CueScrollMetrics] = [:]
    /// Per-display line-top anchors measured from the rendered teleprompter body.
    /// Line stepping uses these absolute offsets first, falling back to a coarse
    /// font-scaled grid only while a view has not reported anchors yet.
    @Published private(set) var lineAnchorOffsetsByDisplay: [CGDirectDisplayID: [CGFloat]] = [:]
    /// Smallest cue-panel height. Content scrolls when the visible panel is
    /// smaller than the cue body, so this is only the drag floor.
    static let minSheetHeight: CGFloat = 72
    /// Practical drag ceiling for the cue panel. This is intentionally NOT tied to
    /// the current display height: the operator can oversize the sheet and rely on
    /// cue scrolling when only part of it is visible.
    static let defaultMaxSheetHeight: CGFloat = 1800
    /// Shared teleprompter width rails. The panel manager keeps the sheet centered,
    /// so width changes expand or contract both sides together.
    static let minSheetWidth: CGFloat = 320
    static let defaultMaxSheetWidth: CGFloat = 900
    static let defaultCueTextScale: CGFloat = 1.0
    nonisolated static let minCueTextScale: CGFloat = 0.72
    nonisolated static let maxCueTextScale: CGFloat = 1.42

    /// Shared panel height in points. Drag-to-resize writes this; both panels follow.
    @Published var sheetHeight: CGFloat = 320
    /// Shared panel width in points. A zero value means "use display default" until
    /// the panel manager sees the first screen and seeds a concrete centered width.
    @Published var sheetWidth: CGFloat = 0
    /// The live upper bound for `sheetHeight`. This is an absolute drag limit, not
    /// a "must fit on screen" rule; oversized sheets stay scrollable through the
    /// visible-viewport metrics below.
    @Published private(set) var maxSheetHeight: CGFloat = OverlaySession.defaultMaxSheetHeight
    @Published private(set) var maxSheetWidth: CGFloat = OverlaySession.defaultMaxSheetWidth
    /// Operator-controlled body text scale for the teleprompter.
    @Published private(set) var cueTextScale: CGFloat = OverlaySession.defaultCueTextScale
    /// Double-Command toggles this mode; while enabled, Up/Down move through the
    /// script on a stable cue-line grid instead of depending on raw wheel pixels.
    @Published var lineStepModeEnabled: Bool = false
    /// True while the edge is being dragged, so the manager resizes the sheets live
    /// and can defer full re-settling until the drag ends.
    @Published var isResizing: Bool = false
    /// Last qualified command-scroll receipt. Also written to a temp JSON file for
    /// shell-side live verification without touching take packages or recordings.
    @Published private(set) var lastScrollEventReceipt: CueScrollEventReceipt?
    @Published private(set) var lastScrollMonitorReceipt: CueScrollMonitorReceipt?
    @Published private(set) var lastScrollMetricsReceipt: CueScrollMetricsReceipt?
    /// Per-display portion of the cue sheet currently visible inside the display's
    /// usable frame. If a deliberately oversized panel extends below the display,
    /// scroll metrics use this visible height instead of the offscreen window height.
    @Published private(set) var visibleSheetHeightByDisplay: [CGDirectDisplayID: CGFloat] = [:]

    // Drift / safety
    @Published private(set) var loadedDeckSourceHash: String?
    @Published var lastError: String?

    /// True while a production take is recording; we must never switch recipients
    /// mid-recording.
    @Published var isRecording: Bool = false

    /// Set true by the controller while a passing exclusion receipt is current.
    @Published var exclusionReceiptCurrent: Bool = false

    /// Locks cue visibility for the active take after the take starts with a
    /// current passing exclusion receipt. Mid-take topology churn can stale the
    /// receipt, but must not make the operator lose the cue sheet in-flight.
    @Published var recordingCueVisibilityLocked: Bool = false

    private let userDefaultsKey = "RecipientCueOverlay.selectedRecipientID"
    private let glanceModeKey = "RecipientCueOverlay.glanceMode"
    private let glanceModePreferenceVersionKey = "RecipientCueOverlay.glanceModePreferenceVersion"
    private static let sheetWidthKey = "RecipientCueOverlay.sheetWidth"
    private static let cueTextScaleKey = "RecipientCueOverlay.cueTextScale"
    private static let fullRunSheetPreferenceVersion = 2

    init() {
        selectedRecipientID = UserDefaults.standard.string(forKey: userDefaultsKey)
        let defaults = UserDefaults.standard
        let savedVersion = defaults.integer(forKey: glanceModePreferenceVersionKey)
        if savedVersion < Self.fullRunSheetPreferenceVersion {
            glanceMode = false
            defaults.set(false, forKey: glanceModeKey)
            defaults.set(Self.fullRunSheetPreferenceVersion, forKey: glanceModePreferenceVersionKey)
        } else if defaults.object(forKey: glanceModeKey) != nil {
            glanceMode = defaults.bool(forKey: glanceModeKey)
        }
        if defaults.object(forKey: Self.sheetWidthKey) != nil {
            sheetWidth = CGFloat(defaults.double(forKey: Self.sheetWidthKey))
                .clamped(Self.minSheetWidth, Self.defaultMaxSheetWidth)
        }
        if defaults.object(forKey: Self.cueTextScaleKey) != nil {
            cueTextScale = CGFloat(defaults.double(forKey: Self.cueTextScaleKey))
                .clamped(Self.minCueTextScale, Self.maxCueTextScale)
        }
    }

    /// Flip the glance/full-teleprompter mode and remember the choice.
    func toggleGlanceMode() {
        glanceMode.toggle()
        lineAnchorOffsetsByDisplay = [:]
        UserDefaults.standard.set(glanceMode, forKey: glanceModeKey)
        UserDefaults.standard.set(Self.fullRunSheetPreferenceVersion, forKey: glanceModePreferenceVersionKey)
    }

    /// A compact "who they are" line for the glance card: the best available
    /// recipient identity, never fabricated (nil when the bundle carries none).
    var glanceIdentity: String? {
        firstNonEmptyGlance(
            bundle?.inserts.currentIdentity,
            bundle?.inserts.currentWork,
            bundle?.inserts.thesis,
            bundle?.inserts.workBridge
        )
    }

    /// The one bounded ask for the glance card.
    var glanceAsk: String? { firstNonEmptyGlance(bundle?.inserts.boundedQuestion) }

    /// The claim ceiling, surfaced small on the glance card so the operator does
    /// not overclaim live.
    var glanceLimit: String? { firstNonEmptyGlance(bundle?.inserts.claimCeiling) }

    private func firstNonEmptyGlance(_ values: String?...) -> String? {
        for value in values {
            if let value, !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                return value
            }
        }
        return nil
    }

    /// True for a general/theme deliverable (vs a person recipient). Drives the
    /// theme glance card built from the spine + doctrine instead of persona fields.
    var isGeneralDeliverable: Bool { bundle?.deck.schema == "general_run_sheet_overlay_deck_v0" }

    /// The first-principles spine (theme deliverables only) — the glanceable mental
    /// model. Nil for person recipients.
    var spine: FirstPrinciplesSpine? { bundle?.spine }

    /// The one public law the whole clip demonstrates (theme deliverables).
    var doctrineLaw: DoctrineFlash? { bundle?.doctrineThroughLine }

    /// The cockpit frontend view to open on camera for this theme (e.g.
    /// "/station/agent-observability Agent Trace"). Shown on the glance card.
    var onCameraView: String? { bundle?.onCameraView }

    var cards: [CueCard] { bundle?.cards ?? [] }

    /// The recipient's full spoken script (run-sheet mic surface) as renderable
    /// blocks. This is the primary full-cues teleprompter surface.
    var scriptBlocks: [ScriptBlock] { bundle?.scriptBlocks ?? [] }

    /// The compressed cue-card beats — fallback for full-cues mode and source for
    /// the compact glance card.
    var compressedScript: [BeatCue] { bundle?.compressedScript ?? [] }

    /// The verbatim `SAY:` lines (exact wording), in order.
    var verbatimLines: [String] { bundle?.verbatimLines ?? [] }

    var activeCard: CueCard? {
        let cards = self.cards
        guard cards.indices.contains(scrollPosition.cardIndex) else { return nil }
        return cards[scrollPosition.cardIndex]
    }

    var recipientName: String { bundle?.recipientName ?? selectedRecipientID ?? "No recipient" }

    /// Load and atomically apply a recipient. Refuses mid-recording.
    /// Returns true on success.
    @discardableResult
    func selectRecipient(_ recipientID: String, repoRoot: URL) -> Bool {
        guard !isRecording else {
            lastError = "Cannot switch recipient while recording."
            return false
        }
        do {
            let loaded = try RecipientCueDeckLoader.load(repoRoot: repoRoot, recipientID: recipientID)
            apply(bundle: loaded)
            return true
        } catch {
            lastError = "Deck load failed for \(recipientID): \(error)"
            return false
        }
    }

    /// Re-load the currently selected recipient (e.g. on launch). No-op if none.
    func reloadSelectedIfNeeded(repoRoot: URL) {
        guard bundle == nil, let id = selectedRecipientID else { return }
        _ = selectRecipient(id, repoRoot: repoRoot)
    }

    private func apply(bundle: RecipientCueBundle) {
        self.bundle = bundle
        selectedRecipientID = bundle.recipientID
        loadedDeckSourceHash = bundle.deckSourceHash
        // Verify deck source hash binding: if the deck recomputes to a different
        // value than recorded, surface it (drift) but still show the deck.
        if let recorded = bundle.deck.sourceOverlayDeckHash, recorded != bundle.deckSourceHash {
            lastError = "Deck hash drift for \(bundle.recipientID)."
        } else {
            lastError = nil
        }
        // Reset to the opening insert / first card.
        resetReadingPosition(clearMetrics: true)
        UserDefaults.standard.set(bundle.recipientID, forKey: userDefaultsKey)
    }

    // MARK: - Shared progress scroll + resize

    /// Advance the canonical reading progress by a point delta measured on the
    /// active display. Other displays mirror the same progress through their own
    /// local geometry.
    @discardableResult
    func scroll(by advance: CGFloat, on displayID: CGDirectDisplayID) -> CueScrollMutationReceipt {
        let before = scrollProgress
        let maximum = maxOffset(for: displayID)
        let offsetBefore = before * maximum
        guard advance.isFinite, maximum > 0 else {
            return CueScrollMutationReceipt(
                displayID: displayID,
                localMaxOffset: maximum,
                offsetBefore: offsetBefore,
                offsetAfter: offsetBefore,
                progressBefore: before,
                progressAfter: scrollProgress
            )
        }
        let localOffset = scrollProgress * maximum
        setScrollProgress((localOffset + advance) / maximum)
        let offsetAfter = scrollProgress * maximum
        return CueScrollMutationReceipt(
            displayID: displayID,
            localMaxOffset: maximum,
            offsetBefore: offsetBefore,
            offsetAfter: offsetAfter,
            progressBefore: before,
            progressAfter: scrollProgress
        )
    }

    @discardableResult
    func stepCueLine(_ direction: CueLineStepDirection, on displayID: CGDirectDisplayID) -> CueLineStepMutationReceipt {
        let before = scrollProgress
        let maximum = maxOffset(for: displayID)
        let offsetBefore = before * maximum
        let lineHeight = CueLineStepNavigator.lineHeight(textScale: cueTextScale)
        let measuredAnchors = lineAnchorOffsetsByDisplay[displayID] ?? []
        guard maximum > 0 else {
            return CueLineStepMutationReceipt(
                displayID: displayID,
                localMaxOffset: maximum,
                lineHeight: lineHeight,
                measuredAnchorCount: measuredAnchors.count,
                usedMeasuredAnchors: false,
                offsetBefore: offsetBefore,
                offsetAfter: offsetBefore,
                progressBefore: before,
                progressAfter: scrollProgress
            )
        }
        let measuredTarget = CueLineAnchorNavigator().targetOffset(
            currentOffset: offsetBefore,
            maxOffset: maximum,
            anchors: measuredAnchors,
            direction: direction
        )
        let target = measuredTarget ?? CueLineStepNavigator().targetOffset(
            currentOffset: offsetBefore,
            maxOffset: maximum,
            lineHeight: lineHeight,
            direction: direction
        )
        setScrollProgress(target / maximum)
        let offsetAfter = scrollProgress * maximum
        return CueLineStepMutationReceipt(
            displayID: displayID,
            localMaxOffset: maximum,
            lineHeight: lineHeight,
            measuredAnchorCount: measuredAnchors.count,
            usedMeasuredAnchors: measuredTarget != nil,
            offsetBefore: offsetBefore,
            offsetAfter: offsetAfter,
            progressBefore: before,
            progressAfter: scrollProgress
        )
    }

    /// Current display-local point offset for rendering.
    func offset(for displayID: CGDirectDisplayID) -> CGFloat {
        scrollProgress * maxOffset(for: displayID)
    }

    func maxOffset(for displayID: CGDirectDisplayID) -> CGFloat {
        let measured = scrollMetricsByDisplay[displayID]?.maxOffset ?? 0
        if measured > 1 { return measured }
        return estimatedFallbackMaxOffset(for: displayID)
    }

    func scrollMetrics(for displayID: CGDirectDisplayID) -> CueScrollMetrics? {
        scrollMetricsByDisplay[displayID]
    }

    func setLineAnchors(for displayID: CGDirectDisplayID, offsets: [CGFloat]) {
        let next = CueLineAnchorNavigator.normalizedOffsets(offsets)
        let stored = next.count >= 2 ? next : []
        if stored.isEmpty {
            if lineAnchorOffsetsByDisplay[displayID] != nil {
                lineAnchorOffsetsByDisplay.removeValue(forKey: displayID)
            }
            return
        }
        guard lineAnchorOffsetsByDisplay[displayID] != stored else { return }
        lineAnchorOffsetsByDisplay[displayID] = stored
    }

    /// Reported by each view once it has measured its content + viewport.
    func setContentMetrics(for displayID: CGDirectDisplayID, contentHeight: CGFloat, viewportHeight: CGFloat) {
        guard contentHeight.isFinite, viewportHeight.isFinite else { return }
        guard contentHeight > 1, viewportHeight > 1 else { return }
        let next = CueScrollMetrics(
            contentHeight: contentHeight,
            viewportHeight: viewportHeight
        )
        if scrollMetricsByDisplay[displayID] != next {
            scrollMetricsByDisplay[displayID] = next
            recordScrollMetricsReceipt(
                CueScrollMetricsReceipt(
                    displayID: UInt32(displayID),
                    contentHeight: Double(next.contentHeight),
                    viewportHeight: Double(next.viewportHeight),
                    measuredMaxOffset: Double(next.maxOffset),
                    fallbackMaxOffset: Double(estimatedFallbackMaxOffset(viewportHeight: next.viewportHeight)),
                    effectiveMaxOffset: Double(maxOffset(for: displayID)),
                    selectedRecipientID: selectedRecipientID,
                    compressedBeatCount: compressedScript.count,
                    scriptBlockCount: scriptBlocks.count
                )
            )
        }
    }

    private func estimatedFallbackMaxOffset(for displayID: CGDirectDisplayID) -> CGFloat {
        let viewport = scrollMetricsByDisplay[displayID]?.viewportHeight ?? max(0, sheetHeight - 62)
        return estimatedFallbackMaxOffset(viewportHeight: viewport)
    }

    private func estimatedFallbackMaxOffset(viewportHeight: CGFloat) -> CGFloat {
        guard bundle != nil else { return 0 }
        let estimatedContentHeight = CueScrollRangeEstimator.estimatedContentHeight(
            compressedScript: compressedScript,
            scriptBlocks: scriptBlocks,
            verbatimLineCount: verbatimLines.count,
            textScale: cueTextScale
        )
        return max(0, estimatedContentHeight - viewportHeight)
    }

    func recordScrollEventReceipt(_ receipt: CueScrollEventReceipt) {
        lastScrollEventReceipt = receipt
        let url = URL(fileURLWithPath: "<host-temp>/demo-take-console-last-scroll.json")
        let streamURL = URL(fileURLWithPath: "<host-temp>/demo-take-console-scroll-events.jsonl")
        do {
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            let data = try encoder.encode(receipt)
            try data.write(to: url, options: .atomic)

            let lineEncoder = JSONEncoder()
            lineEncoder.outputFormatting = [.sortedKeys]
            var line = try lineEncoder.encode(receipt)
            line.append(0x0A)
            if FileManager.default.fileExists(atPath: streamURL.path),
               let handle = try? FileHandle(forWritingTo: streamURL) {
                try handle.seekToEnd()
                try handle.write(contentsOf: line)
                try handle.close()
            } else {
                try line.write(to: streamURL, options: .atomic)
            }
        } catch {
            // Best-effort diagnostic only; scrolling must never fail because the
            // shell-side receipt could not be written.
        }
    }

    func recordScrollMonitorReceipt(_ receipt: CueScrollMonitorReceipt) {
        lastScrollMonitorReceipt = receipt
        let url = URL(fileURLWithPath: "<host-temp>/demo-take-console-scroll-monitor.json")
        do {
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            let data = try encoder.encode(receipt)
            try data.write(to: url, options: .atomic)
        } catch {
            // Best-effort diagnostic only.
        }
    }

    func recordScrollMetricsReceipt(_ receipt: CueScrollMetricsReceipt) {
        lastScrollMetricsReceipt = receipt
        let url = URL(fileURLWithPath: "<host-temp>/demo-take-console-scroll-metrics.json")
        do {
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            let data = try encoder.encode(receipt)
            try data.write(to: url, options: .atomic)
        } catch {
            // Best-effort diagnostic only.
        }
    }

    /// Drag-to-resize writes this; clamped to the shared readable band.
    func setSheetHeight(_ h: CGFloat) {
        let c = h.clamped(Self.minSheetHeight, maxSheetHeight)
        if abs(c - sheetHeight) > 0.5 { sheetHeight = c }
    }

    func setSheetWidth(_ w: CGFloat) {
        let c = w.clamped(Self.minSheetWidth, maxSheetWidth)
        if abs(c - sheetWidth) > 0.5 {
            sheetWidth = c
            lineAnchorOffsetsByDisplay = [:]
            UserDefaults.standard.set(Double(c), forKey: Self.sheetWidthKey)
        }
    }

    /// Update the absolute height ceiling and pull the current height back under it.
    func setMaxSheetHeight(_ proposed: CGFloat) {
        let next = max(Self.minSheetHeight, proposed)
        guard abs(next - maxSheetHeight) > 0.5 else { return }
        maxSheetHeight = next
        setSheetHeight(sheetHeight) // re-clamp the current height under the new ceiling
    }

    func setMaxSheetWidth(_ proposed: CGFloat) {
        let next = max(Self.minSheetWidth, proposed)
        guard abs(next - maxSheetWidth) > 0.5 else {
            if sheetWidth > 0 { setSheetWidth(sheetWidth) }
            return
        }
        maxSheetWidth = next
        if sheetWidth > 0 { setSheetWidth(sheetWidth) }
    }

    func setCueTextScale(_ scale: CGFloat) {
        let next = scale.clamped(Self.minCueTextScale, Self.maxCueTextScale)
        guard abs(next - cueTextScale) > 0.005 else { return }
        cueTextScale = next
        UserDefaults.standard.set(Double(next), forKey: Self.cueTextScaleKey)
        scrollMetricsByDisplay = [:]
        lineAnchorOffsetsByDisplay = [:]
    }

    func adjustCueTextScale(by delta: CGFloat) {
        setCueTextScale(cueTextScale + delta)
    }

    func toggleLineStepMode() {
        lineStepModeEnabled.toggle()
    }

    func setVisibleSheetHeight(_ height: CGFloat, for displayID: CGDirectDisplayID) {
        guard height.isFinite else { return }
        let next = max(0, height)
        guard abs((visibleSheetHeightByDisplay[displayID] ?? -1) - next) > 0.5 else { return }
        visibleSheetHeightByDisplay[displayID] = next
    }

    func visibleSheetHeight(for displayID: CGDirectDisplayID) -> CGFloat? {
        visibleSheetHeightByDisplay[displayID]
    }

    func effectiveScrollViewportHeight(for displayID: CGDirectDisplayID, measuredViewportHeight: CGFloat) -> CGFloat {
        guard measuredViewportHeight.isFinite, measuredViewportHeight > 1 else { return measuredViewportHeight }
        guard let visibleSheetHeight = visibleSheetHeight(for: displayID), visibleSheetHeight > 1 else {
            return measuredViewportHeight
        }
        let fixedPanelChrome = max(0, sheetHeight - measuredViewportHeight)
        let visibleViewport = max(1, visibleSheetHeight - fixedPanelChrome)
        return min(measuredViewportHeight, visibleViewport)
    }

    // MARK: - Semantic scroll (shared across displays)

    /// Advance the shared semantic scroll by a normalized delta. This keeps older
    /// sidecar/navigation hooks tied to the same canonical reading progress.
    func advanceScroll(byFraction delta: Double) {
        setScrollProgress(scrollProgress + CGFloat(delta))
    }

    func goToCard(_ index: Int) {
        guard cards.indices.contains(index) else { return }
        if cards.count <= 1 {
            setScrollProgress(0)
        } else {
            setScrollProgress(CGFloat(index) / CGFloat(cards.count - 1))
        }
    }

    func nextCard() { goToCard(min(scrollPosition.cardIndex + 1, max(cards.count - 1, 0))) }
    func previousCard() { goToCard(max(scrollPosition.cardIndex - 1, 0)) }

    private func resetReadingPosition(clearMetrics: Bool) {
        scrollProgress = 0
        scrollPosition = .start
        if clearMetrics { scrollMetricsByDisplay = [:] }
        lineAnchorOffsetsByDisplay = [:]
    }

    private func setScrollProgress(_ raw: CGFloat) {
        let next = raw.clamped(0, 1)
        guard next != scrollProgress else { return }
        scrollProgress = next
        syncSemanticPositionFromProgress()
    }

    private func syncSemanticPositionFromProgress() {
        let cardCount = cards.count
        guard cardCount > 0 else {
            if scrollPosition != .start { scrollPosition = .start }
            return
        }
        if cardCount == 1 {
            let next = SemanticScrollPosition(cardIndex: 0, intraCardFraction: Double(scrollProgress))
            if scrollPosition != next { scrollPosition = next }
            return
        }
        let scaled = Double(scrollProgress) * Double(cardCount - 1)
        let index = min(Int(scaled.rounded(.down)), cardCount - 1)
        let fraction = index == cardCount - 1 ? 1.0 : scaled - Double(index)
        let next = SemanticScrollPosition(cardIndex: index, intraCardFraction: fraction)
        if scrollPosition != next { scrollPosition = next }
    }

    // MARK: - Per-display presentation

    /// Ensure a presentation entry exists for each current display id; drop entries
    /// for displays that no longer exist; preserve saved geometry where it survives.
    func reconcileDisplays(_ displayIDs: [CGDirectDisplayID]) {
        var next: [CGDirectDisplayID: PerDisplayPresentation] = [:]
        for id in displayIDs {
            if let existing = perDisplay[id] {
                next[id] = existing
            } else {
                next[id] = PerDisplayPresentation(displayID: id)
            }
        }
        perDisplay = next
    }

    func presentation(for displayID: CGDirectDisplayID) -> PerDisplayPresentation {
        perDisplay[displayID] ?? PerDisplayPresentation(displayID: displayID)
    }

    func setSavedFrame(_ frame: CGRect?, for displayID: CGDirectDisplayID) {
        var p = presentation(for: displayID)
        p.savedFrame = frame
        perDisplay[displayID] = p
    }

    // MARK: - State transitions

    func show() {
        guard bundle != nil else {
            lastError = "Select a recipient before showing the overlay."
            return
        }
        // Wake the full sheet from either fully hidden OR peek (nodule-only). The
        // old guard only fired from `.hidden`, so "Show cues" after "Hide cues"
        // (which goes to `.peek`) silently did nothing.
        if interactionState == .hidden || interactionState == .peek {
            interactionState = .readThrough
        }
    }

    func hide() {
        guard !isRecording else {
            lastError = "Cue hide ignored while recording."
            return
        }
        interactionState = .hidden
    }

    func peek() {
        guard !isRecording else {
            lastError = "Cue hide ignored while recording."
            return
        }
        interactionState = .peek
    }

    func setArrange(_ on: Bool) {
        interactionState = on ? .arrange : (bundle != nil ? .readThrough : .hidden)
    }
}

extension CGFloat {
    func clamped(_ lo: CGFloat, _ hi: CGFloat) -> CGFloat {
        Swift.min(Swift.max(self, lo), Swift.max(lo, hi))
    }
}
