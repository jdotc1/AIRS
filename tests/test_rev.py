"""Bounded full-register byte reversal; REV16/REV32 have separate coverage; vector forms stay outside scope."""
from dataclasses import replace
import unittest

from airs.arm64 import ModelError, Value, original
from airs.cfg import PathState, audit_current_function, decode_instruction
from airs.report import validate_report
from airs.types import InputError, Limits
from test_rbit_x_candidate import fixture, call_result, BASE, RET, PRO, EPI, PAIR_PRO, PAIR_EPI, CALL
from test_report_v32_admission_candidate import synthetic_report

MODEL = 'arm64-bounded-rev-v44'


def word(width=32, rd=0, rn=1):
    return (0x5ac00800 if width == 32 else 0xdac00c00) | (rn << 5) | rd


def oracle(value, width):
    """Byte serialization oracle independent of the candidate's shift loop."""
    masked = value & ((1 << width) - 1)
    return int.from_bytes(masked.to_bytes(width // 8, 'little'), 'big')


class REVTests(unittest.TestCase):
    def test_exact_w_x_decoding_and_fixed_control_neighbors(self):
        for width, kind in ((32, 'wrev'), (64, 'xrev')):
            ins = decode_instruction(word(width, 4, 5), BASE)
            self.assertEqual((ins.kind, ins.rd, ins.rn), (kind, 4, 5))
            for bit in range(10, 32):
                try:
                    changed = decode_instruction(word(width) ^ (1 << bit), BASE)
                except ModelError:
                    continue
                self.assertNotIn(changed.kind, ('wrev', 'xrev'))
        for refused in (0x7ac00420, 0xfac00420, 0xfac00820, 0x5ac00c20, 0x4e200820):
            with self.subTest(word=hex(refused)), self.assertRaises(ModelError):
                decode_instruction(refused, BASE)

    def test_concrete_permutations_projection_alias_and_independent_oracle(self):
        cases = [(32, 0x01234567, 0x67452301), (64, 0x0123456789abcdef, 0xefcdab8967452301),
                 (32, 0x1234567889abcdef, 0xefcdab89), (32, -2, 0xfeffffff),
                 (64, -2, 0xfeffffffffffffff), (32, 0x80000000, 0x80),
                 (64, 0x8000000000000000, 0x80), (32, 0, 0), (64, -1, 0xffffffffffffffff)]
        for width, value, expected in cases:
            with self.subTest(width=width, value=value):
                self.assertEqual(oracle(value, width), expected)
                state = PathState()
                state.registers[1] = Value('constant', value)
                state.apply(decode_instruction(word(width, 1, 1), BASE))
                self.assertEqual(state.registers[1], Value('constant', expected))
                state.apply(decode_instruction(word(width, 1, 1), BASE))
                self.assertEqual(state.registers[1], Value('constant', value & ((1 << width) - 1)))

    def test_zr_discard_flags_memory_sp_and_unrelated_registers(self):
        for width in (32, 64):
            for flags in (None, (True, False, True, False)):
                state = PathState(flags=flags, memory={-16: original(29)})
                state.registers[1] = Value('constant', 0x1234)
                before = state.registers.copy()
                conditions = [state.condition(c) for c in range(14)]
                state.apply(decode_instruction(word(width, 31, 1), BASE))
                self.assertEqual(state.registers, before)
                state.apply(decode_instruction(word(width, 0, 31), BASE))
                self.assertEqual(state.registers[0], Value('constant', 0))
                self.assertEqual(state.registers[1:], before[1:])
                self.assertEqual(state.flags, flags)
                self.assertEqual([state.condition(c) for c in range(14)], conditions)
                self.assertEqual(state.memory, {-16: original(29)})
                self.assertEqual(state.sp, Value('stack', displacement=0))

    def test_raw_stack_declines_before_projection_or_discard(self):
        for width in (32, 64):
            for strict in (False, True):
                for rd in (0, 31):
                    state = PathState(strict_call_state=strict)
                    state.registers[1] = Value('stack', displacement=0)
                    with self.assertRaises(ModelError) as caught:
                        state.apply(decode_instruction(word(width, rd), BASE))
                    self.assertEqual(caught.exception.code, 'rev_stack_address_not_modeled')

    def test_unknown_original_and_double_reversal_never_restore_identity(self):
        for width in (32, 64):
            for raw in (original(19), Value('unknown', 'input')):
                state = PathState()
                state.registers[19] = raw
                state.apply(decode_instruction(word(width, 19, 19), BASE))
                state.apply(decode_instruction(word(width, 19, 19), BASE))
                self.assertEqual(state.registers[19].kind, 'unknown')

    def test_owned_leaf_and_refused_control_remain_distinct(self):
        for width in (32, 64):
            result = audit_current_function(*fixture((word(width, 0, 0), RET)))
            self.assertEqual((result.verdict, result.scope, result.checked_pcs),
                             ('agreement', 'modeled_leaf_body', (BASE,)))
        result = audit_current_function(*fixture((0xfac00820, RET)))
        self.assertEqual((result.verdict, result.checked_pcs), ('unresolved', ()))

    def test_frame_and_unrestored_preserved_writes_remain_unresolved(self):
        for width in (32, 64):
            result = call_result((*PRO, word(width, 29, 0), CALL, *EPI))
            self.assertEqual(result.reason_codes, ('cfg_frame_transition_not_modeled',))
            result = audit_current_function(*fixture((word(width, 19, 0), RET)))
            self.assertEqual(result.reason_codes, ('unmodeled_return_state',))

    def test_call_recovery_known_correct_wrong_and_unknown(self):
        for width, expected in ((32, 'constant 0x34120000'), (64, 'constant 0x3412000000000000')):
            words = (*PAIR_PRO, 0xd2824680, word(width, 19, 0), CALL, *PAIR_EPI)
            correct = call_result(words, encoding=0x04000001)
            self.assertEqual((correct.verdict, correct.scope), ('agreement', 'synchronous_call_sites'))
            wrong = call_result(words, encoding=0x04000000)
            self.assertEqual((wrong.verdict, wrong.checked_pcs), ('inconsistency', (BASE + 24,)))
            self.assertTrue(any(e.observed == expected for e in wrong.evidence))
            unknown = call_result((*PAIR_PRO, word(width, 19, 19), CALL, *PAIR_EPI), encoding=0x04000000)
            self.assertEqual(unknown.reason_codes, ('unknown_recovery_value',))

    def test_possible_only_and_later_unknown_keep_unresolved_precedence(self):
        for width in (32, 64):
            concrete = (0xd2824680, word(width, 19, 0))
            possible = call_result((*PAIR_PRO, 0x54000060, *concrete, CALL, *PAIR_EPI), encoding=0x04000000)
            self.assertEqual(possible.reason_codes, ('cfg_path_feasibility_unknown',))
            later = call_result((*PAIR_PRO, *concrete, CALL, word(width, 19, 0), CALL, *PAIR_EPI),
                                encoding=0x04000000, limits=replace(Limits(), max_evidence_per_function=1))
            self.assertEqual(later.reason_codes, ('unknown_recovery_value',))

    def test_dead_refusal_and_work_limits_remain_unresolved(self):
        for width in (32, 64):
            dead = audit_current_function(*fixture((0x14000002, 0x3ac10c00, word(width), RET)))
            self.assertEqual((dead.verdict, dead.checked_pcs), ('unresolved', ()))
            result = audit_current_function(*fixture((word(width), RET)), replace(Limits(), max_cfg_steps_per_function=0))
            self.assertEqual(result.reason_codes, ('cfg_work_limit',))

    def test_exact_v44_and_historical_import_boundaries(self):
        for model in (MODEL, 'arm64-bounded-w-udiv-v43', 'arm64-bounded-w-sdiv-v42'):
            value = synthetic_report(model)
            self.assertIs(validate_report(value), value)
            value['image']['cpu_subtype'] = 0x80000000
            with self.assertRaises(InputError):
                validate_report(value)
        future = synthetic_report(MODEL + '-future')
        future['image']['cpu_subtype'] = 0x80000000
        self.assertIs(validate_report(future), future)
