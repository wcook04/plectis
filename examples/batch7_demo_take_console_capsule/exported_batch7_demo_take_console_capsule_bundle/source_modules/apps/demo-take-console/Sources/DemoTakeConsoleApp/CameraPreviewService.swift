@preconcurrency import AVFoundation
import Foundation

final class CameraPreviewService: @unchecked Sendable {
    private let session = AVCaptureSession()
    private let queue = DispatchQueue(label: "ai.workflow.demo-take-console.camera-preview")

    func start(preferredDeviceName: String?) throws -> AVCaptureSession {
        guard AVCaptureDevice.authorizationStatus(for: .video) == .authorized else {
            throw PreviewError.cameraPermissionMissing
        }
        guard let device = selectCamera(named: preferredDeviceName) else {
            throw PreviewError.cameraUnavailable
        }

        session.beginConfiguration()
        session.inputs.forEach { session.removeInput($0) }
        session.sessionPreset = .medium
        let input = try AVCaptureDeviceInput(device: device)
        if session.canAddInput(input) {
            session.addInput(input)
        }
        session.commitConfiguration()

        queue.async { [session] in
            if !session.isRunning {
                session.startRunning()
            }
        }
        return session
    }

    func stop() {
        queue.async { [session] in
            if session.isRunning {
                session.stopRunning()
            }
        }
    }

    private func selectCamera(named name: String?) -> AVCaptureDevice? {
        let devices = AVCaptureDevice.DiscoverySession(
            deviceTypes: [.builtInWideAngleCamera, .external],
            mediaType: .video,
            position: .unspecified
        ).devices
        guard let name, !name.isEmpty else {
            return devices.first
        }
        return devices.first { $0.localizedName == name }
            ?? devices.first { $0.localizedName.localizedCaseInsensitiveContains(name) }
            ?? devices.first
    }
}

enum PreviewError: LocalizedError {
    case cameraPermissionMissing
    case cameraUnavailable

    var errorDescription: String? {
        switch self {
        case .cameraPermissionMissing:
            "Camera permission is needed before preview can start."
        case .cameraUnavailable:
            "No local camera was available for preview."
        }
    }
}
