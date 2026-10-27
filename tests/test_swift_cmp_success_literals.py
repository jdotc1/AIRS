"""Bounded X move-wide success literals before a qualified CMP EQ test."""
import unittest
from airs.swift_error_flow import recover_swift_error_flow
from test_swift_error_flow import image

# Success x0=42; CMP x21; EQ -> +28 RET; error sets x0=-1.
WORDS = (0xd2800540, 0xf10002bf, 0x54000080, 0xaa1503e0, 0x9400000b, 0x92800000)


def report(words=WORDS):
    return recover_swift_error_flow(image(words), include_error_regions=True,
        validate_region_entries=True, include_structured_presentation=True)


class CmpSuccessLiteralFirstTests(unittest.TestCase):
    def test_success_literal_and_error_literal_form_bound_choice(self):
        call = report()['calls'][0]
        self.assertEqual(call['success_constant']['status'], 'constant_register_candidate')
        self.assertEqual(call['success_constant']['constant_bits'], '0x000000000000002a')
        self.assertEqual(call['error_constant']['constant_bits'], '0xffffffffffffffff')
        choice = call['return_choice']
        self.assertEqual(choice['status'], 'structural_choice_candidate')
        self.assertEqual(choice['success']['kind'], 'constant_bits')
        self.assertFalse(choice['same_constant_bits'])
        self.assertFalse(choice['source_reconstruction_allowed'])
        self.assertFalse(choice['runtime_value_proven'])

class CmpSuccessLiteralBoundaryTests(unittest.TestCase):
    def test_movn_and_copied_seed_recover_exact_bits(self):
        for words, bits in (((0x92800000, *WORDS[1:]), '0xffffffffffffffff'),
            ((0xd2800553, 0xaa1303e0, *WORDS[1:], 0xd65f03c0), '0x000000000000002a')):
            with self.subTest(bits=bits):
                call = report(words)['calls'][0]
                self.assertEqual(call['success_constant']['constant_bits'], bits)
                self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')

    def test_unknown_copy_clobbers_known_success_literal(self):
        call = report((WORDS[0], 0xaa1403e0, *WORDS[1:], 0xd65f03c0))['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertEqual(call['success_constant']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_seed_clobbering_only_error_alias_declines_edge(self):
        call = report((0xd2800555, *WORDS[1:]))['calls'][0]
        self.assertEqual(call['status'], 'declined')
        self.assertEqual(call['reason'], 'error_value_clobbered')

    def test_literal_prefix_does_not_widen_cbz_or_cbnz(self):
        for test in (0xb4000095, 0xb5000095):
            call = report((WORDS[0], test, *WORDS[3:]))['calls'][0]
            self.assertEqual(call['status'], 'declined')
            self.assertEqual(call['reason'], 'literal_prefix_requires_compare_test')

    def test_w_seed_prefix_records_zero_extended_bits(self):
        for word, expected in ((0x52800540, '0x000000000000002a'), (0x12800000, '0x00000000ffffffff')):
            call = report((word, *WORDS[1:]))['calls'][0]
            self.assertEqual(call['success_constant']['constant_bits'], expected)

    def test_success_tail_side_entry_withholds_literal_and_choice(self):
        # Tail starts +28; branch at +32 targets it.
        call = report((*WORDS, 0xd65f03c0, 0x17ffffff))['calls'][0]
        self.assertEqual(call['success_constant']['reason'], 'unexpected_return_tail_entry')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_flag_entry_or_unknown_words_withhold_success_literal(self):
        for word in (0x17fffffa, 0xffffffff):  # +28 -> prefix +4, or unknown.
            call = report((*WORDS, word))['calls'][0]
            self.assertEqual(call['success_constant']['status'], 'declined')
            self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_ne_and_shared_cmp_layouts_stay_unqualified(self):
        call = report((WORDS[0], WORDS[1], WORDS[2] | 1, *WORDS[3:]))['calls'][0]
        self.assertEqual(call['success_constant']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_no_seed_does_not_create_a_success_literal(self):
        call = report(WORDS[1:])['calls'][0]
        self.assertEqual(call['success_constant']['reason'], 'success_x0_constant_not_known')
        self.assertEqual(call['success_result']['status'], 'preserved_register_candidate')
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')

    def test_eight_word_prefix_and_one_word_over_boundary(self):
        exact = report((*(0xd503201f,)*5, *WORDS))['calls'][0]
        self.assertEqual(exact['success_constant']['constant_bits'], '0x000000000000002a')
        over = report((*(0xd503201f,)*6, *WORDS))['calls'][0]
        self.assertEqual(over['status'], 'declined')

    def test_return_choice_binds_literal_tail_and_proof_flags(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        original = report()['calls'][0]
        for key, value in (('return_pc', '0x0'), ('runtime_value_proven', True),
                           ('call_pc', '0x0'), ('return_tail_layout', 'shared_epilogue')):
            call = deepcopy(original);call['success_constant'][key] = value
            self.assertEqual(_return_choice(call)['status'], 'unresolved')

class CmpSuccessLiteralBindingTests(unittest.TestCase):
    def test_stale_raw_cmp_branch_and_prefix_words_are_refused(self):
        import struct
        from airs.swift_error_flow import _path_constant, _caller_direct_edges
        value = image(WORDS); function = value.functions[0]
        call = report()['calls'][0]
        for offset, word in ((4, 0xf2800540),
                             (8, 0xf100029f), (12, 0x54000081), (12, 0x540000a0)):
            with self.subTest(offset=offset, word=hex(word)):
                data = bytearray(value.bytes_at(function.start, function.size))
                struct.pack_into('<I', data, offset, word)
                result = _path_constant(bytes(data), function, call,
                    scan=_caller_direct_edges(bytes(data), function))
                self.assertEqual(result['status'], 'declined')

    def test_error_literal_requires_exact_success_tail_binding(self):
        from copy import deepcopy
        from airs.swift_error_flow import _path_constant
        value = image(WORDS); function = value.functions[0]
        original = report()['calls'][0]
        for key, replacement in (('call_pc', '0x0'), ('return_pc', '0x0'),
                                  ('runtime_value_proven', True), ('instructions', [])):
            call = deepcopy(original); call['success_constant'][key] = replacement
            result = _path_constant(value.bytes_at(function.start, function.size), function, call, error=True)
            self.assertEqual(result['status'], 'declined')

    def test_tail_conflict_totals_stay_exact_when_details_are_capped(self):
        branches = tuple(0x14000000 | ((-1-i) & 0x3ffffff) for i in range(20))
        call = report((*WORDS, 0xd65f03c0, *branches))['calls'][0]
        result = call['success_constant']
        self.assertEqual(result['unexpected_tail_entry_count'], 20)
        self.assertEqual(len(result['unexpected_tail_entries']), 16)
        self.assertFalse(result['tail_entry_details_complete'])

    def test_void_callee_can_have_explicit_literal_bits_without_result_inference(self):
        value = recover_swift_error_flow(image(WORDS, symbol='_$s4Demo5parseyyKF'),
            include_error_regions=True, validate_region_entries=True,
            include_structured_presentation=True)['calls'][0]
        self.assertEqual(value['success_result']['status'], 'declined')
        self.assertEqual(value['return_choice']['success']['kind'], 'constant_bits')
        self.assertFalse(value['return_choice']['caller_return_type_proven'])


class CmpSuccessLiteralDeliveryTests(unittest.TestCase):
    def test_text_shows_both_literals_and_scoped_choice(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report())
        for expected in ('0x000000000000002a', '0xffffffffffffffff', 'structural_choice_candidate',
                         'comparison_pc', 'Source reconstruction: disabled'):
            self.assertIn(expected, text)

    def test_cli_json_retains_literal_choice(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from airs.cli import main
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-cmp-success-literals'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'; source.write_bytes(image(WORDS).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            call = json.loads(output.getvalue())['calls'][0]
            self.assertEqual(call['return_choice']['success']['constant_bits'], '0x000000000000002a')
            self.assertFalse(call['return_choice']['same_constant_bits'])

class CmpSuccessLiteralAdditionalTests(unittest.TestCase):
    def test_saved_error_alias_survives_seed_overwriting_x21(self):
        call = report((0xaa1503f3, 0xd2800555, 0xaa1503e0,
                       0xf100027f, 0x54000080, 0xaa1303e0,
                       0x94000009, 0x92800000))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x000000000000002a')
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')

    def test_tail_budget_eight_and_nine_words(self):
        exact = report((*WORDS, *(0xd503201f,)*7, 0xd65f03c0))['calls'][0]
        self.assertEqual(exact['success_constant']['status'], 'constant_register_candidate')
        over = report((*WORDS, *(0xd503201f,)*8, 0xd65f03c0))['calls'][0]
        self.assertEqual(over['success_constant']['status'], 'declined')
        self.assertEqual(over['return_choice']['status'], 'unresolved')

    def test_partial_caller_declines_and_screened_shared_layout_qualifies(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        value = recover_swift_error_flow(image(WORDS),
            limits=replace(DEFAULT_LIMITS, max_instructions_per_function=7),
            include_error_regions=True, validate_region_entries=True,
            include_structured_presentation=True)['calls'][0]
        self.assertEqual(value['success_constant']['status'], 'declined')
        shared = report((WORDS[0], WORDS[1], 0x540000a0,
            0xaa1503e0, 0x9400000b, 0x92800000, 0x14000002,
            0xd2800000, 0xd65f03c0))['calls'][0]
        self.assertEqual(shared['success_constant']['constant_bits'], '0x0000000000000000')
        self.assertEqual(shared['return_choice']['status'], 'structural_choice_candidate')

class CmpSuccessLiteralFinalBindingTests(unittest.TestCase):
    def test_stale_success_entry_cannot_produce_misbound_literal(self):
        from airs.swift_error_flow import _path_constant, _caller_direct_edges
        value = image(WORDS); function = value.functions[0]
        data = value.bytes_at(function.start, function.size)
        call = report()['calls'][0]; call['success_pc'] = '0x0'
        result = _path_constant(data, function, call, scan=_caller_direct_edges(data, function))
        self.assertEqual(result['status'], 'declined')

    def test_conflicted_tail_retains_inspected_word_evidence(self):
        from airs.swift_error_text import render_swift_error_text
        value = report((*WORDS, 0xd65f03c0, 0x17ffffff))
        result = value['calls'][0]['success_constant']
        self.assertTrue(any(word.get('phase') == 'return_tail' and word['word'] == '0xd65f03c0'
                            for word in result['instructions']))
        self.assertIn('return_tail', render_swift_error_text(value))

class CmpSuccessLiteralPhaseTests(unittest.TestCase):
    def test_prebranch_literal_is_postcall_evidence_with_one_bound_tail(self):
        call = report()['calls'][0]
        words = call['success_constant']['instructions']
        self.assertEqual([word['phase'] for word in words], ['post_call']*3 + ['return_tail'])
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
        self.assertEqual(call['return_choice']['success']['constant_bits'], '0x000000000000002a')
