import AppKit
import ApplicationServices
import Foundation

// Outil en ligne de commande du R1 Bridge Collector. Aucun transfert ni invite TCC.
enum CardError: Int32, Error {
    case unreadable = 65, unavailable = 69, navigation = 70, storage = 74, session = 75, accessibility = 77

    var label: String {
        switch self {
        case .unreadable: return "CARDS_UNREADABLE"
        case .unavailable: return "CARDS_EVEN_UNAVAILABLE"
        case .navigation: return "CARDS_NAVIGATION"
        case .storage: return "CARDS_STORAGE"
        case .session: return "CARDS_SESSION"
        case .accessibility: return "CARDS_ACCESSIBILITY"
        }
    }
}

let bundleID = "com.even.sg"
let keys = ["steps", "calories", "heartRate", "hrv", "spo2", "skinTemperature"]
let titles: [String: Set<String>] = [
    "steps": ["steps", "pas", "nombre de pas"],
    "calories": ["active calories", "calories actives", "calories en activite"],
    "heartRate": ["heart rate", "frequence cardiaque", "rythme cardiaque"],
    "hrv": ["hrv", "vfc", "variabilite de la frequence cardiaque"],
    "spo2": ["spo2", "oxygen saturation", "saturation en oxygene"],
    "skinTemperature": ["temperature", "skin temperature", "temperature cutanee", "temperature de la peau"],
]

struct Reading: Codable, Equatable {
    let value: Double
    let unit: String
    let recency: String
    var recorded_at: String?
}

struct Snapshot: Codable {
    let version: Int
    let recorded_at: String
    let metrics: [String: Reading]
}

func cleaned(_ text: String) -> String {
    text.replacingOccurrences(of: "\u{00a0}", with: " ")
        .replacingOccurrences(of: "\u{202f}", with: " ")
        .trimmingCharacters(in: .whitespacesAndNewlines)
}

func folded(_ text: String) -> String {
    cleaned(text).folding(options: [.caseInsensitive, .diacriticInsensitive], locale: Locale(identifier: "en_US_POSIX"))
        .lowercased().replacingOccurrences(of: "₂", with: "2").replacingOccurrences(of: "’", with: "'")
}

func matches(_ text: String, _ pattern: String) -> Bool {
    text.range(of: "^(?:" + pattern + ")$", options: .regularExpression) != nil
}

func recencyLanguage(_ raw: String) -> String? {
    let text = folded(raw)
    if matches(text, #"just now|now|today|yesterday|(?:[0-9]+|a|an|one) (?:second|minute|hour|day|week|month|year)s? ago"#) {
        return "en"
    }
    if matches(text, #"a l'instant|maintenant|aujourd'hui|hier|il y a (?:[0-9]+|un|une) (?:secondes?|minutes?|heures?|jours?|semaines?|mois|ans?|annees?)"#) {
        return "fr"
    }
    return nil
}

func parse(_ key: String, _ title: String, _ rawValue: String, _ recency: String) -> Reading? {
    guard titles[key]?.contains(folded(title)) == true, let lang = recencyLanguage(recency) else { return nil }
    let raw = cleaned(rawValue).replacingOccurrences(of: "−", with: "-")
    let number: String
    let unit: String
    if key == "steps" {
        guard matches(raw, #"[0-9]+|[0-9]{1,3}(?:[ ,][0-9]{3})+"#) else { return nil }
        unit = "pas"
        number = raw.replacingOccurrences(of: ",", with: "").replacingOccurrences(of: " ", with: "")
    } else {
        let units: [String: [String]] = ["calories": ["kcal"], "heartRate": ["bpm"],
                                        "hrv": ["ms"], "spo2": ["%"], "skinTemperature": ["°C", "°F"]]
        guard let suffix = units[key]?.first(where: raw.hasSuffix) else { return nil }
        unit = suffix
        var num = cleaned(String(raw.dropLast(suffix.count)))
        if key == "skinTemperature" {
            guard let sign = num.first, sign == "+" || sign == "-" else { return nil }
        } else if num.hasPrefix("-") || num.hasPrefix("+") { return nil }
        let format = lang == "en"
            ? #"[+\-]?(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?"#
            : #"[+\-]?(?:[0-9]+|[0-9]{1,3}(?: [0-9]{3})+)(?:[,.][0-9]+)?"#
        guard matches(num, format) else { return nil }
        num = num.replacingOccurrences(of: " ", with: "").replacingOccurrences(of: ",", with: lang == "en" ? "" : ".")
        number = num
    }
    guard let value = Double(number), value.isFinite, key != "spo2" || value <= 100 else { return nil }
    return Reading(value: value, unit: unit, recency: cleaned(recency), recorded_at: nil)
}

func attr<T>(_ node: AXUIElement, _ key: String) -> T? {
    var value: CFTypeRef?
    guard AXUIElementCopyAttributeValue(node, key as CFString, &value) == .success else { return nil }
    return value as? T
}

// Seul l’arbre d’accessibilité des fenêtres appartenant au PID d’Even est visité.
func walk(_ roots: [AXUIElement], pid: pid_t, _ visit: (AXUIElement) -> Bool) {
    var nodes = roots
    var seen = Set<AXUIElement>()
    var i = 0
    while i < nodes.count && seen.count < 2500 {
        let node = nodes[i]
        i += 1
        guard seen.insert(node).inserted else { continue }
        var owner: pid_t = 0
        guard AXUIElementGetPid(node, &owner) == .success && owner == pid else { continue }
        if !visit(node) { return }
        nodes.append(contentsOf: attr(node, kAXChildrenAttribute) ?? [])
    }
}

struct Even {
    let app: AXUIElement
    let pid: pid_t
    var windows: [AXUIElement] {
        var candidates: [AXUIElement] = attr(app, kAXWindowsAttribute) ?? []
        for key in [kAXFocusedWindowAttribute, kAXMainWindowAttribute] {
            if let window: AXUIElement = attr(app, key),
               (attr(window, kAXRoleAttribute) as String?) == kAXWindowRole {
                candidates.append(window)
            }
        }
        var seen = Set<AXUIElement>()
        return candidates.filter { node in
            var owner: pid_t = 0
            return AXUIElementGetPid(node, &owner) == .success && owner == pid && seen.insert(node).inserted
        }
    }

    func element(_ id: String) -> AXUIElement? {
        var result: AXUIElement?
        walk(windows, pid: pid) { node in
            guard (attr(node, kAXIdentifierAttribute) as String?) == id else { return true }
            result = node
            return false
        }
        return result
    }

    func sharePanel() -> AXUIElement? {
        var result: AXUIElement?
        walk(windows, pid: pid) { node in
            guard (attr(node, kAXRoleAttribute) as String?) == "AXPopover" else { return true }
            var labels = Set<String>()
            walk([node], pid: pid) { child in
                if (attr(child, kAXRoleAttribute) as String?) == kAXButtonRole {
                    labels.formUnion(texts(child).map(folded))
                }
                return true
            }
            guard !labels.isDisjoint(with: ["save", "enregistrer"]),
                  !labels.isDisjoint(with: ["copy", "copier"]) else { return true }
            result = node
            return false
        }
        return result
    }

    func closeShare() throws {
        guard let panel = sharePanel() else { return }
        _ = AXUIElementPerformAction(panel, kAXCancelAction as CFString)
        if wait(0.8, { sharePanel() == nil }) { return }
        guard let same = sharePanel(), CFEqual(panel, same) else { throw CardError.navigation }
        try escapeEven()
        guard wait(3, { sharePanel() == nil }) else { throw CardError.navigation }
    }

    func escapeEven() throws {
        guard NSRunningApplication(processIdentifier: pid)?.bundleIdentifier == bundleID,
              let esc = CGEvent(keyboardEventSource: nil, virtualKey: 53, keyDown: true),
              let up = CGEvent(keyboardEventSource: nil, virtualKey: 53, keyDown: false) else { throw CardError.navigation }
        esc.postToPid(pid)
        up.postToPid(pid)
    }

    func readCards() -> [String: Reading] {
        var fields = [String: [String]]()
        let validIDs = Set(keys.flatMap { key in ["title", "value", "time"].map { "health.module.\(key).\($0)" } })
        walk(windows, pid: pid) { node in
            if let id: String = attr(node, kAXIdentifierAttribute), validIDs.contains(id) {
                fields[id, default: []].append(contentsOf: texts(node))
            }
            return true
        }
        var result = [String: Reading]()
        for key in keys {
            let prefix = "health.module.\(key)."
            var parsed: [Reading] = []
            for title in Set(fields[prefix + "title"] ?? []) where titles[key]?.contains(folded(title)) == true {
                for value in Set(fields[prefix + "value"] ?? []) {
                    for recency in Set(fields[prefix + "time"] ?? []) {
                        if let entry = parse(key, title, value, recency), !parsed.contains(entry) {
                            parsed.append(entry)
                        }
                    }
                }
            }
            if parsed.count == 1 { result[key] = parsed[0] }
        }
        return result
    }

    func clickGearIfTargeted(_ id: String) {
        guard NSRunningApplication(processIdentifier: pid)?.bundleIdentifier == bundleID,
              sharePanel() == nil, let gear = element(id),
              let position: AXValue = attr(gear, kAXPositionAttribute),
              let size: AXValue = attr(gear, kAXSizeAttribute) else { return }
        var origin = CGPoint.zero
        var extent = CGSize.zero
        guard AXValueGetValue(position, .cgPoint, &origin), AXValueGetValue(size, .cgSize, &extent),
              extent.width > 0, extent.height > 0 else { return }
        let center = CGPoint(x: origin.x + extent.width / 2, y: origin.y + extent.height / 2)
        guard center.x.isFinite, center.y.isFinite else { return }
        var hit: AXUIElement?
        guard AXUIElementCopyElementAtPosition(app, Float(center.x), Float(center.y), &hit) == .success else { return }
        // Vérifier l’élément sous le point juste avant l’envoi, y compris un enfant du bouton.
        var node = hit
        for _ in 0..<12 {
            guard let current = node else { return }
            var owner: pid_t = 0
            guard AXUIElementGetPid(current, &owner) == .success && owner == pid else { return }
            if CFEqual(current, gear) && (attr(current, kAXIdentifierAttribute) as String?) == id {
                guard let down = CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown,
                                         mouseCursorPosition: center, mouseButton: .left),
                      let up = CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp,
                                       mouseCursorPosition: center, mouseButton: .left) else { return }
                down.postToPid(pid)
                up.postToPid(pid)
                return
            }
            node = attr(current, kAXParentAttribute)
        }
    }

    func capture(at file: URL) throws -> Int {
        // Le ZIP peut être prêt avant l’apparition de la feuille de partage.
        _ = wait(5, { sharePanel() != nil })
        try closeShare()
        let settings = "nav_bar.health.button.settings"
        let exportID = "health.settings.export"
        let backID = "health.settings.back"
        func onOverview() -> Bool {
            element(settings) != nil && element("health.module.steps.title") != nil && element(exportID) == nil
        }
        if !onOverview() {
            guard element(exportID) != nil, let back = element(backID), sharePanel() == nil else { throw CardError.navigation }
            _ = AXUIElementPerformAction(back, kAXPressAction as CFString)
            if !wait(2, onOverview) {
                // Échap seulement si les DEUX contrôles des réglages sont encore visibles
                // et qu’aucune feuille de partage ne s’est ouverte entre-temps.
                guard element(exportID) != nil, element(backID) != nil, sharePanel() == nil else { throw CardError.navigation }
                try escapeEven()
            }
        }
        guard wait(6, onOverview) else { throw CardError.navigation }
        var found = [String: Reading]()
        _ = wait(2, {
            found = readCards()
            return found.count == keys.count
        })
        return try finishCapture(found, at: file) {
            func onSettings() -> Bool {
                element(exportID) != nil && element(backID) != nil && sharePanel() == nil
            }
            if onSettings() { return }
            guard let gear = element(settings), onOverview(), sharePanel() == nil else { throw CardError.navigation }
            _ = AXUIElementPerformAction(gear, kAXPressAction as CFString)
            if wait(2, onSettings) { return }
            if onOverview() { clickGearIfTargeted(settings) }
            if wait(3, onSettings) { return }
            // L’export suivant sait également partir de l’accueil Santé reconnu.
            guard onOverview(), sharePanel() == nil else { throw CardError.navigation }
        }
    }
}

func texts(_ element: AXUIElement) -> [String] {
    [kAXValueAttribute, kAXDescriptionAttribute, kAXTitleAttribute].compactMap { key -> String? in
        if let s: String = attr(element, key) { return cleaned(s) }
        if let s: NSAttributedString = attr(element, key) { return cleaned(s.string) }
        return nil
    }
}

func wait(_ seconds: TimeInterval, _ predicate: () -> Bool) -> Bool {
    let until = ProcessInfo.processInfo.systemUptime + seconds
    repeat {
        if predicate() { return true }
        RunLoop.current.run(until: Date(timeIntervalSinceNow: 0.18))
    } while ProcessInfo.processInfo.systemUptime < until
    return false
}

func merge(_ current: [String: Reading], previous: Snapshot?, observed: String) -> Snapshot? {
    var merged = previous?.metrics ?? [:]
    var changed = false
    for (key, var value) in current {
        if let old = merged[key], value.value == old.value, value.unit == old.unit, value.recency == old.recency {
            continue
        }
        changed = true
        value.recorded_at = observed
        merged[key] = value
    }
    guard changed else { return nil }
    // Toute carte conservée garde son instant de lecture, même dans l’ancien format.
    for key in Array(merged.keys) where merged[key]?.recorded_at == nil {
        merged[key]?.recorded_at = previous?.recorded_at
    }
    return Snapshot(version: 1, recorded_at: observed, metrics: merged)
}

func persist(_ values: [String: Reading], at url: URL) throws {
    let fm = FileManager.default
    let prev: Snapshot?
    if fm.fileExists(atPath: url.path) {
        let attr = try fm.attributesOfItem(atPath: url.path)
        guard attr[.type] as? FileAttributeType == .typeRegular else { throw CardError.storage }
        prev = try JSONDecoder().decode(Snapshot.self, from: Data(contentsOf: url))
        guard prev?.version == 1 else { throw CardError.storage }
    } else { prev = nil }
    let fmt = ISO8601DateFormatter()
    fmt.timeZone = .current
    guard let snapshot = merge(values, previous: prev, observed: fmt.string(from: Date())) else { return }
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.sortedKeys]
    // umask 077 s’applique au temporaire atomique avant le remplacement.
    try encoder.encode(snapshot).write(to: url, options: .atomic)
    try fm.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
}

func finishCapture(_ values: [String: Reading], at url: URL, restore: () throws -> Void) throws -> Int {
    if !values.isEmpty { try persist(values, at: url) }
    try restore()
    guard !values.isEmpty else { throw CardError.unreadable }
    return values.count
}

func collect() throws -> Int {
    let session = CGSessionCopyCurrentDictionary() as? [String: Any]
    guard let session = session, session["CGSSessionScreenIsLocked"] as? Bool != true,
          session["kCGSSessionOnConsoleKey"] as? Bool == true,
          (session["kCGSSessionUserIDKey"] as? NSNumber)?.uint32Value == getuid() else { throw CardError.session }
    guard AXIsProcessTrusted() else { throw CardError.accessibility }
    guard let running = NSRunningApplication.runningApplications(withBundleIdentifier: bundleID).first else { throw CardError.unavailable }
    let even = Even(app: AXUIElementCreateApplication(running.processIdentifier), pid: running.processIdentifier)
    AXUIElementSetMessagingTimeout(even.app, 1)
    let file = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/R1 Bridge/releves_even.json")
    return try even.capture(at: file)
}

func selfTest() -> Bool {
    let steps = parse("steps", "Steps", "1234", "2 hours ago")
    let temp = parse("skinTemperature", "température", "−0,8 °C", "il y a 2 jours")
    let newer = parse("steps", "Steps", "1234", "3 hours ago")
    guard let steps = steps, steps.unit == "pas", let temp = temp, temp.value == -0.8,
          parse("spo2", "SpO₂", "92%", "2 days ago")?.value == 92,
          parse("hrv", "HRV", "—", "3 days ago") == nil,
          parse("calories", "Heart rate", "140 kcal", "3 hours ago") == nil,
          parse("heartRate", "Heart rate", "72 ms", "today") == nil,
          parse("heartRate", "Heart rate", "72 bpm", "unverified string") == nil,
          let first = merge(["steps": steps, "skinTemperature": temp], previous: nil, observed: "first"),
          merge(["steps": steps], previous: first, observed: "later") == nil,
          let newer = newer, let next = merge(["steps": newer], previous: first, observed: "later"),
          next.metrics["steps"]?.recorded_at == "later", next.metrics["skinTemperature"]?.recorded_at == "first" else { return false }
    return true
}

umask(0o077)
if CommandLine.arguments.dropFirst() == ["--self-test"] { exit(selfTest() ? 0 : 1) }
guard CommandLine.arguments.dropFirst() == ["--capture"] else { exit(64) }
do {
    let count = try collect()
    print(count == keys.count ? "CARDS_OK" : "CARDS_PARTIAL")
} catch {
    let cause = (error as? CardError) ?? .storage
    print(cause.label)
    exit(cause.rawValue)
}
