# Required adversarial matrix and evidence classes

Fresh means a new Track A check/observation. Reused means accepted original AIRS
qualification at the baseline, with unchanged relevant production behavior; it
was not rerun merely for handoff. The execution index supplies actual invocations.
Blocked/not-run conditions are not passes. The 40 newly generated mutations are
numbered 001–040 in `test_security_delta_owned_mutations.py`; native archive tests
add 17 mutation families on both owned and authentic retained evidence.

| # | Required boundary | Evidence / disposition |
| ---: | --- | --- |
| 1 | Missing app | Fresh oracle missing/cancelled/truncated fixture |
| 2 | Moved/same-name component | Fresh modified same-name archive digest refusal; reused candidate matching tests |
| 3 | Shared identifier | Reused `SecurityDeltaDeclarationTests.testCandidateAndAmbiguousMatchesNeverCompareDeclarations` |
| 4 | Unicode normalization collision | Fresh APFS directory-alias refusal; reused exact inventory paths; invalid physical UTF-8 construction skipped on APFS, injected invalid name passes |
| 5 | Symlink escape | Fresh archive external-link/link-ancestor/source-link refusals and no-follow oracle exclusions |
| 6 | Transient read failure | Fresh unavailable source acquisition/IO boundaries; actual OS permission-revocation race not induced; existing reader-failure guards reused |
| 7 | Stale stat/read | Fresh stale archive admission and injected stale oracle read; fresh affected changed-Info native regression |
| 8 | Shallow/deep exclusions | Fresh oracle/extraction traversal limits and real Sparkle exclusions; reused any-exclusion inventory absence refusal |
| 9 | Fat slice changed at same path | Fresh 35 authentic changed primary containers and per-slice raw identity/ranges |
| 10 | Subtype/capability mismatch | Fresh raw subtype fixture; reused `SecurityDeltaSignatureTests.testCapabilityBitsCannotBeMatchedByArchitectureLabel` |
| 11 | Missing Info | Fresh owned helper unavailable outcome and four first authentic helper eligibility refusals; reused declaration-only root record gate |
| 12 | Malformed plist | Fresh malformed XML/binary, duplicate keys, invalid offsets and depth mutations |
| 13 | Absent/empty dictionary | Fresh raw present-empty privacy fixture; reused strict entitlement presence models |
| 14 | Missing/unreadable privacy | Fresh bounded oracle presence/exclusion fixture; reused `testMissingPrivacyManifestDiffersFromEmptyAndUnreadable` |
| 15 | Boolean/numeric entitlement | Fresh independent typed comparison/raw plist fixture; reused strict exposed numeric decoder tests |
| 16 | Historical normalized integer | Fresh unspecified raw numeric fidelity fixture; reused `SecurityDeltaValueTests.testStrictTagsAndLegacyNormalization` |
| 17 | Duplicate loader command | Fresh raw command sequence and metadata-group checker regressions; reused loader multiset tests |
| 18 | LC_RPATH change | Reused static loader declaration tests; fresh raw ordered loader parser and authentic loader changes |
| 19 | Unsigned helper | Fresh owned no-signature Mach-O fixtures and unavailable helper preflight; no third-party bundle was stripped or re-signed |
| 20 | Malformed signature slot | Fresh duplicate command, wrong magic, duplicate/overlap slot and truncated-region RED/GREEN fixtures |
| 21 | Signature digest scope mismatch | Fresh raw slice/ref binding; reused `testContradictoryWholeSliceDigestRemainsUnresolved` |
| 22 | Equal signature/image evidence with changed metadata | Fresh owned unchanged-image/changed-Info historical-disappearance fixture |
| 23 | Apparent deletion under incomplete inventory | Real partial scopes preserved; reused `testPartialAndExcludedInventoriesDoNotProveRemoval` |
| 24 | Ambiguous relocation candidate | Reused exact/candidate/ambiguous matching tests; fresh no guessed source-owner correspondence checker |
| 25 | Mixed one-sided parent chain | Reused related-component chain tests; fresh independent recorded-parent/ancestor qualification |
| 26 | Truncated references | Reused deep hierarchy/reference-limit omission tests; fresh checker refuses missing constituent references |
| 27 | Output cap | Fresh oracle output and bounded directory fixtures; reused reduced observation/finding limit disclosure |
| 28 | Export cap | Reused exact base64/preflight boundaries and native export-failure preservation; real >limit application export not run |
| 29 | Swapped archive side | Fresh 17-family native mutation sets and side/inventory/reference checker |
| 30 | Changed model version | Fresh native schema/model/rules mutations, no future-version interpretation |
| 31 | Stale UI task | Reused `ComponentReviewWorkspaceTests.testSecurityCaptureCancellationRevisionAndQuitRetainPriorSession` and pair-job stale publication gates |
| 32 | Cancellation | Fresh acquisition/oracle pre-open cancellation; reused analyzer/archive/native cancellation/settlement guards |
| 33 | Reopen after original disappears | Fresh owned original-bundle removal, historical replay, evidence resolution and live capture refusal; authentic originals preserved |
| 34 | Independent recapture/new UUID | Four first helper captures and one authorized live UI recapture retain new identities separately; no cross-recapture ID equality claim |
| 35 | Incorrect source offset | Fresh archive reference mutation, raw command bounds and exact slice/range checker |
| 36 | Rapid navigation/filter switching | Fresh native category/component/observation/Components/Security mode transitions; late-worker model guards reused |
| 37 | Tiny/malformed executable | Fresh owned header/command/fat bounds mutations; raw unavailable candidates remain counted |
| 38 | Very large nested bundle | Fresh archive expansion/entry/nesting caps and bounded enumeration sentinel; no large destructive/corpus sweep |
| 39 | Read-only app on external volume | BLOCKED: no approved external application volume available on this host. Do not create/mount a volume or change permissions to fabricate acceptance |
| 40 | Nonredistributable public artifact | Real Pearcleaner Commons Clause provenance retained; no payload redistributed. Public cases contain hashes/locators/metadata only |

The portable matrix contains 40 scenarios, not 40 claims of full real-input runtime
coverage. Existing unchanged checks are deliberately reused. Actual blocking inside
Security.framework, a clean machine, macOS 14 runtime, and an external read-only app
volume remain unqualified environmental gates. Those conditions require separate
explicitly authorized environments/runs. No OS/app permissions were changed.
