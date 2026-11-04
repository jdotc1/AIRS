"""Concise recorded literal pairs retain width, path labels and proof limits."""
from copy import deepcopy
import unittest

from airs.swift_error_flow import recover_swift_error_flow
from airs.swift_error_text import render_swift_error_text
from test_swift_error_flow import image
from test_swift_shared_epilogue import WORDS

LABEL = 'Recorded literal outcomes (structural; runtime unproven):'


def report(words=WORDS):
    return recover_swift_error_flow(image(words), include_error_regions=True,
        validate_region_entries=True, include_structured_presentation=True)


class LiteralOutcomeSummaryTests(unittest.TestCase):
    def test_existing_literal_layouts_keep_separate_success_and_error_bits(self):
        from test_swift_literal_call_binding import literal_variants
        for name, words, paths in literal_variants():
            value = report(words); text = render_swift_error_text(value)
            with self.subTest(layout=name):
                if 'success' not in paths:
                    self.assertNotIn(LABEL, text)
                    continue
                expected_error = '0xfffffffffffffff9' if name == 'cbz' else '0xffffffffffffffff'
                self.assertIn(LABEL, text)
                self.assertIn('success x0 bits 0x000000000000002a; error x0 bits ' + expected_error, text)
                for raw in ('Return choice (structural outcomes; source disabled):',
                            'Constant-path instruction:', 'Error-constant instruction:',
                            'Source reconstruction: disabled'):
                    self.assertIn(raw, text)

    def test_equal_patterns_and_word_zero_extension_are_not_collapsed(self):
        from test_swift_owned_word_outcomes import WORDS as packed, WIDTH
        cases = ((WORDS[:3] + (0xd2800000,) + WORDS[4:],
                  'success x0 bits 0x0000000000000000; error x0 bits 0x0000000000000000'),
                 (WIDTH, 'success x0 bits 0x00000000ffffffff; error x0 bits 0xffffffffffffffff'),
                 (packed, 'success x0 bits 0x0000000089abcdef; error x0 bits 0x0000000012345678'))
        for words, expected in cases:
            with self.subTest(expected=expected):
                text = render_swift_error_text(report(words))
                self.assertIn(LABEL, text)
                self.assertIn(expected, text)

    def test_mismatched_choice_or_underlying_binding_withholds_only_summary(self):
        original = report()
        for field in ('bits', 'width', 'call_pc', 'return_pc', 'condition', 'outcome_pc',
                      'outcome_bits', 'proof', 'integer_proof', 'equality_type'):
            value = deepcopy(original); call = value['calls'][0]; choice = call['return_choice']
            if field == 'bits': choice['success']['constant_bits'] = '0x0000000000000001'
            elif field == 'width': choice['success']['bit_width'] = 64.0
            elif field in ('call_pc', 'return_pc'): choice[field] = '0x0'
            elif field == 'condition': choice['condition']['register'] = 'x20'
            elif field == 'outcome_pc': call['success_constant']['success_pc'] = '0x0'
            elif field == 'outcome_bits': call['error_constant']['constant_bits'] = '0x0000000000000001'
            elif field == 'proof': choice['runtime_value_proven'] = True
            elif field == 'integer_proof': choice['runtime_value_proven'] = 0
            else: choice['same_constant_bits'] = 0
            with self.subTest(field=field):
                text = render_swift_error_text(value)
                self.assertNotIn(LABEL, text)
                self.assertIn('Return choice (structural outcomes; source disabled):', text)
                self.assertIn('Constant-path instruction:', text)

    def test_missing_conflicting_blocked_and_nonliteral_outcomes_have_no_literal_line(self):
        original = report()
        for field in ('missing', 'conflicting', 'blocked', 'unresolved', 'malformed_tail'):
            value = deepcopy(original); call = value['calls'][0]
            if field == 'missing': del call['error_constant']
            elif field == 'conflicting': call['success_result']['status'] = 'preserved_register_candidate'
            elif field == 'malformed_tail': call['error_region']['shared_epilogue']['instructions'] = []
            else: call['presentation']['status'] = field
            with self.subTest(field=field):
                self.assertNotIn(LABEL, render_swift_error_text(value))
        from test_swift_arithmetic_call_binding import LAYOUTS
        for word in (0xd503201f, 0x91001400, 0xd1001400):
            for name, layout in LAYOUTS:
                with self.subTest(layout=name, word=hex(word)):
                    self.assertNotIn(LABEL, render_swift_error_text(report(layout((word,)))))

    def test_summary_obeys_existing_output_byte_limit(self):
        from airs.types import InputError
        value = report(); text = render_swift_error_text(value)
        self.assertIn(LABEL, text)
        with self.assertRaises(InputError):
            render_swift_error_text(value, maximum_bytes=len(text.encode('utf-8')) - 1)

    def test_cli_text_summarizes_literals_and_withholds_bypassed_choice(self):
        import contextlib, io
        from pathlib import Path
        from fixture_storage import temporary_directory
        from airs.cli import main
        from test_swift_preserved_result_binding import branch_to_postcall
        bypass = branch_to_postcall((0xaa1503f6, (WORDS[0] & ~31) | 22, *WORDS[1:]), 8)
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            for name, words, expected in (('literal', WORDS, True), ('bypass', bypass, False)):
                source = Path(folder) / (name + '.macho'); source.write_bytes(image(words).data)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    status = main(['swift-error-flow', str(source), '--include-error-regions',
                        '--validate-region-entries', '--include-structured-presentation', '--format', 'text'])
                self.assertEqual(status, 0)
                self.assertEqual(LABEL in output.getvalue(), expected)
                self.assertIn('Source reconstruction: disabled', output.getvalue())
