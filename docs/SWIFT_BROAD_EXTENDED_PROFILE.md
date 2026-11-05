# Extended Swift scan profile

`broad-extended-v1` is an explicitly selected resource profile for the existing broad structural Swift analysis. Its outer model is `swift-broad-error-flow-extended-v1`; its inner call, witness and validation semantics remain the existing broad-v1 family. Earlier profiles retain their original ceilings and historical interpretation.

| Boundary | Extended profile |
| --- | ---: |
| Image | 8 MiB |
| Recorded functions or executable symbols | 9,216 |
| Words scanned overall | 2,097,152 |
| Words scanned per function | 262,144 |
| Retained call records | 8,192 |
| Public JSON | 16 MiB |
| Charged metadata and per-candidate analysis work | 512 Mi steps |

The total word budget is eight times the previous profile and covers at most every four-byte word in the already permitted image size. The per-function budget is separately bounded. A function exceeding that limit is partially scanned; later functions remain eligible if overall budget remains. These are scan limits, not a claim of an RSS or wall-time ceiling. The charged analysis-work counter covers metadata and per-candidate work; the word scan is accounted separately by `scanned_words`.

A complete word scan does not imply complete candidate details or successful witness checks. Per-function candidate limits, the 8,192-call cap, the 16 MiB encoded-output cap, and separate metadata, ABI and witness budgets can still produce omissions or unresolved results. The report retains the exact omitted candidate count and separate completeness states; the user interface displays them and preserves the raw historical export. The profile does not prove runtime calls, reachability, source semantics or handler behavior.

Owned synthetic tests include a call beyond the old overall scan limit, a per-function boundary-plus-one with a later call, a lowered-budget partial scan, 4,097 and 8,193 selected-call cases, exact native admission of 8,192 retained calls and refusal above that envelope, matching profile/model routing, historical reopen and cancellation. An independent nonimplementing reviewer examined the changed profile and retention boundaries. These fixtures establish bounded implementation behavior, not real-app semantic or runtime acceptance.

## Native real-input check

An installed build 32 run used the previously acquired Maccy 2.8.0 ARM64 slice. Within this profile's recorded scope, the scan completed after 393,880 words, compared with the prior profile's partial scan of 262,144 words. It observed 55,863 call instructions and selected 5,263 candidate records; all 5,263 were retained with zero candidate omissions and all remained unresolved indirect targets. Complete scan/accounting does not prove that indirect targets, execution, or source behavior were established.

The native report exported and reopened with the extended profile and historical-evidence label. This is one real-input workflow check, not a corpus or clean-machine qualification. The known AppKit geometry diagnostics appeared again; the application remained responsive and this check did not requalify that previously documented issue.
