import Foundation
import HealthKit
import Security
import SwiftUI

private struct SavedConnection: Codable {
    let pair: MacPair
    var cursor = 0
    var checked: Date?
    var latestWake: String?
    var skipped = 0
}

private enum ConnectionVault {
    static var key: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: "io.github.daviddemri26.sleepsync",
         kSecAttrAccount as String: "connection"]
    }

    static func load() throws -> SavedConnection? {
        var query = key
        query[kSecReturnData as String] = true
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = item as? Data else { throw issue(status) }
        return try JSONDecoder().decode(SavedConnection.self, from: data)
    }

    static func save(_ record: SavedConnection) throws {
        let attributes: [String: Any] = [
            kSecValueData as String: try JSONEncoder().encode(record),
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]
        var status = SecItemUpdate(key as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            status = SecItemAdd(key.merging(attributes) { _, new in new } as CFDictionary, nil)
        }
        guard status == errSecSuccess else { throw issue(status) }
    }

    static func remove() throws {
        let status = SecItemDelete(key as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else { throw issue(status) }
    }

    static func issue(_ status: OSStatus) -> ImportIssue {
        status == errSecInteractionNotAllowed ? .protectedStorage : .storage
    }
}

enum SyncState: Equatable {
    case setup, pairing, ready, syncing, current, waiting, network, health, incompatible, needsPair, retry, invalid, storage
}

@MainActor
final class SleepController: ObservableObject {
    static let shared = SleepController()

    @Published private(set) var state: SyncState = .setup
    @Published private(set) var macName: String?
    @Published private(set) var checked: Date?
    @Published private(set) var latestWake: String?
    @Published private(set) var skipped = 0
    @Published private(set) var demo = false
    @Published private(set) var progress = 0
    @Published var notice: String?

    private let health = HealthWriter()
    private var record: SavedConnection?
    private var worker: Task<Bool, Never>?
    private var modifying = false
    private var loaded = false
    private var screenshotMode = false

    var working: Bool { worker != nil || state == .pairing || state == .syncing || modifying }
    var isPaired: Bool { macName != nil }
    var healthDenied: Bool { !demo && !screenshotMode && health.authorization == .sharingDenied }
    var schedulesRefresh: Bool { !screenshotMode && record != nil }

    private init() {
        let args = ProcessInfo.processInfo.arguments
        if let flag = ["-preview-setup", "-preview-connected", "-preview-waiting"].first(where: args.contains) {
            screenshotMode = true
            if flag != "-preview-setup" { showDemo(waiting: flag == "-preview-waiting") }
        } else {
            load()
        }
    }

    private func load() {
        do {
            record = try ConnectionVault.load()
            loaded = true
            reflect()
            state = record == nil ? .setup : .ready
        } catch {
            state = .storage
        }
    }

    private func reflect() {
        macName = record?.pair.name
        checked = record?.checked
        latestWake = record?.latestWake
        skipped = record?.skipped ?? 0
    }

    func showDemo(waiting: Bool = false) {
        guard !working, record == nil, loaded || screenshotMode else { return }
        demo = true
        macName = "Studio Mac"
        let calendar = Calendar.current
        let now = Date()
        let morning = calendar.date(bySettingHour: 7, minute: 42, second: 0, of: now) ?? now
        let lastSync = morning <= now ? morning : (calendar.date(byAdding: .day, value: -1, to: morning) ?? now)
        var wakeDateFormat = Date.ISO8601FormatStyle().year().month().day()
        wakeDateFormat.timeZone = .current
        latestWake = lastSync.formatted(wakeDateFormat)
        checked = lastSync
        state = waiting ? .waiting : .current
    }

    func endDemo() {
        demo = false
        if screenshotMode {
            reflect()
            state = .setup
        } else {
            load()
        }
    }

    func pair(code: String) async {
        guard !working, !demo, !screenshotMode else { return }
        modifying = true
        state = .pairing
        do {
            let pair = try await MacClient.pair(qr: code)
            let connection = SavedConnection(pair: pair)
            try ConnectionVault.save(connection)
            record = connection
            loaded = true
            reflect()
            state = .health
        } catch {
            apply(error)
            modifying = false
            return
        }
        modifying = false
        await enableHealth()
    }

    func enableHealth() async {
        guard !working, !demo, !screenshotMode else { return }
        modifying = true
        do {
            try await health.authorize()
        } catch {
            apply(error)
            modifying = false
            return
        }
        modifying = false
        _ = await sync()
    }

    func onActive() async {
        guard !demo, !screenshotMode else { return }
        if !loaded || state == .storage { load() }
        if record == nil, state == .network { state = .setup }
        guard record != nil, !working else { return }
        _ = await sync()
    }

    func sync() async -> Bool {
        if demo {
            progress = 0
            state = .syncing
            try? await Task.sleep(for: .milliseconds(250))
            guard demo else { return false }
            progress = 3
            state = .current
            return true
        }
        guard !screenshotMode, !modifying else { return false }
        if !loaded { load() }
        guard record != nil else { return false }
        let task: Task<Bool, Never>
        if let worker {
            task = worker
        } else {
            task = Task { await self.importPages() }
            worker = task
        }
        return await withTaskCancellationHandler(operation: { await task.value }, onCancel: { task.cancel() })
    }

    private func importPages() async -> Bool {
        defer { worker = nil }
        guard var local = record else { return false }
        guard HKHealthStore.isHealthDataAvailable() else { state = .incompatible; return false }
        guard health.authorization == .sharingAuthorized else { state = .health; return false }
        progress = 0
        state = .syncing
        var rescanned = false
        do {
            while true {
                try Task.checkCancellation()
                let page: SleepPage
                do {
                    page = try await MacClient.pull(local.pair, after: local.cursor)
                } catch MacClientError.cursorReset {
                    guard local.cursor > 0, !rescanned else { throw MacClientError.unavailable }
                    local.cursor = 0
                    rescanned = true
                    continue
                }
                guard page.cursor >= local.cursor, !(page.more && page.cursor == local.cursor) else {
                    throw ImportIssue.invalidSession
                }
                for night in page.sessions {
                    try Task.checkCancellation()
                    try await health.save(night)
                    progress += 1
                }
                local.cursor = page.cursor
                local.skipped = page.skipped
                if !page.more {
                    local.latestWake = page.latestWakeDate
                    local.checked = Date()
                }
                try ConnectionVault.save(local)
                record = local
                reflect()
                if !page.more { break }
            }
            state = .current
            return true
        } catch is CancellationError {
            state = .ready
        } catch {
            apply(error)
        }
        return false
    }

    func disconnect(localOnly: Bool = false) async {
        guard !working else { return }
        if demo { endDemo(); return }
        guard let record else { return }
        modifying = true
        defer { modifying = false }
        do {
            if !localOnly {
                do { try await MacClient.unpair(record.pair) } catch MacClientError.unpaired { }
            }
            try ConnectionVault.remove()
            self.record = nil
            reflect()
            state = .setup
        } catch {
            notice = localOnly
                ? "The saved connection could not be removed. Unlock your iPhone and try again."
                : "Couldn’t disconnect from your Mac. Try again on the same Wi-Fi, or forget the connection on this iPhone and remove it on your Mac."
        }
    }

    private func apply(_ error: Error) {
        switch error {
        case MacClientError.waiting: state = isPaired ? .waiting : .setup
        case MacClientError.unavailable: state = .retry
        case MacClientError.localNetwork: state = .network
        case MacClientError.unpaired: state = .needsPair
        case MacClientError.invalidCode: state = isPaired ? .needsPair : .setup
        case MacClientError.ambiguous, ImportIssue.invalidSession: state = .invalid
        case ImportIssue.healthPermission: state = .health
        case ImportIssue.healthUnavailable: state = .incompatible
        case ImportIssue.protectedStorage, ImportIssue.storage: state = .storage
        case let healthError as HKError where healthError.code == .errorAuthorizationDenied: state = .health
        case let healthError as HKError where healthError.code == .errorDatabaseInaccessible: state = .ready
        default: state = .retry
        }
        if !isPaired && state == .setup {
            notice = error.localizedDescription
        }
    }
}
