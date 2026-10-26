import CoreGraphics
import Foundation
import Testing
@testable import DemoTakeConsoleApp

/// The capture-exclusion sentinel is the release-blocking privacy gate. These tests
/// pin the PURE verdict logic — the part that decides pass/fail from probe results —
/// so a regression cannot silently make the proof vacuous. The capture itself needs
/// a live display and is exercised at runtime, not here.
struct ExclusionSentinelVerdictTests {
    private let d1: UInt32 = 1
    private let d2: UInt32 = 2

    // MARK: - Per-probe builders

    @Test
    func baselineDetectedPasses() {
        let r = ExclusionSentinel.baselineResult(displayID: d1, capture: (fraction: 0.2, note: nil))
        #expect(r.kind == "baseline")
        #expect(r.pass == true)
        #expect(r.note == nil)
    }

    @Test
    func baselineBelowFloorFailsClosed() {
        // Marker never rendered (fraction below the floor) → the check would be
        // vacuous, so the baseline probe must FAIL.
        let r = ExclusionSentinel.baselineResult(displayID: d1, capture: (fraction: 0.0, note: nil))
        #expect(r.pass == false)
        #expect(r.note == "sentinel_not_detectable_in_baseline")
    }

    @Test
    func baselineCaptureFailureFailsClosed() {
        let r = ExclusionSentinel.baselineResult(displayID: d1, capture: (fraction: 0.0, note: "capture_failed: x"))
        #expect(r.pass == false)
    }

    @Test
    func productionCleanPasses() {
        let r = ExclusionSentinel.productionResult(displayID: d1, capture: (fraction: 0.0, note: nil))
        #expect(r.kind == "exclusion")
        #expect(r.pass == true)
        #expect(r.clean == true)
    }

    @Test
    func productionDirtyFails() {
        // Marker still visible through the production filter == a real leak → FAIL.
        let r = ExclusionSentinel.productionResult(displayID: d1, capture: (fraction: 0.5, note: nil))
        #expect(r.pass == false)
        #expect(r.note == "sentinel_pixels_present_in_capture")
    }

    @Test
    func productionCaptureFailureFailsClosed() {
        let r = ExclusionSentinel.productionResult(displayID: d1, capture: (fraction: 1.0, note: "capture_failed: x"))
        #expect(r.pass == false)
    }

    // MARK: - Overall verdict

    @Test
    func emptyTopologyNeverPasses() {
        let v = ExclusionSentinel.verdict(results: [], topology: [])
        #expect(v.passed == false)
        #expect(v.staleReason == "no_displays_to_probe")
    }

    @Test
    func baselineDetectedAndProductionCleanPasses() {
        let results = [
            ExclusionSentinel.baselineResult(displayID: d1, capture: (0.2, nil)),
            ExclusionSentinel.productionResult(displayID: d1, capture: (0.0, nil)),
        ]
        let v = ExclusionSentinel.verdict(results: results, topology: [d1])
        #expect(v.passed == true)
        #expect(v.staleReason == nil)
    }

    @Test
    func vacuousBaselineBlocksPassEvenWhenProductionClean() {
        // The crux of the baseline guard: production reads clean, but the baseline
        // never detected the marker, so a "clean" reading cannot be trusted to mean
        // "excluded". Must FAIL, and the reason must point at the baseline, not a leak.
        let results = [
            ExclusionSentinel.baselineResult(displayID: d1, capture: (0.0, nil)),
            ExclusionSentinel.productionResult(displayID: d1, capture: (0.0, nil)),
        ]
        let v = ExclusionSentinel.verdict(results: results, topology: [d1])
        #expect(v.passed == false)
        #expect(v.staleReason == "sentinel_not_detectable_baseline")
    }

    @Test
    func realLeakFailsWithLeakReason() {
        let results = [
            ExclusionSentinel.baselineResult(displayID: d1, capture: (0.2, nil)),
            ExclusionSentinel.productionResult(displayID: d1, capture: (0.4, nil)),
        ]
        let v = ExclusionSentinel.verdict(results: results, topology: [d1])
        #expect(v.passed == false)
        #expect(v.staleReason == "sentinel_pixels_present_in_capture")
    }

    @Test
    func oneDisplayLeakingFailsTheWholeMultiDisplayCheck() {
        let results = [
            ExclusionSentinel.baselineResult(displayID: d1, capture: (0.2, nil)),
            ExclusionSentinel.productionResult(displayID: d1, capture: (0.0, nil)),
            ExclusionSentinel.baselineResult(displayID: d2, capture: (0.2, nil)),
            ExclusionSentinel.productionResult(displayID: d2, capture: (0.3, nil)), // d2 leaks
        ]
        let v = ExclusionSentinel.verdict(results: results, topology: [d1, d2])
        #expect(v.passed == false)
    }
}

struct OverlayCaptureWindowClassificationTests {
    @Test
    func visibleLayerZeroOwnWindowStaysPublicAndCapturable() {
        let row = windowInfoRow(ownerPID: 42, layer: 0, windowID: 123)

        let publicID = RecipientOverlayCaptureExclusion.publicCaptureWindowID(from: row, ownerPID: 42)
        let overlayID = RecipientOverlayCaptureExclusion.overlayCaptureWindowID(from: row, ownerPID: 42)

        #expect(publicID == CGWindowID(123))
        #expect(overlayID == nil)
    }

    @Test
    func floatingOwnWindowIsPrivateOverlayOnly() {
        let row = windowInfoRow(ownerPID: 42, layer: 3, windowID: 456)

        let publicID = RecipientOverlayCaptureExclusion.publicCaptureWindowID(from: row, ownerPID: 42)
        let overlayID = RecipientOverlayCaptureExclusion.overlayCaptureWindowID(from: row, ownerPID: 42)

        #expect(publicID == nil)
        #expect(overlayID == CGWindowID(456))
    }

    @Test
    func overlayWindowIDsFilterToPrivateOwnWindowsOnly() {
        let rows = [
            windowInfoRow(ownerPID: 42, layer: 0, windowID: 123),
            windowInfoRow(ownerPID: 42, layer: 3, windowID: 456),
            windowInfoRow(ownerPID: 99, layer: 3, windowID: 789),
            windowInfoRow(ownerPID: 42, layer: 3, windowID: 321, alpha: 0),
        ]

        let ids = RecipientOverlayCaptureExclusion.overlayCaptureWindowIDs(rows: rows, ownerPID: 42)

        #expect(ids == Set([CGWindowID(456)]))
    }

    private func windowInfoRow(
        ownerPID: Int,
        layer: Int,
        windowID: UInt32,
        width: Double = 1180,
        height: Double = 760,
        alpha: Double = 1
    ) -> [String: Any] {
        [
            kCGWindowOwnerPID as String: NSNumber(value: ownerPID),
            kCGWindowLayer as String: NSNumber(value: layer),
            kCGWindowNumber as String: NSNumber(value: windowID),
            kCGWindowIsOnscreen as String: true,
            kCGWindowAlpha as String: NSNumber(value: alpha),
            kCGWindowBounds as String: [
                "Width": NSNumber(value: width),
                "Height": NSNumber(value: height),
            ],
        ]
    }
}

struct CueOverlayTakeStartPolicyTests {
    @Test
    func visibleUnprovenOverlayRunsSafetyCheckAndFailedReceiptBlocksRecording() {
        #expect(CueOverlayTakeStartPolicy.shouldRunSafetyCheck(
            bundleLoaded: true,
            interactionState: .readThrough,
            overlayProductionEnabled: false
        ))

        let receipt = ExclusionPreflightReceipt(
            generatedAt: Date(timeIntervalSince1970: 0),
            passed: false,
            appBuildID: "test",
            captureFilterGeneration: "generation",
            displayTopology: [1],
            overlayWindowNumbers: [42],
            deckSourceHash: "deck",
            pathResults: [],
            staleReason: "sentinel_pixels_present_in_capture"
        )

        let warning = CueOverlayTakeStartPolicy.visibilityWarning(for: receipt)

        #expect(warning?.contains("Cue overlay blocked recording") == true)
        #expect(warning?.contains("sentinel_pixels_present_in_capture") == true)
    }

    @Test
    func hiddenOverlayDoesNotRunSafetyCheckAtTakeStart() {
        #expect(CueOverlayTakeStartPolicy.shouldRunSafetyCheck(
            bundleLoaded: true,
            interactionState: .hidden,
            overlayProductionEnabled: false
        ) == false)
    }

    @Test
    func currentProductionProofDoesNotWarnAtTakeStart() {
        let receipt = ExclusionPreflightReceipt(
            generatedAt: Date(timeIntervalSince1970: 0),
            passed: true,
            appBuildID: "test",
            captureFilterGeneration: "generation",
            displayTopology: [1],
            overlayWindowNumbers: [42],
            deckSourceHash: "deck",
            pathResults: [],
            staleReason: nil
        )

        #expect(CueOverlayTakeStartPolicy.visibilityWarning(for: receipt) == nil)
    }

    @Test
    func productionGateKeepsLockedCuesVisibleWhenActiveTakeProofStalesAfterStart() {
        #expect(CueOverlayProductionGate.shouldHideCues(
            isRecording: true,
            exclusionReceiptCurrent: false,
            recordingCueVisibilityLocked: true
        ) == false)
    }

    @Test
    func productionGateHidesCuesWhenRecordingWasNotVisibilityLocked() {
        #expect(CueOverlayProductionGate.shouldHideCues(
            isRecording: true,
            exclusionReceiptCurrent: false,
            recordingCueVisibilityLocked: false
        ))
    }

    @Test
    func productionGateDoesNotHideCuesOutsideRecording() {
        #expect(CueOverlayProductionGate.shouldHideCues(
            isRecording: false,
            exclusionReceiptCurrent: false,
            recordingCueVisibilityLocked: false
        ) == false)
    }

    @Test
    func topologyChangeKeepsVisiblePreRecordingOverlayState() {
        #expect(CueOverlayTopologyChangePolicy.nextInteractionStateAfterDisplayChange(
            currentState: .readThrough
        ) == .readThrough)
        #expect(CueOverlayTopologyChangePolicy.nextInteractionStateAfterDisplayChange(
            currentState: .arrange
        ) == .arrange)
        #expect(CueOverlayTopologyChangePolicy.visibilityMessageAfterDisplayChange(
            isRecording: false,
            currentState: .readThrough
        )?.contains("stayed visible") == true)
    }

    @Test
    func topologyChangePreservesHiddenPreRecordingOverlayState() {
        #expect(CueOverlayTopologyChangePolicy.nextInteractionStateAfterDisplayChange(
            currentState: .hidden
        ) == .hidden)
        #expect(CueOverlayTopologyChangePolicy.visibilityMessageAfterDisplayChange(
            isRecording: false,
            currentState: .hidden
        ) == nil)
    }
}
