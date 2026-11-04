# Exact instruction words in current refusal evidence

The saved mixed sample's historical v1 conditional-flow and pointer-authentication
findings retain a reason and preferred VM PC, but not the exact word at that PC.
Those historical refusals do not prove that today's model lacks the same support;
the report contains neither the necessary bytes nor a current audit. Rather than
infer a semantic extension, this increment improves future diagnostic evidence.

Current-model dispatch annotates retained unresolved evidence for exactly
unsupported_instruction, unsupported_control_flow and unsupported_pauth with an
observed string such as `ARM64 instruction word 0xd503233f`. It reads four bytes
from the already selected image at the existing evidence address, interprets the
word little-endian and retains that preferred VM address. It does not read an
external path, execute an image, compute a hash, or infer instruction effects.

Annotation requires ordinary ARM64 subtype 0/1, aligned in-function bounds,
matching refusal reason, retained evidence and no existing observed value. Unmapped
bytes leave the original refusal unchanged. No evidence rows are added, so zero
and other evidence budgets remain intact. Supported results, historical auditors,
refusal codes/messages, scope, checked PCs, schema and model v47 are unchanged.
The existing evidence.observed field carries this diagnostic; it is not a checked
state or a recovery claim. Old reports are not rewritten.

Fresh bounded qualification:

- Three new synthetic test methods passed in 0.024 seconds: all three exact-word
  refusals and preferred-PC serialization; invalid/missing/unmapped addresses,
  nonordinary identity, supported-result and existing-evidence preservation;
  zero evidence budget and historical-auditor equivalence.
- The first test initially constructed nested prologue/epilogue tuples incorrectly.
  After correcting the fixture, all three word cases failed at the missing observed
  value before implementation and passed after it.
- Three affected existing dispatch methods passed in 0.001 seconds, covering
  compact leaf, compact saved-pair call and evaluated-CFI call recovery. Their inputs
  were checked because current dispatch changed; unrelated accepted checks were reused.

Independent read-only review found no actionable issue: dispatch and supported
outcomes remain unchanged, with bounded attribution and evidence preservation.

No complete image, corpus, native GUI or distribution acceptance was repeated.
Native source is unchanged and accepted native build/results are reused. No app
packaging, installation, release, settings or store operations were performed.
