# Track A execution ledger

Baseline: `0b192429cbfb5583557c4c5f04017b1946141e4a`; macOS 27.3 build
26C5035r; Apple Swift 6.4.2 (swiftlang-6.4.2.1.9, clang-2100.4.1.1);
ARM64 host, package deployment macOS 14. Historical START_HERE.md and
VERIFICATION.md are absent from the active checkout; current delta contracts
were read instead. Existing component-delta tests and build 26 qualification
remain accepted within their original scope, without blanket reruns.

## A1 protocol progress

- RED: new manifest test module failed import because the harness did not exist.
- GREEN: initial nine schema/semantic cases passed (0.006 seconds).
- RED: precise invalid raw UTF-8 code and ancestor-symlink escape tests failed.
- GREEN: all 11 manifest methods passed (0.006 seconds; exit 0), after separating
  UTF-8/depth refusal codes and adding descriptor-relative directory traversal.
- Command: `python3 -B -m unittest discover -s tests -p test_security_delta_corpus_manifest.py -v`.
  Runs were supervised by the shared storage guard. Changed inputs were only the
  new corpus protocol/tests. The final full run covered both changed shared
  admission functions; accepted unchanged AIRS tests were not repeated.
- Native baseline checks: pending shared build-root availability; the native Swift
  UI owner currently reserves it. No native test is claimed by these Python runs.

## Current denominators

Authentic pairs acquired/adjudicated: 0/24 requested; applications: 0/12;
publishers: 0/3. These are pending work, not acceptance or source blockers.
No real bundle analysis, oracle, archive replay, native corpus workflow, stress
qualification, or independent Track A adversarial round has run yet.

## A2 acquisition and owned guards

Acquired and admitted 47/47 original official release ZIPs, yielding 35 distinct
chronological pairs from 12 applications and 10 publisher accounts. Downloaded
290,903,043 bytes; extracted 684,656,550 bytes. No source digest was duplicated
within a pair. Payloads are local-only; 35 manifests contain actual URLs, hashes,
license provenance and exact app paths. Oracle expectations remain pending.
Applications: Maccy, Ice, SwiftBar, KeyCastr, xbar, KeepingYouAwake, KnockKnock,
QLMarkdown, AltTab, Pearcleaner, OverSight and TaskExplorer. OverSight's selected
bundle is the publisher's installer app; it is inspected as data and never run.
Pearcleaner records Apache-2.0 with Commons Clause; its payload is not redistributed.

Owned archive tests: initial nine methods passed, then a Unicode-directory
collision test failed on APFS (two exact names silently merged). Inode-to-exact-
path tracking corrected the extraction layer; all ten affected methods passed
(0.013 s, exit 0). Two new transfer methods passed (0.003 s), proving one streamed
hash, no destination replacement, size/digest refusal and pre-transfer cancellation.
A new pre-network budget test failed and passed after moving size validation before
process creation (0.001 s). Only relevant changed/new checks ran.
Commands use `python3 -B -m unittest discover -s tests -p test_security_delta_corpus_acquisition.py`
with focused `-k` selectors for later independent helper changes. All are owned
fixtures; none counts as authentic-pair analysis acceptance.

## A3 oracle progress

Eight owned raw-byte methods passed after a missing-module RED run (0.001 s,
exit 0): typed Boolean/integer/order, raw integer representation uncertainty,
empty/malformed privacy data, duplicate loader sequence, raw subtype bits, fat
slice/UUID provenance, malformed signature versus absence, and truncated input.
Command: `python3 -B -m unittest discover -s tests -p test_security_delta_independent_oracle.py -v`.
No real application binary has been decoded by this oracle yet.
