# TBZ/TBNZ v50

Model `arm64-bounded-test-bit-branch-v50` adds exact TBZ/TBNZ using the owned
MacScope decodeTestAndBranch mapping. Donor reads are confined to the supplied
read-only checkout. Bit b5 comes from instruction bit 31 and bits b4:0 from
instruction bits 23:19. Low-bit forms test W bits 0–31; high-bit forms test X
bits 32–63. Rt31 is ZR, never SP. Signed imm14 is scaled by four from the preferred
instruction PC, giving displacement range -32768 through 32764.

Only a concrete source chooses one successor. The selected bit alone determines
the predicate after width masking. Original and unknown sources retain both edges;
no symbolic bit or address alignment is inferred. Derived stack addresses refuse
before projection. The instructions do not write registers, memory, SP, FP or
NZCV. They require CFG dispatch, never direct state application.

The existing shared conditional-edge sets carry this family through successor
validation, natural-loop discovery, shared teardown recognition/pop totals and
refused-target evidence. Bit-tested teardown evidence has its own code rather
than claiming NZCV or whole-register comparison. Existing exact recurrent-state,
path/work/observation limits, uncertain-path handling and unknown-over-discrepancy
precedence remain authoritative. Indirect branches, unsupported loop shapes and
asynchronous/all-PC recovery are not added. Schema remains 1; v48/v49 retain their
historical identities in Python/native admission.
