import CoreGraphics
import Foundation
import Testing
@testable import ZenithApp

@Test
func windowFrameRecordRoundTripsCGRect() {
    let rect = CGRect(x: 12, y: 34, width: 560, height: 420)
    let record = WindowFrameRecord(rect: rect)
    #expect(record.cgRect.integral == rect.integral)
}

@Test
func nativeLensMapsToExpectedScene() {
    #expect(ZenithNativeLens.rawSeedCapture.sceneID == .rawSeedCapture)
    #expect(ZenithNativeLens.gateQueue.sceneID == .gateQueue)
    #expect(ZenithNativeLens.runtimePanel.sceneID == .runtimePanel)
}

@Test
func quickLensRouteCatalogExposesPrimaryNativeAndWebLenses() {
    #expect(ZenithQuickLens.station.route == "/station")
    #expect(ZenithQuickLens.metaMissions.route == "/meta-missions")
    #expect(ZenithQuickLens.rawSeedCapture.isNative)
    #expect(!ZenithQuickLens.stationDoctrine.isNative)
}

@Test
func windowIdentityCanonicalizesStationNativeAndWebRoutes() {
    #expect(ZenithWindowIdentity.normalizedRoute("/") == "/station")
    #expect(ZenithWindowIdentity.normalizedRoute("meta-missions") == "/meta-missions")
    #expect(ZenithWindowIdentity.windowID(for: "/station") == ZenithSceneID.cockpit.rawValue)
    #expect(ZenithWindowIdentity.windowID(for: ZenithNativeLens.gateQueue.rawValue) == ZenithSceneID.gateQueue.rawValue)
    #expect(ZenithWindowIdentity.windowID(for: "meta-missions") == "web:/meta-missions")
}

@Test
func disconnectedRuntimeSnapshotCarriesRepoLocalStartCommand() {
    let snapshot = RuntimeSnapshot.disconnected(repoRoot: "/tmp/demo")
    #expect(snapshot.backend.state == .stopped)
    #expect(snapshot.startCommand == #"cd "/tmp/demo" && ./repo-python run_server.py"#)
}

@Test
func webLensLoadLatchSuppressesBootOverlayForLoadedWindow() {
    #expect(!ZenithBackendSurfaceAvailability.webSurfaceAvailable(
        backendReady: false,
        backendHasConnected: false,
        loadedWebViewWindowIDs: [],
        windowID: "web:/root-navigator"
    ))
    #expect(ZenithBackendSurfaceAvailability.webSurfaceAvailable(
        backendReady: false,
        backendHasConnected: false,
        loadedWebViewWindowIDs: ["web:/root-navigator"],
        windowID: "web:/root-navigator"
    ))
    #expect(!ZenithBackendSurfaceAvailability.webSurfaceAvailable(
        backendReady: false,
        backendHasConnected: false,
        loadedWebViewWindowIDs: ["web:/root-navigator"],
        windowID: "web:/station"
    ))
}

@Test
func repoRootResolverPrefersValidStoredRoot() throws {
    let temp = URL(fileURLWithPath: NSTemporaryDirectory(), isDirectory: true)
        .appendingPathComponent(UUID().uuidString, isDirectory: true)
    let root = temp.appendingPathComponent("stored", isDirectory: true)
    try makeRepoRoot(root)
    defer { try? FileManager.default.removeItem(at: temp) }

    let resolved = ZenithRepoRootResolver.resolve(
        stored: root.path,
        home: temp.path,
        cwd: "/definitely/not/a/repo"
    )

    #expect(resolved == root.path)
}

@Test
func repoRootResolverFallsBackFromStaleDesktopRootToSrcCheckout() throws {
    let temp = URL(fileURLWithPath: NSTemporaryDirectory(), isDirectory: true)
        .appendingPathComponent(UUID().uuidString, isDirectory: true)
    let srcRoot = temp
        .appendingPathComponent("src", isDirectory: true)
        .appendingPathComponent("ai_workflow", isDirectory: true)
    try makeRepoRoot(srcRoot)
    defer { try? FileManager.default.removeItem(at: temp) }

    let resolved = ZenithRepoRootResolver.resolve(
        stored: temp.appendingPathComponent("Desktop/ai_workflow").path,
        home: temp.path,
        cwd: "/definitely/not/a/repo"
    )

    #expect(resolved == srcRoot.path)
}

@Test
func repoRootResolverPrefersSrcCheckoutOverValidStoredDownloadsRoot() throws {
    let temp = URL(fileURLWithPath: NSTemporaryDirectory(), isDirectory: true)
        .appendingPathComponent(UUID().uuidString, isDirectory: true)
    let downloadsRoot = temp
        .appendingPathComponent("Downloads", isDirectory: true)
        .appendingPathComponent("ai_workflow", isDirectory: true)
    let srcRoot = temp
        .appendingPathComponent("src", isDirectory: true)
        .appendingPathComponent("ai_workflow", isDirectory: true)
    try makeRepoRoot(downloadsRoot)
    try makeRepoRoot(srcRoot)
    defer { try? FileManager.default.removeItem(at: temp) }

    let resolved = ZenithRepoRootResolver.resolve(
        stored: downloadsRoot.path,
        home: temp.path,
        cwd: "/definitely/not/a/repo"
    )

    #expect(ZenithRepoRootResolver.isProtectedUserFolderPath(downloadsRoot.path, home: temp.path))
    #expect(!ZenithRepoRootResolver.isProtectedUserFolderPath(srcRoot.path, home: temp.path))
    #expect(resolved == srcRoot.path)
}

@Test
func repoRootResolverKeepsProtectedStoredRootWhenNoSafeCheckoutExists() throws {
    let temp = URL(fileURLWithPath: NSTemporaryDirectory(), isDirectory: true)
        .appendingPathComponent(UUID().uuidString, isDirectory: true)
    let downloadsRoot = temp
        .appendingPathComponent("Downloads", isDirectory: true)
        .appendingPathComponent("ai_workflow", isDirectory: true)
    try makeRepoRoot(downloadsRoot)
    defer { try? FileManager.default.removeItem(at: temp) }

    let resolved = ZenithRepoRootResolver.resolve(
        stored: downloadsRoot.path,
        home: temp.path,
        cwd: "/definitely/not/a/repo"
    )

    #expect(resolved == downloadsRoot.path)
}

private func makeRepoRoot(_ root: URL) throws {
    let fileManager = FileManager.default
    try fileManager.createDirectory(
        at: root.appendingPathComponent("system/server/ui", isDirectory: true),
        withIntermediateDirectories: true
    )
    try "server".write(to: root.appendingPathComponent("run_server.py"), atomically: true, encoding: .utf8)
    try "python".write(to: root.appendingPathComponent("repo-python"), atomically: true, encoding: .utf8)
    try "{}".write(
        to: root.appendingPathComponent("system/server/ui/package.json"),
        atomically: true,
        encoding: .utf8
    )
}

@Test
func managedBackendRecordDecodesSnakeCasePayload() throws {
    let payload = """
    {"owner_id":"abc","repo_root":"/tmp/demo","backend_pid":4242,"started_at":"2026-04-17T03:00:00Z"}
    """
    let record = try JSONDecoder().decode(ZenithManagedBackendRecord.self, from: Data(payload.utf8))
    #expect(record.ownerID == "abc")
    #expect(record.repoRoot == "/tmp/demo")
    #expect(record.backendPID == 4242)
    #expect(record.startedAt == "2026-04-17T03:00:00Z")
}

@Test
func managedBackendShutdownPolicyStopsCurrentOwnerWithoutCommandInspection() throws {
    let record = ZenithManagedBackendRecord(
        ownerID: "current",
        repoRoot: "/tmp/demo",
        backendPID: 4242,
        startedAt: "2026-04-17T03:00:00Z"
    )

    #expect(ZenithManagedBackendShutdownPolicy.shouldTerminate(
        record: record,
        currentOwnerToken: "current",
        currentRepoRoot: "/tmp/demo",
        commandLine: nil
    ))
}

@Test
func managedBackendShutdownPolicyAdoptsSameRepoPreviousOwnerBackend() throws {
    let record = ZenithManagedBackendRecord(
        ownerID: "previous",
        repoRoot: "/tmp/demo/../demo",
        backendPID: 4242,
        startedAt: "2026-04-17T03:00:00Z"
    )

    #expect(ZenithManagedBackendShutdownPolicy.shouldTerminate(
        record: record,
        currentOwnerToken: "current",
        currentRepoRoot: "/tmp/demo",
        commandLine: "/opt/homebrew/bin/python /tmp/demo/run_server.py"
    ))
}

@Test
func managedBackendShutdownPolicyDoesNotKillExternalOrUnrecognizedProcesses() throws {
    let sameRepoRecord = ZenithManagedBackendRecord(
        ownerID: "previous",
        repoRoot: "/tmp/demo",
        backendPID: 4242,
        startedAt: "2026-04-17T03:00:00Z"
    )
    let otherRepoRecord = ZenithManagedBackendRecord(
        ownerID: "previous",
        repoRoot: "/tmp/other",
        backendPID: 4242,
        startedAt: "2026-04-17T03:00:00Z"
    )

    #expect(!ZenithManagedBackendShutdownPolicy.shouldTerminate(
        record: sameRepoRecord,
        currentOwnerToken: "current",
        currentRepoRoot: "/tmp/demo",
        commandLine: "/usr/bin/python unrelated.py"
    ))
    #expect(!ZenithManagedBackendShutdownPolicy.shouldTerminate(
        record: otherRepoRecord,
        currentOwnerToken: "current",
        currentRepoRoot: "/tmp/demo",
        commandLine: "/opt/homebrew/bin/python /tmp/other/run_server.py"
    ))
}

@Test
func zenithHealthResponseDecodesCheapProbePayload() throws {
    let payload = """
    {"ok":true,"generated_at":"2026-05-15T13:00:00+00:00"}
    """
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    let health = try decoder.decode(ZenithHealthResponse.self, from: Data(payload.utf8))
    #expect(health.ok)
    #expect(health.generatedAt == "2026-05-15T13:00:00+00:00")
}

@Test
func operationParameterCoercesNumericDefaultToString() throws {
    let payload = """
    {
      "operation_id": "raw_seed_atomize",
      "label": "Atomize",
      "kicker": "raw-seed",
      "description_short": "Atomize raw seed.",
      "parameters_schema": {
        "cohort_size": {
          "type": "integer",
          "required": false,
          "default": 12
        },
        "wave_width": {
          "type": "number",
          "required": false,
          "default": 3.5
        }
      }
    }
    """
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    let operation = try decoder.decode(StationLauncherSnapshot.StationOperation.self, from: Data(payload.utf8))
    #expect(operation.parametersSchema?["cohort_size"]?.defaultValue == "12")
    #expect(operation.parametersSchema?["wave_width"]?.defaultValue == "3.5")
}

@Test
func recordingViewEventUsesSnakeCaseAPIKeys() throws {
    let body = RecordingViewEventBody(
        source: "zenith_host",
        runtimeMode: "embedded",
        hostApp: "zenith_macos",
        windowId: "web:/station/root-navigator",
        workspaceId: "workspace-a",
        surfaceKind: "web",
        surfaceId: "root-navigator",
        nativeLens: nil,
        route: "/station/root-navigator",
        viewId: "root-navigator",
        viewLabel: "Root Navigator",
        pathname: "/station/root-navigator",
        search: "",
        hash: "",
        isKeyWindow: true,
        isOperatorActive: true,
        clientAtIso: "2026-05-20T16:00:00Z"
    )

    let encoder = JSONEncoder()
    encoder.keyEncodingStrategy = .convertToSnakeCase
    let data = try encoder.encode(body)
    let object = try #require(JSONSerialization.jsonObject(with: data) as? [String: Any])

    #expect(object["runtime_mode"] as? String == "embedded")
    #expect(object["host_app"] as? String == "zenith_macos")
    #expect(object["window_id"] as? String == "web:/station/root-navigator")
    #expect(object["surface_kind"] as? String == "web")
    #expect(object["is_key_window"] as? Bool == true)
    #expect(object["is_operator_active"] as? Bool == true)
    #expect(object["client_at_iso"] as? String == "2026-05-20T16:00:00Z")
    #expect(object["runtimeMode"] == nil)
    #expect(object["isKeyWindow"] == nil)

    let responseData = Data("""
    {"operator_active":true,"persisted_to":"state/dissemination/demo_takes/take/view_telemetry.jsonl"}
    """.utf8)
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    let response = try decoder.decode(RecordingViewEventResponse.self, from: responseData)
    #expect(response.operatorActive == true)
    #expect(response.persistedTo == "state/dissemination/demo_takes/take/view_telemetry.jsonl")
}
