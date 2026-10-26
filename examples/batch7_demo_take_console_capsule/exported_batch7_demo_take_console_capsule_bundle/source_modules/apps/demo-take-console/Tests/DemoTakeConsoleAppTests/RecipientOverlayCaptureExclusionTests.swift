import CoreGraphics
import Foundation
import Testing
@testable import DemoTakeConsoleApp

struct RecipientOverlayCaptureExclusionTests {
    @Test
    func publicCaptureWindowIDKeepsVisibleLayerZeroOwnWindow() {
        let row = windowInfoRow(ownerPID: 42, layer: 0, windowID: 123)

        let id = RecipientOverlayCaptureExclusion.publicCaptureWindowID(from: row, ownerPID: 42)

        #expect(id == CGWindowID(123))
    }

    @Test
    func publicCaptureWindowIDRejectsOverlayLayerWindow() {
        let row = windowInfoRow(ownerPID: 42, layer: 3, windowID: 123)

        let id = RecipientOverlayCaptureExclusion.publicCaptureWindowID(from: row, ownerPID: 42)

        #expect(id == nil)
    }

    @Test
    func publicCaptureWindowIDRejectsForeignProcessWindow() {
        let row = windowInfoRow(ownerPID: 99, layer: 0, windowID: 123)

        let id = RecipientOverlayCaptureExclusion.publicCaptureWindowID(from: row, ownerPID: 42)

        #expect(id == nil)
    }

    @Test
    func publicCaptureWindowIDsFiltersToNormalOwnProcessWindows() {
        let rows = [
            windowInfoRow(ownerPID: 42, layer: 0, windowID: 123),
            windowInfoRow(ownerPID: 42, layer: 3, windowID: 456),
            windowInfoRow(ownerPID: 99, layer: 0, windowID: 789),
            windowInfoRow(ownerPID: 42, layer: 0, windowID: 321, width: 12, height: 12),
        ]

        let ids = RecipientOverlayCaptureExclusion.publicCaptureWindowIDs(rows: rows, ownerPID: 42)

        #expect(ids == Set([CGWindowID(123)]))
    }

    @Test
    func overlayCaptureWindowIDRejectsVisibleLayerZeroOwnWindow() {
        let row = windowInfoRow(ownerPID: 42, layer: 0, windowID: 123)

        let id = RecipientOverlayCaptureExclusion.overlayCaptureWindowID(from: row, ownerPID: 42)

        #expect(id == nil)
    }

    @Test
    func overlayCaptureWindowIDKeepsPrivateOwnOverlayWindow() {
        let row = windowInfoRow(ownerPID: 42, layer: 3, windowID: 456)

        let id = RecipientOverlayCaptureExclusion.overlayCaptureWindowID(from: row, ownerPID: 42)

        #expect(id == CGWindowID(456))
    }

    @Test
    func overlayCaptureWindowIDsFilterToPrivateOwnWindowsOnly() {
        let rows = [
            windowInfoRow(ownerPID: 42, layer: 0, windowID: 123),
            windowInfoRow(ownerPID: 42, layer: 3, windowID: 456),
            windowInfoRow(ownerPID: 99, layer: 3, windowID: 789),
            windowInfoRow(ownerPID: 42, layer: 3, windowID: 321, alpha: 0),
        ]

        let ids = RecipientOverlayCaptureExclusion.overlayCaptureWindowIDs(rows: rows, ownerPID: 42)

        #expect(ids == Set([CGWindowID(456)]))
    }

    @Test
    func filterGenerationIncludesOverlayAndPublicWindowSets() {
        let generation = ExclusionSentinel.filterGeneration(
            topology: [2],
            windows: [9],
            publicWindows: [123]
        )

        #expect(generation == "topo[2]/overlay[9]/public[123]")
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
