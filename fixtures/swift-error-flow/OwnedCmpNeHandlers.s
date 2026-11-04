// Owned analysis input. Never loaded or executed; no runtime/CFI qualification.
.text
.p2align 2
.globl _airs_cmp_ne_literal
_airs_cmp_ne_literal:
    bl "_$s13AIRSEpilogues8validateyyKF"
    cmp x21, #0
    b.ne L_ne_error
    mov w0, #0x1234
    b L_ne_join
L_ne_error:
    mov x0, x21
    bl _swift_release
    mov x0, #-1
L_ne_join:
    ret
.subsections_via_symbols
