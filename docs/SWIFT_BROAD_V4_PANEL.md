# Panel measurement with `broad-extended-v4`

Roadmap section 4.3, item 1, and the stop rule of the v4 design. This page is a measurement of what the profile reports
on real applications. It is not a correctness claim about those applications, and the counts are not prevalence.

## Method

- Panel: the 12 applications of the real-application corpus
  ([security-delta-real-corpus/cases](security-delta-real-corpus/cases)). For each application, the newest release
  recorded there.
- Each archive was fetched once from its publisher's release URL and admitted only if its SHA-256 equalled the recorded
  digest. All 12 did. It was then extracted without following links.
- Nothing from an archive was executed, opened, signed or installed. Only the engine read the files, as data.
- Input: the main executable of the application bundle, with the `arm64` slice selected. For OverSight, whose release
  archive holds an installer, the input is the `OverSight.app` embedded in the installer.
- Profiles: `broad-extended-v3` as the "before" column, then `broad-extended-v4`, once each, with
  `--include-error-regions --validate-region-entries --include-structured-presentation --include-outcome-witnesses`.
- The first v4 run on Maccy was refused by the profile's own report check (rule C7). Runtime metadata calls are now
  accepted when the import table lists them as `not_swift`. The Maccy row below is from one run after that fix. The
  other v4 reports contain no runtime metadata call, and the fixed check accepts them unchanged.

## Applications the profiles could not read

Five of the 12 exceed an input bound that both profiles share, and neither profile produces a report for them:

| Application | Version | Executable bytes | Refusal |
| --- | --- | ---: | --- |
| Pearcleaner | 5.4.3 | 14,462,048 | `file_size_limit` (8 MiB) |
| QLMarkdown | 1.5.7 | 11,882,608 | `file_size_limit` (8 MiB) |
| xbar | v2.1.7-beta | 24,909,488 | `file_size_limit` (8 MiB; the message was not kept, and the code follows from the size) |
| AltTab | v11.10.1 | 7,113,232 | `function_limit` (8,192 functions) |
| SwiftBar | v2.1.2-beta-5 | 6,689,312 | `swift_broad_metadata_admission`: `symbol_record_limit` |

The file-size bound applies to the whole file, both slices included.

## Applications measured

"Unresolved share" is the v4 stop-rule measure: retained unresolved rows plus omitted calls, divided by selected
candidates. The v3 column uses the same arithmetic. "Attributed Swift calls" is the total of `decision_by_shape`, and
"decided" is the share of those calls whose declaration the grammar decides.

| Application | Version | v3 selected | v3 unresolved share | v4 selected | v4 retained (unresolved / declined) | v4 omitted | v4 unresolved share | Attributed Swift calls | Decided |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Maccy | 2.8.0 | 11,241 | 0.965 | 8,239 | 4,946 (4,498 / 448) | 3,293 | 0.946 | 10,572 | 0.606 |
| Ice | 0.11.13-dev.2 | 8,624 | 0.950 | 7,246 | 4,954 (4,527 / 427) | 2,292 | 0.941 | 8,271 | 0.562 |
| TaskExplorer | v3.1.0 | 5,410 | 0.934 | 4,569 | 4,569 (4,212 / 357) | 0 | 0.922 | 5,268 | 0.594 |
| KnockKnock | v4.1.0 | 28 | 1.000 | 28 | 28 (28 / 0) | 0 | 1.000 | 0 | n/a |
| OverSight | v2.4.0 | 19 | 1.000 | 19 | 19 (19 / 0) | 0 | 1.000 | 0 | n/a |
| KeepingYouAwake | 1.6.8 | 18 | 1.000 | 18 | 18 (18 / 0) | 0 | 1.000 | 0 | n/a |
| KeyCastr | v0.11.1 | 0 | n/a | 0 | 0 | 0 | n/a | 0 | n/a |

- Every v4 omission on the panel has the cause `output_budget`: 3,293 on Maccy and 2,292 on Ice. Each import call
  table is complete, with no residual.
- Every `declined` row has the reason `value_witness_abi_nonthrowing`.
- Calls skipped because the callee is declared non-throwing: Maccy 6,147, Ice 4,483 and TaskExplorer 3,112.
- Distinct imported Swift names decided:
  - Maccy: 546 of 989 (528 non-throwing, 17 throwing, 1 async);
  - Ice: 530 of 944;
  - TaskExplorer: 357 of 610.
- On all three, the largest undecided class is accessors.
- KnockKnock, OverSight and KeepingYouAwake make no attributed call to an imported Swift function. Their few candidates
  are indirect calls. KeyCastr has none.

## What the result means

- The licence decides 56% to 61% of the attributed Swift calls on the three applications that have them. It does not
  move the stop-rule measure much, by design. An imported call leaves the unresolved set only by being skipped as
  non-throwing. A call to a callee declared `throwing` stays `unresolved`, and so does every undecided call.
- On each of the six applications with candidates, the unresolved share is at least 0.92. Three of those six have
  only 18 to 28 candidates each.
- The stop rule of the v4 design asks for an unresolved share of at least 0.90 on every panel application. It can be
  evaluated on only those six. Five applications are outside the input bounds and KeyCastr has no candidates, so the
  condition as written is not shown for the whole panel.
- On the six, the condition holds. The maintainer's decision, taken on that subset, is that no further broad admission
  profile is scheduled from v4.
- Turning a row into a result would take evidence about what a callee does at run time, which no admission profile
  provides.
- Five panel applications are outside the shared input bounds. A larger bound would be its own change and is not
  scheduled.
