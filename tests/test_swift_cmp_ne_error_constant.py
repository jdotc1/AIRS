"""Bounded CMP/B.NE error-arm literals, without success or choice claims."""
import unittest
from test_swift_cmp_ne_handler import report


class NeErrorConstantFirstTests(unittest.TestCase):
    def test_error_literal_is_structural_candidate(self):
        call = report()['calls'][0]
        result = call['error_constant']
        self.assertEqual(result['status'], 'constant_register_candidate')
        self.assertEqual(result['constant_bits'], '0xffffffffffffffff')
        for key in ('runtime_value_proven', 'call_return_proven', 'handler_semantics_proven',
                    'exclusive_path_proven', 'caller_return_type_proven', 'source_reconstruction_allowed'):
            self.assertFalse(result[key])
        self.assertEqual(call['success_result']['status'], 'declined')
        self.assertEqual(call['success_constant']['status'], 'constant_register_candidate')
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')


class NeErrorConstantBoundaryTests(unittest.TestCase):
    def test_opaque_call_invalidates_prior_literal_and_later_literal_recovers(self):
        from test_swift_cmp_ne_handler import WORDS
        before = (*WORDS[:4], 0x92800000, 0x94000010, WORDS[6])
        after = (*WORDS[:4], 0x94000010, 0x92800000, WORDS[6])
        self.assertEqual(report(before)['calls'][0]['error_constant']['reason'], 'error_x0_constant_not_known')
        result = report(after)['calls'][0]['error_constant']
        self.assertEqual(result['constant_bits'], '0xffffffffffffffff')
        self.assertEqual(result['opaque_call_count'], 1)

    def test_word_literals_zero_extend_and_unknown_move_wide_refuses(self):
        from test_swift_cmp_ne_handler import WORDS
        for word, bits in ((0x12800000, '0x00000000ffffffff'), (0x52800540, '0x000000000000002a')):
            self.assertEqual(report((*WORDS[:5], word, WORDS[6]))['calls'][0]['error_constant']['constant_bits'], bits)
        result = report((*WORDS[:5], 0xf2a00020, WORDS[6]))['calls'][0]['error_constant']
        self.assertEqual(result['reason'], 'error_x0_constant_not_known')

    def test_unknown_copy_does_not_invent_a_literal(self):
        from test_swift_cmp_ne_handler import WORDS
        result = report((*WORDS[:4], 0xd2800540, 0xaa1403e0, WORDS[6]))['calls'][0]['error_constant']
        self.assertEqual(result['reason'], 'error_x0_constant_not_known')

    def test_side_entries_partial_and_unknown_callers_decline(self):
        from test_swift_cmp_ne_handler import WORDS
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        for target in (4, 8, 12, 16, 20, 24, 28):
            branch = 0x14000000 | (((target-32)//4) & 0x3ffffff)
            self.assertEqual(report((*WORDS, branch))['calls'][0]['error_constant']['status'], 'declined')
        self.assertEqual(report((*WORDS, 0xffffffff))['calls'][0]['error_constant']['status'], 'declined')
        self.assertEqual(report(limits=replace(DEFAULT_LIMITS, max_instructions_per_function=7))['calls'][0]['error_constant']['status'], 'declined')

    def test_stale_raw_selected_words_and_new_side_entry_decline(self):
        import struct
        from test_swift_cmp_ne_handler import WORDS
        from test_swift_error_flow import image
        from airs.swift_error_flow import _path_constant
        words = (*WORDS, 0xd503201f)
        value = image(words); function = value.functions[0]
        data = value.bytes_at(function.start, function.size)
        call = report(words)['calls'][0]
        for offset, word in ((4, 0xf100029f), (8, 0x54000060), (12, 0xd2800540),
                             (20, 0xd2800540), (28, 0xd65f0000), (32, 0x17fffffd)):
            raw = bytearray(data); struct.pack_into('<I', raw, offset, word)
            self.assertEqual(_path_constant(bytes(raw), function, call, error=True)['status'], 'declined')

    def test_forged_flag_incoming_and_region_metadata_decline(self):
        from copy import deepcopy
        from test_swift_cmp_ne_handler import WORDS
        from test_swift_error_flow import image
        from airs.swift_error_flow import _path_constant
        value = image(WORDS); function = value.functions[0]
        data = value.bytes_at(function.start, function.size)
        original = report()['calls'][0]
        for group, key, changed in (('flag_entry_validation', 'flag_state_proven', True),
            ('incoming_validation', 'unexpected_entry_count', 1), ('error_region', 'opaque_call_count', 1)):
            call = deepcopy(original)
            section = call[group] if group == 'flag_entry_validation' else call['error_region'] if group == 'error_region' else call['error_region'][group]
            section[key] = changed
            self.assertEqual(_path_constant(data, function, call, error=True)['status'], 'declined')

    def test_text_displays_error_candidate_and_retains_closed_choice(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report())
        for expected in ('0xffffffffffffffff', 'constant_register_candidate',
                         'structural_choice_candidate', 'Source reconstruction: disabled'):
            self.assertIn(expected, text)

    def test_cli_preserves_error_candidate_and_closed_return_choice(self):
        import contextlib, io, json, tempfile
        from pathlib import Path
        from airs.cli import main
        from test_swift_cmp_ne_handler import WORDS
        from test_swift_error_flow import image
        root = Path('local-evidence/swift-cmp-ne-error-constant')
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'; source.write_bytes(image(WORDS).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            call = json.loads(output.getvalue())['calls'][0]
            self.assertEqual(call['error_constant']['constant_bits'], '0xffffffffffffffff')
            self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
