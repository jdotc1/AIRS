"""Bounded CMP EQ preserved call results paired with selected error literals."""
import unittest
from airs.swift_error_flow import recover_swift_error_flow
from test_swift_cmp_handler_regions import WORDS
from test_swift_error_flow import image, BASE


def report(words=WORDS):
    return recover_swift_error_flow(image(words), include_error_regions=True,
        validate_region_entries=True, include_structured_presentation=True)


class CmpOutcomeFirstTests(unittest.TestCase):
    def test_preserved_result_and_error_literal_form_structural_choice(self):
        call = report()['calls'][0]
        self.assertEqual(call['success_result']['status'], 'preserved_register_candidate')
        self.assertEqual(call['error_constant']['status'], 'constant_register_candidate')
        self.assertEqual(call['error_constant']['constant_bits'], '0xffffffffffffffff')
        choice = call['return_choice']
        self.assertEqual(choice['status'], 'structural_choice_candidate')
        self.assertEqual(choice['success']['kind'], 'call_result')
        self.assertEqual(choice['error']['constant_bits'], '0xffffffffffffffff')
        self.assertEqual(choice['condition']['comparison_pc'], hex(BASE+4))
        self.assertEqual(choice['condition']['test_condition'], 'eq')
        self.assertFalse(choice['runtime_value_proven'])
        self.assertFalse(choice['source_reconstruction_allowed'])
        self.assertFalse(call['error_constant']['call_return_proven'])
        self.assertEqual(call['success_constant']['status'], 'declined')

class CmpOutcomeBoundaryTests(unittest.TestCase):
    def test_error_alias_copy_does_not_destroy_success_result(self):
        call = report((0xaa1503f3, 0xf100027f, 0x54000080,
                       0xaa1303e0, 0x9400000b, 0x92800000))['calls'][0]
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
        self.assertEqual(call['return_choice']['condition']['register'], 'x19')

    def test_postcall_result_copy_roundtrip_is_retained(self):
        call = report((0xaa0003f3, 0xaa1f03e0, 0xaa1303e0,
                       0xf10002bf, 0x54000080, 0xaa1503e0,
                       0x94000009, 0x92800000))['calls'][0]
        self.assertEqual(call['success_result']['status'], 'copied_register_candidate')
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')

    def test_error_test_in_x0_cannot_preserve_call_result(self):
        call = report((0xaa1503e0, 0xf100001f, 0x54000080,
                       0xaa1503e0, 0x9400000b, 0x92800000))['calls'][0]
        self.assertEqual(call['success_result']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_tail_side_entry_withholds_both_outcomes(self):
        call = report((*WORDS, 0xd65f03c0, 0x17ffffff))['calls'][0]
        self.assertEqual(call['success_result']['reason'], 'unexpected_return_tail_entry')
        self.assertEqual(call['error_constant']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_flag_or_handler_side_entries_cannot_produce_choice(self):
        for word in (0x17fffffc, 0x17fffffd):
            with self.subTest(word=hex(word)):
                call = report((*WORDS, word))['calls'][0]
                self.assertEqual(call['return_choice']['status'], 'unresolved')
                self.assertEqual(call['success_result']['status'], 'declined')

    def test_unknown_and_ne_keep_outcomes_unresolved(self):
        for words in ((*WORDS, 0xffffffff), (WORDS[0], WORDS[1] | 1, *WORDS[2:])):
            call = report(words)['calls'][0]
            self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_literal_before_opaque_call_is_not_reused(self):
        call = report((WORDS[0], WORDS[1], 0x92800000, 0x9400000c, 0xd503201f))['calls'][0]
        self.assertEqual(call['success_result']['status'], 'preserved_register_candidate')
        self.assertEqual(call['error_constant']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_w_error_literal_preserves_zero_extension(self):
        call = report((*WORDS[:-1], 0x12800000))['calls'][0]
        self.assertEqual(call['error_constant']['constant_bits'], '0x00000000ffffffff')
        self.assertEqual(call['return_choice']['error']['constant_bits'], '0x00000000ffffffff')

    def test_wrong_return_register_withholds_choice(self):
        call = report((*WORDS, 0xd65f0000))['calls'][0]  # RET x0 is not RET x30.
        self.assertEqual(call['success_result']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_return_choice_binds_comparison_condition(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        original = report()['calls'][0]
        for key, replacement in (('comparison_pc', hex(BASE)), ('test_condition', 'ne'),
                                 ('test_kind', 'foreign')):
            call = deepcopy(original)
            call['presentation']['display_plan']['condition'][key] = replacement
            self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_success_literal_gate_and_proof_flags_remain_closed(self):
        call = report()['calls'][0]
        self.assertEqual(call['success_constant']['reason'], 'compare_outcome_recovery_not_qualified')
        for key in ('success_result', 'error_constant', 'return_choice'):
            for proof in ('runtime_value_proven', 'source_reconstruction_allowed',
                          'exclusive_path_proven', 'caller_return_type_proven'):
                self.assertFalse(call[key][proof])

class CmpOutcomeRawBindingTests(unittest.TestCase):
    def test_changed_caller_words_cannot_reuse_presentation_for_result(self):
        import struct
        from airs.swift_error_flow import _success_result, _caller_direct_edges
        value = image(WORDS); function = value.functions[0]
        call = report()['calls'][0]
        for offset, word in ((4, 0xf100029f), (8, 0x54000081), (8, 0x540000a0)):
            with self.subTest(offset=offset, word=hex(word)):
                data = bytearray(value.bytes_at(function.start, function.size))
                struct.pack_into('<I', data, offset, word)
                result = _success_result(bytes(data), function, call, _caller_direct_edges(bytes(data), function))
                self.assertEqual(result['status'], 'declined')


class CmpOutcomeDeliveryTests(unittest.TestCase):
    def test_text_retains_candidate_bits_and_false_proof(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report())
        for expected in ('structural_choice_candidate', '0xffffffffffffffff',
                         'comparison_pc', 'test_condition', 'call_result',
                         '"runtime_value_proven": false', 'Source reconstruction: disabled'):
            self.assertIn(expected, text)

    def test_cli_json_and_text_retain_structural_choice(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from airs.cli import main
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-cmp-outcomes'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'; source.write_bytes(image(WORDS).data)
            options = ['swift-error-flow', str(source), '--include-error-regions',
                       '--validate-region-entries', '--include-structured-presentation']
            for extra in ([], ['--format', 'text']):
                output = io.StringIO()
                with contextlib.redirect_stdout(output): status = main(options+extra)
                self.assertEqual(status, 0)
                if extra:
                    self.assertIn('structural_choice_candidate', output.getvalue())
                else:
                    call = json.loads(output.getvalue())['calls'][0]
                    self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
                    self.assertEqual(call['return_choice']['condition']['test_kind'], 'cmp_zero_bcond')
