import SwiftUI
import UIKit

struct SleepView: View {
    @ObservedObject var controller: SleepController
    @Environment(\.colorScheme) private var scheme
    @Environment(\.dynamicTypeSize) private var typeSize
    @Environment(\.openURL) private var openURL
    @State private var scanner = false
    @State private var details = false
    @State private var disconnect = false
    @State private var forget = false

    private let guide = "https://daviddemri26.github.io/even-r1-ring-exporter-for-mac/companion/"
    private var tint: Color { scheme == .dark ? Color(red: 0.50, green: 0.85, blue: 0.78) : Color(red: 0.10, green: 0.36, blue: 0.32) }
    private var canvas: Color { scheme == .dark ? Color(red: 0.06, green: 0.10, blue: 0.10) : Color(red: 0.97, green: 0.98, blue: 0.96) }
    private var panelColor: Color { scheme == .dark ? Color.white.opacity(0.06) : .white }

    var body: some View {
        NavigationStack {
            GeometryReader { geometry in
                ScrollView {
                    VStack(alignment: .leading, spacing: 24) {
                        visual
                            .accessibilityHidden(true)
                        VStack(alignment: .leading, spacing: 10) {
                            Text(title)
                                .font(.system(.largeTitle, design: .rounded, weight: .semibold))
                                .accessibilityAddTraits(.isHeader)
                            if let subtitle { Text(subtitle).font(.body).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true) }
                        }
                        if controller.isPaired { summary }
                        if controller.skipped > 0 {
                            Text(controller.skipped == 1 ? "1 item needs review on your Mac." : "\(controller.skipped) items need review on your Mac.")
                                .font(.footnote).foregroundStyle(.secondary)
                        }
                        Spacer(minLength: 4)
                        actions
                    }
                    .padding(24)
                    .frame(maxWidth: 600, alignment: .leading)
                    .frame(minHeight: geometry.size.height)
                    .frame(maxWidth: .infinity)
                }
            }
            .background(canvas)
            .navigationTitle("Sleep Sync")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { details = true } label: { Image(systemName: "ellipsis.circle") }
                        .accessibilityLabel("Connection and help")
                }
            }
            .sheet(isPresented: $scanner) {
                NavigationStack {
                    VStack(spacing: 0) {
                        PairingScanner { code in
                            scanner = false
                            Task { await controller.pair(code: code) }
                        }
                        Text("Point your camera at the code displayed by the Mac exporter.")
                            .font(.callout).multilineTextAlignment(.center).padding()
                    }
                    .navigationTitle("Scan Mac Code").navigationBarTitleDisplayMode(.inline)
                    .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Cancel") { scanner = false } } }
                }
            }
            .sheet(isPresented: $details) { connectionDetails }
            .alert("Connection", isPresented: Binding(get: { controller.notice != nil }, set: { if !$0 { controller.notice = nil } })) {
                Button("OK") { controller.notice = nil }
            } message: { Text(controller.notice ?? "") }
        }
        .tint(tint)
    }

    private var visual: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 28, style: .continuous)
                .fill(scheme == .dark ? Color(red: 0.12, green: 0.19, blue: 0.18) : Color(red: 0.88, green: 0.93, blue: 0.89))
            Canvas { context, size in
                let center = CGPoint(x: size.width * 0.50, y: size.height * 0.50)
                let radius = min(size.height * 0.32, size.width * 0.17)
                // Paired arcs share one orbit. Their inner gap reads clearly at larger text sizes.
                for (inset, start, end, opacity) in [(0.0, -133.0, 126.0, 1.0), (0.22, 46.0, 302.0, 0.56)] {
                    var path = Path()
                    path.addArc(center: center, radius: radius * (1 - inset),
                                startAngle: .degrees(start), endAngle: .degrees(end), clockwise: false)
                    context.stroke(path, with: .color(tint.opacity(opacity)),
                                   style: StrokeStyle(lineWidth: radius * 0.135, lineCap: .round))
                }
            }
        }
        .frame(height: typeSize.isAccessibilitySize ? 102 : (controller.isPaired ? 148 : 198))
    }

    private var title: String {
        switch controller.state {
        case .setup: return "Connect your Mac"
        case .pairing: return "Pairing with Mac"
        case .ready: return "Ready to sync"
        case .syncing: return "Syncing sleep"
        case .current: return controller.latestWake == nil ? "No nights yet" : "Up to date"
        case .waiting: return "Waiting for Mac"
        case .network: return "Allow local access"
        case .health: return "Allow Sleep access"
        case .incompatible: return "Health unavailable"
        case .needsPair: return "Pair your Mac again"
        case .retry: return "Check your Mac"
        case .invalid: return "Check the export"
        case .storage: return "Unlock your iPhone"
        }
    }

    private var subtitle: String? {
        switch controller.state {
        case .setup: return "Bring your ring’s sleep history into Apple Health. Open Even R1 Ring Exporter for Mac and choose Pair iPhone."
        case .pairing: return "Keep the code open on your Mac."
        case .ready: return "Your next sync checks your Mac for new sleep."
        case .syncing: return controller.progress == 0 ? "Checking your Mac for sleep sessions…" : "\(controller.progress) sleep sessions saved to Apple Health."
        case .current:
            if controller.demo { return "This preview uses sample sleep data." }
            return controller.latestWake == nil ? "Your next verified sleep session will appear in Apple Health." : "Your verified sleep sessions are in Apple Health."
        case .waiting: return "Your Mac keeps new nights until both devices reconnect on the same local network."
        case .network: return "Turn on Local Network for Sleep Sync Companion in iPhone Settings."
        case .health: return controller.healthDenied ? "In Health, tap your profile, then Apps and Services. Allow Sleep Sync Companion to write Sleep." : "Allow this app to save verified sleep stages to Apple Health."
        case .incompatible: return "Apple Health must be available on this iPhone."
        case .needsPair: return "Open Pair iPhone in the Mac exporter and scan a new code."
        case .retry: return "Open the exporter on your Mac, verify a local export, then try again."
        case .invalid: return "Update the exporter on your Mac and verify its last sleep export."
        case .storage: return "Your saved connection is unavailable. Unlock your iPhone and try again."
        }
    }

    private var summary: some View {
        VStack(spacing: 12) {
            detailRow("macbook", "Mac", controller.macName ?? "Paired Mac")
            Divider()
            detailRow("arrow.triangle.2.circlepath", "Last sync", controller.checked?.formatted(date: .abbreviated, time: .shortened) ?? "Pending")
            Divider()
            detailRow("moon", "Latest night", formattedNight)
        }
        .padding(18)
        .background(panelColor, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
    }

    private var formattedNight: String {
        guard let raw = controller.latestWake else { return "Pending" }
        var parser = Date.ISO8601FormatStyle().year().month().day()
        parser.timeZone = .gmt
        guard let date = try? parser.parse(raw) else { return raw }
        var format = Date.FormatStyle(date: .abbreviated, time: .omitted)
        format.timeZone = .gmt
        return date.formatted(format)
    }

    private func detailRow(_ symbol: String, _ label: LocalizedStringKey, _ value: String) -> some View {
        ViewThatFits(in: .horizontal) {
            HStack(spacing: 12) {
                Label(label, systemImage: symbol).foregroundStyle(.secondary)
                Spacer(minLength: 12)
                Text(value).multilineTextAlignment(.trailing)
            }
            VStack(alignment: .leading, spacing: 4) {
                Label(label, systemImage: symbol).foregroundStyle(.secondary)
                Text(value)
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
        .font(.subheadline)
        .accessibilityElement(children: .combine)
    }

    @ViewBuilder private var actions: some View {
        if controller.working {
            HStack { Spacer(); ProgressView(); Spacer() }.padding()
        } else if controller.state == .network {
            primary("Open Settings", "gearshape") { openSettings() }
        } else if controller.state == .health {
            if controller.healthDenied {
                primary("Check Access", "heart") { Task { await controller.onActive() } }
            } else {
                primary("Allow Sleep Access", "heart") { Task { await controller.enableHealth() } }
            }
        } else if controller.state == .storage {
            primary("Try Again", "arrow.clockwise") { Task { await controller.onActive() } }
        } else if !controller.isPaired || controller.state == .needsPair {
            primary("Scan Mac Code", "qrcode.viewfinder") { scanner = true }
        } else {
            Button { Task { _ = await controller.sync() } } label: {
                Label("Sync Now", systemImage: "arrow.clockwise").frame(maxWidth: .infinity)
            }.buttonStyle(.bordered).controlSize(.large)
        }
    }

    private func primary(_ label: LocalizedStringKey, _ symbol: String, _ action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Label(label, systemImage: symbol)
                .fontWeight(.semibold)
                .foregroundStyle(scheme == .dark ? Color.black : Color.white)
                .frame(maxWidth: .infinity, minHeight: 28)
        }.buttonStyle(.borderedProminent).controlSize(.large)
    }

    private func openSettings() {
        if let settings = URL(string: UIApplication.openSettingsURLString) { openURL(settings) }
    }

    private var connectionDetails: some View {
        NavigationStack {
            List {
                if !controller.isPaired {
                    Section { Button("Try a Preview") { details = false; controller.showDemo() } }
                } else if controller.demo {
                    Section("Preview") {
                        Button("Show Waiting for Mac") { controller.showDemo(waiting: true); details = false }
                        Button("End Preview") { controller.endDemo(); details = false }
                    }
                } else {
                    Section("Automation") {
                        Text("Sync runs when you open the app and when iOS allows background refresh. For a Wi-Fi or morning trigger, create a personal automation in Shortcuts and add Sync Sleep.")
                    }
                    Section("Connection") {
                        Button("Disconnect Mac", role: .destructive) { disconnect = true }
                            .confirmationDialog("Disconnect this Mac and iPhone?", isPresented: $disconnect, titleVisibility: .visible) {
                                Button("Disconnect", role: .destructive) { details = false; Task { await controller.disconnect() } }
                            } message: { Text("Sleep already saved stays in Apple Health.") }
                        Button("Forget on This iPhone", role: .destructive) { forget = true }
                            .confirmationDialog("Remove this iPhone’s saved connection?", isPresented: $forget, titleVisibility: .visible) {
                                Button("Forget Connection", role: .destructive) { details = false; Task { await controller.disconnect(localOnly: true) } }
                            } message: { Text("You can also revoke pairing on your Mac. Sleep already saved stays in Apple Health.") }
                    }.disabled(controller.working)
                }
                Section {
                    Link("Setup and Support", destination: URL(string: guide + "#support")!)
                    Link("Privacy", destination: URL(string: guide + "#privacy")!)
                }
            }
            .navigationTitle("Connection and Help")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { details = false } } }
        }
        .presentationDetents([.medium, .large])
    }
}
