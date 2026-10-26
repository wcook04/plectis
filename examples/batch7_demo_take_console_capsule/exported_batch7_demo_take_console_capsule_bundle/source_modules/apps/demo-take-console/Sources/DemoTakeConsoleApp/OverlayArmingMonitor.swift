import AppKit
@preconcurrency import CoreGraphics

// MARK: - Command-scroll arming (contract §6)
//
// Command is a private input mode, not an app-focus requirement. Local/global
// scroll monitors own cue movement; the polling arm state only provides the
// border/click-through presentation while Command is held.

struct CueScrollDeltaReducer {
    /// Mouse wheels report coarse line ticks when precise deltas are unavailable.
    /// Use a cue-text line height rather than an arbitrary multiplier.
    static let coarseWheelLineHeight: CGFloat = 28

    func advance(rawDeltaY: CGFloat, hasPreciseScrollingDeltas: Bool) -> CGFloat {
        guard rawDeltaY.isFinite else { return 0 }
        let points = hasPreciseScrollingDeltas
            ? rawDeltaY
            : rawDeltaY * Self.coarseWheelLineHeight
        // AppKit's vertical scroll delta is inverted relative to document advance:
        // a downward-reading gesture should increase the canonical cue position.
        return -points
    }

    func rawDeltaY(for event: NSEvent) -> CGFloat {
        event.scrollingDeltaY != 0 ? event.scrollingDeltaY : event.deltaY
    }

    func advance(for event: NSEvent) -> CGFloat {
        advance(
            rawDeltaY: rawDeltaY(for: event),
            hasPreciseScrollingDeltas: event.hasPreciseScrollingDeltas
        )
    }
}

enum CueScrollObservationSource: String {
    case local
    case global
    case eventTap = "event_tap"
    case keyStatePoll = "key_state_poll"
}

struct CueScrollObservationDecision: Equatable {
    var shouldMutate: Bool
    var consumeLocalEvent: Bool
}

struct CueScrollObservationReducer {
    func decision(
        source: CueScrollObservationSource,
        overlayLive: Bool,
        commandPresent: Bool,
        displayID: CGDirectDisplayID?
    ) -> CueScrollObservationDecision {
        let shouldMutate = overlayLive && commandPresent && displayID != nil
        return CueScrollObservationDecision(
            shouldMutate: shouldMutate,
            consumeLocalEvent: shouldMutate && source == .local
        )
    }
}

struct CueScrollObservationLogPolicy {
    func shouldRecordObservation(
        decision: CueScrollObservationDecision,
        commandPresent: Bool,
        displayID: CGDirectDisplayID?
    ) -> Bool {
        !decision.shouldMutate && (commandPresent || displayID != nil)
    }
}

enum CueLineStepDirection: Int, Equatable, Hashable {
    case up = -1
    case down = 1
}

struct CueLineStepNavigator {
    static func lineHeight(textScale: CGFloat) -> CGFloat {
        max(18, CueScrollDeltaReducer.coarseWheelLineHeight * textScale)
    }

    func targetOffset(
        currentOffset: CGFloat,
        maxOffset: CGFloat,
        lineHeight: CGFloat,
        direction: CueLineStepDirection
    ) -> CGFloat {
        guard currentOffset.isFinite, maxOffset.isFinite, lineHeight.isFinite else { return 0 }
        guard maxOffset > 0, lineHeight > 0 else { return 0 }
        let currentLine = (currentOffset / lineHeight).rounded(.toNearestOrAwayFromZero)
        let targetLine = currentLine + CGFloat(direction.rawValue)
        return (targetLine * lineHeight).clamped(0, maxOffset)
    }
}

struct CueLineAnchorNavigator {
    static let defaultTopMargin: CGFloat = 4

    var topMargin: CGFloat = Self.defaultTopMargin

    static func normalizedOffsets(_ offsets: [CGFloat]) -> [CGFloat] {
        let sorted = offsets
            .filter { $0.isFinite && $0 >= 0 }
            .sorted()
        var normalized: [CGFloat] = []
        for offset in sorted {
            if let last = normalized.last, abs(last - offset) < 0.5 { continue }
            normalized.append(offset)
        }
        return normalized
    }

    func targetOffset(
        currentOffset: CGFloat,
        maxOffset: CGFloat,
        anchors rawAnchors: [CGFloat],
        direction: CueLineStepDirection
    ) -> CGFloat? {
        guard currentOffset.isFinite, maxOffset.isFinite, maxOffset > 0 else { return nil }
        let anchors = Self.normalizedOffsets(rawAnchors)
        guard anchors.count >= 2 else { return nil }

        let readingLineY = currentOffset + max(0, topMargin)
        let baseIndex = nearestAnchorIndex(to: readingLineY, anchors: anchors)
        let targetIndex = baseIndex + direction.rawValue
        guard targetIndex >= 0 else { return 0 }
        guard targetIndex < anchors.count else { return maxOffset }
        return (anchors[targetIndex] - max(0, topMargin)).clamped(0, maxOffset)
    }

    private func nearestAnchorIndex(to y: CGFloat, anchors: [CGFloat]) -> Int {
        var bestIndex = 0
        var bestDistance = CGFloat.greatestFiniteMagnitude
        for (index, anchor) in anchors.enumerated() {
            let distance = abs(anchor - y)
            if distance < bestDistance {
                bestDistance = distance
                bestIndex = index
            }
        }
        return bestIndex
    }
}

struct CommandDoubleTapDetector {
    static let defaultWindow: TimeInterval = 0.36
    static let leftCommandKeyCode: UInt16 = 55
    static let rightCommandKeyCode: UInt16 = 54

    var doubleTapWindow: TimeInterval = Self.defaultWindow
    private(set) var commandDown = false
    private(set) var lastCommandTapAt: TimeInterval?

    static func isCommandKeyCode(_ keyCode: UInt16) -> Bool {
        keyCode == leftCommandKeyCode || keyCode == rightCommandKeyCode
    }

    mutating func record(commandPresent: Bool, keyCode: UInt16, timestamp: TimeInterval) -> Bool {
        guard commandPresent else {
            commandDown = false
            if let lastCommandTapAt, timestamp - lastCommandTapAt > doubleTapWindow {
                self.lastCommandTapAt = nil
            }
            return false
        }
        guard Self.isCommandKeyCode(keyCode) || !commandDown else { return false }
        guard !commandDown else { return false }

        commandDown = true
        if let lastCommandTapAt, timestamp - lastCommandTapAt <= doubleTapWindow {
            self.lastCommandTapAt = nil
            return true
        }
        lastCommandTapAt = timestamp
        return false
    }
}

struct CommandFlagChangeReducer {
    func commandPresent(cgFlags: CGEventFlags) -> Bool {
        cgFlags.contains(.maskCommand)
    }

    func timestampSeconds(cgTimestamp: CGEventTimestamp) -> TimeInterval {
        Double(cgTimestamp) / 1_000_000_000
    }

    func keyCode(cgKeyCode: Int64) -> UInt16 {
        UInt16(clamping: cgKeyCode)
    }
}

struct CommandStatePollReducer {
    private(set) var lastCommandPresent: Bool?

    mutating func observe(
        snapshot: CommandKeyStateSnapshot,
        timestamp: TimeInterval,
        detector: inout CommandDoubleTapDetector
    ) -> Bool {
        observe(
            commandPresent: snapshot.commandPresent,
            timestamp: timestamp,
            detector: &detector
        )
    }

    mutating func observe(
        commandPresent: Bool,
        timestamp: TimeInterval,
        detector: inout CommandDoubleTapDetector
    ) -> Bool {
        guard let previous = lastCommandPresent else {
            lastCommandPresent = commandPresent
            return false
        }
        guard previous != commandPresent else { return false }
        lastCommandPresent = commandPresent
        return detector.record(
            commandPresent: commandPresent,
            keyCode: commandPresent ? CommandDoubleTapDetector.leftCommandKeyCode : 0,
            timestamp: timestamp
        )
    }

    mutating func reset() {
        lastCommandPresent = nil
    }
}

struct CommandKeyStateSnapshot: Equatable {
    var flagsCommandPresent: Bool
    var leftCommandDown: Bool
    var rightCommandDown: Bool

    var commandPresent: Bool {
        flagsCommandPresent || leftCommandDown || rightCommandDown
    }
}

struct CueLineStepKeyReducer {
    static let minusKeyCode: UInt16 = 27
    static let keypadMinusKeyCode: UInt16 = 78
    static let upArrowKeyCode: UInt16 = 126
    // macOS reports the physical + key as ANSI equals; polling sees the key, not Shift.
    static let plusKeyCode: UInt16 = 24
    static let keypadPlusKeyCode: UInt16 = 69
    static let downArrowKeyCode: UInt16 = 125
    static let upStepKeyCodes: Set<UInt16> = [minusKeyCode, keypadMinusKeyCode, upArrowKeyCode]
    static let downStepKeyCodes: Set<UInt16> = [plusKeyCode, keypadPlusKeyCode, downArrowKeyCode]

    func direction(for keyCode: UInt16) -> CueLineStepDirection? {
        if Self.upStepKeyCodes.contains(keyCode) { return .up }
        if Self.downStepKeyCodes.contains(keyCode) { return .down }
        return nil
    }
}

struct CueLineStepKeyStateSnapshot: Equatable {
    var upStepKeyDown: Bool
    var downStepKeyDown: Bool
}

struct CueLineStepKeyStatePollReducer {
    private(set) var lastUpStepKeyDown = false
    private(set) var lastDownStepKeyDown = false

    mutating func observe(snapshot: CueLineStepKeyStateSnapshot) -> CueLineStepDirection? {
        defer {
            lastUpStepKeyDown = snapshot.upStepKeyDown
            lastDownStepKeyDown = snapshot.downStepKeyDown
        }
        if snapshot.downStepKeyDown, !lastDownStepKeyDown { return .down }
        if snapshot.upStepKeyDown, !lastUpStepKeyDown { return .up }
        return nil
    }

    mutating func reset() {
        lastUpStepKeyDown = false
        lastDownStepKeyDown = false
    }
}

struct CueLineStepDuplicateGate {
    static let defaultMinimumInterval: TimeInterval = 0.08

    var minimumInterval: TimeInterval = Self.defaultMinimumInterval
    private var lastAcceptedAtByDirection: [CueLineStepDirection: TimeInterval] = [:]

    mutating func shouldAccept(direction: CueLineStepDirection, timestamp: TimeInterval) -> Bool {
        guard timestamp.isFinite else { return true }
        if let lastAcceptedAt = lastAcceptedAtByDirection[direction],
           timestamp - lastAcceptedAt < minimumInterval {
            return false
        }
        lastAcceptedAtByDirection[direction] = timestamp
        return true
    }

    mutating func reset() {
        lastAcceptedAtByDirection = [:]
    }
}

struct CueLineStepObservationDecision: Equatable {
    var shouldMutate: Bool
    var consumeLocalEvent: Bool
}

struct CueLineStepObservationReducer {
    func decision(
        source: CueScrollObservationSource,
        overlayLive: Bool,
        lineStepModeEnabled: Bool,
        direction: CueLineStepDirection?,
        displayID: CGDirectDisplayID?
    ) -> CueLineStepObservationDecision {
        let shouldMutate = overlayLive && lineStepModeEnabled && direction != nil && displayID != nil
        let shouldConsume = overlayLive
            && lineStepModeEnabled
            && direction != nil
            && (source == .local || source == .eventTap)
        return CueLineStepObservationDecision(
            shouldMutate: shouldMutate,
            consumeLocalEvent: shouldConsume
        )
    }
}

struct KeyboardStateSnapshot: Equatable {
    var command: CommandKeyStateSnapshot
    var lineStep: CueLineStepKeyStateSnapshot
}

struct KeyboardStateSnapshotSampler {
    func snapshot() -> KeyboardStateSnapshot {
        KeyboardStateSnapshot(
            command: CommandKeyStateSnapshot(
                flagsCommandPresent: commandFlagsPresent(),
                leftCommandDown: keyDown(CommandDoubleTapDetector.leftCommandKeyCode),
                rightCommandDown: keyDown(CommandDoubleTapDetector.rightCommandKeyCode)
            ),
            lineStep: CueLineStepKeyStateSnapshot(
                upStepKeyDown: keyDown(anyOf: CueLineStepKeyReducer.upStepKeyCodes),
                downStepKeyDown: keyDown(anyOf: CueLineStepKeyReducer.downStepKeyCodes)
            )
        )
    }

    private func commandFlagsPresent() -> Bool {
        CGEventSource.flagsState(.hidSystemState).contains(.maskCommand)
            || CGEventSource.flagsState(.combinedSessionState).contains(.maskCommand)
    }

    private func keyDown(_ keyCode: UInt16) -> Bool {
        CGEventSource.keyState(.hidSystemState, key: CGKeyCode(keyCode))
            || CGEventSource.keyState(.combinedSessionState, key: CGKeyCode(keyCode))
    }

    private func keyDown(anyOf keyCodes: Set<UInt16>) -> Bool {
        keyCodes.contains { keyDown($0) }
    }
}

struct KeyboardEventTapConfiguration: Equatable {
    var location: CGEventTapLocation
    var placement: CGEventTapPlacement
    var options: CGEventTapOptions

    var canSuppressEvents: Bool {
        options != .listenOnly
    }

    static let backgroundFirstCandidates: [KeyboardEventTapConfiguration] = [
        KeyboardEventTapConfiguration(
            location: .cgSessionEventTap,
            placement: .headInsertEventTap,
            options: .defaultTap
        ),
        KeyboardEventTapConfiguration(
            location: .cgSessionEventTap,
            placement: .headInsertEventTap,
            options: .listenOnly
        ),
        KeyboardEventTapConfiguration(
            location: .cghidEventTap,
            placement: .headInsertEventTap,
            options: .listenOnly
        ),
    ]
}

@MainActor
final class OverlayArmingMonitor {
    private weak var panelManager: CueOverlayPanelManager?
    private let session: OverlaySession
    private let scrollReducer = CueScrollDeltaReducer()
    private let observationReducer = CueScrollObservationReducer()
    private let logPolicy = CueScrollObservationLogPolicy()
    private let commandFlagReducer = CommandFlagChangeReducer()
    private let lineStepKeyReducer = CueLineStepKeyReducer()
    private let lineStepObservationReducer = CueLineStepObservationReducer()
    private let keyboardStateSampler = KeyboardStateSnapshotSampler()
    private var doubleCommandDetector = CommandDoubleTapDetector()
    private var commandStatePollReducer = CommandStatePollReducer()
    private var lineStepKeyStatePollReducer = CueLineStepKeyStatePollReducer()
    private var lineStepDuplicateGate = CueLineStepDuplicateGate()

    private var armingPollTimer: DispatchSourceTimer?
    private var keyboardPollingActivity: (any NSObjectProtocol)?
    private var globalScrollMonitor: Any?
    private var localScrollMonitor: Any?
    private var globalFlagsMonitor: Any?
    private var localFlagsMonitor: Any?
    private var globalKeyMonitor: Any?
    private var localKeyMonitor: Any?
    private var keyboardEventTap: CFMachPort?
    private var keyboardEventTapSource: CFRunLoopSource?
    private var keyboardEventTapCanSuppress = false
    private var commandHeld = false

    init(session: OverlaySession, panelManager: CueOverlayPanelManager) {
        self.session = session
        self.panelManager = panelManager
    }

    func start() {
        stop()
        globalScrollMonitor = NSEvent.addGlobalMonitorForEvents(matching: .scrollWheel) { [weak self] event in
            MainActor.assumeIsolated {
                _ = self?.handleObservedScroll(event, source: .global)
            }
        }
        localScrollMonitor = NSEvent.addLocalMonitorForEvents(matching: .scrollWheel) { [weak self] event in
            var consumed = false
            MainActor.assumeIsolated {
                guard let self else { return }
                consumed = self.handleObservedScroll(event, source: .local)
            }
            return consumed ? nil : event
        }
        installKeyboardEventTap()
        installKeyboardFallbackMonitors()
        session.recordScrollMonitorReceipt(
            CueScrollMonitorReceipt(
                globalRegistered: globalScrollMonitor != nil,
                localRegistered: localScrollMonitor != nil
            )
        )

        beginKeyboardPollingActivity()
        let timer = DispatchSource.makeTimerSource(queue: .main)
        timer.schedule(deadline: .now(), repeating: .milliseconds(8), leeway: .milliseconds(1))
        timer.setEventHandler { [weak self] in
            Task { @MainActor [weak self] in
                self?.pollArmingState()
            }
        }
        timer.resume()
        armingPollTimer = timer
    }

    func stop() {
        if let globalScrollMonitor {
            NSEvent.removeMonitor(globalScrollMonitor)
            self.globalScrollMonitor = nil
        }
        if let localScrollMonitor {
            NSEvent.removeMonitor(localScrollMonitor)
            self.localScrollMonitor = nil
        }
        if let keyboardEventTapSource {
            CFRunLoopRemoveSource(CFRunLoopGetMain(), keyboardEventTapSource, .commonModes)
            self.keyboardEventTapSource = nil
        }
        if let keyboardEventTap {
            CFMachPortInvalidate(keyboardEventTap)
            self.keyboardEventTap = nil
        }
        keyboardEventTapCanSuppress = false
        if let globalFlagsMonitor {
            NSEvent.removeMonitor(globalFlagsMonitor)
            self.globalFlagsMonitor = nil
        }
        if let localFlagsMonitor {
            NSEvent.removeMonitor(localFlagsMonitor)
            self.localFlagsMonitor = nil
        }
        if let globalKeyMonitor {
            NSEvent.removeMonitor(globalKeyMonitor)
            self.globalKeyMonitor = nil
        }
        if let localKeyMonitor {
            NSEvent.removeMonitor(localKeyMonitor)
            self.localKeyMonitor = nil
        }
        armingPollTimer?.cancel()
        armingPollTimer = nil
        endKeyboardPollingActivity()
        commandHeld = false
        commandStatePollReducer.reset()
        lineStepKeyStatePollReducer.reset()
        lineStepDuplicateGate.reset()
        session.lineStepModeEnabled = false
        panelManager?.disarmAllSheets()
    }

    @discardableResult
    private func installKeyboardEventTap() -> Bool {
        let mask = CGEventMask(1 << CGEventType.flagsChanged.rawValue)
            | CGEventMask(1 << CGEventType.keyDown.rawValue)
        for configuration in KeyboardEventTapConfiguration.backgroundFirstCandidates {
            guard let tap = CGEvent.tapCreate(
                tap: configuration.location,
                place: configuration.placement,
                options: configuration.options,
                eventsOfInterest: mask,
                callback: { _, type, event, userInfo in
                    guard let userInfo else { return Unmanaged.passUnretained(event) }
                    let monitor = Unmanaged<OverlayArmingMonitor>
                        .fromOpaque(userInfo)
                        .takeUnretainedValue()
                    return MainActor.assumeIsolated {
                        monitor.handleKeyboardEventTap(type: type, event: event)
                    }
                },
                userInfo: Unmanaged.passUnretained(self).toOpaque()
            ) else {
                continue
            }
            guard let source = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, tap, 0) else {
                CFMachPortInvalidate(tap)
                continue
            }
            keyboardEventTap = tap
            keyboardEventTapSource = source
            keyboardEventTapCanSuppress = configuration.canSuppressEvents
            CFRunLoopAddSource(CFRunLoopGetMain(), source, .commonModes)
            CGEvent.tapEnable(tap: tap, enable: true)
            return true
        }
        return false
    }

    private func installKeyboardFallbackMonitors() {
        globalFlagsMonitor = NSEvent.addGlobalMonitorForEvents(matching: .flagsChanged) { [weak self] event in
            MainActor.assumeIsolated {
                self?.handleObservedFlagsChanged(event)
            }
        }
        localFlagsMonitor = NSEvent.addLocalMonitorForEvents(matching: .flagsChanged) { [weak self] event in
            MainActor.assumeIsolated {
                self?.handleObservedFlagsChanged(event)
            }
            return event
        }
        globalKeyMonitor = NSEvent.addGlobalMonitorForEvents(matching: .keyDown) { [weak self] event in
            MainActor.assumeIsolated {
                _ = self?.handleObservedKeyDown(event, source: .global)
            }
        }
        localKeyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
            var consumed = false
            MainActor.assumeIsolated {
                guard let self else { return }
                consumed = self.handleObservedKeyDown(event, source: .local)
            }
            return consumed ? nil : event
        }
    }

    private func handleKeyboardEventTap(type: CGEventType, event: CGEvent) -> Unmanaged<CGEvent>? {
        if type == .tapDisabledByTimeout || type == .tapDisabledByUserInput {
            if let keyboardEventTap { CGEvent.tapEnable(tap: keyboardEventTap, enable: true) }
            return Unmanaged.passUnretained(event)
        }
        switch type {
        case .flagsChanged:
            handleObservedFlagsChanged(
                commandPresent: commandFlagReducer.commandPresent(cgFlags: event.flags),
                keyCode: commandFlagReducer.keyCode(
                    cgKeyCode: event.getIntegerValueField(.keyboardEventKeycode)
                ),
                timestamp: commandFlagReducer.timestampSeconds(cgTimestamp: event.timestamp)
            )
            return Unmanaged.passUnretained(event)
        case .keyDown:
            guard let nsEvent = NSEvent(cgEvent: event) else {
                return Unmanaged.passUnretained(event)
            }
            let consumed = handleObservedKeyDown(nsEvent, source: .eventTap)
            return consumed && keyboardEventTapCanSuppress ? nil : Unmanaged.passUnretained(event)
        default:
            return Unmanaged.passUnretained(event)
        }
    }

    @discardableResult
    func handleObservedScroll(
        _ event: NSEvent,
        source: CueScrollObservationSource,
        mouseLocation: CGPoint? = nil
    ) -> Bool {
        let point = mouseLocation ?? NSEvent.mouseLocation
        let displayID = panelManager?.displayID(containing: point)
        let commandPresent = event.modifierFlags
            .intersection(.deviceIndependentFlagsMask)
            .contains(.command)
        let decision = observationReducer.decision(
            source: source,
            overlayLive: isOverlayLive,
            commandPresent: commandPresent,
            displayID: displayID
        )
        let rawDeltaY = scrollReducer.rawDeltaY(for: event)
        let panelIgnoresMouseEvents = displayID.flatMap { panelManager?.sheetIgnoresMouseEvents(for: $0) }
        let metrics = displayID.flatMap { session.scrollMetrics(for: $0) }

        if logPolicy.shouldRecordObservation(
            decision: decision,
            commandPresent: commandPresent,
            displayID: displayID
        ) {
            recordObservedScroll(
                event: event,
                source: source,
                commandPresent: commandPresent,
                displayID: displayID,
                panelIgnoresMouseEvents: panelIgnoresMouseEvents,
                metrics: metrics,
                rawDeltaY: rawDeltaY,
                consumedLocalEvent: false
            )
        }

        guard decision.shouldMutate, let displayID else {
            return decision.consumeLocalEvent
        }

        let mutation = session.scroll(
            by: scrollReducer.advance(for: event),
            on: displayID
        )
        let renderedOffset = session.offset(for: displayID)
        session.recordScrollEventReceipt(
            CueScrollEventReceipt(
                stage: "scroll_mutated",
                eventSource: source.rawValue,
                physicalCommandDown: commandPresent,
                pointerInsideSheet: true,
                targetPanelID: UInt32(displayID),
                targetPanelIgnoresMouseEvents: panelIgnoresMouseEvents,
                eventEnteredPanelDispatch: false,
                consumedLocalEvent: decision.consumeLocalEvent,
                eventWindowNumber: event.windowNumber,
                eventModifiersRaw: event.modifierFlags.rawValue,
                rawDeltaY: Double(rawDeltaY),
                precise: event.hasPreciseScrollingDeltas,
                directionInverted: event.isDirectionInvertedFromDevice,
                localMaxOffset: Double(mutation.localMaxOffset),
                contentHeight: metrics.map { Double($0.contentHeight) },
                viewportHeight: metrics.map { Double($0.viewportHeight) },
                scrollProgress: Double(mutation.progressAfter),
                offsetBefore: Double(mutation.offsetBefore),
                offsetAfter: Double(mutation.offsetAfter),
                renderedOffset: Double(renderedOffset)
            )
        )
        return decision.consumeLocalEvent
    }

    func handleObservedFlagsChanged(_ event: NSEvent) {
        let commandPresent = event.modifierFlags
            .intersection(.deviceIndependentFlagsMask)
            .contains(.command)
        handleObservedFlagsChanged(
            commandPresent: commandPresent,
            keyCode: event.keyCode,
            timestamp: event.timestamp
        )
    }

    func handleObservedFlagsChanged(commandPresent: Bool, keyCode: UInt16, timestamp: TimeInterval) {
        if doubleCommandDetector.record(
            commandPresent: commandPresent,
            keyCode: keyCode,
            timestamp: timestamp
        ) {
            session.toggleLineStepMode()
        }
    }

    @discardableResult
    func handleObservedKeyDown(
        _ event: NSEvent,
        source: CueScrollObservationSource,
        mouseLocation: CGPoint? = nil
    ) -> Bool {
        let direction = lineStepKeyReducer.direction(for: event.keyCode)
        let physicalCommandDown = event.modifierFlags
            .intersection(.deviceIndependentFlagsMask)
            .contains(.command)
        return handleLineStep(
            direction: direction,
            source: source,
            mouseLocation: mouseLocation,
            physicalCommandDown: physicalCommandDown,
            eventWindowNumber: event.windowNumber,
            eventModifiersRaw: event.modifierFlags.rawValue,
            timestamp: event.timestamp
        )
    }

    @discardableResult
    private func handlePolledLineStep(
        direction: CueLineStepDirection,
        commandPresent: Bool,
        timestamp: TimeInterval
    ) -> Bool {
        handleLineStep(
            direction: direction,
            source: .keyStatePoll,
            mouseLocation: nil,
            physicalCommandDown: commandPresent,
            eventWindowNumber: 0,
            eventModifiersRaw: commandPresent ? NSEvent.ModifierFlags.command.rawValue : 0,
            timestamp: timestamp
        )
    }

    @discardableResult
    private func handleLineStep(
        direction: CueLineStepDirection?,
        source: CueScrollObservationSource,
        mouseLocation: CGPoint?,
        physicalCommandDown: Bool,
        eventWindowNumber: Int,
        eventModifiersRaw: UInt,
        timestamp: TimeInterval
    ) -> Bool {
        let point = mouseLocation ?? NSEvent.mouseLocation
        let displayID = panelManager?.lineStepDisplayID(containing: point)
        let decision = lineStepObservationReducer.decision(
            source: source,
            overlayLive: isOverlayLive,
            lineStepModeEnabled: session.lineStepModeEnabled,
            direction: direction,
            displayID: displayID
        )
        guard decision.shouldMutate, let direction, let displayID else {
            return decision.consumeLocalEvent
        }
        guard lineStepDuplicateGate.shouldAccept(direction: direction, timestamp: timestamp) else {
            return decision.consumeLocalEvent
        }

        let mutation = session.stepCueLine(direction, on: displayID)
        session.recordScrollEventReceipt(
            CueScrollEventReceipt(
                stage: "line_step_mutated",
                eventSource: source.rawValue,
                physicalCommandDown: physicalCommandDown,
                pointerInsideSheet: panelManager?.displayID(containing: point) != nil,
                targetPanelID: UInt32(displayID),
                targetPanelIgnoresMouseEvents: panelManager?.sheetIgnoresMouseEvents(for: displayID),
                eventEnteredPanelDispatch: false,
                consumedLocalEvent: decision.consumeLocalEvent,
                eventWindowNumber: eventWindowNumber,
                eventModifiersRaw: eventModifiersRaw,
                rawDeltaY: 0,
                precise: true,
                directionInverted: false,
                localMaxOffset: Double(mutation.localMaxOffset),
                contentHeight: session.scrollMetrics(for: displayID).map { Double($0.contentHeight) },
                viewportHeight: session.scrollMetrics(for: displayID).map { Double($0.viewportHeight) },
                scrollProgress: Double(mutation.progressAfter),
                offsetBefore: Double(mutation.offsetBefore),
                offsetAfter: Double(mutation.offsetAfter),
                renderedOffset: Double(session.offset(for: displayID))
            )
        )
        return decision.consumeLocalEvent
    }

    private func recordObservedScroll(
        event: NSEvent,
        source: CueScrollObservationSource,
        commandPresent: Bool,
        displayID: CGDirectDisplayID?,
        panelIgnoresMouseEvents: Bool?,
        metrics: CueScrollMetrics?,
        rawDeltaY: CGFloat,
        consumedLocalEvent: Bool
    ) {
        let localMaxOffset = displayID.map { session.maxOffset(for: $0) } ?? 0
        let offsetBefore = displayID.map { session.offset(for: $0) } ?? 0
        session.recordScrollEventReceipt(
            CueScrollEventReceipt(
                stage: "scroll_observed",
                eventSource: source.rawValue,
                physicalCommandDown: commandPresent,
                pointerInsideSheet: displayID != nil,
                targetPanelID: displayID.map { UInt32($0) },
                targetPanelIgnoresMouseEvents: panelIgnoresMouseEvents,
                eventEnteredPanelDispatch: false,
                consumedLocalEvent: consumedLocalEvent,
                eventWindowNumber: event.windowNumber,
                eventModifiersRaw: event.modifierFlags.rawValue,
                rawDeltaY: Double(rawDeltaY),
                precise: event.hasPreciseScrollingDeltas,
                directionInverted: event.isDirectionInvertedFromDevice,
                localMaxOffset: Double(localMaxOffset),
                contentHeight: metrics.map { Double($0.contentHeight) },
                viewportHeight: metrics.map { Double($0.viewportHeight) },
                scrollProgress: Double(session.scrollProgress),
                offsetBefore: Double(offsetBefore),
                offsetAfter: Double(offsetBefore),
                renderedOffset: Double(offsetBefore)
            )
        )
    }

    private func beginKeyboardPollingActivity() {
        guard keyboardPollingActivity == nil else { return }
        keyboardPollingActivity = ProcessInfo.processInfo.beginActivity(
            options: [.userInitiated, .latencyCritical],
            reason: "Demo Take Console overlay keyboard polling"
        )
    }

    private func endKeyboardPollingActivity() {
        guard let keyboardPollingActivity else { return }
        ProcessInfo.processInfo.endActivity(keyboardPollingActivity)
        self.keyboardPollingActivity = nil
    }

    private func pollArmingState() {
        let snapshot = keyboardStateSampler.snapshot()
        let command = snapshot.command.commandPresent
        let timestamp = ProcessInfo.processInfo.systemUptime
        if commandStatePollReducer.observe(
            snapshot: snapshot.command,
            timestamp: timestamp,
            detector: &doubleCommandDetector
        ) {
            session.toggleLineStepMode()
        }
        if let direction = lineStepKeyStatePollReducer.observe(snapshot: snapshot.lineStep) {
            handlePolledLineStep(
                direction: direction,
                commandPresent: command,
                timestamp: timestamp
            )
        }

        guard isOverlayLive else {
            disarmIfNeeded()
            return
        }

        guard command else {
            disarmIfNeeded()
            return
        }

        commandHeld = true
        let point = NSEvent.mouseLocation
        if panelManager?.sheetFrameContains(point) == true {
            panelManager?.armSheet(containing: point)
        } else {
            panelManager?.disarmAllSheets()
        }
    }

    private func disarmIfNeeded() {
        if commandHeld || session.armedDisplayID != nil {
            commandHeld = false
            panelManager?.disarmAllSheets()
        }
    }

    private var isOverlayLive: Bool {
        switch session.interactionState {
        case .readThrough, .armed, .arrange: true
        case .hidden, .peek: false
        }
    }
}
