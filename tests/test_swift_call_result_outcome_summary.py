"""Paired call-result/error display preserves recorded distinctions and limits."""
from copy import deepcopy
import unittest

from airs.swift_error_text import render_swift_error_text
from test_swift_literal_outcome_summary import report, LABEL as LITERAL_LABEL
from test_swift_preserved_result_binding import variants, DIRECT, DIRECT_EQ, SAVE, CLEAR, RESTORE

LABEL = 'Recorded call-result/error outcomes (structural; runtime unproven):'


class CallResultOutcomeSummaryTests(unittest.TestCase):
    def test_preserved_and_copied_shared_and_success_entry_results_keep_distinction(self):
        for name, words, status in variants():
            value = report(words)
            with self.subTest(layout=name):
                text = render_swift_error_text(value)
                kind = 'preserved' if status == 'preserved_register_candidate' else 'copied'
                bits = '0xfffffffffffffff9' if name in ('cbz', 'cbz_copy') else '0xffffffffffffffff'
                self.assertIn(LABEL, text)
                self.assertIn('success x0 ' + kind + ' call-result candidate; error x0 bits ' + bits, text)
                self.assertNotIn(LITERAL_LABEL, text)
                self.assertNotIn('Success operation (structural; runtime unproven):', text)
                for raw in ('Return choice (structural outcomes; source disabled):',
                            'Success result (selected-path register evidence only):',
                            'Error constant (selected-path bits; call return unproven):',
                            'Result-path instruction:', 'Error-constant instruction:',
                            'Source reconstruction: disabled'):
                    self.assertIn(raw, text)

    def test_word_zero_extension_and_x_width_error_literals_remain_distinct(self):
        for words in (DIRECT, DIRECT_EQ):
            for prefix in ((), (SAVE, CLEAR, RESTORE)):
                for word, bits in ((0x12800000, '0x00000000ffffffff'),
                                   (0x92800000, '0xffffffffffffffff')):
                    value = report(prefix + tuple(word if item == 0x92800000 else item for item in words))
                    with self.subTest(prefix=prefix, word=hex(word), compare=words == DIRECT_EQ):
                        text = render_swift_error_text(value)
                        self.assertIn(LABEL, text)
                        self.assertIn('error x0 bits ' + bits, text)

    def test_mismatched_choice_or_underlying_outcome_withholds_only_summary(self):
        for name, words, _ in variants():
            original = report(words)
            mutations = (
                ('return_choice', ('success', 'candidate_status'), 'unresolved'),
                ('return_choice', ('success', 'register'), 'x1'),
                ('return_choice', ('error', 'constant_bits'), '0x0000000000000001'),
                ('return_choice', ('error', 'bit_width'), 64.0),
                ('return_choice', ('condition', 'test_pc'), '0x0'),
                ('return_choice', ('call_pc',), '0x0'),
                ('return_choice', ('return_pc',), '0x0'),
                ('success_result', ('status',), 'copied_register_candidate' if not name.endswith('_copy') else 'preserved_register_candidate'),
                ('success_result', ('register',), 'x1'),
                ('success_result', ('call_pc',), '0x0'),
                ('success_result', ('success_pc',), '0x0'),
                ('success_result', ('return_pc',), '0x0'),
                ('error_constant', ('error_pc',), '0x0'),
                ('error_constant', ('constant_bits',), '0x0000000000000001'),
                ('error_constant', ('bit_width',), 64.0),
                ('callee', ('result',), 'Swift.UInt'),
            )
            for section, path, replacement in mutations:
                value = deepcopy(original); target = value['calls'][0][section]
                for part in path[:-1]: target = target[part]
                target[path[-1]] = replacement
                with self.subTest(layout=name, section=section, path=path):
                    text = render_swift_error_text(value)
                    self.assertNotIn(LABEL, text)
                    self.assertIn('Return choice (structural outcomes; source disabled):', text)
                    self.assertIn('Result-path instruction:', text)
                    self.assertIn('Error-constant instruction:', text)

    def test_proof_flags_equality_and_error_patterns_fail_closed(self):
        original = report(DIRECT)
        flags = ('source_reconstruction_allowed', 'runtime_value_proven', 'exclusive_path_proven',
                 'caller_return_type_proven', 'call_return_proven', 'handler_semantics_proven')
        for section in ('return_choice', 'success_result', 'error_constant'):
            for flag in (flags[:4] if section == 'success_result' else flags):
                for replacement in (True, 0):
                    value = deepcopy(original); value['calls'][0][section][flag] = replacement
                    with self.subTest(section=section, flag=flag, value=replacement):
                        self.assertNotIn(LABEL, render_swift_error_text(value))
        for equality in (False, True, 0, ''):
            value = deepcopy(original); value['calls'][0]['return_choice']['same_constant_bits'] = equality
            with self.subTest(equality=equality):
                self.assertNotIn(LABEL, render_swift_error_text(value))
        for bits in ('0xffff', '0xFFFFFFFFFFFFFFFF', 0, '\x1b[2J'):
            value = deepcopy(original); call = value['calls'][0]
            call['return_choice']['error']['constant_bits'] = bits
            call['error_constant']['constant_bits'] = bits
            with self.subTest(bits=bits):
                text = render_swift_error_text(value)
                self.assertNotIn(LABEL, text)
                self.assertNotIn('\x1b', text)

    def test_missing_conflicting_blocked_and_malformed_outcomes_have_no_line(self):
        _, words, _ = next(variants())
        original = report(words)
        for change in ('missing', 'conflicting', 'blocked', 'unresolved', 'empty_tail', 'malformed_tail'):
            value = deepcopy(original); call = value['calls'][0]
            if change == 'missing': del call['error_constant']
            elif change == 'conflicting': call['success_constant']['status'] = 'constant_register_candidate'
            elif change == 'empty_tail': call['error_region']['shared_epilogue']['instructions'] = []
            elif change == 'malformed_tail': call['error_region']['shared_epilogue']['instructions'] = [None]
            else: call['presentation']['status'] = change
            with self.subTest(change=change):
                text = render_swift_error_text(value)
                self.assertNotIn(LABEL, text)
                self.assertIn('Return choice (structural outcomes; source disabled):', text)

    def test_literals_and_adjusted_results_retain_their_own_summaries(self):
        from test_swift_arithmetic_call_binding import LAYOUTS
        text = render_swift_error_text(report())
        self.assertIn(LITERAL_LABEL, text)
        self.assertNotIn(LABEL, text)
        for name, layout in LAYOUTS:
            for word, operation in ((0x91001400, '+'), (0xd1001400, '-')):
                with self.subTest(layout=name, operation=operation):
                    text = render_swift_error_text(report(layout((word,))))
                    self.assertIn('call result ' + operation + ' 5 modulo 2^64', text)
                    self.assertNotIn(LABEL, text)
                    self.assertNotIn(LITERAL_LABEL, text)

    def test_summary_obeys_byte_limit_and_does_not_mutate_report(self):
        from airs.types import InputError
        value = report(DIRECT); original = deepcopy(value)
        text = render_swift_error_text(value); count = len(text.encode('ascii'))
        self.assertIn(LABEL, text)
        self.assertEqual(value, original)
        self.assertEqual(render_swift_error_text(value, maximum_bytes=count), text)
        with self.assertRaises(InputError) as error:
            render_swift_error_text(value, maximum_bytes=count - 1)
        self.assertEqual(error.exception.code, 'generated_report_size_limit')

    def test_cli_summarizes_results_and_withholds_bypassed_choice(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from airs.cli import main
        from test_swift_error_flow import image
        from test_swift_preserved_result_binding import branch_to_postcall
        copied = (SAVE, CLEAR, RESTORE, *DIRECT)
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            for name, words, expected in (('preserved', DIRECT, True), ('copied', copied, True),
                                           ('bypass', branch_to_postcall(copied, 8), False)):
                source = Path(folder) / (name + '.macho'); source.write_bytes(image(words).data)
                for format in ('text', 'json'):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        status = main(['swift-error-flow', str(source), '--include-error-regions',
                            '--validate-region-entries', '--include-structured-presentation', '--format', format])
                    self.assertEqual(status, 0)
                    with self.subTest(name=name, format=format):
                        if format == 'json':
                            call = json.loads(output.getvalue())['calls'][0]
                            self.assertEqual(call['return_choice']['status'] == 'structural_choice_candidate', expected)
                            self.assertNotIn(LABEL, output.getvalue())
                        else:
                            self.assertEqual(LABEL in output.getvalue(), expected)
                            self.assertIn('Success result (selected-path register evidence only):', output.getvalue())
                            self.assertIn('Source reconstruction: disabled', output.getvalue())
