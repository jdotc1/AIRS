# CFG work-budget evidence

A cfg_work_limit finding previously recorded the stop PC and generic exhaustion
message without the configured cap or the work already completed. The existing
row now carries expected `configured CFG state-visit limit N` and observed
`N completed CFG state visits; next visit refused` values. The original reason,
message, address, scope, verdict and cfg_steps remain unchanged.

The gate runs before incrementing steps. Counts describe completed CFG state
visits across paths/loops, not unique instructions, runtime execution, total image
work or elapsed time. The evidence PC names the next refused visit. No extra
exploration or automatic retry occurs. Evidence budgets, including zero, remain
intact. Exact-boundary completion still produces the original supported result;
other resource refusals do not acquire these diagnostics. Schema/model v47 and
all semantic support remain unchanged.

Fresh bounded qualification:

- The initial new regression failed on absent budget evidence for limits 0/1/2.
- Four new synthetic methods passed in 0.001 seconds: exact limits/visit counts/PC
  serialization, one/zero-row evidence handling, supported completion at three
  visits, and preservation of an unrelated observation-limit refusal.
- One affected existing CFG-limit method passed in 0.001 seconds.
- Independent read-only review found no actionable counter-semantics issue.

Accepted unrelated model, native-build, GUI and distribution results are reused.
No complete-image audit, corpus, hashing, native launch, packaging, installation,
release, settings or store operations were performed.

The public repository was renamed to jdotc1/AIRS at the user's request. GitHub
metadata confirms PUBLIC visibility and main as default; this checkout's origin
uses the new URL. The README preview link uses the renamed repository.
