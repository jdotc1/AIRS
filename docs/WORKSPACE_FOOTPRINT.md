# Keeping the local workspace small

Use the public repository as the active development checkout. Completed feature
work does not need a permanent worktree or another packaged application copy.
The source tree and its qualification records are small; compiled products,
embedded runtimes and repeated app bundles account for most local storage.

## Retain

- Committed source, explicit unmerged changes and durable refs for detached work.
- Qualification documents, accepted receipts, logs and owned inputs needed for
  later evidence reuse. Keep local-evidence separate from disposable caches.
- One current distribution candidate when needed; public releases remain the
  durable download source for already-published installers.
- User settings, stores and the installed application, outside this cleanup scope.

## Remove after work settles

- native/.build and other known derived build caches when disk space matters.
  The next authorized build will recreate them; cleanup is not a reason to build.
- Obsolete intermediate packaged app copies and redundant runtime downloads,
  after preserving qualification metadata and any required current candidate.
- Completed Git worktrees after checking ownership and uncommitted/ignored data.
  Preserve unmerged commits and unique artifacts before removal, then prune stale
  worktree metadata. Do not remove another active task's checkout or products.
- Local and remote feature branches only after their exact tips are confirmed
  reachable from the default branch. Keep the default branch and unmerged work.

Avoid treating all ignored files as disposable: this repository intentionally
ignores local evidence and credentials as well as caches. Archive unique local
work outside the checkout before pruning. Historical recovery archives stay
local and are not a reason to republish unsanitized development history.

Directory sizes, Git status, default-branch reachability and remote branch/PR
metadata are sufficient cleanup checks. Reuse accepted analysis, signing and
release results; do not replay sealed checks, rehash inputs or rebuild merely to
verify that generated files were deleted.
