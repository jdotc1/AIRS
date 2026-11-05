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
