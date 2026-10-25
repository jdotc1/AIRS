# CBZ/CBNZ W/X v49

Model `arm64-bounded-compare-branch-v49` adds exact CBZ/CBNZ W/X using the owned
MacScope decodeCompareAndBranch field mapping from donor checkout 18831a68e.
Rt31 means ZR. Signed imm19 is scaled by four from the preferred instruction PC.
Concrete values select an edge after width masking. Unknown/original sources fork
both edges without restoring certainty. A raw stack address refuses before W
projection or zero inference. No register, NZCV, SP or memory is modified.

The shared conditional-edge classification covers dispatch, natural-loop
successors/latches, shared teardown recognition and pop totals, target validation
and retained refused-target diagnostics. Existing path/work/observation limits,
unknown-recovery precedence, exact recurrent-state closure and terminal recovery
checks remain authoritative. Register-tested teardown evidence is distinct from
NZCV EQ–LE evidence. TBZ/TBNZ, indirect branches and unsupported loop shapes remain
outside the subset. No asynchronous or all-PC scope is claimed.

MOVK v48 remains a distinct historical model. Schema version remains 1. New known
model labels receive existing strict Python/native report admission; future-label
import does not establish engine capability.
