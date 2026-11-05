# Actual execution index

Reconstructed from the actual local command records and retained runner logs.
This is an execution index, not a claim that every entry had a separate pre-run
manifest. Shell jobs sometimes ended with a display command; a wrapper exit code
therefore cannot stand in for the child test result. Successful runner results
correspond to runner exit 0; RED failures are preserved and corrected by later
receipts. Exact child exit codes were not separately captured for chained jobs.
Elapsed values below are runner-reported test/build seconds, not whole-process
wall time. Corpus wall/RSS receipts are reported separately in RESULTS.

Absolute personal roots are replaced by portable placeholders. No source hashes,
tests or signing checks were repeated to generate this index.

## R001 — inline-2026-11-05T040706.516Z

UTC: 2026-11-05T04:07:06.516Z; runner: **failed (development RED/repair)**; reported seconds: 0.000; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -m unittest discover -s tests -p test_security_delta_corpus_manifest.py -v
```

## R002 — inline-2026-11-05T040817.675Z

UTC: 2026-11-05T04:08:17.675Z; runner: **passed**; reported seconds: 0.006; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -m unittest discover -s tests -p test_security_delta_corpus_manifest.py -v
```

## R003 — inline-2026-11-05T040855.433Z

UTC: 2026-11-05T04:08:55.433Z; runner: **failed (development RED/repair)**; reported seconds: 0.001; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -m unittest discover -s tests -p test_security_delta_corpus_manifest.py -k 'test_invalid_raw_utf8' -v
```

## R004 — inline-2026-11-05T040855.433Z

UTC: 2026-11-05T04:08:55.433Z; runner: **failed (development RED/repair)**; reported seconds: 0.001; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -m unittest discover -s tests -p test_security_delta_corpus_manifest.py -k 'test_manifest_symlink' -v
```

## R005 — A1-schema-green.log

UTC: 2026-11-05T04:09:12.722Z; runner: **passed**; reported seconds: 0.006; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_corpus_manifest.py -v > local-evidence/security-delta-track-a/A1-schema-green.log 2>&1
```

## R006 — A2-acquisition-red.log

UTC: 2026-11-05T04:14:15.754Z; runner: **failed (development RED/repair)**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_corpus_acquisition.py -v > local-evidence/security-delta-track-a/A2-acquisition-red.log 2>&1
```

## R007 — A2-acquisition-green.log

UTC: 2026-11-05T04:15:28.420Z; runner: **passed**; reported seconds: 0.012; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_corpus_acquisition.py -v > local-evidence/security-delta-track-a/A2-acquisition-green.log 2>&1
```

## R008 — A2-unicode-red.log

UTC: 2026-11-05T04:16:29.581Z; runner: **failed (development RED/repair)**; reported seconds: 0.003; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_corpus_acquisition.py -k test_unicode_directory_alias -v > local-evidence/security-delta-track-a/A2-unicode-red.log 2>&1
```

## R009 — A2-acquisition-unicode-green.log

UTC: 2026-11-05T04:16:40.255Z; runner: **passed**; reported seconds: 0.013; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_corpus_acquisition.py -v > local-evidence/security-delta-track-a/A2-acquisition-unicode-green.log 2>&1
```

## R010 — A2-download-red.log

UTC: 2026-11-05T04:17:38.151Z; runner: **failed (development RED/repair)**; reported seconds: 0.000; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_corpus_acquisition.py -k download -v > local-evidence/security-delta-track-a/A2-download-red.log 2>&1
```

## R011 — A2-download-green.log

UTC: 2026-11-05T04:18:00.848Z; runner: **passed**; reported seconds: 0.003; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_corpus_acquisition.py -k download -v > local-evidence/security-delta-track-a/A2-download-green.log 2>&1
```

## R012 — A2-budget-red.log

UTC: 2026-11-05T04:19:58.496Z; runner: **failed (development RED/repair)**; reported seconds: 0.005; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_corpus_acquisition.py -k invalid_download_budget -v > local-evidence/security-delta-track-a/A2-budget-red.log 2>&1
```

## R013 — A2-budget-green.log

UTC: 2026-11-05T04:20:13.788Z; runner: **passed**; reported seconds: 0.001; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_corpus_acquisition.py -k invalid_download_budget -v > local-evidence/security-delta-track-a/A2-budget-green.log 2>&1
```

## R014 — acquisition-batch.log

UTC: 2026-11-05T04:21:19.433Z; runner: **see receipt**; reported seconds: not captured; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -u local-evidence/security-delta-track-a/acquire_official.py > local-evidence/security-delta-track-a/acquisition-batch.log 2>&1
```

## R015 — A3-oracle-red.log

UTC: 2026-11-05T04:25:38.835Z; runner: **failed (development RED/repair)**; reported seconds: 0.000; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_independent_oracle.py -v > local-evidence/security-delta-track-a/A3-oracle-red.log 2>&1
```

## R016 — A3-oracle-green.log

UTC: 2026-11-05T04:27:48.545Z; runner: **passed**; reported seconds: 0.001; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_independent_oracle.py -v > local-evidence/security-delta-track-a/A3-oracle-green.log 2>&1
```

## R017 — A3-bundle-red.log

UTC: 2026-11-05T04:30:33.613Z; runner: **failed (development RED/repair)**; reported seconds: 0.000; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k bundle -v > local-evidence/security-delta-track-a/A3-bundle-red.log 2>&1
```

## R018 — A3-bundle-green.log

UTC: 2026-11-05T04:31:21.515Z; runner: **passed**; reported seconds: 0.005; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k bundle -v > local-evidence/security-delta-track-a/A3-bundle-green.log 2>&1
```

## R019 — A3-utf8-red.log

UTC: 2026-11-05T04:32:35.260Z; runner: **failed (development RED/repair)**; reported seconds: 0.001; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k invalid_utf8_filesystem -v > local-evidence/security-delta-track-a/A3-utf8-red.log 2>&1
```

## R020 — A3-budget-red.log

UTC: 2026-11-05T04:32:35.260Z; runner: **failed (development RED/repair)**; reported seconds: 0.001; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k oracle_output_ceiling -v > local-evidence/security-delta-track-a/A3-budget-red.log 2>&1
```

## R021 — A3-surrogate-red.log

UTC: 2026-11-05T04:32:55.375Z; runner: **failed (development RED/repair)**; reported seconds: 0.002; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k unrepresentable_directory -v > local-evidence/security-delta-track-a/A3-surrogate-red.log 2>&1
```

## R022 — A3-bounded-oracle-green.log

UTC: 2026-11-05T04:33:48.705Z; runner: **passed**; reported seconds: 0.005; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_independent_oracle.py -v > local-evidence/security-delta-track-a/A3-bounded-oracle-green.log 2>&1
```

## R023 — A3-work-red.log

UTC: 2026-11-05T04:34:29.281Z; runner: **failed (development RED/repair)**; reported seconds: 0.002; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k probe_bytes -v > local-evidence/security-delta-track-a/A3-work-red.log 2>&1
```

## R024 — A3-work-green.log

UTC: 2026-11-05T04:34:37.433Z; runner: **passed**; reported seconds: 0.001; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k probe_bytes -v > local-evidence/security-delta-track-a/A3-work-green.log 2>&1
```

## R025 — A3-tools-red.log

UTC: 2026-11-05T04:35:47.402Z; runner: **failed (development RED/repair)**; reported seconds: 0.000; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k apple_tool_agreement -v > local-evidence/security-delta-track-a/A3-tools-red.log 2>&1
```

## R026 — A3-tools-green.log

UTC: 2026-11-05T04:37:26.349Z; runner: **passed**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH storage-guard run -- python3 -B -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k apple_tool_agreement -v > local-evidence/security-delta-track-a/A3-tools-green.log 2>&1
```

## R027 — A3-atomic-red.log

UTC: 2026-11-05T04:40:03.348Z; runner: **failed (development RED/repair)**; reported seconds: 0.000; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k document_publish -v > local-evidence/security-delta-track-a/A3-atomic-red.log 2>&1
```

## R028 — A3-atomic-green.log

UTC: 2026-11-05T04:40:16.084Z; runner: **passed**; reported seconds: 0.002; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k document_publish -v > local-evidence/security-delta-track-a/A3-atomic-green.log 2>&1
```

## R029 — A3-authentic-oracle.log

UTC: 2026-11-05T04:40:30.064Z; runner: **see receipt**; reported seconds: not captured; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH <STORAGE_GUARD> run -- python3 -u local-evidence/security-delta-track-a/run_oracle_once.py > local-evidence/security-delta-track-a/A3-authentic-oracle.log 2>&1
```

## R030 — A4-native-red.log

UTC: 2026-11-05T04:41:16.560Z; runner: **failed (development RED/repair)**; reported seconds: not captured; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH swift test --package-path native --filter SecurityDeltaRealWorkflowTests.testDriverRequiresDistinctSidesAndBoundedCases > local-evidence/security-delta-track-a/A4-native-red.log 2>&1
```

## R031 — A4-native-green.log

UTC: 2026-11-05T04:42:50.843Z; runner: **passed**; reported seconds: 0.001; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH swift test --package-path native --filter SecurityDeltaRealWorkflowTests.testDriverRequiresDistinctSidesAndBoundedCases > local-evidence/security-delta-track-a/A4-native-green.log 2>&1
```

## R032 — A4-authentic-capture.log

UTC: 2026-11-05T04:43:23.576Z; runner: **passed**; reported seconds: 19.966; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH AIRS_REAL_CORPUS_DRIVER=<AIRS_OUTPUT_ROOT>/security-delta-real-corpus/capture-driver-v1.json /usr/bin/time -l swift test --package-path native --skip-build --filter SecurityDeltaRealWorkflowTests.testAuthorizedAuthenticCaptureAndPureReplay > local-evidence/security-delta-track-a/A4-authentic-capture.log 2>&1
```

## R033 — A3-review-signature-red.log

UTC: 2026-11-05T04:43:45.690Z; runner: **failed (development RED/repair)**; reported seconds: 0.001; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k signature_ -v > local-evidence/security-delta-track-a/A3-review-signature-red.log 2>&1
```

## R034 — A5-historical-replay.log

UTC: 2026-11-05T04:44:14.387Z; runner: **passed**; reported seconds: 4.814; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH AIRS_REAL_CORPUS_REPLAY=<AIRS_OUTPUT_ROOT>/security-delta-real-corpus/capture-driver-v1.json /usr/bin/time -l swift test --package-path native --skip-build --filter SecurityDeltaRealWorkflowTests.testFreshInvocationHistoricalReplay > local-evidence/security-delta-track-a/A5-historical-replay.log 2>&1
```

## R035 — A3-review-signature-green.log

UTC: 2026-11-05T04:44:14.387Z; runner: **passed**; reported seconds: 0.000; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k signature_ -v > local-evidence/security-delta-track-a/A3-review-signature-green.log 2>&1
```

## R036 — A4-evaluator-red.log

UTC: 2026-11-05T04:46:02.886Z; runner: **failed (development RED/repair)**; reported seconds: 0.000; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -v > local-evidence/security-delta-track-a/A4-evaluator-red.log 2>&1
```

## R037 — A4-evaluator-green.log

UTC: 2026-11-05T04:47:23.443Z; runner: **passed**; reported seconds: 0.001; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -v > local-evidence/security-delta-track-a/A4-evaluator-green.log 2>&1
```

## R038 — A4-adjudication-v1.log

UTC: 2026-11-05T04:47:32.704Z; runner: **see receipt**; reported seconds: not captured; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH <STORAGE_GUARD> run -- python3 -B scripts/security_delta_case_evaluator.py --manifests docs/security-delta-real-corpus/cases --cache <AIRS_OUTPUT_ROOT>/security-delta-real-corpus --sources local-evidence/security-delta-track-a/private-acquisitions.json --output <AIRS_OUTPUT_ROOT>/security-delta-real-corpus/adjudication-v1.json > local-evidence/security-delta-track-a/A4-adjudication-v1.log 2>&1
```

## R039 — A4-adjudication-v1.log

UTC: 2026-11-05T04:47:59.488Z; runner: **see receipt**; reported seconds: not captured; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH <STORAGE_GUARD> run --entry scripts/security_delta_case_evaluator.py -- --manifests docs/security-delta-real-corpus/cases --cache <AIRS_OUTPUT_ROOT>/security-delta-real-corpus --sources local-evidence/security-delta-track-a/private-acquisitions.json --output <AIRS_OUTPUT_ROOT>/security-delta-real-corpus > local-evidence/security-delta-track-a/A4-adjudication-v1.log 2>&1
```

## R040 — A4-adjudication-v1.log

UTC: 2026-11-05T04:48:20.266Z; runner: **see receipt**; reported seconds: not captured; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH <STORAGE_GUARD> run --entry scripts/security_delta_case_evaluator.py -- --manifests docs/security-delta-real-corpus/cases --cache <AIRS_OUTPUT_ROOT>/security-delta-real-corpus --sources local-evidence/security-delta-track-a/private-acquisitions.json --output <AIRS_OUTPUT_ROOT> --result-relative security-delta-real-corpus/adjudication-v1.json > local-evidence/security-delta-track-a/A4-adjudication-v1.log 2>&1
```

## R041 — A4-dependency-evaluator-red.log

UTC: 2026-11-05T04:48:49.937Z; runner: **failed (development RED/repair)**; reported seconds: 0.001; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k dependency_count -v > local-evidence/security-delta-track-a/A4-dependency-evaluator-red.log 2>&1
```

## R042 — A4-dependency-evaluator-green.log

UTC: 2026-11-05T04:49:09.625Z; runner: **passed**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k dependency_count -v > local-evidence/security-delta-track-a/A4-dependency-evaluator-green.log 2>&1
```

## R043 — A4-adjudication-v2.log

UTC: 2026-11-05T04:49:09.625Z; runner: **see receipt**; reported seconds: not captured; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH <STORAGE_GUARD> run --entry scripts/security_delta_case_evaluator.py -- --manifests docs/security-delta-real-corpus/cases --cache <AIRS_OUTPUT_ROOT>/security-delta-real-corpus --sources local-evidence/security-delta-track-a/private-acquisitions.json --output <AIRS_OUTPUT_ROOT> --result-relative security-delta-real-corpus/adjudication-v2.json > local-evidence/security-delta-track-a/A4-adjudication-v2.log 2>&1
```

## R044 — A7-owned-mutations-red.log

UTC: 2026-11-05T04:49:56.220Z; runner: **failed (development RED/repair)**; reported seconds: 0.006; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_owned_mutations.py -v > local-evidence/security-delta-track-a/A7-owned-mutations-red.log 2>&1
```

## R045 — A7-owned-mutations-green.log

UTC: 2026-11-05T04:50:32.329Z; runner: **passed**; reported seconds: 0.007; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_owned_mutations.py -v > local-evidence/security-delta-track-a/A7-owned-mutations-green.log 2>&1
```

## R046 — A1-fact-positive-red.log

UTC: 2026-11-05T04:51:02.939Z; runner: **failed (development RED/repair)**; reported seconds: 0.003; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_corpus_manifest.py -k structured -v > local-evidence/security-delta-track-a/A1-fact-positive-red.log 2>&1
```

## R047 — A1-fact-positive-green.log

UTC: 2026-11-05T04:51:21.500Z; runner: **passed**; reported seconds: 0.002; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_corpus_manifest.py -k structured -v > local-evidence/security-delta-track-a/A1-fact-positive-green.log 2>&1
```

## R048 — A3-failed-work-green.log

UTC: 2026-11-05T04:51:21.500Z; runner: **passed**; reported seconds: 0.001; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k failed_stale -v > local-evidence/security-delta-track-a/A3-failed-work-green.log 2>&1
```

## R049 — A5-owned-tamper.log

UTC: 2026-11-05T04:52:04.561Z; runner: **failed (development RED/repair)**; reported seconds: 0.000; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH swift test --package-path native --filter SecurityDeltaRealArchiveAcceptanceTests.testSeventeenOwnedArchiveMutationsRefuse > local-evidence/security-delta-track-a/A5-owned-tamper.log 2>&1
```

## R050 — A5-owned-tamper-green.log

UTC: 2026-11-05T04:52:51.099Z; runner: **passed**; reported seconds: 0.000; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH swift test --package-path native --filter SecurityDeltaRealArchiveAcceptanceTests.testSeventeenOwnedArchiveMutationsRefuse > local-evidence/security-delta-track-a/A5-owned-tamper-green.log 2>&1
```

## R051 — A1-fact-types-red.log

UTC: 2026-11-05T04:54:00.878Z; runner: **failed (development RED/repair)**; reported seconds: 0.004; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_corpus_manifest.py -k malformed_fact -v > local-evidence/security-delta-track-a/A1-fact-types-red.log 2>&1
```

## R052 — A1-fact-types-green.log

UTC: 2026-11-05T04:54:00.878Z; runner: **passed**; reported seconds: 0.003; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_corpus_manifest.py -k malformed_fact -v > local-evidence/security-delta-track-a/A1-fact-types-green.log 2>&1
```

## R053 — A5-authentic-tamper.log

UTC: 2026-11-05T04:54:00.878Z; runner: **passed**; reported seconds: 0.000; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH AIRS_REAL_CORPUS_TAMPER=<AIRS_OUTPUT_ROOT>/security-delta-real-corpus/captures-v1/alienator88.pearcleaner.5.4.0-to-5.4.1/historical.json swift test --package-path native --skip-build --filter SecurityDeltaRealArchiveAcceptanceTests.testOptInAuthenticArchiveTamperingRefuses > local-evidence/security-delta-track-a/A5-authentic-tamper.log 2>&1
```

## R054 — A4-expected-red.log

UTC: 2026-11-05T04:54:24.895Z; runner: **failed (development RED/repair)**; reported seconds: 0.000; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k independent_change -v > local-evidence/security-delta-track-a/A4-expected-red.log 2>&1
```

## R055 — A4-expected-green.log

UTC: 2026-11-05T04:55:05.562Z; runner: **passed**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k independent_change -v > local-evidence/security-delta-track-a/A4-expected-green.log 2>&1
```

## R056 — A4-adjudication-v3.log

UTC: 2026-11-05T04:55:05.562Z; runner: **see receipt**; reported seconds: not captured; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH <STORAGE_GUARD> run --entry scripts/security_delta_case_evaluator.py -- --manifests docs/security-delta-real-corpus/cases --cache <AIRS_OUTPUT_ROOT>/security-delta-real-corpus --sources local-evidence/security-delta-track-a/private-acquisitions.json --output <AIRS_OUTPUT_ROOT> --result-relative security-delta-real-corpus/adjudication-v3.json > local-evidence/security-delta-track-a/A4-adjudication-v3.log 2>&1
```

## R057 — A8-privacy-owner-red.log

UTC: 2026-11-05T04:58:39.798Z; runner: **failed (development RED/repair)**; reported seconds: 0.001; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k privacy_owner -v > local-evidence/security-delta-track-a/A8-privacy-owner-red.log 2>&1
```

## R058 — A8-component-binding-red.log

UTC: 2026-11-05T04:58:39.798Z; runner: **failed (development RED/repair)**; reported seconds: 0.001; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k relabelled -v > local-evidence/security-delta-track-a/A8-component-binding-red.log 2>&1
```

## R059 — A8-privacy-owner-green.log

UTC: 2026-11-05T04:59:18.536Z; runner: **passed**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k privacy_owner -v > local-evidence/security-delta-track-a/A8-privacy-owner-green.log 2>&1
```

## R060 — A8-component-binding-green.log

UTC: 2026-11-05T04:59:18.536Z; runner: **passed**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k relabelled -v > local-evidence/security-delta-track-a/A8-component-binding-green.log 2>&1
```

## R061 — A8-harness-io.log

UTC: 2026-11-05T05:01:13.427Z; runner: **passed**; reported seconds: 0.006; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH swift test --package-path native --filter SecurityDeltaRealWorkflowTests.testHarnessNeverReplacesEvidenceAndBoundsReads > local-evidence/security-delta-track-a/A8-harness-io.log 2>&1
```

## R062 — A8-evaluator-inputs.log

UTC: 2026-11-05T05:01:30.015Z; runner: **passed**; reported seconds: 0.003; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k qualification_input -v > local-evidence/security-delta-track-a/A8-evaluator-inputs.log 2>&1
```

## R063 — A4-adjudication-v4.log

UTC: 2026-11-05T05:01:30.015Z; runner: **see receipt**; reported seconds: not captured; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH <STORAGE_GUARD> run --entry scripts/security_delta_case_evaluator.py -- --manifests docs/security-delta-real-corpus/cases --cache <AIRS_OUTPUT_ROOT>/security-delta-real-corpus --sources local-evidence/security-delta-track-a/private-acquisitions.json --output <AIRS_OUTPUT_ROOT> --result-relative security-delta-real-corpus/adjudication-v4.json > local-evidence/security-delta-track-a/A4-adjudication-v4.log 2>&1
```

## R064 — A3-raw-fields-red.log

UTC: 2026-11-05T05:03:12.514Z; runner: **failed (development RED/repair)**; reported seconds: 0.001; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k minimum_os -v > local-evidence/security-delta-track-a/A3-raw-fields-red.log 2>&1
```

## R065 — A3-raw-fields-green.log

UTC: 2026-11-05T05:03:30.967Z; runner: **passed**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k minimum_os -v > local-evidence/security-delta-track-a/A3-raw-fields-green.log 2>&1
```

## R066 — A3-shared-raw-fields-green.log

UTC: 2026-11-05T05:06:50.230Z; runner: **failed (development RED/repair)**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k minimum_os -v > local-evidence/security-delta-track-a/A3-shared-raw-fields-green.log 2>&1
```

## R067 — A3-shared-raw-fields-corrected.log

UTC: 2026-11-05T05:07:06.432Z; runner: **passed**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k minimum_os -v > local-evidence/security-delta-track-a/A3-shared-raw-fields-corrected.log 2>&1
```

## R068 — A3-range-red.log

UTC: 2026-11-05T05:07:24.268Z; runner: **failed (development RED/repair)**; reported seconds: 0.001; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k recorded_range -v > local-evidence/security-delta-track-a/A3-range-red.log 2>&1
```

## R069 — A3-range-green.log

UTC: 2026-11-05T05:07:55.402Z; runner: **passed**; reported seconds: 0.002; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k recorded_range -v > local-evidence/security-delta-track-a/A3-range-green.log 2>&1
```

## R070 — A3-range-identity-green.log

UTC: 2026-11-05T05:08:28.004Z; runner: **passed**; reported seconds: 0.002; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k recorded_range -v > local-evidence/security-delta-track-a/A3-range-identity-green.log 2>&1
```

## R071 — A3-additional-fields.log

UTC: 2026-11-05T05:08:28.004Z; runner: **see receipt**; reported seconds: not captured; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH <STORAGE_GUARD> run --entry local-evidence/security-delta-track-a/capture_additional_fields.py > local-evidence/security-delta-track-a/A3-additional-fields.log 2>&1
```

## R072 — A3-xml-declaration-red.log

UTC: 2026-11-05T05:09:48.547Z; runner: **failed (development RED/repair)**; reported seconds: 0.002; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k without_declaration -v > local-evidence/security-delta-track-a/A3-xml-declaration-red.log 2>&1
```

## R073 — A3-xml-declaration-green.log

UTC: 2026-11-05T05:09:48.547Z; runner: **passed**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k without_declaration -v > local-evidence/security-delta-track-a/A3-xml-declaration-green.log 2>&1
```

## R074 — A4-inventory-facts-red.log

UTC: 2026-11-05T05:10:48.650Z; runner: **failed (development RED/repair)**; reported seconds: 0.001; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k inventory_facts -v > local-evidence/security-delta-track-a/A4-inventory-facts-red.log 2>&1
```

## R075 — A4-inventory-facts-green.log

UTC: 2026-11-05T05:11:17.460Z; runner: **passed**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k inventory_facts -v > local-evidence/security-delta-track-a/A4-inventory-facts-green.log 2>&1
```

## R076 — A3-xbar-plist-repair.log

UTC: 2026-11-05T05:11:49.598Z; runner: **see receipt**; reported seconds: not captured; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH <STORAGE_GUARD> run --entry local-evidence/security-delta-track-a/repair_xbar_plist_observations.py > local-evidence/security-delta-track-a/A3-xbar-plist-repair.log 2>&1
```

## R077 — A4-adjudication-v5.log

UTC: 2026-11-05T05:11:49.598Z; runner: **see receipt**; reported seconds: not captured; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH <STORAGE_GUARD> run --entry scripts/security_delta_case_evaluator.py -- --manifests docs/security-delta-real-corpus/cases --cache <AIRS_OUTPUT_ROOT>/security-delta-real-corpus --sources local-evidence/security-delta-track-a/private-acquisitions.json --output <AIRS_OUTPUT_ROOT> --result-relative security-delta-real-corpus/adjudication-v5.json > local-evidence/security-delta-track-a/A4-adjudication-v5.log 2>&1
```

## R078 — A4-correlation-red.log

UTC: 2026-11-05T05:14:11.084Z; runner: **failed (development RED/repair)**; reported seconds: 0.000; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k multicategory_rule -v > local-evidence/security-delta-track-a/A4-correlation-red.log 2>&1
```

## R079 — A4-correlation-green.log

UTC: 2026-11-05T05:14:43.850Z; runner: **passed**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k multicategory_rule -v > local-evidence/security-delta-track-a/A4-correlation-green.log 2>&1
```

## R080 — A4-adjudication-v6.log

UTC: 2026-11-05T05:14:43.850Z; runner: **see receipt**; reported seconds: not captured; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH <STORAGE_GUARD> run --entry scripts/security_delta_case_evaluator.py -- --manifests docs/security-delta-real-corpus/cases --cache <AIRS_OUTPUT_ROOT>/security-delta-real-corpus --sources local-evidence/security-delta-track-a/private-acquisitions.json --output <AIRS_OUTPUT_ROOT> --result-relative security-delta-real-corpus/adjudication-v6.json > local-evidence/security-delta-track-a/A4-adjudication-v6.log 2>&1
```

## R081 — A6-inspector-width-build.log

UTC: 2026-11-05T05:15:28.656Z; runner: **passed**; reported seconds: 6.32; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH swift build --package-path native --product AIRSApp > local-evidence/security-delta-track-a/A6-inspector-width-build.log 2>&1
```

## R082 — A8-rule-trigger-red.log

UTC: 2026-11-05T05:16:16.814Z; runner: **failed (development RED/repair)**; reported seconds: 0.001; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k finding_kind -v > local-evidence/security-delta-track-a/A8-rule-trigger-red.log 2>&1
```

## R083 — A8-rule-trigger-green.log

UTC: 2026-11-05T05:16:16.814Z; runner: **passed**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k finding_kind -v > local-evidence/security-delta-track-a/A8-rule-trigger-green.log 2>&1
```

## R084 — A8-privacy-correspondence-red.log

UTC: 2026-11-05T05:16:39.569Z; runner: **failed (development RED/repair)**; reported seconds: 0.001; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k changed_executable -v > local-evidence/security-delta-track-a/A8-privacy-correspondence-red.log 2>&1
```

## R085 — A8-privacy-correspondence-green.log

UTC: 2026-11-05T05:16:39.569Z; runner: **passed**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k changed_executable -v > local-evidence/security-delta-track-a/A8-privacy-correspondence-green.log 2>&1
```

## R086 — A8-null-reference-red.log

UTC: 2026-11-05T05:17:30.528Z; runner: **failed (development RED/repair)**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k null_component -v > local-evidence/security-delta-track-a/A8-null-reference-red.log 2>&1
```

## R087 — A8-null-reference-green.log

UTC: 2026-11-05T05:17:30.528Z; runner: **passed**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k null_component -v > local-evidence/security-delta-track-a/A8-null-reference-green.log 2>&1
```

## R088 — A4-adjudication-v7.log

UTC: 2026-11-05T05:23:32.938Z; runner: **see receipt**; reported seconds: not captured; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH <STORAGE_GUARD> run --entry scripts/security_delta_case_evaluator.py -- --manifests docs/security-delta-real-corpus/cases --cache <AIRS_OUTPUT_ROOT>/security-delta-real-corpus --sources local-evidence/security-delta-track-a/private-acquisitions.json --output <AIRS_OUTPUT_ROOT> --result-relative security-delta-real-corpus/adjudication-v7.json > local-evidence/security-delta-track-a/A4-adjudication-v7.log 2>&1
```

## R089 — A9-prepare-red.log

UTC: 2026-11-05T05:25:20.468Z; runner: **failed (development RED/repair)**; reported seconds: 0.000; outer job exit: 1.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_prepare.py -v > local-evidence/security-delta-track-a/A9-prepare-red.log 2>&1
```

## R090 — A9-prepare-green.log

UTC: 2026-11-05T05:25:57.144Z; runner: **passed**; reported seconds: 0.004; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_prepare.py -v > local-evidence/security-delta-track-a/A9-prepare-green.log 2>&1
```

## R091 — A9-prepare-owned-e2e.log

UTC: 2026-11-05T05:26:39.861Z; runner: **passed**; reported seconds: 0.018; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_prepare.py -k end_to_end -v > local-evidence/security-delta-track-a/A9-prepare-owned-e2e.log 2>&1
```

## R092 — A9-fixture-root-red.log

UTC: 2026-11-05T05:28:23.223Z; runner: **failed (development RED/repair)**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_fixture_support.py -v > local-evidence/security-delta-track-a/A9-fixture-root-red.log 2>&1
```

## R093 — A9-fixture-root-green.log

UTC: 2026-11-05T05:28:23.223Z; runner: **passed**; reported seconds: 0.002; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_fixture_support.py -v > local-evidence/security-delta-track-a/A9-fixture-root-green.log 2>&1
```

## R094 — A6-helper-reason-red.log

UTC: 2026-11-05T05:40:58.747Z; runner: **failed (development RED/repair)**; reported seconds: 0.881; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH swift test --package-path native --filter SecurityDeltaRealWorkflowTests.testUnavailableHelperInfoDoesNotInventStaleness > local-evidence/security-delta-track-a/A6-helper-reason-red.log 2>&1
```

## R095 — A6-helper-reason-green.log

UTC: 2026-11-05T05:41:50.037Z; runner: **passed**; reported seconds: 0.392; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH swift test --package-path native --filter 'SecurityDeltaRealWorkflowTests.testUnavailableHelperInfoDoesNotInventStaleness|ComponentReviewWorkspaceTests.testExplicitStrictCaptureRejectsChangedInfo' > local-evidence/security-delta-track-a/A6-helper-reason-green.log 2>&1
```

## R096 — A9-prepare-architecture-red.log

UTC: 2026-11-05T05:43:23.334Z; runner: **failed (development RED/repair)**; reported seconds: 0.005; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_prepare.py -k unsupported_architecture -v > local-evidence/security-delta-track-a/A9-prepare-architecture-red.log 2>&1
```

## R097 — A9-prepare-architecture-green.log

UTC: 2026-11-05T05:43:23.334Z; runner: **passed**; reported seconds: 0.002; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_prepare.py -k unsupported_architecture -v > local-evidence/security-delta-track-a/A9-prepare-architecture-green.log 2>&1
```

## R098 — A6-first-helper-captures.log

UTC: 2026-11-05T05:43:35.928Z; runner: **passed**; reported seconds: 1.445; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH AIRS_REAL_CORPUS_HELPERS=<AIRS_OUTPUT_ROOT>/security-delta-real-corpus/capture-driver-v1.json swift test --package-path native --filter 'SecurityDeltaRealWorkflowTests.testUnavailableHelperInfoDoesNotInventStaleness|SecurityDeltaRealWorkflowTests.testFirstAuthenticHelperEntitlementCaptures' > local-evidence/security-delta-track-a/A6-first-helper-captures.log 2>&1
```

## R099 — A6-final-app-build.log

UTC: 2026-11-05T05:46:20.456Z; runner: **passed**; reported seconds: 0.46; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH swift build --package-path native --product AIRSApp > local-evidence/security-delta-track-a/A6-final-app-build.log 2>&1
```

## R100 — A4-date-fidelity-red.log

UTC: 2026-11-05T05:53:43.041Z; runner: **failed (development RED/repair)**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k datetime_normalization -v > local-evidence/security-delta-track-a/A4-date-fidelity-red.log 2>&1
```

## R101 — A4-date-fidelity-green.log

UTC: 2026-11-05T05:53:43.041Z; runner: **passed**; reported seconds: 0.000; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_case_evaluator.py -k datetime_normalization -v > local-evidence/security-delta-track-a/A4-date-fidelity-green.log 2>&1
```

## R102 — A5-original-disappearance.log

UTC: 2026-11-05T05:58:58.278Z; runner: **passed**; reported seconds: 0.037; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH swift test --package-path native --filter SecurityDeltaRealWorkflowTests.testChangedInfoWithEqualImageDigestSurvivesOriginalBundleDisappearance > local-evidence/security-delta-track-a/A5-original-disappearance.log 2>&1
```

## R103 — A7-transient-permission.log

UTC: 2026-11-05T05:59:57.839Z; runner: **passed**; reported seconds: 0.001; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_independent_oracle.py -k transient_permission -v > local-evidence/security-delta-track-a/A7-transient-permission.log 2>&1
```

## R104 — A7-native-resource.log

UTC: 2026-11-05T06:09:04.091Z; runner: **passed**; reported seconds: 0.000; outer job exit: not captured at initial return.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH swift test --package-path native --filter SecurityDeltaRealResourceTests.testOwnedMaximumInventoryAndLoweredOutputCapsWithProcessMetrics > local-evidence/security-delta-track-a/A7-native-resource.log 2>&1
```

## R105 — A1-integer-canonical-red.log

UTC: 2026-11-05T06:14:29.425Z; runner: **failed (development RED/repair)**; reported seconds: 0.004; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_corpus_manifest.py -k noncanonical_integer -v > local-evidence/security-delta-track-a/A1-integer-canonical-red.log 2>&1
```

## R106 — A1-integer-canonical-green.log

UTC: 2026-11-05T06:14:29.425Z; runner: **passed**; reported seconds: 0.002; outer job exit: 0.

```sh
PATH=<LOCAL_USER_ROOT>/.local/bin:$PATH python3 -m unittest discover -s tests -p test_security_delta_corpus_manifest.py -k noncanonical_integer -v > local-evidence/security-delta-track-a/A1-integer-canonical-green.log 2>&1
```
