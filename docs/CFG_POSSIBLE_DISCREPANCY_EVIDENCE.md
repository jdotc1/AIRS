# Possible-path discrepancy evidence

CFG analysis already retains bounded recovery-discrepancy details while comparing
all observations. When every concrete discrepancy occurs on a conservative possible
path, the result stays unresolved because reachability is uncertain. Previously,
forming that unresolved summary discarded the retained PC, register and values.

This increment copies the first already-retained discrepancy's preferred VM PC,
expected value and observed value into the existing cfg_path_feasibility_unknown
summary evidence row. Its original message prefix retains uncertain-reachability
meaning; appended detail names the register and conservative possible CFG path.
First means retained traversal order, not earliest PC or highest priority.

No additional evidence rows are created. A one-row budget retains the example;
a zero-row budget stays empty. The example does not prove path feasibility or a
supported inconsistency, and checked_pcs stays empty. Unknown recovery is handled
first and still overrides concrete discrepancies. Known-reachable inconsistencies,
reason codes, scopes, schema and model v47 remain unchanged.

Fresh bounded evidence:

- The initial new regression failed on the missing evidence PC before implementation.
- Four new synthetic methods passed in 0.002 seconds: exact PC/register/value
  serialization with possible-path wording, one/zero-row budgets, preservation of
  a known-reachable inconsistency and unknown precedence over a possible discrepancy.
- Two affected existing recovery methods passed in 0.001 seconds: possible-only
  mismatch refusal and later-unknown precedence. All unrelated checks were reused.

Independent read-only review found no actionable issue in uncertain attribution,
unknown precedence, supported-outcome preservation or evidence budgets.

These tests interpret tiny typed arrays as input data. No complete-image audit,
corpus scan, provenance hashing or GUI/distribution check was repeated. Native
source is unchanged and accepted build results are reused. Installed app, settings
and stores were not accessed; no packaging, installation or release was performed.
