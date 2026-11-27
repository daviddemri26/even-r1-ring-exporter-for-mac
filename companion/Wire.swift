import CryptoKit
import Foundation
import Network
import Security

/// One length-prefixed JSON request and response per authenticated, local TCP connection.
enum SleepWire {
    static let serviceType = "_sleepsync._tcp"
    static let maxFrame = 8 * 1024 * 1024

    enum FrameError: Error { case invalidLength, disconnected }

    static func pairedSecret(bootstrap: Data, token: Data) -> Data {
        let key = HKDF<SHA256>.deriveKey(inputKeyMaterial: SymmetricKey(data: bootstrap),
                                         salt: token, info: Data("Sleep Sync paired transport v1".utf8),
                                         outputByteCount: 32)
        return key.withUnsafeBytes { Data($0) }
    }

    static func parameters(secret: Data) -> NWParameters {
        let tls = NWProtocolTLS.Options()
        let options = tls.securityProtocolOptions
        sec_protocol_options_set_min_tls_protocol_version(options, .TLSv12)
        sec_protocol_options_set_max_tls_protocol_version(options, .TLSv12)
        let suite = tls_ciphersuite_t(rawValue: UInt16(TLS_PSK_WITH_AES_128_GCM_SHA256))!
        sec_protocol_options_append_tls_ciphersuite(options, suite)
        let identity = Data("sleep-sync-v1".utf8)
        sec_protocol_options_add_pre_shared_key(options,
            secret.withUnsafeBytes { DispatchData(bytes: $0) } as __DispatchData,
            identity.withUnsafeBytes { DispatchData(bytes: $0) } as __DispatchData)
        let parameters = NWParameters(tls: tls, tcp: NWProtocolTCP.Options())
        parameters.prohibitedInterfaceTypes = [.cellular]
        return parameters
    }

    static func send(_ data: Data, on connection: NWConnection) async throws {
        guard (1...maxFrame).contains(data.count) else { throw FrameError.invalidLength }
        var length = UInt32(data.count).bigEndian
        var frame = withUnsafeBytes(of: &length) { Data($0) }
        frame.append(data)
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            connection.send(content: frame, completion: .contentProcessed { error in
                if let error { continuation.resume(throwing: error) }
                else { continuation.resume() }
            })
        }
    }

    static func receive(_ connection: NWConnection, limit: Int = maxFrame) async throws -> Data {
        let header = try await read(4, from: connection)
        let length = header.reduce(0) { $0 * 256 + Int($1) }
        guard length > 0, length <= min(limit, maxFrame) else { throw FrameError.invalidLength }
        return try await read(length, from: connection)
    }

    private static func read(_ length: Int, from connection: NWConnection) async throws -> Data {
        var result = Data()
        while result.count < length {
            let remaining = length - result.count
            let chunk: Data = try await withCheckedThrowingContinuation { continuation in
                connection.receive(minimumIncompleteLength: 1, maximumLength: remaining) { data, _, _, error in
                    if let error { continuation.resume(throwing: error) }
                    else if let data, !data.isEmpty { continuation.resume(returning: data) }
                    else { continuation.resume(throwing: FrameError.disconnected) }
                }
            }
            result.append(chunk)
        }
        return result
    }
}
