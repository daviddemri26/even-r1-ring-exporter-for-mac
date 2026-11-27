import AVFoundation
import SwiftUI
import UIKit

struct PairingScanner: UIViewControllerRepresentable {
    let onCode: (String) -> Void

    func makeUIViewController(context: Context) -> ScannerController {
        ScannerController(onCode: onCode)
    }

    func updateUIViewController(_ uiViewController: ScannerController, context: Context) {}
}

final class ScannerController: UIViewController, AVCaptureMetadataOutputObjectsDelegate {
    private let session = AVCaptureSession()
    private let cameraQueue = DispatchQueue(label: "io.github.daviddemri26.sleepsync.camera")
    private let onCode: (String) -> Void
    private var preview: AVCaptureVideoPreviewLayer?
    private var active = false
    private var delivered = false

    init(onCode: @escaping (String) -> Void) {
        self.onCode = onCode
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { nil }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .black
        let layer = AVCaptureVideoPreviewLayer(session: session)
        layer.videoGravity = .resizeAspectFill
        view.layer.addSublayer(layer)
        preview = layer
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        preview?.frame = view.bounds
        if let orientation = view.window?.windowScene?.interfaceOrientation,
           let connection = preview?.connection {
            let angles: [UIInterfaceOrientation: CGFloat] = [
                .portrait: 90, .portraitUpsideDown: 270, .landscapeLeft: 180, .landscapeRight: 0
            ]
            if let angle = angles[orientation], connection.isVideoRotationAngleSupported(angle) {
                connection.videoRotationAngle = angle
            }
        }
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        active = true
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized: startCamera()
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { [weak self] allowed in
                DispatchQueue.main.async {
                    guard let self, self.active else { return }
                    if allowed { self.startCamera() } else { self.showFailure(denied: true) }
                }
            }
        default: showFailure(denied: true)
        }
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        active = false
        let session = session
        cameraQueue.async { if session.isRunning { session.stopRunning() } }
    }

    private func startCamera() {
        cameraQueue.async { [weak self] in
            guard let self else { return }
            do {
                if self.session.inputs.isEmpty {
                    guard let camera = AVCaptureDevice.default(for: .video) else { throw CameraError.unavailable }
                    let input = try AVCaptureDeviceInput(device: camera)
                    let output = AVCaptureMetadataOutput()
                    self.session.beginConfiguration()
                    defer { self.session.commitConfiguration() }
                    guard self.session.canAddInput(input) else { throw CameraError.unavailable }
                    self.session.addInput(input)
                    guard self.session.canAddOutput(output) else {
                        self.session.removeInput(input)
                        throw CameraError.unavailable
                    }
                    self.session.addOutput(output)
                    output.setMetadataObjectsDelegate(self, queue: .main)
                    output.metadataObjectTypes = [.qr]
                }
                self.session.startRunning()
            } catch {
                DispatchQueue.main.async { if self.active { self.showFailure(denied: false) } }
            }
        }
    }

    private func showFailure(denied: Bool) {
        let message = UILabel()
        message.text = denied ? "Allow camera access in Settings to scan the QR code on your Mac." : "The camera is unavailable. Close the scanner and try again on your iPhone."
        message.textColor = .white
        message.textAlignment = .center
        message.numberOfLines = 0
        message.font = .preferredFont(forTextStyle: .body)
        message.adjustsFontForContentSizeCategory = true
        let items = UIStackView(arrangedSubviews: [message])
        items.axis = .vertical
        items.spacing = 16
        if denied {
            let button = UIButton(type: .system)
            button.configuration = .tinted()
            button.setTitle("Open Settings", for: .normal)
            button.addAction(UIAction { _ in
                if let url = URL(string: UIApplication.openSettingsURLString) { UIApplication.shared.open(url) }
            }, for: .touchUpInside)
            items.addArrangedSubview(button)
        }
        items.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(items)
        NSLayoutConstraint.activate([
            items.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            items.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 28),
            items.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -28)
        ])
    }

    func metadataOutput(_ output: AVCaptureMetadataOutput, didOutput metadataObjects: [AVMetadataObject],
                        from connection: AVCaptureConnection) {
        guard active, !delivered,
              let code = metadataObjects.compactMap({ ($0 as? AVMetadataMachineReadableCodeObject)?.stringValue }).first else { return }
        delivered = true
        onCode(code)
    }

    private enum CameraError: Error { case unavailable }
}
