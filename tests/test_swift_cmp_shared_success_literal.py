"""CMP shared-tail success literals remain selected-path evidence."""
import unittest
from test_swift_cmp_shared_epilogue import report, WORDS


class SharedLiteralFirstTests(unittest.TestCase):
    def test_success_arm_literal_forms_structural_choice(self):
        call = report()['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x0000000000000000')
        self.assertEqual(call['return_choice']['success']['kind'], 'constant_bits')
        self.assertEqual(call['return_choice']['error']['constant_bits'], '0xffffffffffffffff')
        self.assertFalse(call['return_choice']['runtime_value_proven'])
        self.assertFalse(call['return_choice']['source_reconstruction_allowed'])


class SharedLiteralBoundaryTests(unittest.TestCase):
    def test_prefix_literal_is_overwritten_by_success_arm(self):
        call = report((0xd2800540, *WORDS))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x0000000000000000')

    def test_unknown_success_copy_invalidates_prefix_literal(self):
        words = (0xd2800540, *WORDS[:6], 0xaa1403e0, *WORDS[7:])
        call = report(words)['calls'][0]
        self.assertEqual(call['success_constant']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_w_literal_zero_extends_and_movk_updates(self):
        words = (*WORDS[:6], 0x12800000, *WORDS[7:])
        self.assertEqual(report(words)['calls'][0]['success_constant']['constant_bits'], '0x00000000ffffffff')
        words = (0xd2800540, *WORDS[:6], 0xf2a00020, *WORDS[7:])
        self.assertEqual(report(words)['calls'][0]['success_constant']['constant_bits'], '0x000000000001002a')

    def test_unknown_movk_does_not_invent_full_value(self):
        words = (*WORDS[:6], 0xf2a00020, *WORDS[7:])
        call = report(words)['calls'][0]
        self.assertEqual(call['success_constant']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_side_entries_partial_unknown_and_ne_do_not_qualify(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        cases = [report((*WORDS, 0x17fffffb)), report((*WORDS, 0xffffffff)),
                 report((WORDS[0], WORDS[1] | 1, *WORDS[2:])),
                 report(limits=replace(DEFAULT_LIMITS, max_instructions_per_function=12))]
        for value in cases:
            self.assertEqual(value['calls'][0]['return_choice']['status'], 'unresolved')

    def test_wrong_return_or_conflicting_evidence_is_refused(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        original = report()['calls'][0]
        for section, key, value in (('success_constant', 'return_pc', '0x0'),
                                     ('error_constant', 'return_pc', '0x0'),
                                     ('success_constant', 'runtime_value_proven', True)):
            call = deepcopy(original); call[section][key] = value
            self.assertEqual(_return_choice(call)['status'], 'unresolved')
        call = deepcopy(original)
        call['presentation']['display_plan']['condition']['comparison_pc'] = '0x0'
        self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_changed_supported_arm_word_rejects_stale_presentation(self):
        import struct
        from airs.swift_error_flow import _path_constant, _caller_direct_edges
        from test_swift_error_flow import image
        value = image(WORDS); function = value.functions[0]
        call = report()['calls'][0]
        data = bytearray(value.bytes_at(function.start, function.size))
        struct.pack_into('<I', data, 28, 0xd2800540)
        result = _path_constant(bytes(data), function, call, scan=_caller_direct_edges(bytes(data), function))
        self.assertEqual(result['reason'], 'shared_success_evidence_inconsistent')
