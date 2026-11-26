import AppKit
import ApplicationServices
import Foundation

// Only these fixed codes are returned to Automator.
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

// Search only Even windows and the sheets hosted by those windows.
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
    guard AXIsProcessTrusted() else { throw ExportError.accessibility }
    var running = NSRunningApplication.runningApplications(withBundleIdentifier: evenIdentifier).first
    if running == nil {
        let space = NSWorkspace.shared
        guard let url = space.urlForApplication(withBundleIdentifier: evenIdentifier) else {
            throw ExportError.unavailable
        }
        let config = NSWorkspace.OpenConfiguration()
        config.activates = false
        space.openApplication(at: url, configuration: config) { _, _ in }
        running = waitFor(18) { NSRunningApplication.runningApplications(withBundleIdentifier: evenIdentifier).first }
    }
    guard let running = running else { throw ExportError.unavailable }
    let app = AXUIElementCreateApplication(running.processIdentifier)
    AXUIElementSetMessagingTimeout(app, 2)
    guard waitFor(18, { windows(app).isEmpty ? nil : true }) != nil else { throw ExportError.unavailable }
    return app
}

func press(_ element: AXUIElement) throws {
    guard AXUIElementPerformAction(element, kAXPressAction as CFString) == .success else {
        throw ExportError.navigation
    }
}

func isModal(_ node: AXUIElement) -> Bool {
    let role: String = attribute(node, kAXRoleAttribute) ?? ""
    let subrole: String = attribute(node, kAXSubroleAttribute) ?? ""
    return [kAXSheetRole, "AXPopover", "AXDialog", "AXSystemDialog"].contains(role)
        || ["AXDialog", "AXSystemDialog"].contains(subrole) || attribute(node, kAXModalAttribute) == true
}

func archiveName(_ text: String) -> Bool {
    text.range(of: #"^Even_health_data_[0-9]{8}(?:\.zip)?$"#, options: .regularExpression) != nil
}

// Accessibility elements in a hosted save panel may belong to a separate process.
// Match the controls within a single sheet so an unrelated dialog stays untouched.
func isExportSaveDialog(archive: Bool, save: Bool, cancelCount: Int) -> Bool {
    archive && save && cancelCount == 1
}

func saveCancel(in panel: AXUIElement) -> AXUIElement? {
    var pending: [AXUIElement] = attribute(panel, kAXChildrenAttribute) ?? []
    var seen = Set<AXUIElement>()
    var foundArchive = false, foundSave = false
    var cancels = [AXUIElement]()
    while let node = pending.popLast(), seen.count < 600 {
        guard seen.insert(node).inserted, !isModal(node) else { continue }
        let role: String = attribute(node, kAXRoleAttribute) ?? ""
        if role == kAXTextFieldRole || role == kAXComboBoxRole {
            if let value: String = attribute(node, kAXValueAttribute), archiveName(value) {
                foundArchive = true
            }
        } else if role == kAXButtonRole {
            let labels = [kAXTitleAttribute, kAXDescriptionAttribute].compactMap { attribute(node, $0) as String? }
            if labels.contains(where: { ["Save", "Enregistrer"].contains($0) }) { foundSave = true }
            if labels.contains(where: { ["Cancel", "Annuler"].contains($0) }) { cancels.append(node) }
        }
        pending.append(contentsOf: attribute(node, kAXChildrenAttribute) ?? [])
    }
    return isExportSaveDialog(archive: foundArchive, save: foundSave, cancelCount: cancels.count) ? cancels[0] : nil
}

func exportCancel(in app: AXUIElement) -> AXUIElement? {
    var button: AXUIElement?
    _ = first(windows(app)) { node in
        let role: String? = attribute(node, kAXRoleAttribute)
        guard role == kAXWindowRole || isModal(node) else { return false }
        button = saveCancel(in: node)
        return button != nil
    }
    return button
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

// A save panel and a share popover may appear in succession.
// Act on the identified accessibility control to preserve keyboard and pointer focus.
func closeExportPanels(_ app: AXUIElement, observeFor seconds: TimeInterval) throws {
    let started = ProcessInfo.processInfo.systemUptime
    var quietUntil = started + seconds
    var acted: AXUIElement?
    var actedAt = started
    repeat {
        guard !windows(app).isEmpty else { throw ExportError.sharing }
        let cancel = exportCancel(in: app)
        if let target = cancel ?? sharingPanel(in: app) {
            let now = ProcessInfo.processInfo.systemUptime
            if acted != target {
                let action = cancel != nil ? kAXPressAction : kAXCancelAction
                guard AXUIElementPerformAction(target, action as CFString) == .success else {
                    throw ExportError.sharing
                }
                acted = target
                actedAt = now
            } else if now - actedAt >= 3 {
                throw ExportError.sharing
            }
            quietUntil = max(quietUntil, now + 1)
        } else {
            acted = nil
        }
        if ProcessInfo.processInfo.systemUptime >= quietUntil { return }
        RunLoop.current.run(until: Date(timeIntervalSinceNow: 0.25))
    } while ProcessInfo.processInfo.systemUptime - started < seconds + 8
    throw ExportError.sharing
}

func requireClear(_ app: AXUIElement) throws {
    let roots = windows(app)
    guard roots.count == 1, exportCancel(in: app) == nil, first(roots, where: isModal) == nil else {
        throw ExportError.navigation
    }
}

func backButton(in roots: [AXUIElement]) -> AXUIElement? {
    let known = ["health.detail.back", "health.steps.back", "dashboard.back"]
    if let back = first(roots, where: { node in
        guard let id: String = attribute(node, kAXIdentifierAttribute) else { return false }
        return known.contains(id)
    }) { return back }
    // Some Dashboard screens expose only the back button’s role and label.
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
    try requireClear(app)
    try press(back)
    guard waitFor(5, { backButton(in: windows(app)) == nil ? true : nil }) != nil else {
        throw ExportError.navigation
    }
}

func exportButton(in app: AXUIElement) throws -> AXUIElement {
    try requireClear(app)
    // Match the Flutter controls used by the Health export.
    let exportID = "health.settings.export"
    let settingsID = "nav_bar.health.button.settings"
    var current = windows(app)
    if let export = namedID(exportID, in: current) { return export }
    if let back = backButton(in: current) {
        try leaveDetail(app, back: back)
        current = windows(app)
    }
    // Flutter may expose settings controls from background tabs. Select Health first.
    if let health = namedID("main.nav.health", in: current) {
        try requireClear(app)
        try press(health)
    }
    guard let settings = waitFor(12, { namedID(settingsID, in: windows(app)) }) else {
        throw ExportError.navigation
    }
    try requireClear(app)
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
    let timeout: TimeInterval = step == "receive" ? 120 : 48
    if waitFor(timeout, { python.isRunning ? nil : true }) == nil {
        python.terminate()
        if waitFor(2, { python.isRunning ? nil : true }) == nil {
            kill(python.processIdentifier, SIGKILL)
        }
        throw ExportError.timeout
    }
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
    // An existing panel may belong to a manual export.
    try requireClear(app)
    let manifest = runDir.appendingPathComponent("manifest")
    try importArchive("baseline", manifest: manifest)
    let export = try exportButton(in: app)
    try requireClear(app)
    do {
        try press(export)
        try importArchive("receive", manifest: manifest)
    } catch {
        try closeExportPanels(app, observeFor: 3)
        throw error
    }
    // The archive is already copied before dismissing the macOS save panel.
    try closeExportPanels(app, observeFor: 4)
    if (try? requireClear(app)) != nil {
        try? importArchive("cards", manifest: manifest)
    }
    try closeExportPanels(app, observeFor: 1)
}

umask(0o077)
let arguments = Array(CommandLine.arguments.dropFirst())
if arguments == ["--self-test"] {
    let valid = ["Even_health_data_20991231", "Even_health_data_20991231.zip"]
    let invalid = ["budget.zip", "Even_health_data_123.zip", "Even_health_data_20991231.txt", "xEven_health_data_20991231.zip", "Even_health_data_20991231.zip.old"]
    let signature = isExportSaveDialog(archive: true, save: true, cancelCount: 1)
        && !isExportSaveDialog(archive: false, save: true, cancelCount: 1)
        && !isExportSaveDialog(archive: true, save: false, cancelCount: 1)
        && !isExportSaveDialog(archive: true, save: true, cancelCount: 2)
    exit(signature && valid.allSatisfy(archiveName) && !invalid.contains(where: archiveName) ? 0 : 1)
}
let checkAccess = arguments.count == 2 && arguments[0] == "--check-access"
guard arguments.count == 1 || checkAccess, let path = arguments.last else { exit(64) }
let runDir = URL(fileURLWithPath: path, isDirectory: true).standardizedFileURL
guard runDir.deletingLastPathComponent().path == support.standardizedFileURL.path,
      runDir.lastPathComponent.hasPrefix(".export-run."),
      let props = try? runDir.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey]),
      props.isDirectory == true, props.isSymbolicLink == false else { exit(64) }

let status: String
do {
    if checkAccess {
        guard AXIsProcessTrusted() else { throw ExportError.accessibility }
    } else {
        try exportArchive(in: runDir)
    }
    status = "OK"
} catch {
    status = (error as? ExportError)?.rawValue ?? ExportError.importFailed.rawValue
}
do {
    try Data(status.utf8).write(to: runDir.appendingPathComponent("status"), options: .atomic)
} catch { exit(74) }
