# AIRS 0.3.3 Preview — build 10

> October 25, 2026 reconciliation: source history and source ZIPs were rewritten
> during cleanup. The app acceptance below retains its original scope; source
> identity and unchanged-source claims describe the original publication. See
> [the reconciliation supplement](RELEASE_HISTORY_RECONCILIATION.md).

Build 10 adds an explicitly opted-in acceptance profile before the ordinary app
initializes. It uses fresh profile storage and separate preferences for AIRS and
Lumen, non-recording document recents, and a native window without restoration or
frame autosave. Production document, entitlement and project controllers are not
constructed in this profile. File pickers and external exports are unavailable.
Invalid, conflicting, symlinked or reused profile configuration fails closed.
See the [profile contract](ISOLATED_ACCEPTANCE_PROFILE.md) for invocation and scope.

## Accepted results reused

- Two profile parser tests passed, covering explicit fresh roots, owned regular
  fixtures, partial/duplicate/conflicting configuration and symlink refusal.
- The optimized native app built. The candidate passed outer signing validation,
  Apple notarization and ticket stapling. Publication reuses that exact signed ZIP
  without rebuilding, re-signing, re-notarizing or reassessing unchanged bytes.
- A Chrome loopback HTTP download matched the candidate archive's retained identity.
  Chrome quarantine survived Archive Utility extraction. Gatekeeper accepted the
  received bundle as Notarized Developer ID. This is local browser-transfer
  evidence; it is not a public-host download of build 10.
- An exact-path NSWorkspace launch with a new instance and explicit profile
  arguments returned actual App Translocation bundle and executable URLs. The
  profile's own receipt independently recorded the translocated executable path.
  The standard macOS first-open confirmation reported no malicious software.
- The real report overview displayed the accepted owned v41 report: 3 functions,
  2 agreements, 0 inconsistencies, 1 unresolved function and 5 modeled observations.
  The real comparison sheet displayed an accepted synthetic 51-row fixture with
  external export disabled; Done dismissed it. Closing the sole window terminated
  the isolated process normally.
- Before/after metadata for the installed app, production stores, preferences,
  saved state and application recents matched. Publication does not operate or
  modify the installed app or production data.
- Prior owned-image v41 qualification, Settings acceptance and the comparison
  warning/filter/pagination qualification remain reused results. The unchanged
  engine and those workflows were not rerun for this release.

## Public distribution

New or changed public source and release metadata receive a first bounded
maintainer-path/credential-marker inspection. The changed native executable gets
its first public-distribution inspection. Unchanged public payload, runtime,
helper and vendor evidence is reused. Pattern inspection cannot establish the
absence of arbitrary confidential text. No fresh CI pass is claimed.

## Limits

This remains an Apple silicon preview with a macOS 14 deployment target. No clean
machine was available. Clean-machine installation, minimum-macOS, Intel-app and
offline qualification remain incomplete. The profile is app-owned isolation, not
an OS sandbox. It qualifies the displayed bounded profile, not ordinary-session
file panels, window restoration, every report or every macOS version. The v41
engine, report formats and conservative unsupported/refusal boundaries are unchanged.
