"""Bounded REV32 X: each 32-bit word reverses bytes without swapping words."""
from dataclasses import replace
import unittest

from airs.arm64 import ModelError, Value, original
from airs.cfg import PathState, audit_current_function, decode_instruction
from airs.report import validate_report
from airs.types import InputError, Limits
from test_rbit_x_candidate import fixture, call_result, BASE, RET, PRO, EPI, PAIR_PRO, PAIR_EPI, CALL
from test_report_v32_admission_candidate import synthetic_report

MODEL = 'arm64-bounded-rev32-v46'
MASK = (1 << 64) - 1


def word(rd=0, rn=1):
    return 0xdac00800 | (rn << 5) | rd


def oracle(value):
    data = (value & MASK).to_bytes(8, 'big')
    return int.from_bytes(data[:4][::-1] + data[4:][::-1], 'big')


class REV32Tests(unittest.TestCase):
    def test_exact_decoder_and_existing_w_rev_neighbor(self):
        ins = decode_instruction(word(4, 5), BASE)
        self.assertEqual((ins.kind, ins.rd, ins.rn), ('xrev32', 4, 5))
        for bit in range(10, 32):
            try:
                changed = decode_instruction(word() ^ (1 << bit), BASE)
            except ModelError:
                continue
            self.assertNotEqual(changed.kind, 'xrev32')
        self.assertEqual(decode_instruction(word() ^ (1 << 31), BASE).kind, 'wrev')
        self.assertEqual(decode_instruction(word() | (1 << 10), BASE).kind, 'xrev')
        for refused in (0x5ac00c20, 0xdac01420, 0x4e200820):
            with self.subTest(word=hex(refused)), self.assertRaises(ModelError):
                decode_instruction(refused, BASE)

    def test_lane_order_masking_alias_and_independent_serialization(self):
        cases = [(0x0123456789abcdef, 0x67452301efcdab89),
                 (0x8000000000000000, 0x0000008000000000),
                 (0x0000000080000000, 0x80), (-2, 0xfffffffffeffffff),
                 (0x0000000100000002, 0x0100000002000000),
                 (0x10000000001234567, 0x67452301),
                 (0xffffffffffffedcb, 0xffffffffcbedffff), (0, 0), (MASK, MASK)]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(oracle(value), expected)
                state = PathState()
                state.registers[1] = Value('constant', value)
                state.apply(decode_instruction(word(1, 1), BASE))
                self.assertEqual(state.registers[1], Value('constant', expected))
                state.apply(decode_instruction(word(1, 1), BASE))
                self.assertEqual(state.registers[1], Value('constant', value & MASK))

    def test_zr_discard_flags_conditions_memory_and_sp(self):
        for flags in (None, (True, False, True, False)):
            state = PathState(flags=flags, memory={-16: original(29)})
            state.registers[1] = Value('constant', 0x1234)
            before = state.registers.copy()
            conditions = [state.condition(c) for c in range(14)]
            state.apply(decode_instruction(word(31, 1), BASE))
            self.assertEqual(state.registers, before)
            state.apply(decode_instruction(word(0, 31), BASE))
            self.assertEqual(state.registers[0], Value('constant', 0))
            self.assertEqual(state.registers[1:], before[1:])
            self.assertEqual(state.flags, flags)
            self.assertEqual([state.condition(c) for c in range(14)], conditions)
            self.assertEqual(state.memory, {-16: original(29)})
            self.assertEqual(state.sp, Value('stack', displacement=0))

    def test_stack_source_refuses_even_when_destination_discarded(self):
        for strict in (False, True):
            for rd in (0, 31):
                state = PathState(strict_call_state=strict)
                state.registers[1] = Value('stack', displacement=0)
                with self.assertRaises(ModelError) as caught:
                    state.apply(decode_instruction(word(rd), BASE))
                self.assertEqual(caught.exception.code, 'rev_stack_address_not_modeled')

    def test_unknown_original_and_double_reversal_never_restore_identity(self):
        for raw in (original(19), Value('unknown', 'input')):
            state = PathState()
            state.registers[19] = raw
            state.apply(decode_instruction(word(19, 19), BASE))
            state.apply(decode_instruction(word(19, 19), BASE))
            self.assertEqual(state.registers[19].kind, 'unknown')

    def test_owned_leaf_and_refused_control_have_distinct_outcomes(self):
        result = audit_current_function(*fixture((word(0, 0), RET)))
        self.assertEqual((result.verdict, result.scope, result.checked_pcs),
                         ('agreement', 'modeled_leaf_body', (BASE,)))
        result = audit_current_function(*fixture((0xfac00820, RET)))
        self.assertEqual((result.verdict, result.checked_pcs), ('unresolved', ()))

    def test_frame_and_unrestored_preserved_writes_remain_unresolved(self):
        result = call_result((*PRO, word(29, 0), CALL, *EPI))
        self.assertEqual(result.reason_codes, ('cfg_frame_transition_not_modeled',))
        result = audit_current_function(*fixture((word(19, 0), RET)))
        self.assertEqual(result.reason_codes, ('unmodeled_return_state',))

    def test_call_recovery_known_correct_wrong_and_unknown(self):
        words = (*PAIR_PRO, 0x92824680, word(19, 0), CALL, *PAIR_EPI)
        correct = call_result(words, encoding=0x04000001)
        self.assertEqual((correct.verdict, correct.scope), ('agreement', 'synchronous_call_sites'))
        wrong = call_result(words, encoding=0x04000000)
        self.assertEqual((wrong.verdict, wrong.checked_pcs), ('inconsistency', (BASE+24,)))
        self.assertTrue(any(e.observed == 'constant 0xffffffffcbedffff' for e in wrong.evidence))
        unknown = call_result((*PAIR_PRO, word(19, 19), CALL, *PAIR_EPI), encoding=0x04000000)
        self.assertEqual(unknown.reason_codes, ('unknown_recovery_value',))

    def test_possible_only_and_later_unknown_keep_unresolved_precedence(self):
        concrete = (0x92824680, word(19, 0))
        possible = call_result((*PAIR_PRO, 0x54000060, *concrete, CALL, *PAIR_EPI), encoding=0x04000000)
        self.assertEqual(possible.reason_codes, ('cfg_path_feasibility_unknown',))
        later = call_result((*PAIR_PRO, *concrete, CALL, word(19, 0), CALL, *PAIR_EPI),
                            encoding=0x04000000, limits=replace(Limits(), max_evidence_per_function=1))
        self.assertEqual(later.reason_codes, ('unknown_recovery_value',))

    def test_dead_refusal_and_work_limits_remain_unresolved(self):
        dead = audit_current_function(*fixture((0x14000002, 0x3ac10c00, word(), RET)))
        self.assertEqual((dead.verdict, dead.checked_pcs), ('unresolved', ()))
        result = audit_current_function(*fixture((word(), RET)), replace(Limits(), max_cfg_steps_per_function=0))
        self.assertEqual(result.reason_codes, ('cfg_work_limit',))

    def test_exact_v46_and_historical_import_boundaries(self):
        for model in (MODEL, 'arm64-bounded-rev16-v45', 'arm64-bounded-rev-v44'):
            value = synthetic_report(model)
            self.assertIs(validate_report(value), value)
            value['image']['cpu_subtype'] = 0x80000000
            with self.assertRaises(InputError):
                validate_report(value)
        future = synthetic_report(MODEL+'-future')
        future['image']['cpu_subtype'] = 0x80000000
        self.assertIs(validate_report(future), future)
