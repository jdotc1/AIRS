"""Literal outcomes require current calls, aliases and selected-path evidence."""
import struct
import unittest

from airs.swift_error_flow import _caller_direct_edges, _path_constant, recover_swift_error_flow
from test_swift_error_flow import image
from test_swift_shared_epilogue import WORDS
from test_swift_arithmetic_call_binding import LAYOUTS, recorded
from test_swift_preserved_result_binding import branch_to_postcall

NOP = 0xd503201f


def literal_variants():
    for name, layout in LAYOUTS:
        yield name, layout((0xd2800540,)), ('success', 'error')
    from test_swift_cmp_success_literals import WORDS as direct_eq
    from test_swift_success_return_tail import WORDS as direct_cbz
    yield 'eq_direct', direct_eq, ('success', 'error')
    yield 'cbz_direct', direct_cbz, ('error',)


def constant(data, function, call, path, scan):
    return _path_constant(data, function, call, error=path == 'error', scan=scan)


class LiteralCallBindingFirstTests(unittest.TestCase):
    def test_entry_bypassing_error_alias_cannot_supply_literal_choice(self):
        words = (0xaa1503f6, (WORDS[0] & ~31) | 22, *WORDS[1:])
        _, _, call = recorded(branch_to_postcall(words, 8))
        self.assertEqual(call['success_constant']['status'], 'declined')
        self.assertEqual(call['error_constant']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')


class LiteralCallBindingBoundaryTests(unittest.TestCase):
    def test_existing_literal_layouts_and_success_entry_outcomes_remain_bound(self):
        for name, words, paths in literal_variants():
            function, data, call = recorded(words)
            scan = _caller_direct_edges(data, function)
            with self.subTest(layout=name):
                for path in paths:
                    result = call[path + '_constant']
                    self.assertEqual(result['status'], 'constant_register_candidate')
                    expected = ('0x000000000000002a' if path == 'success' else
                                '0xfffffffffffffff9' if name == 'cbz' else '0xffffffffffffffff')
                    self.assertEqual(result['constant_bits'], expected)
                    self.assertEqual(result, constant(data, function, call, path, scan))
                    for key in ('depends_on_call_result', 'runtime_value_proven', 'exclusive_path_proven',
                                'caller_return_type_proven', 'source_reconstruction_allowed'):
                        self.assertFalse(result[key])
                    self.assertLessEqual(len(result['instructions']), 24)
                self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
                self.assertFalse(call['error_constant']['handler_semantics_proven'])
                self.assertFalse(call['error_constant']['call_return_proven'])

    def test_x_w_seed_copy_movk_and_zero_register_values_are_unchanged(self):
        cases = (((0xd2800553, 0xaa1303e0), '0x000000000000002a'),
                 ((0x12800000,), '0x00000000ffffffff'),
                 ((0xd2800540, 0xf2a00020), '0x000000000001002a'),
                 ((0x12800000, 0x72a00020), '0x000000000001ffff'),
                 ((0xaa1f03e0,), '0x0000000000000000'))
        for name, layout in LAYOUTS:
            for arm, expected in cases:
                with self.subTest(layout=name, words=arm):
                    _, _, call = recorded(layout(arm))
                    self.assertEqual(call['success_constant']['constant_bits'], expected)
                    self.assertEqual(call['return_choice']['success']['constant_bits'], expected)

    def test_replaced_or_redirected_actual_call_cannot_supply_either_literal(self):
        for name, words, paths in literal_variants():
            function, data, call = recorded(words)
            for word in (NOP, 0x94000040):
                raw = bytearray(data); struct.pack_into('<I', raw, 0, word); changed = bytes(raw)
                for path in paths:
                    with self.subTest(layout=name, path=path, word=hex(word)):
                        self.assertEqual(constant(changed, function, call, path,
                            _caller_direct_edges(changed, function))['status'], 'declined')

    def test_missing_or_mismatched_call_metadata_withholds_literals(self):
        from copy import deepcopy
        for name, words, paths in literal_variants():
            function, data, original = recorded(words)
            scan = _caller_direct_edges(data, function)
            for key, value in (('call_word', '0x94000040'), ('callee_pc', original['success_pc']),
                               ('call_word', None), ('callee_pc', None), ('call_pc', hex(function.start + 1))):
                call = deepcopy(original); call[key] = value
                for path in paths:
                    with self.subTest(layout=name, path=path, key=key):
                        self.assertEqual(constant(data, function, call, path, scan)['status'], 'declined')
            call = deepcopy(original); del call['call_word']
            for path in paths:
                self.assertEqual(constant(data, function, call, path, scan)['status'], 'declined')

    def test_live_error_alias_survives_but_bypass_entries_withhold_both_literals(self):
        for name, layout in LAYOUTS:
            words = list(layout((0xd2800540,)))
            words[0] = ((words[0] & ~(31 << 5)) | (22 << 5) if name in ('eq', 'ne')
                        else (words[0] & ~31) | 22)
            words = (0xaa1503f6, *words)
            with self.subTest(layout=name):
                _, _, positive = recorded(words)
                self.assertEqual(positive['tested_register'], 'x22')
                self.assertEqual(positive['return_choice']['status'], 'structural_choice_candidate')
                for target in (4, 8):
                    _, _, call = recorded(branch_to_postcall(words, target))
                    self.assertEqual(call['success_constant']['status'], 'declined')
                    self.assertEqual(call['error_constant']['status'], 'declined')
                    self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_changed_error_alias_cannot_be_forged_as_established(self):
        from copy import deepcopy
        for name, layout in LAYOUTS:
            words = list(layout((0xd2800540,)))
            words[0] = ((words[0] & ~(31 << 5)) | (22 << 5) if name in ('eq', 'ne')
                        else (words[0] & ~31) | 22)
            function, data, original = recorded((0xaa1503f6, *words))
            raw = bytearray(data); struct.pack_into('<I', raw, 4, 0xaa0003f6); changed = bytes(raw)
            call = deepcopy(original); call['window'][0]['word'] = '0xaa0003f6'
            for path in ('success', 'error'):
                with self.subTest(layout=name, path=path):
                    self.assertEqual(constant(changed, function, call, path,
                        _caller_direct_edges(changed, function))['status'], 'declined')

    def test_stale_success_or_error_words_cannot_supply_current_literal(self):
        for name, words, paths in literal_variants():
            function, data, call = recorded(words)
            for path in paths:
                rows = call[path + '_constant']['instructions']
                row = next(item for item in rows if item['word'] in ('0xd2800540', '0x92800000', '0x928000c0'))
                raw = bytearray(data)
                struct.pack_into('<I', raw, int(row['pc'], 16) - function.start, 0xd2800560)
                changed = bytes(raw)
                with self.subTest(layout=name, path=path):
                    self.assertEqual(constant(changed, function, call, path,
                        _caller_direct_edges(changed, function))['status'], 'declined')

    def test_forged_region_display_or_successor_metadata_refuses(self):
        from copy import deepcopy
        for name, words, paths in literal_variants():
            function, data, original = recorded(words)
            scan = _caller_direct_edges(data, function)
            for field in ('region', 'display', 'successor'):
                call = deepcopy(original)
                if field == 'region':
                    call['error_region']['opaque_call_count'] += 1
                elif field == 'display':
                    call['presentation']['display_plan']['condition']['register'] = 'x20'
                else:
                    call['success_pc'] = call['error_pc']
                for path in paths:
                    with self.subTest(layout=name, path=path, field=field):
                        self.assertEqual(constant(data, function, call, path, scan)['status'], 'declined')

    def test_missing_stale_unknown_and_partial_scans_withhold_literals(self):
        from copy import deepcopy
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        for name, words, paths in literal_variants():
            function, data, call = recorded(words)
            stale = deepcopy(_caller_direct_edges(data, function)); stale['scanned_word_count'] += 1
            with self.subTest(layout=name):
                for scan in (None, stale):
                    for path in paths:
                        self.assertEqual(constant(data, function, call, path, scan)['status'], 'declined')
                _, _, unknown = recorded((*words, 0xffffffff))
                self.assertEqual(unknown['return_choice']['status'], 'unresolved')
                limited = recover_swift_error_flow(image(words), include_error_regions=True,
                    validate_region_entries=True, include_structured_presentation=True,
                    limits=replace(DEFAULT_LIMITS, max_instructions_per_function=5))
                self.assertEqual(limited['calls'][0]['return_choice']['status'], 'unresolved')

    def test_cli_withholds_bypassed_literals_and_keeps_proof_limits(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from airs.cli import main
        words = branch_to_postcall((0xaa1503f6, (WORDS[0] & ~31) | 22, *WORDS[1:]), 8)
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder) / 'bypassed-literal.macho'
            source.write_bytes(image(words).data)
            for format in ('json', 'text'):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    status = main(['swift-error-flow', str(source), '--include-error-regions',
                        '--validate-region-entries', '--include-structured-presentation', '--format', format])
                self.assertEqual(status, 0)
                if format == 'json':
                    call = json.loads(output.getvalue())['calls'][0]
                    self.assertEqual(call['success_constant']['status'], 'declined')
                    self.assertEqual(call['error_constant']['status'], 'declined')
                    self.assertEqual(call['return_choice']['status'], 'unresolved')
                else:
                    self.assertIn('unexpected_postcall_entries', output.getvalue())
                    self.assertIn('Source reconstruction: disabled', output.getvalue())
                    self.assertNotIn('constant_register_candidate', output.getvalue())
