# Release acceptance on a hosted runner

`.github/workflows/release-acceptance.yml` tests one published release on a hosted
macOS runner. A hosted runner is a machine that someone else provisioned, that has
never held the application and that has none of the builder's files. The workflow is
the clean-machine check for a release, within the limits listed below.

It is started by hand and never by a push, a pull request or a release event:

```
gh workflow run release-acceptance.yml -f tag=v0.3.4-build32 -f runner=xcode-27
```

`tag` is a published release tag. `runner` is the hosted image: `xcode-27` (macOS 27,
the default), `macos-26` or `macos-15`. The workflow reads the release and changes
nothing: it has read-only repository permission, and it does not sign, publish or
install.

## What it checks

Each check is one step, and a failed step names the check that failed.

1. **Checksums.** Every asset the release publishes is downloaded, and each file
   the release's own SHA-256 list names is compared with it. The application archive
   must be among the files the list names.
2. **Signature, Gatekeeper and notarization.** `scripts/release_preflight.py` runs
   `codesign --verify --deep --strict`, the Gatekeeper assessment and the stapled-ticket
   check. It also requires the build record inside the application to name this
   repository, the bundle identifier, the build number in the tag and the commit the
   tag points at.
3. **Minimum system.** The host's system version is not older than the
   `LSMinimumSystemVersion` the application declares. The record says whether the
   host is at the declared minimum's major version or newer than it.
4. **Engine identity.** The engine inside the application equals the engine in the
   tagged source, file for file.
5. **Bundled interpreter.** The interpreter inside the application runs that engine
   on two owned fixtures, and an independently installed Python runs the tagged
   source on the same fixtures. The exit codes must be equal and the reports must be
   byte-identical. The fixtures are read as data and are never executed.
6. **Start.** The application is opened and must still be running fifteen seconds
   later. It is then ended, and no diagnostic report may have been written for it
   two seconds after that. A report written later is not seen.

The checks come from the revision the workflow is started on. The tagged source is
used only as data: its engine and fixtures are read, and its engine is run by the
independent interpreter.

## What a green run does not show

- **The first-open dialog.** The archive is downloaded by a command-line client and
  carries no quarantine attribute, so the dialog macOS shows when a downloaded
  application is first opened is not exercised, and nobody is present to answer it.
- **Anything a person does.** Nothing is clicked or typed. No window content, file
  picker, export or setting is tested.
- **Other systems.** One runner image is one system version on one kind of hardware.
- **Network isolation.** The runner is online.
- **Who built the archive.** The build record is the builder's statement. The
  signature and the notarization ticket show who signed and that Apple accepted the
  submission. Neither shows that the archive can be rebuilt from the source.

## Record

The run uploads an artifact named for the tag and the runner. It holds the host and
image versions, the two revisions, the asset list, the checksum output, the preflight
receipt, the minimum-system comparison, the engine comparison, the exit codes and
report digests, and the launch line. Artifacts are kept for 90 days, so a release
document that cites a run copies the facts it relies on.

No run had completed when this page was written. The workflow can be started only
from the default branch, so its first run follows its own merge.
