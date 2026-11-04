"""W UDIV arithmetic, provenance and recovery over bounded owned examples."""
from dataclasses import replace
from pathlib import Path
import unittest

from airs import ANALYSIS_MODEL_VERSION
from airs.arm64 import ModelError, Value, original
from airs.cfg import PathState, audit_current_function, decode_instruction
from airs.report import validate_report
from airs.types import InputError, Limits
from test_rbit_x_candidate import fixture, call_result, BASE, RET, PRO, EPI, PAIR_PRO, PAIR_EPI, CALL
from test_report_v32_admission_candidate import synthetic_report

MODEL = 'arm64-bounded-w-udiv-v43'


def word(rd=0, rn=1, rm=2):
    return 0x1ac00800 | (rm << 16) | (rn << 5) | rd


def oracle(a, b):
    """Independent fixed 32-step long division without host quotient arithmetic."""
    a, b = a & 0xffffffff, b & 0xffffffff
    if b == 0:
        return 0
    remainder = quotient = 0
    for bit in range(31, -1, -1):
        remainder = (remainder << 1) | ((a >> bit) & 1)
        if remainder >= b:
            remainder -= b
            quotient |= 1 << bit
    return quotient


class UDIVWTests(unittest.TestCase):
    def test_exact_decoder_controls_and_signed_neighbor(self):
        ins = decode_instruction(word(4, 5, 6), BASE)
        self.assertEqual((ins.kind, ins.rd, ins.rn, ins.rt2), ('wudiv', 4, 5, 6))
        for bit in (*range(10, 16), *range(21, 31)):
            try:
                neighbor = decode_instruction(word() ^ (1 << bit), BASE)
            except ModelError:
                continue
            self.assertNotEqual(neighbor.kind, 'wudiv')
        self.assertEqual(decode_instruction(word() | (1 << 31), BASE).kind, 'xudiv')
        self.assertEqual(decode_instruction(word() | (1 << 10), BASE).kind, 'wsdiv')

    def test_unsigned_arithmetic_low32_zero_extension_and_independent_oracle(self):
        cases = [(0, 0, 0), (19, 0, 0), (0, 9, 0), (2, 3, 0), (19, 3, 6),
                 (0xffffffff, 2, 0x7fffffff), (0x80000000, 3, 0x2aaaaaaa),
                 (-1, 0xffffffff, 1), ((1 << 40), 3, 0),
                 (0x100000013, 0x100000003, 6), (19, 0x100000000, 0),
                 (0xffffffff, 1, 0xffffffff)]
        for a, b, expected in cases:
            with self.subTest(a=a, b=b):
                self.assertEqual(oracle(a, b), expected)
                state = PathState()
                state.registers[1], state.registers[2] = Value('constant', a), Value('constant', b)
                state.apply(decode_instruction(word(), BASE))
                self.assertEqual(state.registers[0], Value('constant', expected))

    def test_aliases_zr_and_discard_use_old_operands(self):
        for rd, rn, rm, expected in [(1, 1, 2, 6), (2, 1, 2, 6), (1, 1, 1, 1),
                                     (0, 31, 2, 0), (0, 1, 31, 0), (31, 1, 2, None)]:
            state = PathState()
            state.registers[1], state.registers[2] = Value('constant', 19), Value('constant', 3)
            before = state.registers.copy()
            state.apply(decode_instruction(word(rd, rn, rm), BASE))
            if rd == 31:
                self.assertEqual(state.registers, before)
            else:
                self.assertEqual(state.registers[rd], Value('constant', expected))
        state = PathState()
        state.registers[1] = Value('constant', 0)
        state.apply(decode_instruction(word(1, 1, 1), BASE))
        self.assertEqual(state.registers[1], Value('constant', 0))

    def test_either_raw_stack_source_refuses_before_projection_or_discard(self):
        for strict in (False, True):
            for source in (1, 2):
                for rd in (0, 31):
                    state = PathState(strict_call_state=strict)
                    state.registers[1] = state.registers[2] = Value('constant', 0)
                    state.registers[source] = Value('stack', displacement=0)
                    with self.assertRaises(ModelError) as caught:
                        state.apply(decode_instruction(word(rd), BASE))
                    self.assertEqual(caught.exception.code, 'udiv_stack_address_not_modeled')

    def test_unknown_and_original_inputs_do_not_simplify(self):
        for source in (1, 2):
            for raw in (original(source), Value('unknown', 'input')):
                state = PathState()
                state.registers[1] = state.registers[2] = Value('constant', 0)
                state.registers[source] = raw
                state.apply(decode_instruction(word(), BASE))
                self.assertEqual(state.registers[0].kind, 'unknown')
        state = PathState()
        state.apply(decode_instruction(word(0, 1, 1), BASE))
        self.assertEqual(state.registers[0].kind, 'unknown')

    def test_nzcv_conditions_memory_sp_and_unrelated_registers_are_preserved(self):
        for flags in (None, (True, False, True, False), (False, True, False, True)):
            state = PathState(flags=flags, memory={-16: original(29)})
            state.registers[1], state.registers[2] = Value('constant', 19), Value('constant', 3)
            before = state.registers.copy()
            conditions = [state.condition(c) for c in range(14)]
            state.apply(decode_instruction(word(), BASE))
            self.assertEqual(state.flags, flags)
            self.assertEqual([state.condition(c) for c in range(14)], conditions)
            self.assertEqual(state.registers[1:], before[1:])
            self.assertEqual(state.memory, {-16: original(29)})
            self.assertEqual(state.sp, Value('stack', displacement=0))

    def test_owned_leaf_and_unmodeled_control_have_distinct_outcomes(self):
        result = audit_current_function(*fixture((word(0, 0, 1), RET)))
        self.assertEqual((result.verdict, result.scope, result.checked_pcs),
                         ('agreement', 'modeled_leaf_body', (BASE,)))
        refused = audit_current_function(*fixture((0x3ac10800, RET)))
        self.assertEqual((refused.verdict, refused.checked_pcs), ('unresolved', ()))

    def test_frame_and_unrestored_preserved_destination_remain_unresolved(self):
        result = call_result((*PRO, word(29, 0, 1), CALL, *EPI))
        self.assertEqual(result.reason_codes, ('cfg_frame_transition_not_modeled',))
        result = audit_current_function(*fixture((word(19, 0, 1), RET)))
        self.assertEqual(result.reason_codes, ('unmodeled_return_state',))

    def test_call_recovery_correct_wrong_and_unknown(self):
        words = (*PAIR_PRO, 0x92800000, 0xd2800041, word(19, 0, 1), CALL, *PAIR_EPI)
        correct = call_result(words, encoding=0x04000001)
        self.assertEqual((correct.verdict, correct.scope), ('agreement', 'synchronous_call_sites'))
        wrong = call_result(words, encoding=0x04000000)
        self.assertEqual((wrong.verdict, wrong.checked_pcs), ('inconsistency', (BASE + 28,)))
        self.assertTrue(any(e.observed == 'constant 0x7fffffff' for e in wrong.evidence))
        unknown = call_result((*PAIR_PRO, word(19, 19, 0), CALL, *PAIR_EPI), encoding=0x04000000)
        self.assertEqual(unknown.reason_codes, ('unknown_recovery_value',))

    def test_possible_only_and_later_unknown_keep_unresolved_precedence(self):
        concrete = (0xd2800260, 0xd2800061, word(19, 0, 1))
        possible = call_result((*PAIR_PRO, 0x54000080, *concrete, CALL, *PAIR_EPI), encoding=0x04000000)
        self.assertEqual(possible.reason_codes, ('cfg_path_feasibility_unknown',))
        later = call_result((*PAIR_PRO, *concrete, CALL, word(19, 0, 1), CALL, *PAIR_EPI),
                            encoding=0x04000000, limits=replace(Limits(), max_evidence_per_function=1))
        self.assertEqual(later.reason_codes, ('unknown_recovery_value',))

    def test_exact_v43_and_historical_import_boundaries(self):
        for model in (MODEL, 'arm64-bounded-w-sdiv-v42', 'arm64-bounded-cfi-control-v41'):
            report = synthetic_report(model)
            self.assertIs(validate_report(report), report)
            report['image']['cpu_subtype'] = 0x80000000
            with self.assertRaises(InputError):
                validate_report(report)
        future = synthetic_report(MODEL + '-future')
        future['image']['cpu_subtype'] = 0x80000000
        self.assertIs(validate_report(future), future)
