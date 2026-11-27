import Foundation

enum ImportIssue: Error {
    case healthUnavailable, healthPermission, invalidSession, protectedStorage, storage
}

enum SleepKind: String {
    case awake, core, deep, rem
}

struct SleepInterval {
    let identifier: String
    let kind: SleepKind
    let start: Date
    let end: Date
}

/// An entire verified session is validated before its first write. Replaying a page
/// reuses its HealthKit identifiers, even if the previous run stopped before cleanup.
struct SleepImport {
    let id: String
    let version: Int
    let intervals: [SleepInterval]

    init(_ session: SleepSession) throws {
        guard !session.id.isEmpty, session.version > 0, !session.stages.isEmpty else { throw ImportIssue.invalidSession }
        var previousEnd: Double?
        intervals = try session.stages.enumerated().map { index, stage in
            guard let kind = SleepKind(rawValue: stage.kind), stage.start.isFinite, stage.end.isFinite,
                  stage.start < stage.end, previousEnd == nil || stage.start == previousEnd else { throw ImportIssue.invalidSession }
            previousEnd = stage.end
            return SleepInterval(identifier: "io.github.daviddemri26.sleepsync.\(session.id).\(index)",
                                 kind: kind, start: Date(timeIntervalSince1970: stage.start),
                                 end: Date(timeIntervalSince1970: stage.end))
        }
        id = session.id
        version = session.version
    }

    func commit(upsert: ([SleepInterval]) async throws -> Void,
                deleteOlder: (String, Int) async throws -> Void) async throws {
        try await upsert(intervals)
        if version > 1 { try await deleteOlder(id, version) }
    }
}
