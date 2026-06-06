import AppKit
import SwiftUI
import WebKit

final class ZenithHostScriptHandler: NSObject, WKScriptMessageHandler, WKNavigationDelegate {
    weak var model: ZenithAppModel?
    weak var webView: WKWebView?
    var windowID: String?
    var onFailedLoad: (() -> Void)?

    init(model: ZenithAppModel) {
        self.model = model
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.name == "zenithHost",
              let body = message.body as? [String: Any],
              let method = body["method"] as? String else {
            return
        }

        switch method {
        case "openLens":
            if let route = body["route"] as? String {
                model?.openLens(route)
            }
        case "focusLens":
            if let windowID = body["windowId"] as? String {
                model?.focusWindow(windowID: windowID)
            }
        case "saveWorkspace":
            let name = body["name"] as? String ?? ""
            Task { await model?.saveWorkspace(named: name) }
        case "restoreWorkspace":
            if let workspaceID = body["workspaceId"] as? String {
                Task { await model?.restoreWorkspace(id: workspaceID) }
            }
        case "showCommandPalette":
            model?.showCommandPalette()
        case "notify":
            let title = body["title"] as? String ?? "Zenith"
            let content = body["body"] as? String ?? ""
            model?.postImmediateNotification(title: title, body: content)
        case "copyText":
            if let text = body["text"] as? String {
                model?.copyTextFromHost(text)
            }
        case "recordingViewChanged":
            if let payload = body["payload"] as? [String: Any] {
                model?.recordingViewChanged(payload, windowID: windowID)
            }
        default:
            break
        }
    }

    // MARK: WKNavigationDelegate

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        guard webView.url?.host == "127.0.0.1",
              let windowID else {
            return
        }
        Task { @MainActor in
            self.model?.markWebViewLoaded(windowID: windowID)
        }
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        onFailedLoad?()
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        onFailedLoad?()
    }
}

struct EmbeddedLensWebView: NSViewRepresentable {
    @ObservedObject var model: ZenithAppModel
    var route: String
    var windowID: String
    var workspaceID: String?

    func makeCoordinator() -> ZenithHostScriptHandler {
        ZenithHostScriptHandler(model: model)
    }

    func makeNSView(context: Context) -> WKWebView {
        let userContentController = WKUserContentController()
        userContentController.add(context.coordinator, name: "zenithHost")
        userContentController.addUserScript(
            WKUserScript(
                source: hostBootstrapScript(),
                injectionTime: .atDocumentStart,
                forMainFrameOnly: true
            )
        )

        let configuration = WKWebViewConfiguration()
        configuration.userContentController = userContentController
        configuration.defaultWebpagePreferences.allowsContentJavaScript = true
        configuration.defaultWebpagePreferences.preferredContentMode = .desktop

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.setValue(false, forKey: "drawsBackground")
        webView.navigationDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true
        webView.customUserAgent = "ZenithApp/0.1 (macOS; embedded WKWebView)"
        context.coordinator.webView = webView
        context.coordinator.windowID = windowID
        context.coordinator.onFailedLoad = { [weak webView] in
            guard let webView else { return }
            // Retry briefly; the backend may still be warming.
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
                Task { @MainActor in
                    if model.backendSurfaceAvailable {
                        loadRemote(into: webView, route: route)
                    }
                }
            }
        }

        loadContent(into: webView)
        model.registerWebView(webView, windowID: windowID)
        return webView
    }

    func updateNSView(_ webView: WKWebView, context: Context) {
        context.coordinator.windowID = windowID
        model.registerWebView(webView, windowID: windowID)
        // If the backend just came online, swap the webview over to the live
        // URL. The earlier version also gated on `!webView.isLoading`, which
        // caused a stuck-blank state: when backendReady flipped while the
        // bundle was still loading, the guard blocked the reload and updateNSView
        // never ran again (no further @Published churn). Cheap to just reload.
        if model.backendSurfaceAvailable, (webView.url?.host ?? "") != "127.0.0.1" {
            loadRemote(into: webView, route: route)
        }
    }

    private func loadContent(into webView: WKWebView) {
        if model.backendSurfaceAvailable {
            loadRemote(into: webView, route: route)
            return
        }
        // Backend not yet ready: show bundled fallback if we have one so the
        // view isn't just a blank canvas during warm-up.
        let bundleIndex = Bundle.main.resourceURL?.appendingPathComponent("EmbeddedWeb/index.html")
        if let bundleIndex, FileManager.default.fileExists(atPath: bundleIndex.path) {
            webView.loadFileURL(bundleIndex, allowingReadAccessTo: bundleIndex.deletingLastPathComponent())
            return
        }
        // No bundle and no backend: leave blank; the SwiftUI overlay shows a
        // readable status message instead of a white/black void.
    }

    private func loadRemote(into webView: WKWebView, route: String) {
        var components = URLComponents()
        components.scheme = "http"
        components.host = "127.0.0.1"
        components.port = 8000
        let normalizedPath = route.hasPrefix("/") ? route : "/\(route)"
        if let routeComponents = URLComponents(string: normalizedPath) {
            components.path = routeComponents.path.isEmpty ? "/" : routeComponents.path
            components.percentEncodedQuery = routeComponents.percentEncodedQuery
            components.percentEncodedFragment = routeComponents.percentEncodedFragment
        } else {
            components.path = normalizedPath.isEmpty ? "/" : normalizedPath
        }
        guard let url = components.url else { return }
        // Bypass WKWebView's disk cache so the webview never serves a stale
        // index.html after a frontend rebuild. The asset filenames are
        // content-hashed, so fresh index.html is the only thing we need to
        // re-fetch — the JS/CSS cache-validates normally once loaded.
        var request = URLRequest(url: url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        webView.load(request)
    }

    private func hostBootstrapScript() -> String {
        let payload: [String: Any] = [
            "mode": "embedded",
            "initialRoute": route,
            "backendHttpBase": "http://127.0.0.1:8000/api",
            "backendWsBase": "ws://127.0.0.1:8000/ws",
            "workspaceId": workspaceID as Any,
            "windowId": windowID,
            "hostCapabilities": [
                "openLens": true,
                "focusLens": true,
                "saveWorkspace": true,
                "restoreWorkspace": true,
                "showCommandPalette": true,
                "notify": true,
                "copyText": true,
                "recordingViewChanged": true,
            ],
        ]
        let jsonData = try? JSONSerialization.data(withJSONObject: payload, options: [])
        let json = String(data: jsonData ?? Data("{}".utf8), encoding: .utf8) ?? "{}"
        return """
        window.__ZENITH_RUNTIME_CONTEXT__ = \(json);
        window.__ZENITH_HOST_BRIDGE__ = {
          openLens: function(route, options) {
            window.webkit.messageHandlers.zenithHost.postMessage({ method: 'openLens', route: route, options: options || {} });
          },
          focusLens: function(windowId) {
            window.webkit.messageHandlers.zenithHost.postMessage({ method: 'focusLens', windowId: windowId });
          },
          saveWorkspace: function(name) {
            window.webkit.messageHandlers.zenithHost.postMessage({ method: 'saveWorkspace', name: name || '' });
          },
          restoreWorkspace: function(workspaceId) {
            window.webkit.messageHandlers.zenithHost.postMessage({ method: 'restoreWorkspace', workspaceId: workspaceId });
          },
          showCommandPalette: function() {
            window.webkit.messageHandlers.zenithHost.postMessage({ method: 'showCommandPalette' });
          },
          notify: function(kind, title, body) {
            window.webkit.messageHandlers.zenithHost.postMessage({ method: 'notify', kind: kind || 'info', title: title || 'Zenith', body: body || '' });
          },
          copyText: function(text) {
            window.webkit.messageHandlers.zenithHost.postMessage({ method: 'copyText', text: String(text || '') });
            return true;
          },
          recordingViewChanged: function(payload) {
            window.webkit.messageHandlers.zenithHost.postMessage({ method: 'recordingViewChanged', payload: payload || {} });
          }
        };
        """
    }
}

struct BootStatusChip: View {
    let label: String
    let value: String
    let tint: Color

    var body: some View {
        HStack(spacing: 6) {
            Text(label.uppercased())
                .font(.system(.caption2, design: .monospaced))
                .foregroundStyle(.secondary)
            Text(value)
                .font(.caption.weight(.semibold))
                .lineLimit(1)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .background(Capsule().fill(tint.opacity(0.12)))
        .overlay(Capsule().stroke(tint.opacity(0.25), lineWidth: 1))
    }
}

/// Full-window loading surface while Zenith auto-starts or reconnects to the
/// local backend. The bootstrap still happens through a hidden Terminal-owned
/// process, but that plumbing stays out of the user's way unless startup stalls.
struct BackendBootScreen: View {
    @ObservedObject var model: ZenithAppModel
    let routeTitle: String
    let windowID: String?

    @State private var revealRecovery = false

    private var shouldShow: Bool {
        model.shouldShowBackendBootScreen(windowID: windowID)
    }

    private var stage: ZenithAppModel.BackendBootStage {
        model.backendBootStage
    }

    private var accent: Color {
        switch stage {
        case .waiting:
            return .orange
        case .launching:
            return .yellow
        case .starting:
            return .blue
        case .ready:
            return .green
        }
    }

    private var stageLabel: String {
        switch stage {
        case .waiting:
            return "Queued"
        case .launching:
            return "Launching"
        case .starting:
            return "Warming"
        case .ready:
            return "Connected"
        }
    }

    private var subtitle: String {
        switch stage {
        case .waiting:
            return "Preparing the local control runtime."
        case .launching:
            return "Starting services quietly in the background."
        case .starting:
            return "Connecting the cockpit to live runtime surfaces."
        case .ready:
            return "Connected."
        }
    }

    private var phaseTitle: String? {
        let raw = model.stationLauncher?.activePhase?.title
            ?? model.attentionSnapshot?.activePhase?.title
        guard let raw, !raw.isEmpty else { return nil }
        let trimmed = raw.replacingOccurrences(of: "Phase ", with: "")
        return trimmed.count > 26 ? String(trimmed.prefix(26)) : trimmed
    }

    /// Compact "5s" / "12s" / "2m" age string for the boot status chip row.
    /// Probes fire every 650-1800ms; the chip is meant to confirm the loop is
    /// alive and how recently it tried.
    private func relativeAge(_ date: Date) -> String {
        let elapsed = max(0, Date().timeIntervalSince(date))
        if elapsed < 1.0 { return "now" }
        if elapsed < 60 { return "\(Int(elapsed))s" }
        if elapsed < 3600 { return "\(Int(elapsed / 60))m" }
        return "\(Int(elapsed / 3600))h"
    }

    var body: some View {
        if shouldShow {
            ZStack {
                LinearGradient(
                    colors: [
                        Color(red: 0.04, green: 0.05, blue: 0.08),
                        Color(red: 0.02, green: 0.02, blue: 0.03),
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                RadialGradient(
                    colors: [
                        accent.opacity(0.24),
                        accent.opacity(0.08),
                        .clear,
                    ],
                    center: .top,
                    startRadius: 20,
                    endRadius: 420
                )
                .blendMode(.plusLighter)

                VStack(spacing: 24) {
                    Spacer(minLength: 60)

                    ZStack {
                        Circle()
                            .fill(accent.opacity(0.14))
                            .frame(width: 132, height: 132)
                            .blur(radius: 18)
                        RoundedRectangle(cornerRadius: 30)
                            .fill(.ultraThinMaterial)
                            .frame(width: 92, height: 92)
                            .overlay(
                                RoundedRectangle(cornerRadius: 30)
                                    .stroke(Color.white.opacity(0.09), lineWidth: 1)
                            )
                        Image(systemName: "waveform.path.ecg.rectangle")
                            .font(.system(size: 34, weight: .semibold))
                            .foregroundStyle(accent)
                    }

                    VStack(spacing: 10) {
                        Text("Zenith")
                            .font(.system(size: 34, weight: .bold, design: .rounded))
                        Text("Preparing \(routeTitle)")
                            .font(.title3.weight(.medium))
                            .foregroundStyle(.primary)
                        Text(subtitle)
                            .font(.callout)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                    }

                    ProgressView()
                        .controlSize(.regular)
                        .tint(accent)

                    let diagnostic = model.bootDiagnostic

                    HStack(spacing: 10) {
                        BootStatusChip(label: "Runtime", value: stageLabel, tint: accent)
                        BootStatusChip(label: "Target", value: routeTitle, tint: .blue)
                        if let pid = diagnostic.pid {
                            BootStatusChip(
                                label: "PID",
                                value: diagnostic.pidIsRunning ? "\(pid)" : "\(pid) gone",
                                tint: diagnostic.pidIsRunning ? .green : .red
                            )
                        }
                        if let lastProbe = diagnostic.lastProbeAttemptAt {
                            BootStatusChip(
                                label: "Probe",
                                value: relativeAge(lastProbe),
                                tint: .secondary
                            )
                        }
                        if let phaseTitle {
                            BootStatusChip(label: "Phase", value: phaseTitle, tint: .secondary)
                        }
                    }
                    .frame(maxWidth: .infinity)

                    Text(model.backendStatusText)
                        .font(.caption)
                        .foregroundStyle(.tertiary)

                    if !diagnostic.recoveryReason.isEmpty {
                        Text(diagnostic.recoveryReason)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                            .frame(maxWidth: 540)
                    }

                    if revealRecovery {
                        VStack(spacing: 10) {
                            Text("Startup is taking longer than usual.")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            HStack(spacing: 10) {
                                Button("Retry") {
                                    Task { await model.refreshAll() }
                                }
                                .buttonStyle(.bordered)
                                Button("Restart Bootstrap") {
                                    model.startBackendBootstrap()
                                }
                                .buttonStyle(.borderedProminent)
                                Button("Runtime") {
                                    model.openLens(ZenithNativeLens.runtimePanel.rawValue)
                                }
                                .buttonStyle(.bordered)
                            }
                            HStack(spacing: 10) {
                                Button("Copy start command") {
                                    model.copyBackendStartCommand()
                                }
                                .buttonStyle(.borderless)
                                Button("Copy log path") {
                                    model.copyBackendLogPath()
                                }
                                .buttonStyle(.borderless)
                                Button("Reveal log") {
                                    model.revealBackendLogInFinder()
                                }
                                .buttonStyle(.borderless)
                            }
                            .font(.caption)

                            Text(diagnostic.logPath)
                                .font(.system(.caption2, design: .monospaced))
                                .foregroundStyle(.tertiary)
                                .lineLimit(1)
                                .truncationMode(.middle)
                                .frame(maxWidth: 540)

                            let tail = model.recentBackendLogTail(limit: 8)
                            if !tail.isEmpty {
                                ScrollView {
                                    VStack(alignment: .leading, spacing: 2) {
                                        ForEach(Array(tail.enumerated()), id: \.offset) { _, line in
                                            Text(line)
                                                .font(.system(.caption2, design: .monospaced))
                                                .foregroundStyle(.secondary)
                                                .lineLimit(2)
                                                .frame(maxWidth: .infinity, alignment: .leading)
                                        }
                                    }
                                    .padding(8)
                                }
                                .frame(maxWidth: 600, maxHeight: 140)
                                .background(Color.black.opacity(0.25))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 6)
                                        .stroke(Color.white.opacity(0.08), lineWidth: 1)
                                )
                                .clipShape(RoundedRectangle(cornerRadius: 6))
                            }
                        }
                        .padding(.top, 6)
                        .transition(.opacity)
                    }

                    if let error = model.lastErrorMessage {
                        Text(error)
                            .font(.caption)
                            .foregroundStyle(.red)
                            .multilineTextAlignment(.center)
                            .frame(maxWidth: 520)
                    }

                    Spacer(minLength: 70)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .task(id: shouldShow) {
                revealRecovery = false
                guard shouldShow else { return }
                try? await Task.sleep(for: .seconds(8))
                guard !Task.isCancelled, shouldShow else { return }
                withAnimation(.easeInOut(duration: 0.2)) {
                    revealRecovery = true
                }
            }
        }
    }
}

/// Fires `onResolve` exactly once per NSWindow instance. SwiftUI re-runs
/// `updateNSView` on every `@Published` tick; the previous implementation
/// re-ran window configuration on every one of those, which caused AppKit
/// to toggle titlebar opacity in sync with the auto-poll and made the
/// cockpit visibly flicker.
struct WindowAccessor: NSViewRepresentable {
    var onResolve: (NSWindow) -> Void

    func makeCoordinator() -> Coordinator { Coordinator() }

    final class Coordinator {
        weak var resolvedWindow: NSWindow?
    }

    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        scheduleResolve(view: view, coordinator: context.coordinator)
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {
        scheduleResolve(view: nsView, coordinator: context.coordinator)
    }

    private func scheduleResolve(view: NSView, coordinator: Coordinator) {
        DispatchQueue.main.async {
            guard let window = view.window else { return }
            if coordinator.resolvedWindow === window { return }
            coordinator.resolvedWindow = window
            onResolve(window)
        }
    }
}

/// Stable window chrome for all Zenith scenes.
///
/// Default is the seamless titlebar: `titlebarAppearsTransparent` plus
/// `fullSizeContentView` so the unified-compact toolbar and the SwiftUI
/// sidebar paint up to the top edge under the traffic lights, and the
/// native chrome and Zenith chrome read as one surface.
///
/// History: an earlier seamless attempt was reverted for two reasons.
/// (1) The lens web view's top-left "Zenith STATION" pill collided with
/// the traffic lights because the web HTML didn't reserve a left inset.
/// (2) The titlebar opacity visibly flickered because SwiftUI re-ran
/// `updateNSView` on every `@Published` tick and re-applied window
/// configuration each time. The flicker is now structurally fixed by
/// `WindowAccessor` firing exactly once per NSWindow instance. The pill
/// collision is still a concern for lens scenes, so they pass
/// `mergeTitlebar: false` and keep the traditional opaque titlebar until
/// the lens HTML grows a 88px-wide left safe-area inset.
@MainActor
func applyZenithWindowStyle(_ window: NSWindow, title: String, mergeTitlebar: Bool = true) {
    window.title = title
    window.isRestorable = false
    window.titleVisibility = .hidden
    window.toolbarStyle = .unifiedCompact
    window.tabbingMode = .disallowed
    if mergeTitlebar {
        window.titlebarAppearsTransparent = true
        window.styleMask.insert(.fullSizeContentView)
        window.isMovableByWindowBackground = true
    } else {
        // Lens scenes still need the opaque titlebar to keep the web
        // brand pill from colliding with the traffic lights. Explicitly
        // _remove_ the transparent/full-size flags in case an earlier
        // build left them on: NSWindow state survives hot-reload of the
        // app binary when the same window instance is reused.
        window.titlebarAppearsTransparent = false
        window.styleMask.remove(.fullSizeContentView)
        window.isMovableByWindowBackground = false
    }
    window.backgroundColor = NSColor(calibratedWhite: 0.07, alpha: 1.0)
}
