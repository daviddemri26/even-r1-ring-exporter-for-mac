import Foundation

struct MacPair: Codable {
    let service: String
    let secret: Data
    let token: Data
    let name: String
}

struct SleepPage: Codable {
    let sessions: [SleepSession]
    let cursor: Int
    let more: Bool
    let skipped: Int
    var latestWakeDate: String? = nil
}

struct SleepSession: Codable {
    let id: String
    let version: Int
    let wakeDate: String
    let stages: [SleepStage]
}

struct SleepStage: Codable {
    let kind: String
    let start: Double
    let end: Double
}

enum MacClientError: LocalizedError {
    case waiting, unpaired, invalidCode, unavailable, localNetwork, ambiguous, cursorReset
    var errorDescription: String? {
        switch self {
        case .waiting: return "Waiting for Mac. Check that your Mac is awake and both devices are on the same local network."
        case .unpaired: return "Pair this iPhone again using a new code from your Mac."
        case .invalidCode: return "Open Pair iPhone on your Mac and scan the new code."
        case .unavailable: return "Open the exporter on your Mac and check its last export. Then try again."
        case .localNetwork: return "Allow Local Network access in Settings to reach your Mac."
        case .cursorReset: return "The Mac rebuilt its sleep index. Sync again to refresh your history."
        case .ambiguous: return "The Mac sent an unreadable sleep update. Update the exporter and try again."
        }
    }
}
