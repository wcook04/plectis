import AppKit
import Darwin
import SwiftUI
import WebKit

actor WorkspaceStore {
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    init() {
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.dateEncodingStrategy = .iso8601
        decoder.dateDecodingStrategy = .iso8601
    }

    func loadAll() throws -> [ZenithWorkspace] {
        let root = try workspaceRoot()
        guard FileManager.default.fileExists(atPath: root.path) else {
            return []
        }
        let files = try FileManager.default.contentsOfDirectory(at: root, includingPropertiesForKeys: nil)
        let items = try files
            .filter { $0.pathExtension == "json" }
            .map { try decoder.decode(ZenithWorkspace.self, from: Data(contentsOf: $0)) }
            .sorted { $0.savedAt > $1.savedAt }
        return items
    }

    func save(_ workspace: ZenithWorkspace) throws {
        let root = try workspaceRoot()
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let path = root.appendingPathComponent("\(workspace.id).json")
        let data = try encoder.encode(workspace)
        try data.write(to: path, options: .atomic)
    }

    private func workspaceRoot() throws -> URL {
        let root = try FileManager.default.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )
        return root.appendingPathComponent("Zenith/workspaces", isDirectory: true)
    }
}

private final class WeakWebViewBox {
    weak var webView: WKWebView?
    weak var window: NSWindow?

    init(webView: WKWebView?, window: NSWindow?) {
        self.webView = webView
        self.window = window
    }
}

struct ZenithBackendSurfaceAvailability: Equatable {
    static func backendSurfaceAvailable(backendReady: Bool, backendHasConnected: Bool) -> Bool {
        backendReady || backendHasConnected
    }

    static func webSurfaceAvailable(
        backendReady: Bool,
        backendHasConnected: Bool,
        loadedWebViewWindowIDs: Set<String>,
        windowID: String?
    ) -> Bool {
        if backendSurfaceAvailable(backendReady: backendReady, backendHasConnected: backendHasConnected) {
            return true
        }
        guard let windowID else { return false }
        return loadedWebViewWindowIDs.contains(windowID)
    }
}

struct ZenithManagedBackendShutdownPolicy: Equatable {
    static func isSameRepoRoot(_ lhs: String, _ rhs: String) -> Bool {
        URL(fileURLWithPath: lhs, isDirectory: true).standardizedFileURL.path
            == URL(fileURLWithPath: rhs, isDirectory: true).standardizedFileURL.path
    }

    static func commandLooksLikeZenithBackend(_ commandLine: String?) -> Bool {
        guard let commandLine else { return false }
        let lowered = commandLine.lowercased()
        return lowered.contains("run_server.py")
            || (lowered.contains("uvicorn") && lowered.contains("system.server"))
    }

    static func shouldTerminate(
        record: ZenithManagedBackendRecord?,
        currentOwnerToken: String,
        currentRepoRoot: String,
        commandLine: String?
    ) -> Bool {
        guard let record else { return false }
        if record.ownerID == currentOwnerToken {
            return true
        }
        guard isSameRepoRoot(record.repoRoot, currentRepoRoot) else {
            return false
        }
        return commandLooksLikeZenithBackend(commandLine)
    }
}

@MainActor
final class ZenithAppModel: ObservableObject {
    enum BackendBootStage {
        case waiting
        case launching
        case starting
        case ready
    }

    /// Structured boot/runtime evidence the BootstrapView renders instead of a
    /// mood-lit "Warming local runtime…" string. Honours pri_104 (fail-loud) and
    /// pri_058 (observability surfacing freshness): the boot screen names the
    /// PID, log path, last probe attempt age, and recovery reason rather than
    /// hiding them behind a spinner.
    struct BootDiagnostic: Equatable {
        var stage: BackendBootStage
        var statusText: String
        var pid: Int32?
        var pidIsRunning: Bool
        var hasManagedRecord: Bool
        var logPath: String
        var lastProbeAttemptAt: Date?
        var lastProbeFailureMessage: String?
        var lastBackendLaunchAttemptAt: Date?
        var lastErrorMessage: String?
        /// One-sentence reason for the current stuck state. Empty when ready
        /// or genuinely uninformative (no PID, never tried, etc).
        var recoveryReason: String
        var startCommand: String
    }

    @Published private(set) var stationLauncher: StationLauncherSnapshot?
    @Published private(set) var attentionSnapshot: AttentionSnapshot?
    @Published private(set) var workspaces: [ZenithWorkspace] = []
    @Published private(set) var backendReady: Bool = false
    @Published private(set) var backendHasConnected: Bool = false
    @Published private(set) var loadedWebViewWindowIDs: Set<String> = []
    @Published private(set) var backendStatusText: String = "Preparing local runtime…"
    @Published private(set) var lastProbeAttemptAt: Date?
    @Published private(set) var lastProbeFailureMessage: String?
    @Published var lastActionMessage: String?
    @Published var lastErrorMessage: String?

    let runtimeSupervisor: RuntimeSupervisor

    private let apiClient = ZenithAPIClient()
    private let workspaceStore = WorkspaceStore()
    private let backendOwnerToken = UUID().uuidString
    private var pollingTask: Task<Void, Never>?
    private var backendBootstrapTask: Task<Void, Never>?
    private var lastNotificationToken: String?
    private var trackedWindows: [String: (descriptor: WindowRegistrationDescriptor, window: WeakWindowBox)] = [:]
    private var trackedWebViews: [String: WeakWebViewBox] = [:]
    private var latestWebSurfaceByWindowID: [String: RecordingViewEventBody] = [:]
    nonisolated(unsafe) private var keyWindowObserver: NSObjectProtocol?
    private var pendingFrames: [String: WindowFrameRecord] = [:]
    private var openNativeWindow: ((ZenithSceneID) -> Void)?
    private var openWebLensWindow: ((String) -> Void)?
    private var backendAutoLaunchAttempted = false
    private var backendLaunchInFlight = false
    private var lastBackendLaunchAttemptAt: Date?

    var repoRoot: String

    init(repoRoot: String) {
        self.repoRoot = repoRoot
        self.runtimeSupervisor = RuntimeSupervisor(initialSnapshot: .disconnected(repoRoot: repoRoot))
        installRecordingKeyWindowObserver()
        Task { await reloadWorkspaces() }
        bootstrapBackend()
        startPolling()
    }

    /// Zenith starts one app-owned bootstrap process, records the child pid,
    /// and reconnects over HTTP. The bootstrap stays out of Terminal so a
    /// normal app launch does not create a second visible window.
    private func bootstrapBackend() {
        backendBootstrapTask?.cancel()
        backendBootstrapTask = Task { [weak self] in
            guard let self else { return }
            var attempt = 0
            while !Task.isCancelled {
                self.lastProbeAttemptAt = .now
                if await self.apiClient.ping(timeout: 1.5) {
                    self.lastProbeFailureMessage = nil
                    if let runtime = try? await self.apiClient.runtimeSnapshot(timeout: 1.5) {
                        self.runtimeSupervisor.replace(with: runtime)
                    }
                    await self.markBackendReady()
                    Task { [weak self] in
                        await self?.refreshAll()
                    }
                    return
                }
                self.clearStaleManagedBackendStateIfNeeded()
                self.lastProbeFailureMessage = self.synthesizedProbeFailureMessage()
                if !self.backendAutoLaunchAttempted {
                    self.backendAutoLaunchAttempted = true
                    self.startBackendBootstrap(auto: true)
                }
                if self.backendReady { self.backendReady = false }
                self.runtimeSupervisor.markDisconnected(repoRoot: self.repoRoot)
                self.reconcileBackendLaunchState()
                attempt += 1
                self.backendStatusText = self.backendWaitingStatusText(attempt: attempt)
                try? await Task.sleep(for: .milliseconds(attempt < 18 ? 650 : 1800))
            }
        }
    }

    func startBackendBootstrap() {
        startBackendBootstrap(auto: false)
    }

    var backendBootStage: BackendBootStage {
        if backendReady {
            return .ready
        }
        if managedBackendIsRunning() {
            return .starting
        }
        if backendLaunchInFlight {
            return .launching
        }
        return .waiting
    }

    var backendSurfaceAvailable: Bool {
        ZenithBackendSurfaceAvailability.backendSurfaceAvailable(
            backendReady: backendReady,
            backendHasConnected: backendHasConnected
        )
    }

    var shouldShowBackendBootScreen: Bool {
        shouldShowBackendBootScreen(windowID: nil)
    }

    func webSurfaceAvailable(windowID: String?) -> Bool {
        ZenithBackendSurfaceAvailability.webSurfaceAvailable(
            backendReady: backendReady,
            backendHasConnected: backendHasConnected,
            loadedWebViewWindowIDs: loadedWebViewWindowIDs,
            windowID: windowID
        )
    }

    func shouldShowBackendBootScreen(windowID: String?) -> Bool {
        !webSurfaceAvailable(windowID: windowID)
    }

    /// Structured snapshot of bootstrap evidence for the boot screen.
    /// Honours pri_104 / pri_058: the surface should name PID, log path,
    /// probe age, and recovery reason instead of hiding behind a spinner.
    var bootDiagnostic: BootDiagnostic {
        let pid = managedBackendPID()
        let pidRunning = pid.map { processIsRunning(pid: $0) } ?? false
        return BootDiagnostic(
            stage: backendBootStage,
            statusText: backendStatusText,
            pid: pid,
            pidIsRunning: pidRunning,
            hasManagedRecord: managedBackendRecord() != nil,
            logPath: backendLaunchLogPath(),
            lastProbeAttemptAt: lastProbeAttemptAt,
            lastProbeFailureMessage: lastProbeFailureMessage,
            lastBackendLaunchAttemptAt: lastBackendLaunchAttemptAt,
            lastErrorMessage: lastErrorMessage,
            recoveryReason: synthesizedRecoveryReason(pid: pid, pidRunning: pidRunning),
            startCommand: backendStartCommand()
        )
    }

    /// Best-effort one-line cause derived from on-disk state. Prefer evidence
    /// that points the operator at the next correct action rather than at the
    /// spinner.
    private func synthesizedRecoveryReason(pid: Int32?, pidRunning: Bool) -> String {
        if backendReady { return "" }
        if let pid, pidRunning {
            return "Backend pid \(pid) recorded but /api/zenith/runtime is not responding — server may still be importing or have crashed silently."
        }
        if pid != nil, !pidRunning {
            return "Backend pid file is stale — recorded process is gone. Restart the bootstrap to relaunch."
        }
        if backendLaunchInFlight {
            return "Bootstrap process is launching the backend. Watch the log for import or port-bind errors."
        }
        if backendAutoLaunchAttempted {
            return "Auto-launch attempted but backend never came up. Check the log path or run the start command in Terminal."
        }
        return "Backend has not been launched yet."
    }

    private func synthesizedProbeFailureMessage() -> String {
        let pid = managedBackendPID()
        if let pid, processIsRunning(pid: pid) {
            return "HTTP probe to 127.0.0.1:8000 failed (pid \(pid) alive)."
        }
        if pid != nil {
            return "HTTP probe failed and managed backend pid is gone."
        }
        return "HTTP probe failed — no managed backend process recorded."
    }

    /// Copy the absolute path of the backend launch log so the operator can
    /// open it in Console / `tail -f` without re-deriving where it lives.
    func copyBackendLogPath() {
        copyToPasteboard(backendLaunchLogPath(), success: "Backend log path copied.")
    }

    /// Reveal the backend log file in Finder if it exists. Falls back to
    /// surfacing the path as the last action message when the file isn't
    /// there yet (e.g. first boot before any write).
    func revealBackendLogInFinder() {
        let path = backendLaunchLogPath()
        let url = URL(fileURLWithPath: path)
        if FileManager.default.fileExists(atPath: path) {
            NSWorkspace.shared.activateFileViewerSelecting([url])
            lastActionMessage = "Revealed backend log in Finder."
        } else {
            lastErrorMessage = "Backend log not yet at \(path)."
        }
    }

    /// Return the last `limit` non-empty lines of the backend log. Bounded
    /// read (last 64 KB) — production log files routinely run to hundreds of
    /// thousands of lines and reading them whole on the main actor would
    /// hitch the boot screen. Used by the boot screen to show fail-loud
    /// evidence when stuck.
    func recentBackendLogTail(limit: Int = 8) -> [String] {
        guard limit > 0 else { return [] }
        let path = backendLaunchLogPath()
        guard let handle = FileHandle(forReadingAtPath: path) else { return [] }
        defer { try? handle.close() }
        let tailWindow: UInt64 = 64 * 1024
        let size = (try? handle.seekToEnd()) ?? 0
        let offset = size > tailWindow ? size - tailWindow : 0
        try? handle.seek(toOffset: offset)
        guard let data = try? handle.readToEnd(),
              let text = String(data: data, encoding: .utf8) else { return [] }
        let lines = text.split(whereSeparator: { $0 == "\n" || $0 == "\r" })
            .map(String.init)
            .filter { !$0.trimmingCharacters(in: .whitespaces).isEmpty }
        return Array(lines.suffix(limit))
    }

    private func startBackendBootstrap(auto: Bool) {
        clearStaleManagedBackendStateIfNeeded()
        if let pid = bootstrapShellPID(), !processIsRunning(pid: pid) {
            try? FileManager.default.removeItem(at: backendShellPIDFileURL())
        }
        if backendReady {
            backendStatusText = "Connected to 127.0.0.1:8000"
            if !auto {
                lastActionMessage = "Backend is already running."
            }
            return
        }
        if managedBackendIsRunning() {
            backendLaunchInFlight = true
            backendStatusText = "Warming local runtime…"
            if !auto {
                lastActionMessage = "Local runtime is already starting."
            }
            return
        }
        if let lastBackendLaunchAttemptAt,
           Date().timeIntervalSince(lastBackendLaunchAttemptAt) < 8 {
            backendLaunchInFlight = true
            backendStatusText = "Starting local runtime…"
            if !auto {
                lastActionMessage = "Runtime bootstrap is already starting."
            }
            return
        }
        do {
            let scriptURL = try writeBackendLaunchCommandFile()
            try launchBackendBootstrapScript(scriptURL)
            backendLaunchInFlight = true
            lastBackendLaunchAttemptAt = .now
            backendStatusText = "Starting local runtime…"
            if !auto {
                lastActionMessage = "Restarting the local runtime bootstrap…"
            }
        } catch {
            backendLaunchInFlight = false
            lastErrorMessage = "Couldn't start backend bootstrap: \(error.localizedDescription)"
        }
    }

    private func launchBackendBootstrapScript(_ scriptURL: URL) throws {
        let logURL = URL(fileURLWithPath: backendLaunchLogPath())
        try FileManager.default.createDirectory(
            at: logURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        if !FileManager.default.fileExists(atPath: logURL.path) {
            _ = FileManager.default.createFile(atPath: logURL.path, contents: nil)
        }
        let logHandle = try FileHandle(forWritingTo: logURL)
        try logHandle.seekToEnd()
        defer { try? logHandle.close() }

        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/bin/bash")
        process.arguments = [scriptURL.path]
        process.standardInput = FileHandle.nullDevice
        process.standardOutput = logHandle
        process.standardError = logHandle
        try process.run()
    }

    func backendStartCommand() -> String {
        let command = runtimeSupervisor.snapshot.startCommand
        return command.isEmpty ? #"cd "\#(repoRoot)" && ./repo-python run_server.py"# : command
    }

    func copyBackendStartCommand() {
        copyToPasteboard(backendStartCommand(), success: "Backend command copied.")
    }

    func copyRuntimeLogPath() {
        guard let path = runtimeSupervisor.snapshot.serverLogPath, !path.isEmpty else {
            lastErrorMessage = "No backend log path is available yet."
            return
        }
        copyToPasteboard(path, success: "Backend log path copied.")
    }

    private func copyToPasteboard(_ text: String, success: String) {
        let pb = NSPasteboard.general
        pb.clearContents()
        pb.setString(text, forType: .string)
        lastActionMessage = success
    }

    func copyTextFromHost(_ text: String) {
        guard !text.isEmpty else { return }
        copyToPasteboard(text, success: "Copied to clipboard.")
    }

    private func writeBackendLaunchCommandFile() throws -> URL {
        let dir = try zenithStateDirectory()
        let scriptURL = backendLaunchScriptURL(in: dir)
        let ownerPath = backendOwnerRecordURL(in: dir).path
        let pidPath = backendPIDFileURL(in: dir).path
        let shellPIDPath = backendShellPIDFileURL(in: dir).path
        let logPath = backendLaunchLogPath()
        let body = """
        #!/bin/bash
        set -euo pipefail
        STATE_DIR="\(dir.path)"
        OWNER_FILE="\(ownerPath)"
        PID_FILE="\(pidPath)"
        SHELL_PID_FILE="\(shellPIDPath)"
        LOG_FILE="\(logPath)"
        OWNER_ID="\(backendOwnerToken)"
        REPO_ROOT="\(repoRoot)"

        printf '%s\n' "$$" > "$SHELL_PID_FILE"

        fail_startup() {
          local message="${1:-Zenith backend failed to start.}"
          echo "$message"
          if [[ -f "$PID_FILE" ]]; then
            /bin/rm -f "$PID_FILE"
          fi
          if [[ -f "$OWNER_FILE" ]] && /usr/bin/grep -q "$OWNER_ID" "$OWNER_FILE" 2>/dev/null; then
            /bin/rm -f "$OWNER_FILE"
          fi
          echo
          echo "Recent backend log:"
          /usr/bin/tail -n 40 "$LOG_FILE" 2>/dev/null || true
          exit 1
        }

        if /usr/bin/curl -fsS --max-time 1 http://127.0.0.1:8000/api/zenith/runtime >/dev/null 2>&1; then
          echo "Zenith backend already reachable on 127.0.0.1:8000."
          exit 0
        fi

        if [[ -f "$PID_FILE" ]]; then
          EXISTING_PID="$(/bin/cat "$PID_FILE" 2>/dev/null || true)"
          if [[ -n "$EXISTING_PID" ]] && /bin/kill -0 "$EXISTING_PID" 2>/dev/null; then
            echo "Zenith-owned backend already running (pid $EXISTING_PID)."
            exit 0
          fi
          /bin/rm -f "$PID_FILE"
        fi

        cd "\(repoRoot)" || exit 1
        /bin/mkdir -p "$(/usr/bin/dirname "$LOG_FILE")"
        echo "Starting Zenith backend from $(pwd)"
        echo "Logging to $LOG_FILE"
        printf '{"owner_id":"%s","repo_root":"%s","backend_pid":null,"started_at":"%s"}\n' \
          "$OWNER_ID" "$REPO_ROOT" "$(/bin/date -u +%Y-%m-%dT%H:%M:%SZ)" > "$OWNER_FILE"
        /usr/bin/nohup ./repo-python run_server.py >> "$LOG_FILE" 2>&1 &
        SERVER_PID=$!
        disown "$SERVER_PID" 2>/dev/null || true
        printf '%s\n' "$SERVER_PID" > "$PID_FILE"
        printf '{"owner_id":"%s","repo_root":"%s","backend_pid":%s,"started_at":"%s"}\n' \
          "$OWNER_ID" "$REPO_ROOT" "$SERVER_PID" "$(/bin/date -u +%Y-%m-%dT%H:%M:%SZ)" > "$OWNER_FILE"
        for _ in $(/usr/bin/seq 1 24); do
          if /usr/bin/curl -fsS --max-time 1 http://127.0.0.1:8000/api/zenith/runtime >/dev/null 2>&1; then
            exit 0
          fi
          if ! /bin/kill -0 "$SERVER_PID" 2>/dev/null; then
            fail_startup "Zenith backend exited before becoming ready."
          fi
          /bin/sleep 0.25
        done
        echo "Zenith backend is still starting in the background."
        exit 0
        """
        try body.write(to: scriptURL, atomically: true, encoding: .utf8)
        try FileManager.default.setAttributes(
            [.posixPermissions: NSNumber(value: Int16(0o755))],
            ofItemAtPath: scriptURL.path
        )
        return scriptURL
    }

    private func markBackendReady() async {
        backendHasConnected = true
        if !backendReady {
            backendReady = true
            backendStatusText = "Connected to 127.0.0.1:8000"
        }
        backendLaunchInFlight = false
        terminateBootstrapShellIfNeeded()
    }

    deinit {
        pollingTask?.cancel()
        backendBootstrapTask?.cancel()
        if let keyWindowObserver {
            NotificationCenter.default.removeObserver(keyWindowObserver)
        }
    }

    func updateRepoRoot(_ repoRoot: String) {
        guard self.repoRoot != repoRoot else { return }
        self.repoRoot = repoRoot
        backendHasConnected = false
        loadedWebViewWindowIDs = []
        backendAutoLaunchAttempted = false
        backendLaunchInFlight = false
        lastBackendLaunchAttemptAt = nil
        runtimeSupervisor.markDisconnected(repoRoot: repoRoot)
        Task {
            await reloadWorkspaces()
            await refreshAll()
        }
    }

    func installOpeners(openWindow: OpenWindowAction) {
        openNativeWindow = { scene in
            openWindow(id: scene.rawValue)
            NSApp.activate(ignoringOtherApps: true)
        }
        openWebLensWindow = { route in
            openWindow(id: ZenithSceneID.webLens.rawValue, value: route)
            NSApp.activate(ignoringOtherApps: true)
        }
    }

    func refreshAll() async {
        lastProbeAttemptAt = .now
        if let runtime = try? await apiClient.runtimeSnapshot(timeout: 1.5) {
            lastProbeFailureMessage = nil
            await markBackendReady()
            runtimeSupervisor.replace(with: runtime)
            if let attention = try? await apiClient.attention(timeout: 2.5) {
                attentionSnapshot = attention
                reloadDockBadge()
                notifyOnAttentionChange()
            }
            if let launcher = try? await apiClient.stationLauncher(timeout: 3.0) {
                stationLauncher = launcher
            }
            return
        }
        backendReady = false
        clearStaleManagedBackendStateIfNeeded()
        reconcileBackendLaunchState()
        backendStatusText = backendWaitingStatusText(attempt: nil)
        lastProbeFailureMessage = synthesizedProbeFailureMessage()
        runtimeSupervisor.markDisconnected(repoRoot: repoRoot)
    }

    func openLens(_ route: String) {
        let normalized = ZenithWindowIdentity.normalizedRoute(route)
        let windowID = ZenithWindowIdentity.windowID(for: normalized)
        if focusExistingWindow(windowID: windowID) {
            return
        }

        switch windowID {
        case ZenithSceneID.cockpit.rawValue:
            openNativeWindow?(.cockpit)
        case ZenithSceneID.rawSeedCapture.rawValue:
            openNativeWindow?(.rawSeedCapture)
        case ZenithSceneID.gateQueue.rawValue:
            openNativeWindow?(.gateQueue)
        case ZenithSceneID.runtimePanel.rawValue:
            openNativeWindow?(.runtimePanel)
        default:
            openWebLensWindow?(normalized)
        }
    }

    func registerWindow(_ window: NSWindow, descriptor: WindowRegistrationDescriptor) {
        trackedWindows[descriptor.windowID] = (descriptor, WeakWindowBox(window: window))
        if let pending = pendingFrames.removeValue(forKey: descriptor.windowID) {
            apply(frame: pending, to: window)
        }
        if window === NSApp.keyWindow {
            emitRecordingSurfaceForWindowID(descriptor.windowID)
        }
    }

    func registerWebView(_ webView: WKWebView, windowID: String) {
        let window = trackedWindows[windowID]?.window.window
        trackedWebViews[windowID] = WeakWebViewBox(webView: webView, window: window)
    }

    func recordingViewChanged(_ payload: [String: Any], windowID: String?) {
        guard let windowID else { return }
        let event = makeWebRecordingEvent(payload: payload, windowID: windowID)
        latestWebSurfaceByWindowID[windowID] = event
        emitRecordingSurfaceForWindowID(windowID)
    }

    func markWebViewLoaded(windowID: String) {
        if !loadedWebViewWindowIDs.contains(windowID) {
            var next = loadedWebViewWindowIDs
            next.insert(windowID)
            loadedWebViewWindowIDs = next
        }
        backendHasConnected = true
    }

    /// Force every live webview to re-fetch the SPA, bypassing the local disk
    /// cache. Used by the top-bar refresh button and the Cmd+R shortcut.
    ///
    /// Intentionally NOT auto-fired on frontend rebuilds. A filesystem watcher
    /// that reloads mid-navigation bounces the operator back to the home
    /// route and interrupts the two-finger back gesture — catastrophic UX.
    /// If you want hot-reload in dev, point the app at the Vite dev server
    /// (port 5173) instead; Vite's HMR preserves route + scroll + state.
    func reloadAllWebViews() {
        for entry in trackedWebViews.values {
            guard let webView = entry.webView else { continue }
            webView.reloadFromOrigin()
        }
    }

    func showCommandPalette() {
        if let active = activeWebView() {
            active.evaluateJavaScript("window.dispatchEvent(new CustomEvent('zenith:show-command-palette'));")
        } else {
            openLens("/station")
        }
    }

    func focusWindow(windowID: String) {
        guard let window = liveWindow(windowID: windowID) else { return }
        NSApp.activate(ignoringOtherApps: true)
        window.makeKeyAndOrderFront(nil)
        emitRecordingSurfaceForWindowID(windowID)
    }

    func focusCockpitWindow() -> Bool {
        focusExistingWindow(windowID: ZenithSceneID.cockpit.rawValue)
    }

    func applicationWillTerminate() {
        terminateBootstrapShellIfNeeded()
        stopManagedBackendIfNeeded()
    }

    func saveWorkspace(named name: String) async {
        let title = name.trimmingCharacters(in: .whitespacesAndNewlines)
        let finalName = title.isEmpty ? "Workspace \(Date.now.formatted(date: .abbreviated, time: .shortened))" : title

        let windows: [ZenithWorkspaceWindow] = trackedWindows.compactMap { key, value in
            guard let window = value.window.window else { return nil }
            return ZenithWorkspaceWindow(
                id: key,
                route: value.descriptor.route,
                nativeLens: value.descriptor.nativeLens,
                title: value.descriptor.title ?? window.title,
                frame: WindowFrameRecord(rect: window.frame),
                screenName: window.screen?.localizedName
            )
        }

        let workspace = ZenithWorkspace(
            id: UUID().uuidString,
            name: finalName,
            savedAt: .now,
            repoRoot: repoRoot,
            windows: windows
        )

        do {
            try await workspaceStore.save(workspace)
            await reloadWorkspaces()
            lastActionMessage = "Saved workspace '\(finalName)'."
        } catch {
            lastErrorMessage = error.localizedDescription
        }
    }

    func restoreWorkspace(id: String) async {
        guard let workspace = workspaces.first(where: { $0.id == id }) else { return }
        if workspace.repoRoot != repoRoot {
            updateRepoRoot(workspace.repoRoot)
        }
        for window in workspace.windows {
            if let frame = window.frame {
                pendingFrames[window.id] = frame
            }
            if let nativeLens = window.nativeLens {
                openLens(nativeLens.rawValue)
            } else if let route = window.route {
                openLens(route)
            }
        }
        lastActionMessage = "Restored workspace '\(workspace.name)'."
    }

    func appendRawSeedAndDispatch(
        family: String,
        heading: String?,
        text: String,
        provider: String,
        cohortSize: Int,
        waveWidth: Int
    ) async {
        let trimmedText = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedText.isEmpty else {
            lastErrorMessage = "Raw seed text is empty."
            return
        }

        do {
            let append = try await apiClient.appendRawSeed(
                RawSeedAppendRequestBody(
                    family: family.isEmpty ? "__active__" : family,
                    text: trimmedText,
                    heading: heading?.isEmpty == true ? nil : heading
                )
            )
            let launch = try await apiClient.launchOperation(
                operationID: "raw_seed_distill_cycle",
                parameters: [
                    "family": family.isEmpty ? "__active__" : family,
                    "provider": provider,
                    "cohort_size": String(cohortSize),
                    "wave_width": String(waveWidth),
                ]
            )
            if !launch.ok {
                throw ZenithAPIError.http(400, launch.error ?? "Operation launch failed")
            }
            lastActionMessage = "Appended \(append.appendedAnchorIds.count) anchor(s) and launched distill cycle."
            await refreshAll()
            openLens(ZenithNativeLens.gateQueue.rawValue)
        } catch {
            lastErrorMessage = error.localizedDescription
        }
    }

    func acknowledgeGate(reason: String? = nil) async {
        do {
            let result = try await apiClient.acknowledgeGate(reason: reason)
            if !result.ok {
                throw ZenithAPIError.http(400, result.error ?? "Acknowledge failed")
            }
            await refreshAll()
            lastActionMessage = "Acknowledged orchestration gate."
        } catch {
            lastErrorMessage = error.localizedDescription
        }
    }

    func launchOperation(_ operationID: String, parameters: [String: String] = [:]) async {
        do {
            let result = try await apiClient.launchOperation(operationID: operationID, parameters: parameters)
            if !result.ok {
                throw ZenithAPIError.http(400, result.error ?? "Operation launch failed")
            }
            lastActionMessage = "Launched \(operationID)."
            await refreshAll()
        } catch {
            lastErrorMessage = error.localizedDescription
        }
    }

    func handleDeepLink(_ url: URL) {
        guard url.scheme?.lowercased() == "zenith" else { return }
        let host = url.host?.lowercased() ?? ""
        let path = url.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        var route = "/" + path
        if let query = url.query, !query.isEmpty {
            route += "?\(query)"
        }
        if let fragment = url.fragment, !fragment.isEmpty {
            route += "#\(fragment)"
        }
        switch host {
        case "workspace":
            Task { await restoreWorkspace(id: path) }
        case "lens":
            openLens(route)
        case "phase":
            openLens("/station/phase/\(path)")
        case "gate":
            openLens(ZenithNativeLens.gateQueue.rawValue)
        default:
            break
        }
    }

    func recommendedFamilyToken() -> String {
        stationLauncher?.family.familyNumber ?? "__active__"
    }

    func actionableAttentionItems() -> [AttentionSnapshot.AttentionItem] {
        (attentionSnapshot?.attentionItems ?? []).filter { item in
            item.kind == "gate" || item.kind == "driver_block"
        }
    }

    func gateQueueOperations() -> [StationLauncherSnapshot.StationOperation] {
        let operations = stationLauncher?.operations ?? []
        let interesting = Set(["raw_seed_route_review", "raw_seed_apply_routing", "raw_seed_surface_to_codex"])
        return operations.filter { interesting.contains($0.operationId) }
    }

    private func reloadWorkspaces() async {
        do {
            workspaces = try await workspaceStore.loadAll()
        } catch {
            lastErrorMessage = error.localizedDescription
        }
    }

    private func applyBootstrap(_ bootstrap: ZenithBootstrapResponse) async {
        await markBackendReady()
        stationLauncher = bootstrap.stationLauncher
        attentionSnapshot = bootstrap.attention
        runtimeSupervisor.replace(with: bootstrap.runtime)
        reloadDockBadge()
        notifyOnAttentionChange()
    }

    private func startPolling() {
        pollingTask?.cancel()
        pollingTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                await self.refreshAll()
                try? await Task.sleep(for: .seconds(15))
            }
        }
    }

    private func reloadDockBadge() {
        let count = actionableAttentionItems().count
        NSApp.dockTile.badgeLabel = count > 0 ? String(count) : nil
    }

    private func notifyOnAttentionChange() {
        guard let attentionSnapshot else { return }
        let top = actionableAttentionItems().first
        let token = "\(top?.id ?? "none")|\(attentionSnapshot.banner.title)"
        guard token != lastNotificationToken else { return }
        lastNotificationToken = token

        if let item = top {
            postNotification(
                identifier: item.id,
                title: item.title,
                body: item.detail ?? attentionSnapshot.banner.summary ?? "Operator attention required."
            )
        }
    }

    // Notifications are intentionally disabled for unsigned dev builds.
    // `UNUserNotificationCenter.add(...)` invokes its completion handler on
    // its own serial queue; under Swift 6 strict concurrency that trips a
    // main-actor isolation assertion inside `swift_task_isCurrentExecutor`
    // and crashes the app with `EXC_BREAKPOINT` on the
    // `com.apple.usernotifications.UNUserNotificationServiceConnection.call-out`
    // dispatch queue. Without a Developer ID + notarisation, notifications
    // also don't reliably get authorised anyway. Re-enable behind a feature
    // flag once the app ships with proper code signing.
    private func postNotification(identifier: String, title: String, body: String) {
        _ = (identifier, title, body)  // deliberate no-op
    }

    func postImmediateNotification(title: String, body: String) {
        _ = (title, body)  // deliberate no-op — see postNotification comment
    }

    private func activeWebView() -> WKWebView? {
        if let keyWindow = NSApp.keyWindow {
            for entry in trackedWebViews.values where entry.window === keyWindow {
                return entry.webView
            }
        }
        return trackedWebViews.values.compactMap(\.webView).first
    }

    private func installRecordingKeyWindowObserver() {
        keyWindowObserver = NotificationCenter.default.addObserver(
            forName: NSWindow.didBecomeKeyNotification,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            guard let window = notification.object as? NSWindow else { return }
            Task { @MainActor in
                self?.recordingWindowBecameKey(window)
            }
        }
    }

    private func recordingWindowBecameKey(_ window: NSWindow) {
        guard let entry = trackedWindows.first(where: { _, value in
            value.window.window === window
        }) else {
            return
        }
        emitRecordingSurfaceForWindowID(entry.key)
    }

    private func emitRecordingSurfaceForWindowID(_ windowID: String) {
        guard let entry = trackedWindows[windowID],
              let window = entry.window.window,
              window === NSApp.keyWindow else {
            return
        }

        let event: RecordingViewEventBody
        if let webEvent = latestWebSurfaceByWindowID[windowID] {
            event = hostStampedWebRecordingEvent(webEvent, windowID: windowID)
        } else {
            event = fallbackRecordingEvent(for: entry.descriptor, window: window)
        }

        Task { [apiClient] in
            _ = try? await apiClient.postRecordingViewEvent(event)
        }
    }

    private func hostStampedWebRecordingEvent(
        _ event: RecordingViewEventBody,
        windowID: String
    ) -> RecordingViewEventBody {
        RecordingViewEventBody(
            source: "zenith_host",
            runtimeMode: "embedded",
            hostApp: "zenith_macos",
            windowId: windowID,
            workspaceId: event.workspaceId,
            surfaceKind: "web",
            surfaceId: event.surfaceId ?? event.viewId,
            nativeLens: nil,
            route: event.route,
            viewId: event.viewId,
            viewLabel: event.viewLabel,
            pathname: event.pathname,
            search: event.search,
            hash: event.hash,
            isKeyWindow: true,
            isOperatorActive: true,
            clientAtIso: isoTimestamp()
        )
    }

    private func fallbackRecordingEvent(
        for descriptor: WindowRegistrationDescriptor,
        window: NSWindow
    ) -> RecordingViewEventBody {
        if let nativeLens = descriptor.nativeLens {
            return RecordingViewEventBody(
                source: "zenith_host",
                runtimeMode: "embedded",
                hostApp: "zenith_macos",
                windowId: descriptor.windowID,
                workspaceId: nil,
                surfaceKind: "native",
                surfaceId: nativeLens.rawValue,
                nativeLens: nativeLens.rawValue,
                route: nil,
                viewId: nativeLens.rawValue,
                viewLabel: descriptor.title ?? window.title,
                pathname: nil,
                search: nil,
                hash: nil,
                isKeyWindow: true,
                isOperatorActive: true,
                clientAtIso: isoTimestamp()
            )
        }

        let route = descriptor.route ?? "/station"
        let surfaceID = captureSurfaceForRoute(route)
        return RecordingViewEventBody(
            source: "zenith_host",
            runtimeMode: "embedded",
            hostApp: "zenith_macos",
            windowId: descriptor.windowID,
            workspaceId: nil,
            surfaceKind: "web",
            surfaceId: surfaceID,
            nativeLens: nil,
            route: route,
            viewId: surfaceID,
            viewLabel: descriptor.title ?? window.title,
            pathname: route,
            search: "",
            hash: "",
            isKeyWindow: true,
            isOperatorActive: true,
            clientAtIso: isoTimestamp()
        )
    }

    private func makeWebRecordingEvent(payload: [String: Any], windowID: String) -> RecordingViewEventBody {
        let route = stringPayload(payload, "route") ?? stringPayload(payload, "pathname") ?? "/station"
        let viewID = stringPayload(payload, "view_id") ?? captureSurfaceForRoute(route)
        return RecordingViewEventBody(
            source: "zenith_host",
            runtimeMode: "embedded",
            hostApp: "zenith_macos",
            windowId: windowID,
            workspaceId: stringPayload(payload, "workspace_id"),
            surfaceKind: "web",
            surfaceId: stringPayload(payload, "surface_id") ?? viewID,
            nativeLens: nil,
            route: route,
            viewId: viewID,
            viewLabel: stringPayload(payload, "view_label"),
            pathname: stringPayload(payload, "pathname") ?? route,
            search: stringPayload(payload, "search") ?? "",
            hash: stringPayload(payload, "hash") ?? "",
            isKeyWindow: false,
            isOperatorActive: false,
            clientAtIso: isoTimestamp()
        )
    }

    private func stringPayload(_ payload: [String: Any], _ key: String) -> String? {
        if let value = payload[key] as? String {
            let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
            return trimmed.isEmpty ? nil : value
        }
        return nil
    }

    private func captureSurfaceForRoute(_ route: String) -> String {
        let normalized = ZenithWindowIdentity.normalizedRoute(route)
        if normalized == "/station" || normalized == "/world" {
            return "home"
        }
        if normalized.hasPrefix("/station/") {
            let rest = normalized.dropFirst("/station/".count)
            return rest.split(separator: "/").first.map(String.init) ?? "station"
        }
        if normalized.hasPrefix("/world/") {
            let rest = normalized.dropFirst("/world/".count)
            return rest.split(separator: "/").first.map(String.init) ?? "station"
        }
        return normalized.trimmingCharacters(in: CharacterSet(charactersIn: "/")).split(separator: "/").first.map(String.init) ?? "root"
    }

    private func isoTimestamp() -> String {
        ISO8601DateFormatter().string(from: Date())
    }

    private func liveWindow(windowID: String) -> NSWindow? {
        guard let entry = trackedWindows[windowID] else { return nil }
        guard let window = entry.window.window else {
            trackedWindows.removeValue(forKey: windowID)
            trackedWebViews.removeValue(forKey: windowID)
            return nil
        }
        return window
    }

    private func focusExistingWindow(windowID: String) -> Bool {
        guard let window = liveWindow(windowID: windowID) else { return false }
        NSApp.activate(ignoringOtherApps: true)
        window.makeKeyAndOrderFront(nil)
        return true
    }

    private func apply(frame: WindowFrameRecord, to window: NSWindow) {
        let target = frame.cgRect
        if NSScreen.screens.contains(where: { $0.visibleFrame.intersects(target) }) {
            window.setFrame(target, display: true)
            return
        }
        guard let fallback = NSScreen.main?.visibleFrame else { return }
        let size = CGSize(
            width: min(target.width, fallback.width - 80),
            height: min(target.height, fallback.height - 80)
        )
        let origin = CGPoint(
            x: fallback.minX + 40,
            y: fallback.maxY - size.height - 40
        )
        window.setFrame(CGRect(origin: origin, size: size), display: true)
    }

    private func zenithStateDirectory() throws -> URL {
        let caches = try FileManager.default.url(
            for: .cachesDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )
        let dir = caches.appendingPathComponent("Zenith", isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    private func backendOwnerRecordURL(in directory: URL? = nil) -> URL {
        let base = directory ?? (try? zenithStateDirectory()) ?? URL(fileURLWithPath: NSTemporaryDirectory(), isDirectory: true)
        return base.appendingPathComponent("managed_backend_owner.json")
    }

    private func backendPIDFileURL(in directory: URL? = nil) -> URL {
        let base = directory ?? (try? zenithStateDirectory()) ?? URL(fileURLWithPath: NSTemporaryDirectory(), isDirectory: true)
        return base.appendingPathComponent("managed_backend.pid")
    }

    private func backendLaunchScriptURL(in directory: URL? = nil) -> URL {
        let base = directory ?? (try? zenithStateDirectory()) ?? URL(fileURLWithPath: NSTemporaryDirectory(), isDirectory: true)
        return base.appendingPathComponent("start_zenith_backend.command")
    }

    private func backendShellPIDFileURL(in directory: URL? = nil) -> URL {
        let base = directory ?? (try? zenithStateDirectory()) ?? URL(fileURLWithPath: NSTemporaryDirectory(), isDirectory: true)
        return base.appendingPathComponent("bootstrap_terminal_shell.pid")
    }

    private func managedBackendRecord() -> ZenithManagedBackendRecord? {
        let url = backendOwnerRecordURL()
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(ZenithManagedBackendRecord.self, from: data)
    }

    private func managedBackendPID() -> Int32? {
        if let record = managedBackendRecord(), let pid = record.backendPID {
            return pid
        }
        let url = backendPIDFileURL()
        guard let text = try? String(contentsOf: url, encoding: .utf8) else { return nil }
        return Int32(text.trimmingCharacters(in: .whitespacesAndNewlines))
    }

    private func processIsRunning(pid: Int32) -> Bool {
        guard pid > 0 else { return false }
        return kill(pid, 0) == 0 || errno != ESRCH
    }

    private func managedBackendIsRunning() -> Bool {
        guard let pid = managedBackendPID() else { return false }
        return processIsRunning(pid: pid)
    }

    private func bootstrapShellPID() -> Int32? {
        let url = backendShellPIDFileURL()
        guard let text = try? String(contentsOf: url, encoding: .utf8) else { return nil }
        return Int32(text.trimmingCharacters(in: .whitespacesAndNewlines))
    }

    private func clearStaleManagedBackendStateIfNeeded() {
        guard let pid = managedBackendPID() else { return }
        guard !processIsRunning(pid: pid) else { return }
        try? FileManager.default.removeItem(at: backendOwnerRecordURL())
        try? FileManager.default.removeItem(at: backendPIDFileURL())
    }

    private func terminateBootstrapShellIfNeeded() {
        defer { try? FileManager.default.removeItem(at: backendShellPIDFileURL()) }
        guard let pid = bootstrapShellPID() else { return }
        guard processIsRunning(pid: pid) else { return }
        _ = kill(pid, SIGTERM)
    }

    private func reconcileBackendLaunchState() {
        if managedBackendIsRunning() {
            backendLaunchInFlight = true
            return
        }
        if let lastBackendLaunchAttemptAt,
           Date().timeIntervalSince(lastBackendLaunchAttemptAt) < 8 {
            backendLaunchInFlight = true
        } else {
            backendLaunchInFlight = false
        }
    }

    private func backendWaitingStatusText(attempt: Int?) -> String {
        _ = attempt
        if managedBackendIsRunning() {
            return "Warming local runtime…"
        }
        if backendLaunchInFlight {
            return "Starting local runtime…"
        }
        return "Preparing local runtime…"
    }

    private func stopManagedBackendIfNeeded() {
        guard let record = managedBackendRecord(),
              let pid = record.backendPID,
              processIsRunning(pid: pid) else {
            clearManagedBackendStateFilesIfStale()
            return
        }
        let commandLine = processCommandLine(pid: pid)
        guard ZenithManagedBackendShutdownPolicy.shouldTerminate(
            record: record,
            currentOwnerToken: backendOwnerToken,
            currentRepoRoot: repoRoot,
            commandLine: commandLine
        ) else {
            return
        }
        _ = kill(pid, SIGTERM)
        for _ in 0..<10 where processIsRunning(pid: pid) {
            usleep(100_000)
        }
        if processIsRunning(pid: pid) {
            _ = kill(pid, SIGKILL)
        }
        clearManagedBackendStateFiles()
    }

    private func processCommandLine(pid: Int32) -> String? {
        guard pid > 0 else { return nil }
        let process = Process()
        let pipe = Pipe()
        process.executableURL = URL(fileURLWithPath: "/bin/ps")
        process.arguments = ["-p", "\(pid)", "-o", "command="]
        process.standardOutput = pipe
        process.standardError = Pipe()
        do {
            try process.run()
            process.waitUntilExit()
        } catch {
            return nil
        }
        guard process.terminationStatus == 0 else { return nil }
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        let command = String(data: data, encoding: .utf8)?
            .trimmingCharacters(in: .whitespacesAndNewlines)
        return command?.isEmpty == false ? command : nil
    }

    private func clearManagedBackendStateFilesIfStale() {
        if let pid = managedBackendPID(), processIsRunning(pid: pid) {
            return
        }
        clearManagedBackendStateFiles()
    }

    private func clearManagedBackendStateFiles() {
        try? FileManager.default.removeItem(at: backendOwnerRecordURL())
        try? FileManager.default.removeItem(at: backendPIDFileURL())
        try? FileManager.default.removeItem(at: backendShellPIDFileURL())
    }

    private func backendLaunchLogPath() -> String {
        URL(fileURLWithPath: repoRoot)
            .appendingPathComponent("state/server_debug.log")
            .path
    }
}
