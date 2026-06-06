import AppKit
import Foundation

enum ZenithSceneID: String, CaseIterable {
    case cockpit = "zenith.cockpit"
    case rawSeedCapture = "zenith.raw-seed-capture"
    case gateQueue = "zenith.gate-queue"
    case runtimePanel = "zenith.runtime-panel"
    case webLens = "zenith.web-lens"
}

enum ZenithNativeLens: String, Codable, CaseIterable {
    case rawSeedCapture = "/native/raw-seed"
    case gateQueue = "/native/gates"
    case runtimePanel = "/native/runtime"

    var sceneID: ZenithSceneID {
        switch self {
        case .rawSeedCapture:
            return .rawSeedCapture
        case .gateQueue:
            return .gateQueue
        case .runtimePanel:
            return .runtimePanel
        }
    }
}

enum ZenithWindowIdentity {
    static func normalizedRoute(_ route: String) -> String {
        let trimmed = route.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty || trimmed == "/" {
            return "/station"
        }
        return trimmed.hasPrefix("/") ? trimmed : "/\(trimmed)"
    }

    static func windowID(for route: String) -> String {
        let normalized = normalizedRoute(route)
        if normalized == "/station" {
            return ZenithSceneID.cockpit.rawValue
        }
        if let nativeLens = ZenithNativeLens(rawValue: normalized) {
            return nativeLens.sceneID.rawValue
        }
        return "web:\(normalized)"
    }
}

enum ZenithQuickLens: CaseIterable, Identifiable {
    case station
    case stationGraph
    case stationTopology
    case stationRoutes
    case stationDoctrine
    case stationDrift
    case metaMissions
    case launchpad
    case inspector
    case rawSeedCapture
    case gateQueue
    case runtimePanel

    var id: String { route }

    var route: String {
        switch self {
        case .station: return "/station"
        case .stationGraph: return "/station/graph"
        case .stationTopology: return "/station/topology"
        case .stationRoutes: return "/station/routes"
        case .stationDoctrine: return "/station/doctrine"
        case .stationDrift: return "/station/drift"
        case .metaMissions: return "/meta-missions"
        case .launchpad: return "/launchpad"
        case .inspector: return "/inspector"
        case .rawSeedCapture: return ZenithNativeLens.rawSeedCapture.rawValue
        case .gateQueue: return ZenithNativeLens.gateQueue.rawValue
        case .runtimePanel: return ZenithNativeLens.runtimePanel.rawValue
        }
    }

    var title: String {
        switch self {
        case .station: return "Station"
        case .stationGraph: return "Station Graph"
        case .stationTopology: return "Topology"
        case .stationRoutes: return "Routes"
        case .stationDoctrine: return "Doctrine"
        case .stationDrift: return "Drift"
        case .metaMissions: return "Meta Missions"
        case .launchpad: return "Launchpad"
        case .inspector: return "Inspector"
        case .rawSeedCapture: return "Raw Seed Capture"
        case .gateQueue: return "Gate Queue"
        case .runtimePanel: return "Runtime"
        }
    }

    var systemImage: String {
        switch self {
        case .station: return "waveform.path.ecg.rectangle"
        case .stationGraph: return "point.3.connected.trianglepath.dotted"
        case .stationTopology: return "square.3.layers.3d"
        case .stationRoutes: return "arrow.triangle.branch"
        case .stationDoctrine: return "books.vertical"
        case .stationDrift: return "tornado"
        case .metaMissions: return "sparkles.rectangle.stack"
        case .launchpad: return "rocket"
        case .inspector: return "sidebar.right"
        case .rawSeedCapture: return "square.and.pencil"
        case .gateQueue: return "exclamationmark.bubble"
        case .runtimePanel: return "terminal"
        }
    }

    var isNative: Bool {
        switch self {
        case .rawSeedCapture, .gateQueue, .runtimePanel:
            return true
        default:
            return false
        }
    }

    static var toolbarPrimary: [ZenithQuickLens] {
        [.station, .metaMissions, .rawSeedCapture, .gateQueue, .runtimePanel]
    }

    static var browserLenses: [ZenithQuickLens] {
        [.stationGraph, .stationTopology, .stationRoutes, .stationDoctrine, .stationDrift, .launchpad, .inspector]
    }

    static func title(for route: String?) -> String {
        guard let route else { return "Zenith" }
        return ZenithQuickLens.allCases.first(where: { $0.route == route })?.title ?? route
    }
}

struct WindowFrameRecord: Codable, Hashable {
    var x: Double
    var y: Double
    var width: Double
    var height: Double

    init(rect: CGRect) {
        self.x = rect.origin.x
        self.y = rect.origin.y
        self.width = rect.size.width
        self.height = rect.size.height
    }

    var cgRect: CGRect {
        CGRect(x: x, y: y, width: width, height: height)
    }
}

struct ZenithWorkspaceWindow: Codable, Hashable, Identifiable {
    var id: String
    var route: String?
    var nativeLens: ZenithNativeLens?
    var title: String?
    var frame: WindowFrameRecord?
    var screenName: String?
}

struct ZenithWorkspace: Codable, Hashable, Identifiable {
    var id: String
    var name: String
    var savedAt: Date
    var repoRoot: String
    var windows: [ZenithWorkspaceWindow]
}

struct ZenithManagedBackendRecord: Codable, Equatable {
    let ownerID: String
    let repoRoot: String
    let backendPID: Int32?
    let startedAt: String

    enum CodingKeys: String, CodingKey {
        case ownerID = "owner_id"
        case repoRoot = "repo_root"
        case backendPID = "backend_pid"
        case startedAt = "started_at"
    }
}

struct StationLauncherSnapshot: Decodable {
    struct FamilySummary: Decodable {
        let familyId: String?
        let familyNumber: String?
        let title: String?
    }

    struct ActivePhaseSummary: Decodable {
        let phaseId: String?
        let title: String?
        let stage: String?
        let cycle: Int?
        let gateReason: String?
    }

    struct StationAlert: Decodable, Identifiable {
        let id: String
        let tone: String
        let label: String
        let detail: String?
        let command: String?
    }

    struct StationOperation: Decodable, Identifiable {
        struct OperationParameter: Decodable {
            let type: String?
            let required: Bool?
            let defaultValue: String?

            enum CodingKeys: String, CodingKey {
                case type
                case required
                case defaultValue = "default"
            }

            init(from decoder: Decoder) throws {
                let container = try decoder.container(keyedBy: CodingKeys.self)
                type = try container.decodeIfPresent(String.self, forKey: .type)
                required = try container.decodeIfPresent(Bool.self, forKey: .required)
                if let stringValue = try? container.decodeIfPresent(String.self, forKey: .defaultValue) {
                    defaultValue = stringValue
                } else if let intValue = try? container.decodeIfPresent(Int.self, forKey: .defaultValue) {
                    defaultValue = String(intValue)
                } else if let doubleValue = try? container.decodeIfPresent(Double.self, forKey: .defaultValue) {
                    defaultValue = String(doubleValue)
                } else if let boolValue = try? container.decodeIfPresent(Bool.self, forKey: .defaultValue) {
                    defaultValue = String(boolValue)
                } else {
                    defaultValue = nil
                }
            }
        }

        let operationId: String
        let label: String
        let kicker: String
        let descriptionShort: String
        let parametersSchema: [String: OperationParameter]?

        var id: String { operationId }
    }

    let generatedAt: String
    let family: FamilySummary
    let activePhase: ActivePhaseSummary?
    let alerts: [StationAlert]
    let operations: [StationOperation]
}

struct AttentionSnapshot: Decodable {
    struct AttentionBanner: Decodable {
        let tone: String
        let title: String
        let summary: String?
        let gateReason: String?
        let command: String?
    }

    struct AttentionItem: Decodable, Identifiable {
        let id: String
        let kind: String
        let title: String
        let detail: String?
        let owner: String?
        let command: String?
        let score: Int
    }

    struct ActivePhase: Decodable {
        let phaseId: String?
        let title: String?
        let phaseDir: String
        let stage: String?
        let cycle: Int?
        let blocked: Bool
        let gateReason: String?
    }

    struct NextHandoff: Decodable {
        let actorId: String?
        let mode: String?
        let command: String?
        let reviewSurface: String?
    }

    let generatedAt: String
    let banner: AttentionBanner
    let attentionItems: [AttentionItem]
    let activePhase: ActivePhase?
    let nextHandoff: NextHandoff?
}

struct RawSeedAppendArtifacts: Decodable {
    let familyDir: String
    let rawSeedPath: String
    let rawSeedJsonPath: String?
    let rawSeedIndexPath: String?
    let rawSeedSnapshotPath: String?
}

struct RawSeedAppendResponse: Decodable {
    let ok: Bool
    let family: String
    let heading: String?
    let appendedAnchorIds: [String]
    let artifacts: RawSeedAppendArtifacts
}

struct RawSeedAppendRequestBody: Encodable {
    let family: String
    let text: String
    let heading: String?
}

struct OperationLaunchRequestBody: Encodable {
    let operationId: String
    let parameters: [String: String]
    let actorId: String
}

struct OperationLaunchEnvelope: Decodable {
    struct ResultPayload: Decodable {
        let operationId: String?
        let returncode: Int?
        let stdout: String?
        let stderr: String?
    }

    let ok: Bool
    let result: ResultPayload?
    let error: String?
}

struct OrchestrationAcknowledgeRequestBody: Encodable {
    let actorId: String
    let reason: String?
}

struct OrchestrationAcknowledgeEnvelope: Decodable {
    let ok: Bool
    let error: String?
}

struct ZenithHealthResponse: Decodable, Equatable {
    let ok: Bool
    let generatedAt: String
}

struct RuntimeServiceStatus: Decodable, Identifiable, Equatable {
    enum State: String, Decodable {
        case running
        case attached
        case stopped
        case failed
        case unknown
    }

    let id: String
    var label: String
    var state: State
    var detail: String
    var tone: String?
    var path: String?
    var updatedAt: String?
    var command: String?
}

struct RuntimeSnapshot: Decodable, Equatable {
    var generatedAt: String?
    var repoRoot: String
    var startCommand: String
    var serverLogPath: String?
    var backend: RuntimeServiceStatus
    var pipelineSignalWatcher: RuntimeServiceStatus
    var controllerSurfaces: [RuntimeServiceStatus]
    var launchAgents: [RuntimeServiceStatus]
    var helperSurfaces: [RuntimeServiceStatus]
    var backendLogLines: [String]

    static let empty = RuntimeSnapshot(
        generatedAt: nil,
        repoRoot: "",
        startCommand: "",
        serverLogPath: nil,
        backend: RuntimeServiceStatus(id: "backend", label: "FastAPI backend", state: .unknown, detail: "Not checked yet."),
        pipelineSignalWatcher: RuntimeServiceStatus(id: "pipeline-signal-watcher", label: "pipeline_signal_watcher.py", state: .unknown, detail: "Not checked yet."),
        controllerSurfaces: [],
        launchAgents: [],
        helperSurfaces: [],
        backendLogLines: []
    )

    static func disconnected(repoRoot: String) -> RuntimeSnapshot {
        RuntimeSnapshot(
            generatedAt: nil,
            repoRoot: repoRoot,
            startCommand: #"cd "\#(repoRoot)" && ./repo-python run_server.py"#,
            serverLogPath: nil,
            backend: RuntimeServiceStatus(
                id: "backend",
                label: "FastAPI backend",
                state: .stopped,
                detail: "Not reachable on 127.0.0.1:8000."
            ),
            pipelineSignalWatcher: RuntimeServiceStatus(
                id: "pipeline-signal-watcher",
                label: "pipeline_signal_watcher.py",
                state: .unknown,
                detail: "Waiting for backend connection."
            ),
            controllerSurfaces: [],
            launchAgents: [],
            helperSurfaces: [],
            backendLogLines: []
        )
    }
}

struct ZenithBootstrapResponse: Decodable {
    let generatedAt: String
    let attention: AttentionSnapshot
    let stationLauncher: StationLauncherSnapshot
    let runtime: RuntimeSnapshot
}

struct WindowRegistrationDescriptor {
    var windowID: String
    var route: String?
    var nativeLens: ZenithNativeLens?
    var title: String?
}

struct RecordingViewEventBody: Codable, Sendable {
    var source: String
    var runtimeMode: String
    var hostApp: String
    var windowId: String?
    var workspaceId: String?
    var surfaceKind: String
    var surfaceId: String?
    var nativeLens: String?
    var route: String?
    var viewId: String?
    var viewLabel: String?
    var pathname: String?
    var search: String?
    var hash: String?
    var isKeyWindow: Bool
    var isOperatorActive: Bool
    var clientAtIso: String?
}

struct RecordingViewEventResponse: Codable {
    var operatorActive: Bool?
    var persistedTo: String?
}

final class WeakWindowBox {
    weak var window: NSWindow?

    init(window: NSWindow?) {
        self.window = window
    }
}
