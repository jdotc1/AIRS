"""Structural presentation requires current call and error-alias evidence."""
import struct
import unittest

from airs.swift_error_flow import _presentation_eligibility, recover_swift_error_flow
from test_swift_error_flow import image
from test_swift_arithmetic_call_binding import LAYOUTS, recorded
from test_swift_preserved_result_binding import branch_to_postcall


def variants():
    for name, layout in LAYOUTS:
        yield name, layout((0xd2800540,))
    from test_swift_success_return_tail import WORDS as direct
    from test_swift_cmp_success_literals import WORDS as literal
    yield 'direct', direct
    yield 'direct_eq', (0xf10002bf, 0x54000060, *direct[1:])
    yield 'literal_eq', literal


def aliased(words, compare=False):
    test = (words[0] & ~(31 << 5)) | (22 << 5) if compare else (words[0] & ~31) | 22
    return (0xaa1503f6, test, *words[1:])


class PresentationCallBindingFirstTests(unittest.TestCase):
    def test_alias_bypass_withholds_plan_but_preserves_raw_region(self):
        name, layout = LAYOUTS[0]
        _, _, call = recorded(branch_to_postcall(aliased(layout((0xd2800540,))), 8))
        self.assertEqual(call['presentation']['status'], 'blocked')
        self.assertEqual(call['presentation']['reason'], 'unexpected_postcall_entries')
        self.assertNotIn('display_plan', call['presentation'])
        self.assertEqual(call['error_region']['status'], 'structural_region_candidate')
        self.assertTrue(call['window'])
        self.assertTrue(call['error_region']['instructions'])


class PresentationCallBindingBoundaryTests(unittest.TestCase):
    def test_current_calls_keep_existing_shared_and_success_entry_plans(self):
        for name, words in variants():
            with self.subTest(layout=name):
                function, data, call = recorded(words)
                result = call['presentation']
                self.assertEqual(result['status'], 'eligible_structural_only')
                self.assertEqual(result, _presentation_eligibility(call, data, function))
                self.assertEqual(result['display_plan']['condition']['register'], 'x21')
                self.assertFalse(result['source_reconstruction_allowed'])
                self.assertTrue(any('exclusive entry' in text for text in result['limitations']))
                self.assertTrue(any('opaque' in text for text in result['limitations']))

    def test_live_copied_error_alias_survives_original_register_kill(self):
        for name, layout in LAYOUTS:
            words = aliased(layout((0xd2800540,)), name in ('eq', 'ne'))
            words = (words[0], 0xaa1f03f5, *words[1:])
            with self.subTest(layout=name):
                _, _, call = recorded(words)
                self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
                self.assertEqual(call['presentation']['display_plan']['condition']['register'], 'x22')
                self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')

    def test_actual_call_replacement_or_retargeting_cannot_supply_plan(self):
        for name, words in variants():
            function, data, call = recorded(words)
            for word in (0xd503201f, 0x94000040):
                with self.subTest(layout=name, word=hex(word)):
                    raw = bytearray(data); struct.pack_into('<I', raw, 0, word)
                    result = _presentation_eligibility(call, bytes(raw), function)
                    self.assertEqual(result['status'], 'unresolved')
                    self.assertNotIn('display_plan', result)

    def test_missing_or_mismatched_call_fields_withhold_plan(self):
        from copy import deepcopy
        for name, words in variants():
            function, data, original = recorded(words)
            for key, value in (('call_word', '0x94000040'), ('call_word', None),
                               ('callee_pc', original['success_pc']), ('callee_pc', None),
                               ('call_pc', hex(function.start + 1))):
                with self.subTest(layout=name, field=key):
                    call = deepcopy(original); call[key] = value
                    self.assertNotEqual(_presentation_eligibility(call, data, function)['status'],
                                        'eligible_structural_only')
            call = deepcopy(original); del call['call_word']
            self.assertEqual(_presentation_eligibility(call, data, function)['status'], 'unresolved')

    def test_direct_entries_into_copy_or_test_withhold_all_layouts(self):
        for name, layout in LAYOUTS:
            words = aliased(layout((0xd2800540,)), name in ('eq', 'ne'))
            for target in (4, 8):
                with self.subTest(layout=name, target=target):
                    _, _, call = recorded(branch_to_postcall(words, target))
                    self.assertEqual(call['presentation']['status'], 'blocked')
                    self.assertNotIn('display_plan', call['presentation'])
                    self.assertEqual(call['return_choice']['status'], 'unresolved')
                    if name not in ('eq', 'ne'):
                        entry = call['presentation']['postcall_entry_validation']
                        self.assertEqual(entry['unexpected_entry_count'], 1)
                        self.assertEqual(entry['unexpected_entries'][0]['target_pc'],
                                         hex(int(call['caller_pc'], 16) + target))
                        self.assertFalse(entry['exclusive_entry_proven'])
                        self.assertFalse(entry['flag_state_proven'])

    def test_stale_or_forged_alias_window_cannot_reach_plan(self):
        from copy import deepcopy
        for name, layout in LAYOUTS:
            words = aliased(layout((0xd2800540,)), name in ('eq', 'ne'))
            function, data, original = recorded(words)
            raw = bytearray(data); struct.pack_into('<I', raw, 4, 0xaa0003f6); changed = bytes(raw)
            for rewrite in (False, True):
                with self.subTest(layout=name, rewrite=rewrite):
                    call = deepcopy(original)
                    if rewrite:
                        call['window'][0]['word'] = '0xaa0003f6'
                    self.assertEqual(_presentation_eligibility(call, changed, function)['status'], 'unresolved')

    def test_stale_region_and_incoming_metadata_do_not_supply_plan(self):
        from copy import deepcopy
        for name, words in variants():
            function, data, original = recorded(words)
            error = original['error_region']['instructions'][0]
            raw = bytearray(data)
            struct.pack_into('<I', raw, int(error['pc'], 16) - function.start, 0xd503201f)
            with self.subTest(layout=name):
                self.assertEqual(_presentation_eligibility(original, bytes(raw), function)['status'], 'unresolved')
                call = deepcopy(original); call['error_region']['opaque_call_count'] += 1
                self.assertEqual(_presentation_eligibility(call, data, function)['status'], 'unresolved')
                call = deepcopy(original); call['error_region']['incoming_validation']['scanned_word_count'] += 1
                self.assertEqual(_presentation_eligibility(call, data, function)['status'], 'unresolved')

    def test_missing_or_truncated_caller_bytes_cannot_enable_plan(self):
        for name, words in variants():
            function, data, call = recorded(words)
            for raw, boundary in ((None, None), (None, function), (data, None), (data[:-4], function)):
                with self.subTest(layout=name, length=None if raw is None else len(raw)):
                    result = _presentation_eligibility(call, raw, boundary)
                    self.assertNotEqual(result['status'], 'eligible_structural_only')
                    self.assertNotIn('display_plan', result)

    def test_unclassified_current_word_overrides_stale_complete_ledger(self):
        name, layout = LAYOUTS[0]
        words = (*layout((0xd2800540,)), 0xd503201f)
        function, data, call = recorded(words)
        raw = bytearray(data); struct.pack_into('<I', raw, len(words) * 4, 0xffffffff)
        result = _presentation_eligibility(call, bytes(raw), function)
        self.assertEqual(result['status'], 'unresolved')
        self.assertEqual(result['reason'], 'postcall_entries_unresolved')
        self.assertEqual(result['postcall_entry_validation']['unclassified_word_count'], 1)
        self.assertNotIn('display_plan', result)

    def test_partial_instruction_bytes_refuse_without_exception(self):
        for name, words in variants():
            function, data, call = recorded(words)
            for count in (1, 2, 3):
                with self.subTest(layout=name, omitted=count):
                    result = _presentation_eligibility(call, data[:-count], function)
                    self.assertEqual(result['status'], 'unresolved')
                    self.assertNotIn('display_plan', result)

    def test_postcall_conflict_details_stay_capped_with_exact_total(self):
        name, layout = LAYOUTS[0]
        words = aliased(layout((0xd2800540,)))
        start = 4 + len(words) * 4
        branches = tuple(0x14000000 | (((8 - start - index * 4) // 4) & 0x3ffffff)
                         for index in range(20))
        _, _, call = recorded((*words, *branches))
        entry = call['presentation']['postcall_entry_validation']
        self.assertEqual(entry['unexpected_entry_count'], 20)
        self.assertEqual(len(entry['unexpected_entries']), 16)
        self.assertFalse(entry['entry_details_complete'])
        self.assertEqual(entry['scope'], 'caller_local_direct_edges_into_postcall_window')

    def test_cli_displays_bypass_evidence_without_structural_condition(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from airs.cli import main
        name, layout = LAYOUTS[0]
        words = branch_to_postcall(aliased(layout((0xd2800540,))), 8)
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder) / 'bypassed-presentation.macho'
            source.write_bytes(image(words).data)
            for format in ('json', 'text'):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    status = main(['swift-error-flow', str(source), '--include-error-regions',
                        '--validate-region-entries', '--include-structured-presentation', '--format', format])
                self.assertEqual(status, 0)
                if format == 'json':
                    value = json.loads(output.getvalue())
                    self.assertEqual(value['summary']['presentation_eligible_structural_only_count'], 0)
                    self.assertEqual(value['calls'][0]['presentation']['status'], 'blocked')
                    self.assertNotIn('display_plan', value['calls'][0]['presentation'])
                else:
                    for text in ('Structured plan: withheld', 'unexpected_postcall_entries',
                                 'Post-call entry validation:', 'Unexpected post-call entry:',
                                 'Region instruction evidence:', 'Source reconstruction: disabled'):
                        self.assertIn(text, output.getvalue())
                    self.assertNotIn('Condition (structural):', output.getvalue())

    def test_presentation_remains_explicit_opt_in(self):
        name, layout = LAYOUTS[0]
        value = recover_swift_error_flow(image(layout((0xd2800540,))),
            include_error_regions=True, validate_region_entries=True)
        self.assertNotIn('structured_presentation_model_version', value)
        self.assertNotIn('presentation', value['calls'][0])
