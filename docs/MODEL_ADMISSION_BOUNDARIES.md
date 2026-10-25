# Historical and unknown-model decoder boundary qualification

The registry hardening's accepted tests cover every exact CFG label and registry
relationships. This increment adds decoder-level controls for the policies outside
the CFG set, rather than inferring those behaviors from set membership.

New Python and native tests demonstrate:

- Linear v1 and linear-DWARF v2 retain masked ordinary subtype admission for compact
  findings, while refusing a masked nonordinary subtype.
- Historical v1 refuses evaluated CFI. Linear-DWARF v2 accepts an otherwise valid
  evaluated-CFI finding only with an exact ordinary subtype, refusing capability bits.
- Future, suffixed and differently cased labels retain generic import admission;
  an out-of-function checked PC is still rejected for each label.

Unknown-label import is structural navigation compatibility, not engine support or
independent verification of a saved finding's truth. These tests add no labels,
instruction semantics, schema changes or production-code changes.

Fresh results: three new Python methods passed in 0.001 seconds; three new native
methods passed with zero failures in 0.008 seconds. Python uses synthetic in-memory
reports. Native cases mutate decoded fixture objects to create new policy inputs;
they do not re-audit the image or re-qualify the original fixture. Only the new test
classes ran. Independent read-only review found no actionable issue or coverage
overclaim. No corpus scan, hashing, full suite or GUI check was performed.

The accepted registry build, review and tests, CLS v47 semantics, earlier owned-image
results and build 12 GUI/distribution acceptance are reused. No app packaging,
installation or release was performed; installed app, settings and stores remain
unchanged.
