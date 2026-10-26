import Foundation
import Testing
@testable import DemoTakeConsoleApp

@MainActor
struct ObservationAtlasControllerTests {
    @Test
    func loadsAtlasPhraseCardsAndRenderedClipPointers() throws {
        let takeRoot = try makeTakeRoot()
        try writePackageSidecars(to: takeRoot)

        let controller = ObservationAtlasController()
        controller.reload(takeRoot: takeRoot)

        #expect(controller.status == .ready)
        #expect(controller.phraseCards.count == 2)
        #expect(controller.chapters.count == 1)
        #expect(controller.candidateClips.count == 1)
        #expect(controller.summaryLine.contains("2 phrase cards"))
        #expect(controller.summaryLine.contains("1 clips"))
        #expect(controller.storageLine.contains("storage efficient"))

        let second = try #require(controller.phraseCards.last)
        #expect(second.id == "phrase_000001")
        #expect(second.seekSeconds == 5.54)
        #expect(second.displayText.contains("marker"))

        let clip = try #require(controller.candidateClips.first)
        #expect(clip.seekSeconds == 5.19)
        #expect(clip.renderedClipURL(in: takeRoot)?.lastPathComponent == "clip_0001_proof_checkpoint_span_proxy.mp4")
    }

    @Test
    func missingAtlasIsNonFatal() throws {
        let takeRoot = try makeTakeRoot()
        let controller = ObservationAtlasController()

        controller.reload(takeRoot: takeRoot)

        #expect(controller.status == .missing)
        #expect(controller.phraseCards.isEmpty)
        #expect(controller.summaryLine == "No browse digest yet.")
    }

    private func makeTakeRoot() throws -> URL {
        let takeRoot = FileManager.default.temporaryDirectory
            .appendingPathComponent("demo-take-atlas-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: takeRoot, withIntermediateDirectories: true)
        return takeRoot
    }

    private func writePackageSidecars(to takeRoot: URL) throws {
        let atlasJSON = """
        {
          "schema": "demo_take_observation_atlas_v0",
          "take_id": "take_test",
          "created_at": "2026-06-09T06:40:43Z",
          "summary": {
            "duration_display": "00:20.100",
            "duration_seconds": 20.1,
            "phrase_card_count": 2,
            "candidate_clip_count": 1,
            "marker_count": 2,
            "transcript_cue_count": 2,
            "transcript_coverage_ratio": 0.76,
            "storage": {
              "storage_profile": "efficient",
              "proxy_state": "proxy_ready",
              "local_raw_state": "local_raw_present",
              "cloud_state": "archive_missing"
            }
          },
          "chapters": [
            {
              "id": "chapter_0000",
              "title": "Checkpoint span",
              "display_time": "00:05.775-00:16.136",
              "duration_seconds": 10.361,
              "active_start_seconds": 5.775,
              "active_end_seconds": 16.136,
              "phrase_card_count": 2,
              "phrase_card_ids": ["phrase_000000", "phrase_000001"],
              "candidate_clip_refs": ["clip_0001_proof_checkpoint_span"],
              "representative_frame": "frames/phrase_cards/phrase_000001_mid.jpg"
            }
          ],
          "phrase_card_index": [],
          "candidate_clip_index": [
            {
              "id": "clip_0001_proof_checkpoint_span",
              "clip_kind": "proof_moment",
              "display_time": "00:05.775-00:16.136",
              "view_label": "Checkpoint span",
              "score": 0.65,
              "public_safe": true,
              "render_receipt": "render/clips/clip_0001_proof_checkpoint_span_proxy_receipt.json",
              "safe_render_range": {
                "start_seconds": 5.19,
                "end_seconds": 16.136
              }
            }
          ]
        }
        """
        try Data(atlasJSON.utf8).write(to: takeRoot.appendingPathComponent("observation_atlas.json"))

        let phraseCards = """
        {"id":"phrase_000000","take_id":"take_test","display_time":"00:00.760-00:05.100","active_start_seconds":0.76,"active_end_seconds":5.1,"text":"Hello test.","representative_frame":"frames/phrase_cards/phrase_000000_mid.jpg","candidate_clip_refs":[],"audio_summary":{"speech_confidence":0.8},"visual_summary":{"motion_kind":"no_visual_events"}}
        {"id":"phrase_000001","take_id":"take_test","display_time":"00:05.540-00:11.680","active_start_seconds":5.54,"active_end_seconds":11.68,"text":"Checkpoint marker phrase.","representative_frame":"frames/phrase_cards/phrase_000001_mid.jpg","candidate_clip_refs":["clip_0001_proof_checkpoint_span"],"audio_summary":{"speech_confidence":0.9},"visual_summary":{"motion_kind":"no_visual_events"}}
        """
        try Data(phraseCards.utf8).write(to: takeRoot.appendingPathComponent("phrase_cards.jsonl"))

        let clipURL = takeRoot.appendingPathComponent("render/clips/clip_0001_proof_checkpoint_span_proxy.mp4")
        try FileManager.default.createDirectory(at: clipURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        try Data("fake clip".utf8).write(to: clipURL)
    }
}
