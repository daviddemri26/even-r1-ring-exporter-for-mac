import Darwin
import Foundation

// Exercise the production Bonjour listener, TLS framing and iPhone client. All
// credentials live in memory and every session is created here for this run.
@main
enum LocalSyncCheck {
    struct CheckFailure: LocalizedError {
        let message: String
        var errorDescription: String? { message }
    }

    static func require(_ result: Bool, _ message: String) throws {
        if !result { throw CheckFailure(message: message) }
    }

    static func main() async {
        do { try await run() }
        catch {
            FileHandle.standardError.write(Data("Local sync check failed: \(error.localizedDescription)\n".utf8))
            exit(1)
        }
    }

    static func run() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("SleepSyncCheck-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false,
                                                attributes: [.posixPermissions: 0o700])
        defer { try? FileManager.default.removeItem(at: directory) }
        try verifyPhonePairing(base: directory)
        var identity: PhoneIdentity?
        let store = PhonePairingStore(base: directory, read: { identity }, write: { identity = $0 })
        let grant = try store.newGrant()
        guard CommandLine.arguments.count == 3 else {
            throw CheckFailure(message: "Pass the initial and completed synthetic sleep-feed pages.")
        }
        let initial = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
        let completed = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[2]))
        let router = PhoneRouter(store: store, name: "Synthetic Mac", feed: { after in
            switch after {
            case 0: return initial
            case 2: return completed
            default: throw PhoneError.cursorReset
            }
        })
        let server = PhoneServer(router: router)
        server.start()
        let ready = directory.appendingPathComponent(".iphone-network-status")
        let deadline = Date().addingTimeInterval(12)
        while (try? String(contentsOf: ready, encoding: .utf8)) != "" {
            guard Date() < deadline else {
                throw CheckFailure(message: "The Bonjour listener could not start. Check macOS Local Network permission and run again.")
            }
            try await Task.sleep(for: .milliseconds(100))
        }

        let qr = String(decoding: try JSONEncoder().encode(grant), as: UTF8.self)
        let pair = try await MacClient.pair(qr: qr)
        try require(pair.name == "Synthetic Mac" && pair.service == grant.service, "Paired status was not confirmed.")
        try require(pair.secret != grant.secret && (try store.identity())?.secret == pair.secret, "Pairing key was not rotated.")
        var previousIDs: [String]?
        for _ in 0..<2 {
            let page = try await MacClient.pull(pair, after: 0)
            try require(page.cursor == 2 && !page.more && page.skipped == 0, "Incorrect cursor or skip count.")
            try require(page.sessions.count == 2, "Expected a night and a nap.")
            let ids = page.sessions.map(\.id)
            try require(Set(ids).count == 2 && (previousIDs == nil || ids == previousIDs), "Session identities changed on replay.")
            previousIDs = ids
            let night = page.sessions[0]
            try require(night.version == 1 && night.wakeDate == "2026-11-15", "The wake date changed.")
            try require(night.stages.map(\.kind) == ["core", "deep", "rem", "awake", "core", "rem", "core"], "Stage order changed.")
            try require(night.stages.first?.start == 1_794_726_000 && night.stages.last?.end == 1_794_754_800, "Timestamps changed.")
        }
        let finished = try await MacClient.pull(pair, after: 2)
        try require(finished.cursor == 2 && finished.sessions.isEmpty && !finished.more, "Completed cursor should return an empty page.")
        try require(finished.latestWakeDate == "2026-11-15", "An empty page lost the current latest wake date.")
        do {
            _ = try await MacClient.pull(pair, after: 3)
            throw CheckFailure(message: "The restored Mac's index accepted an obsolete cursor.")
        } catch MacClientError.cursorReset { }
        try await MacClient.unpair(pair)
        try require(try store.identity() == nil, "Remote disconnect failed.")
        print("Verified a synthetic Mac archive through Bonjour pairing, TLS key rotation, authenticated status, replay, cursor recovery, timestamped intervals and disconnect.")
    }
}
