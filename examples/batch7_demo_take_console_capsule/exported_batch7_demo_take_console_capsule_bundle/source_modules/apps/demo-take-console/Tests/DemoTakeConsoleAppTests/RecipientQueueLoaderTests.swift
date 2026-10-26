import Foundation
import Testing
@testable import DemoTakeConsoleApp

struct RecipientQueueLoaderTests {
    @Test
    func fullQueueIsPreferredOverFrozenTranche() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("recipient-queue-loader-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let queueURL = root
            .appendingPathComponent("docs", isDirectory: true)
            .appendingPathComponent("dissemination", isDirectory: true)
            .appendingPathComponent("outreach", isDirectory: true)
            .appendingPathComponent("recipient_recording_overlay_queue_v0.json")
        try FileManager.default.createDirectory(
            at: queueURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try Data("""
        {
          "schema": "recipient_recording_overlay_queue_v0",
          "rows": [
            {
              "recipient_id": "beth_barnes_metr",
              "recipient_name": "Beth Barnes",
              "recording_order": 1,
              "recording_status": "needs_personal_take"
            },
            {
              "recipient_id": "andy_matuschak",
              "recipient_name": "Andy Matuschak",
              "recording_order": 42,
              "recording_status": "needs_personal_take"
            }
          ]
        }
        """.utf8).write(to: queueURL)

        let snapshot = try RecipientQueueLoader.loadSnapshot(repoRoot: root)
        let rows = snapshot.rows

        #expect(snapshot.sourceKind == .primaryGeneratedQueue)
        #expect(rows.map(\.recipientID) == ["beth_barnes_metr", "andy_matuschak"])
        #expect(rows[1].recipientName == "Andy Matuschak")
        #expect(rows[1].isRecordable)
    }

    @Test
    func frozenTrancheRemainsFallbackWhenQueueIsMissing() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("recipient-tranche-fallback-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let specURL = root
            .appendingPathComponent("docs", isDirectory: true)
            .appendingPathComponent("dissemination", isDirectory: true)
            .appendingPathComponent("outreach", isDirectory: true)
            .appendingPathComponent("recording_tranches", isDirectory: true)
            .appendingPathComponent("first_recording_ready_tranche_v0", isDirectory: true)
            .appendingPathComponent("tranche_spec.json")
        try FileManager.default.createDirectory(
            at: specURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try Data("""
        {
          "selected_recipients": [
            {
              "recipient_id": "legacy_recipient",
              "recipient_name": "Legacy Recipient",
              "recording_order": 7
            }
          ]
        }
        """.utf8).write(to: specURL)

        let rows = try RecipientQueueLoader.loadRecipients(repoRoot: root)

        #expect(rows.map(\.recipientID) == ["legacy_recipient"])
        #expect(rows[0].recipientName == "Legacy Recipient")
    }

    @Test
    func validEmptyPrimaryQueueDoesNotFallBackToFrozenTranche() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("recipient-empty-queue-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let queueURL = root
            .appendingPathComponent("docs", isDirectory: true)
            .appendingPathComponent("dissemination", isDirectory: true)
            .appendingPathComponent("outreach", isDirectory: true)
            .appendingPathComponent("recipient_recording_overlay_queue_v0.json")
        try FileManager.default.createDirectory(
            at: queueURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try Data("""
        {
          "schema": "recipient_recording_overlay_queue_v0",
          "generated_at": "2026-06-25T00:00:00Z",
          "rows": []
        }
        """.utf8).write(to: queueURL)
        try writeFallbackTranche(root: root, recipientID: "legacy_recipient")

        let snapshot = try RecipientQueueLoader.loadSnapshot(repoRoot: root)

        #expect(snapshot.sourceKind == .primaryGeneratedQueue)
        #expect(snapshot.rows.isEmpty)
        #expect(snapshot.generatedAt == "2026-06-25T00:00:00Z")
    }

    @Test
    func completedRowsSortAfterUnfinishedRows() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("recipient-done-sort-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let queueURL = root
            .appendingPathComponent("docs", isDirectory: true)
            .appendingPathComponent("dissemination", isDirectory: true)
            .appendingPathComponent("outreach", isDirectory: true)
            .appendingPathComponent("recipient_recording_overlay_queue_v0.json")
        try FileManager.default.createDirectory(
            at: queueURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try Data("""
        {
          "schema": "recipient_recording_overlay_queue_v0",
          "rows": [
            {
              "recipient_id": "beth_barnes_metr",
              "recipient_name": "Beth Barnes",
              "recording_order": 1,
              "recording_status": "recorded_not_send_ready",
              "take_id": "take_20260625_024851",
              "video_path": "state/dissemination/demo_takes/take_20260625_024851/render/rough_cut.mp4"
            },
            {
              "recipient_id": "andy_matuschak",
              "recipient_name": "Andy Matuschak",
              "recording_order": 2,
              "recording_status": "needs_personal_take"
            }
          ]
        }
        """.utf8).write(to: queueURL)

        let rows = try RecipientQueueLoader.loadRecipients(repoRoot: root)

        #expect(rows.map(\.recipientID) == ["andy_matuschak", "beth_barnes_metr"])
        #expect(rows[1].isDoneByProjection)
    }

    @Test
    func malformedPrimaryQueueFallsBackWithDegradedReceipt() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("recipient-degraded-queue-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let queueURL = root
            .appendingPathComponent("docs", isDirectory: true)
            .appendingPathComponent("dissemination", isDirectory: true)
            .appendingPathComponent("outreach", isDirectory: true)
            .appendingPathComponent("recipient_recording_overlay_queue_v0.json")
        try FileManager.default.createDirectory(
            at: queueURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try Data("""
        {
          "schema": "recipient_recording_overlay_queue_v0",
          "rows": [
            {"recipient_name": "Missing ID"}
          ]
        }
        """.utf8).write(to: queueURL)
        try writeFallbackTranche(root: root, recipientID: "legacy_recipient")

        let snapshot = try RecipientQueueLoader.loadSnapshot(repoRoot: root)

        #expect(snapshot.sourceKind == .degradedFrozenTrancheFallback)
        #expect(snapshot.isDegraded)
        #expect(snapshot.rows.map(\.recipientID) == ["legacy_recipient"])
        #expect(snapshot.fallbackReason?.contains("invalid row payloads") == true)
    }

    @Test
    func discoverGeneralRunSheetsSurfacesOnlyDeclaredDeliverables() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("recipient-general-discovery-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let sidecar = root
            .appendingPathComponent("obsidian", isDirectory: true)
            .appendingPathComponent("recording_sidecar", isDirectory: true)
        try FileManager.default.createDirectory(at: sidecar, withIntermediateDirectories: true)

        // A declared general deliverable (front matter opts in, with a title).
        try Data("""
        ---
        recording_deliverable: general
        title: Website tour
        ---

        # Walkthrough run sheet - Website tour
        """.utf8).write(to: sidecar.appendingPathComponent("walkthrough_run_sheet_website_tour.md"))
        // An orphan person sheet with NO marker: must NOT leak into the general lane
        // even though it is not in the queue. This is the 159-orphan guard.
        try Data("# Walkthrough run sheet - Terence Tao cut\n".utf8)
            .write(to: sidecar.appendingPathComponent("walkthrough_run_sheet_terence_tao.md"))
        // A queue recipient's sheet (excluded by id) and the bare app walkthrough.
        try Data("# fixture\n".utf8).write(to: sidecar.appendingPathComponent("walkthrough_run_sheet_simon_willison.md"))
        try Data("# fixture\n".utf8).write(to: sidecar.appendingPathComponent("walkthrough_run_sheet.md"))

        let rows = RecipientQueueLoader.discoverGeneralRunSheets(
            repoRoot: root,
            excludingIDs: ["simon_willison"]
        )

        // Only the DECLARED, non-queue, id-bearing sheet survives: terence_tao has
        // no marker, simon is a queue id, the bare walkthrough has no id.
        #expect(rows.map(\.recipientID) == ["website_tour"])
        #expect(rows[0].kind == .generalDeliverable)
        #expect(rows[0].recipientName == "Website tour") // front-matter title override
        #expect(rows[0].isRecordable)
        #expect(rows[0].runSheetPath == "<private-obsidian-root>/recording_sidecar/walkthrough_run_sheet_website_tour.md")
    }

    @Test
    func generalDeliverablesAppearFirstInTheRecipientMenu() throws {
        // Regression: the Select Recipient menu must always surface on-disk general
        // deliverables, ahead of a long outreach queue (which can be 40+ rows and
        // would otherwise push them off-screen). This locks the discover + merge +
        // group chain the menu bar relies on.
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("recipient-menu-groups-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let queueURL = root
            .appendingPathComponent("docs", isDirectory: true)
            .appendingPathComponent("dissemination", isDirectory: true)
            .appendingPathComponent("outreach", isDirectory: true)
            .appendingPathComponent("recipient_recording_overlay_queue_v0.json")
        try FileManager.default.createDirectory(
            at: queueURL.deletingLastPathComponent(), withIntermediateDirectories: true
        )
        try Data("""
        {
          "schema": "recipient_recording_overlay_queue_v0",
          "rows": [
            {"recipient_id": "jay_baxter", "recipient_name": "Jay Baxter", "recording_order": 1, "recording_status": "needs_personal_take"}
          ]
        }
        """.utf8).write(to: queueURL)

        let sidecar = root
            .appendingPathComponent("obsidian", isDirectory: true)
            .appendingPathComponent("recording_sidecar", isDirectory: true)
        try FileManager.default.createDirectory(at: sidecar, withIntermediateDirectories: true)
        try Data("""
        ---
        recording_deliverable: general
        title: T1 - Core thesis
        ---

        # Walkthrough run sheet - T1
        """.utf8).write(to: sidecar.appendingPathComponent("walkthrough_run_sheet_theme_t1_core_thesis.md"))

        // Mirror what RecipientCueOverlayController.loadRecipientQueue() assembles.
        let snapshot = try RecipientQueueLoader.loadSnapshot(repoRoot: root)
        let queueIDs = Set(snapshot.rows.map(\.recipientID))
        let general = RecipientQueueLoader.discoverGeneralRunSheets(repoRoot: root, excludingIDs: queueIDs)
        let merged = snapshot.rows + general

        let groups = RecipientQueueLoader.menuGroups(merged)
        #expect(groups.general.map(\.recipientID) == ["theme_t1_core_thesis"])
        #expect(groups.general.first?.kind == .generalDeliverable)
        #expect(groups.outreach.map(\.recipientID) == ["jay_baxter"])
        // The deliverable must be present and recordable even with the outreach queue loaded.
        #expect(groups.general.first?.isRecordable == true)
    }

    private func writeFallbackTranche(root: URL, recipientID: String) throws {
        let specURL = root
            .appendingPathComponent("docs", isDirectory: true)
            .appendingPathComponent("dissemination", isDirectory: true)
            .appendingPathComponent("outreach", isDirectory: true)
            .appendingPathComponent("recording_tranches", isDirectory: true)
            .appendingPathComponent("first_recording_ready_tranche_v0", isDirectory: true)
            .appendingPathComponent("tranche_spec.json")
        try FileManager.default.createDirectory(
            at: specURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try Data("""
        {
          "selected_recipients": [
            {
              "recipient_id": "\(recipientID)",
              "recipient_name": "Legacy Recipient",
              "recording_order": 7
            }
          ]
        }
        """.utf8).write(to: specURL)
    }
}
