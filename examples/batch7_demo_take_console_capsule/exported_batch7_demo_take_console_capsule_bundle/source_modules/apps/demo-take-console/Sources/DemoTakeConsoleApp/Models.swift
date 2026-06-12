import CoreGraphics
import Foundation

enum RecordingState: String, Codable {
    case idle
    case setupNeeded = "setup_needed"
    case ready
    case countingDown = "counting_down"
    case recording
    case paused
    case stopping
    case reviewReady = "review_ready"
    case postprocessing
    case packageReady = "package_ready"
    case packageFailed = "package_failed"

    var label: String {
        switch self {
        case .idle: "Idle"
        case .setupNeeded: "Setup needed"
        case .ready: "Ready to record"
        case .countingDown: "Starting"
        case .recording: "Recording"
        case .paused: "Paused"
        case .stopping: "Stopping"
        case .reviewReady: "Review ready"
        case .postprocessing: "Postprocessing"
        case .packageReady: "Package ready"
        case .packageFailed: "Package failed"
        }
    }
}

enum DeviceKind: String, Codable {
    case video
    case audio
}

struct CaptureDevice: Identifiable, Hashable, Codable {
    let id: String
    let index: Int
    let name: String
    let kind: DeviceKind
    let uniqueID: String?

    init(id: String, index: Int, name: String, kind: DeviceKind, uniqueID: String? = nil) {
        self.id = id
        self.index = index
        self.name = name
        self.kind = kind
        self.uniqueID = uniqueID
    }

    enum CodingKeys: String, CodingKey {
        case id
        case index
        case name
        case kind
        case uniqueID = "unique_id"
    }

    var identityDescription: String {
        if let uniqueID, !uniqueID.isEmpty {
            return "\(name) [\(uniqueID)]"
        }
        return name
    }

    var isScreen: Bool {
        name.localizedCaseInsensitiveContains("screen")
    }

    var isLikelyWebcam: Bool {
        kind == .video && !isScreen
    }

    var screenOrdinal: Int {
        guard isScreen else { return index }
        let marker = "Capture screen "
        guard let range = name.range(of: marker, options: .caseInsensitive),
              let ordinal = Int(name[range.upperBound...].trimmingCharacters(in: .whitespaces))
        else {
            return index
        }
        return ordinal
    }
}

struct DeviceInventory: Codable {
    var videoDevices: [CaptureDevice] = []
    var audioDevices: [CaptureDevice] = []

    static let empty = DeviceInventory()
}

struct PermissionSnapshot {
    var screenCapture: CapabilityStatus = .unknown
    var microphone: CapabilityStatus = .unknown
    var camera: CapabilityStatus = .unknown
    var disk: CapabilityStatus = .unknown
    var ffmpeg: CapabilityStatus = .unknown

    var blockers: [String] {
        var rows: [String] = []
        if screenCapture == .missing { rows.append("Screen Recording") }
        if microphone == .missing { rows.append("Microphone") }
        if camera == .missing { rows.append("Camera") }
        if disk == .low { rows.append("Disk Space") }
        if ffmpeg == .missing { rows.append("FFmpeg") }
        return rows
    }
}

enum CapabilityStatus: Equatable {
    case ready
    case missing
    case low
    case unknown
    case notRequired

    var label: String {
        switch self {
        case .ready: "Ready"
        case .missing: "Needs permission"
        case .low: "Low"
        case .unknown: "Needs test"
        case .notRequired: "Off"
        }
    }
}

struct DisplayMetadata: Equatable {
    let index: Int
    let name: String
    let resolution: String
    let origin: String
    let mappingConfidence: String
    let displayID: UInt32?
    let bounds: DisplayBounds?
    let scaleFactor: Double

    var summary: String {
        "\(name) \(resolution)"
    }

    var detail: String {
        "Screen ordinal \(index) · \(origin) · \(mappingConfidence)"
    }
}

struct DisplayBounds: Equatable {
    let x: Double
    let y: Double
    let width: Double
    let height: Double

    var dictionary: [String: Double] {
        [
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        ]
    }

    var cgRect: CGRect {
        CGRect(x: x, y: y, width: width, height: height)
    }
}

struct TrackRecord: Codable, Identifiable {
    let id: String
    let role: String
    let deviceName: String?
    let deviceIndex: Int?
    let deviceUniqueID: String?
    let relativePath: String

    enum CodingKeys: String, CodingKey {
        case id
        case role
        case deviceName = "device_name"
        case deviceIndex = "device_index"
        case deviceUniqueID = "device_unique_id"
        case relativePath = "relative_path"
    }
}

struct ActiveTake {
    let takeID: String
    let rootURL: URL
    let tracksURL: URL
    let framesURL: URL
    let transcriptURL: URL
    let renderURL: URL
    let reviewURL: URL
    var tracks: [TrackRecord]
}

enum MarkerSource: String, Codable {
    case hotkey
    case voice
    case button
    case api

    var label: String {
        switch self {
        case .hotkey: "Hotkey"
        case .voice: "Voice"
        case .button: "Button"
        case .api: "API"
        }
    }
}

struct Marker: Codable, Identifiable, Hashable {
    let id: String
    let source: MarkerSource
    let label: String?
    let wallTSeconds: Double
    let videoTSeconds: Double
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case source
        case label
        case wallTSeconds = "wall_t_seconds"
        case videoTSeconds = "video_t_seconds"
        case createdAt = "created_at"
    }
}

struct RunMapScheduleState: Codable {
    let status: String
    let currentStepID: String?
    let currentTitle: String?
    let currentRoute: String?
    let stepIndex: Int?
    let totalSteps: Int
    let remainingSteps: Int?
    let nextStepID: String?
    let nextTitle: String?
    let currentFlashSay: String
    let currentShortSay: String
    let longAnchors: [String]
    let operatorCue: String
    let publicClaimBoundary: String
    let recordingTreatment: String?
    let controls: [String]

    enum CodingKeys: String, CodingKey {
        case status
        case currentStepID = "current_step_id"
        case currentTitle = "current_title"
        case currentRoute = "current_route"
        case stepIndex = "step_index"
        case totalSteps = "total_steps"
        case remainingSteps = "remaining_steps"
        case nextStepID = "next_step_id"
        case nextTitle = "next_title"
        case currentFlashSay = "current_flash_say"
        case currentShortSay = "current_short_say"
        case longAnchors = "long_anchors"
        case operatorCue = "operator_cue"
        case publicClaimBoundary = "public_claim_boundary"
        case recordingTreatment = "recording_treatment"
        case controls
    }

    var progressLabel: String {
        guard let stepIndex else { return "Run map waiting" }
        return "Step \(stepIndex)/\(totalSteps)"
    }
}
