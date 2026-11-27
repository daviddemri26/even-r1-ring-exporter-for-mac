import Foundation

/// Runs only in the packaged --verify-install path, using an in-memory credential.
func verifyPhonePairing(base: URL) throws {
    func checked(_ result: Bool, _ message: String) throws {
        if !result { throw NSError(domain: "PhonePairingTest", code: 1, userInfo: [NSLocalizedDescriptionKey: message]) }
    }
    var identity: PhoneIdentity?
    var now = Date(timeIntervalSince1970: 1_000_000)
    let store = PhonePairingStore(base: base, read: { identity }, write: { identity = $0 }, now: { now })
    let token = Data(repeating: 0x2a, count: 32)
    let other = Data(repeating: 0x55, count: 32)
    let page = Data(#"{"sessions":[],"cursor":0,"more":false,"skipped":0}"#.utf8)
    // Exercise the real process exit-code mapping with an isolated script.
    let testRuntime = base.appendingPathComponent("runtime")
    try FileManager.default.createDirectory(at: testRuntime, withIntermediateDirectories: true)
    try Data("import sys\nsys.exit(3 if sys.argv[1] == '9' else 1)\n".utf8)
        .write(to: testRuntime.appendingPathComponent("sleep_feed.py"))
    let router = PhoneRouter(store: store, name: "Test Mac", feed: { cursor in
        if cursor == 0 { return page }
        return try readPhoneFeed(resources: base, after: cursor)
    })
    func request(_ op: String, _ snapshot: PhoneIdentity, code: Data? = nil, key: Data = token, after: Int = 0) throws -> Data {
        var fields: [String: Any] = ["op": op, "token": key.base64EncodedString(), "after": after]
        if let code { fields["code"] = code.base64EncodedString() }
        return try router.reply(JSONSerialization.data(withJSONObject: fields), identity: snapshot)
    }
    let expired = try store.newGrant()
    now = now.addingTimeInterval(301)
    try checked(try request("pair", identity!, code: expired.code) == Data(#"{"error":"pairing"}"#.utf8), "Expired grant accepted.")
    let grant = try store.newGrant()
    let pending = identity!
    try checked(expired.secret != grant.secret && expired.service != grant.service, "Pairing key reused.")
    try checked(try request("pull", pending) != page, "Unpaired pull succeeded.")
    try checked(try request("pair", pending, code: expired.code) == Data(#"{"error":"pairing"}"#.utf8), "Stale code accepted.")
    let reply = try JSONSerialization.jsonObject(with: request("pair", pending, code: grant.code)) as? [String: Any]
    try checked(reply?["ok"] as? Bool == true, "Valid pairing failed.")
    let paired = identity!
    try checked(paired.secret == SleepWire.pairedSecret(bootstrap: grant.secret, token: token), "Transport key did not rotate.")
    try checked(try request("pull", pending) != page, "Old pairing socket gained access.")
    try checked(try request("pull", paired, key: other) != page, "Wrong phone gained access.")
    let status = try JSONSerialization.jsonObject(with: request("status", paired)) as? [String: Any]
    try checked(status?["ok"] as? Bool == true && status?["name"] as? String == "Test Mac", "Could not confirm paired key.")
    for _ in 0..<2 { try checked(try request("pull", paired) == page, "Paired pull failed.") }
    try checked(try request("pull", paired, after: 9) == Data(#"{"error":"cursorReset"}"#.utf8), "A rebuilt cursor was not recognized.")
    try checked(try request("pull", paired, after: 8) == Data(#"{"error":"unavailable"}"#.utf8), "A feed error cleared a valid cursor.")
    let denied = PhoneServer.networkProblem(.dns(-65570))
    try Data(denied.utf8).write(to: store.networkStatusURL)
    try checked(store.networkProblem == denied && denied.contains("Privacy & Security → Local Network"), "Missing local network recovery.")
    try Data().write(to: store.networkStatusURL)
    try checked(store.networkProblem == nil, "The ready listener still shows an error.")
    try store.closeGrant(grant.code)
    try checked(try store.accepts(token), "Closing the used QR disconnected the phone.")
    try checked(try request("unpair", paired) == Data(#"{"ok":true}"#.utf8), "Remote revocation failed.")
    try checked(try request("pull", paired) != page && identity == nil, "Disconnected phone retained access.")
    let unused = try store.newGrant()
    try store.closeGrant(unused.code)
    try checked(identity == nil, "Canceled grant survived.")
}
