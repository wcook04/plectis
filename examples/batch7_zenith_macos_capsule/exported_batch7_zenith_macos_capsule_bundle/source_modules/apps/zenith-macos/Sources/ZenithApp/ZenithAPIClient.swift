import Foundation

enum ZenithAPIError: LocalizedError {
    case invalidBaseURL
    case invalidResponse
    case http(Int, String)

    var errorDescription: String? {
        switch self {
        case .invalidBaseURL:
            return "Invalid backend base URL."
        case .invalidResponse:
            return "Backend returned a non-HTTP response."
        case let .http(status, detail):
            return detail.isEmpty ? "HTTP \(status)" : detail
        }
    }
}

struct ZenithAPIClient {
    var baseURL: URL = URL(string: "http://127.0.0.1:8000")!

    private var decoder: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }

    private var encoder: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        return encoder
    }

    func stationLauncher(timeout: TimeInterval = 3.0) async throws -> StationLauncherSnapshot {
        try await request("/api/station/launcher", timeout: timeout)
    }

    func attention(timeout: TimeInterval = 2.5) async throws -> AttentionSnapshot {
        try await request("/api/world-model/attention", timeout: timeout)
    }

    func bootstrap(timeout: TimeInterval = 5.0) async throws -> ZenithBootstrapResponse {
        try await request("/api/zenith/bootstrap", timeout: timeout)
    }

    func runtimeSnapshot(timeout: TimeInterval = 1.5) async throws -> RuntimeSnapshot {
        try await request("/api/zenith/runtime", timeout: timeout)
    }

    func health(timeout: TimeInterval = 0.8) async throws -> ZenithHealthResponse {
        try await request("/api/zenith/health", timeout: timeout)
    }

    func appendRawSeed(_ body: RawSeedAppendRequestBody) async throws -> RawSeedAppendResponse {
        try await request("/api/raw-seed/append", method: "POST", body: body)
    }

    func launchOperation(operationID: String, parameters: [String: String]) async throws -> OperationLaunchEnvelope {
        try await request(
            "/api/world-model/operations/launch",
            method: "POST",
            body: OperationLaunchRequestBody(
                operationId: operationID,
                parameters: parameters,
                actorId: "human_operator"
            )
        )
    }

    func acknowledgeGate(reason: String? = nil) async throws -> OrchestrationAcknowledgeEnvelope {
        try await request(
            "/api/world-model/orchestration/acknowledge",
            method: "POST",
            body: OrchestrationAcknowledgeRequestBody(
                actorId: "human_operator",
                reason: reason
            )
        )
    }

    func postRecordingViewEvent(
        _ body: RecordingViewEventBody,
        timeout: TimeInterval = 1.0
    ) async throws -> RecordingViewEventResponse {
        try await request("/api/recording/view-event", method: "POST", body: body, timeout: timeout)
    }

    func ping(timeout: TimeInterval = 1.5) async -> Bool {
        do {
            return try await health(timeout: min(timeout, 0.8)).ok
        } catch ZenithAPIError.http(let status, _) where status == 404 {
            do {
                _ = try await runtimeSnapshot(timeout: timeout)
                return true
            } catch {
                return false
            }
        } catch {
            return false
        }
    }

    private func request<T: Decodable>(
        _ path: String,
        method: String = "GET",
        timeout: TimeInterval = 10.0
    ) async throws -> T {
        try await request(path, method: method, bodyData: nil, timeout: timeout)
    }

    private func request<T: Decodable, Body: Encodable>(
        _ path: String,
        method: String,
        body: Body,
        timeout: TimeInterval = 10.0
    ) async throws -> T {
        try await request(path, method: method, bodyData: encoder.encode(body), timeout: timeout)
    }

    private func request<T: Decodable>(
        _ path: String,
        method: String,
        bodyData: Data?,
        timeout: TimeInterval
    ) async throws -> T {
        guard let url = URL(string: path, relativeTo: baseURL) else {
            throw ZenithAPIError.invalidBaseURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = timeout
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = bodyData

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw ZenithAPIError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            let detail = String(data: data, encoding: .utf8) ?? ""
            throw ZenithAPIError.http(http.statusCode, detail)
        }
        do {
            return try decoder.decode(T.self, from: data)
        } catch let decodeError {
            // Log the exact decode failure to stderr so `log stream` can show
            // which path and which coding key failed. Still throws so callers
            // handle the empty-state, but the operator can see *why* when
            // debugging a schema drift.
            FileHandle.standardError.write(Data(
                "[ZenithAPI] decode failed for \(path) → \(T.self): \(decodeError)\n".utf8
            ))
            throw decodeError
        }
    }
}
