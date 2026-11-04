"""Selected CMP/B.NE success literals and bound return choice."""
import unittest
from test_swift_cmp_ne_handler import report, WORDS


class NeSuccessLiteralFirstTests(unittest.TestCase):
    def test_success_literal_and_error_literal_form_structural_choice(self):
        call = report()['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x0000000000000000')
        self.assertEqual(call['return_choice']['success']['constant_bits'], '0x0000000000000000')
        self.assertEqual(call['return_choice']['error']['constant_bits'], '0xffffffffffffffff')
        self.assertFalse(call['return_choice']['runtime_value_proven'])
        self.assertFalse(call['return_choice']['source_reconstruction_allowed'])


class NeSuccessLiteralBoundaryTests(unittest.TestCase):
    def test_success_arm_overwrites_prefix_literal(self):
        call = report((0xd2800540, *WORDS))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x0000000000000000')

    def test_prefix_literal_survives_nop_success_arm(self):
        words = (0xd2800540, *WORDS[:2], 0xd503201f, *WORDS[3:])
        call = report(words)['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x000000000000002a')
        self.assertEqual(call['return_choice']['success']['kind'], 'constant_bits')

    def test_unknown_copy_and_unknown_movk_do_not_invent_value(self):
        for word in (0xaa1403e0, 0xf2a00020):
            words = (*WORDS[:2], word, *WORDS[3:])
            call = report(words)['calls'][0]
            self.assertEqual(call['success_constant']['status'], 'declined')
            self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_word_literal_zero_extends_and_movk_updates_seed(self):
        for word, bits in ((0x12800000, '0x00000000ffffffff'), (0x52800540, '0x000000000000002a')):
            call = report((*WORDS[:2], word, *WORDS[3:]))['calls'][0]
            self.assertEqual(call['success_constant']['constant_bits'], bits)
        words = (0xd2800540, *WORDS[:2], 0xf2a00020, *WORDS[3:])
        self.assertEqual(report(words)['calls'][0]['success_constant']['constant_bits'], '0x000000000001002a')

    def test_result_and_literal_sources_cannot_both_win(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        call = deepcopy(report()['calls'][0]); call['success_result']['status'] = 'preserved_register_candidate'
        self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_error_literal_before_opaque_call_cannot_form_choice(self):
        words = (*WORDS[:4], 0x92800000, 0x94000010, WORDS[6])
        call = report(words)['calls'][0]
        self.assertEqual(call['success_constant']['status'], 'constant_register_candidate')
        self.assertEqual(call['error_constant']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_side_entries_partial_unknown_and_bad_success_exit_decline(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        for target in (4, 8, 12, 16, 20, 24, 28):
            branch = 0x14000000 | (((target - 32)//4) & 0x3ffffff)
            self.assertEqual(report((*WORDS, branch))['calls'][0]['success_constant']['status'], 'declined')
        self.assertEqual(report((*WORDS, 0xffffffff))['calls'][0]['success_constant']['status'], 'declined')
        self.assertEqual(report(limits=replace(DEFAULT_LIMITS, max_instructions_per_function=7))['calls'][0]['success_constant']['status'], 'declined')
        self.assertEqual(report((*WORDS[:3], 0x14000002, *WORDS[4:]))['calls'][0]['success_constant']['status'], 'declined')

    def test_changed_supported_prefix_arm_tail_and_side_entry_refuse_stale_record(self):
        import struct
        from airs.swift_error_flow import _path_constant
        from test_swift_error_flow import image
        words = (0xd2800540, *WORDS, 0xd503201f)
        value = image(words); function = value.functions[0]
        data = value.bytes_at(function.start, function.size); call = report(words)['calls'][0]
        for offset, word in ((4, 0xd2800560), (8, 0xf100029f), (12, 0x54000060),
                             (16, 0xd2800540), (20, 0x14000002), (24, 0xd2800540),
                             (32, 0xd65f0000), (36, 0x17fffffd)):
            raw = bytearray(data); struct.pack_into('<I', raw, offset, word)
            self.assertEqual(_path_constant(bytes(raw), function, call)['status'], 'declined')

    def test_condition_return_and_proof_flags_bind_literal_choice(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        call = report()['calls'][0]
        for section, key, value in (('success_constant', 'return_pc', '0x0'),
            ('error_constant', 'return_pc', '0x0'), ('success_constant', 'runtime_value_proven', True),
            ('success_constant', 'return_tail_layout', 'success_entry'), ('error_constant', 'bit_width', 32)):
            altered = deepcopy(call); altered[section][key] = value
            self.assertEqual(_return_choice(altered)['status'], 'unresolved')
        altered = deepcopy(call); altered['presentation']['display_plan']['condition']['test_condition'] = 'eq'
        self.assertEqual(_return_choice(altered)['status'], 'unresolved')

    def test_text_and_cli_preserve_structural_literal_choice(self):
        import contextlib, io, json, tempfile
        from pathlib import Path
        from airs.cli import main
        from airs.swift_error_text import render_swift_error_text
        from test_swift_error_flow import image
        text = render_swift_error_text(report())
        for expected in ('structural_choice_candidate', '0xffffffffffffffff', 'Source reconstruction: disabled'):
            self.assertIn(expected, text)
        root = Path('local-evidence/swift-cmp-ne-success-literal'); root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'; source.write_bytes(image(WORDS).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            call = json.loads(output.getvalue())['calls'][0]
            self.assertEqual(call['return_choice']['success']['kind'], 'constant_bits')
            self.assertFalse(call['return_choice']['runtime_value_proven'])

    def test_void_callee_can_establish_explicit_literal_bits(self):
        from airs.swift_error_flow import recover_swift_error_flow
        from test_swift_error_flow import image
        value = recover_swift_error_flow(image(WORDS, symbol='_$s4Demo4readyyKF'),
            include_error_regions=True, validate_region_entries=True, include_structured_presentation=True)
        call = value['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x0000000000000000')
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
        self.assertFalse(call['return_choice']['caller_return_type_proven'])

    def test_prefix_and_success_arm_have_separate_eight_word_limits(self):
        exact = (0xd2800540, *(0xd503201f,)*5, *WORDS[:2], 0xd503201f, *WORDS[3:])
        self.assertEqual(report(exact)['calls'][0]['success_constant']['constant_bits'], '0x000000000000002a')
        over = (0xd2800540, *(0xd503201f,)*6, *WORDS[:2], 0xd503201f, *WORDS[3:])
        self.assertEqual(report(over)['calls'][0]['success_constant']['status'], 'declined')
        for count in (8, 9):
            error = 12 + 4 * count; join = error + 4
            words = (0xf10002bf, 0x54000001 | (((error-8)//4) << 5), 0xd2800000,
                     *((0xd503201f,) * (count-2)), 0x14000000 | ((join-(error-4))//4),
                     0x92800000, 0xd65f03c0)
            result = report(words)['calls'][0]['success_constant']
            self.assertEqual(result['status'], 'constant_register_candidate' if count == 8 else 'declined')
