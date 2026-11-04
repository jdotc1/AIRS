"""Owned MOVK encodings and recovery boundaries; target instructions are data."""
import unittest
from airs.arm64 import ModelError, Value, original
from airs.cfg import PathState, audit_current_function, decode_instruction
from test_rbit_x_candidate import fixture, call_result, BASE, RET, PAIR_PRO, PAIR_EPI, PRO, EPI, CALL


def word(width=64, rd=0, imm=0x1234, shift=0):
    return (0xf2800000 if width == 64 else 0x72800000) | ((shift//16)<<21) | (imm<<5) | rd


class MOVKTests(unittest.TestCase):
    def test_decode_exact_fields_and_invalid_word_shifts(self):
        for width in (32, 64):
            for shift in range(0, width, 16):
                ins=decode_instruction(word(width, 19, 0xabcd, shift), BASE)
                self.assertEqual((ins.kind, ins.rd, ins.immediate, ins.addressing),
                                 ('xmovk' if width == 64 else 'wmovk', 19, 0xabcd, str(shift)))
        for shift in (32, 48):
            with self.assertRaises(ModelError): decode_instruction(word(32, shift=shift), BASE)
        for bit in (23, 24, 25, 26, 27, 28, 29, 30):
            try: ins=decode_instruction(word() ^ (1<<bit), BASE)
            except ModelError: continue
            self.assertNotIn(ins.kind, ('xmovk', 'wmovk'))

    def test_lane_replacement_width_and_old_destination(self):
        # Literal expectations independent of the implementation mask formula.
        for width, shift, expected in ((64,0,0x0123456789abbeef), (64,16,0x01234567beefcdef),
                                      (64,32,0x0123beef89abcdef), (64,48,0xbeef456789abcdef),
                                      (32,0,0x89abbeef), (32,16,0xbeefcdef)):
            s=PathState(); s.registers[0]=Value('constant',0x0123456789abcdef)
            s.apply(decode_instruction(word(width, 0, 0xbeef, shift)))
            self.assertEqual(s.registers[0], Value('constant',expected))

    def test_unknown_and_original_remain_unknown_even_after_all_lanes(self):
        for width in (32,64):
            for value in (original(19),Value('unknown','input')):
                s=PathState(); s.registers[19]=value
                for shift in range(0,width,16): s.apply(decode_instruction(word(width,19,0,shift)))
                self.assertEqual(s.registers[19].kind,'unknown')

    def test_raw_stack_destination_refuses_before_projection(self):
        for width in (32,64):
            for strict in (False,True):
                s=PathState(strict_call_state=strict); s.registers[0]=Value('stack',displacement=-16)
                with self.assertRaises(ModelError) as caught: s.apply(decode_instruction(word(width)))
                self.assertEqual(caught.exception.code,'movk_stack_address_not_modeled')

    def test_zr_discard_flags_memory_and_sp(self):
        for width in (32,64):
            s=PathState(flags=(True,False,True,False),memory={-16:original(29)})
            before=s.copy()
            s.apply(decode_instruction(word(width,31)))
            self.assertEqual(s.loop_key(True,0),before.loop_key(True,0))

    def test_owned_leaf_and_frame_guards(self):
        self.assertEqual(audit_current_function(*fixture((0xd2800000,word(),RET))).verdict,'agreement')
        self.assertEqual(call_result((*PRO,word(rd=29),CALL,*EPI)).reason_codes,
                         ('cfg_frame_transition_not_modeled',))
        self.assertEqual(audit_current_function(*fixture((word(rd=19),RET))).reason_codes,
                         ('unmodeled_return_state',))

    def test_call_recovery_correct_wrong_and_unknown(self):
        for width in (32,64):
            words=(*PAIR_PRO,0xd2800013,word(width,19,0x1234),CALL,*PAIR_EPI)
            self.assertEqual(call_result(words,encoding=0x04000001).verdict,'agreement')
            wrong=call_result(words,encoding=0x04000000)
            self.assertEqual((wrong.verdict,wrong.checked_pcs),('inconsistency',(BASE+24,)))
            self.assertTrue(any(e.observed=='constant 0x1234' for e in wrong.evidence))
            unknown=call_result((*PAIR_PRO,word(width,19),CALL,*PAIR_EPI))
            self.assertEqual(unknown.reason_codes,('unknown_recovery_value',))

    def test_normalization_and_zero_lane_do_not_preserve_symbolic_identity(self):
        for width in (32,64):
            s=PathState(); s.registers[0]=Value('constant',-1)
            s.apply(decode_instruction(word(width,0,0)))
            self.assertEqual(s.registers[0],Value('constant',((1<<width)-1)^0xffff))
