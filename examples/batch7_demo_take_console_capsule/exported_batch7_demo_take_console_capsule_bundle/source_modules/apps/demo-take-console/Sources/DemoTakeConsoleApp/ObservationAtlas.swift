import Foundation

enum ObservationAtlasStatus: Equatable {
    case notChecked
    case missing
    case ready
    case failed(String)
}

struct ObservationAtlasFile: Decodable {
    let takeId: String?
    let createdAt: String?
    let summary: ObservationAtlasSummary?
    let chapters: [ObservationChapter]
    let phraseCardIndex: [ObservationPhraseIndex]
    let candidateClipIndex: [ObservationCandidateClip]

    enum CodingKeys: String, CodingKey {
        case takeId
        case createdAt
        case summary
        case chapters
        case phraseCardIndex
        case candidateClipIndex
    }
}

struct ObservationAtlasSummary: Decodable {
    let durationDisplay: String?
    let durationSeconds: Double?
    let markerCount: Int?
    let phraseCardCount: Int?
    let candidateClipCount: Int?
    let transcriptCueCount: Int?
    let transcriptCoverageRatio: Double?
    let storage: ObservationStorageSummary?
}

struct ObservationStorageSummary: Decodable {
    let mediaTier: String?
    let storageProfile: String?
    let cloudState: String?
    let localRawState: String?
    let hydrateState: String?
    let proxyState: String?

    var compactLine: String {
        [
            storageProfile.map { "storage \($0)" },
            proxyState.map { "proxy \($0)" },
            localRawState.map { "raw \($0)" },
            cloudState.map { "cloud \($0)" },
        ]
        .compactMap { $0 }
        .joined(separator: " / ")
    }
}

struct ObservationChapter: Decodable, Identifiable, Hashable {
    let id: String
    let title: String?
    let displayTime: String?
    let durationSeconds: Double?
    let activeStartSeconds: Double?
    let activeEndSeconds: Double?
    let phraseCardCount: Int?
    let phraseCardIds: [String]?
    let candidateClipRefs: [String]?
    let representativeFrame: String?

    var seekSeconds: Double {
        activeStartSeconds ?? ObservationTimeParser.startSeconds(from: displayTime) ?? 0
    }
}

struct ObservationPhraseIndex: Decodable, Identifiable, Hashable {
    let id: String
    let displayTime: String?
    let text: String?
    let representativeFrame: String?
    let candidateClipRefs: [String]?
    let motionKind: String?
}

struct ObservationPhraseCard: Decodable, Identifiable, Hashable {
    let id: String
    let takeId: String?
    let displayTime: String?
    let text: String?
    let representativeFrame: String?
    let activeStartSeconds: Double?
    let activeEndSeconds: Double?
    let candidateClipRefs: [String]?
    let nearbyEvents: [ObservationNearbyEvent]?
    let audioSummary: ObservationAudioSummary?
    let visualSummary: ObservationVisualSummary?

    init(
        id: String,
        takeId: String?,
        displayTime: String?,
        text: String?,
        representativeFrame: String?,
        activeStartSeconds: Double?,
        activeEndSeconds: Double?,
        candidateClipRefs: [String]?,
        nearbyEvents: [ObservationNearbyEvent]? = nil,
        audioSummary: ObservationAudioSummary? = nil,
        visualSummary: ObservationVisualSummary? = nil
    ) {
        self.id = id
        self.takeId = takeId
        self.displayTime = displayTime
        self.text = text
        self.representativeFrame = representativeFrame
        self.activeStartSeconds = activeStartSeconds
        self.activeEndSeconds = activeEndSeconds
        self.candidateClipRefs = candidateClipRefs
        self.nearbyEvents = nearbyEvents
        self.audioSummary = audioSummary
        self.visualSummary = visualSummary
    }

    var seekSeconds: Double {
        activeStartSeconds ?? ObservationTimeParser.startSeconds(from: displayTime) ?? 0
    }

    var displayText: String {
        let trimmed = (text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? id : trimmed
    }

    func representativeFrameURL(in takeRoot: URL?) -> URL? {
        guard let takeRoot, let representativeFrame, !representativeFrame.isEmpty else { return nil }
        return takeRoot.appendingPathComponent(representativeFrame)
    }
}

struct ObservationNearbyEvent: Decodable, Hashable {
    let id: String?
    let kind: String?
    let label: String?
    let activeTimeUs: Int64?
}

struct ObservationAudioSummary: Decodable, Hashable {
    let speechConfidence: Double?
    let method: String?
}

struct ObservationVisualSummary: Decodable, Hashable {
    let motionKind: String?
    let sceneChangeScore: Double?
    let needsContactSheet: Bool?
}

struct ObservationCandidateClip: Decodable, Identifiable, Hashable {
    let id: String
    let clipKind: String?
    let displayTime: String?
    let safeRenderRange: ObservationSafeRenderRange?
    let score: Double?
    let publicSafe: Bool?
    let renderReceipt: String?
    let viewLabel: String?

    var title: String {
        let raw = viewLabel ?? id.replacingOccurrences(of: "_", with: " ")
        return raw.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? id : raw
    }

    var seekSeconds: Double {
        safeRenderRange?.startSeconds ?? ObservationTimeParser.startSeconds(from: displayTime) ?? 0
    }

    func renderedClipURL(in takeRoot: URL?) -> URL? {
        guard let takeRoot else { return nil }
        let candidates = [
            "render/clips/\(id)_proxy.mp4",
            "render/clips/\(id).mp4",
        ].map { takeRoot.appendingPathComponent($0) }
        return candidates.first { FileManager.default.fileExists(atPath: $0.path) }
    }
}

struct ObservationSafeRenderRange: Decodable, Hashable {
    let startSeconds: Double?
    let endSeconds: Double?
    let startActiveUs: Int64?
    let endActiveUs: Int64?
    let policy: String?
}

@MainActor
final class ObservationAtlasController: ObservableObject {
    @Published var status: ObservationAtlasStatus = .notChecked
    @Published var atlas: ObservationAtlasFile?
    @Published var phraseCards: [ObservationPhraseCard] = []

    private var loadedTakePath: String?

    var hasBrowseData: Bool {
        atlas != nil || !phraseCards.isEmpty
    }

    var chapters: [ObservationChapter] {
        atlas?.chapters ?? []
    }

    var candidateClips: [ObservationCandidateClip] {
        atlas?.candidateClipIndex ?? []
    }

    var summaryLine: String {
        guard let summary = atlas?.summary else {
            if phraseCards.isEmpty { return "No browse digest yet." }
            return "\(phraseCards.count) phrase cards"
        }
        let coverage = summary.transcriptCoverageRatio.map { "\(Int(($0 * 100).rounded()))% transcript" }
        return [
            summary.durationDisplay,
            phraseCards.isEmpty ? summary.phraseCardCount.map { "\($0) phrase cards" } : "\(phraseCards.count) phrase cards",
            summary.candidateClipCount.map { "\($0) clips" },
            summary.markerCount.map { "\($0) markers" },
            coverage,
        ]
        .compactMap { $0 }
        .joined(separator: " / ")
    }

    var storageLine: String {
        atlas?.summary?.storage?.compactLine ?? ""
    }

    func reload(takeRoot: URL?, force: Bool = false) {
        guard let takeRoot else {
            loadedTakePath = nil
            atlas = nil
            phraseCards = []
            status = .notChecked
            return
        }
        if !force, loadedTakePath == takeRoot.path { return }
        loadedTakePath = takeRoot.path

        do {
            let loadedAtlas = try loadAtlas(from: takeRoot)
            let loadedCards = try loadPhraseCards(from: takeRoot, atlas: loadedAtlas)
            atlas = loadedAtlas
            phraseCards = loadedCards
            status = (loadedAtlas == nil && loadedCards.isEmpty) ? .missing : .ready
        } catch {
            atlas = nil
            phraseCards = []
            status = .failed(error.localizedDescription)
        }
    }

    private func loadAtlas(from takeRoot: URL) throws -> ObservationAtlasFile? {
        let url = takeRoot.appendingPathComponent("observation_atlas.json")
        guard FileManager.default.fileExists(atPath: url.path) else { return nil }
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(ObservationAtlasFile.self, from: Data(contentsOf: url))
    }

    private func loadPhraseCards(from takeRoot: URL, atlas: ObservationAtlasFile?) throws -> [ObservationPhraseCard] {
        let url = takeRoot.appendingPathComponent("phrase_cards.jsonl")
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        if FileManager.default.fileExists(atPath: url.path) {
            let text = try String(contentsOf: url, encoding: .utf8)
            return try text.split(separator: "\n").compactMap { line -> ObservationPhraseCard? in
                let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
                guard !trimmed.isEmpty else { return nil }
                return try decoder.decode(ObservationPhraseCard.self, from: Data(trimmed.utf8))
            }
            .sorted { $0.seekSeconds < $1.seekSeconds }
        }

        return (atlas?.phraseCardIndex ?? []).map { phrase in
            ObservationPhraseCard(
                id: phrase.id,
                takeId: atlas?.takeId,
                displayTime: phrase.displayTime,
                text: phrase.text,
                representativeFrame: phrase.representativeFrame,
                activeStartSeconds: ObservationTimeParser.startSeconds(from: phrase.displayTime),
                activeEndSeconds: ObservationTimeParser.endSeconds(from: phrase.displayTime),
                candidateClipRefs: phrase.candidateClipRefs,
                visualSummary: ObservationVisualSummary(
                    motionKind: phrase.motionKind,
                    sceneChangeScore: nil,
                    needsContactSheet: nil
                )
            )
        }
        .sorted { $0.seekSeconds < $1.seekSeconds }
    }
}

enum ObservationTimeParser {
    static func startSeconds(from displayTime: String?) -> Double? {
        guard let first = displayTime?.split(separator: "-").first else { return nil }
        return seconds(fromClock: String(first))
    }

    static func endSeconds(from displayTime: String?) -> Double? {
        guard let last = displayTime?.split(separator: "-").last else { return nil }
        return seconds(fromClock: String(last))
    }

    static func seconds(fromClock raw: String) -> Double? {
        let parts = raw.trimmingCharacters(in: .whitespacesAndNewlines).split(separator: ":").map(String.init)
        guard parts.count >= 2 else { return Double(raw) }
        guard let seconds = Double(parts.last ?? "") else { return nil }
        let minutes = Double(parts.dropLast().last ?? "") ?? 0
        let hours = parts.count == 3 ? (Double(parts.first ?? "") ?? 0) : 0
        return hours * 3600 + minutes * 60 + seconds
    }
}
