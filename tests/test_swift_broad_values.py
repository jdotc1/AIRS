"""Synthetic primitive patterns; these do not qualify compiler output."""
import unittest

def parameterize(names, cases):
    def decorate(function):
        def check(self):
            for case in cases:
                args = case if isinstance(case, tuple) else (case,)
                with self.subTest(case=case):
                    function(*args)
        return check
    return decorate
from airs.arm64 import Instruction


def test_typed_value_foundation_exists():
    from airs import swift_outcome_values as v
    assert v.initial_state().read_register('x0') == v.Unknown()


def ins(kind, rd=0, rn=0, immediate=0, rt2=0, addressing=''):
    return Instruction(0, 0, kind, rd, rn, rt2, immediate, addressing)


def run(*instructions, seeds=None, limits=None):
    from airs import swift_outcome_values as v
    state = v.initial_state(seeds)
    for instruction in instructions:
        result = v.transfer_swift_value(state, instruction, **({'limits': limits} if limits else {}))
        assert result.status == 'resolved', result.reason
        state = result.state
    return state


@parameterize('kind,value,width', [('movz',17,64),('wmovz',17,32),('movn',-18,64),('wmovn',-18,32)])
def test_literal_width_patterns(kind,value,width):
    from airs import swift_outcome_values as v
    state = run(ins(kind, immediate=17))
    assert state.read_register('x0') == v.Literal(value & ((1 << width)-1),64)


def test_aliases_and_zero_register_are_distinct_from_sp():
    from airs import swift_outcome_values as v
    state = run(ins('wmov',1,0), ins('mov',2,31), ins('sub',31,31,32),seeds={0:v.Literal((1<<40)+7,64)})
    assert state.read_register('x1') == v.Literal(7,64)
    assert state.read_register('x2') == v.Literal(0,64)
    assert state.sp_offset == -32
    assert state.read_register('wzr') == v.Literal(0,32)


@parameterize('kind,start,imm,expected', [('add',(1<<64)-1,1,0),('sub',0,1,(1<<64)-1),('wadd',0xffffffff,2,1),('wlsl',3,2,12)])
def test_arithmetic_modulo_patterns(kind,start,imm,expected):
    from airs import swift_outcome_values as v
    state = run(ins(kind,0,0,imm),seeds={0:v.Literal(start,64)})
    assert state.read_register(0) == v.Literal(expected,64)


def test_symbolic_copies_keep_origin_and_epoch():
    from airs import swift_outcome_values as v
    origin=v.RegisterCopy('argument:x0@0',64)
    state=run(ins('mov',1,0),ins('movz',0,immediate=99),seeds={0:origin})
    assert state.read_register(1)==origin
    assert dict(state.register_epochs)[0]==1
    assert state.read_register(0)==v.Literal(99,64)


def test_abi_seeds_are_explicit_and_calls_clobber():
    from airs import swift_outcome_values as v
    state=run(ins('bl'),seeds={0:v.Literal(7,64),19:v.Literal(8,64),21:v.Literal(9,64)})
    assert state.read_register(0)==v.Unknown()
    assert state.read_register(19)==v.Literal(8,64)
    assert v.initial_state().read_register(21)==v.Unknown()


def test_stack_roundtrip_overlap_epoch_and_call_escape():
    from airs import swift_outcome_values as v
    state=run(ins('sub',31,31,32),ins('movz',immediate=42),ins('xstr',0,31),ins('xldr',1,31))
    assert state.read_register(1)==v.Literal(42,64)
    overwritten=v.transfer_swift_value(state,ins('wstr',0,31,4)).state
    assert overwritten.stack_epoch>state.stack_epoch
    assert v.transfer_swift_value(overwritten,ins('xldr',2,31)).state.read_register(2)==v.Unknown()
    called=v.transfer_swift_value(state,ins('bl')).state
    assert not called.stack


def test_pair_writeback_and_frame_release():
    from airs import swift_outcome_values as v
    state=run(ins('stp',0,31,-16,1,'pre'),ins('ldp',2,31,16,3,'post'),seeds={0:v.Literal(5,64),1:v.Literal(6,64)})
    assert state.read_register(2)==v.Literal(5,64)
    assert state.read_register(3)==v.Literal(6,64)
    assert state.sp_offset==0
    assert not state.stack


def test_join_never_turns_missing_unknown_or_unavailable_into_zero():
    from airs import swift_outcome_values as v
    a=v.initial_state({0:v.Literal(0,64),1:v.Unavailable()})
    b=v.initial_state({0:v.Literal(1,64)})
    merged=v.join_swift_values((a,b))
    assert isinstance(merged.read_register(0),v.PhiMerge)
    assert merged.read_register(1)==v.Unknown()
    assert v.join_swift_values((a,v.initial_state())).read_register(0)==v.Unknown()


@parameterize('kind',['pacibsp','retab','br','blr','xudiv','unmodeled'])
def test_unmodeled_or_authenticated_transfer_refuses(kind):
    from airs import swift_outcome_values as v
    assert v.transfer_swift_value(v.initial_state(),ins(kind)).status=='unresolved'


def test_bounds_are_checked_before_growth():
    from airs import swift_outcome_values as v
    state=v.initial_state()
    assert v.transfer_swift_value(state,ins('nop'),limits=v.ValueLimits(max_steps=0)).status=='unresolved'
    state=run(ins('sub',31,31,16))
    assert v.transfer_swift_value(state,ins('xstr',0,31),limits=v.ValueLimits(max_slots=0)).status=='unresolved'
    assert v.join_swift_values((v.initial_state({0:v.Literal(0,64)}),v.initial_state({0:v.Literal(1,64)})),limits=v.ValueLimits(max_merge_inputs=1)).read_register(0)==v.Unknown()


def test_sign_extension_and_unsupported_bitfield_mutation():
    from airs import swift_outcome_values as v
    state=run(ins('xsbfm',0,0,7,addressing='0'),seeds={0:v.Literal(255,64)})
    assert state.read_register(0)==v.Literal((1<<64)-1,64)
    result=v.transfer_swift_value(state,ins('xsbfm',0,0,7,addressing='3'))
    assert result.status=='unresolved'


def test_frame_pointer_sp_restore_and_outside_frame_refusal():
    from airs import swift_outcome_values as v
    state=run(ins('sub',31,31,32),ins('add',29,31,0),ins('movz',immediate=12),ins('xstr',0,29,8),ins('xldr',1,29,8),ins('add',31,29,32))
    assert state.read_register(1)==v.Literal(12,64)
    assert state.sp_offset==0
    assert v.transfer_swift_value(state,ins('xstr',0,31)).status=='unresolved'


def test_decoded_words_lane_insert_and_mutated_shift():
    from airs import swift_outcome_values as v
    from airs.swift_error_flow import decode_instruction
    state=run(decode_instruction(0x52800020),decode_instruction(0x72a00040))
    assert state.read_register(0)==v.Literal(0x20001,64)
    result=v.transfer_swift_value(state,ins('wmovk',immediate=3,addressing='32'))
    assert result.status=='unresolved'


def test_symbolic_width_conversion_provenance_and_trace_limit():
    from airs import swift_outcome_values as v
    state=run(ins('wmov',1,0),seeds={0:v.RegisterCopy('argument:x0@0',64)})
    assert isinstance(state.read_register(1),v.Derived)
    assert state.read_register(1).operation=='zero_extend'
    result=v.trace_swift_values((ins('nop') for _ in range(3)),limits=v.ValueLimits(max_steps=2))
    assert result.status=='unresolved' and result.state.steps==2


def test_decoded_conditional_tail_is_value_neutral_and_capacity_refuses():
    from airs import swift_outcome_values as v
    from airs.cfg import decode_instruction
    state=v.initial_state({0:v.Literal(4,64)})
    result=v.transfer_swift_value(state,decode_instruction(0xb4000020))
    assert result.status=='resolved' and result.state.read_register(0)==v.Literal(4,64)
    result=v.transfer_swift_value(state,ins('mov',1,0),limits=v.ValueLimits(max_state_entries=1))
    assert result.status=='unresolved' and result.state==state


@parameterize('kind', ['wadd','wadds','wsubs','xadds','xsubs'])
def test_immediate_sp_source_is_never_zero_register(kind):
    from airs import swift_outcome_values as v
    result=v.transfer_swift_value(v.initial_state(),ins(kind,0,31,1))
    assert result.status=='unresolved'


def test_typed_domain_rejects_mutable_inputs_and_invalid_width():
    from airs import swift_outcome_values as v
    for create in (lambda:v.Derived('add',[],64),lambda:v.RegisterCopy('x0',8),lambda:v.PhiMerge([])):
        try:create()
        except ValueError:pass
        else:raise AssertionError('invalid domain member accepted')


def test_join_limit_refusal_cannot_manufacture_sp_or_reset_budget():
    from airs import swift_outcome_values as v
    from dataclasses import replace
    state=replace(v.initial_state(),sp_offset=None,steps=9)
    joined=v.join_swift_values((state,state),limits=v.ValueLimits(max_merge_inputs=1,max_steps=10))
    assert joined.sp_offset is None and joined.steps>=state.steps
    assert joined.refusal is not None
    result=v.transfer_swift_value(joined,ins('sub',31,31,16))
    assert result.status=='unresolved'
    assert v.transfer_swift_value(result.state,ins('xstr',0,31)).status=='unresolved'


def test_join_and_transfer_preflight_external_value_trees():
    from airs import swift_outcome_values as v
    value=v.Literal(1,64)
    for _ in range(1100):value=v.PhiMerge((value,))
    external=v.ValueState(registers=((0,value),))
    joined=v.join_swift_values((external,))
    assert joined.refusal=='value_provenance_limit'
    assert v.transfer_swift_value(external,ins('nop')).status=='unresolved'
    stacked=v.ValueState(stack=(v.StackCell(-8,1,64,value),),sp_offset=-16)
    assert v.transfer_swift_value(stacked,ins('xldr',0,31,8)).status=='unresolved'
    wide=v.PhiMerge(tuple(v.Literal(i,64) for i in range(100)))
    assert v.join_swift_values((v.ValueState(registers=((0,wide),)),)).refusal=='value_provenance_limit'


@parameterize('kind,immediate,addressing', [
    ('movz',-1,''),('movn',-1,''),('wmovz',-1,''),('wmovn',-1,''),
    ('movz',(1<<40)+7,''),('wmovz',1<<32,''),('movn',0x10001,''),
    ('xmovk',65536,'0'),('wmovk',-1,'16'),('xmovk',-1,'0'),
])
def test_move_wide_refuses_impossible_decoded_immediates(kind,immediate,addressing):
    from airs import swift_outcome_values as v
    state=v.initial_state({0:v.Literal(0,64)})
    result=v.transfer_swift_value(state,ins(kind,immediate=immediate,addressing=addressing))
    assert result.status=='unresolved' and result.state==state


@parameterize('kind,immediate', [('movz',0xffff<<48),('movn',0x1234<<32),('wmovz',0xffff<<16),('wmovn',0)])
def test_move_wide_accepts_exact_single_lane_immediates(kind,immediate):
    from airs import swift_outcome_values as v
    width=32 if kind.startswith('w') else 64
    expected=(~immediate if kind.endswith('movn') else immediate)&((1<<width)-1)
    assert run(ins(kind,immediate=immediate)).read_register(0)==v.Literal(expected,64)


class TestBroadValues(unittest.TestCase):
    pass

for _name, _test in list(globals().items()):
    if _name.startswith("test_"):
        if _test.__name__ == "check":
            setattr(TestBroadValues, _name, _test)
        else:
            def _method(self, test=_test):
                test()
            setattr(TestBroadValues, _name, _method)

del _name, _test, _method


class BroadRegisterBankTransferTests(unittest.TestCase):
    def test_logical_masks_and_conditional_writes_never_retain_stale_values(self):
        from airs import swift_outcome_values as v
        from airs.swift_broad_instructions import decode_instruction
        state=v.initial_state({'x22':v.Literal(3,64),'x0':v.Literal(6,64),
                               'x21':v.RegisterCopy('new-logical-transfer-test',64)})
        result=v.transfer_swift_value(state,decode_instruction(0x120002c0)) # AND W0,W22,#1
        self.assertEqual(result.state.read_register('x0'),v.Literal(1,64))
        result=v.transfer_swift_value(state,ins('xorr_imm',0,0,8))
        self.assertEqual(result.state.read_register('x0'),v.Literal(14,64))
        result=v.transfer_swift_value(state,ins('xeor_imm',0,0,3))
        self.assertEqual(result.state.read_register('x0'),v.Literal(5,64))
        result=v.transfer_swift_value(state,decode_instruction(0x7100011f)) # CMP W8,#0
        self.assertEqual(result.state.read_register('x21'),state.read_register('x21'))
        result=v.transfer_swift_value(state,decode_instruction(0x9a810015)) # CSEL X21,X0,X1,EQ
        self.assertEqual(result.state.read_register('x21'),v.Unknown())

    def test_unsigned_bitfield_shift_extract_insert_and_unknown(self):
        from airs import swift_outcome_values as v
        cases=((64,63,62,0xffffffffffffffff,0xfffffffffffffffe),
               (64,4,11,0xabcde,0xcd),(64,60,3,0xa,0xa0),(32,4,7,0xff,0xf))
        for width,rotate,end,number,expected in cases:
            with self.subTest(width=width,rotate=rotate,end=end):
                state=v.initial_state({'x1':v.Literal(number,width)})
                result=v.transfer_swift_value(state,ins('xubfm' if width==64 else 'wubfm',
                    rd=0,rn=1,immediate=end,addressing=str(rotate)))
                self.assertEqual(result.state.read_register('x0'),v.Literal(expected,64))
        result=v.transfer_swift_value(v.initial_state(),ins('xubfm',rd=0,rn=1,immediate=62,addressing='63'))
        self.assertEqual(result.state.read_register('x0'),v.Unknown())

    def test_new_generic_memory_and_register_arithmetic_preserve_only_proved_origins(self):
        from airs import swift_outcome_values as v
        from airs.swift_broad_instructions import decode_instruction
        state=v.initial_state({'x1':v.Literal(7,64),'x2':v.Literal(9,64),
                               'x21':v.RegisterCopy('new-generic-memory-test',64)})
        result=v.transfer_swift_value(state,decode_instruction(0x8b020020))
        self.assertEqual(result.state.read_register('x0'),v.Literal(16,64))
        for instruction in (ins('sub',31,31,32),ins('add',1,31,8)):
            state=v.transfer_swift_value(state,instruction).state
        state=v.transfer_swift_value(state,decode_instruction(0xf9000035)).state # STR X21,[X1]
        state=v.transfer_swift_value(state,decode_instruction(0xf9400022)).state # LDR X2,[X1]
        self.assertEqual(state.read_register('x2'),v.RegisterCopy('new-generic-memory-test',64))
        # A vector store overlaps the cell but cannot fabricate a scalar value.
        state=v.transfer_swift_value(state,decode_instruction(0x3d8003e0)).state # STR Q0,[SP]
        self.assertFalse(state.stack)

    def test_fp_destination_and_flags_cannot_clobber_gpr_error_origin(self):
        from airs import swift_outcome_values as v
        from airs.swift_broad_instructions import decode_instruction
        seed=v.RegisterCopy('new-register-bank-test',64)
        state=v.initial_state({'x21':seed})
        for word in (0x9e670115,0x1e6022a0):
            step=v.transfer_swift_value(state,decode_instruction(word))
            self.assertEqual(step.status,'resolved',step)
            self.assertEqual(step.state.read_register('x21'),seed)
        # FMOV X21,D0 crosses banks and destroys an error-register origin.
        step=v.transfer_swift_value(state,decode_instruction(0x9e660015))
        self.assertEqual(step.state.read_register('x21'),v.Unknown())

    def test_partial_store_forgets_overlapping_qualified_stack_cell(self):
        from airs import swift_outcome_values as v
        from airs.swift_broad_instructions import decode_instruction
        state=v.initial_state({'x21':v.RegisterCopy('new-partial-memory-test',64)})
        for instruction in (ins('sub',31,31,16),ins('xstr',21,31,0,addressing='offset')):
            state=v.transfer_swift_value(state,instruction).state
        self.assertEqual(len(state.stack),1)
        step=v.transfer_swift_value(state,decode_instruction(0x390007e0)) # STRB W0,[SP,#1]
        self.assertEqual(step.status,'resolved')
        self.assertFalse(step.state.stack)
        step=v.transfer_swift_value(step.state,ins('xldr',1,31,0,addressing='offset'))
        self.assertEqual(step.state.read_register('x1'),v.Unknown())

    def test_unknown_narrow_address_invalidates_stack_and_load_forgets_target(self):
        from airs import swift_outcome_values as v
        from airs.swift_broad_instructions import decode_instruction
        seed=v.RegisterCopy('new-unknown-memory-test',64)
        state=v.initial_state({'x21':seed})
        for instruction in (ins('sub',31,31,16),ins('xstr',21,31,0,addressing='offset')):
            state=v.transfer_swift_value(state,instruction).state
        step=v.transfer_swift_value(state,decode_instruction(0x79000140)) # STRH W0,[X10]
        self.assertFalse(step.state.stack)
        step=v.transfer_swift_value(state,decode_instruction(0x394003f5)) # LDRB W21,[SP]
        self.assertEqual(step.state.read_register('x21'),v.Unknown())
