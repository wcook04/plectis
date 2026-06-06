import Foundation

struct StartCaptureResponse: Decodable {
    let takeID: String
    let rootPath: String
    let title: String?
    let statusLines: [String]
}

struct StopCaptureResponse: Decodable {
    let takeID: String
    let rootPath: String
    let statusLines: [String]
    let knownFailures: [String]?
}

struct HelperStatusResponse: Decodable {
    let statusLines: [String]
}

struct TitleUpdateResponse: Decodable {
    let takeID: String
    let rootPath: String
    let title: String?
    let statusLines: [String]

    enum CodingKeys: String, CodingKey {
        case takeID = "takeID"
        case rootPath
        case title
        case statusLines
    }
}

struct ImportVideoResponse: Decodable {
    let takeID: String
    let rootPath: String
    let title: String?
    let asset: String?
    let statusLines: [String]
}

struct CompactStorageResponse: Decodable {
    let takeID: String
    let rootPath: String
    let bytesSaved: Int64?
    let statusLines: [String]
    let knownFailures: [String]?
}

struct StorageStatusResponse: Decodable {
    let takeID: String
    let rootPath: String
    let physicalBytes: Int64?
    let logicalBytes: Int64?
    let dedupeSavedBytes: Int64?
    let roughCutScreenHardlinked: Bool?
    let canCompact: Bool?
    let storageLine: String?
    let statusLines: [String]?
}

struct ExportVideoResponse: Decodable {
    let takeID: String
    let rootPath: String
    let source: String?
    let exportPath: String
    let exportRelativePath: String?
    let method: String?
    let bytes: Int64?
    let statusLines: [String]
}

struct TestMicrophoneResponse: Decodable {
    let status: String
    let statusLines: [String]
    let bytes: Int?
}

struct MarkResponse: Decodable {
    let marker: Marker
    let markerCount: Int
}

struct ListMarkersResponse: Decodable {
    let markers: [Marker]
}

enum CaptureHelperClient {
    static func loadDevices(ffmpegPath: String) async throws -> DeviceInventory {
        let data = try await run(["devices", "--ffmpeg", ffmpegPath])
        return try JSONDecoder().decode(DeviceInventory.self, from: data)
    }

    static func start(
        ffmpegPath: String,
        screens: [CaptureDevice],
        microphone: CaptureDevice?,
        webcam: CaptureDevice?,
        screenshotInterval: Int,
        transcribeBinary: String?,
        transcribeModel: String,
        takeTitle: String
    ) async throws -> StartCaptureResponse {
        var config: [String: Any] = [
            "repo_root": HostEnvironment.repoRoot.path,
            "ffmpeg_path": ffmpegPath,
            "screenshot_interval_seconds": screenshotInterval,
            "screens": screens.map(deviceObject),
            "microphone": microphone.map(deviceObject) ?? NSNull(),
            "webcam": webcam.map(deviceObject) ?? NSNull(),
            "transcribe_model": transcribeModel,
        ]
        if let transcribeBinary, !transcribeBinary.isEmpty {
            config["transcribe_binary"] = transcribeBinary
        }
        let title = takeTitle.trimmingCharacters(in: .whitespacesAndNewlines)
        if !title.isEmpty {
            config["take_title"] = title
        }
        let data = try JSONSerialization.data(withJSONObject: config, options: [.sortedKeys])
        let configJSON = String(decoding: data, as: UTF8.self)
        let output = try await run(["start", "--config-json", configJSON])
        return try JSONDecoder().decode(StartCaptureResponse.self, from: output)
    }

    static func pause(takeRoot: URL) async throws -> HelperStatusResponse {
        let data = try await run(["pause", "--take-root", takeRoot.path])
        return try JSONDecoder().decode(HelperStatusResponse.self, from: data)
    }

    static func resume(takeRoot: URL) async throws -> HelperStatusResponse {
        let data = try await run(["resume", "--take-root", takeRoot.path])
        return try JSONDecoder().decode(HelperStatusResponse.self, from: data)
    }

    static func finalize(takeRoot: URL) async throws -> StopCaptureResponse {
        let data = try await run(["finalize", "--take-root", takeRoot.path])
        return try JSONDecoder().decode(StopCaptureResponse.self, from: data)
    }

    static func postprocess(takeRoot: URL) async throws -> StopCaptureResponse {
        let data = try await run(["postprocess", "--take-root", takeRoot.path])
        return try JSONDecoder().decode(StopCaptureResponse.self, from: data)
    }

    static func testMicrophone(ffmpegPath: String, microphone: CaptureDevice) async throws -> TestMicrophoneResponse {
        let data = try await run([
            "test-microphone",
            "--ffmpeg", ffmpegPath,
            "--index", "\(microphone.index)",
            "--name", microphone.name,
        ])
        return try JSONDecoder().decode(TestMicrophoneResponse.self, from: data)
    }

    static func stop(takeRoot: URL) async throws -> StopCaptureResponse {
        let data = try await run(["stop", "--take-root", takeRoot.path])
        return try JSONDecoder().decode(StopCaptureResponse.self, from: data)
    }

    static func mark(takeRoot: URL, source: MarkerSource, label: String?) async throws -> MarkResponse {
        var args = ["mark", "--take-root", takeRoot.path, "--source", source.rawValue]
        if let label, !label.isEmpty {
            args.append("--label")
            args.append(label)
        }
        let data = try await run(args)
        return try JSONDecoder().decode(MarkResponse.self, from: data)
    }

    static func listMarkers(takeRoot: URL) async throws -> ListMarkersResponse {
        let data = try await run(["list-markers", "--take-root", takeRoot.path])
        return try JSONDecoder().decode(ListMarkersResponse.self, from: data)
    }

    static func setTitle(takeRoot: URL, title: String) async throws -> TitleUpdateResponse {
        let data = try await run(["set-title", "--take-root", takeRoot.path, "--title", title])
        return try JSONDecoder().decode(TitleUpdateResponse.self, from: data)
    }

    static func importVideo(sourceURL: URL, title: String) async throws -> ImportVideoResponse {
        var args = [
            "import-video",
            "--source", sourceURL.path,
            "--repo-root", HostEnvironment.repoRoot.path,
        ]
        let cleanTitle = title.trimmingCharacters(in: .whitespacesAndNewlines)
        if !cleanTitle.isEmpty {
            args += ["--title", cleanTitle]
        }
        let data = try await run(args)
        return try JSONDecoder().decode(ImportVideoResponse.self, from: data)
    }

    static func compactStorage(takeRoot: URL) async throws -> CompactStorageResponse {
        let data = try await run(["compact-storage", "--take-root", takeRoot.path])
        return try JSONDecoder().decode(CompactStorageResponse.self, from: data)
    }

    static func storageStatus(takeRoot: URL) async throws -> StorageStatusResponse {
        let data = try await run(["storage-status", "--take-root", takeRoot.path])
        return try JSONDecoder().decode(StorageStatusResponse.self, from: data)
    }

    static func exportVideo(takeRoot: URL) async throws -> ExportVideoResponse {
        let data = try await run(["export-video", "--take-root", takeRoot.path])
        return try JSONDecoder().decode(ExportVideoResponse.self, from: data)
    }

    static func scheduleState(takeRoot: URL?) async throws -> RunMapScheduleState {
        var args = ["schedule-state"]
        if let takeRoot {
            args.append("--take-root")
            args.append(takeRoot.path)
            args.append("--emit-progress")
        }
        let data = try await run(args)
        return try JSONDecoder().decode(RunMapScheduleState.self, from: data)
    }

    private static func run(_ arguments: [String]) async throws -> Data {
        try await Task.detached(priority: .utility) {
            let process = Process()
            process.executableURL = repoPythonURL()
            process.arguments = [helperScriptURL().path] + arguments

            let stdout = Pipe()
            let stderr = Pipe()
            process.standardOutput = stdout
            process.standardError = stderr
            try process.run()
            process.waitUntilExit()

            let output = stdout.fileHandleForReading.readDataToEndOfFile()
            if process.terminationStatus == 0 {
                return output
            }
            let errorData = stderr.fileHandleForReading.readDataToEndOfFile()
            let errorText = String(decoding: errorData, as: UTF8.self)
            throw HelperError.failed(errorText.isEmpty ? "capture helper exited \(process.terminationStatus)" : errorText)
        }.value
    }

    private static func repoPythonURL() -> URL {
        let repoPython = HostEnvironment.repoRoot.appendingPathComponent("repo-python")
        if FileManager.default.isExecutableFile(atPath: repoPython.path) {
            return repoPython
        }
        return URL(fileURLWithPath: "/usr/bin/python3")
    }

    private static func helperScriptURL() -> URL {
        HostEnvironment.repoRoot
            .appendingPathComponent("apps", isDirectory: true)
            .appendingPathComponent("demo-take-console", isDirectory: true)
            .appendingPathComponent("support", isDirectory: true)
            .appendingPathComponent("demo_take_capture.py")
    }

    private static func deviceObject(_ device: CaptureDevice) -> [String: Any] {
        [
            "id": device.id,
            "index": device.index,
            "name": device.name,
            "kind": device.kind.rawValue,
            "is_screen": device.isScreen,
        ]
    }
}

enum HelperError: LocalizedError {
    case failed(String)

    var errorDescription: String? {
        switch self {
        case .failed(let message):
            message.trimmingCharacters(in: .whitespacesAndNewlines)
        }
    }
}
