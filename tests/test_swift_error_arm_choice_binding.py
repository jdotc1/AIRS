"""Keep return choices bound to their complete recorded error arm."""
from copy import deepcopy
import unittest

from airs.swift_error_flow import _return_choice
from test_swift_literal_outcome_summary import report
from test_swift_return_choice_tail_binding import shared_variants
from test_swift_success_entry_choice_tail import direct_variants


def with_error_arm(layout, arm):
    prefix = (0xf10002bf,) if layout.startswith('eq') or layout == 'ne' else ()
    if layout in ('cbnz', 'ne'):
        test = (0xb5000015 if layout == 'cbnz' else 0x54000001) | (3 << 5)
        return (*prefix, test, 0xd2800540, 0x14000000 | (len(arm) + 1), *arm, 0xd65f03c0)
    shared = layout.endswith('shared')
    error = (*arm, 0x14000002) if shared else arm
    test = (0x54000000 if prefix else 0xb4000015) | ((len(error) + 1) << 5)
    return (*prefix, test, *error, *((0xd2800540,) if shared else ()), 0xd65f03c0)


def sync_error_records(call):
    """Keep the three records aligned to isolate encoding/shape inconsistencies."""
    region = call['error_region']
    call['presentation']['display_plan']['error_interval'] = {
        key: deepcopy(region[key]) for key in ('start_pc', 'end_pc_exclusive', 'instructions')}
    tail = [row for row in call['error_constant']['instructions'] if row.get('phase') == 'return_tail']
    call['error_constant']['instructions'] = [
        {'pc': row.get('pc'), 'word': row.get('word'), 'phase': 'error',
         **({'constant_state': 'cleared_after_opaque_call'} if row.get('kind') == 'bl' else {})}
        for row in region['instructions']] + tail


class ErrorArmChoiceBindingFirstTests(unittest.TestCase):
    def test_stale_error_instruction_cannot_supply_a_return_choice(self):
        call = deepcopy(report()['calls'][0])
        call['error_constant']['instructions'][0]['word'] = '0xd503201f'
        self.assertEqual(_return_choice(call)['status'], 'unresolved')


class ErrorArmChoiceBindingBoundaryTests(unittest.TestCase):
    def assert_unresolved(self, call):
        choice = _return_choice(call)
        self.assertEqual(choice['status'], 'unresolved')
        self.assertEqual(choice['reason'], 'outcome_evidence_inconsistent')
        for flag in ('runtime_value_proven', 'source_reconstruction_allowed', 'exclusive_path_proven',
                     'caller_return_type_proven', 'call_return_proven', 'handler_semantics_proven'):
            self.assertIs(choice[flag], False)

    def test_existing_layouts_and_success_outcome_kinds_remain_bound(self):
        for name, words in (*shared_variants(), *direct_variants()):
            with self.subTest(variant=name):
                call = report(words)['calls'][0]; original = deepcopy(call)
                self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
                self.assertEqual(_return_choice(call), call['return_choice'])
                self.assertEqual(call, original)

    def test_literal_widths_movk_copies_and_opaque_call_counts(self):
        arms = ((0xd2800540,), (0x12800000,), (0xd2800540, 0xf2a00020),
                (0x12800000, 0x72a00020), (0xd2800553, 0xaa1303e0),
                (0x92800013, 0x2a1303e0), (0xaa1f03e0,),
                (0x94000100, 0x92800000), (0x94000100, 0x94000100, 0xd2800540))
        for layout in ('cbz_direct', 'eq_direct', 'cbz_shared', 'eq_shared', 'cbnz', 'ne'):
            for arm in arms:
                with self.subTest(layout=layout, arm=arm):
                    call = report(with_error_arm(layout, arm))['calls'][0]
                    self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
                    self.assertEqual(_return_choice(call), call['return_choice'])
                    self.assertEqual(call['error_constant']['opaque_call_count'], arm.count(0x94000100))

    def test_direct_eq_literal_prefix_with_void_callees(self):
        from test_swift_success_result import report as symbol_report
        from test_swift_void_outcomes import NOARG, INTARG
        words = (0xd2800540, *with_error_arm('eq_direct', (0x94000100, 0x92800000)))
        for symbol in (NOARG, INTARG):
            with self.subTest(symbol=symbol):
                call = symbol_report(words, symbol=symbol)['calls'][0]
                self.assertEqual(call['return_choice']['success']['kind'], 'constant_bits')
                self.assertEqual(_return_choice(call), call['return_choice'])

    def test_sixteen_error_rows_and_eight_tail_rows_remain_eligible(self):
        words = with_error_arm('cbz_direct', (0xd503201f,) * 15 + (0x92800000,))
        call = report(words[:-1] + (0xd503201f,) * 7 + (0xd65f03c0,))['calls'][0]
        self.assertEqual(len(call['error_constant']['instructions']), 24)
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
        oversized = deepcopy(call)
        oversized['error_region']['instructions'].append(deepcopy(oversized['error_region']['instructions'][-1]))
        sync_error_records(oversized)
        self.assert_unresolved(oversized)

    def test_displayed_interval_must_match_region_start_end_and_ordered_rows(self):
        original = report()['calls'][0]
        for change in ('start', 'end', 'missing', 'empty', 'word', 'reordered', 'extra', 'none'):
            call = deepcopy(original); interval = call['presentation']['display_plan']['error_interval']
            if change == 'start': interval['start_pc'] = '0x0'
            elif change == 'end': interval['end_pc_exclusive'] = '0x0'
            elif change == 'missing': del interval['instructions']
            elif change == 'empty': interval['instructions'] = []
            elif change == 'word': interval['instructions'][0]['word'] = '0xd503201f'
            elif change == 'reordered': interval['instructions'].reverse()
            elif change == 'extra': interval['extra'] = True
            else: call['presentation']['display_plan']['error_interval'] = None
            with self.subTest(change=change): self.assert_unresolved(call)

    def test_missing_malformed_and_oversized_region_records_refuse(self):
        original = report()['calls'][0]
        rows = original['error_region']['instructions']
        for value in (None, {}, [], tuple(rows), [None], rows * 5):
            call = deepcopy(original); call['error_region']['instructions'] = value
            with self.subTest(rows=value): self.assert_unresolved(call)
        for key in ('instructions', 'start_pc', 'end_pc_exclusive'):
            call = deepcopy(original); del call['error_region'][key]
            with self.subTest(missing=key): self.assert_unresolved(call)

    def test_error_prefix_requires_exact_order_length_phase_and_fields(self):
        original = report()['calls'][0]
        for change in ('missing', 'duplicate', 'reverse', 'phase', 'missing_phase', 'extra', 'pc', 'word', 'none'):
            call = deepcopy(original); rows = call['error_constant']['instructions']
            prefix = [row for row in rows if row['phase'] == 'error']
            tail = [row for row in rows if row['phase'] == 'return_tail']
            if change == 'missing': del prefix[0]
            elif change == 'duplicate': prefix.append(deepcopy(prefix[-1]))
            elif change == 'reverse': prefix.reverse()
            elif change == 'phase': prefix[0]['phase'] = 'success'
            elif change == 'missing_phase': del prefix[0]['phase']
            elif change == 'extra': prefix[0]['extra'] = True
            elif change == 'pc': prefix[0]['pc'] = prefix[-1]['pc']
            elif change == 'word': prefix[0]['word'] = '0xd503201f'
            else: prefix[0] = None
            call['error_constant']['instructions'] = prefix + tail
            with self.subTest(change=change): self.assert_unresolved(call)

    def test_canonical_interval_pc_and_word_records_are_required(self):
        original = report()['calls'][0]
        for change in ('start_type', 'start_case', 'unaligned', 'negative', 'overflow', 'end',
                       'pc_type', 'pc_case', 'gap', 'word_type', 'word_case', 'word_short'):
            call = deepcopy(original); region = call['error_region']; row = region['instructions'][0]
            if change == 'start_type': region['start_pc'] = int(region['start_pc'], 16)
            elif change == 'start_case': region['start_pc'] = '0X' + region['start_pc'][2:]
            elif change == 'unaligned': region['start_pc'] = hex(int(region['start_pc'], 16) + 1)
            elif change == 'negative': region['start_pc'] = '-0x4'
            elif change == 'overflow': region['start_pc'] = hex(1 << 64)
            elif change == 'end': region['end_pc_exclusive'] = hex(int(region['end_pc_exclusive'], 16) + 4)
            elif change == 'pc_type': row['pc'] = int(row['pc'], 16)
            elif change == 'pc_case': row['pc'] = '0X' + row['pc'][2:]
            elif change == 'gap': row['pc'] = hex(int(row['pc'], 16) + 4)
            elif change == 'word_type': row['word'] = int(row['word'], 16)
            elif change == 'word_case': row['word'] = row['word'].upper()
            else: row['word'] = '0x0'
            sync_error_records(call)
            with self.subTest(change=change): self.assert_unresolved(call)

    def test_synchronized_invalid_encodings_kinds_and_exit_targets_refuse(self):
        original = report()['calls'][0]
        for change in ('unknown', 'ret', 'early_b', 'wrong_kind', 'branch_target', 'branch_word', 'extra'):
            call = deepcopy(original); rows = call['error_region']['instructions']
            if change == 'unknown': rows[0]['word'] = '0xffffffff'
            elif change == 'ret': rows[0].update(word='0xd65f03c0', kind='ret')
            elif change == 'early_b': rows[0].update(word='0x14000001', kind='b')
            elif change == 'wrong_kind': rows[0]['kind'] = 'nop'
            elif change == 'branch_target': rows[-1]['target_pc'] = '0x0'
            elif change == 'branch_word': rows[-1]['word'] = '0x14000001'
            else: rows[0]['extra'] = True
            sync_error_records(call)
            with self.subTest(change=change): self.assert_unresolved(call)
        call = report(with_error_arm('cbz_direct', (0x92800000, 0xd503201f)))['calls'][0]
        call['error_region']['instructions'].pop()
        call['error_region']['end_pc_exclusive'] = hex(int(call['error_region']['end_pc_exclusive'], 16) - 4)
        sync_error_records(call)
        self.assert_unresolved(call)

    def test_opaque_call_target_semantics_and_constant_clear_markers_are_bound(self):
        original = report(with_error_arm('cbz_direct', (0x94000100, 0x92800000)))['calls'][0]
        for key, value in (('call_target_pc', '0x0'), ('call_target_pc', 0),
                           ('semantics', 'returned'), ('semantics', None), ('kind', 'nop')):
            call = deepcopy(original); call['error_region']['instructions'][0][key] = value
            sync_error_records(call)
            with self.subTest(key=key, value=value): self.assert_unresolved(call)
        for value in (None, True, 'retained'):
            call = deepcopy(original); call['error_constant']['instructions'][0]['constant_state'] = value
            with self.subTest(clear=value): self.assert_unresolved(call)
        call = deepcopy(original); del call['error_constant']['instructions'][0]['constant_state']
        self.assert_unresolved(call)
        call = deepcopy(original); call['error_constant']['instructions'][1]['constant_state'] = 'cleared_after_opaque_call'
        self.assert_unresolved(call)

    def test_counts_and_region_scope_require_exact_types(self):
        original = report(with_error_arm('cbz_direct', (0x94000100, 0x92800000)))['calls'][0]
        for which in ('error_region', 'error_constant'):
            for value in (None, 0, 2, True, 1.0, '1'):
                call = deepcopy(original); call[which]['opaque_call_count'] = value
                with self.subTest(record=which, count=value): self.assert_unresolved(call)
        for flag in ('call_return_proven', 'join_reachability_proven'):
            for value in (None, 0, True):
                call = deepcopy(original); call['error_region'][flag] = value
                with self.subTest(flag=flag, value=value): self.assert_unresolved(call)
        call = deepcopy(original); call['error_region']['status'] = 'declined'
        self.assert_unresolved(call)

    def test_renderer_withholds_inconsistent_pairs_and_keeps_raw_records(self):
        from airs.swift_error_text import render_swift_error_text
        for name, words in (*shared_variants(), *direct_variants()):
            value = report(words); call = value['calls'][0]
            call['error_constant']['instructions'][0]['word'] = '0xffffffff'
            with self.subTest(variant=name):
                text = render_swift_error_text(value)
                for summary in ('Recorded literal outcomes', 'Recorded call-result/error outcomes',
                                'Recorded adjusted-result/error outcomes'):
                    self.assertNotIn(summary, text)
                self.assertIn('Return choice (structural outcomes; source disabled):', text)
                self.assertIn('Error-constant instruction:', text)
