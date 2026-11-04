"""Bind preserved/copied call results to the current caller and alias window."""
import struct
import unittest

from airs.swift_error_flow import _caller_direct_edges, _success_result, recover_swift_error_flow
from test_swift_error_flow import image
from test_swift_arithmetic_call_binding import LAYOUTS, recorded

NOP = 0xd503201f
SAVE = 0xaa0003f3
CLEAR = 0xaa1f03e0
RESTORE = 0xaa1303e0
DIRECT = (0xb4000075, 0x92800000, 0x14000001, 0xd65f03c0)
DIRECT_EQ = (0xf10002bf, 0x54000060, 0x92800000, 0x14000001, 0xd65f03c0)


def variants():
    for name, layout in LAYOUTS:
        yield name, layout((NOP,)), 'preserved_register_candidate'
        yield name + '_copy', (SAVE, CLEAR, *layout((RESTORE,))), 'copied_register_candidate'
    for name, words in (('direct', DIRECT), ('direct_eq', DIRECT_EQ)):
        yield name, words, 'preserved_register_candidate'
        yield name + '_copy', (SAVE, CLEAR, RESTORE, *words), 'copied_register_candidate'


def branch_to_postcall(words, target):
    source = 4 + len(words) * 4
    return (*words, 0x14000000 | (((target - source) // 4) & 0x3ffffff))


class PreservedResultBindingFirstTests(unittest.TestCase):
    def test_entry_bypassing_saved_copy_cannot_supply_call_result(self):
        _, layout = LAYOUTS[0]
        words = (SAVE, CLEAR, *layout((RESTORE,)))
        _, _, call = recorded(branch_to_postcall(words, 8))
        self.assertEqual(call['success_result']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')


class PreservedResultBindingBoundaryTests(unittest.TestCase):
    def test_valid_preserved_and_copied_results_keep_bounds_and_proof_limits(self):
        for name, words, status in variants():
            with self.subTest(layout=name):
                function, data, call = recorded(words)
                result = call['success_result']
                self.assertEqual(result['status'], status)
                self.assertEqual(result, _success_result(data, function, call, _caller_direct_edges(data, function)))
                self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
                self.assertEqual(call['return_choice']['success']['kind'], 'call_result')
                self.assertLessEqual(len(result['instructions']), 24)
                for key in ('runtime_value_proven', 'source_reconstruction_allowed',
                            'exclusive_path_proven', 'caller_return_type_proven'):
                    self.assertFalse(result[key])

    def test_actual_call_replacement_or_retargeting_refuses_every_result_layout(self):
        for name, words, _ in variants():
            function, data, call = recorded(words)
            for word in (NOP, 0x94000040):
                with self.subTest(layout=name, word=hex(word)):
                    raw = bytearray(data); struct.pack_into('<I', raw, 0, word); changed = bytes(raw)
                    self.assertEqual(_success_result(changed, function, call,
                        _caller_direct_edges(changed, function))['status'], 'declined')

    def test_missing_or_mismatched_call_metadata_refuses(self):
        from copy import deepcopy
        for name, words, _ in variants():
            function, data, original = recorded(words)
            scan = _caller_direct_edges(data, function)
            for key, value in (('call_word', '0x94000040'), ('callee_pc', original['success_pc']),
                               ('call_word', None), ('callee_pc', None),
                               ('call_pc', hex(function.start + 1))):
                with self.subTest(layout=name, key=key):
                    call = deepcopy(original); call[key] = value
                    self.assertEqual(_success_result(data, function, call, scan)['status'], 'declined')
            call = deepcopy(original); del call['call_word']
            self.assertEqual(_success_result(data, function, call, scan)['status'], 'declined')

    def test_branches_into_copy_or_test_window_withhold_fresh_result(self):
        for name, words, _ in variants():
            _, _, original = recorded(words)
            end = int(original['test_pc'], 16) - int(original['caller_pc'], 16)
            for target in (4, end):
                with self.subTest(layout=name, target=target):
                    _, _, call = recorded(branch_to_postcall(words, target))
                    self.assertEqual(call['success_result']['status'], 'declined')
                    self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_live_error_alias_survives_but_clobbered_alias_cannot_be_forged(self):
        from copy import deepcopy
        for name, layout in LAYOUTS:
            words = list(layout((RESTORE,)))
            if name in ('eq', 'ne'):
                words[0] = (words[0] & ~(31 << 5)) | (22 << 5)
            else:
                words[0] = (words[0] & ~31) | 22
            words = (SAVE, CLEAR, 0xaa1503f6, 0xaa1f03f5, *words)
            with self.subTest(layout=name):
                function, data, original = recorded(words)
                self.assertEqual(original['success_result']['status'], 'copied_register_candidate')
                self.assertEqual(original['tested_register'], 'x22')
                raw = bytearray(data); struct.pack_into('<I', raw, 12, 0xaa0003f6); changed = bytes(raw)
                call = deepcopy(original)
                call['window'][2]['word'] = '0xaa0003f6'
                self.assertEqual(_success_result(changed, function, call,
                    _caller_direct_edges(changed, function))['status'], 'declined')

    def test_stale_error_words_or_region_metadata_cannot_supply_result(self):
        from copy import deepcopy
        for name, words, _ in variants():
            function, data, original = recorded(words)
            error = original['error_region']['instructions'][0]
            raw = bytearray(data); struct.pack_into('<I', raw, int(error['pc'], 16) - function.start, NOP)
            changed = bytes(raw)
            with self.subTest(layout=name):
                self.assertEqual(_success_result(changed, function, original,
                    _caller_direct_edges(changed, function))['status'], 'declined')
                call = deepcopy(original); call['error_region']['opaque_call_count'] += 1
                self.assertEqual(_success_result(data, function, call,
                    _caller_direct_edges(data, function))['status'], 'declined')
                call = deepcopy(original)
                call['presentation']['display_plan']['condition']['register'] = 'x20'
                self.assertEqual(_success_result(data, function, call,
                    _caller_direct_edges(data, function))['status'], 'declined')

    def test_missing_stale_or_partial_scan_never_clears_binding(self):
        from copy import deepcopy
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        for name, words, _ in variants():
            function, data, call = recorded(words)
            scan = _caller_direct_edges(data, function)
            stale = deepcopy(scan); stale['scanned_word_count'] += 1
            with self.subTest(layout=name):
                for supplied in (None, stale):
                    self.assertEqual(_success_result(data, function, call, supplied)['status'], 'declined')
                _, _, unknown = recorded((*words, 0xffffffff))
                self.assertEqual(unknown['return_choice']['status'], 'unresolved')
                value = recover_swift_error_flow(image(words), include_error_regions=True,
                    validate_region_entries=True, include_structured_presentation=True,
                    limits=replace(DEFAULT_LIMITS, max_instructions_per_function=5))
                self.assertEqual(value['calls'][0]['return_choice']['status'], 'unresolved')

    def test_changed_test_or_successor_metadata_cannot_reuse_call_result(self):
        from copy import deepcopy
        for name, words, _ in variants():
            function, data, original = recorded(words)
            scan = _caller_direct_edges(data, function)
            for key, value in (('tested_register', 'x20'), ('success_pc', original['error_pc']),
                               ('error_pc', original['success_pc'])):
                with self.subTest(layout=name, key=key):
                    call = deepcopy(original); call[key] = value
                    self.assertEqual(_success_result(data, function, call, scan)['status'], 'declined')

    def test_cli_withholds_bypassed_result_and_retains_structural_limits(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from airs.cli import main
        _, layout = LAYOUTS[0]
        words = branch_to_postcall((SAVE, CLEAR, *layout((RESTORE,))), 8)
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder) / 'bypassed-result.macho'
            source.write_bytes(image(words).data)
            for format in ('json', 'text'):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    status = main(['swift-error-flow', str(source), '--include-error-regions',
                        '--validate-region-entries', '--include-structured-presentation', '--format', format])
                self.assertEqual(status, 0)
                if format == 'json':
                    call = json.loads(output.getvalue())['calls'][0]
                    self.assertEqual(call['success_result']['status'], 'declined')
                    self.assertEqual(call['return_choice']['status'], 'unresolved')
                else:
                    self.assertIn('unexpected_postcall_entries', output.getvalue())
                    self.assertIn('Source reconstruction: disabled', output.getvalue())
                    self.assertNotIn('copied_register_candidate', output.getvalue())
