# AIRS 0.3.3 Preview — build 12

> October 25, 2026 reconciliation: source history and source ZIPs were rewritten
> during cleanup. The app acceptance below retains its original scope; source
> identity and unchanged-source claims describe the original publication. See
> [the reconciliation supplement](RELEASE_HISTORY_RECONCILIATION.md).

Build 12 corrects persistent sidebar sizing and pointer navigation. Page-header
subtitles use the bounded Lumen wrapping helper so minimum-width measurement does
not displace the sidebar. The sidebar uses the complete LumenSourceList component
rather than a custom ScrollView and plain-button wrapper. This keeps visible rows
and their click targets aligned under the toolbar. All nine destinations remain
available and the selected destination remains highlighted after pending work settles.
Existing busy, modal, error and unsaved-checkpoint admission checks remain intact.
See [the diagnosis and acceptance scope](SIDEBAR_NAVIGATION.md).

## Accepted results reused

- Focused page-header sizing regression.
- All 81 ordered destination pairs in isolated navigation-state checks, waiting for
  asynchronous work to settle and queued notifications to run.
- Physical mouse selection of all nine destinations at 1240 by 800 and 1031 by 805,
  including Batch History to Image Batches, with settled selection read-back.
- The accepted optimized native build, new outer Developer ID signature, strict
  bundle validation, Apple notarization and ticket stapling.
- All nine physical pointer checks again in the installed build 12, preserving
  settings and stores. The bounded installed-process query found no AttributeGraph,
  publishing-during-update or fatal-error messages.
- Existing engine, helper, private Python, Settings and comparison results retain
  their own scope. The separate post-publication build 12 download acceptance below
  adds its own received-file and isolated-launch evidence.

The exact accepted signed/stapled app ZIP is reused. No rebuild, re-signing,
re-notarization, unchanged payload hashing or repeated qualification is performed.
A first bounded publication inspection covers the changed native executable and
bundle metadata; unchanged runtime and resource receipts are reused. The public
source migration already inspected its changed payload. This release's changed
source/release metadata receives its own first inspection. No fresh CI pass is claimed.

## Accepted public-download and App Translocation follow-up

A bounded check of the published build 12 completed on October 24, 2026. Chrome
received the ZIP directly from the public GitHub release asset. The first received
transfer digest matched the accepted archive identity, and Chrome quarantine remained
on the ZIP and on the app after Archive Utility extraction. The extracted app was
not moved or altered, and quarantine was not removed.

An exact-path NSWorkspace launch created a separate app instance with a fresh
acceptance profile, activation and recents disabled, and running-app substitution
refused. The launch receipt and the profile's independent receipt agreed on an actual
AppTranslocation executable. Production controllers, restoration, system panels and
external-open routing were disabled by the existing acceptance profile.

The real isolated native report overview displayed the accepted owned-image fixture:
3 functions, 2 agreements, 0 inconsistencies, 1 unresolved function and 5 modeled PC
observations. Closing the sole window terminated the isolated process normally.
The bounded isolated-process diagnostic query found no AttributeGraph,
publishing-during-update or fatal-error messages. Before/after metadata matched for
the installed app, production stores, preferences, saved state and application recents.

This updates the original publication-time download/translocation gap. See the
[sanitized qualification supplement](qualification/BUILD12_DOWNLOAD_ACCEPTANCE.json).
At the October 24 follow-up, the original publication qualification and checksums
were retained alongside a separate download-acceptance supplement and its checksum
file. The later cleanup regenerated source ZIPs and updated their checksum records;
see the reconciliation supplement for that distinct change.
No build, engine analysis, comparison-sheet or sidebar workflow was rerun. Existing
accepted results and the exact-path launch helper were reused.

## Scope and limitations

This is an Apple silicon preview with a macOS 14 deployment target. Clean-machine,
minimum-macOS, Intel-app and offline qualification remain incomplete. This bounded
acceptance ran on the existing development Mac, not a clean environment. No fresh
first-open confirmation dialog was observed on this previously used host. The
isolated profile is app-owned isolation, not an OS sandbox; successful quarantined
launch does not establish clean-host Gatekeeper acceptance. The engine model,
report formats and conservative unresolved/refusal boundaries are
unchanged. Prior receipts do not establish broader engine or platform coverage.

The release tag now identifies rewritten public source. The retained signed app
keeps its original implementation identity. Historical Git-object mapping and the
original test-path substitution describe the publication-time state; cleanup path
changes do not inherit those byte-identity or execution claims. The reconciliation
supplement records the new source identity and outstanding qualification boundary.

Publication does not operate or modify the installed app, settings or stores.
Earlier release assets remain available.
