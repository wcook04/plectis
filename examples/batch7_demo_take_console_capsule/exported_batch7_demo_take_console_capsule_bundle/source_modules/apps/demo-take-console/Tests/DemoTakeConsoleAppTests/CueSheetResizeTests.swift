import CoreGraphics
import Foundation
import Testing
@testable import DemoTakeConsoleApp

/// Covers the cue-panel vertical resize: the pure drag solver (no dead zone), the
/// absolute height ceiling, and visible-viewport scroll math for oversized panels.
@MainActor
struct CueSheetResizeTests {
    private func withClearedDefault(_ key: String, run body: () -> Void) {
        let defaults = UserDefaults.standard
        let previous = defaults.object(forKey: key)
        defaults.removeObject(forKey: key)
        defer {
            if let previous {
                defaults.set(previous, forKey: key)
            } else {
                defaults.removeObject(forKey: key)
            }
        }
        body()
    }

    // MARK: - Drag solver

    @Test
    func dragDownGrowsAndDragUpShrinksWithinTheBand() {
        var drag = CueSheetResizeDrag(startHeight: 400, startPointerY: 500, minHeight: 160, maxHeight: 800)

        // Pointer Y decreases when dragging down → the top-anchored panel grows.
        #expect(drag.resolve(pointerY: 460) == 440)
        // Back up past the start shrinks it again.
        #expect(drag.resolve(pointerY: 540) == 360)
    }

    @Test
    func draggingPastTheCeilingThenReversingRespondsImmediately() {
        var drag = CueSheetResizeDrag(startHeight: 400, startPointerY: 500, minHeight: 160, maxHeight: 800)

        // Drag far past the ceiling: pinned at 800, not 900.
        #expect(drag.resolve(pointerY: 0) == 800)

        // The bug this guards: the OLD absolute math (start + total displacement)
        // would still read 400 + (500 - 50) = 850 → clamped 800, so the panel would
        // not shrink until the cursor returned to the cap. Re-anchoring at the rail
        // makes the very next upward move respond, so a 50pt reverse lands at 750.
        #expect(drag.resolve(pointerY: 50) == 750)
    }

    @Test
    func draggingPastTheFloorThenReversingRespondsImmediately() {
        var drag = CueSheetResizeDrag(startHeight: 300, startPointerY: 500, minHeight: 160, maxHeight: 800)

        // Drag up well past the floor: pinned at 160, not 100.
        #expect(drag.resolve(pointerY: 740) == 160)
        // A small downward reverse grows immediately instead of sitting in a dead zone.
        #expect(drag.resolve(pointerY: 700) == 200)
    }

    @Test
    func solverClampsAnImpossibleStartHeightIntoTheBand() {
        var tooTall = CueSheetResizeDrag(startHeight: 5000, startPointerY: 500, minHeight: 160, maxHeight: 800)
        #expect(tooTall.resolve(pointerY: 500) == 800)

        var tooShort = CueSheetResizeDrag(startHeight: 10, startPointerY: 500, minHeight: 160, maxHeight: 800)
        #expect(tooShort.resolve(pointerY: 500) == 160)
    }

    @Test
    func widthDragMirrorsTheGrabbedSideAroundPanelCenter() {
        var rightSide = CueSheetWidthResizeDrag(
            startWidth: 420,
            startPointerX: 500,
            startLocalX: 120,
            handleMidX: 87,
            minWidth: 320,
            maxWidth: 700
        )

        #expect(rightSide.resolve(pointerX: 530) == 480)
        #expect(rightSide.resolve(pointerX: 490) == 400)

        var leftSide = CueSheetWidthResizeDrag(
            startWidth: 420,
            startPointerX: 500,
            startLocalX: 50,
            handleMidX: 87,
            minWidth: 320,
            maxWidth: 700
        )

        #expect(leftSide.resolve(pointerX: 470) == 480)
        #expect(leftSide.resolve(pointerX: 510) == 400)
    }

    @Test
    func widthDragReversesImmediatelyAfterAWidthRail() {
        var drag = CueSheetWidthResizeDrag(
            startWidth: 600,
            startPointerX: 500,
            startLocalX: 120,
            handleMidX: 87,
            minWidth: 320,
            maxWidth: 700
        )

        #expect(drag.resolve(pointerX: 580) == 700)
        #expect(drag.resolve(pointerX: 560) == 660)
    }

    // MARK: - Height limits

    @Test
    func overlayFloorAllowsCompactCuePanel() {
        #expect(OverlaySession.minSheetHeight <= 80)
    }

    @Test
    func setSheetHeightHonoursTheFloorAndAbsoluteCeiling() {
        let session = OverlaySession()
        session.setMaxSheetHeight(700)

        session.setSheetHeight(40)
        #expect(session.sheetHeight == OverlaySession.minSheetHeight)

        session.setSheetHeight(5000)
        #expect(session.sheetHeight == 700)
    }

    @Test
    func loweringTheAbsoluteCeilingPullsAnOversizedHeightBackDown() {
        let session = OverlaySession()
        session.setMaxSheetHeight(900)
        session.setSheetHeight(880)
        #expect(session.sheetHeight == 880)

        session.setMaxSheetHeight(500)
        #expect(session.maxSheetHeight == 500)
        #expect(session.sheetHeight == 500)
    }

    @Test
    func raisingTheCeilingLeavesACurrentHeightUntouched() {
        let session = OverlaySession()
        session.setMaxSheetHeight(500)
        session.setSheetHeight(420)

        session.setMaxSheetHeight(900)
        #expect(session.maxSheetHeight == 900)
        #expect(session.sheetHeight == 420)
    }

    @Test
    func ceilingNeverDropsBelowTheReadableFloor() {
        let session = OverlaySession()
        session.setMaxSheetHeight(10)
        #expect(session.maxSheetHeight == OverlaySession.minSheetHeight)
    }

    @Test
    func setSheetWidthHonoursTheFloorAndAbsoluteCeiling() {
        withClearedDefault("RecipientCueOverlay.sheetWidth") {
            let session = OverlaySession()
            session.setMaxSheetWidth(620)

            session.setSheetWidth(40)
            #expect(session.sheetWidth == OverlaySession.minSheetWidth)

            session.setSheetWidth(5000)
            #expect(session.sheetWidth == 620)
        }
    }

    @Test
    func loweringWidthCeilingPullsOversizedWidthBackDown() {
        withClearedDefault("RecipientCueOverlay.sheetWidth") {
            let session = OverlaySession()
            session.setMaxSheetWidth(800)
            session.setSheetWidth(760)
            #expect(session.sheetWidth == 760)

            session.setMaxSheetWidth(500)
            #expect(session.maxSheetWidth == 500)
            #expect(session.sheetWidth == 500)
        }
    }

    @Test
    func cueTextScaleHonoursReadableRails() {
        withClearedDefault("RecipientCueOverlay.cueTextScale") {
            let session = OverlaySession()

            session.setCueTextScale(9)
            #expect(session.cueTextScale == OverlaySession.maxCueTextScale)

            session.adjustCueTextScale(by: -99)
            #expect(session.cueTextScale == OverlaySession.minCueTextScale)
        }
    }

    @Test
    func oversizedSheetUsesVisibleViewportForScrolling() {
        let session = OverlaySession()
        let displayID: CGDirectDisplayID = 42
        session.setSheetHeight(1000)
        session.setVisibleSheetHeight(720, for: displayID)

        // Measured viewport is the full offscreen window body. The effective
        // viewport removes the fixed header/chrome from the visible sheet height,
        // so content hidden below the display remains reachable by scrolling.
        #expect(session.effectiveScrollViewportHeight(for: displayID, measuredViewportHeight: 940) == 660)
    }

    @Test
    func fullyVisibleSheetKeepsMeasuredViewport() {
        let session = OverlaySession()
        let displayID: CGDirectDisplayID = 42
        session.setSheetHeight(500)
        session.setVisibleSheetHeight(500, for: displayID)

        #expect(session.effectiveScrollViewportHeight(for: displayID, measuredViewportHeight: 440) == 440)
    }
}
