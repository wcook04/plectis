import CoreGraphics
import Foundation

// MARK: - Operator-private overlay sidecar (contract §7)
//
// On take start/stop the overlay writes a private sidecar into the take package
// (per codex/standards/std_demo_take_package.json::recipient_recording_overlay):
//   state/dissemination/demo_takes/<take_id>/recipient_recording_overlay/
//
// This is LEARNING DATA ONLY. It is not recipient material and confers no send
// authority. The overlay cannot start/stop recording; this writer only records
// what the operator's cue plane did during a take.

/// A single typed transition the sidecar accumulates.
struct OverlayViewTransition: Codable, Equatable {
    var at: Date
    var fromCardIndex: Int
    var toCardIndex: Int
    var sceneID: String?
}

struct OverlayScrollSyncEvent: Codable, Equatable {
    var at: Date
    var cardIndex: Int
    var intraCardFraction: Double
    var leaderDisplayID: UInt32?
}

struct OverlayVisibilityTransition: Codable, Equatable {
    var at: Date
    var state: String // OverlayInteractionState.rawValue
}

struct OverlayGeometryChange: Codable, Equatable {
    var at: Date
    var displayID: UInt32
    var frame: [Double] // [x, y, w, h]
}

/// The full sidecar object.
struct OverlaySidecar: Codable, Equatable {
    var schema: String = "recipient_recording_overlay_sidecar_v0"
    var deckSourceHash: String?
    var selectedRecipient: String?
    var viewTransitions: [OverlayViewTransition]
    var scrollSyncEvents: [OverlayScrollSyncEvent]
    var visibilityTransitions: [OverlayVisibilityTransition]
    var geometryChanges: [OverlayGeometryChange]
    var displayTopology: [UInt32]
    var captureFilterGeneration: String?
    var exclusionPreflightReceipt: ExclusionPreflightReceipt?
    /// True when the take started without a current passing exclusion receipt, so
    /// the cue sheet was held hidden by the fail-closed production gate at start.
    var cuesProductionGatedAtStart: Bool?
    var takeID: String?
    var startedAt: Date?
    var stoppedAt: Date?

    enum CodingKeys: String, CodingKey {
        case schema
        case deckSourceHash = "deck_source_hash"
        case selectedRecipient = "selected_recipient"
        case viewTransitions = "view_transitions"
        case scrollSyncEvents = "scroll_sync_events"
        case visibilityTransitions = "visibility_transitions"
        case geometryChanges = "geometry_changes"
        case displayTopology = "display_topology"
        case captureFilterGeneration = "capture_filter_generation"
        case exclusionPreflightReceipt = "exclusion_preflight_receipt"
        case cuesProductionGatedAtStart = "cues_production_gated_at_start"
        case takeID = "take_id"
        case startedAt = "started_at"
        case stoppedAt = "stopped_at"
    }

    static func empty() -> OverlaySidecar {
        OverlaySidecar(
            deckSourceHash: nil,
            selectedRecipient: nil,
            viewTransitions: [],
            scrollSyncEvents: [],
            visibilityTransitions: [],
            geometryChanges: [],
            displayTopology: [],
            captureFilterGeneration: nil,
            exclusionPreflightReceipt: nil,
            cuesProductionGatedAtStart: nil,
            takeID: nil,
            startedAt: nil,
            stoppedAt: nil
        )
    }
}

/// Writes the overlay sidecar into a take package directory.
enum OverlaySidecarWriter {
    /// `state/dissemination/demo_takes/<take_id>/recipient_recording_overlay/`
    /// We use the take ROOT URL the recorder already owns (which is under that
    /// path) so we land in the same package the recorder created.
    static func sidecarDirectory(takeRoot: URL) -> URL {
        takeRoot.appendingPathComponent("recipient_recording_overlay", isDirectory: true)
    }

    static func write(_ sidecar: OverlaySidecar, takeRoot: URL) throws {
        let dir = sidecarDirectory(takeRoot: takeRoot)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let url = dir.appendingPathComponent("overlay_sidecar.json")
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.dateEncodingStrategy = .iso8601
        let data = try encoder.encode(sidecar)
        try data.write(to: url, options: .atomic)
    }
}
