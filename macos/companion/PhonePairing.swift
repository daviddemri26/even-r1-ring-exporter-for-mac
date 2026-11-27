import CryptoKit
import Darwin
import Foundation
import Security

struct PairingQR: Codable {
    let v: Int
    let service: String
    let secret: Data
    let code: Data
}

struct PhoneIdentity: Codable {
    let service: String
    var secret: Data
    var grantDigest: Data?
    var expires: Date?
    var tokenDigest: Data?
}

enum PhoneError: LocalizedError {
    case storage, paired, network, grant, stale, cursorReset

    var errorDescription: String? {
        switch self {
        case .storage: return "The Mac could not access its pairing details. Unlock the login Keychain and try again."
        case .paired: return "An iPhone is already paired. Disconnect it before pairing another iPhone."
        case .network: return "The local connection could not start. Check Local Network access in System Settings."
        case .grant: return "The pairing code expired. Show a new code on your Mac."
        case .stale: return "Reconnect your iPhone to this Mac."
        case .cursorReset: return "The Mac rebuilt its sleep index. Restart the import from the first available session."
        }
    }
}

// The window and its background agent are the same signed executable. A process
// lock serializes changes to their one login Keychain item, including consumption
// of a pairing grant. Its transport key and credential digests stay on this Mac.
struct PhonePairingStore {
    let base: URL
    var read: () throws -> PhoneIdentity?
    var write: (PhoneIdentity?) throws -> Void
    var now: () -> Date = Date.init

    static func keychain(base: URL) -> Self {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: "Even R1 Ring Exporter - iPhone Pairing",
            kSecAttrAccount as String: "local-sleep-sync-v1"
        ]
        return Self(base: base, read: {
            var find = query
            find[kSecReturnData as String] = true
            var result: CFTypeRef?
            let status = SecItemCopyMatching(find as CFDictionary, &result)
            if status == errSecItemNotFound { return nil }
            guard status == errSecSuccess, let bytes = result as? Data,
                  let identity = try? JSONDecoder().decode(PhoneIdentity.self, from: bytes),
                  identity.secret.count == 32 else { throw PhoneError.storage }
            return identity
        }, write: { identity in
            guard let identity else {
                let status = SecItemDelete(query as CFDictionary)
                guard status == errSecSuccess || status == errSecItemNotFound else { throw PhoneError.storage }
                return
            }
            let bytes = try JSONEncoder().encode(identity)
            let changes = [kSecValueData as String: bytes]
            var status = SecItemUpdate(query as CFDictionary, changes as CFDictionary)
            if status == errSecItemNotFound {
                var insert = query
                insert.merge(changes) { _, value in value }
                status = SecItemAdd(insert as CFDictionary, nil)
            }
            guard status == errSecSuccess else { throw PhoneError.storage }
        })
    }

    private func locked<T>(_ operation: () throws -> T) throws -> T {
        let fd = open(base.appendingPathComponent(".iphone-pairing.lock").path, O_RDWR | O_CREAT | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard fd >= 0 else { throw PhoneError.storage }
        defer { close(fd) }
        guard flock(fd, LOCK_EX) == 0 else { throw PhoneError.storage }
        return try operation()
    }

    private func randomKey() throws -> Data {
        var bytes = [UInt8](repeating: 0, count: 32)
        guard SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes) == errSecSuccess else { throw PhoneError.storage }
        return Data(bytes)
    }

    var signalURL: URL { base.appendingPathComponent(".iphone-pairing.lock") }

    var networkStatusURL: URL { base.appendingPathComponent(".iphone-network-status") }
    var networkProblem: String? {
        guard let message = try? String(contentsOf: networkStatusURL, encoding: .utf8),
              !message.isEmpty else { return nil }
        return message
    }

    private func save(_ value: PhoneIdentity?) throws {
        try write(value)
        try? FileManager.default.removeItem(at: networkStatusURL)
        _ = utimes(signalURL.path, nil)
    }

    func identity() throws -> PhoneIdentity? { try locked { try read() } }

    func newGrant() throws -> PairingQR {
        try locked {
            guard try read()?.tokenDigest == nil else { throw PhoneError.paired }
            var identity = try PhoneIdentity(service: "R1-\(UUID().uuidString.lowercased())", secret: randomKey())
            let code = try randomKey()
            identity.grantDigest = Self.digest(code)
            identity.expires = now().addingTimeInterval(300)
            try save(identity)
            return PairingQR(v: 1, service: identity.service, secret: identity.secret, code: code)
        }
    }

    static func digest(_ key: Data) -> Data { Data(SHA256.hash(data: key)) }

    static func matches(_ key: Data, _ digest: Data?) -> Bool {
        guard key.count == 32, let digest, digest.count == 32 else { return false }
        return zip(Self.digest(key), digest).reduce(UInt8(0)) { $0 | ($1.0 ^ $1.1) } == 0
    }

    func claim(code: Data, token: Data) throws {
        try locked {
            guard token.count == 32, var identity = try read(), identity.tokenDigest == nil,
                  let expiry = identity.expires, expiry > now(), Self.matches(code, identity.grantDigest) else { throw PhoneError.grant }
            identity.secret = SleepWire.pairedSecret(bootstrap: identity.secret, token: token)
            identity.tokenDigest = Self.digest(token)
            identity.grantDigest = nil
            identity.expires = nil
            try save(identity)
        }
    }

    func closeGrant(_ code: Data) throws {
        try locked {
            guard let identity = try read(), Self.matches(code, identity.grantDigest) else { return }
            try save(nil)
        }
    }

    func accepts(_ token: Data) throws -> Bool { try locked { Self.matches(token, try read()?.tokenDigest) } }

    func disconnect(token: Data? = nil) throws {
        try locked {
            if let token {
                guard let identity = try read(), Self.matches(token, identity.tokenDigest) else { throw PhoneError.stale }
            }
            try save(nil)
        }
    }
}
