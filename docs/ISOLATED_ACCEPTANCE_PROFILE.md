# Isolated downloaded-app acceptance

The signed production bundle supports an explicit, bounded acceptance profile.
Dispatch occurs before the ordinary SwiftUI app, document controllers, entitlement
workspace, project store, recents, and Settings scene initialize. Normal launches
retain the existing app entry path.

Launch a new instance with these arguments, in order:

```
--acceptance-profile /absolute/AIRS-acceptance-<UUID>
--acceptance-report /absolute/<owned-audit.json>
--acceptance-comparison /absolute/<owned-comparison.json>
```

Use the current user's actual home path. The profile directory must already exist,
be empty, be a physical directory immediately inside `Codex`, and have
a UUID suffix. Fixture paths must be physical regular files under that parent.
Partial, duplicated, malformed, conflicting legacy-review, or reused configuration
fails closed with exit 64; it never falls back to the ordinary app. The profile
claims its root exclusively before copying bounded, decoded fixtures into Inputs.

Audit storage uses the profile's data directory and an isolated preferences suite.
Lumen uses the profile's themes directory and a separately preflighted suite.
System recents are replaced by a non-recording implementation. No production
entitlement, inspection, project, or file-routing controller is constructed.
The native window has no frame autosave name and disables state restoration;
the delegate declines secure application-state save and restore and ignores
external file-open events. No native file panel or external export is exposed.
Comparison export is visibly disabled in this profile; ordinary export is unchanged.

The profile displays the real report overview and real comparison sheet. It is an
app-owned isolation boundary, not an OS sandbox or a substitute for clean-machine
qualification. It qualifies downloaded launch, observed executable/translocation
identity, and these displayed UI boundaries. It does not qualify normal-session
file panels, restoration, installation, or minimum-macOS compatibility.

`profile.json` records the launch executable path and profile properties. Runtime
acceptance additionally records the actual PID/path and production-data metadata
before and after this isolated run. Accepted engine/comparison/signing results for
unchanged inputs are reused; only new profile behavior receives fresh checks.
