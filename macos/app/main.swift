import AppKit
import Foundation
import CoreImage

private let fm = FileManager.default

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
    private var installedStamp: URL { installed.appendingPathComponent(".app-payload.sha256") }
    private var bundledStamp: URL { resources.appendingPathComponent("runtime.sha256") }
    var ready: Bool {
        guard let stamp = try? Data(contentsOf: bundledStamp),
              let active = try? Data(contentsOf: installedStamp),
              stamp == active, fm.isReadableFile(atPath: runtime.appendingPathComponent("r1.py").path) else { return false }

        // Check packaged files only. Archives, settings and other user files live alongside them.
        let keys: Set<URLResourceKey> = [.isRegularFileKey, .isExecutableKey]
        var reachedEnd = true
        guard let files = fm.enumerator(at: runtime, includingPropertiesForKeys: Array(keys),
                                        options: [.skipsHiddenFiles, .producesRelativePathURLs], errorHandler: { _, _ in
            reachedEnd = false
            return false
        }) else { return false }
        for case let source as URL in files {
            guard let info = try? source.resourceValues(forKeys: keys) else { return false }
            guard info.isRegularFile == true else { continue }
            let target = installed.appendingPathComponent(source.relativePath)
            guard fm.contentsEqual(atPath: source.path, andPath: target.path),
                  info.isExecutable != true || fm.isExecutableFile(atPath: target.path) else { return false }
        }
        return reachedEnd
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
        do {
            let stamp = try Data(contentsOf: bundledStamp)
            // A failed migration must remain retryable even if all program files were replaced.
            if fm.fileExists(atPath: installedStamp.path) { try fm.removeItem(at: installedStamp) }
            let result = python("r1.py", ["prepare"], from: runtime)
            guard result.succeeded else { return result }
            try stamp.write(to: installedStamp, options: .atomic)
        } catch { return CommandResult(code: 1, message: "Could not update the installed version. \(error.localizedDescription)") }
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
    private let collectPage = column(10)
    private let tunnelPage = column(10)
    private let collectionOptions = column(8)
    private let connectionOptions = column(8)
    private let status = label("", size: 14, weight: .semibold)
    private let detail = label("", size: 13)
    private let feedback = label("", size: 13, secondary: true)
    private var buttons: [NSButton] = []
    private var busy = false
    private var prepared = false
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
    private var collectionToggle: NSButton!
    private var connectionToggle: NSButton!

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
        guard let content = window.contentView else { return false }
        prepared = bridge.ready
        for tab in 0...1 {
            section.selectedSegment = tab
            collectPage.isHidden = tab != 0
            tunnelPage.isHidden = tab != 1
            controls()
            status.stringValue = tab == 0 ? "Collection status" : "Tunnel status"
            detail.stringValue = prepared
                ? "Next scheduled check at 12:15 PM.\nLast export succeeded.\nThe test dataset contains no readings."
                : "Select Set Up This Mac on the Mac Collection tab to install the collector in your user account."
            let primary = tab == 0 && !prepared ? setup! : (tab == 0 ? test! : connectTunnel!)
            let toggle = tab == 0 ? collectionToggle! : connectionToggle!
            let options = tab == 0 ? collectionOptions : connectionOptions
            let secondary = tab == 0 ? openArchives! : enterKey!
            guard options.isHidden, toggle.isEnabled, setup.isHidden == prepared,
                  test.isEnabled == prepared, schedule.isEnabled == prepared, connectTunnel.isEnabled == prepared else { return false }
            for state in 0...2 {
                if state > 0 { toggle.performClick(nil) }
                let expanded = state == 1
                content.layoutSubtreeIfNeeded()
                guard options.isHidden == !expanded, secondary.isHiddenOrHasHiddenAncestor == !expanded else { return false }
                var visible: [NSView] = [primary, toggle, refresh, detail]
                if expanded { visible.append(secondary) }
                guard visible.allSatisfy({ !$0.isHiddenOrHasHiddenAncestor && $0.window === window &&
                    content.bounds.contains($0.convert($0.bounds, to: content)) }) else { return false }
            }
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
        let root = column(12)
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

        wrapped(label("Collect your ring readings", size: 20, weight: .semibold), in: collectPage)
        wrapped(label("Sign in to Even on this Mac with your iPhone’s Even account. Once you see a reading, test an export. If macOS asks, allow Even R1 Ring Collector for Mac.", size: 13), in: collectPage)
        setup = button("Set Up This Mac", #selector(prepareMac))
        test = button("Test an Export", #selector(tryExport))
        schedule = button("Schedule Collection", #selector(startSchedule))
        collectPage.addArrangedSubview(row([setup, test, schedule, button("Pair iPhone", #selector(pairPhone))]))
        wrapped(label("Checks start at 5:15 AM, 8:15 AM, 12:15 PM, 6:15 PM and 11:15 PM local time. Your Mac exports when it is unlocked and idle for two minutes.", size: 13, secondary: true), in: collectPage)
        collectionToggle = button("Show Collection Options", #selector(toggleCollectionOptions))
        collectPage.addArrangedSubview(row([collectionToggle, button("Installation Guide ↗", #selector(openInstallGuide))]))
        stop = button("Stop Schedule", #selector(stopSchedule))
        reveal = button("Show Collector", #selector(showCollector))
        openArchives = button("Open Archives", #selector(showArchives))
        collectionOptions.addArrangedSubview(row([button("Accessibility Settings", #selector(openAccess)), reveal, openArchives, stop]))
        collectPage.addArrangedSubview(collectionOptions)
        collectionOptions.isHidden = true

        wrapped(label("Ask ChatGPT about your ring", size: 20, weight: .semibold), in: tunnelPage)
        wrapped(label("Connect your own ChatGPT account to read the latest export from this Mac. Keep your Mac awake and online when you ask a question.", size: 13), in: tunnelPage)
        connectTunnel = button("Connect Even R1 Ring to ChatGPT…", #selector(openAssistant))
        tunnelPage.addArrangedSubview(row([connectTunnel, button("Connection Guide ↗", #selector(openGuide))]))
        wrapped(label("The setup assistant opens in Terminal. It stores your dedicated OpenAI key in the Mac Keychain.", size: 13, secondary: true), in: tunnelPage)
        connectionToggle = button("Show Connection Options", #selector(toggleConnectionOptions))
        tunnelPage.addArrangedSubview(connectionToggle)
        enterKey = button("Update Key…", #selector(openKeyPrompt))
        stopTunnel = button("Stop Tunnel", #selector(endTunnel))
        connectionOptions.addArrangedSubview(row([enterKey, stopTunnel, button("Manage Tunnels ↗", #selector(openTunnels))]))
        tunnelPage.addArrangedSubview(connectionOptions)
        connectionOptions.isHidden = true

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

    @objc private func toggleCollectionOptions() {
        collectionOptions.isHidden.toggle()
        collectionToggle.title = collectionOptions.isHidden ? "Show Collection Options" : "Hide Collection Options"
    }

    @objc private func toggleConnectionOptions() {
        connectionOptions.isHidden.toggle()
        connectionToggle.title = connectionOptions.isHidden ? "Show Connection Options" : "Hide Connection Options"
    }

    private func controls() {
        buttons.forEach { $0.isEnabled = !busy }
        section.isEnabled = !busy
        guard !busy else { return }
        setup.isHidden = prepared
        [test, schedule, reveal, openArchives].forEach { $0?.isEnabled = prepared }
        stop.isEnabled = prepared && fm.fileExists(atPath: bridge.home.appendingPathComponent("Library/LaunchAgents/local.r1bridge.collection.plist").path)
        connectTunnel.isEnabled = prepared
        enterKey.isEnabled = prepared && fm.isExecutableFile(atPath: bridge.securePrompt.path)
        stopTunnel.isEnabled = prepared && fm.fileExists(atPath: bridge.home.appendingPathComponent("Library/LaunchAgents/local.r1bridge.tunnel.plist").path)
    }

    private func update(_ message: String = "") {
        feedback.stringValue = message
        let tunnel = isTunnelPage
        busy = true
        controls()
        let bridge = self.bridge
        DispatchQueue.global(qos: .utility).async {
            let result: CommandResult?
            if bridge.ready {
                result = tunnel ? bridge.tunnel(["status"]) : bridge.collect("status")
            } else {
                result = nil
            }
            DispatchQueue.main.async {
                self.prepared = result != nil
                self.busy = false
                if let result = result {
                    self.status.stringValue = tunnel ? "Tunnel status" : "Collection status"
                    self.detail.stringValue = result.message.isEmpty ? "Status unavailable." : result.message
                } else {
                    self.status.stringValue = "Set up this Mac"
                    self.detail.stringValue = "Select Set Up This Mac on the Mac Collection tab to install the collector in your user account."
                }
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
                if !result.succeeded && !self.isTunnelPage && self.collectionOptions.isHidden {
                    self.toggleCollectionOptions()
                }
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
    @objc private func pairPhone() {
        PhoneWindow.present(in: window, home: bridge.home) { [weak self] in self?.feedback.stringValue = $0 }
    }
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
if CommandLine.arguments.contains("--serve-iphone") {
    do {
        let base = try PhoneWindow.directory(home: fm.homeDirectoryForCurrentUser)
        let server = PhoneServer(store: .keychain(base: base), resources: resources)
        server.start()
        withExtendedLifetime(server) { dispatchMain() }
    } catch { exit(1) }
} else if CommandLine.arguments.contains("--verify-install") {
    let scratch = fm.temporaryDirectory.appendingPathComponent("even-r1-ring-exporter-test-" + UUID().uuidString)
    func require(_ condition: Bool, _ failure: String) throws {
        if !condition {
            throw NSError(domain: "EvenR1InstallTest", code: 1, userInfo: [NSLocalizedDescriptionKey: failure])
        }
    }
    do {
        try fm.createDirectory(at: scratch, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        defer { try? fm.removeItem(at: scratch) }
        try verifyPhonePairing(base: scratch)
        let example = PairingQR(v: 1, service: "Synthetic-Mac", secret: Data(repeating: 1, count: 32),
                                code: Data(repeating: 2, count: 32))
        let rendered = try PhoneWindow.qrImage(for: example)
        let detector = CIDetector(ofType: CIDetectorTypeQRCode, context: nil, options: [CIDetectorAccuracy: CIDetectorAccuracyHigh])
        let feature = detector?.features(in: CIImage(cgImage: rendered)).first as? CIQRCodeFeature
        let decoded = try JSONDecoder().decode(PairingQR.self, from: Data((feature?.messageString ?? "").utf8))
        try require(decoded.v == 1 && decoded.service == example.service && decoded.secret == example.secret && decoded.code == example.code,
                    "The scanner could not recover the pairing code from the rendered QR image.")
        let testBridge = Bridge(resources: resources, home: scratch)
        let app = NSApplication.shared
        app.setActivationPolicy(.prohibited)
        try require(WindowController(testBridge).checkLayout(), "First launch view verification failed.")
        let result = testBridge.prepare()
        try require(result.succeeded && testBridge.ready && fm.fileExists(atPath: testBridge.archives.path),
                    "Installation test failed. \(result.message)")
        let report = testBridge.collect("status")
        try require(report.succeeded, "Collection status failed. \(report.message)")
        try require(fm.isExecutableFile(atPath: resources.appendingPathComponent("Connect Even R1 Ring to ChatGPT.command").path),
                    "The connection assistant is missing or cannot run.")
        try require(WindowController(testBridge).checkLayout(), "Installed app view verification failed.")

        let collectorExecutable = testBridge.collector.appendingPathComponent("Contents/MacOS/EvenR1Export")
        try fm.setAttributes([.posixPermissions: 0o600], ofItemAtPath: collectorExecutable.path)
        try require(!testBridge.ready, "A collector without execute permission was reported as ready.")
        try fm.setAttributes([.posixPermissions: 0o755], ofItemAtPath: collectorExecutable.path)
        try require(testBridge.ready, "The executable permission was not restored.")
        try fm.removeItem(at: testBridge.installed.appendingPathComponent("r1.py"))
        try require(!testBridge.ready, "A missing runtime module was reported as ready.")
        let existingArchive = testBridge.archives.appendingPathComponent("synthetic-archive.txt")
        let archiveBytes = Data("Synthetic archive fixture".utf8)
        try archiveBytes.write(to: existingArchive)
        let invalidDatabase = testBridge.installed.appendingPathComponent("collection.sqlite3")
        try Data("Synthetic invalid database".utf8).write(to: invalidDatabase)
        let failedRepair = testBridge.prepare()
        try require(!failedRepair.succeeded && !testBridge.ready, "A failed migration was reported as ready.")
        try fm.removeItem(at: invalidDatabase)
        let repaired = testBridge.prepare()
        try require(repaired.succeeded && testBridge.ready && testBridge.collect("status").succeeded,
                    "Runtime repair failed. \(repaired.message)")
        try require(try Data(contentsOf: existingArchive) == archiveBytes, "Runtime repair changed the existing archive.")
        print("Verified one-time pairing, key rotation, access revocation, first launch, installation, both tabs, status and repair of a damaged runtime in a temporary user folder.")
    } catch { fputs("Package verification failed. \(error.localizedDescription)\n", stderr); exit(1) }
} else {
    let app = NSApplication.shared
    let bridge = Bridge(resources: resources, home: FileManager.default.homeDirectoryForCurrentUser)
    let controller = WindowController(bridge)
    app.setActivationPolicy(.regular)
    app.delegate = controller
    withExtendedLifetime(controller) { app.run() }
}
