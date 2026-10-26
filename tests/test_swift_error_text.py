"""Bounded structural display, preserving uncertainty and terminal safety."""
import unittest
from airs.swift_error_flow import recover_swift_error_flow
from airs.swift_error_text import render_swift_error_text
from test_swift_error_flow import image


def report(tail=()):
    return recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0x94000005, 0x92800000, *tail)),
        include_error_regions=True, validate_region_entries=True, include_structured_presentation=True)


class SwiftErrorTextFirstTests(unittest.TestCase):
    def test_structural_plan_and_opaque_target_are_visible(self):
        text = render_swift_error_text(report())
        self.assertIn('AIRS Swift error-path structural review', text)
        self.assertIn('eligible_structural_only', text)
        self.assertIn('Condition (structural):', text)
        self.assertIn('Error interval:', text)
        self.assertIn('Success entry:', text)
        self.assertIn('0x94000005', text)
        self.assertIn('opaque_call', text)
        self.assertIn('Source reconstruction: disabled', text)
        self.assertTrue(text.endswith('\n'))


class SwiftErrorTextEvidenceTests(unittest.TestCase):
    def test_postcall_raw_test_and_successors_are_retained(self):
        text = render_swift_error_text(report())
        self.assertIn('Post-call instruction evidence:', text)
        self.assertIn('0xb4000095', text)
        self.assertIn('Recorded return edges:', text)
        self.assertIn('"test_pc"', text)
        self.assertIn('"success_pc"', text)
        self.assertIn('"error_pc"', text)


class SwiftErrorTextBoundaryTests(unittest.TestCase):
    def test_blocked_and_unresolved_show_evidence_without_plan(self):
        for tail, status in (((0x17fffffd,), 'blocked'), ((0xffffffff,), 'unresolved')):
            text = render_swift_error_text(report(tail))
            self.assertIn('"status": "' + status + '"', text)
            self.assertIn('Structured plan: withheld', text)
            self.assertNotIn('Condition (structural):', text)
            self.assertIn('Region instruction evidence:', text)
            self.assertIn('Post-call instruction evidence:', text)
            self.assertIn('Incoming validation:', text)
            if status == 'blocked': self.assertIn('Unexpected direct entry:', text)
            else: self.assertIn('Unclassified word:', text)

    def test_all_dynamic_fields_are_terminal_safe_ascii(self):
        value = report()
        unsafe = '\x1b[31m\n\r\t\x00\u202eé\x7f'
        value['image'] = {unsafe: unsafe}
        value['summary'][unsafe] = 4
        value['input_issues'] = [{unsafe: unsafe}]
        call = value['calls'][0]
        call['callee']['symbol'] = unsafe
        call['window'][0]['kind'] = unsafe
        call['presentation']['display_plan']['label'] = unsafe
        call['presentation']['display_plan']['condition'][unsafe] = unsafe
        call['presentation']['display_plan']['error_interval']['instructions'][0]['kind'] = unsafe
        call['error_region']['incoming_validation'][unsafe] = unsafe
        call['presentation']['limitations'] = [unsafe]
        value['limitations'] = [unsafe]
        text = render_swift_error_text(value)
        self.assertTrue(text.isascii())
        for raw in ('\x1b', '\r', '\t', '\x00', '\u202e', 'é', '\x7f'):
            self.assertNotIn(raw, text)
        self.assertIn('\\u001b[31m\\n\\r\\t\\u0000\\u202e\\u00e9\\u007f', text)

    def test_call_caps_and_source_omissions_preserve_full_counts(self):
        from copy import deepcopy
        value = report(); value['calls'] = [deepcopy(value['calls'][0]) for _ in range(40)]
        value['summary'].update(retained_call_count=40, observed_direct_call_count=47, omitted_call_count=7,
            recovered_candidate_count=40, declined_retained_call_count=0,
            presentation_eligible_structural_only_count=40, presentation_blocked_count=0)
        value['call_details_complete'] = False
        text = render_swift_error_text(value)
        self.assertEqual(text.count('\nCall candidate\n'), 32)
        self.assertIn('Retained call rows omitted by renderer: 8', text)
        self.assertIn('"omitted_call_count": 7', text)
        self.assertIn('"retained_call_count": 40', text)
        self.assertIn('"observed_direct_call_count": 47', text)
        self.assertIn('Call details complete: false', text)

    def test_evidence_limits_and_source_truncation_are_distinct(self):
        from copy import deepcopy
        value = report(); call = value['calls'][0]
        call['window'] = [deepcopy(call['window'][0]) for _ in range(10)]
        call['presentation']['display_plan']['error_interval']['instructions'] *= 7
        entry = call['error_region']['incoming_validation']
        entry['unexpected_entries'] = [{'source_pc': '0x10', 'target_pc': '0x20'}] * 20
        entry['unexpected_entry_count'] = 27; entry['entry_details_complete'] = False
        entry['unclassified_words'] = [{'pc': '0x30', 'word': '0xffffffff'}] * 18
        entry['unclassified_word_count'] = 25; entry['unclassified_details_complete'] = False
        text = render_swift_error_text(value)
        self.assertIn('Post-call instruction evidence detail rows omitted by renderer: 2', text)
        self.assertIn('Instruction detail rows omitted by renderer: 5', text)
        self.assertIn('Unexpected direct entry detail rows omitted by renderer: 4', text)
        self.assertIn('Unclassified word detail rows omitted by renderer: 2', text)
        self.assertIn('"unexpected_entry_count": 27', text)
        self.assertIn('"entry_details_complete": false', text)

    def test_report_issues_and_limitations_have_explicit_omissions(self):
        value = report(); value['input_issues'] = [{'code': 'issue'}] * 19
        value['limitations'] = ['limit'] * 20
        value['calls'][0]['presentation']['limitations'] = ['candidate limit'] * 18
        text = render_swift_error_text(value)
        self.assertIn('Input issue detail rows omitted by renderer: 3', text)
        self.assertIn('Report limitation detail rows omitted by renderer: 4', text)
        self.assertIn('Candidate limitation detail rows omitted by renderer: 2', text)

    def test_exact_byte_fit_and_one_byte_overflow(self):
        from airs.types import InputError
        value = report(); expected = render_swift_error_text(value)
        size = len(expected.encode('ascii'))
        self.assertEqual(render_swift_error_text(value, maximum_bytes=size), expected)
        with self.assertRaises(InputError) as caught:
            render_swift_error_text(value, maximum_bytes=size - 1)
        self.assertEqual(caught.exception.code, 'generated_report_size_limit')

    def test_invalid_limits_and_global_cap(self):
        from unittest.mock import patch
        from airs.types import InputError
        value = report()
        for limit in (True, False, -1, 1.5, None, '8'):
            with self.assertRaises(InputError) as caught:
                render_swift_error_text(value, maximum_bytes=limit)
            self.assertEqual(caught.exception.code, 'invalid_report_size_limit')
        with patch('airs.swift_error_text.MAXIMUM_TEXT_BYTES', 256):
            with self.assertRaises(InputError):
                render_swift_error_text(value, maximum_bytes=1024 * 1024)

    def test_render_does_not_mutate_producer_report(self):
        from copy import deepcopy
        value = report(); original = deepcopy(value)
        render_swift_error_text(value)
        self.assertEqual(value, original)

    def test_model_and_presentation_prerequisites_refuse(self):
        from copy import deepcopy
        from airs.types import InputError
        original = report()
        for key in ('model_version', 'error_region_model_version', 'region_incoming_model_version', 'structured_presentation_model_version'):
            value = deepcopy(original); del value[key]
            with self.assertRaises(InputError): render_swift_error_text(value)
        for mode in ('missing', 'unknown', 'source'):
            value = deepcopy(original)
            if mode == 'missing': del value['calls'][0]['presentation']
            elif mode == 'unknown': value['calls'][0]['presentation']['status'] = 'approved'
            else: value['calls'][0]['presentation']['source_reconstruction_allowed'] = True
            with self.assertRaises(InputError): render_swift_error_text(value)

    def test_empty_report_has_explicit_zero_detail_count(self):
        value = report(); value['calls'] = []
        value['summary'] = {'retained_call_count': 0, 'omitted_call_count': 0}
        text = render_swift_error_text(value)
        self.assertIn('Retained call rows available: 0', text)
        self.assertIn('Retained call rows omitted by renderer: 0', text)
        self.assertNotIn('\nCall candidate\n', text)

    def test_cli_text_json_protected_export_and_size_refusal(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        from airs.cli import main
        from airs.types import InputError
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-error-flow'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source, output_file = Path(folder) / 'render.macho', Path(folder) / 'review.txt'
            original = image((0xb4000095, 0xaa1503e0, 0x94000005, 0x92800000)).data
            source.write_bytes(original)
            options = ['swift-error-flow', str(source), '--include-error-regions', '--validate-region-entries', '--include-structured-presentation']
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                self.assertEqual(main([*options, '--format', 'text', '--output', str(output_file)]), 0)
            self.assertIn('AIRS Swift error-path structural review', output_file.read_text())
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                self.assertEqual(main([*options, '--format', 'text', '--output', str(source)]), 2)
            self.assertEqual(source.read_bytes(), original)
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                self.assertEqual(main(options), 0)
            self.assertEqual(json.loads(output.getvalue())['report_kind'], 'airs.swift_error_flow')
            with contextlib.redirect_stderr(errors):
                self.assertEqual(main(['swift-error-flow', str(source), '--format', 'text']), 2)
            before = output_file.read_bytes()
            with patch('airs.cli.render_swift_error_text', side_effect=InputError('generated_report_size_limit', 'bounded')):
                with contextlib.redirect_stderr(errors):
                    self.assertEqual(main([*options, '--format', 'text', '--output', str(output_file)]), 2)
            self.assertEqual(output_file.read_bytes(), before)
