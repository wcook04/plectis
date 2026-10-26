import CryptoKit
import Foundation

// MARK: - Cue deck model
//
// Typed, *lenient* decode of the on-disk recipient overlay package. The authority
// files live at
//   docs/dissemination/outreach/recording_tranches/<tranche>/packages/<recipient_id>/
// `overlay_deck.json` carries the glanceable cue cards; `package.json` carries the
// recipient-specific framing (thesis, work bridge, claim guards, identity).
//
// Every field is optional or defaulted so a future deck shape (extra keys, missing
// keys, a different schema) still decodes what is present rather than failing the
// whole take. We decode what we can and surface gaps as honest empties, never
// fabricated text. This mirrors backend contract §1 ("honest author-time gaps,
// never fabricated").

/// One glanceable cue card. Terse key points the operator reads, not prose.
struct CueCard: Codable, Identifiable, Equatable {
    var sceneID: String
    var lines: [String]
    var visibleObject: String?
    var fallbackIfViewFails: String?
    var transition: String?
    var timeBudget: CueTimeBudget?

    var id: String { sceneID }

    enum CodingKeys: String, CodingKey {
        case sceneID = "scene_id"
        case lines
        case visibleObject = "visible_object"
        case fallbackIfViewFails = "fallback_if_view_fails"
        case transition
        case timeBudget = "time_budget"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        sceneID = (try? c.decode(String.self, forKey: .sceneID)) ?? "unnamed_scene"
        lines = (try? c.decode([String].self, forKey: .lines)) ?? []
        visibleObject = try? c.decodeIfPresent(String.self, forKey: .visibleObject)
        fallbackIfViewFails = try? c.decodeIfPresent(String.self, forKey: .fallbackIfViewFails)
        transition = try? c.decodeIfPresent(String.self, forKey: .transition)
        timeBudget = try? c.decodeIfPresent(CueTimeBudget.self, forKey: .timeBudget)
    }

    init(
        sceneID: String,
        lines: [String],
        visibleObject: String? = nil,
        fallbackIfViewFails: String? = nil,
        transition: String? = nil,
        timeBudget: CueTimeBudget? = nil
    ) {
        self.sceneID = sceneID
        self.lines = lines
        self.visibleObject = visibleObject
        self.fallbackIfViewFails = fallbackIfViewFails
        self.transition = transition
        self.timeBudget = timeBudget
    }

    /// Split `lines` into the loose speech / do / guard groups the cue text carries.
    /// The deck encodes the group as a `Do:` / `Guard:` prefix; everything else is
    /// a speech key point. We classify by prefix, never by reordering.
    var classifiedLines: [ClassifiedCueLine] {
        lines.map { raw in
            let trimmed = raw.trimmingCharacters(in: .whitespaces)
            if let body = strip(prefix: "Do:", from: trimmed) {
                return ClassifiedCueLine(group: .operatorRail, text: body)
            }
            if let body = strip(prefix: "Guard:", from: trimmed) {
                return ClassifiedCueLine(group: .guardStrip, text: body)
            }
            return ClassifiedCueLine(group: .speech, text: trimmed)
        }
    }

    private func strip(prefix: String, from value: String) -> String? {
        guard value.lowercased().hasPrefix(prefix.lowercased()) else { return nil }
        return String(value.dropFirst(prefix.count)).trimmingCharacters(in: .whitespaces)
    }
}

struct ClassifiedCueLine: Equatable, Identifiable {
    enum Group: Equatable {
        case speech
        case operatorRail
        case guardStrip
    }
    let group: Group
    let text: String
    var id: String { "\(group)-\(text)" }
}

struct CueTimeBudget: Codable, Equatable {
    var start: String?
    var end: String?
    var seconds: Int?
}

struct CueGlanceabilityPolicy: Codable, Equatable {
    var maxCharsPerLine: Int?
    var maxLinesPerCard: Int?

    enum CodingKeys: String, CodingKey {
        case maxCharsPerLine = "max_chars_per_line"
        case maxLinesPerCard = "max_lines_per_card"
    }
}

/// The decoded overlay deck (from `overlay_deck.json`).
struct OverlayDeck: Codable, Equatable {
    var recipientID: String
    var recipientName: String?
    var schema: String?
    var cards: [CueCard]
    var glanceabilityPolicy: CueGlanceabilityPolicy?
    /// sha over the source deck minus volatile fields, as stamped by the backend.
    var sourceOverlayDeckHash: String?

    enum CodingKeys: String, CodingKey {
        case recipientID = "recipient_id"
        case recipientName = "recipient_name"
        case schema
        case cards
        case glanceabilityPolicy = "glanceability_policy"
        case sourceOverlayDeckHash = "source_overlay_deck_hash"
    }

    init(
        recipientID: String,
        recipientName: String?,
        schema: String?,
        cards: [CueCard],
        glanceabilityPolicy: CueGlanceabilityPolicy? = nil,
        sourceOverlayDeckHash: String? = nil
    ) {
        self.recipientID = recipientID
        self.recipientName = recipientName
        self.schema = schema
        self.cards = cards
        self.glanceabilityPolicy = glanceabilityPolicy
        self.sourceOverlayDeckHash = sourceOverlayDeckHash
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        recipientID = (try? c.decode(String.self, forKey: .recipientID)) ?? "unknown"
        recipientName = try? c.decodeIfPresent(String.self, forKey: .recipientName)
        schema = try? c.decodeIfPresent(String.self, forKey: .schema)
        cards = (try? c.decode([CueCard].self, forKey: .cards)) ?? []
        glanceabilityPolicy = try? c.decodeIfPresent(CueGlanceabilityPolicy.self, forKey: .glanceabilityPolicy)
        sourceOverlayDeckHash = try? c.decodeIfPresent(String.self, forKey: .sourceOverlayDeckHash)
    }
}

/// Recipient-specific framing pulled from `package.json`. These are the
/// `recipient_inserts` equivalents (opening / bridge / closing material) plus the
/// claim guards the operator must not exceed.
struct RecipientInserts: Equatable {
    var thesis: String?
    var workBridge: String?
    var claimCeiling: String?
    var honestLimitation: String?
    var boundedQuestion: String?
    var currentIdentity: String?
    var currentWork: String?
}

/// One renderable block of the recipient's FULL spoken script (the run-sheet mic
/// surface), parsed from markdown. This is the full teleprompter text the operator
/// reads and scrolls, not the truncated glanceable cue lines.
struct ScriptBlock: Equatable, Identifiable {
    /// Role of the block, so the teleprompter can colour-code spoken word vs
    /// direction-to-the-operator at a glance:
    ///   heading    — beat / section scaffold (blue)
    ///   say        — an exact `SAY:` line, the wording that carries weight (green pill)
    ///   spoken     — a riff / quoted line you say in your own words (white, green bar)
    ///   direction  — a note to YOU: what to do / show, not to read aloud (amber)
    ///   note       — meta framing ("riff, do not read") (dim)
    ///   mono       — a code / command block
    enum Kind: Equatable { case heading, say, spoken, direction, note, mono }
    let kind: Kind
    let text: String
    let index: Int
    /// Tiny visual target marker rendered inside the first speakable block of a
    /// segment. It is metadata on spoken text, never a block above it.
    var viewCue: String? = nil
    var id: Int { index }
}

/// The per-segment visual surface to put on camera. It can be a Station frontend
/// route, a website page, a repo artifact, or any other non-CLI view the operator
/// can open visually while speaking.
struct SegmentScreenCue: Equatable {
    var view: String? = nil
    var onScreen: String? = nil

    var isEmpty: Bool {
        clean(view) == nil && clean(onScreen) == nil
    }

    var teleprompterText: String? {
        if let view = clean(view) {
            return Self.shortViewLabel(view)
        }
        return clean(onScreen)
    }

    private func clean(_ value: String?) -> String? {
        guard let value else { return nil }
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }

    private static func shortViewLabel(_ value: String) -> String {
        let parts = value.split(separator: " ", maxSplits: 1).map(String.init)
        guard let first = parts.first else { return value }
        if first == "/station" {
            return parts.count > 1 ? "Station \(parts[1])" : "Station Surface Atlas"
        }
        if first.hasPrefix("/station/") {
            return parts.count > 1 ? parts[1] : String(first.dropFirst("/station/".count))
        }
        return value
    }
}

/// One compressed beat from the run sheet's `Overlay cue cards` layer — the
/// glanceable phrase-bullet spine, not prose. Each beat carries the semantic
/// points to LAND, the thing to SHOW, the ceiling (LIMIT), and the connector to
/// the next beat (NEXT). This is what the teleprompter shows by default; the prose
/// blocks are the fallback when a run sheet has no cue-card layer.
struct BeatCue: Equatable, Identifiable {
    let num: String        // "0", "1", "6.5"
    let name: String       // "RECOGNITION"
    var land: [String]     // the semantic points to land (compressed)
    var show: [String]     // what is on screen (stage direction)
    var limit: String?     // the ceiling / what not to imply
    var next: String?      // connector to the next beat
    /// Verbatim lines (the run sheet's `SAY:` exacts) that belong to this beat —
    /// shown in full, because the wording carries weight.
    var verbatim: [String]
    /// The one public doctrine object this beat's screen is an instance of, from the
    /// run sheet's `DOCTRINE` cue line / `## Doctrine flash per movement` block.
    var doctrine: DoctrineFlash? = nil
    /// The concrete visual view to open for this beat, from `## On-screen views`.
    /// This is deliberately view-agnostic: frontend route, website, repo artifact,
    /// or another non-CLI surface.
    var view: String? = nil
    /// One sentence of what is on the cockpit view for this beat and how it connects
    /// to another theme, from the `## On-screen views` section.
    var onScreen: String? = nil
    var id: String { num + "-" + name }
}

/// One public-doctrine flash: the single law / principle / anti-principle a beat
/// (or the whole clip) is a local instance of, viewer-openable on the public
/// doctrine page. Surfaced on the overlay so each clip visibly obeys one small
/// constitution instead of reading as a pile of demos.
struct DoctrineFlash: Equatable {
    var id: String            // "AX-3", "P-16", "AP-2"
    var title: String         // "Authority by derivation, not possession"
    var flashText: String     // 3-8 word on-screen flash
    var doNotImply: String?   // the overclaim this flash must not smuggle in
    var publicURL: String?
}

/// The first-principles freestyle spine: the compact mental model the operator
/// holds to explain a theme from understanding, not by reading. Parsed from the
/// run sheet's `## First-principles freestyle spine` section.
struct FirstPrinciplesSpine: Equatable {
    var primitiveProblem: String?
    var irreducibleObjects: String?
    var mechanism: String?
    var workedExample: String?
    var claimCeiling: String?
    var recoveryLine: String?
}

/// The fully-loaded cue bundle a recipient selection produces.
struct RecipientCueBundle: Equatable {
    var recipientID: String
    var recipientName: String
    var deck: OverlayDeck
    var inserts: RecipientInserts
    /// The deck source hash the runtime binds to, so it can detect deck drift.
    var deckSourceHash: String
    /// The full spoken script (run-sheet mic surface) as renderable blocks. Used as
    /// the fallback teleprompter when there is no compressed cue layer.
    var scriptBlocks: [ScriptBlock]
    /// The compressed cue-card beats (preferred teleprompter surface).
    var compressedScript: [BeatCue]
    /// The first-principles spine (general/theme deliverables only); nil for person
    /// recipients. Drives the glanceable theme card.
    var spine: FirstPrinciplesSpine? = nil
    /// The one law the whole clip demonstrates (from `## Doctrine through-line`).
    var doctrineThroughLine: DoctrineFlash? = nil
    /// One doctrine flash per movement (from `## Doctrine flash per movement`).
    var doctrineFlashes: [DoctrineFlash] = []
    /// The dominant on-camera frontend view for this theme (e.g.
    /// "/station/agent-observability Agent Trace"), from `## On-screen views`.
    /// Shown on the glance card so the operator knows which cockpit view to open.
    var onCameraView: String? = nil

    var cards: [CueCard] { deck.cards }

    /// The verbatim `SAY:` lines across the whole script, in order — the exact
    /// wording, regardless of which beat owns them.
    var verbatimLines: [String] {
        scriptBlocks.filter { $0.kind == .say }.map(\.text)
    }
}

// MARK: - Loader

enum RecipientCueDeckLoaderError: Error, CustomStringConvertible {
    case packageDirectoryMissing(String)
    case deckMissing(String)
    case deckUnreadable(String)
    case dynamicAuthorityCardMissing(String)

    var description: String {
        switch self {
        case .packageDirectoryMissing(let path): "Package directory not found: \(path)"
        case .deckMissing(let path): "overlay_deck.json not found: \(path)"
        case .deckUnreadable(let detail): "overlay_deck.json could not be decoded: \(detail)"
        case .dynamicAuthorityCardMissing(let path): "dynamic authority card not found: \(path)"
        }
    }
}

/// Loads recipient cue bundles from disk. There is no HTTP client in this app;
/// the overlay reads the tranche package files directly.
enum RecipientCueDeckLoader {
    /// The frozen first recording-ready tranche.
    static let defaultTrancheID = "first_recording_ready_tranche_v0"

    static func trancheRoot(repoRoot: URL, trancheID: String = defaultTrancheID) -> URL {
        repoRoot
            .appendingPathComponent("docs", isDirectory: true)
            .appendingPathComponent("dissemination", isDirectory: true)
            .appendingPathComponent("outreach", isDirectory: true)
            .appendingPathComponent("recording_tranches", isDirectory: true)
            .appendingPathComponent(trancheID, isDirectory: true)
    }

    static func packageDirectory(
        repoRoot: URL,
        recipientID: String,
        trancheID: String = defaultTrancheID
    ) -> URL {
        trancheRoot(repoRoot: repoRoot, trancheID: trancheID)
            .appendingPathComponent("packages", isDirectory: true)
            .appendingPathComponent(recipientID, isDirectory: true)
    }

    /// Load a recipient's cue bundle (deck + package framing). Lenient: a missing
    /// `package.json` still yields a usable bundle with empty inserts.
    static func load(
        repoRoot: URL,
        recipientID: String,
        trancheID: String = defaultTrancheID
    ) throws -> RecipientCueBundle {
        let dir = packageDirectory(repoRoot: repoRoot, recipientID: recipientID, trancheID: trancheID)
        do {
            return try loadPackagedBundle(packageDir: dir, repoRoot: repoRoot, recipientID: recipientID)
        } catch {
            if let dynamic = try? loadDynamicAuthorityBundle(repoRoot: repoRoot, recipientID: recipientID) {
                return dynamic
            }
            // Final fallback: a general deliverable with no package and no authority
            // card, just a run-sheet markdown on disk. This is what makes any
            // walkthrough_run_sheet_<id>.md immediately recordable.
            if let general = try? loadGeneralRunSheetBundle(repoRoot: repoRoot, runSheetID: recipientID) {
                return general
            }
            throw error
        }
    }

    /// Build a cue bundle from a pure run-sheet markdown (no package, no authority
    /// card). The deck cards are synthesized from the `Overlay cue cards` beats; the
    /// teleprompter still parses the mic-surface section and the compressed beats.
    static func loadGeneralRunSheetBundle(
        repoRoot: URL,
        runSheetID: String
    ) throws -> RecipientCueBundle {
        let rel = RecipientQueueLoader.generalRunSheetRelPath(runSheetID)
        let url = repoRoot.appendingPathComponent(rel)
        guard let md = try? String(contentsOf: url, encoding: .utf8), !md.isEmpty else {
            throw RecipientCueDeckLoaderError.deckMissing(url.path)
        }
        // Enforce the opt-in contract HERE, not only in the picker: an undeclared
        // person/outreach run sheet that exists on disk must not load as a general
        // deliverable even when selected directly or via a stale persisted id.
        let declaration = RecipientQueueLoader.generalDeliverableDeclaration(inFrontMatterOf: md)
        guard declaration.declared else {
            throw RecipientCueDeckLoaderError.deckUnreadable(
                "\(rel) is not a declared general deliverable "
                    + "(front matter `recording_deliverable: general` required)"
            )
        }
        let hash = sha256Hex(Data(md.utf8))
        let name = declaration.title ?? RecipientQueueLoader.generalDisplayName(runSheetID)
        // The study/coherence layers the operator built: the first-principles spine
        // and the public-doctrine flashes. These used to be dropped on the floor;
        // they are what makes the overlay show substance, not a bare cue card.
        let spine = parseSpine(md)
        let throughLine = parseDoctrineThroughLine(md)
        let flashes = parseDoctrineFlashes(md)
        let compressed = bindOnScreenToBeats(bindDoctrineToBeats(parseCueCards(md), flashes: flashes), md: md)
        let cards = generalDeliverableCards(from: compressed, runSheetID: runSheetID, displayName: name)
        let deck = OverlayDeck(
            recipientID: runSheetID,
            recipientName: name,
            schema: "general_run_sheet_overlay_deck_v0",
            cards: cards,
            sourceOverlayDeckHash: hash
        )
        let scriptBlocks = loadScriptBlocks(
            packageDir: url.deletingLastPathComponent(),
            repoRoot: repoRoot,
            deck: deck,
            markdown: md
        )
        return RecipientCueBundle(
            recipientID: runSheetID,
            recipientName: name,
            deck: deck,
            inserts: RecipientInserts(),
            deckSourceHash: hash,
            scriptBlocks: scriptBlocks,
            compressedScript: compressed,
            spine: spine,
            doctrineThroughLine: throughLine,
            doctrineFlashes: flashes,
            onCameraView: parseOnCameraView(md)
        )
    }

    /// The ordered per-beat visual cues from the `## On-screen views` section:
    /// `View:` is the surface to put on camera; `On screen:` is the local reading
    /// of what that surface demonstrates. These can name website/frontend/artifact
    /// views; they are not commands for the operator to run.
    static func parseScreenCues(_ md: String) -> [SegmentScreenCue] {
        let sec = sectionBody(md, heading: "on-screen views")
        guard !sec.isEmpty else { return [] }

        var cues: [SegmentScreenCue] = []
        var current = SegmentScreenCue()

        func flush() {
            guard !current.isEmpty else { return }
            cues.append(current)
            current = SegmentScreenCue()
        }

        for raw in sec.components(separatedBy: "\n") {
            let trimmed = raw.trimmingCharacters(in: .whitespaces)
            if trimmed.hasPrefix("###") {
                flush()
                continue
            }
            let line = trimBulletMarker(raw)
            if let view = screenCueField(line, label: "View") {
                if current.view != nil || current.onScreen != nil { flush() }
                current.view = view
            } else if let onScreen = screenCueField(line, label: "On screen") {
                if current.onScreen != nil { flush() }
                current.onScreen = onScreen
            }
        }
        flush()
        return cues
    }

    /// Compatibility helper for older tests/callers that only need the sentence.
    static func parseOnScreenLines(_ md: String) -> [String] {
        parseScreenCues(md).compactMap(\.onScreen)
    }

    /// Attach each beat's screen cue by order (beats and On-screen rows are both
    /// authored in beat order).
    static func bindOnScreenToBeats(_ beats: [BeatCue], md: String) -> [BeatCue] {
        let cues = parseScreenCues(md)
        guard !cues.isEmpty else { return beats }
        var out = beats
        for i in out.indices where i < cues.count {
            out[i].view = cues[i].view
            out[i].onScreen = cues[i].onScreen
        }
        return out
    }

    /// The dominant visual view to open on camera for this theme: prefer the most
    /// common `/station/` frontend route, otherwise fall back to the most common
    /// visual target. Shown on the glance card.
    static func parseOnCameraView(_ md: String) -> String? {
        let views = parseScreenCues(md).compactMap { cue in
            cue.view?.trimmingCharacters(in: .whitespacesAndNewlines)
        }.filter { !$0.isEmpty }
        guard !views.isEmpty else { return nil }

        let preferred = views.filter { $0.contains("/station/") }
        let candidates = preferred.isEmpty ? views : preferred
        var counts: [String: Int] = [:]
        var order: [String] = []
        for value in candidates {
            if counts[value] == nil { order.append(value) }
            counts[value, default: 0] += 1
        }
        guard !order.isEmpty else { return nil }
        // Most frequent view wins; ties break to the first that appeared.
        return order.max { a, b in
            let ca = counts[a] ?? 0, cb = counts[b] ?? 0
            if ca != cb { return ca < cb }
            return (order.firstIndex(of: a) ?? 0) > (order.firstIndex(of: b) ?? 0)
        }
    }

    private static func trimBulletMarker(_ raw: String) -> String {
        var line = raw.trimmingCharacters(in: .whitespaces)
        while let f = line.first, f == "-" || f == "*" || f == ">" || f == " " {
            line.removeFirst()
        }
        return line.trimmingCharacters(in: .whitespaces)
    }

    private static func screenCueField(_ line: String, label: String) -> String? {
        let key = label.lowercased() + ":"
        let stripped = line.lowercased().replacingOccurrences(of: "*", with: "")
        guard stripped.hasPrefix(key), let colon = line.range(of: ":") else { return nil }
        let value = String(line[colon.upperBound...])
            .trimmingCharacters(in: CharacterSet(charactersIn: " *"))
        return value.isEmpty ? nil : value
    }

    /// Synthesize glanceable deck cards from the run sheet's overlay cue-card beats.
    /// Falls back to a single pointer card when the sheet has no cue-card block.
    private static func generalDeliverableCards(
        from beats: [BeatCue],
        runSheetID: String,
        displayName: String
    ) -> [CueCard] {
        guard !beats.isEmpty else {
            return [CueCard(
                sceneID: runSheetID,
                lines: ["\(displayName): open walkthrough_run_sheet_\(runSheetID).md for the full mic surface."]
            )]
        }
        return beats.map { beat in
            var lines: [String] = beat.land
            for s in beat.show { lines.append("Do: \(s)") }
            if let limit = beat.limit, !limit.isEmpty { lines.append("Guard: \(limit)") }
            let scene = beat.name.isEmpty ? "beat_\(beat.num)" : beat.name
            return CueCard(sceneID: scene, lines: lines.isEmpty ? [scene] : lines)
        }
    }

    private static func loadPackagedBundle(
        packageDir dir: URL,
        repoRoot: URL,
        recipientID: String
    ) throws -> RecipientCueBundle {
        let fm = FileManager.default
        guard fm.fileExists(atPath: dir.path) else {
            throw RecipientCueDeckLoaderError.packageDirectoryMissing(dir.path)
        }

        let deckURL = dir.appendingPathComponent("overlay_deck.json")
        guard fm.fileExists(atPath: deckURL.path) else {
            throw RecipientCueDeckLoaderError.deckMissing(deckURL.path)
        }
        let deckData: Data
        do {
            deckData = try Data(contentsOf: deckURL)
        } catch {
            throw RecipientCueDeckLoaderError.deckUnreadable(error.localizedDescription)
        }
        let deck: OverlayDeck
        do {
            deck = try JSONDecoder().decode(OverlayDeck.self, from: deckData)
        } catch {
            throw RecipientCueDeckLoaderError.deckUnreadable(error.localizedDescription)
        }

        // Bind to the recorded hash if present, else recompute a stable hash over
        // the raw deck bytes so drift is still detectable session-to-session.
        let deckSourceHash = deck.sourceOverlayDeckHash ?? Self.sha256Hex(deckData)

        let inserts = Self.loadInserts(packageDir: dir)
        let recipientName = deck.recipientName
            ?? inserts.currentIdentity.flatMap { _ in nil }
            ?? recipientID
        let md = Self.runSheetMarkdown(packageDir: dir, repoRoot: repoRoot)
        let scriptBlocks = Self.loadScriptBlocks(packageDir: dir, repoRoot: repoRoot, deck: deck, markdown: md)
        let compressed = md.map { Self.bindOnScreenToBeats(Self.parseCueCards($0), md: $0) } ?? []

        return RecipientCueBundle(
            recipientID: recipientID,
            recipientName: recipientName,
            deck: deck,
            inserts: inserts,
            deckSourceHash: deckSourceHash,
            scriptBlocks: scriptBlocks,
            compressedScript: compressed,
            onCameraView: md.flatMap(Self.parseOnCameraView)
        )
    }

    /// Full-queue recipients can be recordable before they have a frozen tranche
    /// package. In that case, synthesize the runtime cue bundle from the generated
    /// authority card plus the proof-room run sheet named by the backend.
    private static func loadDynamicAuthorityBundle(
        repoRoot: URL,
        recipientID: String
    ) throws -> RecipientCueBundle {
        let authorityURL = repoRoot
            .appendingPathComponent("docs", isDirectory: true)
            .appendingPathComponent("dissemination", isDirectory: true)
            .appendingPathComponent("outreach", isDirectory: true)
            .appendingPathComponent("recipient_authority_cards", isDirectory: true)
            .appendingPathComponent("\(recipientID).json")
        guard let authorityData = try? Data(contentsOf: authorityURL),
              let root = (try? JSONSerialization.jsonObject(with: authorityData)) as? [String: Any]
        else {
            throw RecipientCueDeckLoaderError.dynamicAuthorityCardMissing(authorityURL.path)
        }

        let recipientName = dynamicRecipientName(
            repoRoot: repoRoot,
            recipientID: recipientID,
            authorityRoot: root
        )
        let cards = dynamicCueCards(authorityRoot: root)
        let sourceHash = (root["authority_deck_hash"] as? String) ?? sha256Hex(authorityData)
        let deck = OverlayDeck(
            recipientID: recipientID,
            recipientName: recipientName,
            schema: "dynamic_authority_card_overlay_deck_v0",
            cards: cards.isEmpty ? fallbackDynamicCards(root: root, recipientName: recipientName) : cards,
            sourceOverlayDeckHash: sourceHash
        )
        let markdown = dynamicRunSheetMarkdown(
            repoRoot: repoRoot,
            recipientID: recipientID,
            authorityRoot: root
        )
        let scriptBlocks = loadScriptBlocks(
            packageDir: authorityURL.deletingLastPathComponent(),
            repoRoot: repoRoot,
            deck: deck,
            markdown: markdown
        )
        let compressed = markdown.map { bindOnScreenToBeats(parseCueCards($0), md: $0) } ?? []
        return RecipientCueBundle(
            recipientID: recipientID,
            recipientName: recipientName,
            deck: deck,
            inserts: dynamicInserts(root: root),
            deckSourceHash: sourceHash,
            scriptBlocks: scriptBlocks,
            compressedScript: compressed,
            onCameraView: markdown.flatMap(parseOnCameraView)
        )
    }

    private static func dynamicCueCards(authorityRoot root: [String: Any]) -> [CueCard] {
        guard let rawCards = root["cards"] as? [[String: Any]] else { return [] }
        return rawCards
            .sorted { a, b in
                ((a["order"] as? Int) ?? Int.max) < ((b["order"] as? Int) ?? Int.max)
            }
            .enumerated()
            .map { index, raw in
                let sceneID = (raw["card_id"] as? String) ?? "dynamic_card_\(index + 1)"
                var lines: [String] = []
                appendString(raw["POINT"], to: &lines)
                if let see = raw["See"] as? String, !see.isEmpty {
                    lines.append("Do: \(see)")
                }
                if let backend = raw["Backend"] as? String, !backend.isEmpty {
                    lines.append("Backend: \(backend)")
                }
                if let letsYou = raw["Lets you"] as? String, !letsYou.isEmpty {
                    lines.append("Lets you: \(letsYou)")
                }
                if let ceiling = claimCeiling(from: raw), !ceiling.isEmpty {
                    lines.append("Guard: \(ceiling)")
                }
                if lines.isEmpty {
                    lines.append(sceneID.replacingOccurrences(of: "_", with: " "))
                }
                return CueCard(sceneID: sceneID, lines: lines)
            }
    }

    private static func fallbackDynamicCards(
        root: [String: Any],
        recipientName: String
    ) -> [CueCard] {
        var lines: [String] = []
        if let boundary = root["boundary"] as? String, !boundary.isEmpty {
            lines.append("Guard: \(boundary)")
        }
        if lines.isEmpty {
            lines.append("Prepare private recording for \(recipientName).")
        }
        return [CueCard(sceneID: "dynamic_authority_fallback", lines: lines)]
    }

    private static func dynamicInserts(root: [String: Any]) -> RecipientInserts {
        let firstCard = (root["cards"] as? [[String: Any]])?.first
        let branch = proofBranch(from: firstCard)
        return RecipientInserts(
            thesis: root["boundary"] as? String,
            workBridge: nil,
            claimCeiling: branch?["claim_ceiling"] as? String,
            honestLimitation: nil,
            boundedQuestion: branch?["one_ask"] as? String,
            currentIdentity: nil,
            currentWork: nil
        )
    }

    private static func dynamicRecipientName(
        repoRoot: URL,
        recipientID: String,
        authorityRoot root: [String: Any]
    ) -> String {
        if let name = root["recipient_name"] as? String, !name.isEmpty { return name }
        if let name = root["name"] as? String, !name.isEmpty { return name }
        if let name = queueRecipientName(repoRoot: repoRoot, recipientID: recipientID) { return name }
        if let manifest = manifestRoot(repoRoot: repoRoot, authorityRoot: root),
           let name = manifest["recipient_name"] as? String,
           !name.isEmpty {
            return name
        }
        if let dossier = dossierRoot(repoRoot: repoRoot, authorityRoot: root),
           let name = dossier["name"] as? String,
           !name.isEmpty {
            return name
        }
        return recipientID
            .split(separator: "_")
            .map { $0.prefix(1).uppercased() + $0.dropFirst() }
            .joined(separator: " ")
    }

    private static func dynamicRunSheetMarkdown(
        repoRoot: URL,
        recipientID: String,
        authorityRoot root: [String: Any]
    ) -> String? {
        let refs = dynamicRunSheetRefs(
            repoRoot: repoRoot,
            recipientID: recipientID,
            authorityRoot: root
        )
        for ref in refs {
            let url = repoRoot.appendingPathComponent(ref)
            if let md = try? String(contentsOf: url, encoding: .utf8), !md.isEmpty {
                return md
            }
        }
        return nil
    }

    private static func dynamicRunSheetRefs(
        repoRoot: URL,
        recipientID: String,
        authorityRoot root: [String: Any]
    ) -> [String] {
        var refs: [String] = []
        if let cards = root["cards"] as? [[String: Any]] {
            for card in cards {
                if let sourceRefs = sourceRefs(from: card),
                   let paths = sourceRefs["run_sheet_paths"] as? [String] {
                    refs.append(contentsOf: paths)
                }
            }
        }
        if let video = videoReadinessRoot(repoRoot: repoRoot, authorityRoot: root),
           let primary = video["primary_take"] as? [String: Any],
           let runSheet = primary["run_sheet"] as? String {
            refs.append(runSheet)
        }
        refs.append("<private-obsidian-root>/recording_sidecar/walkthrough_run_sheet_\(recipientID).md")
        var seen: Set<String> = []
        return refs.filter { ref in
            guard !ref.isEmpty, !seen.contains(ref) else { return false }
            seen.insert(ref)
            return true
        }
    }

    private static func queueRecipientName(repoRoot: URL, recipientID: String) -> String? {
        let queueURL = repoRoot
            .appendingPathComponent("docs", isDirectory: true)
            .appendingPathComponent("dissemination", isDirectory: true)
            .appendingPathComponent("outreach", isDirectory: true)
            .appendingPathComponent("recipient_recording_overlay_queue_v0.json")
        guard let data = try? Data(contentsOf: queueURL),
              let root = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
              let rows = root["rows"] as? [[String: Any]]
        else { return nil }
        return rows.first { $0["recipient_id"] as? String == recipientID }?["recipient_name"] as? String
    }

    private static func manifestRoot(
        repoRoot: URL,
        authorityRoot root: [String: Any]
    ) -> [String: Any]? {
        guard let ref = firstSourceRef(root: root, key: "manifest_path") else { return nil }
        return jsonObject(repoRoot: repoRoot, ref: ref)
    }

    private static func dossierRoot(
        repoRoot: URL,
        authorityRoot root: [String: Any]
    ) -> [String: Any]? {
        guard let ref = firstSourceRef(root: root, key: "dossier_path") else { return nil }
        return jsonObject(repoRoot: repoRoot, ref: ref)
    }

    private static func videoReadinessRoot(
        repoRoot: URL,
        authorityRoot root: [String: Any]
    ) -> [String: Any]? {
        if let ref = firstSourceRef(root: root, key: "video_readiness_receipt_path"),
           let json = jsonObject(repoRoot: repoRoot, ref: ref) {
            return json
        }
        guard let manifestRef = firstSourceRef(root: root, key: "manifest_path") else { return nil }
        let manifestURL = repoRoot.appendingPathComponent(manifestRef)
        let videoURL = manifestURL
            .deletingLastPathComponent()
            .appendingPathComponent("VIDEO_READINESS_RECEIPT.json")
        guard let data = try? Data(contentsOf: videoURL),
              let json = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
        else { return nil }
        return json
    }

    private static func firstSourceRef(root: [String: Any], key: String) -> String? {
        guard let cards = root["cards"] as? [[String: Any]] else { return nil }
        for card in cards {
            if let sourceRefs = sourceRefs(from: card),
               let ref = sourceRefs[key] as? String,
               !ref.isEmpty {
                return ref
            }
        }
        return nil
    }

    private static func sourceRefs(from card: [String: Any]) -> [String: Any]? {
        guard let proofCell = card["proof_cell"] as? [String: Any] else { return nil }
        return proofCell["source_refs"] as? [String: Any]
    }

    private static func proofBranch(from card: [String: Any]?) -> [String: Any]? {
        guard let proofCell = card?["proof_cell"] as? [String: Any] else { return nil }
        return proofCell["proof_branch"] as? [String: Any]
    }

    private static func claimCeiling(from card: [String: Any]) -> String? {
        proofBranch(from: card)?["claim_ceiling"] as? String
    }

    private static func jsonObject(repoRoot: URL, ref: String) -> [String: Any]? {
        let url = repoRoot.appendingPathComponent(ref)
        guard let data = try? Data(contentsOf: url),
              let json = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
        else { return nil }
        return json
    }

    private static func appendString(_ value: Any?, to lines: inout [String]) {
        guard let text = value as? String, !text.isEmpty else { return }
        lines.append(text)
    }

    /// Read the recipient-specific framing from `package.json`. Best-effort; any
    /// missing field is simply nil.
    private static func loadInserts(packageDir: URL) -> RecipientInserts {
        let packageURL = packageDir.appendingPathComponent("package.json")
        guard let data = try? Data(contentsOf: packageURL),
              let root = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
        else {
            return RecipientInserts()
        }

        let claimGuards = root["claim_guards"] as? [String: Any]
        let identityWork = root["identity_work"] as? [String: Any]

        return RecipientInserts(
            thesis: root["recipient_specific_thesis"] as? String,
            workBridge: root["recipient_work_bridge"] as? String,
            claimCeiling: claimGuards?["claim_ceiling"] as? String,
            honestLimitation: claimGuards?["honest_limitation"] as? String,
            boundedQuestion: claimGuards?["bounded_question"] as? String,
            currentIdentity: identityWork?["current_identity"] as? String,
            currentWork: identityWork?["current_work"] as? String
        )
    }

    static func sha256Hex(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }

    // MARK: - Full spoken script (run-sheet mic surface) as renderable blocks

    /// Load the recipient's FULL spoken script for the teleprompter. Prefers the
    /// obsidian run-sheet mic surface (the fuller arc the operator actually reads),
    /// falls back to the in-package spoken_run_sheet.md, then to the deck cards so
    /// the panel always shows something rather than a frozen empty.
    static func loadScriptBlocks(packageDir: URL, repoRoot: URL, deck: OverlayDeck, markdown: String?) -> [ScriptBlock] {
        if let md = markdown {
            let section = micSurfaceSection(md)
            let blocks = parseScript(section.isEmpty ? md : section)
            let enriched = bindScreenCuesToScriptBlocks(blocks, md: md)
            if !enriched.isEmpty { return enriched }
        }
        let spoken = packageDir.appendingPathComponent("spoken_run_sheet.md")
        if let data = try? Data(contentsOf: spoken), let md = String(data: data, encoding: .utf8) {
            let section = micSurfaceSection(md)
            let blocks = parseScript(section.isEmpty ? md : section)
            let enriched = bindScreenCuesToScriptBlocks(blocks, md: md)
            if !enriched.isEmpty { return enriched }
        }
        // Fallback: the (possibly terse) deck cards, full lines, untruncated as present.
        var blocks: [ScriptBlock] = []
        var i = 0
        for card in deck.cards {
            blocks.append(ScriptBlock(kind: .heading,
                                      text: card.sceneID.replacingOccurrences(of: "_", with: " ").uppercased(),
                                      index: i)); i += 1
            for line in card.lines {
                blocks.append(ScriptBlock(kind: .direction, text: line, index: i)); i += 1
            }
        }
        return blocks
    }

    /// Attach the visual cue to the first speakable block in each headed segment.
    /// The cue is metadata on spoken text, never a separate block above it.
    static func bindScreenCuesToScriptBlocks(_ blocks: [ScriptBlock], md: String) -> [ScriptBlock] {
        let cueTexts = parseScreenCues(md).compactMap(\.teleprompterText)
        guard !blocks.isEmpty, !cueTexts.isEmpty else { return blocks }

        var cueIndex = 0
        var shouldConsumeCueForNextContent = true
        var pendingViewCue: String?
        var lastViewCue: String?
        var out: [ScriptBlock] = []

        for block in blocks {
            if block.kind == .heading {
                out.append(block)
                shouldConsumeCueForNextContent = true
                pendingViewCue = nil
                continue
            }

            if shouldConsumeCueForNextContent {
                if cueIndex < cueTexts.count {
                    let cue = cueTexts[cueIndex]
                    if cue != lastViewCue {
                        pendingViewCue = cue
                        lastViewCue = cue
                    }
                    cueIndex += 1
                }
                shouldConsumeCueForNextContent = false
            }

            var next = block
            if isSpeakableKind(block.kind), let cue = pendingViewCue {
                next.viewCue = cue
                pendingViewCue = nil
            }
            out.append(next)
        }
        return out
    }

    private static func isSpeakableKind(_ kind: ScriptBlock.Kind) -> Bool {
        kind == .say || kind == .spoken
    }

    /// Resolve and read the obsidian run-sheet markdown via the path recorded in the
    /// package's authority_card.json source_refs.
    private static func runSheetMarkdown(packageDir: URL, repoRoot: URL) -> String? {
        let authority = packageDir.appendingPathComponent("authority_card.json")
        guard let data = try? Data(contentsOf: authority),
              let root = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
        else { return nil }
        var rel: String?
        if let cards = root["cards"] as? [[String: Any]] {
            for c in cards {
                if let pc = c["proof_cell"] as? [String: Any],
                   let sr = pc["source_refs"] as? [String: Any],
                   let paths = sr["run_sheet_paths"] as? [String],
                   let first = paths.first {
                    rel = first
                    break
                }
            }
        }
        guard let relPath = rel else { return nil }
        let url = repoRoot.appendingPathComponent(relPath)
        return try? String(contentsOf: url, encoding: .utf8)
    }

    /// Slice the "THE MIC SURFACE" section out of a run sheet (the speakable beats),
    /// stopping at the prep / reference sections.
    private static func micSurfaceSection(_ md: String) -> String {
        let lines = md.components(separatedBy: "\n")
        var start: Int?
        for (i, l) in lines.enumerated() where l.hasPrefix("#") {
            if l.lowercased().contains("mic surface") { start = i; break }
        }
        guard let s = start else { return "" }
        var end = lines.count
        let stops = ["record-time preflight", "self-serve", "claim ledger",
                     "research frontier", "## sources", "acceptance loop"]
        if (s + 1) < lines.count {
            for i in (s + 1)..<lines.count {
                let lower = lines[i].lowercased()
                if lines[i].hasPrefix("## "), stops.contains(where: { lower.contains($0) }) {
                    end = i
                    break
                }
            }
        }
        return lines[s..<end].joined(separator: "\n")
    }

    /// Parse markdown into role-tagged teleprompter blocks. Two passes: first
    /// re-assemble soft-wrapped source lines into logical units (a run sheet wraps a
    /// single spoken sentence across several lines, and bullets continue on indented
    /// lines), then classify each unit as spoken word vs direction-to-the-operator so
    /// the view can colour-code it. Markdown emphasis markers are kept on the text so
    /// the view can render inline highlights; only detection strips them.
    private static func parseScript(_ md: String) -> [ScriptBlock] {
        enum UnitKind { case heading, bullet, code, para }
        struct Unit { var kind: UnitKind; var text: String }

        let rawLines = md.components(separatedBy: "\n")
        var units: [Unit] = []
        var paraBuf: [String] = []
        var inFence = false

        func flushPara() {
            let joined = paraBuf.joined(separator: " ").trimmingCharacters(in: .whitespaces)
            paraBuf.removeAll(keepingCapacity: true)
            if !joined.isEmpty { units.append(Unit(kind: .para, text: joined)) }
        }

        var i = 0
        while i < rawLines.count {
            let raw = rawLines[i]
            let line = raw.trimmingCharacters(in: .whitespaces)

            if line.hasPrefix("```") { flushPara(); inFence.toggle(); i += 1; continue }
            if inFence { units.append(Unit(kind: .code, text: raw)); i += 1; continue }
            if line.isEmpty { flushPara(); i += 1; continue }

            if line.hasPrefix("#") {
                flushPara()
                units.append(Unit(kind: .heading, text: line))
                i += 1
            } else if line.hasPrefix("- ") || line.hasPrefix("* ") {
                flushPara()
                var text = String(line.dropFirst(2))
                // Absorb indented continuation lines (soft-wrapped bullet body).
                var j = i + 1
                while j < rawLines.count {
                    let cont = rawLines[j]
                    let contTrim = cont.trimmingCharacters(in: .whitespaces)
                    let indented = cont.first == " " || cont.first == "\t"
                    if indented, !contTrim.isEmpty,
                       !contTrim.hasPrefix("- "), !contTrim.hasPrefix("* ") {
                        text += " " + contTrim
                        j += 1
                    } else { break }
                }
                units.append(Unit(kind: .bullet, text: text))
                i = j
            } else {
                paraBuf.append(line)
                i += 1
            }
        }
        flushPara()

        var blocks: [ScriptBlock] = []
        var idx = 0
        func emit(_ kind: ScriptBlock.Kind, _ text: String) {
            let t = text.trimmingCharacters(in: .whitespaces)
            if t.isEmpty { return }
            blocks.append(ScriptBlock(kind: kind, text: t, index: idx)); idx += 1
        }

        for u in units {
            switch u.kind {
            case .code:
                emit(.mono, u.text)
            case .heading:
                emit(.heading, plainStrip(String(u.text.drop(while: { $0 == "#" }))))
            case .bullet:
                let key = detectKey(u.text)
                if key.hasPrefix("say:") || key.contains("(say:") {
                    emit(.say, spokenPayload(u.text))
                } else if hasLeadLabel(u.text) {
                    emit(.spoken, u.text)
                } else if u.text.trimmingCharacters(in: .whitespaces).first.map(isQuote) == true {
                    emit(.spoken, spokenPayload(u.text))
                } else {
                    emit(.direction, u.text)
                }
            case .para:
                let text = u.text
                if text.hasPrefix("**") {
                    // Bold-labelled paragraph: a "say it like this" riff is spoken,
                    // everything else ("riff, do not read", "the spine…") is framing.
                    if boldLabel(text).lowercased().contains("say it like this") {
                        emit(.spoken, spokenPayload(text))
                    } else {
                        emit(.note, text)
                    }
                } else if detectKey(text).hasPrefix("say:") {
                    emit(.say, spokenPayload(text))
                } else if text.first.map(isQuote) == true {
                    emit(.spoken, spokenPayload(text))
                } else {
                    emit(.direction, text)
                }
            }
        }
        return blocks
    }

    // MARK: - Inline text helpers

    private static func isQuote(_ c: Character) -> Bool {
        c == "\"" || c == "\u{201C}" || c == "\u{201D}"
    }

    /// Lowercased, marker-stripped form used only for classifying a unit.
    private static func detectKey(_ s: String) -> String {
        plainStrip(s).lowercased()
    }

    /// Remove `**` / backtick markers, preserving case, for display fallbacks.
    private static func plainStrip(_ s: String) -> String {
        s.replacingOccurrences(of: "**", with: "")
         .replacingOccurrences(of: "`", with: "")
         .trimmingCharacters(in: .whitespaces)
    }

    /// Lead-label convention for teleprompter bullets: `Intro :: spoken line`.
    /// The view renders the lead smaller and coloured, while preserving the
    /// sentence as normal spoken text.
    private static func hasLeadLabel(_ s: String) -> Bool {
        let stripped = plainStrip(s)
        guard let range = stripped.range(of: "::") else { return false }
        let lead = stripped[..<range.lowerBound].trimmingCharacters(in: .whitespaces)
        let body = stripped[range.upperBound...].trimmingCharacters(in: .whitespaces)
        return !lead.isEmpty && lead.count <= 32 && !body.isEmpty
    }

    /// The bold label at the very start of a paragraph (text between the first pair
    /// of `**`), or "" when there is none.
    private static func boldLabel(_ s: String) -> String {
        guard s.hasPrefix("**") else { return "" }
        let rest = s.dropFirst(2)
        guard let end = rest.range(of: "**") else { return "" }
        return String(rest[..<end.lowerBound])
    }

    /// The substring inside the first … last quote pair, or nil.
    private static func extractQuoted(_ s: String) -> String? {
        guard let f = s.firstIndex(where: isQuote),
              let l = s.lastIndex(where: isQuote), l > f else { return nil }
        let inner = s[s.index(after: f)..<l].trimmingCharacters(in: .whitespaces)
        return inner.isEmpty ? nil : inner
    }

    /// The spoken words from a SAY / riff / quoted unit: prefer the quoted span,
    /// else the text after a `SAY:` label, else the whole stripped line.
    private static func spokenPayload(_ raw: String) -> String {
        let stripped = plainStrip(raw)
        if stripped.lowercased() == "say:" { return "" }
        if let q = extractQuoted(raw) { return q }
        if let r = raw.range(of: "SAY:", options: .caseInsensitive) {
            let after = String(raw[r.upperBound...])
                .trimmingCharacters(in: CharacterSet(charactersIn: " :`*\""))
            if !after.isEmpty { return plainStrip(after) }
        }
        return stripped
    }

    // MARK: - Compressed cue-card layer

    /// Parse the run sheet's `## Overlay cue cards` fenced block into compressed
    /// beats. Grammar (one fenced block, fixed columns):
    ///     0 RECOGNITION  LAND  made for you: …
    ///                    SHOW  webcam, her name, her work first
    ///                    LIMIT relevance not endorsement / NEXT one-sentence frame
    /// A line that starts with a digit opens a new beat (its header sits before the
    /// first role keyword); indented continuation lines add more LAND/SHOW/LIMIT.
    static func parseCueCards(_ md: String) -> [BeatCue] {
        // 1) Lift the fenced block under the "overlay cue cards" heading.
        var inSection = false
        var inFence = false
        var body: [String] = []
        for line in md.components(separatedBy: "\n") {
            if line.hasPrefix("#") {
                inSection = line.lowercased().contains("overlay cue cards")
                continue
            }
            guard inSection else { continue }
            if line.hasPrefix("```") {
                if inFence { break }      // close of the first fence ends the block
                inFence = true
                continue
            }
            if inFence { body.append(line) }
        }
        guard !body.isEmpty else { return [] }

        // 2) Walk the rows, opening a beat on a digit-led line.
        let roles = ["LAND", "SHOW", "LIMIT"]
        func firstRole(_ s: String) -> (role: String, at: String.Index)? {
            var best: (String, String.Index)?
            for r in roles {
                var searchStart = s.startIndex
                while searchStart < s.endIndex {
                    guard let range = s.range(of: r, range: searchStart..<s.endIndex) else { break }
                    let beforeOK = range.lowerBound == s.startIndex
                        || s[s.index(before: range.lowerBound)].isWhitespace
                    let afterOK = range.upperBound == s.endIndex
                        || s[range.upperBound].isWhitespace
                    if beforeOK, afterOK, best == nil || range.lowerBound < best!.1 {
                        best = (r, range.lowerBound)
                    }
                    searchStart = range.upperBound
                }
            }
            return best.map { ($0.0, $0.1) }
        }
        func apply(_ role: String, _ content: String, to beat: inout BeatCue) {
            switch role {
            case "LAND" where !content.isEmpty: beat.land.append(content)
            case "SHOW" where !content.isEmpty: beat.show.append(content)
            case "LIMIT":
                // "ceiling … / NEXT connector"
                if let r = content.range(of: "NEXT") {
                    let limit = String(content[..<r.lowerBound])
                        .trimmingCharacters(in: CharacterSet(charactersIn: " /"))
                    let next = String(content[r.upperBound...]).trimmingCharacters(in: .whitespaces)
                    if !limit.isEmpty { beat.limit = limit }
                    if !next.isEmpty { beat.next = next }
                } else if !content.isEmpty {
                    beat.limit = content
                }
            default: break
            }
        }

        var beats: [BeatCue] = []
        for raw in body {
            let trimmed = raw.trimmingCharacters(in: .whitespaces)
            if trimmed.isEmpty { continue }
            // A `DOCTRINE <id> <flash text>` continuation line binds the beat to its
            // public doctrine object. It carries no LAND/SHOW/LIMIT role, so it would
            // otherwise be silently dropped here.
            if trimmed.uppercased().hasPrefix("DOCTRINE"), !beats.isEmpty {
                let rest = String(trimmed.dropFirst("DOCTRINE".count)).trimmingCharacters(in: .whitespaces)
                let parts = rest.split(separator: " ", maxSplits: 1).map(String.init)
                if let did = parts.first, !did.isEmpty {
                    let text = parts.count > 1 ? parts[1].trimmingCharacters(in: .whitespaces) : ""
                    beats[beats.count - 1].doctrine = DoctrineFlash(
                        id: did, title: "", flashText: text, doNotImply: nil, publicURL: nil
                    )
                }
                continue
            }
            guard let (role, at) = firstRole(trimmed) else { continue }
            let prefix = String(trimmed[..<at]).trimmingCharacters(in: .whitespaces)
            let content = String(trimmed[trimmed.index(at, offsetBy: role.count)...])
                .trimmingCharacters(in: .whitespaces)

            if let head = prefix.first, head.isNumber {
                let parts = prefix.split(separator: " ", maxSplits: 1)
                let num = String(parts[0])
                let name = parts.count > 1 ? String(parts[1]) : ""
                var beat = BeatCue(num: num, name: name, land: [], show: [], limit: nil, next: nil, verbatim: [])
                apply(role, content, to: &beat)
                beats.append(beat)
            } else if !beats.isEmpty {
                apply(role, content, to: &beats[beats.count - 1])
            }
        }
        return beats
    }

    // MARK: - First-principles spine + doctrine flash (the coherence layer)

    /// Body of a `##`/`#` section whose heading contains `heading` (lowercased
    /// substring), sliced to the next H1/H2. H3 (`### Movement`) lines stay inside.
    private static func sectionBody(_ md: String, heading: String) -> String {
        let lines = md.components(separatedBy: "\n")
        var start: Int?
        for (i, l) in lines.enumerated() where l.hasPrefix("#") {
            if l.lowercased().contains(heading) { start = i; break }
        }
        guard let s = start, s + 1 < lines.count else { return "" }
        var end = lines.count
        for i in (s + 1)..<lines.count where lines[i].hasPrefix("# ") || lines[i].hasPrefix("## ") {
            end = i
            break
        }
        return lines[(s + 1)..<end].joined(separator: "\n")
    }

    /// Value after a `- **Label:** value` / `Label: value` bullet, ignoring markdown
    /// bold and bullet markers. Nil when absent or empty.
    private static func bulletField(_ section: String, label: String) -> String? {
        let key = label.lowercased() + ":"
        for raw in section.components(separatedBy: "\n") {
            var line = raw.trimmingCharacters(in: .whitespaces)
            while let f = line.first, f == "-" || f == "*" || f == ">" || f == " " { line.removeFirst() }
            let stripped = line.lowercased().replacingOccurrences(of: "*", with: "")
            guard stripped.hasPrefix(key), let colon = line.range(of: ":") else { continue }
            let value = String(line[colon.upperBound...])
                .trimmingCharacters(in: CharacterSet(charactersIn: " *"))
            return value.isEmpty ? nil : value
        }
        return nil
    }

    /// "AX-3 Authority by derivation, not possession" -> id + title.
    private static func doctrineFromPrimary(_ s: String, doNotImply: String?) -> DoctrineFlash? {
        let parts = s.trimmingCharacters(in: .whitespaces).split(separator: " ", maxSplits: 1).map(String.init)
        guard let id = parts.first,
              id.range(of: "^(AX|P|AP)-[0-9]+$", options: .regularExpression) != nil else { return nil }
        let title = parts.count > 1 ? parts[1].trimmingCharacters(in: .whitespaces) : ""
        return DoctrineFlash(id: id, title: title, flashText: "", doNotImply: doNotImply, publicURL: nil)
    }

    static func parseSpine(_ md: String) -> FirstPrinciplesSpine? {
        let sec = sectionBody(md, heading: "first-principles freestyle spine")
        guard !sec.isEmpty else { return nil }
        let spine = FirstPrinciplesSpine(
            primitiveProblem: bulletField(sec, label: "Primitive problem"),
            irreducibleObjects: bulletField(sec, label: "Irreducible objects"),
            mechanism: bulletField(sec, label: "Mechanism"),
            workedExample: bulletField(sec, label: "Worked example"),
            claimCeiling: bulletField(sec, label: "Claim ceiling"),
            recoveryLine: bulletField(sec, label: "Freestyle recovery line")
        )
        if spine.irreducibleObjects == nil, spine.mechanism == nil, spine.claimCeiling == nil { return nil }
        return spine
    }

    static func parseDoctrineThroughLine(_ md: String) -> DoctrineFlash? {
        let sec = sectionBody(md, heading: "doctrine through-line")
        guard !sec.isEmpty, let primary = bulletField(sec, label: "Primary") else { return nil }
        return doctrineFromPrimary(primary, doNotImply: nil)
    }

    static func parseDoctrineFlashes(_ md: String) -> [DoctrineFlash] {
        let sec = sectionBody(md, heading: "doctrine flash per movement")
        guard !sec.isEmpty else { return [] }
        var flashes: [DoctrineFlash] = []
        var current: [String] = []
        func flush() {
            guard !current.isEmpty else { return }
            let block = current.joined(separator: "\n")
            if let primary = bulletField(block, label: "Primary"),
               var d = doctrineFromPrimary(primary, doNotImply: bulletField(block, label: "Do not imply")) {
                d.flashText = bulletField(block, label: "Flash text") ?? ""
                d.publicURL = bulletField(block, label: "Public surface")
                flashes.append(d)
            }
            current = []
        }
        for raw in sec.components(separatedBy: "\n") {
            var line = raw.trimmingCharacters(in: .whitespaces)
            while let f = line.first, f == "-" || f == "*" || f == ">" || f == " " { line.removeFirst() }
            if line.lowercased().replacingOccurrences(of: "*", with: "").hasPrefix("primary:") {
                flush()
                current = [raw]
            } else {
                current.append(raw)
            }
        }
        flush()
        return flashes
    }

    /// Attach each movement's doctrine flash to its beat. A terse `DOCTRINE` cue
    /// line (id + flash text) is enriched with the title/url/do-not-imply from the
    /// matching per-movement block; beats with no cue line take the flash by order.
    static func bindDoctrineToBeats(_ beats: [BeatCue], flashes: [DoctrineFlash]) -> [BeatCue] {
        guard !flashes.isEmpty || beats.contains(where: { $0.doctrine != nil }) else { return beats }
        var out = beats
        for i in out.indices {
            if let cue = out[i].doctrine {
                let match = flashes.first(where: { $0.id == cue.id }) ?? (i < flashes.count ? flashes[i] : nil)
                if let m = match {
                    out[i].doctrine = DoctrineFlash(
                        id: cue.id,
                        title: m.title,
                        flashText: cue.flashText.isEmpty ? m.flashText : cue.flashText,
                        doNotImply: m.doNotImply,
                        publicURL: m.publicURL
                    )
                }
            } else if i < flashes.count {
                out[i].doctrine = flashes[i]
            }
        }
        return out
    }
}
