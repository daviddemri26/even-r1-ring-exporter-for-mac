import Foundation

// Run against synthetic sessions on macOS without an iPhone or health database.
@main
enum SleepImportCheck {
    struct Entry {
        let id: String
        let version: Int
        let kind: SleepKind
    }
    enum Failure: Error { case injected }
    final class Store {
        var entries: [String: Entry] = [:]
        var failCleanup = false

        func save(_ session: SleepSession) async throws {
            let batch = try SleepImport(session)
            try await batch.commit { intervals in
                for interval in intervals where (self.entries[interval.identifier]?.version ?? 0) < batch.version {
                    self.entries[interval.identifier] = Entry(id: batch.id, version: batch.version, kind: interval.kind)
                }
            } deleteOlder: { id, version in
                if self.failCleanup { throw Failure.injected }
                self.entries = self.entries.filter { $0.value.id != id || $0.value.version >= version }
            }
        }
    }

    static func night(_ id: String, _ version: Int, _ kinds: [String], start: Double = 0) -> SleepSession {
        SleepSession(id: id, version: version, wakeDate: "2026-11-01",
                     stages: kinds.enumerated().map { index, kind in
                         let begin = start + Double(index) * 30
                         return SleepStage(kind: kind, start: begin, end: begin + 30)
                     })
    }

    static func main() async throws {
        let first = night("night", 1, ["core", "deep", "core", "rem", "awake"])
        let changed = night("night", 2, ["rem", "deep", "core"])
        let nap = night("nap", 1, ["core"], start: 60_000)
        let store = Store()
        try await store.save(first)
        try await store.save(first)
        try await store.save(nap)
        precondition(store.entries.count == 6)

        store.failCleanup = true
        do { try await store.save(changed); fatalError("The interrupted write must fail.") }
        catch Failure.injected { }
        store.failCleanup = false
        try await store.save(changed)
        try await store.save(changed)
        precondition(store.entries.count == 4)
        precondition(store.entries["io.github.daviddemri26.sleepsync.night.0"]?.kind == .rem)
        precondition(store.entries.values.filter { $0.id == "night" }.allSatisfy { $0.version == 2 })
        precondition(store.entries.values.filter { $0.id == "nap" }.count == 1)

        for invalid in [night("night", 3, ["unknown"]), night("night", 0, ["core"]),
                        night("night", 3, []), night("night", 3, ["core"], start: .nan)] {
            do { try await store.save(invalid); fatalError("Invalid session accepted.") }
            catch ImportIssue.invalidSession { }
        }
        let gap = SleepSession(id: "night", version: 3, wakeDate: "2026-11-01",
                               stages: [.init(kind: "core", start: 0, end: 30), .init(kind: "rem", start: 40, end: 70)])
        do { try await store.save(gap); fatalError("Gap accepted.") }
        catch ImportIssue.invalidSession { }
        precondition(store.entries.count == 4)
        print("Verified duplicate suppression, same-day naps, corrected stages, cleanup retry and invalid timelines.")
    }
}
