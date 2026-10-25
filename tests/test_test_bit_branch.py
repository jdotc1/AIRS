"""Owned TBZ/TBNZ bit predicates and conservative CFG recovery boundaries."""
from dataclasses import replace
import unittest
from airs.arm64 import ModelError, Value, original
from airs.cfg import PathState, audit_current_function, decode_instruction
from airs.types import Limits
from test_rbit_x_candidate import fixture, call_result, BASE, RET, PAIR_PRO, PAIR_EPI, CALL


def branch(bit=0, rn=0, offset=8, nonzero=False):
    return 0x36000000 | ((bit>>5)<<31) | ((bit&31)<<19) | (int(nonzero)<<24) | (((offset//4)&0x3fff)<<5) | rn


class TestBitBranchTests(unittest.TestCase):
    def test_all_bit_fields_extreme_displacements_and_exact_controls(self):
        for bit in range(64):
            for nz in (False,True):
                for delta in (-32768,-4,0,4,32764):
                    ins=decode_instruction(branch(bit,31,delta,nz),BASE)
                    self.assertEqual((ins.kind,ins.rn,ins.immediate,ins.addressing),
                                     (('x' if bit>=32 else 'w')+('tbnz' if nz else 'tbz'),31,delta,str(bit)))
        for fixed in (25,26,27,28,29,30):
            try: ins=decode_instruction(branch()^(1<<fixed),BASE)
            except ModelError: continue
            self.assertNotIn(ins.kind,('wtbz','wtbnz','xtbz','xtbnz'))

    def test_selected_bit_only_zr_and_state_preservation(self):
        for bit in range(64):
            for nz in (False,True):
                for value,set_bit in ((0,False),(1<<bit,True),((1<<64)-1,True),
                                      (-1,True),(1<<(bit+64),False)):
                    s=PathState(flags=(True,False,True,False),memory={-16:original(29)})
                    s.registers[0]=Value('constant',value)
                    before=s.loop_key(True,0)
                    self.assertEqual(s.branch_condition(decode_instruction(branch(bit,nonzero=nz))),set_bit==nz)
                    self.assertEqual(s.branch_condition(decode_instruction(branch(bit,31,nonzero=nz))),not nz)
                    self.assertEqual(s.loop_key(True,0),before)
        with self.assertRaises(ModelError) as caught: PathState().apply(decode_instruction(branch()))
        self.assertEqual(caught.exception.code,'cfg_edge_requires_dispatch')

    def test_unknown_original_and_raw_stack_source(self):
        for bit in (0,31,32,63):
            for raw in (original(0),Value('unknown','input')):
                s=PathState();s.registers[0]=raw
                self.assertIsNone(s.branch_condition(decode_instruction(branch(bit))))
            for strict in (False,True):
                s=PathState(strict_call_state=strict);s.registers[0]=Value('stack',displacement=0)
                with self.assertRaises(ModelError) as caught:s.branch_condition(decode_instruction(branch(bit)))
                self.assertEqual(caught.exception.code,'test_bit_branch_stack_address_not_modeled')

    def test_known_taken_fallthrough_skip_bad_write_at_high_and_low_bits(self):
        for bit,mov in ((0,0xd2800020),(31,0xd2b00000),(32,0xd2c00020),(63,0xd2f00000)):
            for nz,initial in ((False,0xd2800000),(True,mov)):
                words=(initial,branch(bit,offset=8,nonzero=nz),0xd2800033,RET)
                self.assertEqual(audit_current_function(*fixture(words)).verdict,'agreement')
                words=(initial,branch(bit,offset=8,nonzero=not nz),0xd2800033,RET)
                self.assertEqual(audit_current_function(*fixture(words)).reason_codes,('unmodeled_return_state',))

    def test_unknown_path_mismatch_and_later_unknown_precedence(self):
        for bit in (0,63):
            words=(*PAIR_PRO,branch(bit),0xd2800033,CALL,*PAIR_EPI)
            self.assertEqual(call_result(words).reason_codes,('cfg_path_feasibility_unknown',))
            words=(*PAIR_PRO,branch(bit,offset=12),0xd2800033,0x14000002,0x2a0003f3,CALL,*PAIR_EPI)
            self.assertEqual(call_result(words).reason_codes,('unknown_recovery_value',))

    def test_unknown_safe_paths_limits_and_zr_without_fork(self):
        words=(branch(),0xd503201f,RET)
        self.assertEqual(audit_current_function(*fixture(words)).verdict,'agreement')
        limited=replace(Limits(),max_cfg_paths_per_function=1)
        self.assertEqual(audit_current_function(*fixture(words),limited).reason_codes,('cfg_path_limit',))
        self.assertEqual(audit_current_function(*fixture((branch(rn=31),0xd503201f,RET)),limited).verdict,'agreement')
        limited=replace(Limits(),max_cfg_steps_per_function=1)
        self.assertEqual(audit_current_function(*fixture(words),limited).reason_codes,('cfg_work_limit',))

    def test_natural_loop_negative_displacement_and_self_edge_refusal(self):
        words=(0xd2800040,0x71000400,branch(0,offset=-4,nonzero=True),RET)
        result=audit_current_function(*fixture(words))
        self.assertEqual(result.verdict,'agreement')
        self.assertTrue(any(e.code=='cfg_loop_checked' for e in result.evidence))
        self.assertEqual(audit_current_function(*fixture((branch(offset=0),RET))).reason_codes,('cfg_loop_shape_not_modeled',))

    def test_refused_target_evidence(self):
        result=audit_current_function(*fixture((branch(offset=-4),RET)))
        self.assertEqual(result.reason_codes,('cfg_edge_not_modeled',))
        self.assertTrue(any('preferred VM target 0xffc' in (e.observed or '') for e in result.evidence))

    def test_shared_teardown_successors_and_pop_totals(self):
        from test_cfg_conditional import FRAME, LEAF, frame, leaf
        words=list(FRAME);words[4]=branch(63,offset=12)
        result=frame(tuple(words))
        self.assertEqual(result.verdict,'agreement')
        self.assertTrue(any(e.code=='cfg_test_bit_branch_teardown' for e in result.evidence))
        self.assertFalse(any(e.code in ('cfg_conditional_teardown','cfg_compare_branch_teardown') for e in result.evidence))
        words=list(LEAF);words[4]=branch(offset=12)
        self.assertEqual(leaf(tuple(words)).verdict,'agreement')
        words[7]=0x910083ff
        self.assertEqual(leaf(tuple(words)).verdict,'unresolved')

    def test_later_known_bit_branch_preserves_uncertainty(self):
        words=(*PAIR_PRO,branch(offset=12),branch(rn=31,offset=4),0xd2800033,CALL,*PAIR_EPI)
        self.assertEqual(call_result(words).reason_codes,('cfg_path_feasibility_unknown',))
