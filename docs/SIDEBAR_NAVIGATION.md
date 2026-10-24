# Sidebar navigation and sizing corrections

The build 12 source includes two accepted UI corrections. The page-header subtitle
now uses the existing bounded Lumen wrapping helper, preventing a split-view
minimum-width measurement from displacing the persistent sidebar outside the window.
The sidebar now uses the complete LumenSourceList component with a binding to the
existing AIRS navigation admission checks.

The previous custom ScrollView and plain-button wrapper could draw rows out of
alignment with their native hit regions under the toolbar. Accessibility activation
could pass while a mouse click activated a different row, appearing to flash or
revert. Tracing the empty batch-history transition found that history completion
updates entries and status, not the selected destination. The evidence identified
an AIRS integration defect; it did not establish a global Lumen defect. Lumen already
provides the complete toolbar-safe source-list layout and input handling.

Retained acceptance includes the focused page-header sizing regression, an isolated
81-pair navigation-state check after asynchronous settlement, and physical mouse
selection of all nine destinations at both 1240 by 800 and 1031 by 805. The signed,
notarized and installed build 12 passed all nine physical mouse checks again after
pending work settled. Exactly the intended destination remained selected and all
nine rows remained present. Navigation did not start image analysis or comparison.
The bounded installed-process diagnostic query found no AttributeGraph,
publishing-during-update or fatal-error messages.

Existing busy, modal, error and unsaved-checkpoint admission guards remain in force.
The source-list component rejects disallowed choices through the existing guard;
blocked rows no longer have the old custom per-row disabled styling during an
unsaved checkpoint. No engine semantics or vendor implementation changed.

These are retained results for their named source/artifact boundaries. The migration
reuses them and the unchanged engine, helper and private Python receipts. It does not
claim clean-machine or minimum-macOS acceptance, and it does not publish build 12.
Private raw logs, machine paths, settings, stores and signing credentials are omitted.
