# Bounded first-unknown CFG recovery evidence

CFG unknown-recovery findings previously retained only the aggregate count. The
analysis already had each observation PC, requested caller register, expected
identity, modeled unknown value and path-certainty flag; those details were lost
when forming the unresolved result. Linear-auditor evidence remains separate.

The existing single CFG summary row now retains the first encountered unknown's
preferred VM PC, expected identity and observed unknown value, and names its
register and known-reachable or conservative-possible path context in the message.
The full unknown count remains the message prefix. It counts unknown required
values across observations/path states, not unique registers or distinct functions.
First means traversal order; no lowest-PC or most-important witness is claimed.

This uses existing evidence fields, adds no rows and changes no schema/model v47.
A one-row budget retains both the complete count and one example. A zero-row
budget retains no evidence. The example is an unresolved observation, not a checked
PC or a demonstrated mismatch. All unknown values are still counted, and any
unknown still overrides concrete mismatches. Possible paths are never labeled
known-reachable. Supported outcomes, scopes and historical auditors are unchanged.

Fresh bounded qualification:

- The new initial regression failed on the missing observation PC before the fix.
- Four new synthetic methods passed in 0.001 seconds: exact register/PC/value
  serialization, full repeated-observation count with budgets one/zero, later
  unknown overriding a concrete mismatch, and conservative-possible path labeling.
- Three affected existing recovery methods passed in 0.001 seconds: unknown refusal,
  later-unknown precedence and saved-pair agreement. Other accepted results reused.

Independent read-only review found no actionable issue in count preservation,
certainty labeling, unknown precedence or evidence-budget handling.

The tests interpret tiny typed instruction arrays as data. No complete-image audit,
corpus scan, provenance hashing or GUI/distribution workflow was repeated. Native
source is unchanged and accepted native-build results are reused. Installed app,
settings and stores were not accessed; no packaging, installation or release.
