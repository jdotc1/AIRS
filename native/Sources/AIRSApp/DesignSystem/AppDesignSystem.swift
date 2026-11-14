import SwiftUI
import LumenTokens
import LumenUI

/// AIRS-owned symbols identify domain-specific destinations.
enum AppDesign {
    enum Symbol {
        static let audit = "waveform.path"
        static let entitlements = "square.split.2x1"
        static let batch = "square.stack"
        static let history = "clock.arrow.circlepath"
        static let library = "books.vertical"
        static let recovery = "arrow.clockwise"
    }
}

private struct AppDialogSurface: ViewModifier {
    @Environment(\.lumenPalette) private var palette
    func body(content: Content) -> some View {
        content.background(palette[.bgCanvas]).tint(palette[.accent])
    }
}

extension View {
    func appDialogSurface() -> some View { modifier(AppDialogSurface()) }
}
