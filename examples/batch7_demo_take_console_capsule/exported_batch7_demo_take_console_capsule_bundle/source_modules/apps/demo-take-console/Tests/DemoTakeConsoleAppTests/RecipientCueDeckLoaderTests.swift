import Foundation
import Testing
@testable import DemoTakeConsoleApp

struct RecipientCueDeckLoaderTests {
    @Test
    func dynamicAuthorityCardLoadsWhenTranchePackageIsMissing() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("recipient-dynamic-cue-deck-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let authorityURL = root
            .appendingPathComponent("docs", isDirectory: true)
            .appendingPathComponent("dissemination", isDirectory: true)
            .appendingPathComponent("outreach", isDirectory: true)
            .appendingPathComponent("recipient_authority_cards", isDirectory: true)
            .appendingPathComponent("andy_matuschak.json")
        try FileManager.default.createDirectory(
            at: authorityURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try Data("""
        {
          "authority_deck_hash": "fixture_dynamic_hash",
          "boundary": "Private recording only.",
          "cards": [
            {
              "card_id": "andy_matuschak:1:root_navigator_map",
              "order": 1,
              "POINT": "Preserve orientation while changing scale.",
              "See": "Root Navigator focused on one path.",
              "Backend": "Generated projections route back to source.",
              "Lets you": "Choose the next drilldown without treating the map as authority.",
              "proof_cell": {
                "source_refs": {
                  "manifest_path": "docs/dissemination/outreach/proof_rooms/andy_matuschak/MANIFEST.json"
                },
                "proof_branch": {
                  "claim_ceiling": "No live-control claim.",
                  "one_ask": "What should become directly changeable?"
                }
              }
            }
          ]
        }
        """.utf8).write(to: authorityURL)

        let proofRoom = root
            .appendingPathComponent("docs", isDirectory: true)
            .appendingPathComponent("dissemination", isDirectory: true)
            .appendingPathComponent("outreach", isDirectory: true)
            .appendingPathComponent("proof_rooms", isDirectory: true)
            .appendingPathComponent("andy_matuschak", isDirectory: true)
        try FileManager.default.createDirectory(at: proofRoom, withIntermediateDirectories: true)
        try Data("""
        {
          "recipient_name": "Andy Matuschak"
        }
        """.utf8).write(to: proofRoom.appendingPathComponent("MANIFEST.json"))
        try Data("""
        {
          "primary_take": {
            "run_sheet": "<private-obsidian-root>/recording_sidecar/walkthrough_run_sheet_andy_matuschak.md"
          }
        }
        """.utf8).write(to: proofRoom.appendingPathComponent("VIDEO_READINESS_RECEIPT.json"))

        let runSheetURL = root
            .appendingPathComponent("obsidian", isDirectory: true)
            .appendingPathComponent("recording_sidecar", isDirectory: true)
            .appendingPathComponent("walkthrough_run_sheet_andy_matuschak.md")
        try FileManager.default.createDirectory(
            at: runSheetURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try Data("""
        # Walkthrough run sheet

        ## Opening

        - Intro :: Andy, this is one concrete path through the actual screens.
        - Boundary :: This is observability, not live control.
        """.utf8).write(to: runSheetURL)

        let bundle = try RecipientCueDeckLoader.load(
            repoRoot: root,
            recipientID: "andy_matuschak"
        )

        #expect(bundle.recipientID == "andy_matuschak")
        #expect(bundle.recipientName == "Andy Matuschak")
        #expect(bundle.deckSourceHash == "fixture_dynamic_hash")
        #expect(bundle.cards.first?.lines.contains("Preserve orientation while changing scale.") == true)
        #expect(bundle.cards.first?.lines.contains("Guard: No live-control claim.") == true)
        #expect(bundle.scriptBlocks.contains {
            $0.kind == .spoken
                && $0.text == "Intro :: Andy, this is one concrete path through the actual screens."
        })
    }

    @Test
    func generalRunSheetLoadsWithNoPackageOrAuthorityCard() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("general-run-sheet-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let runSheetURL = root
            .appendingPathComponent("obsidian", isDirectory: true)
            .appendingPathComponent("recording_sidecar", isDirectory: true)
            .appendingPathComponent("walkthrough_run_sheet_website_tour.md")
        try FileManager.default.createDirectory(
            at: runSheetURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        // Built via an array so the fenced cue-card block sits at column 0 exactly
        // as the parser expects.
        let md = [
            "---",
            "recording_deliverable: general",
            "title: Website Tour",
            "---",
            "",
            "# Walkthrough run sheet - Website tour",
            "",
            "## Overlay cue cards",
            "",
            "```",
            "0 OPEN   LAND  public map of a workflow system",
            "         SHOW  landing hero",
            "         LIMIT public slice / NEXT the map",
            "1 MAP    LAND  seven areas on one screen",
            "         SHOW  overview map",
            "         LIMIT a record not a runtime",
            "```",
            "",
            "# THE MIC SURFACE - all you speak",
            "",
            "## Open",
            "",
            "- Intro :: This is a public map you can check yourself.",
            "",
            "## Record-time preflight",
            "",
            "- Do not include this line.",
        ].joined(separator: "\n")
        try Data(md.utf8).write(to: runSheetURL)

        // No package directory and no authority card exist: the loader must fall
        // through to the on-disk run sheet.
        let bundle = try RecipientCueDeckLoader.load(repoRoot: root, recipientID: "website_tour")

        #expect(bundle.recipientID == "website_tour")
        #expect(bundle.recipientName == "Website Tour")
        #expect(bundle.deck.schema == "general_run_sheet_overlay_deck_v0")
        #expect(bundle.compressedScript.count == 2)
        #expect(bundle.cards.first?.sceneID == "OPEN")
        #expect(bundle.cards.first?.lines.contains("public map of a workflow system") == true)
        #expect(bundle.cards.first?.lines.contains("Guard: public slice") == true)
        #expect(bundle.scriptBlocks.contains {
            $0.kind == .spoken && $0.text == "Intro :: This is a public map you can check yourself."
        })
        #expect(!bundle.scriptBlocks.contains { $0.text.contains("Do not include this line") })
    }

    @Test
    func generalRunSheetSurfacesSpineAndDoctrineFlash() throws {
        // Regression: the first-principles spine and the public-doctrine flashes are
        // the substance the operator authored. They MUST reach the loaded bundle so
        // the overlay can show them, instead of being dropped on the floor (which
        // left the cue panel showing a bare beat).
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("general-spine-doctrine-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let runSheetURL = root
            .appendingPathComponent("obsidian", isDirectory: true)
            .appendingPathComponent("recording_sidecar", isDirectory: true)
            .appendingPathComponent("walkthrough_run_sheet_theme_t13_mcp_protocol.md")
        try FileManager.default.createDirectory(
            at: runSheetURL.deletingLastPathComponent(), withIntermediateDirectories: true
        )
        let md = [
            "---",
            "recording_deliverable: general",
            "title: T13 - MCP and tool-authority boundary",
            "---",
            "",
            "# Walkthrough run sheet - T13",
            "",
            "## First-principles freestyle spine",
            "",
            "- **Primitive problem:** Tool access without an authority boundary lets injected data escalate into commands.",
            "- **Irreducible objects:** tool authority, scope, approval, rollback, the instruction-data split.",
            "- **Mechanism:** a synthetic replay shows scopes and rollback lining up while instruction stays separate from data.",
            "- **Worked example:** the MCP tool authority replay specimen.",
            "- **Claim ceiling:** not a live MCP server, not a security guarantee.",
            "- **Freestyle recovery line:** this is a boundary specimen, not a live server.",
            "- **Explain-it-to-yourself prompt:** A viewer should be able to say why instruction and data stay separate.",
            "",
            "## Doctrine through-line",
            "",
            "- Primary: AX-3 Authority by derivation, not possession",
            "- Why: the whole clip is the rule that holding a token is not permission.",
            "- Public surface: https://wcook04.github.io/plectis/docs/doctrine.html#dcard-ax-3",
            "",
            "## Doctrine flash per movement",
            "",
            "### Movement 0 - what this is",
            "- Primary: AX-3 Authority by derivation, not possession",
            "- Flash text: authority is derived, never possessed",
            "- Why this beat: opening names the law.",
            "- Screen: the component card.",
            "- Public surface: https://wcook04.github.io/plectis/docs/doctrine.html#dcard-ax-3",
            "- Do not imply: that this is a live server.",
            "### Movement 1 - scopes",
            "- Primary: P-16 Bind authority to transaction scope",
            "- Flash text: authority is the whole transaction",
            "- Why this beat: scope plus approval plus rollback are one bundle.",
            "- Screen: the policy file.",
            "- Public surface: https://wcook04.github.io/plectis/docs/doctrine.html#dcard-p-16",
            "- Do not imply: that references prove enforcement.",
            "",
            "## Overlay cue cards",
            "",
            "```",
            "0 WHAT   LAND  authority is worked out per call",
            "         SHOW  the component card",
            "         DOCTRINE  AX-3  authority is derived, never possessed",
            "         LIMIT not a live server / NEXT scopes",
            "1 SCOPES LAND  scope plus approval plus rollback are one bundle",
            "         SHOW  the policy file",
            "         DOCTRINE  P-16  authority is the whole transaction",
            "         LIMIT references are not enforcement",
            "```",
            "",
            "# THE MIC SURFACE - all you speak",
            "",
            "## Open",
            "",
            "- Intro :: This is a boundary specimen.",
        ].joined(separator: "\n")
        try Data(md.utf8).write(to: runSheetURL)

        let bundle = try RecipientCueDeckLoader.load(repoRoot: root, recipientID: "theme_t13_mcp_protocol")

        // The spine reached the bundle.
        #expect(bundle.spine?.irreducibleObjects?.contains("scope") == true)
        #expect(bundle.spine?.mechanism?.isEmpty == false)
        #expect(bundle.spine?.claimCeiling?.contains("not a live MCP server") == true)
        #expect(bundle.spine?.recoveryLine?.contains("boundary specimen") == true)
        // The through-line law reached the bundle.
        #expect(bundle.doctrineThroughLine?.id == "AX-3")
        #expect(bundle.doctrineThroughLine?.title.contains("Authority by derivation") == true)
        // Per-movement flashes reached the bundle.
        #expect(bundle.doctrineFlashes.count == 2)
        #expect(bundle.doctrineFlashes.first?.id == "AX-3")
        #expect(bundle.doctrineFlashes.first?.flashText == "authority is derived, never possessed")
        #expect(bundle.doctrineFlashes.first?.doNotImply?.contains("live server") == true)
        // Each beat carries its doctrine flash (cue line, enriched with the title).
        #expect(bundle.compressedScript.first?.doctrine?.id == "AX-3")
        #expect(bundle.compressedScript.first?.doctrine?.flashText == "authority is derived, never possessed")
        #expect(bundle.compressedScript.first?.doctrine?.title.contains("Authority by derivation") == true)
        #expect(bundle.compressedScript.last?.doctrine?.id == "P-16")
    }

    @Test
    func onCameraViewPicksDominantStationRoute() {
        // The glance card shows which cockpit view to OPEN; it is the most common
        // /station route in the On-screen views section (ties to first appearance).
        let md = [
            "## On-screen views",
            "### Beat 0",
            "- View: /station/agent-observability Agent Trace",
            "### Beat 1",
            "- View: /station/ledger Ledger",
            "### Beat 2",
            "- View: /station/agent-observability Agent Trace",
        ].joined(separator: "\n")
        #expect(RecipientCueDeckLoader.parseOnCameraView(md) == "/station/agent-observability Agent Trace")
        #expect(RecipientCueDeckLoader.parseOnCameraView("# nothing here") == nil)
    }

    @Test
    func screenCuesPairVisualTargetWithOnScreenReading() {
        let md = [
            "## On-screen views",
            "### Beat 0",
            "- View: /station Surface Atlas",
            "### Beat 1",
            "- View: /station/agent-observability Agent Trace",
            "- On screen: Agent Trace opened on a complete run path.",
            "### Beat 2",
            "- View: https://wcook04.github.io/plectis/docs/",
            "- On screen: the public website page, not a local command.",
        ].joined(separator: "\n")

        let cues = RecipientCueDeckLoader.parseScreenCues(md)

        #expect(cues.count == 3)
        #expect(cues.first?.view == "/station Surface Atlas")
        #expect(cues.first?.teleprompterText == "Station Surface Atlas")
        #expect(cues[1].view == "/station/agent-observability Agent Trace")
        #expect(cues[1].onScreen == "Agent Trace opened on a complete run path.")
        #expect(cues[1].teleprompterText == "Agent Trace")
        #expect(cues.last?.view == "https://wcook04.github.io/plectis/docs/")
        #expect(cues.last?.teleprompterText == "https://wcook04.github.io/plectis/docs/")
        #expect(RecipientCueDeckLoader.parseOnScreenLines(md) == [
            "Agent Trace opened on a complete run path.",
            "the public website page, not a local command.",
        ])
    }

    @Test
    func onCameraViewFallsBackToNonStationVisualTarget() {
        let md = [
            "## On-screen views",
            "### Beat 0",
            "- View: https://wcook04.github.io/plectis/docs/",
            "### Beat 1",
            "- View: Local Agent Trace Structurer app",
            "### Beat 2",
            "- View: https://wcook04.github.io/plectis/docs/",
        ].joined(separator: "\n")

        #expect(RecipientCueDeckLoader.parseOnCameraView(md) == "https://wcook04.github.io/plectis/docs/")
    }

    @Test
    func cueCardRoleDetectionDoesNotSplitNamesContainingRoleText() throws {
        let md = [
            "## Overlay cue cards",
            "",
            "```",
            "0 LANDING      LAND  landed means the recorded HEAD moved",
            "               SHOW  landing receipt with head-before and head-after",
            "               LIMIT attempted, not proven / NEXT route record",
            "```",
        ].joined(separator: "\n")

        let beats = RecipientCueDeckLoader.parseCueCards(md)

        #expect(beats.count == 1)
        #expect(beats.first?.num == "0")
        #expect(beats.first?.name == "LANDING")
        #expect(beats.first?.land == ["landed means the recorded HEAD moved"])
        #expect(beats.first?.show == ["landing receipt with head-before and head-after"])
        #expect(beats.first?.limit == "attempted, not proven")
        #expect(beats.first?.next == "route record")
    }

    @Test
    func undeclaredRunSheetDoesNotLoadThroughGeneralFallback() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("undeclared-run-sheet-\(UUID().uuidString)", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let runSheetURL = root
            .appendingPathComponent("obsidian", isDirectory: true)
            .appendingPathComponent("recording_sidecar", isDirectory: true)
            .appendingPathComponent("walkthrough_run_sheet_terence_tao.md")
        try FileManager.default.createDirectory(
            at: runSheetURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        // A person/outreach sheet that exists on disk and is even well-formed
        // (cue cards + mic surface) but never opted in via front matter. The opt-in
        // gate is on the DECLARATION, not the grammar: it must NOT load as a general
        // deliverable, even when selected directly (e.g. a stale persisted id).
        let md = [
            "# Walkthrough run sheet - Terence Tao cut",
            "",
            "## Overlay cue cards",
            "",
            "```",
            "0 OPEN LAND a person sheet",
            "```",
            "",
            "# THE MIC SURFACE - all you speak",
            "",
            "## Open",
            "",
            "- Intro :: hello",
        ].joined(separator: "\n")
        try Data(md.utf8).write(to: runSheetURL)

        #expect(throws: (any Error).self) {
            try RecipientCueDeckLoader.load(repoRoot: root, recipientID: "terence_tao")
        }
    }

    @Test
    func leadLabeledBulletsBecomeSpokenBlocks() throws {
        let deckData = Data("""
        {
          "recipient_id": "fixture_recipient",
          "recipient_name": "Fixture Recipient",
          "cards": []
        }
        """.utf8)
        let deck = try JSONDecoder().decode(OverlayDeck.self, from: deckData)
        let markdown = """
        # Walkthrough run sheet

        # THE MIC SURFACE - chronological teleprompter

        ## 00:00 Opening

        - Intro :: Beth, I am Will Cook.
        - Hook :: The useful part is the rejection path.

        ## Record-time preflight

        - Do not include this line.
        """

        let blocks = RecipientCueDeckLoader.loadScriptBlocks(
            packageDir: URL(fileURLWithPath: "<host-temp>/nonexistent-recipient-package"),
            repoRoot: URL(fileURLWithPath: "<host-temp>/nonexistent-repo-root"),
            deck: deck,
            markdown: markdown
        )

        #expect(blocks.contains { $0.kind == .heading && $0.text == "00:00 Opening" })
        #expect(blocks.contains { $0.kind == .spoken && $0.text == "Intro :: Beth, I am Will Cook." })
        #expect(blocks.contains { $0.kind == .spoken && $0.text == "Hook :: The useful part is the rejection path." })
        #expect(!blocks.contains { $0.text.contains("Do not include this line") })
    }

    @Test
    func onScreenViewsBecomeInlineViewChangeCues() throws {
        let deckData = Data("""
        {
          "recipient_id": "fixture_recipient",
          "recipient_name": "Fixture Recipient",
          "cards": []
        }
        """.utf8)
        let deck = try JSONDecoder().decode(OverlayDeck.self, from: deckData)
        let markdown = """
        # Walkthrough run sheet

        ## On-screen views

        ### Beat 0
        - View: /station/agent-observability Agent Trace
        - On screen: Agent Trace opened on a complete run path.

        ### Beat 1
        - View: /station/codemap Code Map
        - On screen: Code Map showing the same logic through a second view.

        # THE MIC SURFACE - chronological teleprompter

        ## Open

        - Intro :: Boris, I am going to show you the frontend first.

        ## Follow the trace

        - Trace :: This same run can be read as a trace and as code structure.
        """

        let blocks = RecipientCueDeckLoader.loadScriptBlocks(
            packageDir: URL(fileURLWithPath: "<host-temp>/nonexistent-recipient-package"),
            repoRoot: URL(fileURLWithPath: "<host-temp>/nonexistent-repo-root"),
            deck: deck,
            markdown: markdown
        )

        let spokenBlocks = blocks.filter { $0.kind == .spoken }
        #expect(spokenBlocks.map(\.viewCue) == ["Agent Trace", "Code Map"])
        #expect(spokenBlocks.first?.text == "Intro :: Boris, I am going to show you the frontend first.")
        let ordered = ScriptBlockTeleprompterOrder.speakableFirst(blocks)
        #expect(ordered.visibleBlocks.first?.kind == .spoken)
        #expect(ordered.visibleBlocks.first?.viewCue == "Agent Trace")
        #expect(!ordered.visibleBlocks.contains { $0.kind == .heading })
    }

    @Test
    func repeatedOnScreenViewsOnlyCueWhenTheViewChanges() throws {
        let deckData = Data("""
        {
          "recipient_id": "fixture_recipient",
          "recipient_name": "Fixture Recipient",
          "cards": []
        }
        """.utf8)
        let deck = try JSONDecoder().decode(OverlayDeck.self, from: deckData)
        let markdown = """
        # Walkthrough run sheet

        ## On-screen views

        ### Beat 0
        - View: /station/agent-observability Agent Trace

        ### Beat 1
        - View: /station/agent-observability Agent Trace

        ### Beat 2
        - View: /station/codemap Code Map

        # THE MIC SURFACE - chronological teleprompter

        ## Open

        - Intro :: Open on the trace.

        ## Same view

        - Continue :: Keep the trace open.

        ## Switch view

        - Map :: Now switch to the code map.
        """

        let blocks = RecipientCueDeckLoader.loadScriptBlocks(
            packageDir: URL(fileURLWithPath: "<host-temp>/nonexistent-recipient-package"),
            repoRoot: URL(fileURLWithPath: "<host-temp>/nonexistent-repo-root"),
            deck: deck,
            markdown: markdown
        )

        let spokenBlocks = blocks.filter { $0.kind == .spoken }
        #expect(spokenBlocks.map(\.viewCue) == ["Agent Trace", nil, "Code Map"])
    }

    @Test
    func bareSayLabelsAreNotRenderedAsSpeakableLines() throws {
        let deckData = Data("""
        {
          "recipient_id": "fixture_recipient",
          "recipient_name": "Fixture Recipient",
          "cards": []
        }
        """.utf8)
        let deck = try JSONDecoder().decode(OverlayDeck.self, from: deckData)
        let markdown = """
        # Walkthrough run sheet

        Screen: Root Navigator or a stable focused Root Navigator capture.

        Say:

        - "This is the broad map, but I only want to follow one path through it."
        - "The important thing is not the number of nodes."

        Boundary:

        - Use it for orientation only.
        """

        let blocks = RecipientCueDeckLoader.loadScriptBlocks(
            packageDir: URL(fileURLWithPath: "<host-temp>/nonexistent-recipient-package"),
            repoRoot: URL(fileURLWithPath: "<host-temp>/nonexistent-repo-root"),
            deck: deck,
            markdown: markdown
        )

        #expect(!blocks.contains { $0.kind == .say && $0.text == "Say:" })
        #expect(blocks.contains {
            $0.kind == .spoken
                && $0.text == "This is the broad map, but I only want to follow one path through it."
        })
        #expect(blocks.contains {
            $0.kind == .spoken
                && $0.text == "The important thing is not the number of nodes."
        })
    }
}
