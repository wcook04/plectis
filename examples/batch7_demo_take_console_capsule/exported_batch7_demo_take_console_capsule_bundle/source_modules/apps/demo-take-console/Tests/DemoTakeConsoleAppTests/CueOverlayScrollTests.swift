import CoreGraphics
import Foundation
import Testing
@testable import DemoTakeConsoleApp

@MainActor
struct CueOverlayScrollTests {
    private let primary: CGDirectDisplayID = 101
    private let secondary: CGDirectDisplayID = 202
    private let glanceModeKey = "RecipientCueOverlay.glanceMode"
    private let glanceModePreferenceVersionKey = "RecipientCueOverlay.glanceModePreferenceVersion"

    @Test
    func freshSessionsDefaultToFullRunSheetMode() {
        UserDefaults.standard.removeObject(forKey: glanceModeKey)
        UserDefaults.standard.removeObject(forKey: glanceModePreferenceVersionKey)
        defer {
            UserDefaults.standard.removeObject(forKey: glanceModeKey)
            UserDefaults.standard.removeObject(forKey: glanceModePreferenceVersionKey)
        }

        let session = OverlaySession()

        #expect(session.glanceMode == false)
        #expect(UserDefaults.standard.bool(forKey: glanceModeKey) == false)
    }

    @Test
    func oldGlancePreferenceMigratesToFullRunSheetModeOnce() {
        UserDefaults.standard.set(true, forKey: glanceModeKey)
        UserDefaults.standard.removeObject(forKey: glanceModePreferenceVersionKey)
        defer {
            UserDefaults.standard.removeObject(forKey: glanceModeKey)
            UserDefaults.standard.removeObject(forKey: glanceModePreferenceVersionKey)
        }

        let session = OverlaySession()

        #expect(session.glanceMode == false)
        #expect(UserDefaults.standard.bool(forKey: glanceModeKey) == false)
        #expect(UserDefaults.standard.integer(forKey: glanceModePreferenceVersionKey) == 2)
    }

    @Test
    func zeroRangeOnOneDisplayDoesNotEraseAnotherDisplaysScroll() {
        let session = OverlaySession()
        session.setContentMetrics(for: primary, contentHeight: 900, viewportHeight: 300)
        session.setContentMetrics(for: secondary, contentHeight: 100, viewportHeight: 300)

        session.scroll(by: 120, on: primary)

        #expect(abs(session.offset(for: primary) - 120) < 0.001)
        #expect(session.offset(for: secondary) == 0)

        session.scroll(by: 120, on: primary)

        #expect(abs(session.offset(for: primary) - 240) < 0.001)
        #expect(session.scrollProgress > 0)
    }

    @Test
    func displaysProjectTheSameNormalizedReadingPositionThroughLocalRanges() {
        let session = OverlaySession()
        session.setContentMetrics(for: primary, contentHeight: 900, viewportHeight: 300)
        session.setContentMetrics(for: secondary, contentHeight: 1500, viewportHeight: 300)

        session.scroll(by: 300, on: primary)

        #expect(abs(session.scrollProgress - 0.5) < 0.001)
        #expect(abs(session.offset(for: primary) - 300) < 0.001)
        #expect(abs(session.offset(for: secondary) - 600) < 0.001)
    }

    @Test
    func resizingDisplayRangePreservesProgressInsteadOfSnappingBack() {
        let session = OverlaySession()
        session.setContentMetrics(for: primary, contentHeight: 900, viewportHeight: 300)
        session.scroll(by: 300, on: primary)

        session.setContentMetrics(for: primary, contentHeight: 1400, viewportHeight: 300)

        #expect(abs(session.scrollProgress - 0.5) < 0.001)
        #expect(abs(session.offset(for: primary) - 550) < 0.001)
    }

    @Test
    func repeatedSmallPreciseDeltasAccumulateInsteadOfBeingDropped() {
        let session = OverlaySession()
        session.setContentMetrics(for: primary, contentHeight: 20_300, viewportHeight: 300)

        for _ in 0..<100 {
            session.scroll(by: 0.2, on: primary)
        }

        #expect(abs(session.offset(for: primary) - 20) < 0.001)
    }

    @Test
    func zeroMetricReportsDoNotOverwriteMeasuredRange() {
        let session = OverlaySession()
        session.setContentMetrics(for: primary, contentHeight: 900, viewportHeight: 300)

        session.setContentMetrics(for: primary, contentHeight: 0, viewportHeight: 300)
        session.setContentMetrics(for: primary, contentHeight: 900, viewportHeight: 0)

        #expect(session.scrollMetricsByDisplay[primary]?.contentHeight == 900)
        #expect(session.scrollMetricsByDisplay[primary]?.viewportHeight == 300)
        #expect(session.maxOffset(for: primary) == 600)
    }

    @Test
    func cueRangeEstimatorProvidesFallbackForMultiBeatDecks() {
        let beats = (0..<8).map { idx in
            BeatCue(
                num: "\(idx)",
                name: "BEAT \(idx)",
                land: ["land the point", "connect it"],
                show: ["show the proof"],
                limit: "do not overclaim",
                next: "next beat",
                verbatim: []
            )
        }

        let estimated = CueScrollRangeEstimator.estimatedContentHeight(
            compressedScript: beats,
            scriptBlocks: [],
            verbatimLineCount: 2
        )

        #expect(estimated > 700)
    }

    @Test
    func cueRangeEstimatorPrefersFullRunSheetBlocksWhenAvailable() {
        let beats = (0..<20).map { idx in
            BeatCue(
                num: "\(idx)",
                name: "BEAT \(idx)",
                land: ["compressed point", "another point"],
                show: ["compressed stage direction"],
                limit: "do not overclaim",
                next: "next beat",
                verbatim: []
            )
        }
        let blocks = [
            ScriptBlock(kind: .heading, text: "THE MIC SURFACE", index: 0),
            ScriptBlock(kind: .spoken, text: "This is the full run sheet.", index: 1),
            ScriptBlock(kind: .direction, text: "Open the proof object.", index: 2),
        ]

        let estimated = CueScrollRangeEstimator.estimatedContentHeight(
            compressedScript: beats,
            scriptBlocks: blocks,
            verbatimLineCount: 0
        )

        #expect(estimated == 198)
    }

    @Test
    func fullRunSheetTeleprompterStartsWithFirstSpeakableBlock() {
        let blocks = [
            ScriptBlock(kind: .heading, text: "THE MIC SURFACE - all you speak", index: 0),
            ScriptBlock(kind: .heading, text: "Open", index: 1),
            ScriptBlock(kind: .spoken, text: "Boris, I may be mapping this to the wrong layer.", index: 2),
            ScriptBlock(kind: .direction, text: "Open the proof object.", index: 3),
        ]

        let ordered = ScriptBlockTeleprompterOrder.speakableFirst(blocks)

        #expect(ordered.visibleBlocks.map(\.text) == [
            "Boris, I may be mapping this to the wrong layer.",
            "Open the proof object.",
        ])
    }

    @Test
    func fullRunSheetTeleprompterKeepsViewCueInsideFirstSpeakableBlock() {
        var firstSpoken = ScriptBlock(
            kind: .spoken,
            text: "Boris, I am showing the frontend first.",
            index: 4
        )
        firstSpoken.viewCue = "Agent Trace"
        let blocks = [
            ScriptBlock(kind: .heading, text: "THE MIC SURFACE - all you speak", index: 0),
            ScriptBlock(kind: .heading, text: "Open", index: 1),
            ScriptBlock(kind: .direction, text: "Open Agent Trace visually.", index: 3),
            firstSpoken,
            ScriptBlock(kind: .direction, text: "Keep the same trace open.", index: 5),
        ]

        let ordered = ScriptBlockTeleprompterOrder.speakableFirst(blocks)

        #expect(ordered.visibleBlocks.map(\.kind) == [.spoken, .direction])
        #expect(ordered.visibleBlocks.first?.viewCue == "Agent Trace")
    }

    @Test
    func fullRunSheetTeleprompterKeepsNonspokenFallbackWhenNoSpeakableBlockExists() {
        let blocks = [
            ScriptBlock(kind: .heading, text: "THE MIC SURFACE", index: 0),
            ScriptBlock(kind: .direction, text: "Open the proof object.", index: 1),
        ]

        let ordered = ScriptBlockTeleprompterOrder.speakableFirst(blocks)

        #expect(ordered.visibleBlocks == blocks)
    }

    @Test
    func scrollReducerPreservesPreciseDeltasAndScalesCoarseWheelTicks() {
        let reducer = CueScrollDeltaReducer()

        #expect(reducer.advance(rawDeltaY: -12, hasPreciseScrollingDeltas: true) == 12)
        #expect(reducer.advance(rawDeltaY: -1, hasPreciseScrollingDeltas: false) == CueScrollDeltaReducer.coarseWheelLineHeight)
        #expect(reducer.advance(rawDeltaY: 0, hasPreciseScrollingDeltas: true) == 0)
    }

    @Test
    func commandDoubleTapDetectorTogglesOnlyAfterQuickSecondPress() {
        var detector = CommandDoubleTapDetector(doubleTapWindow: 0.36)

        #expect(detector.record(commandPresent: true, keyCode: CommandDoubleTapDetector.leftCommandKeyCode, timestamp: 10) == false)
        #expect(detector.record(commandPresent: false, keyCode: CommandDoubleTapDetector.leftCommandKeyCode, timestamp: 10.08) == false)
        let toggled = detector.record(commandPresent: true, keyCode: CommandDoubleTapDetector.leftCommandKeyCode, timestamp: 10.24)
        #expect(toggled)
        #expect(detector.record(commandPresent: true, keyCode: CommandDoubleTapDetector.leftCommandKeyCode, timestamp: 10.25) == false)
    }

    @Test
    func commandDoubleTapDetectorSurvivesDuplicatePressEventsAndUnknownReleaseKeyCode() {
        var detector = CommandDoubleTapDetector(doubleTapWindow: 0.36)

        #expect(detector.record(commandPresent: true, keyCode: CommandDoubleTapDetector.leftCommandKeyCode, timestamp: 10) == false)
        #expect(detector.record(commandPresent: true, keyCode: 0, timestamp: 10.001) == false)
        #expect(detector.record(commandPresent: false, keyCode: 0, timestamp: 10.08) == false)
        #expect(detector.record(commandPresent: false, keyCode: CommandDoubleTapDetector.leftCommandKeyCode, timestamp: 10.081) == false)
        let toggled = detector.record(
            commandPresent: true,
            keyCode: CommandDoubleTapDetector.leftCommandKeyCode,
            timestamp: 10.24
        )
        #expect(toggled)
        #expect(detector.record(commandPresent: true, keyCode: 0, timestamp: 10.241) == false)
    }

    @Test
    func commandDoubleTapDetectorIgnoresSlowSecondPressAndNonCommandFlags() {
        var detector = CommandDoubleTapDetector(doubleTapWindow: 0.36)

        #expect(detector.record(commandPresent: true, keyCode: CommandDoubleTapDetector.leftCommandKeyCode, timestamp: 10) == false)
        #expect(detector.record(commandPresent: false, keyCode: CommandDoubleTapDetector.leftCommandKeyCode, timestamp: 10.1) == false)
        #expect(detector.record(commandPresent: true, keyCode: CommandDoubleTapDetector.leftCommandKeyCode, timestamp: 10.6) == false)
        #expect(detector.record(commandPresent: true, keyCode: 58, timestamp: 10.7) == false)
    }

    @Test
    func commandStatePollingDetectsDoubleTapWithoutKeyboardFocusEvents() {
        var detector = CommandDoubleTapDetector(doubleTapWindow: 0.36)
        var poller = CommandStatePollReducer()

        #expect(poller.observe(commandPresent: false, timestamp: 10.00, detector: &detector) == false)
        #expect(poller.observe(commandPresent: true, timestamp: 10.05, detector: &detector) == false)
        #expect(poller.observe(commandPresent: true, timestamp: 10.07, detector: &detector) == false)
        #expect(poller.observe(commandPresent: false, timestamp: 10.12, detector: &detector) == false)
        let toggled = poller.observe(commandPresent: true, timestamp: 10.26, detector: &detector)

        #expect(toggled)
        #expect(poller.observe(commandPresent: true, timestamp: 10.27, detector: &detector) == false)
    }

    @Test
    func commandStatePollingAcceptsDirectCommandKeySnapshots() {
        var detector = CommandDoubleTapDetector(doubleTapWindow: 0.36)
        var poller = CommandStatePollReducer()

        #expect(poller.observe(
            snapshot: CommandKeyStateSnapshot(
                flagsCommandPresent: false,
                leftCommandDown: false,
                rightCommandDown: false
            ),
            timestamp: 10.00,
            detector: &detector
        ) == false)
        #expect(poller.observe(
            snapshot: CommandKeyStateSnapshot(
                flagsCommandPresent: false,
                leftCommandDown: true,
                rightCommandDown: false
            ),
            timestamp: 10.04,
            detector: &detector
        ) == false)
        #expect(poller.observe(
            snapshot: CommandKeyStateSnapshot(
                flagsCommandPresent: false,
                leftCommandDown: false,
                rightCommandDown: false
            ),
            timestamp: 10.11,
            detector: &detector
        ) == false)
        let toggled = poller.observe(
            snapshot: CommandKeyStateSnapshot(
                flagsCommandPresent: false,
                leftCommandDown: false,
                rightCommandDown: true
            ),
            timestamp: 10.24,
            detector: &detector
        )

        #expect(toggled)
    }

    @Test
    func commandKeyStateSnapshotTreatsFlagsOrEitherPhysicalCommandAsPresent() {
        #expect(CommandKeyStateSnapshot(
            flagsCommandPresent: true,
            leftCommandDown: false,
            rightCommandDown: false
        ).commandPresent)
        #expect(CommandKeyStateSnapshot(
            flagsCommandPresent: false,
            leftCommandDown: true,
            rightCommandDown: false
        ).commandPresent)
        #expect(CommandKeyStateSnapshot(
            flagsCommandPresent: false,
            leftCommandDown: false,
            rightCommandDown: true
        ).commandPresent)
        #expect(CommandKeyStateSnapshot(
            flagsCommandPresent: false,
            leftCommandDown: false,
            rightCommandDown: false
        ).commandPresent == false)
    }

    @Test
    func commandFlagChangeReducerReadsEventTapFieldsDirectly() {
        let reducer = CommandFlagChangeReducer()

        #expect(reducer.commandPresent(cgFlags: [.maskCommand]))
        #expect(reducer.commandPresent(cgFlags: [.maskShift]) == false)
        #expect(reducer.keyCode(cgKeyCode: Int64(CommandDoubleTapDetector.rightCommandKeyCode)) == CommandDoubleTapDetector.rightCommandKeyCode)
        #expect(reducer.timestampSeconds(cgTimestamp: 240_000_000) == 0.24)
    }

    @Test
    func keyboardEventTapCandidatesKeepBackgroundPassiveFallbacks() {
        let candidates = KeyboardEventTapConfiguration.backgroundFirstCandidates

        #expect(candidates.count == 3)
        #expect(candidates[0].location == .cgSessionEventTap)
        #expect(candidates[0].options == .defaultTap)
        #expect(candidates[0].canSuppressEvents)
        #expect(candidates[1].location == .cgSessionEventTap)
        #expect(candidates[1].options == .listenOnly)
        #expect(candidates[1].canSuppressEvents == false)
        #expect(candidates[2].location == .cghidEventTap)
        #expect(candidates[2].options == .listenOnly)
        #expect(candidates[2].canSuppressEvents == false)
    }

    @Test
    func lineStepNavigatorSnapsOffGridOffsetsBeforeMoving() {
        let navigator = CueLineStepNavigator()
        let lineHeight: CGFloat = 28

        #expect(navigator.targetOffset(currentOffset: 55, maxOffset: 200, lineHeight: lineHeight, direction: .down) == 84)
        #expect(navigator.targetOffset(currentOffset: 60, maxOffset: 200, lineHeight: lineHeight, direction: .up) == 28)
        #expect(navigator.targetOffset(currentOffset: 197, maxOffset: 200, lineHeight: lineHeight, direction: .down) == 200)
        #expect(navigator.targetOffset(currentOffset: 3, maxOffset: 200, lineHeight: lineHeight, direction: .up) == 0)
    }

    @Test
    func measuredLineAnchorNavigatorStepsThroughAbsoluteLineTargets() {
        let navigator = CueLineAnchorNavigator(topMargin: 4)
        let anchors: [CGFloat] = [4, 31, 59, 92]

        #expect(navigator.targetOffset(currentOffset: 0, maxOffset: 200, anchors: anchors, direction: .down) == 27)
        #expect(navigator.targetOffset(currentOffset: 27, maxOffset: 200, anchors: anchors, direction: .down) == 55)
        #expect(navigator.targetOffset(currentOffset: 55, maxOffset: 200, anchors: anchors, direction: .up) == 27)
        #expect(navigator.targetOffset(currentOffset: 88, maxOffset: 200, anchors: anchors, direction: .down) == 200)
    }

    @Test
    func measuredLineAnchorNavigatorSnapsManualOffGridScrollBeforeStepping() {
        let navigator = CueLineAnchorNavigator(topMargin: 4)
        let anchors: [CGFloat] = [4, 31, 59, 92]

        #expect(navigator.targetOffset(currentOffset: 53, maxOffset: 200, anchors: anchors, direction: .down) == 88)
        #expect(navigator.targetOffset(currentOffset: 53, maxOffset: 200, anchors: anchors, direction: .up) == 27)
    }

    @Test
    func sessionLineStepPrefersMeasuredAnchorsOverFallbackGrid() {
        let session = OverlaySession()
        session.setContentMetrics(for: primary, contentHeight: 900, viewportHeight: 300)
        session.setLineAnchors(for: primary, offsets: [4, 31, 59, 92])

        let first = session.stepCueLine(.down, on: primary)
        let second = session.stepCueLine(.down, on: primary)
        let back = session.stepCueLine(.up, on: primary)

        #expect(first.usedMeasuredAnchors)
        #expect(first.measuredAnchorCount == 4)
        #expect(abs(first.offsetAfter - 27) < 0.001)
        #expect(abs(second.offsetAfter - 55) < 0.001)
        #expect(abs(back.offsetAfter - 27) < 0.001)
        #expect(abs(session.offset(for: primary) - 27) < 0.001)
    }

    @Test
    func sessionLineStepFallsBackToFixedGridBeforeAnchorsReport() {
        let session = OverlaySession()
        session.setContentMetrics(for: primary, contentHeight: 900, viewportHeight: 300)
        session.scroll(by: 57, on: primary)

        let down = session.stepCueLine(.down, on: primary)
        let up = session.stepCueLine(.up, on: primary)

        #expect(down.usedMeasuredAnchors == false)
        #expect(abs(down.offsetAfter - 84) < 0.001)
        #expect(abs(up.offsetAfter - 56) < 0.001)
        #expect(abs(session.offset(for: primary) - 56) < 0.001)
    }

    @Test
    func lineStepKeyReducerMapsMinusPlusAndVerticalArrows() {
        let reducer = CueLineStepKeyReducer()

        #expect(reducer.direction(for: CueLineStepKeyReducer.plusKeyCode) == .down)
        #expect(reducer.direction(for: CueLineStepKeyReducer.keypadPlusKeyCode) == .down)
        #expect(reducer.direction(for: CueLineStepKeyReducer.downArrowKeyCode) == .down)
        #expect(reducer.direction(for: CueLineStepKeyReducer.minusKeyCode) == .up)
        #expect(reducer.direction(for: CueLineStepKeyReducer.keypadMinusKeyCode) == .up)
        #expect(reducer.direction(for: CueLineStepKeyReducer.upArrowKeyCode) == .up)
    }

    @Test
    func lineStepKeyStatePollingOnlyEmitsOnFreshStepKeyPresses() {
        var reducer = CueLineStepKeyStatePollReducer()

        #expect(reducer.observe(snapshot: CueLineStepKeyStateSnapshot(upStepKeyDown: false, downStepKeyDown: false)) == nil)
        #expect(reducer.observe(snapshot: CueLineStepKeyStateSnapshot(upStepKeyDown: false, downStepKeyDown: true)) == .down)
        #expect(reducer.observe(snapshot: CueLineStepKeyStateSnapshot(upStepKeyDown: false, downStepKeyDown: true)) == nil)
        #expect(reducer.observe(snapshot: CueLineStepKeyStateSnapshot(upStepKeyDown: false, downStepKeyDown: false)) == nil)
        #expect(reducer.observe(snapshot: CueLineStepKeyStateSnapshot(upStepKeyDown: true, downStepKeyDown: false)) == .up)
    }

    @Test
    func lineStepDuplicateGateRejectsSameDirectionPollAndEventDuplicates() {
        var gate = CueLineStepDuplicateGate()
        gate.minimumInterval = 0.08

        let firstDown = gate.shouldAccept(direction: .down, timestamp: 10.000)
        let duplicateDown = gate.shouldAccept(direction: .down, timestamp: 10.040)
        let differentDirection = gate.shouldAccept(direction: .up, timestamp: 10.012)
        let laterDown = gate.shouldAccept(direction: .down, timestamp: 10.090)

        #expect(firstDown)
        #expect(duplicateDown == false)
        #expect(differentDirection)
        #expect(laterDown)
    }

    @Test
    func lineStepObservationRequiresLiveEnabledOverlayAndTargetDisplay() {
        let reducer = CueLineStepObservationReducer()

        let local = reducer.decision(
            source: .local,
            overlayLive: true,
            lineStepModeEnabled: true,
            direction: .down,
            displayID: primary
        )
        let global = reducer.decision(
            source: .global,
            overlayLive: true,
            lineStepModeEnabled: true,
            direction: .down,
            displayID: primary
        )
        let eventTap = reducer.decision(
            source: .eventTap,
            overlayLive: true,
            lineStepModeEnabled: true,
            direction: .down,
            displayID: primary
        )
        let keyStatePoll = reducer.decision(
            source: .keyStatePoll,
            overlayLive: true,
            lineStepModeEnabled: true,
            direction: .down,
            displayID: primary
        )

        #expect(local.shouldMutate)
        #expect(local.consumeLocalEvent)
        #expect(global.shouldMutate)
        #expect(global.consumeLocalEvent == false)
        #expect(eventTap.shouldMutate)
        #expect(eventTap.consumeLocalEvent)
        #expect(keyStatePoll.shouldMutate)
        #expect(keyStatePoll.consumeLocalEvent == false)
        #expect(reducer.decision(source: .local, overlayLive: false, lineStepModeEnabled: true, direction: .down, displayID: primary).shouldMutate == false)
        #expect(reducer.decision(source: .local, overlayLive: true, lineStepModeEnabled: false, direction: .down, displayID: primary).shouldMutate == false)
        #expect(reducer.decision(source: .local, overlayLive: true, lineStepModeEnabled: true, direction: nil, displayID: primary).shouldMutate == false)
        #expect(reducer.decision(source: .local, overlayLive: true, lineStepModeEnabled: true, direction: .down, displayID: nil).shouldMutate == false)
    }

    @Test
    func lineStepObservationConsumesOwnedKeysEvenWithoutTargetDisplay() {
        let reducer = CueLineStepObservationReducer()

        let local = reducer.decision(
            source: .local,
            overlayLive: true,
            lineStepModeEnabled: true,
            direction: .down,
            displayID: nil
        )
        let eventTap = reducer.decision(
            source: .eventTap,
            overlayLive: true,
            lineStepModeEnabled: true,
            direction: .up,
            displayID: nil
        )
        let global = reducer.decision(
            source: .global,
            overlayLive: true,
            lineStepModeEnabled: true,
            direction: .down,
            displayID: nil
        )

        #expect(local.shouldMutate == false)
        #expect(local.consumeLocalEvent)
        #expect(eventTap.shouldMutate == false)
        #expect(eventTap.consumeLocalEvent)
        #expect(global.shouldMutate == false)
        #expect(global.consumeLocalEvent == false)
    }

    @Test
    func plainScrollIsRejectedByMonitorDecision() {
        let reducer = CueScrollObservationReducer()

        let decision = reducer.decision(
            source: .local,
            overlayLive: true,
            commandPresent: false,
            displayID: primary
        )

        #expect(decision.shouldMutate == false)
        #expect(decision.consumeLocalEvent == false)
    }

    @Test
    func commandScrollOutsideSheetIsRejectedByMonitorDecision() {
        let reducer = CueScrollObservationReducer()

        let decision = reducer.decision(
            source: .local,
            overlayLive: true,
            commandPresent: true,
            displayID: nil
        )

        #expect(decision.shouldMutate == false)
        #expect(decision.consumeLocalEvent == false)
    }

    @Test
    func localQualifiedCommandScrollMutatesAndConsumes() {
        let reducer = CueScrollObservationReducer()

        let decision = reducer.decision(
            source: .local,
            overlayLive: true,
            commandPresent: true,
            displayID: primary
        )

        #expect(decision.shouldMutate)
        #expect(decision.consumeLocalEvent)
    }

    @Test
    func globalQualifiedCommandScrollMutatesWithoutConsumableRepresentation() {
        let reducer = CueScrollObservationReducer()

        let decision = reducer.decision(
            source: .global,
            overlayLive: true,
            commandPresent: true,
            displayID: primary
        )

        #expect(decision.shouldMutate)
        #expect(decision.consumeLocalEvent == false)
    }

    @Test
    func commandScrollInsideResolvedDisplayMutatesSessionOnce() {
        let session = OverlaySession()
        let observationReducer = CueScrollObservationReducer()
        let deltaReducer = CueScrollDeltaReducer()
        session.setContentMetrics(for: primary, contentHeight: 900, viewportHeight: 300)

        let decision = observationReducer.decision(
            source: .local,
            overlayLive: true,
            commandPresent: true,
            displayID: primary
        )
        if decision.shouldMutate {
            session.scroll(
                by: deltaReducer.advance(rawDeltaY: -12, hasPreciseScrollingDeltas: true),
                on: primary
            )
        }

        #expect(abs(session.offset(for: primary) - 12) < 0.001)
        #expect(decision.consumeLocalEvent)
    }

    @Test
    func plainGlobalScrollDoesNotWriteObservationReceipt() {
        let reducer = CueScrollObservationReducer()
        let policy = CueScrollObservationLogPolicy()
        let decision = reducer.decision(
            source: .global,
            overlayLive: true,
            commandPresent: false,
            displayID: nil
        )

        #expect(policy.shouldRecordObservation(
            decision: decision,
            commandPresent: false,
            displayID: nil
        ) == false)
    }

    @Test
    func commandScrollMutationWritesMutationReceiptOnly() {
        let reducer = CueScrollObservationReducer()
        let policy = CueScrollObservationLogPolicy()
        let decision = reducer.decision(
            source: .global,
            overlayLive: true,
            commandPresent: true,
            displayID: primary
        )

        #expect(decision.shouldMutate)
        #expect(policy.shouldRecordObservation(
            decision: decision,
            commandPresent: true,
            displayID: primary
        ) == false)
    }

    @Test
    func commandScrollOutsideSheetStillWritesDiagnosticObservation() {
        let reducer = CueScrollObservationReducer()
        let policy = CueScrollObservationLogPolicy()
        let decision = reducer.decision(
            source: .global,
            overlayLive: true,
            commandPresent: true,
            displayID: nil
        )

        #expect(decision.shouldMutate == false)
        #expect(policy.shouldRecordObservation(
            decision: decision,
            commandPresent: true,
            displayID: nil
        ))
    }
}
