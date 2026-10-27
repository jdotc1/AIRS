// Owned analysis input. Never loaded or executed; no runtime/CFI qualification.
.text
.p2align 2
.globl _airs_scalar_post
_airs_scalar_post:
.cfi_startproc
    sub sp, sp, #32
    stp x19, x21, [sp]
    str x30, [sp, #16]
    mov x21, xzr
    bl "_$s13AIRSEpilogues8validateyyKF"
    cbz x21, L_scalar_success
    mov x0, x21
    bl _swift_release
    mov x0, #-1
    b L_scalar_join
L_scalar_success:
    mov w19, #0x1234
    mov w0, w19
L_scalar_join:
    ldr x30, [sp, #16]
    ldr x21, [sp, #8]
    ldr x19, [sp], #32
    ret
.cfi_endproc

.p2align 2
.globl _airs_split_frame
_airs_split_frame:
.cfi_startproc
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    sub sp, sp, #16
    stp x19, x21, [sp]
    mov x21, xzr
    bl "_$s13AIRSEpilogues8validateyyKF"
    cbz x21, L_split_success
    mov x0, x21
    bl _swift_release
    mov x0, #-2
    b L_split_join
L_split_success:
    mov w0, #0x5678
L_split_join:
    ldp x19, x21, [sp]
    mov sp, x29
    ldr x30, [sp, #8]
    ldr x29, [sp], #16
    ret
.cfi_endproc
.subsections_via_symbols
