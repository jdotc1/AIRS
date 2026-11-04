"""Bound recorded success prefixes to the post-call edge window."""
from copy import deepcopy
import unittest

from airs.swift_error_flow import _return_choice, _bind_choice_postcall
from test_swift_literal_outcome_summary import report
from test_swift_return_choice_tail_binding import shared_variants, selected_outcomes
from test_swift_success_entry_choice_tail import direct_variants


class PostcallWindowBindingTests(unittest.TestCase):
    def calls(self):
        for name, words in list(shared_variants()) + list(direct_variants()):
            yield name, report(words)['calls'][0]

    def test_supported_shared_and_direct_choices_are_preserved(self):
        for name, call in self.calls():
            with self.subTest(name=name):
                before = deepcopy(call)
                self.assertEqual(_return_choice(call)['status'], 'structural_choice_candidate')
                self.assertEqual(call, before)

    def test_stale_missing_extra_and_reordered_captured_prefix_refuses(self):
        for name, original in self.calls():
            success = selected_outcomes(original)[0]
            if not any(row['phase'] == 'post_call' for row in success['instructions']):
                continue
            for mutation in ('stale', 'missing', 'extra', 'reordered'):
                with self.subTest(name=name, mutation=mutation):
                    call = deepcopy(original); rows = selected_outcomes(call)[0]['instructions']
                    post = [i for i, row in enumerate(rows) if row['phase'] == 'post_call']
                    if mutation == 'stale': rows[post[0]]['word'] = ('0xd503201f' if rows[post[0]]['word'] != '0xd503201f' else '0xd503203f')
                    elif mutation == 'missing': rows.pop(post[0])
                    elif mutation == 'extra': rows.insert(post[0], deepcopy(rows[post[0]]))
                    elif len(post) > 1: rows[post[0]], rows[post[-1]] = rows[post[-1]], rows[post[0]]
                    else: continue
                    self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_window_and_edge_tampering_refuses_without_mutating_input(self):
        for name, original in self.calls():
            for key, value in (('word', '0xd503201f'), ('pc', '0x0'), ('kind', 'nop'), ('word', 0), ('extra', True)):
                with self.subTest(name=name, key=key, value=value):
                    call = deepcopy(original); call['window'][-1][key] = value
                    before = deepcopy(call)
                    self.assertEqual(_return_choice(call)['status'], 'unresolved')
                    self.assertEqual(call, before)
            for key, value in (('window', []), ('window', None), ('tested_register', 'x0'), ('test_pc', '0x0'), ('error_pc', '0x0')):
                with self.subTest(name=name, field=key):
                    call = deepcopy(original); call[key] = value
                    self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_noncompare_literal_does_not_require_a_captured_prefix(self):
        choices = [(n, c) for n, c in self.calls() if n in ('cbz_literal', 'cbnz_literal')]
        self.assertEqual(len(choices), 2)
        for name, call in choices:
            with self.subTest(name=name):
                self.assertFalse(any(row['phase'] == 'post_call' for row in selected_outcomes(call)[0]['instructions']))
                self.assertEqual(_return_choice(call)['status'], 'structural_choice_candidate')

    def test_last_aligned_successor_address_accepts_exclusive_64_bit_end(self):
        call = report(dict(direct_variants())['cbz_preserved'])['calls'][0]
        success = selected_outcomes(call)[0]
        delta = (1 << 64) - 4 - max(int(call['success_pc'], 16), int(call['error_pc'], 16))
        for key in ('call_pc', 'test_pc', 'success_pc', 'error_pc'):
            call[key] = hex(int(call[key], 16) + delta)
        for row in call['window']:
            row['pc'] = hex(int(row['pc'], 16) + delta)
        for row in success['instructions']:
            if row['phase'] == 'post_call':
                row['pc'] = hex(int(row['pc'], 16) + delta)
        tail_count = sum(row['phase'] == 'return_tail' for row in success['instructions'])
        _bind_choice_postcall(call, success, tail_count, 0)
