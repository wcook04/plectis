import CoreGraphics
import Foundation
import Testing
@testable import DemoTakeConsoleApp

@MainActor
struct DisplayPreviewServiceTests {
    @Test
    func emptyRefreshClearsSnapshotState() {
        let preview = DisplayPreviewService()

        preview.refresh(displayIDs: [])

        #expect(preview.thumbnails.isEmpty)
        #expect(preview.lastRefreshed == nil)
        #expect(!preview.isRefreshing)
        #expect(preview.status.contains("No display snapshots"))
    }

    @Test
    func queuedEmptyRefreshClearsInFlightSnapshotResult() async throws {
        let image = try makePreviewImage()
        let preview = DisplayPreviewService { ids in
            try? await Task.sleep(nanoseconds: 50_000_000)
            return ids.map { DisplayPreviewFrame(id: $0, image: image) }
        }

        preview.refresh(displayIDs: [1])
        preview.refresh(displayIDs: [])

        try await waitUntilPreviewSettles(preview)

        #expect(preview.thumbnails.isEmpty)
        #expect(preview.lastRefreshed == nil)
        #expect(!preview.isRefreshing)
        #expect(preview.status.contains("No display snapshots"))
    }

    private func makePreviewImage() throws -> CGImage {
        let colorSpace = CGColorSpaceCreateDeviceRGB()
        let context = try #require(CGContext(
            data: nil,
            width: 1,
            height: 1,
            bitsPerComponent: 8,
            bytesPerRow: 4,
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ))
        context.setFillColor(CGColor(red: 0.1, green: 0.4, blue: 0.9, alpha: 1))
        context.fill(CGRect(x: 0, y: 0, width: 1, height: 1))
        return try #require(context.makeImage())
    }

    private func waitUntilPreviewSettles(_ preview: DisplayPreviewService) async throws {
        let deadline = Date().addingTimeInterval(2)
        while preview.isRefreshing && Date() < deadline {
            try await Task.sleep(nanoseconds: 20_000_000)
        }
    }
}
