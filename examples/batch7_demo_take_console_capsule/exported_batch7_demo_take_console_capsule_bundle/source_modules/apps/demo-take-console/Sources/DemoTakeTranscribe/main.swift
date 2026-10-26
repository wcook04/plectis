import Foundation
import WhisperKit

@main
struct DemoTakeTranscribe {
    static func main() async {
        do {
            let options = try parseArgs(CommandLine.arguments)
            try await run(options)
        } catch {
            let payload: [String: Any] = [
                "status": "failed",
                "error": String(describing: error),
            ]
            if let data = try? JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys]) {
                FileHandle.standardError.write(data)
                FileHandle.standardError.write("\n".data(using: .utf8)!)
            }
            exit(1)
        }
    }

    static func run(_ options: Options) async throws {
        let absAudio = URL(fileURLWithPath: options.audioPath).path
        guard FileManager.default.fileExists(atPath: absAudio) else {
            throw RuntimeError.audioNotFound(absAudio)
        }

        let config = WhisperKitConfig(model: options.model, verbose: false)
        let pipe = try await WhisperKit(config)

        // VAD chunking parallelizes by splitting at detected silences, but on
        // long quiet-mic narration it can misclassify dense speech as silence
        // and silently drop multi-minute spans (observed on take_20260612_092437:
        // 600s of continuous speech -> 7 segments). Sequential (.none) decodes
        // every window. Callers that want the fast path can pass --chunking vad.
        let decode = DecodingOptions(
            verbose: false,
            task: .transcribe,
            language: options.language,
            wordTimestamps: true,
            chunkingStrategy: options.chunking == "vad" ? .vad : nil
        )

        let results = try await pipe.transcribe(
            audioPath: absAudio,
            decodeOptions: decode,
            callback: nil
        )

        let payload = buildPayload(
            results: results,
            options: options,
            audioPath: absAudio
        )
        let data = try JSONSerialization.data(
            withJSONObject: payload,
            options: [.prettyPrinted, .sortedKeys]
        )
        try data.write(to: URL(fileURLWithPath: options.outputJSON))

        if let srtPath = options.outputSRT {
            let srt = buildSRT(results: results)
            try srt.data(using: .utf8)?.write(to: URL(fileURLWithPath: srtPath))
        }

        let status: [String: Any] = [
            "status": "ready",
            "output_json": options.outputJSON,
            "output_srt": options.outputSRT as Any? ?? NSNull(),
            "segment_count": results.flatMap(\.segments).count,
            "model": options.model,
        ]
        let statusData = try JSONSerialization.data(withJSONObject: status, options: [.sortedKeys])
        FileHandle.standardOutput.write(statusData)
        FileHandle.standardOutput.write("\n".data(using: .utf8)!)
    }

    static func buildPayload(
        results: [TranscriptionResult],
        options: Options,
        audioPath: String
    ) -> [String: Any] {
        var segmentObjects: [[String: Any]] = []
        var wordObjects: [[String: Any]] = []
        var totalDuration: Float = 0
        var language: String? = nil

        for result in results {
            if language == nil, !result.language.isEmpty { language = result.language }
            for segment in result.segments {
                totalDuration = max(totalDuration, segment.end)
                var segmentWordObjects: [[String: Any]] = []
                if let words = segment.words {
                    for word in words {
                        let wordRecord: [String: Any] = [
                            "word": word.word,
                            "start": Double(word.start),
                            "end": Double(word.end),
                            "probability": Double(word.probability),
                        ]
                        segmentWordObjects.append(wordRecord)
                        wordObjects.append(wordRecord)
                    }
                }
                segmentObjects.append([
                    "id": String(format: "seg_%04d", segment.id),
                    "start": Double(segment.start),
                    "end": Double(segment.end),
                    "text": segment.text,
                    "words": segmentWordObjects,
                    "avg_log_prob": Double(segment.avgLogprob),
                    "no_speech_prob": Double(segment.noSpeechProb),
                    "compression_ratio": Double(segment.compressionRatio),
                ])
            }
        }

        let createdAt = ISO8601DateFormatter().string(from: Date())
        return [
            "schema": "demo_take_transcript_v0",
            "status": "ready",
            "created_at": createdAt,
            "model": options.model,
            "language": language ?? "",
            "source_track": options.sourceTrackRelativePath ?? audioPath,
            "duration_seconds": Double(totalDuration),
            "segments": segmentObjects,
            "words": wordObjects,
            "segment_count": segmentObjects.count,
            "word_count": wordObjects.count,
        ]
    }

    static func buildSRT(results: [TranscriptionResult]) -> String {
        var lines: [String] = []
        var index = 1
        for result in results {
            for segment in result.segments {
                lines.append("\(index)")
                lines.append("\(srtTimestamp(segment.start)) --> \(srtTimestamp(segment.end))")
                lines.append(segment.text.trimmingCharacters(in: .whitespacesAndNewlines))
                lines.append("")
                index += 1
            }
        }
        return lines.joined(separator: "\n")
    }

    static func srtTimestamp(_ seconds: Float) -> String {
        let totalMilliseconds = Int((seconds * 1000).rounded())
        let hours = totalMilliseconds / 3_600_000
        let minutes = (totalMilliseconds % 3_600_000) / 60_000
        let secs = (totalMilliseconds % 60_000) / 1_000
        let millis = totalMilliseconds % 1_000
        return String(format: "%02d:%02d:%02d,%03d", hours, minutes, secs, millis)
    }
}

struct Options {
    let audioPath: String
    let outputJSON: String
    let outputSRT: String?
    let model: String
    let language: String?
    let sourceTrackRelativePath: String?
    let chunking: String
}

enum RuntimeError: Error, CustomStringConvertible {
    case missingFlag(String)
    case unknownArg(String)
    case audioNotFound(String)
    case usage(String)

    var description: String {
        switch self {
        case .missingFlag(let flag): "missing required flag: \(flag)"
        case .unknownArg(let arg): "unknown argument: \(arg)"
        case .audioNotFound(let path): "audio file not found: \(path)"
        case .usage(let text): text
        }
    }
}

func parseArgs(_ argv: [String]) throws -> Options {
    var audioPath: String?
    var outputJSON: String?
    var outputSRT: String?
    var model: String = "openai_whisper-base"
    var language: String?
    var sourceTrackRelativePath: String?
    var chunking: String = "none"

    var i = 1
    while i < argv.count {
        let arg = argv[i]
        switch arg {
        case "--audio":
            i += 1
            audioPath = argv[safe: i]
        case "--output-json":
            i += 1
            outputJSON = argv[safe: i]
        case "--output-srt":
            i += 1
            outputSRT = argv[safe: i]
        case "--model":
            i += 1
            model = argv[safe: i] ?? model
        case "--language":
            i += 1
            language = argv[safe: i]
        case "--source-track":
            i += 1
            sourceTrackRelativePath = argv[safe: i]
        case "--chunking":
            i += 1
            chunking = argv[safe: i] ?? chunking
        case "--help", "-h":
            throw RuntimeError.usage("""
                demo-take-transcribe --audio <path> --output-json <path> [--output-srt <path>] [--model <name>] [--language <code>] [--source-track <relative>] [--chunking none|vad]
                """)
        default:
            throw RuntimeError.unknownArg(arg)
        }
        i += 1
    }

    guard let audioPath else { throw RuntimeError.missingFlag("--audio") }
    guard let outputJSON else { throw RuntimeError.missingFlag("--output-json") }
    return Options(
        audioPath: audioPath,
        outputJSON: outputJSON,
        outputSRT: outputSRT,
        model: model,
        language: language,
        sourceTrackRelativePath: sourceTrackRelativePath,
        chunking: chunking
    )
}

private extension Array {
    subscript(safe index: Int) -> Element? {
        indices.contains(index) ? self[index] : nil
    }
}
