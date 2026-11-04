# EntitlementDiff reusable modules

This bounded snapshot is adapted from the owner-authored EntitlementDiff modules.

Core, Model, Security and CLIKit sources and LICENSE are copied unchanged from Git,
not from the historical integration ZIP. Package.swift is an AIRS-owned library-only
manifest retaining Swift 6 and macOS 14. No donor executable, scene, GUI commands,
file-open registration, executable target, tests or resources are included.

CLI checkpoint adds unchanged Sources/EntitlementDiffCLIKit/ComparisonCommand.swift
from the same source snapshot. AIRS owns its separate entry point and executable name;
the runner retains the donor argument, status, schema and exclusive-output policy.

See docs/ENTITLEMENTS_INTEGRATION.md in the AIRS repository for the exact manifest,
capability scope, donor receipts and fresh host evidence.
