import AppKit
import CoreImage
import ServiceManagement

enum PhoneWindow {
    static let agentName = "local.r1bridge.iphone.plist"

    static func directory(home: URL) throws -> URL {
        let base = home.appendingPathComponent("Library/Application Support/R1 Sleep Companion", isDirectory: true)
        try FileManager.default.createDirectory(at: base, withIntermediateDirectories: true,
                                               attributes: [.posixPermissions: 0o700])
        return base
    }

    static func present(in window: NSWindow, home: URL, feedback: @escaping (String) -> Void) {
        let service = SMAppService.agent(plistName: agentName)
        do {
            let store = PhonePairingStore.keychain(base: try directory(home: home))
            if try store.identity()?.tokenDigest != nil {
                let alert = NSAlert()
                alert.messageText = "Paired iPhone"
                let enabled = service.status == .enabled
                func message() -> String {
                    if service.status != .enabled { return "Resume the background service to let this iPhone sync sleep again." }
                    return store.networkProblem ?? "Your iPhone can sync sleep while this Mac is awake. Disconnecting stops future access."
                }
                alert.informativeText = message()

                alert.addButton(withTitle: "Done")
                let disconnect = alert.addButton(withTitle: "Disconnect iPhone")
                disconnect.hasDestructiveAction = true
                if !enabled { alert.addButton(withTitle: "Resume Sync") }
                let refresh = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { _ in
                    let current = message()
                    if alert.informativeText != current { alert.informativeText = current }
                }
                alert.beginSheetModal(for: window) { choice in
                    refresh.invalidate()
                    if choice == .alertThirdButtonReturn {
                        do { try enable(service, feedback: feedback) } catch { feedback(error.localizedDescription) }
                        return
                    }
                    guard choice == .alertSecondButtonReturn else { return }
                    do {
                        try store.disconnect()
                        if service.status != .notRegistered { try service.unregister() }
                        feedback("The iPhone is disconnected.")
                    } catch { feedback(error.localizedDescription) }
                }
                return
            }
            try enable(service, feedback: feedback)
            guard service.status == .enabled else { return }
            let grant = try store.newGrant()
            do { try show(grant: grant, store: store, window: window, feedback: feedback) }
            catch { try store.closeGrant(grant.code); throw error }
        } catch { feedback(error.localizedDescription) }
    }

    private static func enable(_ service: SMAppService, feedback: (String) -> Void) throws {
        if service.status == .notRegistered || service.status == .notFound { try service.register() }
        if service.status == .requiresApproval { SMAppService.openSystemSettingsLoginItems() }
        if service.status != .enabled {
            feedback("Allow the exporter under Login Items & Extensions, then select Pair iPhone again.")
        }
    }

    static func qrImage(for grant: PairingQR) throws -> CGImage {
        let bytes = try JSONEncoder().encode(grant)
        guard let filter = CIFilter(name: "CIQRCodeGenerator") else { throw PhoneError.network }
        filter.setValue(bytes, forKey: "inputMessage")
        filter.setValue("M", forKey: "inputCorrectionLevel")
        guard let qr = filter.outputImage else { throw PhoneError.network }
        // Keep whole square modules with an opaque white quiet zone on either appearance.
        let extent = qr.extent.insetBy(dx: -4, dy: -4)
        let white = CIImage(color: .white).cropped(to: extent)
        let scale = floor(320 / extent.width)
        let framed = qr.composited(over: white).transformed(by: .init(scaleX: scale, y: scale))
        guard let cg = CIContext().createCGImage(framed, from: framed.extent) else { throw PhoneError.network }
        return cg
    }

    private static func show(grant: PairingQR, store: PhonePairingStore, window: NSWindow,
                             feedback: @escaping (String) -> Void) throws {
        let cg = try qrImage(for: grant)
        let side = CGFloat(cg.width)
        let image = NSImageView(frame: NSRect(x: 0, y: 0, width: side, height: side))
        image.image = NSImage(cgImage: cg, size: image.frame.size)
        image.setAccessibilityLabel("One-time iPhone pairing code")
        let alert = NSAlert()
        alert.messageText = "Pair iPhone"
        let instructions = "Open Sleep Sync Companion on your iPhone and tap Scan Mac Code. This code is valid for five minutes."
        alert.informativeText = instructions
        alert.accessoryView = image
        alert.addButton(withTitle: "Cancel")
        var completed = false
        var timer: Timer?
        alert.beginSheetModal(for: window) { _ in
            timer?.invalidate()
            do { try store.closeGrant(grant.code) } catch { feedback(error.localizedDescription); return }
            if completed { feedback("iPhone paired. Your Mac can now deliver sleep updates in the background.") }
        }
        let expiry = Date().addingTimeInterval(300)
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { _ in
            do {
                if let identity = try store.identity(), identity.service == grant.service, identity.tokenDigest != nil {
                    completed = true
                    window.endSheet(alert.window)
                } else if Date() >= expiry {
                    feedback("The code expired. Select Pair iPhone for a new code.")
                    window.endSheet(alert.window)
                } else {
                    let current = store.networkProblem ?? instructions
                    if alert.informativeText != current { alert.informativeText = current }
                }
            } catch {
                feedback(error.localizedDescription)
                window.endSheet(alert.window)
            }
        }
    }
}
