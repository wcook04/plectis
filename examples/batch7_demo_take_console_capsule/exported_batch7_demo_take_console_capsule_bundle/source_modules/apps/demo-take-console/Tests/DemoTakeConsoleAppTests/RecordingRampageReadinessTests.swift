import Foundation
import Testing
@testable import DemoTakeConsoleApp

struct RecordingRampageReadinessTests {
    @Test
    func currentRecordingWindowLoadsSpeakableCueDecks() throws {
        let recipientIDs = [
            "tomas_petricek",
            "inkandswitch_pvh",
            "inkandswitch_geoffrey_litt",
            "simon_willison",
            "anca_dragan",
            "swe_agent_kilian_lieret",
            "swe_agent_carlos_jimenez",
        ]

        let snapshot = try RecipientQueueLoader.loadSnapshot(repoRoot: Self.repoRoot)
        #expect(snapshot.sourceKind == .primaryGeneratedQueue)

        let rowsByID = Dictionary(uniqueKeysWithValues: snapshot.rows.map { ($0.recipientID, $0) })
        let rows = try recipientIDs.map { recipientID in
            try #require(rowsByID[recipientID])
        }

        #expect(rows.map(\.recordingOrder) == Array(30...36))

        for row in rows {
            #expect(row.contentReadiness.recordable)
            #expect(row.contentReadiness.status == "full_cue_deck")
            #expect(row.contentReadiness.missingAuthoringCount == 0)

            let bundle = try RecipientCueDeckLoader.load(repoRoot: Self.repoRoot, recipientID: row.recipientID)
            #expect(!bundle.cards.isEmpty)
            #expect(!bundle.scriptBlocks.isEmpty)

            let visibleBlocks = ScriptBlockTeleprompterOrder
                .speakableFirst(bundle.scriptBlocks)
                .visibleBlocks
            let firstBlock = try #require(visibleBlocks.first)
            #expect(firstBlock.kind == .say || firstBlock.kind == .spoken)
            #expect(!firstBlock.text.localizedCaseInsensitiveContains("mic surface"))
            #expect(!firstBlock.text.localizedCaseInsensitiveContains("record-time preflight"))
        }
    }

    private static var repoRoot: URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent() // DemoTakeConsoleAppTests
            .deletingLastPathComponent() // Tests
            .deletingLastPathComponent() // demo-take-console
            .deletingLastPathComponent() // apps
            .deletingLastPathComponent() // repo root
    }
}
