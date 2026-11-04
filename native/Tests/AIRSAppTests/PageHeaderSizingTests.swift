import AppKit
import SwiftUI
import LumenUI
import XCTest
@testable import AIRSApp

final class PageHeaderSizingTests: XCTestCase {
    @MainActor
    func testSplitViewMinimumWidthProbeDoesNotCreateAnOffscreenPage() {
        let subtitle = "Open a saved checkpoint to inspect every selected image and explicitly resume remaining work. Completed reports are never automatically analyzed again."
        let header = NSHostingController(rootView: AppPageHeader(title: "Batch History", subtitle: subtitle) {
            Button("Refresh") {}
        }.lumenPaletteRoot(windowChrome: false).lumenMetrics(.standard))
        let ordinary = header.sizeThatFits(in: CGSize(width: 700, height: 10_000))
        let minimum = header.sizeThatFits(in: CGSize(width: 1, height: 10_000))
        let state = NSHostingController(rootView: LumenEmptyState(systemImage: "clock.arrow.circlepath",
            title: "No saved batches", message: "Analyze Selected Images creates a checkpoint before launching work.")
            .lumenPaletteRoot(windowChrome: false).lumenMetrics(.standard))
        let empty = state.sizeThatFits(in: CGSize(width: 1, height: 1))
        print("Page header sizing: ordinary=\(ordinary), minimum=\(minimum), Lumen state minimum=\(empty)")
        XCTAssertLessThan(minimum.height, 500, "A split view's minimum-width probe must not establish a page taller than the window")
        XCTAssertLessThan(ordinary.height, 160)
        XCTAssertLessThan(empty.height, 500)
    }

}
