# AIRS 0.3.3 Preview — build 12

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
- Existing engine, helper, private Python, Settings, comparison and build 10 isolated
  download/translocation results retain their own scope. They are not repeated
  build 12 browser-download or App Translocation qualification.

The exact accepted signed/stapled app ZIP is reused. No rebuild, re-signing,
re-notarization, unchanged payload hashing or repeated qualification is performed.
A first bounded publication inspection covers the changed native executable and
bundle metadata; unchanged runtime and resource receipts are reused. The public
source migration already inspected its changed payload. This release's changed
source/release metadata receives its own first inspection. No fresh CI pass is claimed.

## Scope and limitations

This is an Apple silicon preview with a macOS 14 deployment target. Clean-machine,
minimum-macOS, Intel-app and offline qualification remain incomplete. Build 12 has
not received a new public-host browser download or App Translocation check. The
engine model, report formats and conservative unresolved/refusal boundaries are
unchanged. Prior receipts do not establish broader engine or platform coverage.

The public repository is the single source of truth. The release tag and source ZIP
identify the public source; the signed candidate retains its original implementation
revision, mapped to the public tree by retained Git object identities. The only
migration test-source substitution makes a test workspace relative to the current
user's home. No new execution is claimed for that path substitution.

Publication does not operate or modify the installed app, settings or stores.
Earlier release assets remain available.
