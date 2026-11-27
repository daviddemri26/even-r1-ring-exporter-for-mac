import Foundation
import HealthKit

struct HealthWriter {
    private let store = HKHealthStore()
    private let type = HKCategoryType(.sleepAnalysis)
    private let nightKey = "io.github.daviddemri26.sleepsync.night"

    var authorization: HKAuthorizationStatus { store.authorizationStatus(for: type) }

    func authorize() async throws {
        guard HKHealthStore.isHealthDataAvailable() else { throw ImportIssue.healthUnavailable }
        try await store.requestAuthorization(toShare: [type], read: [])
        guard authorization == .sharingAuthorized else { throw ImportIssue.healthPermission }
    }

    func save(_ night: SleepSession) async throws {
        let batch = try SleepImport(night)
        try await batch.commit { intervals in
            let samples = intervals.map { interval in
                let value: HKCategoryValueSleepAnalysis
                switch interval.kind {
                case .awake: value = .awake
                case .core: value = .asleepCore
                case .deep: value = .asleepDeep
                case .rem: value = .asleepREM
                }
                let metadata: [String: Any] = [
                    nightKey: batch.id,
                    HKMetadataKeySyncIdentifier: interval.identifier,
                    HKMetadataKeySyncVersion: NSNumber(value: batch.version)
                ]
                return HKCategorySample(type: type, value: value.rawValue, start: interval.start,
                                        end: interval.end, metadata: metadata)
            }
            try await store.save(samples)
        } deleteOlder: { id, version in
            // HealthKit deletes only the caller's own samples. Match one session
            // and strictly older revisions to remove any surplus intervals.
            let stale = NSCompoundPredicate(andPredicateWithSubpredicates: [
                HKQuery.predicateForObjects(withMetadataKey: nightKey, allowedValues: [id]),
                HKQuery.predicateForObjects(withMetadataKey: HKMetadataKeySyncVersion,
                                            operatorType: .lessThan, value: NSNumber(value: version))
            ])
            _ = try await store.deleteObjects(of: type, predicate: stale)
        }
    }
}
