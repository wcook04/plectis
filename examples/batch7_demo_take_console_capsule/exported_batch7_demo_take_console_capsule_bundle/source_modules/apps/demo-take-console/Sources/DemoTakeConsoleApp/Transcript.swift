import Foundation

// MARK: - Transcript verification model
//
// The take package writes `transcript/transcript.json` (schema
// `demo_take_transcript_v0`) and `transcript/transcript.srt` after postprocess.
// The native app never loaded them before. This is a view-side reader: it parses
// the local sidecar into timed cues so the Review stage can overlay toggleable
// subtitles and a clickable sync rail. It does NOT mutate the package, and the
// session-local subtitle offset is never persisted.

enum TranscriptStatus: Equatable {
    case notChecked
    case missing
    case ready
    case unavailable(String)
    case failed(String)
}

struct TranscriptCue: Identifiable, Hashable {
    let id: String
    let index: Int
    let start: Double
    let end: Double
    let text: String
}

final class TranscriptController: ObservableObject {
    @Published var status: TranscriptStatus = .notChecked
    @Published var cues: [TranscriptCue] = []
    @Published var subtitlesEnabled: Bool = true
    @Published var largeCaptions: Bool = false
    @Published var offset: Double = 0
    @Published var model: String = ""
    @Published var language: String = ""
    @Published var sourceKind: String = ""

    private var declaredDuration: Double = 0
    private var loadedTakePath: String?

    var cueCount: Int { cues.count }
    var coverageSeconds: Double { cues.last?.end ?? 0 }

    var coverageLine: String {
        switch status {
        case .ready:
            let cov = dtcClock(coverageSeconds)
            if declaredDuration > 0 {
                let pct = min(100, max(0, Int((coverageSeconds / declaredDuration) * 100)))
                return "\(cues.count) cues · \(cov) covered · \(pct)%"
            }
            return "\(cues.count) cues · \(cov) covered"
        case .missing, .notChecked: return "not built"
        case .unavailable:          return "unavailable"
        case .failed:               return "failed"
        }
    }

    func activeCue(at t: Double) -> TranscriptCue? {
        cues.first { t >= $0.start - 0.05 && t <= $0.end + 0.05 }
    }

    func isActive(_ cue: TranscriptCue, at t: Double) -> Bool {
        t >= cue.start - 0.05 && t <= cue.end + 0.05
    }

    func reload(takeRoot: URL?, mediaDuration: Double, force: Bool = false) {
        guard let takeRoot else {
            status = .notChecked
            cues = []
            loadedTakePath = nil
            return
        }
        if !force, loadedTakePath == takeRoot.path, !cues.isEmpty { return }
        loadedTakePath = takeRoot.path
        declaredDuration = mediaDuration

        let fm = FileManager.default
        let jsonURL = takeRoot.appendingPathComponent("transcript/transcript.json")
        let srtURL = takeRoot.appendingPathComponent("transcript/transcript.srt")

        if fm.fileExists(atPath: jsonURL.path) {
            if loadJSON(jsonURL) { return }
        }
        if fm.fileExists(atPath: srtURL.path),
           let text = try? String(contentsOf: srtURL, encoding: .utf8) {
            let parsed = TranscriptController.parseSRT(text)
            cues = parsed
            status = parsed.isEmpty ? .missing : .ready
            sourceKind = "transcript.srt"
            return
        }
        cues = []
        status = .missing
        sourceKind = ""
    }

    // MARK: - JSON

    private struct TranscriptFile: Decodable {
        let status: String?
        let model: String?
        let language: String?
        let durationSeconds: Double?
        let reason: String?
        let error: String?
        let segments: [Seg]?
        struct Seg: Decodable {
            let id: String?
            let start: Double?
            let end: Double?
            let text: String?
        }
    }

    private func loadJSON(_ url: URL) -> Bool {
        do {
            let data = try Data(contentsOf: url)
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            let file = try decoder.decode(TranscriptFile.self, from: data)

            if (file.status ?? "").lowercased() == "unavailable" {
                cues = []
                status = .unavailable(file.reason ?? file.error ?? "Transcription was not available for this take.")
                sourceKind = "transcript.json"
                return true
            }

            let parsed = (file.segments ?? []).enumerated().compactMap { idx, seg -> TranscriptCue? in
                guard let start = seg.start, let end = seg.end,
                      let raw = seg.text?.trimmingCharacters(in: .whitespacesAndNewlines),
                      !raw.isEmpty else { return nil }
                return TranscriptCue(id: seg.id ?? "seg_\(idx)", index: idx, start: start, end: end, text: raw)
            }

            model = file.model ?? ""
            language = file.language ?? ""
            if let d = file.durationSeconds, d > 0 { declaredDuration = max(declaredDuration, d) }
            sourceKind = "transcript.json"
            cues = parsed
            status = parsed.isEmpty
                ? .unavailable("Transcript file had no usable segments.")
                : .ready
            return true
        } catch {
            cues = []
            status = .failed("Could not parse transcript.json (\(error.localizedDescription)).")
            sourceKind = "transcript.json"
            return true
        }
    }

    // MARK: - SRT

    static func parseSRT(_ text: String) -> [TranscriptCue] {
        var cues: [TranscriptCue] = []
        let normalized = text.replacingOccurrences(of: "\r\n", with: "\n")
        let blocks = normalized.components(separatedBy: "\n\n")
        var index = 0
        for block in blocks {
            let lines = block.split(separator: "\n", omittingEmptySubsequences: true).map(String.init)
            guard lines.count >= 2,
                  let timeLineIndex = lines.firstIndex(where: { $0.contains("-->") }) else { continue }
            let parts = lines[timeLineIndex].components(separatedBy: "-->")
            guard parts.count == 2,
                  let start = parseSRTTime(parts[0]),
                  let end = parseSRTTime(parts[1]) else { continue }
            let textLines = Array(lines[(timeLineIndex + 1)...])
            let cueText = textLines.joined(separator: " ").trimmingCharacters(in: .whitespacesAndNewlines)
            guard !cueText.isEmpty else { continue }
            cues.append(TranscriptCue(id: "srt_\(index)", index: index, start: start, end: end, text: cueText))
            index += 1
        }
        return cues
    }

    static func parseSRTTime(_ raw: String) -> Double? {
        let trimmed = raw.trimmingCharacters(in: .whitespaces).replacingOccurrences(of: ",", with: ".")
        let comps = trimmed.components(separatedBy: ":")
        guard comps.count == 3,
              let h = Double(comps[0]),
              let m = Double(comps[1]),
              let s = Double(comps[2]) else { return nil }
        return h * 3600 + m * 60 + s
    }
}
