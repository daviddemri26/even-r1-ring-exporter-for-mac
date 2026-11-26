import AppKit
import ApplicationServices
import Foundation

// Les seuls messages renvoyés à Automator sont les résultats constants de cette liste.
enum ExportError: String, Error {
    case accessibility = "ACCESSIBILITY"
    case unavailable = "EVEN_UNAVAILABLE"
    case navigation = "EVEN_NAVIGATION"
    case sharing = "EVEN_SHARE"
    case timeout = "EVEN_TIMEOUT"
    case importFailed = "EVEN_IMPORT"
    case appData = "APP_DATA_PERMISSION"
}

let evenIdentifier = "com.even.sg"
let support = FileManager.default.homeDirectoryForCurrentUser
    .appendingPathComponent("Library/Application Support/R1 Bridge", isDirectory: true)

func attribute<T>(_ node: AXUIElement, _ key: String) -> T? {
    var value: CFTypeRef?
    guard AXUIElementCopyAttributeValue(node, key as CFString, &value) == .success else { return nil }
    return value as? T
}

func windows(_ app: AXUIElement) -> [AXUIElement] {
    var owner: pid_t = 0
    guard AXUIElementGetPid(app, &owner) == .success else { return [] }
    let listed: [AXUIElement] = attribute(app, kAXWindowsAttribute) ?? []
    var candidates: [AXUIElement] = []
    for key in [kAXFocusedWindowAttribute, kAXMainWindowAttribute] {
        var raw: CFTypeRef?
        guard AXUIElementCopyAttributeValue(app, key as CFString, &raw) == .success,
              let raw = raw, CFGetTypeID(raw) == AXUIElementGetTypeID() else { continue }
        candidates.append(raw as! AXUIElement)
    }
    var seen = Set<AXUIElement>()
    return (candidates + listed).filter { window in
        var pid: pid_t = 0
        let role: String? = attribute(window, kAXRoleAttribute)
        return role == kAXWindowRole && AXUIElementGetPid(window, &pid) == .success
            && pid == owner && seen.insert(window).inserted
    }
}

// Recherche limitée aux fenêtres du processus Even ou à la feuille qu’il héberge.
func first(_ roots: [AXUIElement], where matches: (AXUIElement) -> Bool) -> AXUIElement? {
    var pending = roots
    var seen = Set<AXUIElement>()
    var offset = 0
    while offset < pending.count && seen.count < 1800 {
        let node = pending[offset]
        offset += 1
        guard seen.insert(node).inserted else { continue }
        if matches(node) { return node }
        let children: [AXUIElement] = attribute(node, kAXChildrenAttribute) ?? []
        pending.append(contentsOf: children)
    }
    return nil
}

func namedID(_ id: String, in roots: [AXUIElement]) -> AXUIElement? {
    first(roots) { element in
        let candidate: String? = attribute(element, kAXIdentifierAttribute)
        return candidate == id
    }
}

func waitFor<T>(_ seconds: TimeInterval, _ check: () -> T?) -> T? {
    let until = ProcessInfo.processInfo.systemUptime + seconds
    repeat {
        if let result = check() { return result }
        RunLoop.current.run(until: Date(timeIntervalSinceNow: 0.3))
    } while ProcessInfo.processInfo.systemUptime < until
    return nil
}

func accessibleEven() throws -> AXUIElement {
    let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
    guard AXIsProcessTrustedWithOptions(options) else { throw ExportError.accessibility }
    var running = NSRunningApplication.runningApplications(withBundleIdentifier: evenIdentifier).first
    if running == nil {
        let space = NSWorkspace.shared
        guard let url = space.urlForApplication(withBundleIdentifier: evenIdentifier) else {
            throw ExportError.unavailable
        }
        let config = NSWorkspace.OpenConfiguration()
        config.activates = true
        space.openApplication(at: url, configuration: config) { _, _ in }
        running = waitFor(18) { NSRunningApplication.runningApplications(withBundleIdentifier: evenIdentifier).first }
    }
    guard let running = running else { throw ExportError.unavailable }
    running.activate(options: [])
    let app = AXUIElementCreateApplication(running.processIdentifier)
    AXUIElementSetMessagingTimeout(app, 1.5)
    guard waitFor(18, { windows(app).isEmpty ? nil : true }) != nil else { throw ExportError.unavailable }
    return app
}

func press(_ element: AXUIElement) throws {
    guard AXUIElementPerformAction(element, kAXPressAction as CFString) == .success else {
        throw ExportError.navigation
    }
}

func sendEscape(to element: AXUIElement) -> Bool {
    var pid: pid_t = 0
    guard AXUIElementGetPid(element, &pid) == .success,
          NSRunningApplication(processIdentifier: pid)?.bundleIdentifier == evenIdentifier,
          let down = CGEvent(keyboardEventSource: nil, virtualKey: 53, keyDown: true),
          let up = CGEvent(keyboardEventSource: nil, virtualKey: 53, keyDown: false) else { return false }
    down.postToPid(pid)
    up.postToPid(pid)
    return true
}

func sharingPanel(in app: AXUIElement) -> AXUIElement? {
    let roots = windows(app)
    return first(roots) { element in
        let panelRole: String? = attribute(element, kAXRoleAttribute)
        guard panelRole == "AXPopover" else { return false }
        func hasButton(_ labels: Set<String>) -> Bool {
            first([element]) { button in
                let buttonRole: String? = attribute(button, kAXRoleAttribute)
                guard buttonRole == kAXButtonRole else { return false }
                for key in [kAXTitleAttribute, kAXDescriptionAttribute, kAXValueAttribute] {
                    if let value: String = attribute(button, key), labels.contains(value) { return true }
                }
                return false
            } != nil
        }
        return hasButton(["Save", "Enregistrer"]) && hasButton(["Copy", "Copier"])
    }
}

func closeSharing(_ app: AXUIElement, panel: AXUIElement) throws {
    _ = AXUIElementPerformAction(panel, kAXCancelAction as CFString)
    if waitFor(1, { sharingPanel(in: app) == nil ? true : nil }) != nil { return }
    guard let current = sharingPanel(in: app), CFEqual(current, panel),
          sendEscape(to: current) else {
        throw ExportError.sharing
    }
    guard waitFor(3, { sharingPanel(in: app) == nil ? true : nil }) != nil else {
        throw ExportError.sharing
    }
}

func backButton(in roots: [AXUIElement]) -> AXUIElement? {
    let known = ["health.detail.back", "health.steps.back", "dashboard.back"]
    if let back = first(roots, where: { node in
        guard let id: String = attribute(node, kAXIdentifierAttribute) else { return false }
        return known.contains(id)
    }) { return back }
    // Certains écrans Dashboard ne nomment que le titre et le rôle du bouton Retour.
    let title = first(roots) { node in
        let role: String? = attribute(node, kAXRoleAttribute)
        let desc: String? = attribute(node, kAXDescriptionAttribute)
        return role == "AXHeading" && desc == "Dashboard"
    }
    guard title != nil else { return nil }
    return first(roots) { node in
        let role: String? = attribute(node, kAXRoleAttribute)
        let desc: String? = attribute(node, kAXDescriptionAttribute)
        return role == kAXButtonRole && (desc == "Back" || desc == "Retour")
    }
}

func leaveDetail(_ app: AXUIElement, back: AXUIElement) throws {
    _ = AXUIElementPerformAction(back, kAXPressAction as CFString)
    if waitFor(2, { backButton(in: windows(app)) == nil ? true : nil }) != nil { return }
    let roots = windows(app)
    let modal = first(roots) { node in
        let role: String? = attribute(node, kAXRoleAttribute)
        return role == kAXSheetRole || role == "AXPopover" || role == "AXDialog"
            || role == "AXSystemDialog" || attribute(node, kAXModalAttribute) == true
    }
    guard modal == nil, let same = backButton(in: roots), CFEqual(same, back),
          sendEscape(to: same),
          waitFor(5, { backButton(in: windows(app)) == nil ? true : nil }) != nil else {
        throw ExportError.navigation
    }
}

func exportButton(in app: AXUIElement) throws -> AXUIElement {
    if let old = sharingPanel(in: app) { try closeSharing(app, panel: old) }
    // Les identifiants Flutter servent de liste blanche. Aucun chemin Bluetooth ou Calendrier.
    let exportID = "health.settings.export"
    let settingsID = "nav_bar.health.button.settings"
    var current = windows(app)
    if let export = namedID(exportID, in: current) { return export }
    if let back = backButton(in: current) {
        try leaveDetail(app, back: back)
        current = windows(app)
    }
    // Flutter peut exposer la roue dentée des onglets en arrière-plan.
    // Activer d'abord Santé lorsque la navigation principale est disponible.
    if let health = namedID("main.nav.health", in: current) {
        try press(health)
    }
    guard let settings = waitFor(12, { namedID(settingsID, in: windows(app)) }) else {
        throw ExportError.navigation
    }
    try press(settings)
    guard let export = waitFor(12, { namedID(exportID, in: windows(app)) }) else {
        throw ExportError.navigation
    }
    return export
}

func importArchive(_ step: String, manifest: URL) throws {
    let importer = Bundle.main.bundleURL.deletingLastPathComponent().appendingPathComponent("import_export.py")
    let python = Process()
    python.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
    python.arguments = ["-B", importer.path, step, manifest.path]
    python.standardInput = FileHandle.nullDevice
    python.standardOutput = FileHandle.nullDevice
    python.standardError = FileHandle.nullDevice
    python.currentDirectoryURL = support
    do { try python.run() } catch { throw ExportError.importFailed }
    python.waitUntilExit()
    switch python.terminationStatus {
    case 0: return
    case 75: throw ExportError.timeout
    case 77: throw ExportError.appData
    default: throw ExportError.importFailed
    }
}

func exportArchive(in runDir: URL) throws {
    let app = try accessibleEven()
    let export = try exportButton(in: app)
    let manifest = runDir.appendingPathComponent("manifest")
    try importArchive("avant", manifest: manifest)
    try press(export)
    do {
        try importArchive("recuperer", manifest: manifest)
    } catch {
        if let panel = sharingPanel(in: app) { try? closeSharing(app, panel: panel) }
        throw error
    }
    if let panel = waitFor(3, { sharingPanel(in: app) }) {
        try closeSharing(app, panel: panel)
    }
}

umask(0o077)
guard CommandLine.arguments.count == 2 else { exit(64) }
let arg = CommandLine.arguments[1]
if arg == "--self-test" { exit(0) }
let runDir = URL(fileURLWithPath: arg, isDirectory: true).standardizedFileURL
guard runDir.deletingLastPathComponent().path == support.standardizedFileURL.path,
      runDir.lastPathComponent.hasPrefix(".export-run."),
      let props = try? runDir.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey]),
      props.isDirectory == true, props.isSymbolicLink == false else { exit(64) }

let status: String
do {
    try exportArchive(in: runDir)
    status = "OK"
} catch {
    status = (error as? ExportError)?.rawValue ?? ExportError.importFailed.rawValue
}
do {
    try Data(status.utf8).write(to: runDir.appendingPathComponent("status"), options: .atomic)
} catch { exit(74) }
