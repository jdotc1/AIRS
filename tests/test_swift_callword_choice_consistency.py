"""Bind return choices to their recorded call-site BL encoding."""
from copy import deepcopy
import unittest
from airs.swift_error_flow import _return_choice, _bind_choice_call_word
from test_swift_literal_outcome_summary import report
from test_swift_return_choice_tail_binding import shared_variants
from test_swift_success_entry_choice_tail import direct_variants

class CallWordChoiceConsistencyTests(unittest.TestCase):
    def cases(self):
        for name, words in list(shared_variants()) + list(direct_variants()):
            yield name, report(words)['calls'][0]

    def test_supported_direct_and_shared_choices_remain_eligible(self):
        for name, call in self.cases():
            with self.subTest(name=name):
                before = deepcopy(call)
                self.assertEqual(_return_choice(call)['status'], 'structural_choice_candidate')
                self.assertEqual(call, before)

    def test_call_encoding_and_target_changes_withhold_choice(self):
        for name, original in self.cases():
            other = '0x94000001' if original['call_word'] != '0x94000001' else '0x94000002'
            for value in ('0xd503201f', '0xd65f03c0', other, None, 0, '0X94000001', '0x9400000A', '0x0'):
                with self.subTest(name=name, value=value):
                    call = deepcopy(original); call['call_word'] = value
                    result = _return_choice(call)
                    self.assertEqual(result['reason'], 'outcome_evidence_inconsistent')
                    self.assertFalse(result['runtime_value_proven'])
            call = deepcopy(original); del call['call_word']
            self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_noncanonical_invalid_and_overflow_addresses_refuse(self):
        original = report()['calls'][0]
        for key, value in (('call_pc', None), ('call_pc', '0x00'), ('call_pc', '-0x4'),
                           ('call_pc', '0x10000000000000000'), ('call_pc', '0x1'),
                           ('callee_pc', None), ('callee_pc', '0x00'), ('callee_pc', '-0x4'),
                           ('callee_pc', '0x10000000000000000'), ('callee_pc', '0x1')):
            with self.subTest(key=key, value=value):
                call = deepcopy(original); call[key] = value
                self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_signed_target_bounds_without_image_access(self):
        _bind_choice_call_word({'call_pc': '0x4', 'call_word': '0x97ffffff', 'callee_pc': '0x0'})
        for call in ({'call_pc': '0x0', 'call_word': '0x97ffffff', 'callee_pc': '0x0'},
                     {'call_pc': '0xfffffffffffffffc', 'call_word': '0x94000001', 'callee_pc': '0x0'}):
            with self.subTest(call=call):
                with self.assertRaises(ValueError): _bind_choice_call_word(call)

    def test_renderer_withholds_stale_call_pair_and_retains_raw_evidence(self):
        from airs.swift_error_text import render_swift_error_text
        value = report()
        self.assertIn('Recorded literal outcomes', render_swift_error_text(value))
        value['calls'][0]['call_word'] = '0xd503201f'
        text = render_swift_error_text(value)
        self.assertNotIn('Recorded literal outcomes', text)
        self.assertNotIn('Recorded call-result/error outcomes', text)
        self.assertNotIn('Recorded adjusted-result/error outcomes', text)
        self.assertIn('Error-constant instruction:', text)
