import AppKit
import Foundation

private let fm = FileManager.default
private let collectTimes = "08 h 15, 12 h 15 et 18 h 15, heure locale."

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
    var collector: URL { installed.appendingPathComponent("Export.workflow/Contents/Resources/R1 Bridge Collector.app", isDirectory: true) }
    var securePrompt: URL { installed.appendingPathComponent("tunnel/Enregistrer la clé.command") }
    var ready: Bool {
        guard fm.fileExists(atPath: collector.appendingPathComponent("Contents/MacOS/EvenR1Export").path),
              fm.fileExists(atPath: installed.appendingPathComponent("tunnel_r1.py").path),
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
            return CommandResult(code: 1, message: "Installez les outils en ligne de commande d’Apple avec « xcode-select --install » dans Terminal. Rouvrez R1 Bridge une fois l’installation terminée.")
        }
        let result = python("r1.py", ["preparer"], from: runtime)
        guard result.succeeded else { return result }
        do {
            let stamp = try Data(contentsOf: resources.appendingPathComponent("runtime.sha256"))
            try stamp.write(to: installed.appendingPathComponent(".app-payload.sha256"), options: .atomic)
        } catch { return CommandResult(code: 1, message: "Impossible d’enregistrer la version installée. \(error.localizedDescription)") }
        return CommandResult(code: 0, message: "Le Mac est prêt. Ouvrez Even et vérifiez qu’une mesure y est visible, puis testez un export.")
    }

    func collect(_ action: String) -> CommandResult { python("r1.py", [action], from: installed) }
    func tunnel(_ args: [String]) -> CommandResult { python("tunnel_r1.py", args, from: installed) }
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
        appMenu.addItem(withTitle: "À propos de R1 Bridge", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quitter R1 Bridge", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        menu.addItem(appItem)
        let editItem = NSMenuItem()
        let edit = NSMenu(title: "Édition")
        for (title, action, key) in [("Couper", "cut:", "x"), ("Copier", "copy:", "c"), ("Coller", "paste:", "v"), ("Tout sélectionner", "selectAll:", "a")] {
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
            status.stringValue = tab == 0 ? "État de la collecte" : "État du tunnel"
            detail.stringValue = "Dernière tentative vérifiée.\nAucune mesure dans le jeu de test."
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
        window.title = "R1 Bridge"
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
        root.addArrangedSubview(label("R1 Bridge", size: 30, weight: .bold))
        section = NSSegmentedControl(labels: ["Collecte sur le Mac", "Connexion ChatGPT"], trackingMode: .selectOne, target: self, action: #selector(changeSection))
        section.selectedSegment = 0
        root.addArrangedSubview(section)
        for page in [collectPage, tunnelPage] {
            root.addArrangedSubview(page)
            page.widthAnchor.constraint(equalTo: root.widthAnchor).isActive = true
        }
        tunnelPage.isHidden = true

        wrapped(label("Exporter les données de la bague", size: 20, weight: .semibold), in: collectPage)
        wrapped(label("Gardez la R1 appairée à l’iPhone. Sur le Mac, ouvrez l’app Even avec le même compte et vérifiez que les données de la bague y apparaissent.", size: 13, secondary: true), in: collectPage)
        setup = button("Préparer ce Mac", #selector(prepareMac))
        test = button("Tester un export", #selector(tryExport))
        collectPage.addArrangedSubview(row([setup, test]))
        wrapped(label("Créneaux de collecte à " + collectTimes + " L’export programmé attend deux minutes d’inactivité dans une session déverrouillée.", size: 13, secondary: true), in: collectPage)
        schedule = button("Programmer la collecte", #selector(startSchedule))
        stop = button("Arrêter la planification", #selector(stopSchedule))
        collectPage.addArrangedSubview(row([schedule, stop]))
        reveal = button("Afficher le collecteur", #selector(showCollector))
        openArchives = button("Ouvrir les archives", #selector(showArchives))
        collectPage.addArrangedSubview(row([reveal, button("Réglages d’accessibilité", #selector(openAccess)), openArchives]))

        wrapped(label("Relier votre compte personnel", size: 20, weight: .semibold), in: tunnelPage)
        wrapped(label("Le tunnel permet à votre ChatGPT personnel de lire les données depuis ce Mac. Chaque utilisateur configure son propre tunnel OpenAI et sa propre clé.", size: 13, secondary: true), in: tunnelPage)
        connectTunnel = button("Connecter ChatGPT…", #selector(openAssistant))
        tunnelPage.addArrangedSubview(row([connectTunnel, button("Guide de connexion ↗", #selector(openGuide))]))
        wrapped(label("L’assistant s’ouvre dans Terminal. Il vous guide pour installer le client officiel et conserver la clé dans votre Trousseau. Les archives restent sur le Mac.", size: 13, secondary: true), in: tunnelPage)
        enterKey = button("Mettre à jour la clé…", #selector(openKeyPrompt))
        stopTunnel = button("Arrêter le tunnel", #selector(endTunnel))
        tunnelPage.addArrangedSubview(row([enterKey, stopTunnel, button("Gérer mes tunnels ↗", #selector(openTunnels))]))

        let divider = NSBox()
        divider.boxType = .separator
        root.addArrangedSubview(divider)
        divider.widthAnchor.constraint(equalTo: root.widthAnchor).isActive = true
        refresh = button("Actualiser", #selector(refreshStatus))
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
        stop.isEnabled = prepared && fm.fileExists(atPath: bridge.home.appendingPathComponent("Library/LaunchAgents/local.r1bridge.collecte.plist").path)
        connectTunnel.isEnabled = prepared
        enterKey.isEnabled = prepared && fm.isExecutableFile(atPath: bridge.securePrompt.path)
        stopTunnel.isEnabled = prepared && fm.fileExists(atPath: bridge.home.appendingPathComponent("Library/LaunchAgents/local.r1bridge.tunnel.plist").path)
    }

    private func update(_ message: String = "") {
        feedback.stringValue = message
        controls()
        guard bridge.ready else {
            status.stringValue = "Préparation requise"
            detail.stringValue = "Cliquez sur « Préparer ce Mac » dans l’onglet Collecte. Les fichiers seront installés dans le dossier Application Support de votre session."
            return
        }
        let tunnel = isTunnelPage
        busy = true
        controls()
        let bridge = self.bridge
        DispatchQueue.global(qos: .utility).async {
            let result = tunnel ? bridge.tunnel(["etat"]) : bridge.collect("etat")
            DispatchQueue.main.async {
                self.busy = false
                self.status.stringValue = tunnel ? "État du tunnel" : "État de la collecte"
                self.detail.stringValue = result.message.isEmpty ? "Aucun état disponible." : result.message
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
                let message = result.message.isEmpty ? (result.succeeded ? "Opération terminée." : "L’opération a échoué.") : result.message
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
    @objc private func prepareMac() { perform("Préparation en cours…") { $0.prepare() } }
    @objc private func tryExport() { perform("Export en cours…") { $0.collect("essai") } }
    @objc private func startSchedule() { perform("Activation de la collecte…") { $0.collect("planifier") } }
    @objc private func stopSchedule() { perform("Arrêt de la planification…") { $0.collect("arreter") } }
    @objc private func endTunnel() { perform("Arrêt du tunnel…") { $0.tunnel(["arreter"]) } }
    @objc private func showCollector() { NSWorkspace.shared.activateFileViewerSelecting([bridge.collector]) }
    @objc private func showArchives() { NSWorkspace.shared.open(bridge.archives) }
    @objc private func openAccess() { NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")!) }
    @objc private func openTunnels() { NSWorkspace.shared.open(URL(string: "https://platform.openai.com/settings/organization/tunnels")!) }
    @objc private func openGuide() { NSWorkspace.shared.open(URL(string: "https://github.com/daviddemri26/r1-bridge/blob/main/docs/chatgpt.md")!) }
    @objc private func openAssistant() {
        openTerminal(bridge.resources.appendingPathComponent("Connecter ChatGPT.command"))
    }
    @objc private func openKeyPrompt() { openTerminal(bridge.securePrompt) }

    private func openTerminal(_ file: URL) {
        guard fm.isExecutableFile(atPath: file.path) else {
            feedback.stringValue = "L’assistant est introuvable. Réinstallez R1 Bridge depuis l’image disque."
            return
        }
        guard let terminal = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.apple.Terminal") else {
            feedback.stringValue = "Ouvrez l’assistant dans Terminal."
            NSWorkspace.shared.activateFileViewerSelecting([file])
            return
        }
        NSWorkspace.shared.open([file], withApplicationAt: terminal, configuration: NSWorkspace.OpenConfiguration()) { _, error in
            DispatchQueue.main.async {
                self.feedback.stringValue = error?.localizedDescription ?? "Suivez les indications dans Terminal, puis cliquez sur Actualiser."
            }
        }
    }
}

guard let resources = Bundle.main.resourceURL else { exit(1) }
if CommandLine.arguments.contains("--verify-install") {
    let scratch = fm.temporaryDirectory.appendingPathComponent("r1bridge-verification-" + UUID().uuidString)
    do {
        try fm.createDirectory(at: scratch, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        defer { try? fm.removeItem(at: scratch) }
        let testBridge = Bridge(resources: resources, home: scratch)
        let result = testBridge.prepare()
        guard result.succeeded, testBridge.ready, fm.fileExists(atPath: testBridge.archives.path) else { fputs("Échec du test d’installation : \(result.message)\n", stderr); exit(1) }
        let report = testBridge.collect("etat")
        guard report.succeeded, fm.isExecutableFile(atPath: testBridge.collector.appendingPathComponent("Contents/MacOS/EvenR1Export").path) else { exit(1) }
        guard fm.isExecutableFile(atPath: resources.appendingPathComponent("Connecter ChatGPT.command").path) else { exit(1) }
        let app = NSApplication.shared
        app.setActivationPolicy(.prohibited)
        let check = WindowController(testBridge)
        guard check.checkLayout() else { fputs("Le contrôle des vues de l’app a échoué.\n", stderr); exit(1) }
        print("Installation, lecture d’état et vues Collecte/ChatGPT vérifiées dans un dossier temporaire.")
    } catch { fputs("Impossible de tester le paquet.\n", stderr); exit(1) }
} else {
    let app = NSApplication.shared
    let bridge = Bridge(resources: resources, home: FileManager.default.homeDirectoryForCurrentUser)
    let controller = WindowController(bridge)
    app.setActivationPolicy(.regular)
    app.delegate = controller
    withExtendedLifetime(controller) { app.run() }
}
