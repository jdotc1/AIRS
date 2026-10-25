"""CBZ/CBNZ W/X edge and recovery qualification with owned instruction words."""
from dataclasses import replace
import unittest
from airs.arm64 import ModelError, Value
from airs.cfg import PathState, audit_current_function, decode_instruction
from airs.types import Limits
from test_rbit_x_candidate import fixture, call_result, BASE, RET, PAIR_PRO, PAIR_EPI, CALL


def branch(width=64, rn=0, offset=8, nonzero=False):
    return (0xb4000000 if width == 64 else 0x34000000) | (int(nonzero)<<24) | (((offset//4)&0x7ffff)<<5) | rn


class CompareBranchTests(unittest.TestCase):
    def test_exact_width_source_displacement_and_neighbor(self):
        for width in (32,64):
            for nz in (False,True):
                for delta in (-0x100000,-4,0,4,0xffffc):
                    ins=decode_instruction(branch(width,31,delta,nz),BASE)
                    self.assertEqual((ins.kind,ins.rn,ins.immediate),
                                     (('x' if width == 64 else 'w')+('cbnz' if nz else 'cbz'),31,delta))
        with self.assertRaises(ModelError): decode_instruction(0x36000040,BASE) # TBZ remains separate.

    def test_predicate_width_zr_and_no_state_effects(self):
        for width in (32,64):
            for nz in (False,True):
                s=PathState(flags=(True,False,True,False)); s.registers[0]=Value('constant',1<<32)
                before=s.loop_key(True,0)
                self.assertEqual(s.branch_condition(decode_instruction(branch(width,nonzero=nz))),
                                 (width==32) != nz)
                self.assertEqual(s.branch_condition(decode_instruction(branch(width,31,nonzero=nz))),not nz)
                self.assertEqual(s.loop_key(True,0),before)
                with self.assertRaises(ModelError) as caught: s.apply(decode_instruction(branch(width)))
                self.assertEqual(caught.exception.code,'cfg_edge_requires_dispatch')

    def test_stack_source_refuses_before_w_projection(self):
        for width in (32,64):
            for strict in (False,True):
                s=PathState(strict_call_state=strict); s.registers[0]=Value('stack',displacement=0)
                with self.assertRaises(ModelError) as caught: s.branch_condition(decode_instruction(branch(width)))
                self.assertEqual(caught.exception.code,'compare_branch_stack_address_not_modeled')

    def test_known_taken_and_fallthrough_skip_bad_preserved_write(self):
        # CBZ/CBNZ jumps over MOV X19,#1 only when the literal predicate is true.
        for width in (32,64):
            for nz,initial in ((False,0xd2800000),(True,0xd2800020)):
                result=audit_current_function(*fixture((initial,branch(width,offset=8,nonzero=nz),0xd2800033,RET)))
                self.assertEqual(result.verdict,'agreement')
                result=audit_current_function(*fixture((initial,branch(width,offset=8,nonzero=not nz),0xd2800033,RET)))
                self.assertEqual(result.reason_codes,('unmodeled_return_state',))

    def test_unknown_source_possible_discrepancy_stays_unresolved(self):
        for width in (32,64):
            result=call_result((*PAIR_PRO,branch(width,offset=8),0xd2800033,CALL,*PAIR_EPI))
            self.assertEqual(result.verdict,'unresolved')
            self.assertIn('cfg_path_feasibility_unknown',result.reason_codes)

    def test_unknown_safe_paths_and_path_budget(self):
        words=(branch(offset=8),0xd503201f,RET)
        self.assertEqual(audit_current_function(*fixture(words)).verdict,'agreement')
        result=audit_current_function(*fixture(words),replace(Limits(),max_cfg_paths_per_function=1))
        self.assertEqual(result.reason_codes,('cfg_path_limit',))
        # A known ZR predicate requires no fork under the same budget.
        self.assertEqual(audit_current_function(*fixture((branch(rn=31),0xd503201f,RET)),
                         replace(Limits(),max_cfg_paths_per_function=1)).verdict,'agreement')

    def test_natural_loop_and_self_edge_refusal(self):
        # MOV X0,#3; SUBS W0,W0,#1; CBNZ W0,body; RET.
        words=(0xd2800060,0x71000400,branch(32,offset=-4,nonzero=True),RET)
        result=audit_current_function(*fixture(words))
        self.assertEqual(result.verdict,'agreement')
        self.assertTrue(any(e.code=='cfg_loop_checked' for e in result.evidence))
        result=audit_current_function(*fixture((branch(offset=0),RET)))
        self.assertEqual(result.reason_codes,('cfg_loop_shape_not_modeled',))

    def test_invalid_edge_retains_encoded_target_evidence(self):
        result=audit_current_function(*fixture((branch(offset=-4),RET)))
        self.assertEqual(result.reason_codes,('cfg_edge_not_modeled',))
        self.assertTrue(any('preferred VM target 0xffc' in (e.observed or '') for e in result.evidence))

    def test_shared_restore_prefix_retains_both_successors_and_total_guard(self):
        from test_cfg_conditional import FRAME, LEAF, frame, leaf
        frame_words=list(FRAME); frame_words[4]=branch(offset=12)
        r=frame(tuple(frame_words))
        self.assertEqual(r.verdict,'agreement')
        self.assertTrue(any(e.code=='cfg_compare_branch_teardown' for e in r.evidence))
        self.assertFalse(any(e.code=='cfg_conditional_teardown' for e in r.evidence))
        leaf_words=list(LEAF); leaf_words[4]=branch(offset=12)
        self.assertEqual(leaf(tuple(leaf_words)).verdict,'agreement')
        leaf_words[7]=0x910083ff
        self.assertEqual(leaf(tuple(leaf_words)).verdict,'unresolved')

    def test_concrete_later_branch_does_not_restore_certainty(self):
        # Unknown x0 forks; the known xzr branch on one successor must not make
        # its later mismatch definite. Other successor jumps directly to BL.
        words=(*PAIR_PRO,branch(offset=12),branch(rn=31,offset=4),0xd2800033,CALL,*PAIR_EPI)
        r=call_result(words)
        self.assertEqual(r.reason_codes,('cfg_path_feasibility_unknown',))

    def test_later_unknown_recovery_overrides_possible_mismatch(self):
        words=(*PAIR_PRO,branch(offset=12),0xd2800033,0x14000002,0x2a0003f3,CALL,*PAIR_EPI)
        self.assertEqual(call_result(words).reason_codes,('unknown_recovery_value',))
