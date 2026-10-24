"""Bounded W signed division with owned literals and independent expectations."""
from dataclasses import replace
import json
from pathlib import Path
import unittest

from airs import ANALYSIS_MODEL_VERSION
from airs.arm64 import ModelError, Value, original
from airs.cfg import PathState, audit_current_function, decode_instruction
from airs.report import validate_report
from airs.types import InputError
from test_rbit_x_candidate import fixture, call_result, BASE, RET, PRO, EPI, PAIR_PRO, PAIR_EPI, CALL
from test_report_v32_admission_candidate import synthetic_report

MODEL = 'arm64-bounded-w-sdiv-v42'


def word(rd=0, rn=1, rm=2):
    return 0x1ac00c00 | (rm << 16) | (rn << 5) | rd


def oracle(a, b):
    """Independent 32-step signed long division, without host division."""
    a, b = a & 0xffffffff, b & 0xffffffff
    a = a - (1 << 32) if a & (1 << 31) else a
    b = b - (1 << 32) if b & (1 << 31) else b
    if b == 0:
        return 0
    remainder = quotient = 0
    for bit in range(31, -1, -1):
        remainder = (remainder << 1) | ((abs(a) >> bit) & 1)
        if remainder >= abs(b):
            remainder -= abs(b)
            quotient |= 1 << bit
    return (-quotient if (a < 0) != (b < 0) else quotient) & 0xffffffff


class SDIVWTests(unittest.TestCase):
    def test_decode_exact_form_and_reserved_neighbors(self):
        ins = decode_instruction(word(4, 5, 6), BASE)
        self.assertEqual((ins.kind, ins.rd, ins.rn, ins.rt2), ('wsdiv', 4, 5, 6))
        for bit in (*range(10, 16), *range(21, 31)):
            try:
                neighbor = decode_instruction(word() ^ (1 << bit), BASE)
            except ModelError:
                continue
            self.assertNotEqual(neighbor.kind, 'wsdiv')
        self.assertEqual(decode_instruction(word() | (1 << 31), BASE).kind, 'xsdiv')
        with self.assertRaises(ModelError):
            decode_instruction(0x1ac20820, BASE)  # W UDIV is still refused

    def test_signed_edges_low32_masking_zero_extension_and_oracle(self):
        cases = [(7, 3, 2), (-7, 3, 0xfffffffe), (7, -3, 0xfffffffe),
                 (-7, -3, 2), (19, 0, 0), (-19, 0, 0), (-2, 3, 0),
                 (0x80000000, -1, 0x80000000), (0x80000000, 1, 0x80000000),
                 (0x7fffffff, -1, 0x80000001), ((1 << 40) + 19, 3, 6),
                 (0x100000013, 0x1fffffffd, 0xfffffffa),
                 (0x80000000, 3, 0xd5555556)]
        for a, b, expected in cases:
            with self.subTest(a=a, b=b):
                self.assertEqual(oracle(a, b), expected)
                state = PathState()
                state.registers[1], state.registers[2] = Value('constant', a), Value('constant', b)
                state.apply(decode_instruction(word(), BASE))
                self.assertEqual(state.registers[0], Value('constant', expected))

    def test_aliases_and_zero_registers_capture_old_operands(self):
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

    def test_raw_stack_sources_refuse_before_projection_zero_and_discard(self):
        for strict in (False, True):
            for source in (1, 2):
                for rd in (0, 31):
                    state = PathState(strict_call_state=strict)
                    state.registers[1] = state.registers[2] = Value('constant', 0)
                    state.registers[source] = Value('stack', displacement=0)
                    with self.assertRaises(ModelError) as caught:
                        state.apply(decode_instruction(word(rd), BASE))
                    self.assertEqual(caught.exception.code, 'sdiv_stack_address_not_modeled')

    def test_unknown_original_flags_memory_and_sp_remain_conservative(self):
        for source in (1, 2):
            for raw in (original(source), Value('unknown', 'input')):
                state = PathState(flags=(True, False, True, False), memory={-16: original(29)})
                state.registers[1] = state.registers[2] = Value('constant', 0)
                state.registers[source] = raw
                state.apply(decode_instruction(word(), BASE))
                self.assertEqual(state.registers[0].kind, 'unknown')
                self.assertEqual(state.flags, (True, False, True, False))
                self.assertEqual(state.memory, {-16: original(29)})
                self.assertEqual(state.sp, Value('stack', displacement=0))

    def test_owned_leaf_and_unsigned_neighbor_keep_distinct_outcomes(self):
        result = audit_current_function(*fixture((word(0, 0, 1), RET)))
        self.assertEqual((result.verdict, result.scope, result.checked_pcs),
                         ('agreement', 'modeled_leaf_body', (BASE,)))
        refused = audit_current_function(*fixture((0x1ac10800, RET)))
        self.assertEqual((refused.verdict, refused.checked_pcs), ('unresolved', ()))

    def test_frame_destination_and_unrestored_preserved_register_refuse(self):
        result = call_result((*PRO, word(29, 0, 1), CALL, *EPI))
        self.assertEqual(result.reason_codes, ('cfg_frame_transition_not_modeled',))
        result = audit_current_function(*fixture((word(19, 0, 1), RET)))
        self.assertEqual((result.verdict, result.reason_codes), ('unresolved', ('unmodeled_return_state',)))

    def test_owned_call_recovery_correct_wrong_and_unknown(self):
        words = (*PAIR_PRO, 0x928000c0, 0xd2800061, word(19, 0, 1), CALL, *PAIR_EPI)
        correct = call_result(words, encoding=0x04000001)
        self.assertEqual((correct.verdict, correct.scope), ('agreement', 'synchronous_call_sites'))
        wrong = call_result(words, encoding=0x04000000)
        self.assertEqual((wrong.verdict, wrong.checked_pcs), ('inconsistency', (BASE + 28,)))
        self.assertTrue(any(e.observed == 'constant 0xfffffffe' for e in wrong.evidence))
        unknown = call_result((*PAIR_PRO, word(19, 19, 0), CALL, *PAIR_EPI), encoding=0x04000000)
        self.assertEqual(unknown.reason_codes, ('unknown_recovery_value',))

    def test_v42_model_and_strict_import_boundary(self):
        self.assertEqual(ANALYSIS_MODEL_VERSION, MODEL)
        self.assertIsNotNone(validate_report(synthetic_report(MODEL)))
        for model in (MODEL, 'arm64-bounded-cfi-control-v41'):
            value = synthetic_report(model)
            value['image']['cpu_subtype'] = 0x80000000
            with self.assertRaises(InputError):
                validate_report(value)
        future = synthetic_report(MODEL + '-future')
        future['image']['cpu_subtype'] = 0x80000000
        self.assertIs(validate_report(future), future)


    def test_possible_only_and_later_unknown_preserve_unresolved_precedence(self):
        from airs.types import Limits
        concrete = (0xd2800260, 0xd2800061, word(19, 0, 1))
        possible = call_result((*PAIR_PRO, 0x54000080, *concrete, CALL, *PAIR_EPI), encoding=0x04000000)
        self.assertEqual(possible.reason_codes, ('cfg_path_feasibility_unknown',))
        later = call_result((*PAIR_PRO, *concrete, CALL, word(19, 0, 1), CALL, *PAIR_EPI),
                            encoding=0x04000000, limits=replace(Limits(), max_evidence_per_function=1))
        self.assertEqual(later.reason_codes, ('unknown_recovery_value',))

    def test_emitted_owned_call_fixture_round_trip(self):
        from unittest.mock import patch
        from airs.engine import audit_path
        from airs.report import dumps, load_report
        from airs.types import UnwindEntry, UnwindTable
        import tempfile
        words = (*PAIR_PRO, 0x928000c0, 0xd2800061, word(19, 0, 1), CALL, *PAIR_EPI)
        image, function, entry = fixture(words, 0x04000000, with_callee=True)
        image = replace(image, container_sha256='1'*64, slice_sha256='2'*64,
                        functions=(replace(function, name='owned_w_sdiv_call'), image.functions[1]))
        sink = image.functions[1]
        table = UnwindTable((entry, UnwindEntry(sink.start, sink.end, 0x02000000, 0)))
        output = Path(__file__).resolve().parents[1] / 'local-evidence/w-sdiv-v42'
        with tempfile.TemporaryDirectory(dir=output) as directory:
            path = Path(directory) / 'owned.bin'
            path.write_bytes(image.data)
            with patch('airs.engine.parse_macho', return_value=image), patch('airs.engine.parse_compact_unwind', return_value=table):
                report = audit_path(path)
        self.assertEqual(report['generator']['analysis_model_version'], MODEL)
        self.assertEqual(report['summary']['function_count'], 2)
        self.assertEqual(report['findings'][0]['verdict'], 'inconsistency')
        self.assertEqual(report['findings'][0]['checked_pcs'], ['0x101c'])
        target = output / 'w-sdiv-v42.json'
        target.write_text(dumps(report), encoding='utf-8')
        self.assertEqual(load_report(target), report)
