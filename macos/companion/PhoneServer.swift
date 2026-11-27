import Darwin
import Foundation
import Network

private struct PhoneRequest: Decodable {
    let op: String
    let code: Data?
    let token: Data
    let after: Int?
}

struct PhoneRouter {
    let store: PhonePairingStore
    let name: String
    let feed: (Int) throws -> Data

    func reply(_ bytes: Data, identity: PhoneIdentity) -> Data {
        func failure(_ reason: String) -> Data { Data("{\"error\":\"\(reason)\"}".utf8) }
        guard bytes.count <= 2048, let request = try? JSONDecoder().decode(PhoneRequest.self, from: bytes),
              request.token.count == 32 else { return failure("unpaired") }
        do {
            // A socket accepted just before a key rotation cannot use the new key's authority.
            guard let live = try store.identity(), live.service == identity.service,
                  live.secret == identity.secret else { return failure("unpaired") }
            if request.op == "pair" {
                guard live.tokenDigest == nil, let code = request.code else { return failure("pairing") }
                try store.claim(code: code, token: request.token)
                return try JSONSerialization.data(withJSONObject: ["ok": true, "name": name])
            }
            guard try store.accepts(request.token) else { return failure("unpaired") }
            if request.op == "status" {
                return try JSONSerialization.data(withJSONObject: ["ok": true, "name": name])
            }
            if request.op == "unpair" {
                try store.disconnect(token: request.token)
                return Data("{\"ok\":true}".utf8)
            }
            guard request.op == "pull", let after = request.after, after >= 0 else { return failure("unavailable") }
            let result = try feed(after)
            guard try store.accepts(request.token) else { return failure("unpaired") }
            return result
        } catch PhoneError.grant { return failure("pairing") }
        catch PhoneError.cursorReset { return failure("cursorReset") }
        catch PhoneError.stale { return failure("unpaired") }
        catch { return failure("unavailable") }
    }
}

private let maxFeedBytes = SleepWire.maxFrame

func readPhoneFeed(resources: URL, after: Int) throws -> Data {
    let task = Process()
    task.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
    task.arguments = ["-B", resources.appendingPathComponent("runtime/sleep_feed.py").path, String(after)]
    task.environment = ["HOME": FileManager.default.homeDirectoryForCurrentUser.path, "PATH": "/usr/bin:/bin"]
    task.standardInput = FileHandle.nullDevice
    task.standardError = FileHandle.nullDevice
    let pipe = Pipe()
    task.standardOutput = pipe
    try task.run()
    let deadline = DispatchWorkItem { if task.isRunning { task.terminate() } }
    DispatchQueue.global().asyncAfter(deadline: .now() + 90, execute: deadline)
    defer { deadline.cancel() }
    var data = Data()
    while let chunk = try pipe.fileHandleForReading.read(upToCount: 65536), !chunk.isEmpty {
        guard data.count + chunk.count <= maxFeedBytes else {
            task.terminate()
            throw PhoneError.network
        }
        data.append(chunk)
    }
    task.waitUntilExit()
    if task.terminationReason == .exit, task.terminationStatus == 3 { throw PhoneError.cursorReset }
    guard task.terminationStatus == 0, !data.isEmpty else { throw PhoneError.network }
    return data
}

// Listener state and connection counts are confined to queue. PhonePairingStore serializes its own access.
final class PhoneServer: @unchecked Sendable {
    let queue = DispatchQueue(label: "local.r1bridge.iphone")
    private let router: PhoneRouter
    private var listener: NWListener?
    private var identity: PhoneIdentity?
    private var watch: DispatchSourceFileSystemObject?
    private var connections = 0
    private var timer: DispatchSourceTimer?

    init(router: PhoneRouter) { self.router = router }

    convenience init(store: PhonePairingStore, resources: URL) {
        self.init(router: PhoneRouter(store: store, name: Host.current().localizedName ?? "Mac",
                                      feed: { try readPhoneFeed(resources: resources, after: $0) }))
    }

    func start() {
        // Pairing updates touch one stable lock file. Wake immediately on changes
        // and occasionally recover when a login Keychain becomes available again.
        let fd = open(router.store.signalURL.path, O_CREAT | O_RDONLY | O_CLOEXEC | O_NOFOLLOW, 0o600)
        if fd >= 0 {
            let source = DispatchSource.makeFileSystemObjectSource(fileDescriptor: fd, eventMask: [.attrib, .write], queue: queue)
            source.setEventHandler { [weak self] in self?.refresh() }
            source.setCancelHandler { close(fd) }
            source.resume()
            watch = source
        }
        let timer = DispatchSource.makeTimerSource(queue: queue)
        timer.schedule(deadline: .now(), repeating: 30, leeway: .seconds(2))
        timer.setEventHandler { self.refresh() }
        timer.resume()
        self.timer = timer
    }

    private func refresh() {
        let now = Date()
        let current = try? router.store.identity()
        let active = current.flatMap { value in
            value.tokenDigest != nil || (value.expires ?? .distantPast) > now ? value : nil
        }
        guard listener == nil || active?.secret != identity?.secret else { return }
        listener?.cancel()
        listener = nil
        identity = active
        guard let active else { return }
        do {
            let parameters = SleepWire.parameters(secret: active.secret)
            parameters.acceptLocalOnly = true
            parameters.prohibitedInterfaceTypes = [.cellular, .other]
            let next = try NWListener(using: parameters)
            var advertisement = NWListener.Service(name: active.service, type: SleepWire.serviceType, domain: "local.")
            advertisement.noAutoRename = true
            next.service = advertisement
            next.newConnectionHandler = { [weak self] in self?.accept($0, identity: active) }
            next.stateUpdateHandler = { [weak self, weak next] state in
                guard let self, let next, self.listener === next else { return }
                switch state {
                case .failed(let error):
                    next.cancel()
                    self.listener = nil
                    self.queue.asyncAfter(deadline: .now() + 2) { self.refresh() }
                    self.report(Self.networkProblem(error))
                case .waiting(let error):
                    self.report(Self.networkProblem(error))
                case .ready: self.report("")
                default: break
                }
            }
            listener = next
            next.start(queue: queue)
            if let expiry = active.expires {
                queue.asyncAfter(deadline: .now() + max(0, expiry.timeIntervalSinceNow)) { [weak self] in self?.refresh() }
            }
        } catch { report(Self.networkProblem(error as? NWError)) }
    }

    static func networkProblem(_ error: NWError?) -> String {
        let recovery = "In System Settings → Privacy & Security → Local Network, allow Even R1 Ring Exporter for Mac. Then tap Sync Now on your iPhone."
        switch error {
        case .dns(-65570), .posix(.EACCES), .posix(.EPERM):
            return "macOS denied local network access. " + recovery
        default:
            return "The Mac is waiting for its local connection. Check that both devices are on the same local network. " + recovery
        }
    }

    private func report(_ text: String) {
        try? Data(text.utf8).write(to: router.store.networkStatusURL, options: .atomic)
    }

    private func accept(_ connection: NWConnection, identity: PhoneIdentity) {
        guard connections < 6 else { connection.cancel(); return }
        connections += 1
        let timeout = DispatchWorkItem { connection.cancel() }
        queue.asyncAfter(deadline: .now() + 105, execute: timeout)
        connection.start(queue: queue)
        Task.detached { [self] in
            defer {
                connection.cancel()
                timeout.cancel()
                queue.async {
                    self.connections -= 1
                    self.refresh()
                }
            }
            do {
                let bytes = try await SleepWire.receive(connection, limit: 2048)
                let result = router.reply(bytes, identity: identity)
                try await SleepWire.send(result, on: connection)
            } catch { return }
        }
    }
}
