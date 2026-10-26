import AppKit
import SwiftUI

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    let store: RecorderStore
    let cueOverlay: RecipientCueOverlayController
    private var hudController: HudOverlayController?
    private var hotkeyMonitor: HotkeyMonitor?

    override init() {
        let store = RecorderStore()
        self.store = store
        self.cueOverlay = RecipientCueOverlayController(store: store)
        super.init()
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)

        hudController = HudOverlayController(store: store)
        store.onHudShouldShow = { [weak self] in
            self?.hudController?.show()
        }
        store.onHudShouldHide = { [weak self] in
            self?.hudController?.hide()
        }

        let monitor = HotkeyMonitor { [weak self] in
            guard let self else { return }
            self.store.markClip(source: .hotkey)
        }
        monitor.start()
        self.hotkeyMonitor = monitor

        // Recipient cue plane: per-display panels, arming monitor, sidecar binding.
        cueOverlay.start()

        DispatchQueue.main.async {
            self.configureMainWindow()
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        hotkeyMonitor?.stop()
        cueOverlay.stop()
    }

    private func configureMainWindow() {
        for window in NSApp.windows where window.title == "Demo Take Console" {
            window.minSize = NSSize(width: 1180, height: 760)
        }
    }
}

@main
struct DemoTakeConsoleApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate

    var body: some Scene {
        WindowGroup("Demo Take Console") {
            ContentView(store: appDelegate.store)
                .task {
                    await appDelegate.store.refreshPreflight()
                }
        }
        .defaultSize(width: 1440, height: 900)
        .windowStyle(.hiddenTitleBar)
        .commands {
            CommandMenu("Recording") {
                Button("Start") {
                    Task { await appDelegate.store.startRecording() }
                }
                .disabled(!appDelegate.store.canStart)
                .keyboardShortcut("r", modifiers: [.command])

                Button(appDelegate.store.state == .paused ? "Resume" : "Pause") {
                    appDelegate.store.togglePause()
                }
                .disabled(!appDelegate.store.canPauseOrResume)
                .keyboardShortcut("p", modifiers: [.command])

                Button("Stop") {
                    Task { await appDelegate.store.stopRecording() }
                }
                .disabled(!appDelegate.store.canStop)
                .keyboardShortcut(".", modifiers: [.command])

                Divider()

                Button("Mark Clip") {
                    appDelegate.store.markClip(source: .button)
                }
                .disabled(!appDelegate.store.canMark)
                .keyboardShortcut("m", modifiers: [.control, .option, .command])
            }

            CommandMenu("Package") {
                Button("Import Video...") {
                    appDelegate.store.importVideoFromPanel()
                }
                .disabled(!appDelegate.store.canImportVideo)
                .keyboardShortcut("i", modifiers: [.command])

                Button("Import Latest Phone Video") {
                    Task { await appDelegate.store.importRecentVideoCandidate() }
                }
                .disabled(!appDelegate.store.canImportRecentVideoCandidate)
                .keyboardShortcut("i", modifiers: [.command, .shift])

                Button("Export Upload") {
                    Task { await appDelegate.store.exportActiveTakeVideo() }
                }
                .disabled(!appDelegate.store.canExportVideo)
                .keyboardShortcut("e", modifiers: [.command])

                Button("Preview Take Review") {
                    appDelegate.store.previewActiveTakeReview()
                }
                .disabled(!appDelegate.store.canPreviewActiveTakeReview)

                Button("Prepare Review") {
                    Task { await appDelegate.store.prepareActiveTakeReview() }
                }
                .disabled(!appDelegate.store.canPrepareActiveTakeReview)

                Button("Build Package") {
                    Task { await appDelegate.store.buildPackageSidecars() }
                }
                .disabled(!appDelegate.store.canBuildPackage)

                Button("Preview Export") {
                    appDelegate.store.previewActiveTakeExport()
                }
                .disabled(!appDelegate.store.canPreviewActiveTakeExport)

                Button("Reveal Export") {
                    appDelegate.store.openActiveTakeExport()
                }
                .disabled(!appDelegate.store.canOpenActiveTakeExport)

                Button("Copy Export Path") {
                    appDelegate.store.copyActiveTakeExportPath()
                }
                .disabled(!appDelegate.store.canCopyActiveTakeExportPath)

                Button("Reveal Playback File") {
                    appDelegate.store.revealPlaybackAsset()
                }
                .disabled(!appDelegate.store.canRevealPlaybackAsset)

                Button("Copy Playback Path") {
                    appDelegate.store.copyPlaybackAssetPath()
                }
                .disabled(!appDelegate.store.canCopyPlaybackAssetPath)

                Divider()

                Button("Open Take Folder") {
                    appDelegate.store.revealTakeFolder()
                }
                .disabled(appDelegate.store.activeTakeURL == nil)

                Button("Delete Selected Take") {
                    appDelegate.store.requestDeleteTargetTake()
                }
                .disabled(!appDelegate.store.canRequestDeleteTargetTake)
                .keyboardShortcut(.delete, modifiers: [])

                Button("Open Exports Folder") {
                    appDelegate.store.openExportsRoot()
                }
            }

            CommandMenu("Overlay") {
                Button("Recipient Picker...") {
                    appDelegate.cueOverlay.showPicker()
                }
                .keyboardShortcut("o", modifiers: [.command, .shift])

                Menu("Select Recipient") {
                    OverlayRecipientMenu(controller: appDelegate.cueOverlay)
                }

                Divider()

                Button("Show Overlay") {
                    appDelegate.cueOverlay.showOverlay()
                }
                Button("Hide Overlay") {
                    appDelegate.cueOverlay.hideOverlay()
                }
                Button("Toggle Arrange Mode") {
                    appDelegate.cueOverlay.toggleArrange()
                }
                Button("Toggle Glance / Full Cues") {
                    appDelegate.cueOverlay.session.toggleGlanceMode()
                }
                .keyboardShortcut("g", modifiers: [.command, .shift])

                Divider()

                Button("Run Safety Check") {
                    Task { await appDelegate.cueOverlay.runSafetyCheck() }
                }
                .disabled(appDelegate.cueOverlay.safetyCheckInProgress)
            }
        }
    }
}

/// Fast shell over the full backend-generated recipient workbench.
private struct OverlayRecipientMenu: View {
    @ObservedObject var controller: RecipientCueOverlayController

    var body: some View {
        if controller.recipientRows.isEmpty {
            Button("No recipients loaded") {}.disabled(true)
        } else {
            currentRecipientLine
            Button("Choose Recipient...") {
                controller.showPicker()
            }
            let groups = RecipientQueueLoader.menuGroups(controller.recipientMenuRows)
            let general = groups.general
            let outreach = groups.outreach
            if !general.isEmpty {
                Divider()
                Button("General deliverables") {}.disabled(true)
                ForEach(general) { row in
                    Button(menuLabel(row)) {
                        controller.selectRecipient(row.recipientID)
                    }
                    .disabled(controller.session.isRecording || !row.isRecordable)
                }
            }
            if !outreach.isEmpty {
                Divider()
                ForEach(outreach) { row in
                    Button(menuLabel(row)) {
                        controller.selectRecipient(row.recipientID)
                    }
                    .disabled(controller.session.isRecording || !row.isRecordable)
                }
            }
        }
    }

    private var currentRecipientLine: some View {
        let selected = controller.recipientRows.first {
            $0.recipientID == controller.session.selectedRecipientID
        }
        return Button("Current: \(selected?.recipientName ?? "None")") {}
            .disabled(true)
    }

    private func menuLabel(_ row: RecipientQueueRow) -> String {
        let selected = row.recipientID == controller.session.selectedRecipientID ? "✓ " : ""
        let done = row.isDoneByProjection ? " · done" : ""
        // General deliverables have no meaningful recording order; omit the number.
        let lead = row.kind == .generalDeliverable ? "" : "\(row.recordingOrder). "
        let label = "\(selected)\(lead)\(row.recipientName)\(done)"
        return label.count <= 34 ? label : String(label.prefix(31)) + "..."
    }
}
