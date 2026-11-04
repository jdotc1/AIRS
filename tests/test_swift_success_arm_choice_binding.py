"""Keep shared return choices bound to their complete recorded success arm."""
from copy import deepcopy
import unittest

from airs.swift_error_flow import _return_choice
from test_swift_literal_outcome_summary import report
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_return_choice_tail_binding import selected_outcomes, shared_variants


def sync_success_records(call):
    """Align independent producer formats to isolate malformed shared records."""
    interval = call['error_region']['success_interval']
    call['presentation']['display_plan']['success_interval'] = deepcopy(interval)
    outcome = selected_outcomes(call)[0]
    postcall = [row for row in outcome['instructions'] if row.get('phase') == 'post_call']
    tail = [row for row in outcome['instructions'] if row.get('phase') == 'return_tail']
    outcome['instructions'] = postcall + [
        {'pc': row.get('pc'), 'word': row.get('word'), 'phase': 'success'}
        for row in interval['instructions']] + tail


class SuccessArmChoiceBindingFirstTests(unittest.TestCase):
    def test_stale_success_instruction_cannot_supply_a_literal_choice(self):
        call = deepcopy(report()['calls'][0])
        selected_outcomes(call)[0]['instructions'][0]['word'] = '0xd503201f'
        self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_success_block_cannot_precede_postcall_evidence(self):
        call = report(LAYOUTS[0][1]((0x91001400,)))['calls'][0]
        success = selected_outcomes(call)[0]
        rows = success['instructions']
        postcall = [row for row in rows if row['phase'] == 'post_call']
        arm = [row for row in rows if row['phase'] == 'success']
        tail = [row for row in rows if row['phase'] == 'return_tail']
        success['instructions'] = arm + postcall + tail
        self.assertEqual(_return_choice(call)['status'], 'unresolved')


class SuccessArmChoiceBindingBoundaryTests(unittest.TestCase):
    def assert_unresolved(self, call):
        choice = _return_choice(call)
        self.assertEqual(choice['status'], 'unresolved')
        self.assertEqual(choice['reason'], 'outcome_evidence_inconsistent')
        for key in ('runtime_value_proven', 'source_reconstruction_allowed', 'exclusive_path_proven',
                    'caller_return_type_proven', 'call_return_proven', 'handler_semantics_proven'):
            self.assertIs(choice[key], False)

    def test_all_shared_layouts_bind_literal_preserved_copied_and_adjusted_results(self):
        kinds = {'literal': 'constant_bits', 'preserved': 'call_result', 'copied': 'call_result',
                 'add': 'call_result_add_immediate', 'sub': 'call_result_sub_immediate'}
        for name, words in shared_variants():
            with self.subTest(variant=name):
                call = report(words)['calls'][0]; before = deepcopy(call)
                choice = _return_choice(call)
                result = name.rsplit('_', 1)[1]
                self.assertEqual(choice['status'], 'structural_choice_candidate')
                self.assertEqual(choice['success']['kind'], kinds[result])
                if result == 'literal':
                    self.assertEqual(choice['success']['constant_bits'], '0x000000000000002a')
                elif result in ('preserved', 'copied'):
                    self.assertEqual(choice['success']['candidate_status'], result + '_register_candidate')
                else:
                    self.assertEqual(choice['success']['immediate'], 5 if result == 'add' else 4096)
                self.assertEqual(call, before)

    def test_literal_widths_movk_copies_and_zero_register_remain_eligible(self):
        cases = (((0x92800000,), '0xffffffffffffffff'),
                 ((0x12800000,), '0x00000000ffffffff'),
                 ((0xd2800540, 0xf2a00020), '0x000000000001002a'),
                 ((0x12800000, 0x72a00020), '0x000000000001ffff'),
                 ((0xd2800553, 0xaa1303e0), '0x000000000000002a'),
                 ((0x92800013, 0x2a1303e0), '0x00000000ffffffff'),
                 ((0xaa1f03e0,), '0x0000000000000000'))
        for name, layout in LAYOUTS:
            for arm, expected in cases:
                with self.subTest(layout=name, arm=arm):
                    choice = report(layout(arm))['calls'][0]['return_choice']
                    self.assertEqual(choice['status'], 'structural_choice_candidate')
                    self.assertEqual(choice['success']['constant_bits'], expected)

    def test_eight_word_bound_and_forward_branch_only_arm(self):
        for name, layout in LAYOUTS:
            arm = (0xd503201f,) * (7 if name in ('ne', 'cbnz') else 8)
            call = report(layout(arm))['calls'][0]
            with self.subTest(layout=name):
                self.assertEqual(len(call['error_region']['success_interval']['instructions']), 8)
                self.assertEqual(_return_choice(call)['success']['kind'], 'call_result')
                oversized = deepcopy(call)
                oversized['error_region']['success_interval']['instructions'].append(
                    deepcopy(oversized['error_region']['success_interval']['instructions'][-1]))
                sync_success_records(oversized)
                self.assert_unresolved(oversized)
                if name in ('ne', 'cbnz'):
                    single = report(layout(()))['calls'][0]
                    self.assertEqual(len(single['error_region']['success_interval']['instructions']), 1)
                    self.assertEqual(_return_choice(single)['success']['kind'], 'call_result')

    def test_direct_success_entry_controls_keep_their_existing_outcomes(self):
        from test_swift_success_entry_choice_tail import direct_variants
        for name, words in direct_variants():
            with self.subTest(variant=name):
                call = report(words)['calls'][0]
                self.assertNotIn('shared_epilogue', call['error_region'])
                self.assertEqual(_return_choice(call)['status'], 'structural_choice_candidate')

    def test_presentation_must_retain_the_exact_success_interval(self):
        original = report()['calls'][0]
        for change in ('start', 'end', 'word', 'missing', 'extra', 'none', 'list'):
            call = deepcopy(original)
            interval = call['presentation']['display_plan']['success_interval']
            if change == 'start': interval['start_pc'] = '0x0'
            elif change == 'end': interval['end_pc_exclusive'] = '0x0'
            elif change == 'word': interval['instructions'][0]['word'] = '0xd503201f'
            elif change == 'missing': del interval['instructions']
            elif change == 'extra': interval['extra'] = True
            else: call['presentation']['display_plan']['success_interval'] = None if change == 'none' else []
            with self.subTest(change=change): self.assert_unresolved(call)

    def test_missing_malformed_or_extra_interval_fields_refuse(self):
        original = report()['calls'][0]
        for value in (None, [], {}, 'interval'):
            call = deepcopy(original); call['error_region']['success_interval'] = value
            with self.subTest(interval=value): self.assert_unresolved(call)
        for value in (None, {}, [], (), [None]):
            call = deepcopy(original); call['error_region']['success_interval']['instructions'] = value
            with self.subTest(rows=value): self.assert_unresolved(call)
        for key in ('start_pc', 'end_pc_exclusive', 'instructions'):
            call = deepcopy(original); del call['error_region']['success_interval'][key]
            with self.subTest(missing=key): self.assert_unresolved(call)
        call = deepcopy(original)
        call['error_region']['success_interval']['instructions_complete'] = True
        sync_success_records(call)
        self.assert_unresolved(call)

    def test_interval_pc_and_word_records_require_canonical_contiguity(self):
        original = report(LAYOUTS[0][1]((0xd503201f, 0xd2800540)))['calls'][0]
        for change in ('start_type', 'start_case', 'unaligned', 'negative', 'overflow', 'wrong_start',
                       'end', 'gap', 'pc_type', 'pc_case', 'word_type', 'word_case', 'word_short'):
            call = deepcopy(original); interval = call['error_region']['success_interval']
            row = interval['instructions'][0]
            if change == 'start_type': interval['start_pc'] = int(interval['start_pc'], 16)
            elif change == 'start_case': interval['start_pc'] = interval['start_pc'].upper()
            elif change == 'unaligned': interval['start_pc'] = hex(int(interval['start_pc'], 16) + 1)
            elif change == 'negative': interval['start_pc'] = '-0x4'
            elif change == 'overflow': interval['start_pc'] = hex(1 << 64)
            elif change == 'wrong_start': interval['start_pc'] = hex(int(interval['start_pc'], 16) + 4)
            elif change == 'end': interval['end_pc_exclusive'] = hex(int(interval['end_pc_exclusive'], 16) + 4)
            elif change == 'gap': row['pc'] = interval['instructions'][1]['pc']
            elif change == 'pc_type': row['pc'] = int(row['pc'], 16)
            elif change == 'pc_case': row['pc'] = row['pc'].upper()
            elif change == 'word_type': row['word'] = int(row['word'], 16)
            elif change == 'word_case': row['word'] = row['word'].upper()
            else: row['word'] = '0x0'
            sync_success_records(call)
            with self.subTest(change=change): self.assert_unresolved(call)

    def test_success_outcome_block_requires_exact_rows_order_and_phases(self):
        for name, layout in LAYOUTS:
            original = report(layout((0xd503201f, 0xd2800540)))['calls'][0]
            for change in ('missing', 'duplicate', 'reverse', 'phase', 'missing_phase', 'extra',
                           'pc', 'word', 'interrupt', 'earlier_success', 'none'):
                call = deepcopy(original); success = selected_outcomes(call)[0]
                before = [row for row in success['instructions'] if row['phase'] == 'post_call']
                arm = [row for row in success['instructions'] if row['phase'] == 'success']
                tail = [row for row in success['instructions'] if row['phase'] == 'return_tail']
                if change == 'missing': del arm[0]
                elif change == 'duplicate': arm.append(deepcopy(arm[-1]))
                elif change == 'reverse': arm.reverse()
                elif change == 'phase': arm[0]['phase'] = 'post_call'
                elif change == 'missing_phase': del arm[0]['phase']
                elif change == 'extra': arm[0]['kind'] = 'nop'
                elif change == 'pc': arm[0]['pc'] = arm[-1]['pc']
                elif change == 'word': arm[0]['word'] = '0xd2800020'
                elif change == 'interrupt': arm.insert(1, {**arm[0], 'phase': 'post_call'})
                elif change == 'earlier_success': before.insert(0, deepcopy(arm[0]))
                else: arm[0] = None
                success['instructions'] = before + arm + tail
                with self.subTest(layout=name, change=change): self.assert_unresolved(call)

    def test_noncomparison_literal_cannot_gain_a_postcall_prefix(self):
        for name, layout in LAYOUTS:
            if name not in ('cbz', 'cbnz'): continue
            call = report(layout((0xd2800540,)))['calls'][0]
            outcome = selected_outcomes(call)[0]
            outcome['instructions'].insert(0, {**outcome['instructions'][0], 'phase': 'post_call'})
            with self.subTest(layout=name): self.assert_unresolved(call)

    def test_forward_interval_completeness_is_exact_boolean_in_both_records(self):
        for name, layout in LAYOUTS:
            if name not in ('cbnz', 'ne'): continue
            original = report(layout((0xd2800540,)))['calls'][0]
            for source in ('region', 'presentation', 'both'):
                for value in (False, None, 1, 1.0, 'true', 'missing'):
                    call = deepcopy(original)
                    intervals = (call['error_region']['success_interval'],
                                 call['presentation']['display_plan']['success_interval'])
                    for interval in (intervals if source == 'both' else (intervals[source == 'presentation'],)):
                        if value == 'missing': del interval['instructions_complete']
                        else: interval['instructions_complete'] = value
                    with self.subTest(layout=name, source=source, value=value): self.assert_unresolved(call)

    def test_forward_terminal_branch_word_target_and_position_must_agree(self):
        for name, layout in LAYOUTS:
            if name not in ('cbnz', 'ne'): continue
            original = report(layout((0xd503201f, 0xd2800540)))['calls'][0]
            for change in ('target', 'word', 'missing_target', 'early_branch', 'fallthrough', 'extra'):
                call = deepcopy(original); rows = call['error_region']['success_interval']['instructions']
                if change == 'target': rows[-1]['target_pc'] = call['error_pc']
                elif change == 'word': rows[-1]['word'] = '0x14000001'
                elif change == 'missing_target': del rows[-1]['target_pc']
                elif change == 'early_branch': rows[0].update(word='0x14000001', kind='b', target_pc=rows[1]['pc'])
                elif change == 'fallthrough': rows[-1] = {**rows[-1], 'word': '0xd503201f', 'kind': 'nop'}
                else: rows[-1]['extra'] = True
                sync_success_records(call)
                with self.subTest(layout=name, change=change): self.assert_unresolved(call)

    def test_synchronized_unsupported_words_and_kinds_do_not_create_choices(self):
        original = report()['calls'][0]
        for word, kind in (('0xffffffff', 'unclassified'), ('0xd65f03c0', 'ret'),
                           ('0x94000001', 'bl'), ('0x14000001', 'b'),
                           ('0xd503201f', 'movz'), ('0x91001400', 'add')):
            call = deepcopy(original)
            call['error_region']['success_interval']['instructions'][0].update(word=word, kind=kind)
            sync_success_records(call)
            with self.subTest(word=word, kind=kind): self.assert_unresolved(call)

    def test_arithmetic_arm_retains_single_operation_and_operand_limits(self):
        for name, layout in LAYOUTS:
            original = report(layout((0xd503201f, 0x91001400)))['calls'][0]
            for word, kind in (('0x91001400', 'add'), ('0xd2800020', 'movz'),
                               ('0x11001400', 'wadd'), ('0xb1001400', 'adds'),
                               ('0x910017e0', 'add'), ('0x91000000', 'add')):
                call = deepcopy(original)
                call['error_region']['success_interval']['instructions'][0].update(word=word, kind=kind)
                sync_success_records(call)
                with self.subTest(layout=name, word=word): self.assert_unresolved(call)

    def test_renderer_withholds_stale_pairs_and_retains_raw_evidence(self):
        from airs.swift_error_text import render_swift_error_text
        for name, layout in LAYOUTS:
            for arm, label in (((0xd2800540,), 'Recorded literal outcomes'),
                               ((0xd503201f,), 'Recorded call-result/error outcomes'),
                               ((0x91001400,), 'Recorded adjusted-result/error outcomes')):
                value = report(layout(arm)); call = value['calls'][0]
                self.assertIn(label, render_swift_error_text(value))
                next(row for row in selected_outcomes(call)[0]['instructions']
                     if row['phase'] == 'success')['word'] = '0xd2800020'
                text = render_swift_error_text(value)
                with self.subTest(layout=name, arm=arm):
                    self.assertNotIn(label, text)
                    self.assertIn('Error-constant instruction:', text)
                    self.assertIn('0xd2800020', text)
