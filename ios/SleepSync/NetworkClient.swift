import Foundation
import Network
import os
import Security

enum MacClient {
    private struct Code: Decodable {
        let v: Int
        let service: String
        let secret: Data
        let code: Data
    }

    private struct Request: Encodable {
        let op: String
        let token: Data
        var code: Data?
        var after: Int?
    }

    private struct Reply: Decodable {
        var ok: Bool?
        var name: String?
        var error: String?
    }

    static func pair(qr: String) async throws -> MacPair {
        guard qr.utf8.count <= 1024,
              let scan = try? JSONDecoder().decode(Code.self, from: Data(qr.utf8)),
              scan.v == 1, (1...63).contains(scan.service.utf8.count),
              !scan.service.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }),
              scan.secret.count == 32, scan.code.count == 32 else { throw MacClientError.invalidCode }
        var token = Data(count: 32)
        let status = token.withUnsafeMutableBytes { SecRandomCopyBytes(kSecRandomDefault, $0.count, $0.baseAddress!) }
        guard status == errSecSuccess else { throw MacClientError.unavailable }
        let secret = SleepWire.pairedSecret(bootstrap: scan.secret, token: token)
        let request = Request(op: "pair", token: token, code: scan.code)
        let confirmedName: String?
        do {
            let response = try await exchange(request, service: scan.service, secret: scan.secret)
            guard response.reply.ok == true, let name = response.reply.name else { throw MacClientError.invalidCode }
            confirmedName = name
        } catch MacClientError.waiting {
            // The response can be lost after the Mac consumes the one-time code.
            confirmedName = nil
        }
        let probe = Request(op: "status", token: token)
        for attempt in 0..<5 {
            do {
                let result = try await exchange(probe, service: scan.service, secret: secret, timeout: 4)
                guard result.reply.ok == true, let name = result.reply.name else { throw MacClientError.invalidCode }
                return MacPair(service: scan.service, secret: secret, token: token, name: name)
            } catch let error as MacClientError {
                switch error {
                case .waiting, .unpaired:
                    if attempt == 4 {
                        // Keep a confirmed credential if the paired listener will only
                        // become reachable later, for example after Wi-Fi disconnects.
                        if let name = confirmedName {
                            return MacPair(service: scan.service, secret: secret, token: token, name: name)
                        }
                        throw MacClientError.invalidCode
                    }
                    try await Task.sleep(for: .milliseconds(400))
                default: throw error
                }
            }
        }
        throw MacClientError.waiting
    }

    static func pull(_ pair: MacPair, after: Int) async throws -> SleepPage {
        let request = Request(op: "pull", token: pair.token, after: after)
        let response = try await exchange(request, service: pair.service, secret: pair.secret)
        guard let page = try? JSONDecoder().decode(SleepPage.self, from: response.data),
              page.skipped >= 0, page.cursor >= after,
              page.cursor > after || (page.sessions.isEmpty && !page.more)
        else { throw MacClientError.ambiguous }
        return page
    }

    static func unpair(_ pair: MacPair) async throws {
        let response = try await exchange(Request(op: "unpair", token: pair.token),
                                          service: pair.service, secret: pair.secret)
        guard response.reply.ok == true else { throw MacClientError.unavailable }
    }

    private static func exchange(_ request: Request, service: String, secret: Data, timeout: Int? = nil) async throws -> (data: Data, reply: Reply) {
        try Task.checkCancellation()
        let endpoint = NWEndpoint.service(name: service, type: SleepWire.serviceType, domain: "local.", interface: nil)
        let connection = NWConnection(to: endpoint, using: SleepWire.parameters(secret: secret))
        let queue = DispatchQueue(label: "io.github.daviddemri26.sleepsync.connection")
        let deadline = DispatchSource.makeTimerSource(queue: queue)
        deadline.schedule(deadline: .now() + .seconds(timeout ?? (request.op == "pull" ? 95 : 12)))
        deadline.setEventHandler { connection.cancel() }
        deadline.resume()
        defer { deadline.cancel(); connection.cancel() }
        let denied = OSAllocatedUnfairLock(initialState: false)
        return try await withTaskCancellationHandler {
            connection.stateUpdateHandler = { state in
                guard case .waiting(let error) = state else { return }
                if connection.currentPath?.unsatisfiedReason == .localNetworkDenied || error == .dns(-65570) {
                    denied.withLock { $0 = true }
                    connection.cancel()
                }
            }
            connection.start(queue: queue)
            let data: Data
            do {
                try await SleepWire.send(JSONEncoder().encode(request), on: connection)
                data = try await SleepWire.receive(connection)
            } catch {
                try Task.checkCancellation()
                if denied.withLock({ $0 }) || connection.currentPath?.unsatisfiedReason == .localNetworkDenied {
                    throw MacClientError.localNetwork
                }
                if case NWError.tls = error { throw request.op == "pair" ? MacClientError.invalidCode : MacClientError.unpaired }
                throw MacClientError.waiting
            }
            guard let reply = try? JSONDecoder().decode(Reply.self, from: data) else { throw MacClientError.ambiguous }
            switch reply.error {
            case nil: return (data, reply)
            case "unpaired": throw MacClientError.unpaired
            case "pairing": throw MacClientError.invalidCode
            case "cursorReset": throw MacClientError.cursorReset
            default: throw MacClientError.unavailable
            }
        } onCancel: {
            connection.cancel()
        }
    }
}
