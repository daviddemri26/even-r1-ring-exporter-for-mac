import AppKit
import Foundation

private let fm = FileManager.default
private let collectTimes = "8:15 AM, 12:15 PM, and 6:15 PM local time."

private struct CommandResult {
    let code: Int32
    let message: String
    var succeeded: Bool { code == 0 }
}

private struct Bridge {
    let resources: URL
    let home: URL
    var runtime: URL { resources.appendingPathComponent("runtime", isDirectory: true) }
    var installed: URL { home.appendingPathComponent("Library/Application Support/R1 Bridge", isDirectory: true) }
    var archives: URL { installed.appendingPathComponent("Archives", isDirectory: true) }
    var collector: URL { installed.appendingPathComponent("Export.workflow/Contents/Resources/Even R1 Ring Collector for Mac.app", isDirectory: true) }
    var securePrompt: URL { installed.appendingPathComponent("tunnel/Store Key.command") }
    var ready: Bool {
        guard fm.fileExists(atPath: collector.appendingPathComponent("Contents/MacOS/EvenR1Export").path),
              fm.fileExists(atPath: installed.appendingPathComponent("tunnel.py").path),
              let stamp = try? Data(contentsOf: resources.appendingPathComponent("runtime.sha256")),
              let active = try? Data(contentsOf: installed.appendingPathComponent(".app-payload.sha256")) else { return false }
        return stamp == active
    }

    func command(_ executable: String, _ arguments: [String]) -> CommandResult {
        let task = Process()
        let output = Pipe()
        task.executableURL = URL(fileURLWithPath: executable)
        task.arguments = arguments
        task.environment = ["HOME": home.path, "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LC_CTYPE": "UTF-8"]
        task.standardInput = FileHandle.nullDevice
        task.standardOutput = output
        task.standardError = output
        do { try task.run() } catch { return CommandResult(code: 1, message: error.localizedDescription) }
        let bytes = output.fileHandleForReading.readDataToEndOfFile()
        task.waitUntilExit()
        let message = String(decoding: bytes, as: UTF8.self).trimmingCharacters(in: .whitespacesAndNewlines)
        return CommandResult(code: task.terminationStatus, message: message)
    }

    func python(_ script: String, _ args: [String], from directory: URL) -> CommandResult {
        command("/usr/bin/python3", ["-B", directory.appendingPathComponent(script).path] + args)
    }

    func prepare() -> CommandResult {
        guard command("/usr/bin/xcode-select", ["-p"]).succeeded,
              command("/usr/bin/python3", ["-c", "import sys; sys.exit(sys.version_info < (3,9))"]).succeeded else {
            return CommandResult(code: 1, message: "Run xcode-select --install in Terminal to install the Apple Command Line Tools. Reopen Even R1 Ring Exporter for Mac when installation finishes.")
        }
        let result = python("r1.py", ["prepare"], from: runtime)
        guard result.succeeded else { return result }
        do {
            let stamp = try Data(contentsOf: resources.appendingPathComponent("runtime.sha256"))
            try stamp.write(to: installed.appendingPathComponent(".app-payload.sha256"), options: .atomic)
        } catch { return CommandResult(code: 1, message: "Could not save the installed version. \(error.localizedDescription)") }
        return CommandResult(code: 0, message: "This Mac is ready. Open Even, check that a ring reading is visible, then test an export.")
    }

    func collect(_ action: String) -> CommandResult { python("r1.py", [action], from: installed) }
    func tunnel(_ args: [String]) -> CommandResult { python("tunnel.py", args, from: installed) }
}

private func label(_ text: String, size: CGFloat, weight: NSFont.Weight = .regular, secondary: Bool = false) -> NSTextField {
    let field = NSTextField(wrappingLabelWithString: text)
    field.font = NSFont.systemFont(ofSize: size, weight: weight)
    field.textColor = secondary ? .secondaryLabelColor : .labelColor
    field.setContentCompressionResistancePriority(.required, for: .vertical)
    return field
}

private func column(_ spacing: CGFloat) -> NSStackView {
    let view = NSStackView()
    view.orientation = .vertical
    view.alignment = .leading
    view.spacing = spacing
    return view
}

private func row(_ views: [NSView]) -> NSStackView {
    let view = NSStackView(views: views)
    view.spacing = 8
    view.alignment = .centerY
    return view
}

private final class WindowController: NSObject, NSApplicationDelegate {
    let bridge: Bridge
    let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 705, height: 625),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable],
                          backing: .buffered, defer: false)
    private let collectPage = column(14)
    private let tunnelPage = column(14)
    private let status = label("", size: 14, weight: .semibold)
    private let detail = label("", size: 13)
    private let feedback = label("", size: 13, secondary: true)
    private var buttons: [NSButton] = []
    private var busy = false
    private var section: NSSegmentedControl!
    private var setup: NSButton!
    private var test: NSButton!
    private var schedule: NSButton!
    private var stop: NSButton!
    private var reveal: NSButton!
    private var openArchives: NSButton!
    private var refresh: NSButton!
    private var connectTunnel: NSButton!
    private var enterKey: NSButton!
    private var stopTunnel: NSButton!

    init(_ bridge: Bridge) { self.bridge = bridge }

    func applicationDidFinishLaunching(_ notification: Notification) {
        configureWindow()
        let menu = NSMenu()
        let appItem = NSMenuItem()
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "About Even R1 Ring Exporter for Mac", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quit Even R1 Ring Exporter for Mac", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        menu.addItem(appItem)
        let editItem = NSMenuItem()
        let edit = NSMenu(title: "Edit")
        for (title, action, key) in [("Cut", "cut:", "x"), ("Copy", "copy:", "c"), ("Paste", "paste:", "v"), ("Select All", "selectAll:", "a")] {
            edit.addItem(withTitle: title, action: NSSelectorFromString(action), keyEquivalent: key)
        }
        editItem.submenu = edit
        menu.addItem(editItem)
        NSApp.mainMenu = menu
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        update()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    // Exercise both navigation paths without opening a window or changing settings.
    func checkLayout() -> Bool {
        configureWindow()
        for tab in 0...1 {
            section.selectedSegment = tab
            collectPage.isHidden = tab != 0
            tunnelPage.isHidden = tab != 1
            controls()
            status.stringValue = tab == 0 ? "Collection status" : "Tunnel status"
            detail.stringValue = "Last attempt verified.\nThe test dataset contains no readings."
            guard let content = window.contentView else { return false }
            content.layoutSubtreeIfNeeded()
            let primary = tab == 0 ? test! : connectTunnel!
            guard primary.isEnabled, primary.window === window,
                  content.bounds.contains(primary.convert(primary.bounds, to: content)),
                  content.bounds.contains(detail.convert(detail.bounds, to: content)) else { return false }
        }
        return true
    }

    private func button(_ title: String, _ action: Selector) -> NSButton {
        let b = NSButton(title: title, target: self, action: action)
        b.bezelStyle = .rounded
        buttons.append(b)
        return b
    }

    private func wrapped(_ field: NSTextField, in stack: NSStackView) {
        stack.addArrangedSubview(field)
        field.widthAnchor.constraint(equalTo: stack.widthAnchor).isActive = true
    }

    private func configureWindow() {
        window.title = "Even R1 Ring Exporter for Mac"
        window.minSize = NSSize(width: 670, height: 605)
        let root = column(16)
        root.translatesAutoresizingMaskIntoConstraints = false
        let content = window.contentView!
        content.addSubview(root)
        NSLayoutConstraint.activate([
            root.leadingAnchor.constraint(equalTo: content.leadingAnchor, constant: 28),
            root.trailingAnchor.constraint(equalTo: content.trailingAnchor, constant: -28),
            root.topAnchor.constraint(equalTo: content.topAnchor, constant: 22),
            root.bottomAnchor.constraint(lessThanOrEqualTo: content.bottomAnchor, constant: -18)
        ])
        root.addArrangedSubview(label("Even R1 Ring Exporter for Mac", size: 30, weight: .bold))
        section = NSSegmentedControl(labels: ["Mac Collection", "ChatGPT Connection"], trackingMode: .selectOne, target: self, action: #selector(changeSection))
        section.selectedSegment = 0
        root.addArrangedSubview(section)
        for page in [collectPage, tunnelPage] {
            root.addArrangedSubview(page)
            page.widthAnchor.constraint(equalTo: root.widthAnchor).isActive = true
        }
        tunnelPage.isHidden = true

        wrapped(label("Export your ring data", size: 20, weight: .semibold), in: collectPage)
        wrapped(label("Keep your R1 paired with your iPhone. Open Even on your Mac, sign in to the same account, and confirm that you can see your ring data.", size: 13, secondary: true), in: collectPage)
        setup = button("Set Up This Mac", #selector(prepareMac))
        test = button("Test an Export", #selector(tryExport))
        collectPage.addArrangedSubview(row([setup, test, button("Installation Guide ↗", #selector(openInstallGuide))]))
        wrapped(label("Collection windows start at " + collectTimes + " Scheduled exports wait until your Mac is unlocked and has been idle for two minutes.", size: 13, secondary: true), in: collectPage)
        schedule = button("Schedule Collection", #selector(startSchedule))
        stop = button("Stop Schedule", #selector(stopSchedule))
        collectPage.addArrangedSubview(row([schedule, stop]))
        reveal = button("Show Collector", #selector(showCollector))
        openArchives = button("Open Archives", #selector(showArchives))
        collectPage.addArrangedSubview(row([reveal, button("Accessibility Settings", #selector(openAccess)), openArchives]))

        wrapped(label("Connect your ChatGPT account", size: 20, weight: .semibold), in: tunnelPage)
        wrapped(label("Your ChatGPT account can use a private tunnel to read data from this Mac. Set it up with your own OpenAI tunnel and key.", size: 13, secondary: true), in: tunnelPage)
        connectTunnel = button("Connect Even R1 Ring to ChatGPT…", #selector(openAssistant))
        tunnelPage.addArrangedSubview(row([connectTunnel, button("Connection Guide ↗", #selector(openGuide))]))
        wrapped(label("The assistant opens in Terminal. It installs the official client and stores your key in the macOS Keychain. Your ZIP archives stay on this Mac.", size: 13, secondary: true), in: tunnelPage)
        enterKey = button("Update Key…", #selector(openKeyPrompt))
        stopTunnel = button("Stop Tunnel", #selector(endTunnel))
        tunnelPage.addArrangedSubview(row([enterKey, stopTunnel, button("Manage Tunnels ↗", #selector(openTunnels))]))

        let divider = NSBox()
        divider.boxType = .separator
        root.addArrangedSubview(divider)
        divider.widthAnchor.constraint(equalTo: root.widthAnchor).isActive = true
        refresh = button("Refresh", #selector(refreshStatus))
        root.addArrangedSubview(row([status, refresh]))
        detail.isSelectable = true
        wrapped(detail, in: root)
        feedback.isSelectable = true
        wrapped(feedback, in: root)
    }

    private var isTunnelPage: Bool { section.selectedSegment == 1 }

    private func controls() {
        buttons.forEach { $0.isEnabled = !busy }
        section.isEnabled = !busy
        guard !busy else { return }
        let prepared = bridge.ready
        setup.isHidden = prepared
        [test, schedule, reveal, openArchives].forEach { $0?.isEnabled = prepared }
        stop.isEnabled = prepared && fm.fileExists(atPath: bridge.home.appendingPathComponent("Library/LaunchAgents/local.r1bridge.collection.plist").path)
        connectTunnel.isEnabled = prepared
        enterKey.isEnabled = prepared && fm.isExecutableFile(atPath: bridge.securePrompt.path)
        stopTunnel.isEnabled = prepared && fm.fileExists(atPath: bridge.home.appendingPathComponent("Library/LaunchAgents/local.r1bridge.tunnel.plist").path)
    }

    private func update(_ message: String = "") {
        feedback.stringValue = message
        controls()
        guard bridge.ready else {
            status.stringValue = "Set up this Mac"
            detail.stringValue = "Select Set Up This Mac on the Mac Collection tab to install the collector in your user account."
            return
        }
        let tunnel = isTunnelPage
        busy = true
        controls()
        let bridge = self.bridge
        DispatchQueue.global(qos: .utility).async {
            let result = tunnel ? bridge.tunnel(["status"]) : bridge.collect("status")
            DispatchQueue.main.async {
                self.busy = false
                self.status.stringValue = tunnel ? "Tunnel status" : "Collection status"
                self.detail.stringValue = result.message.isEmpty ? "Status unavailable." : result.message
                self.controls()
            }
        }
    }

    private func perform(_ activity: String, _ block: @escaping (Bridge) -> CommandResult) {
        guard !busy else { return }
        busy = true
        status.stringValue = activity
        feedback.stringValue = ""
        controls()
        let bridge = self.bridge
        DispatchQueue.global(qos: .userInitiated).async {
            let result = block(bridge)
            DispatchQueue.main.async {
                self.busy = false
                let message = result.message.isEmpty ? (result.succeeded ? "Done." : "The operation failed.") : result.message
                self.update(message)
            }
        }
    }

    @objc private func changeSection() {
        collectPage.isHidden = isTunnelPage
        tunnelPage.isHidden = !isTunnelPage
        update()
    }
    @objc private func refreshStatus() { update() }
    @objc private func prepareMac() { perform("Preparing this Mac…") { $0.prepare() } }
    @objc private func tryExport() { perform("Exporting…") { $0.collect("export") } }
    @objc private func startSchedule() { perform("Scheduling collection…") { $0.collect("schedule") } }
    @objc private func stopSchedule() { perform("Stopping the schedule…") { $0.collect("stop") } }
    @objc private func endTunnel() { perform("Stopping the tunnel…") { $0.tunnel(["stop"]) } }
    @objc private func showCollector() { NSWorkspace.shared.activateFileViewerSelecting([bridge.collector]) }
    @objc private func showArchives() { NSWorkspace.shared.open(bridge.archives) }
    @objc private func openAccess() { NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")!) }
    @objc private func openTunnels() { NSWorkspace.shared.open(URL(string: "https://platform.openai.com/settings/organization/tunnels")!) }
    @objc private func openInstallGuide() { NSWorkspace.shared.open(URL(string: "https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/install/")!) }
    @objc private func openGuide() { NSWorkspace.shared.open(URL(string: "https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/guides/chatgpt/")!) }
    @objc private func openAssistant() {
        openTerminal(bridge.resources.appendingPathComponent("Connect Even R1 Ring to ChatGPT.command"))
    }
    @objc private func openKeyPrompt() { openTerminal(bridge.securePrompt) }

    private func openTerminal(_ file: URL) {
        guard fm.isExecutableFile(atPath: file.path) else {
            feedback.stringValue = "The setup assistant is missing. Reinstall Even R1 Ring Exporter for Mac from the disk image."
            return
        }
        guard let terminal = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.apple.Terminal") else {
            feedback.stringValue = "Open the setup assistant in Terminal."
            NSWorkspace.shared.activateFileViewerSelecting([file])
            return
        }
        NSWorkspace.shared.open([file], withApplicationAt: terminal, configuration: NSWorkspace.OpenConfiguration()) { _, error in
            DispatchQueue.main.async {
                self.feedback.stringValue = error?.localizedDescription ?? "Follow the steps in Terminal, then click Refresh."
            }
        }
    }
}

guard let resources = Bundle.main.resourceURL else { exit(1) }
if CommandLine.arguments.contains("--verify-install") {
    let scratch = fm.temporaryDirectory.appendingPathComponent("even-r1-ring-exporter-test-" + UUID().uuidString)
    do {
        try fm.createDirectory(at: scratch, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        defer { try? fm.removeItem(at: scratch) }
        let testBridge = Bridge(resources: resources, home: scratch)
        let result = testBridge.prepare()
        guard result.succeeded, testBridge.ready, fm.fileExists(atPath: testBridge.archives.path) else { fputs("Installation test failed. \(result.message)\n", stderr); exit(1) }
        let report = testBridge.collect("status")
        guard report.succeeded, fm.isExecutableFile(atPath: testBridge.collector.appendingPathComponent("Contents/MacOS/EvenR1Export").path) else { exit(1) }
        guard fm.isExecutableFile(atPath: resources.appendingPathComponent("Connect Even R1 Ring to ChatGPT.command").path) else { exit(1) }
        let app = NSApplication.shared
        app.setActivationPolicy(.prohibited)
        let check = WindowController(testBridge)
        guard check.checkLayout() else { fputs("App view verification failed.\n", stderr); exit(1) }
        print("Verified installation, status, and both app views in a temporary user folder.")
    } catch { fputs("Package verification failed.\n", stderr); exit(1) }
} else {
    let app = NSApplication.shared
    let bridge = Bridge(resources: resources, home: FileManager.default.homeDirectoryForCurrentUser)
    let controller = WindowController(bridge)
    app.setActivationPolicy(.regular)
    app.delegate = controller
    withExtendedLifetime(controller) { app.run() }
}
