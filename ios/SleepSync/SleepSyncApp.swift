import AppIntents
import BackgroundTasks
import SwiftUI
import UIKit

@main
struct SleepSyncApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var delegate
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var controller = SleepController.shared

    var body: some Scene {
        WindowGroup {
            SleepView(controller: controller)
                .task { await controller.onActive() }
                .onChange(of: scenePhase) { _, phase in
                    if phase == .active { Task { await controller.onActive() } }
                    if phase == .background && controller.schedulesRefresh { Refresh.schedule() }
                }
        }
    }
}

private enum Refresh {
    static let id = "io.github.daviddemri26.sleepsync.refresh"

    static func schedule() {
        let request = BGAppRefreshTaskRequest(identifier: id)
        request.earliestBeginDate = Date(timeIntervalSinceNow: 60 * 60)
        do { try BGTaskScheduler.shared.submit(request) }
        catch { /* The next app launch or Shortcuts automation can retry. */ }
    }
}

private final class AppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        BGTaskScheduler.shared.register(forTaskWithIdentifier: Refresh.id, using: .main) { task in
            let work = Task { @MainActor in
                let controller = SleepController.shared
                if controller.schedulesRefresh { Refresh.schedule() }
                let result = await controller.sync()
                task.setTaskCompleted(success: result && !Task.isCancelled)
            }
            task.expirationHandler = { work.cancel() }
        }
        return true
    }
}

struct SyncSleepIntent: AppIntent {
    static let title: LocalizedStringResource = "Sync Sleep"
    static let description = IntentDescription("Import sleep from your paired Mac into Apple Health.")
    static let openAppWhenRun = false

    @MainActor
    func perform() async throws -> some IntentResult & ProvidesDialog {
        let controller = SleepController.shared
        guard controller.schedulesRefresh else { return .result(dialog: "Open Sleep Sync Companion to pair your Mac.") }
        if await controller.sync() { return .result(dialog: "Sleep is up to date.") }
        if controller.state == .waiting { return .result(dialog: "Waiting for Mac. Try again on the same Wi-Fi.") }
        return .result(dialog: "Open Sleep Sync Companion to check your connection and permissions.")
    }
}

struct SleepShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(intent: SyncSleepIntent(),
                    phrases: ["Sync my sleep with \(.applicationName)"],
                    shortTitle: "Sync Sleep", systemImageName: "moon.zzz")
    }
}
