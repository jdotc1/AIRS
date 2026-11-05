# Known macOS limitations

## Window-sharing indicator geometry diagnostics

On macOS 27.3 (build 26C5035r), window capture can produce AppKit diagnostics:

```text
Invalid view geometry: width is negative.
Invalid view geometry: height is negative.
```

A targeted debugger investigation caught a width of `-1` being passed to
`NSView.setFrameSize` for the system-owned
`NSWindowSharingSessionRecipientIndicator`. The stack traversed
`NSThemeFrame._positionSharingIndicator`, intrinsic-content-size invalidation,
and a selective-window-sharing-state notification. These private symbol names
identify the observed system stack; AIRS does not call them.

A minimal standalone AppKit application containing only a standard titled,
resizable `NSWindow` reproduced three width and three height diagnostics during
window capture. It used no AIRS, SwiftUI, or Lumen code. This isolates the observed
failure from AIRS content layout on the tested macOS build. It does not establish
behavior on other macOS versions or explain unrelated geometry warnings.

No supported public application API was identified for repairing the system
indicator's layout. AIRS does not suppress the diagnostics, modify private AppKit
implementation, disable window capture, or change permissions to hide them.

The investigation is closed as a documented macOS limitation. AIRS 0.3.4 build 25
remains the current release; no replacement binary is required for this finding.
Existing signing, notarization and qualification evidence retains its recorded
scope. No accepted tests, signing checks, or provenance hashes were repeated.
Revisit this finding only when new evidence or a supported platform workaround
becomes available.
