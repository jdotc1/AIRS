# Path aliases in destination and location checks

macOS reaches some folders through more than one spelling: `/tmp`, `/var` and
`/etc` are links into `/private`. Foundation's file-system standardizing calls
remove a leading `/private` only when the resulting path exists. An existing
folder and a destination that does not exist yet could therefore be compared
under different spellings.

## What was wrong

Three kinds of check compared path strings after such a call:

- Export and reconstruction guards compared a new destination with an existing
  protected folder by string prefix. When the protected folder lay below an
  aliased folder, a destination nested inside it was not refused. This affected
  portable project export, settled-batch companion export, re-export and
  reconstruction, and the application's rule that a JSON export may not be
  written inside an inspected application or debug-symbol bundle.
- A relative entitlement manifest saved beside its applications below an
  aliased folder was refused, because the manifest folder was standardized and
  the application paths were not.
- Validation of a discovered bundle image refused an unchanged image when the
  caller's path and the recorded path used different spellings.

No analysis result, report or stored evidence was affected. The first kind
could let an export be created inside a folder the check was meant to protect;
an existing file could not be replaced this way, because an existing
destination is spelled the same way as the folder that contains it and the
earlier test already refused it.

## The rule now

`PathContainment` in the native core resolves the deepest existing ancestor of
a path through the file system, appends the remaining components as written,
and compares the results. Where both entries exist it also compares device and
inode, so spellings that differ only by case or Unicode form are treated as one
location. It opens, reads and creates nothing.

- Every guard listed above keeps its earlier string test and adds the new
  test. A guard can refuse more than before and never less. Errors and messages
  are unchanged.
- A relative manifest keeps the manifest folder as the caller spelled it. An
  application path is relative to that folder when it begins with one of three
  spellings of the folder: as given, Foundation's standardized form, or the
  resolved form. Application paths are still compared as exact bytes and are
  never opened, tested for existence or resolved.
- Bundle image validation accepts the recorded path or another spelling of the
  same location. The no-follow descriptor walk below the recorded bundle root
  and the device, inode, size and time checks are unchanged.

## Limits

These are preflight checks on names. They do not protect against a process
that changes the file system between the check and the write; the writers'
own refusal of existing destinations and their staging folders remain the
protection there. The vendored entitlement comparison package already resolved
its destination's parent folder and compared file identity; it is unchanged.
A symbolic link whose target does not exist is compared by its own name and
is not followed, as before. Mounted volumes, firmlinks and network locations
were not examined. No analysis model, report schema or engine behavior
changed, and no release qualification is claimed.

## Evidence

Tests build one temporary folder and address it through both spellings. They
cover the comparison rule itself, the store, companion, re-export,
reconstruction and bundle-export guards in both directions with a destination
outside still accepted, the four spelling combinations of a relative manifest
and its round trip, and bundle image validation for an unchanged and a changed
image. In each guard test the direction that names the protected folder by its
longer spelling was already refused before this change; the other direction is
the one that fails without it. The Swift error-flow export guard uses the same
rule and has no test of its own.

The local native run for this change executed 1,193 tests with 6 skipped and
no failure, from a checkout below a symbolically linked folder, where six
path-comparison cases failed before.
