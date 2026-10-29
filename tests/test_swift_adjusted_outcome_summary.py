"""Pair existing adjusted-result evidence with its recorded error literal."""
from copy import deepcopy
import unittest

from airs.swift_error_text import render_swift_error_text, _consistent_return_choice
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_literal_outcome_summary import report, LABEL as LITERAL_LABEL
from test_swift_call_result_outcome_summary import LABEL as CALL_RESULT_LABEL

LABEL = 'Recorded adjusted-result/error outcomes (structural; runtime unproven):'
OPERATION_LABEL = 'Success operation (structural; runtime unproven):'


def adjusted_report(word=0x91001400):
    return report(LAYOUTS[0][1]((word,)))


class AdjustedOutcomeSummaryTests(unittest.TestCase):
    def test_add_subtract_and_effective_shifted_amounts_across_existing_layouts(self):
        for name, layout in LAYOUTS:
            for base, sign in ((0x91000000, '+'), (0xd1000000, '-')):
                for encoded, shift, effective in ((5, 0, 5), (1, 12, 4096), (4095, 12, 16773120)):
                    word = base | ((shift == 12) << 22) | (encoded << 10)
                    with self.subTest(layout=name, sign=sign, effective=effective):
                        text = render_swift_error_text(report(layout((word,))))
                        error = '0xfffffffffffffff9' if name == 'cbz' else '0xffffffffffffffff'
                        self.assertIn(LABEL, text)
                        self.assertIn(f'success x0 call result {sign} {effective} modulo 2^64; error x0 bits {error}', text)
                        self.assertIn(OPERATION_LABEL, text)
                        for raw in ('Return choice (structural outcomes; source disabled):',
                                    'Result-path instruction:', 'Error-constant instruction:',
                                    'Source reconstruction: disabled'):
                            self.assertIn(raw, text)

    def test_copied_source_and_adjusted_register_restore_remain_visible(self):
        for name, layout in LAYOUTS:
            for operation, sign in ((0x91400674, '+'), (0xd1400674, '-')):
                words = (0xaa0003f3, 0xaa1f03e0, *layout((operation, 0xaa1403e0)))
                with self.subTest(layout=name, sign=sign):
                    text = render_swift_error_text(report(words))
                    self.assertIn(LABEL, text)
                    self.assertIn(f'success x0 call result {sign} 4096 modulo 2^64;', text)
                    self.assertIn('"adjustment_source_register": 19', text)
                    self.assertIn('"adjustment_register": 20', text)

    def test_error_word_zero_extension_and_x_width_patterns_are_distinct(self):
        for name, layout in LAYOUTS:
            for operation in (0x91001400, 0xd1001400):
                for literal, bits in ((0x12800000, '0x00000000ffffffff'),
                                      (0x92800000, '0xffffffffffffffff')):
                    words = tuple(literal if word in (0x92800000, 0x928000c0) else word
                                  for word in layout((operation,)))
                    with self.subTest(layout=name, operation=hex(operation), bits=bits):
                        text = render_swift_error_text(report(words))
                        self.assertIn(LABEL, text)
                        self.assertIn('error x0 bits ' + bits, text)

    def test_inconsistent_error_pair_withholds_new_line_but_keeps_existing_operation(self):
        original = adjusted_report()
        for field in ('choice_bits', 'outcome_bits', 'error_pc', 'width', 'integer_width',
                      'proof', 'integer_proof', 'equality', 'pattern', 'depends', 'missing', 'conflicting'):
            value = deepcopy(original); call = value['calls'][0]
            choice, error = call['return_choice'], call['error_constant']
            if field == 'choice_bits': choice['error']['constant_bits'] = '0x0000000000000001'
            elif field == 'outcome_bits': error['constant_bits'] = '0x0000000000000001'
            elif field == 'error_pc': error['error_pc'] = '0x0'
            elif field == 'width': choice['error']['bit_width'] = 64.0
            elif field == 'integer_width': error['bit_width'] = True
            elif field == 'proof': error['handler_semantics_proven'] = True
            elif field == 'integer_proof': error['runtime_value_proven'] = 0
            elif field == 'equality': choice['same_constant_bits'] = False
            elif field == 'pattern':
                choice['error']['constant_bits'] = error['constant_bits'] = '0xFFFFFFFFFFFFFFF9'
            elif field == 'depends': error['depends_on_call_result'] = True
            elif field == 'missing': del call['error_constant']
            else: call['success_constant']['status'] = 'constant_register_candidate'
            with self.subTest(field=field):
                text = render_swift_error_text(value)
                self.assertNotIn(LABEL, text)
                self.assertIn(OPERATION_LABEL, text)
                self.assertIn('Return choice (structural outcomes; source disabled):', text)
                self.assertIn('Result-path instruction:', text)

    def test_operation_descriptor_and_binding_mismatches_withhold_pair(self):
        original = adjusted_report()
        for path, replacement in (
                (('success', 'kind'), 'call_result_sub_immediate'),
                (('success', 'operation'), 'sub_immediate_modulo'),
                (('success', 'register'), 'x1'),
                (('success', 'immediate'), 6),
                (('success', 'immediate'), 5.0),
                (('success', 'immediate'), True),
                (('success', 'immediate_shift'), 12),
                (('success', 'immediate_shift'), 0.0),
                (('success', 'bit_width'), 64.0),
                (('condition', 'test_pc'), '0x0'),
                (('call_pc',), '0x0'), (('return_pc',), '0x0')):
            value = deepcopy(original); target = value['calls'][0]['return_choice']
            for part in path[:-1]: target = target[part]
            target[path[-1]] = replacement
            with self.subTest(path=path, replacement=replacement):
                self.assertNotIn(LABEL, render_swift_error_text(value))
        for flag in ('runtime_value_proven', 'source_reconstruction_allowed', 'exclusive_path_proven',
                     'caller_return_type_proven', 'call_return_proven', 'handler_semantics_proven'):
            for replacement in (True, 0):
                value = deepcopy(original); value['calls'][0]['return_choice'][flag] = replacement
                with self.subTest(flag=flag, replacement=replacement):
                    self.assertNotIn(LABEL, render_swift_error_text(value))

    def test_consistent_choice_does_not_bypass_existing_operation_tail_guards(self):
        original = adjusted_report()
        for replacement in (True, 0):
            value = deepcopy(original); call = value['calls'][0]
            call['presentation']['display_plan']['shared_epilogue']['restore_state_proven'] = replacement
            with self.subTest(restore_state=replacement):
                self.assertIsNotNone(_consistent_return_choice(call))
                text = render_swift_error_text(value)
                self.assertNotIn(OPERATION_LABEL, text)
                self.assertNotIn(LABEL, text)

    def test_blocked_unresolved_and_malformed_tail_withhold_pair(self):
        original = adjusted_report()
        for change in ('blocked', 'unresolved', 'empty_tail', 'malformed_tail'):
            value = deepcopy(original); call = value['calls'][0]
            if change == 'empty_tail': call['error_region']['shared_epilogue']['instructions'] = []
            elif change == 'malformed_tail': call['error_region']['shared_epilogue']['instructions'] = [None]
            else: call['presentation']['status'] = change
            with self.subTest(change=change):
                text = render_swift_error_text(value)
                self.assertNotIn(LABEL, text)
                self.assertIn('Result-path instruction:', text)

    def test_literal_preserved_and_copied_pairs_keep_separate_labels(self):
        from test_swift_preserved_result_binding import variants
        text = render_swift_error_text(report())
        self.assertIn(LITERAL_LABEL, text)
        self.assertNotIn(LABEL, text)
        for name, words, _ in variants():
            with self.subTest(layout=name):
                text = render_swift_error_text(report(words))
                self.assertIn(CALL_RESULT_LABEL, text)
                self.assertNotIn(LABEL, text)

    def test_output_budget_and_report_immutability_are_preserved(self):
        from airs.types import InputError
        value = adjusted_report(); original = deepcopy(value)
        text = render_swift_error_text(value); count = len(text.encode('ascii'))
        self.assertIn(LABEL, text)
        self.assertEqual(value, original)
        self.assertEqual(render_swift_error_text(value, maximum_bytes=count), text)
        with self.assertRaises(InputError) as error:
            render_swift_error_text(value, maximum_bytes=count - 1)
        self.assertEqual(error.exception.code, 'generated_report_size_limit')

    def test_cli_pair_and_bypass_withholding_preserve_json_and_raw_evidence(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from airs.cli import main
        from test_swift_error_flow import image
        from test_swift_preserved_result_binding import branch_to_postcall
        add = LAYOUTS[0][1]((0x91001400,))
        subtract = (0xaa0003f3, *LAYOUTS[0][1]((0xd1400674, 0xaa1403e0)))
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            for name, words, expected in (('add', add, True), ('subtract', subtract, True),
                                           ('bypass', branch_to_postcall(subtract, 8), False)):
                source = Path(folder) / (name + '.macho'); source.write_bytes(image(words).data)
                for format in ('text', 'json'):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        status = main(['swift-error-flow', str(source), '--include-error-regions',
                            '--validate-region-entries', '--include-structured-presentation', '--format', format])
                    self.assertEqual(status, 0)
                    with self.subTest(name=name, format=format):
                        if format == 'json':
                            self.assertEqual(json.loads(output.getvalue())['calls'], report(words)['calls'])
                            self.assertNotIn(LABEL, output.getvalue())
                        else:
                            self.assertEqual(LABEL in output.getvalue(), expected)
                            self.assertIn('Return choice (structural outcomes; source disabled):', output.getvalue())
                            self.assertIn('Source reconstruction: disabled', output.getvalue())
