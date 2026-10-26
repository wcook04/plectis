import Foundation

// MARK: - Recipient queue + tranche projection
//
// The picker lists the full generated recording overlay queue. The frozen tranche
// remains as a compatibility fallback only; the current app should show every
// dossier-backed recipient emitted by recipient_recording_overlay_queue_v0.json.
//
// "Done" is a PROJECTION of the queue row, never an independent checkbox DB:
//   done == (take_id != null && video_path != null)
// A manual override may exist only as a typed correction, never a free toggle.

/// Whether a picker row is an outreach recipient (backed by the generated queue)
/// or a general recording deliverable discovered from an on-disk run sheet that
/// has no queue row (e.g. a website tour, an app walkthrough). The two are loaded
/// and grouped differently but both resolve to a cue bundle.
enum RecipientRowKind: String, Equatable {
    case outreachRecipient = "outreach_recipient"
    case generalDeliverable = "general_deliverable"
}

/// One recipient row, generic over recipient_id. Decoded leniently from either the
/// queue file rows or the tranche spec's selected_recipients.
struct RecipientQueueRow: Equatable, Identifiable {
    var recipientID: String
    var recipientName: String
    var recordingOrder: Int
    var recordingStatus: String?
    var takeID: String?
    var videoPath: String?
    var claimCeiling: String?
    var contentReadiness: RecipientContentReadiness
    var recordingLifecycleStatus: String?
    var projectionHealthStatus: String?
    /// Outreach recipient (queue-backed) vs general deliverable (on-disk run sheet).
    var kind: RecipientRowKind = .outreachRecipient
    /// For general deliverables, the repo-relative path of the run-sheet markdown.
    var runSheetPath: String? = nil

    var id: String { recipientID }

    /// Done is a pure projection of queue state.
    var isDoneByProjection: Bool {
        guard let takeID, !takeID.isEmpty else { return false }
        guard let videoPath, !videoPath.isEmpty else { return false }
        return true
    }

    var isRecordable: Bool {
        contentReadiness.recordable
    }

    var readinessLabel: String {
        switch contentReadiness.status {
        case "full_cue_deck": "full cue deck"
        case "insert_only_usable": "insert-only usable"
        case "authoring_incomplete": "needs authoring"
        case "blocked": "blocked"
        default: contentReadiness.status.replacingOccurrences(of: "_", with: " ")
        }
    }

    var readinessDetail: String {
        if !contentReadiness.blockers.isEmpty {
            return contentReadiness.blockers
                .map { $0.replacingOccurrences(of: "_", with: " ") }
                .joined(separator: ", ")
        }
        if !contentReadiness.caveats.isEmpty {
            return contentReadiness.caveats
                .map { $0.replacingOccurrences(of: "_", with: " ") }
                .joined(separator: ", ")
        }
        return isRecordable ? "recording surface available" : "not recordable yet"
    }
}

struct RecipientContentReadiness: Equatable {
    var status: String
    var recordable: Bool
    var usableMode: String?
    var blockers: [String]
    var caveats: [String]
    var cardCount: Int?
    var cueCardCount: Int?
    var missingAuthoringCount: Int?

    static let legacyRecordable = RecipientContentReadiness(
        status: "insert_only_usable",
        recordable: true,
        usableMode: "compatibility_fallback",
        blockers: [],
        caveats: ["readiness_not_present_in_legacy_source"],
        cardCount: nil,
        cueCardCount: nil,
        missingAuthoringCount: nil
    )
}

enum RecipientQueueSourceKind: String, Equatable {
    case primaryGeneratedQueue = "primary_generated_queue"
    case frozenTrancheFallback = "frozen_tranche_fallback"
    case degradedFrozenTrancheFallback = "degraded_frozen_tranche_fallback"
}

struct RecipientQueueSnapshot: Equatable {
    var rows: [RecipientQueueRow]
    var sourceKind: RecipientQueueSourceKind
    var schema: String?
    var generatedAt: String?
    var sourcePath: String
    var fallbackReason: String?
    var diagnostics: [String]

    var isDegraded: Bool {
        sourceKind == .degradedFrozenTrancheFallback || !diagnostics.isEmpty
    }

    var projectionHealthStatus: String {
        switch sourceKind {
        case .primaryGeneratedQueue:
            diagnostics.isEmpty ? "primary_generated_snapshot" : "stale_or_degraded_snapshot"
        case .frozenTrancheFallback:
            "compatibility_fallback"
        case .degradedFrozenTrancheFallback:
            "degraded_snapshot_fallback"
        }
    }

    var countLine: String {
        "\(rows.count) recipients"
    }
}

/// A typed manual correction to the projected done-state. This is the only allowed
/// override; it is itself an auditable record, not a hidden boolean.
struct RecipientDoneOverride: Codable, Equatable {
    var recipientID: String
    var takeID: String?
    var timestamp: Date
    var reason: String
    var markDone: Bool
}

enum RecipientQueueLoaderError: Error, CustomStringConvertible {
    case queueProjectionUnreadable(String)
    case unsupportedQueueSchema(String)
    case trancheSpecMissing(String)
    case trancheSpecUnreadable(String)

    var description: String {
        switch self {
        case .queueProjectionUnreadable(let d): "recipient_recording_overlay_queue_v0.json could not be read: \(d)"
        case .unsupportedQueueSchema(let d): "recipient_recording_overlay_queue_v0.json has unsupported schema: \(d)"
        case .trancheSpecMissing(let p): "tranche_spec.json not found: \(p)"
        case .trancheSpecUnreadable(let d): "tranche_spec.json could not be read: \(d)"
        }
    }
}

enum RecipientQueueLoader {
    /// The full generated recording queue, with the frozen tranche as a fallback
    /// for old checkouts. Returns rows sorted: unfinished by recording_order
    /// ascending, completed below.
    static func loadRecipients(repoRoot: URL) throws -> [RecipientQueueRow] {
        try loadSnapshot(repoRoot: repoRoot).rows
    }

    /// Load the recording workbench snapshot, preserving source/provenance and
    /// diagnostics so the UI can distinguish catalog visibility from readiness.
    static func loadSnapshot(repoRoot: URL) throws -> RecipientQueueSnapshot {
        let url = queueURL(repoRoot: repoRoot)
        guard FileManager.default.fileExists(atPath: url.path) else {
            return try loadFallbackSnapshot(
                repoRoot: repoRoot,
                reason: "primary_queue_missing",
                degraded: false
            )
        }
        do {
            return try loadPrimarySnapshot(repoRoot: repoRoot, url: url)
        } catch let primaryError {
            do {
                return try loadFallbackSnapshot(
                    repoRoot: repoRoot,
                    reason: String(describing: primaryError),
                    degraded: true
                )
            } catch {
                throw primaryError
            }
        }
    }

    /// Compatibility fallback: the 12 recording-ready recipients from the frozen
    /// tranche, ordered by the tranche `recording_order`, then enriched with
    /// done-state from the campaign queue file.
    static func loadTranche(
        repoRoot: URL,
        trancheID: String = RecipientCueDeckLoader.defaultTrancheID
    ) throws -> [RecipientQueueRow] {
        let trancheRoot = RecipientCueDeckLoader.trancheRoot(repoRoot: repoRoot, trancheID: trancheID)
        let specURL = trancheRoot.appendingPathComponent("tranche_spec.json")
        guard FileManager.default.fileExists(atPath: specURL.path) else {
            throw RecipientQueueLoaderError.trancheSpecMissing(specURL.path)
        }
        let data: Data
        do {
            data = try Data(contentsOf: specURL)
        } catch {
            throw RecipientQueueLoaderError.trancheSpecUnreadable(error.localizedDescription)
        }
        guard let root = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
              let selected = root["selected_recipients"] as? [[String: Any]]
        else {
            throw RecipientQueueLoaderError.trancheSpecUnreadable("missing selected_recipients")
        }

        // Enrich done-state from the campaign queue when available.
        let queueByID = (try? loadQueueRowsByID(repoRoot: repoRoot)) ?? [:]

        var rows: [RecipientQueueRow] = selected.compactMap { entry in
            guard let id = entry["recipient_id"] as? String else { return nil }
            let order = (entry["recording_order"] as? Int) ?? Int.max
            let name = (entry["recipient_name"] as? String) ?? id
            let queued = queueByID[id]
            return RecipientQueueRow(
                recipientID: id,
                recipientName: name,
                recordingOrder: order,
                recordingStatus: queued?.recordingStatus ?? (entry["recording_status"] as? String),
                takeID: queued?.takeID,
                videoPath: queued?.videoPath,
                claimCeiling: queued?.claimCeiling ?? (entry["claim_ceiling"] as? String),
                contentReadiness: queued?.contentReadiness ?? .legacyRecordable,
                recordingLifecycleStatus: queued?.recordingLifecycleStatus ?? "needs_take",
                projectionHealthStatus: queued?.projectionHealthStatus ?? "compatibility_fallback"
            )
        }

        rows.sort(by: sortOrder)
        return rows
    }

    /// Sort: unfinished first (by recording_order ascending), completed below.
    static func sortOrder(_ a: RecipientQueueRow, _ b: RecipientQueueRow) -> Bool {
        if a.isDoneByProjection != b.isDoneByProjection {
            return !a.isDoneByProjection // unfinished before done
        }
        if a.recordingOrder != b.recordingOrder {
            return a.recordingOrder < b.recordingOrder
        }
        return a.recipientID < b.recipientID
    }

    private static func queueURL(repoRoot: URL) -> URL {
        repoRoot
            .appendingPathComponent("docs", isDirectory: true)
            .appendingPathComponent("dissemination", isDirectory: true)
            .appendingPathComponent("outreach", isDirectory: true)
            .appendingPathComponent("recipient_recording_overlay_queue_v0.json")
    }

    private static func loadPrimarySnapshot(repoRoot: URL, url: URL) throws -> RecipientQueueSnapshot {
        let data: Data
        do {
            data = try Data(contentsOf: url)
        } catch {
            throw RecipientQueueLoaderError.queueProjectionUnreadable(error.localizedDescription)
        }
        guard let root = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] else {
            throw RecipientQueueLoaderError.queueProjectionUnreadable("invalid JSON object")
        }
        let schema = root["schema"] as? String
        guard schema == "recipient_recording_overlay_queue_v0" else {
            throw RecipientQueueLoaderError.unsupportedQueueSchema(schema ?? "missing")
        }
        guard let rawRows = root["rows"] as? [[String: Any]] else {
            throw RecipientQueueLoaderError.queueProjectionUnreadable("missing rows")
        }
        var rows: [RecipientQueueRow] = []
        var invalid: [String] = []
        for (index, raw) in rawRows.enumerated() {
            if let row = decodeQueueRow(raw) {
                rows.append(row)
            } else {
                invalid.append("rows[\(index)]")
            }
        }
        if !invalid.isEmpty {
            throw RecipientQueueLoaderError.queueProjectionUnreadable(
                "invalid row payloads: \(invalid.joined(separator: ", "))"
            )
        }
        return RecipientQueueSnapshot(
            rows: rows.sorted(by: sortOrder),
            sourceKind: .primaryGeneratedQueue,
            schema: schema,
            generatedAt: root["generated_at"] as? String,
            sourcePath: url.path,
            fallbackReason: nil,
            diagnostics: []
        )
    }

    private static func loadFallbackSnapshot(
        repoRoot: URL,
        reason: String,
        degraded: Bool
    ) throws -> RecipientQueueSnapshot {
        let rows = try loadTranche(repoRoot: repoRoot)
        return RecipientQueueSnapshot(
            rows: rows,
            sourceKind: degraded ? .degradedFrozenTrancheFallback : .frozenTrancheFallback,
            schema: "recipient_recording_tranche_spec_v0",
            generatedAt: nil,
            sourcePath: RecipientCueDeckLoader
                .trancheRoot(repoRoot: repoRoot, trancheID: RecipientCueDeckLoader.defaultTrancheID)
                .appendingPathComponent("tranche_spec.json")
                .path,
            fallbackReason: reason,
            diagnostics: degraded ? [reason] : []
        )
    }

    /// Read every campaign row from the generated queue file.
    static func loadQueueRows(repoRoot: URL) throws -> [RecipientQueueRow] {
        let url = queueURL(repoRoot: repoRoot)
        guard FileManager.default.fileExists(atPath: url.path) else { return [] }
        return try loadPrimarySnapshot(repoRoot: repoRoot, url: url).rows
    }

    /// Read every campaign row from the queue file, keyed by recipient_id. Used to
    /// project done-state onto the frozen-tranche fallback.
    static func loadQueueRowsByID(repoRoot: URL) throws -> [String: RecipientQueueRow] {
        var byID: [String: RecipientQueueRow] = [:]
        for row in try loadQueueRows(repoRoot: repoRoot) {
            byID[row.recipientID] = row
        }
        return byID
    }

    private static func decodeQueueRow(_ raw: [String: Any]) -> RecipientQueueRow? {
        guard let id = raw["recipient_id"] as? String else { return nil }
        return RecipientQueueRow(
            recipientID: id,
            recipientName: (raw["recipient_name"] as? String) ?? id,
            recordingOrder: (raw["recording_order"] as? Int) ?? Int.max,
            recordingStatus: raw["recording_status"] as? String,
            takeID: raw["take_id"] as? String,
            videoPath: raw["video_path"] as? String,
            claimCeiling: raw["claim_ceiling"] as? String,
            contentReadiness: decodeContentReadiness(raw),
            recordingLifecycleStatus: raw["recording_lifecycle"] as? String,
            projectionHealthStatus: raw["projection_health"] as? String
        )
    }

    private static func decodeContentReadiness(_ raw: [String: Any]) -> RecipientContentReadiness {
        let workbench = raw["workbench_state"] as? [String: Any]
        let nested = workbench?["content_readiness"] as? [String: Any]
        let status = (nested?["status"] as? String) ?? (raw["content_readiness"] as? String) ?? "insert_only_usable"
        let blockers = nested?["blockers"] as? [String] ?? []
        let caveats = nested?["caveats"] as? [String] ?? []
        let recordable = (nested?["recordable"] as? Bool) ?? (status != "authoring_incomplete" && status != "blocked")
        return RecipientContentReadiness(
            status: status,
            recordable: recordable,
            usableMode: nested?["usable_mode"] as? String,
            blockers: blockers,
            caveats: caveats,
            cardCount: nested?["card_count"] as? Int,
            cueCardCount: nested?["cue_card_count"] as? Int,
            missingAuthoringCount: nested?["missing_authoring_count"] as? Int
        )
    }

    // MARK: - General deliverable discovery (on-disk run sheets)
    //
    // Architectural fix for the gap where a walkthrough run sheet dropped into the
    // recording sidecar was invisible unless it happened to match an outreach
    // recipient_id. Any `walkthrough_run_sheet_<id>.md` whose <id> is NOT already a
    // queue row becomes a selectable general deliverable, so the picker reflects the
    // run sheets that actually exist on disk. This is generic: it surfaces every
    // non-queue run sheet, not one named instance.

    static let recordingSidecarRelDir = "<private-obsidian-root>/recording_sidecar"

    /// Grouping for the Select Recipient menu. General deliverables ALWAYS come
    /// first: they are what the operator records right now, and the outreach queue
    /// can be 40+ rows long, which would otherwise push the deliverables off the
    /// bottom of a full-height menu. Outreach rows keep their existing (sorted)
    /// order. Pure and order-preserving so the menu view and its regression test
    /// agree on what "first" means.
    static func menuGroups(
        _ rows: [RecipientQueueRow]
    ) -> (general: [RecipientQueueRow], outreach: [RecipientQueueRow]) {
        (
            rows.filter { $0.kind == .generalDeliverable },
            rows.filter { $0.kind == .outreachRecipient }
        )
    }
    private static let runSheetPrefix = "walkthrough_run_sheet_"
    private static let runSheetSuffix = ".md"

    /// Repo-relative path of the run-sheet markdown for a given deliverable id.
    static func generalRunSheetRelPath(_ id: String) -> String {
        "\(recordingSidecarRelDir)/\(runSheetPrefix)\(id)\(runSheetSuffix)"
    }

    /// Title-case a run-sheet id ("website_tour" -> "Website Tour") for display.
    static func generalDisplayName(_ id: String) -> String {
        let words = id.split(whereSeparator: { $0 == "_" || $0 == "-" })
        guard !words.isEmpty else { return id }
        return words.map { $0.prefix(1).uppercased() + $0.dropFirst() }.joined(separator: " ")
    }

    /// Discover general-deliverable run sheets on disk. A run sheet is a general
    /// deliverable ONLY if it opts in via YAML front matter (see
    /// `generalDeliverableDeclaration`). This is deliberate: the recording sidecar
    /// holds ~190 run sheets, the overwhelming majority of which are person/outreach
    /// sheets reached through the outreach queue, not the picker's General
    /// deliverables group. Without the opt-in marker, every person sheet whose
    /// queue row happens to be absent would leak into the public/general lane (159
    /// of them, as of the greenline batch). Excludes ids already in the queue and
    /// the bare `walkthrough_run_sheet.md` (the app walkthrough has no id).
    static func discoverGeneralRunSheets(repoRoot: URL, excludingIDs: Set<String>) -> [RecipientQueueRow] {
        let dir = repoRoot.appendingPathComponent(recordingSidecarRelDir, isDirectory: true)
        let fm = FileManager.default
        guard let entries = try? fm.contentsOfDirectory(atPath: dir.path) else { return [] }
        var rows: [RecipientQueueRow] = []
        var order = 1
        for name in entries.sorted() {
            guard name.hasPrefix(runSheetPrefix), name.hasSuffix(runSheetSuffix) else { continue }
            let id = String(name.dropFirst(runSheetPrefix.count).dropLast(runSheetSuffix.count))
            guard !id.isEmpty, !excludingIDs.contains(id) else { continue }
            let declaration = generalDeliverableDeclaration(at: dir.appendingPathComponent(name))
            guard declaration.declared else { continue }
            let readiness = RecipientContentReadiness(
                status: "general_run_sheet",
                recordable: true,
                usableMode: "general_deliverable",
                blockers: [],
                caveats: [],
                cardCount: nil,
                cueCardCount: nil,
                missingAuthoringCount: nil
            )
            rows.append(RecipientQueueRow(
                recipientID: id,
                recipientName: declaration.title ?? generalDisplayName(id),
                recordingOrder: order,
                recordingStatus: nil,
                takeID: nil,
                videoPath: nil,
                claimCeiling: nil,
                contentReadiness: readiness,
                recordingLifecycleStatus: "general_deliverable",
                projectionHealthStatus: "disk_run_sheet",
                kind: .generalDeliverable,
                runSheetPath: "\(recordingSidecarRelDir)/\(name)"
            ))
            order += 1
        }
        return rows
    }

    /// A run sheet opts into being a general recording deliverable via YAML front
    /// matter at the very top of the file:
    ///
    ///     ---
    ///     recording_deliverable: general
    ///     title: Website tour
    ///     ---
    ///
    /// Person/outreach run sheets carry no such marker and are reached through the
    /// outreach queue, never this lane. Returns whether the sheet declared itself
    /// and an optional display title override. Reads only the file head.
    static func generalDeliverableDeclaration(at url: URL) -> (declared: Bool, title: String?) {
        guard let handle = try? FileHandle(forReadingFrom: url) else { return (false, nil) }
        defer { try? handle.close() }
        let head = (try? handle.read(upToCount: 4096)) ?? Data()
        guard let text = String(data: head, encoding: .utf8) else { return (false, nil) }
        return generalDeliverableDeclaration(inFrontMatterOf: text)
    }

    /// The same declaration parse over already-loaded text. The direct cue-bundle
    /// loader uses this so discovery and load agree on what "declared" means; the
    /// opt-in contract is then enforced at the bundle boundary, not only the picker.
    static func generalDeliverableDeclaration(inFrontMatterOf text: String) -> (declared: Bool, title: String?) {
        let lines = text.components(separatedBy: "\n")
        guard lines.first?.trimmingCharacters(in: .whitespaces) == "---" else { return (false, nil) }
        let positive: Set<String> = ["general", "public", "public_website_tour", "deliverable", "true", "yes"]
        var declared = false
        var title: String? = nil
        for raw in lines.dropFirst() {
            let line = raw.trimmingCharacters(in: .whitespaces)
            if line == "---" { break } // end of front matter
            if let v = frontMatterValue(line, key: "recording_deliverable") {
                declared = positive.contains(v.lowercased())
            } else if let v = frontMatterValue(line, key: "title") {
                title = v
            }
        }
        return (declared, title)
    }

    private static func frontMatterValue(_ line: String, key: String) -> String? {
        guard line.lowercased().hasPrefix(key.lowercased() + ":") else { return nil }
        let value = line.dropFirst(key.count + 1)
            .trimmingCharacters(in: CharacterSet(charactersIn: " \t\"'"))
        return value.isEmpty ? nil : value
    }
}
