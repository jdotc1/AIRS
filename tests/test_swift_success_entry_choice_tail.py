"""Bind direct success-entry choices to matching recorded return tails."""
from copy import deepcopy
import unittest

from airs.swift_error_flow import _return_choice
from test_swift_literal_outcome_summary import report
from test_swift_preserved_result_binding import DIRECT, DIRECT_EQ, SAVE, CLEAR, RESTORE
from test_swift_return_choice_tail_binding import selected_outcomes


def direct_variants():
    for name, words in (('cbz', DIRECT), ('eq', DIRECT_EQ)):
        yield name + '_preserved', words
        yield name + '_copied', (SAVE, CLEAR, RESTORE, *words)
    from test_swift_cmp_success_literals import WORDS
    yield 'eq_literal', (*WORDS, 0xd65f03c0)


def replace_tail_records(call, tail):
    for outcome in selected_outcomes(call):
        prefix = [row for row in outcome['instructions'] if row['phase'] != 'return_tail']
        outcome['instructions'] = prefix + [{**row, 'phase': 'return_tail'} for row in tail]


class SuccessEntryChoiceTailFirstTests(unittest.TestCase):
    def test_stale_error_tail_cannot_supply_a_direct_return_choice(self):
        call = deepcopy(report(DIRECT)['calls'][0])
        call['error_constant']['instructions'][-1]['word'] = '0xd65f0000'
        self.assertEqual(_return_choice(call)['status'], 'unresolved')


class SuccessEntryChoiceTailBoundaryTests(unittest.TestCase):
    def assert_unresolved(self, call):
        choice = _return_choice(call)
        self.assertEqual(choice['status'], 'unresolved')
        self.assertEqual(choice['reason'], 'outcome_evidence_inconsistent')
        for key in ('runtime_value_proven', 'source_reconstruction_allowed', 'exclusive_path_proven',
                    'caller_return_type_proven', 'call_return_proven', 'handler_semantics_proven'):
            self.assertIs(choice[key], False)

    def test_direct_preserved_copied_and_literal_outcomes_remain_bound(self):
        for name, words in direct_variants():
            with self.subTest(variant=name):
                call = report(words)['calls'][0]; original = deepcopy(call)
                self.assertNotIn('shared_epilogue', call['error_region'])
                self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
                self.assertEqual(call['success_pc'], call['error_region']['join_pc'])
                self.assertEqual(_return_choice(call), call['return_choice'])
                self.assertEqual(call, original)

    def test_eq_literal_prefix_widths_copies_movk_and_void_callees_remain_supported(self):
        from test_swift_cmp_success_literals import WORDS
        from test_swift_success_result import report as symbol_report
        from test_swift_void_outcomes import NOARG, INTARG
        from test_swift_error_flow import SYMBOL
        prefixes = (((0xd2800540,), '0x000000000000002a'),
                    ((0x12800000,), '0x00000000ffffffff'),
                    ((0xd2800540, 0xf2a00020), '0x000000000001002a'),
                    ((0x12800000, 0x72a00020), '0x000000000001ffff'),
                    ((0xd2800553, 0xaa1303e0), '0x000000000000002a'),
                    ((0x92800013, 0x2a1303e0), '0x00000000ffffffff'))
        for prefix, bits in prefixes:
            for symbol in (SYMBOL, NOARG, INTARG):
                with self.subTest(prefix=prefix, symbol=symbol):
                    call = symbol_report((*prefix, *WORDS[1:], 0xd65f03c0), symbol=symbol)['calls'][0]
                    self.assertEqual(call['return_choice']['success']['constant_bits'], bits)
                    self.assertEqual(_return_choice(call), call['return_choice'])
                    self.assertEqual(call['success_constant']['instructions'][0]['phase'], 'post_call')

    def test_existing_tail_families_and_eight_word_limit(self):
        from test_swift_scalar_restore_tail import load
        from test_swift_postindexed_scalar_tail import pop
        from test_swift_postindexed_epilogue import pop_word
        from test_swift_split_frame_tail import TAIL
        tails = ((0xd65f03c0,), (0xd503201f,) * 7 + (0xd65f03c0,),
                 (0xa9427bfd, 0x9100c3ff, 0xd65f03c0),
                 (load(19), load(30, 8), 0xd65f03c0), (pop(), 0xd65f03c0),
                 (pop_word(), 0xd65f03c0), (0x910003bf, pop_word(), 0xd65f03c0), TAIL)
        for name, words in direct_variants():
            for tail in tails:
                with self.subTest(variant=name, tail=tail):
                    call = report(words[:-1] + tail)['calls'][0]
                    self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
                    self.assertEqual(_return_choice(call), call['return_choice'])

    def test_join_success_and_return_addresses_must_match_actual_tail(self):
        for name, words in direct_variants():
            original = report(words)['calls'][0]
            for change in ('join', 'success', 'both_returns', 'success_return', 'error_return',
                           'join_type', 'join_format', 'join_unaligned', 'join_overflow'):
                call = deepcopy(original); success, error = selected_outcomes(call)
                if change == 'join': call['error_region']['join_pc'] = '0x0'
                elif change == 'success':
                    call['success_pc'] = success['success_pc'] = call['presentation']['display_plan']['success_entry_pc'] = '0x0'
                elif change == 'both_returns': success['return_pc'] = error['return_pc'] = '0x0'
                elif change in ('success_return', 'error_return'):
                    (success if change == 'success_return' else error)['return_pc'] = '0x0'
                else:
                    original_join = call['error_region']['join_pc']
                    changed = (int(original_join, 16) if change == 'join_type' else
                               '0X' + original_join[2:] if change == 'join_format' else
                               hex(int(original_join, 16) + 1) if change == 'join_unaligned' else hex(1 << 64))
                    call['error_region']['join_pc'] = call['success_pc'] = success['success_pc'] = changed
                    call['presentation']['display_plan']['success_entry_pc'] = changed
                with self.subTest(variant=name, change=change): self.assert_unresolved(call)

    def test_foreign_presentation_tail_and_layout_do_not_change_direct_eligibility(self):
        for name, words in direct_variants():
            original = report(words)['calls'][0]
            for value in (None, {}, {'instructions': []}):
                call = deepcopy(original); call['presentation']['display_plan']['shared_epilogue'] = value
                with self.subTest(variant=name, presentation=value): self.assert_unresolved(call)
            for layout in ('shared_epilogue', 'foreign', None):
                call = deepcopy(original); selected_outcomes(call)[0]['return_tail_layout'] = layout
                with self.subTest(variant=name, layout=layout): self.assert_unresolved(call)

    def test_empty_malformed_oversized_and_incomplete_captured_tails_refuse(self):
        original = report(DIRECT[:-1] + (0xd503201f, 0xd65f03c0))['calls'][0]
        for which in (0, 1):
            for change in ('empty', 'none', 'tuple', 'nondict', 'missing', 'nine_tail', 'oversized'):
                call = deepcopy(original); outcome = selected_outcomes(call)[which]; rows = outcome['instructions']
                if change == 'empty': outcome['instructions'] = []
                elif change == 'none': outcome['instructions'] = None
                elif change == 'tuple': outcome['instructions'] = tuple(rows)
                elif change == 'nondict': rows[-1] = None
                elif change == 'missing': del rows[-1]
                elif change == 'nine_tail': rows.extend([deepcopy(rows[-1])] * 7)
                else: outcome['instructions'] = [{'phase': 'post_call'}] * 25 + rows
                with self.subTest(outcome=which, change=change): self.assert_unresolved(call)

    def test_captured_tail_is_final_contiguous_ordered_and_identical_on_both_paths(self):
        for name, words in direct_variants():
            original = report(words[:-1] + (0xd503201f, 0xd65f03c0))['calls'][0]
            for which in (0, 1):
                for change in ('front', 'interleaved', 'duplicate', 'reordered', 'word', 'kind', 'extra'):
                    call = deepcopy(original); outcome = selected_outcomes(call)[which]
                    prefix = [row for row in outcome['instructions'] if row['phase'] != 'return_tail']
                    tail = [row for row in outcome['instructions'] if row['phase'] == 'return_tail']
                    if change == 'front': outcome['instructions'] = tail + prefix
                    elif change == 'interleaved': outcome['instructions'] = prefix[:-1] + tail[:1] + prefix[-1:] + tail[1:]
                    elif change == 'duplicate': outcome['instructions'].append(deepcopy(tail[-1]))
                    elif change == 'reordered': outcome['instructions'] = prefix + list(reversed(tail))
                    elif change == 'word': tail[0]['word'] = '0xd65f03c0'
                    elif change == 'kind': tail[0]['kind'] = 'ret'
                    else: tail[0]['extra'] = True
                    with self.subTest(variant=name, outcome=which, change=change): self.assert_unresolved(call)

    def test_matching_invalid_encodings_pc_sequences_and_metadata_types_refuse(self):
        original = report(DIRECT[:-1] + (0xd503201f, 0xd65f03c0))['calls'][0]
        for change in ('unknown', 'word_type', 'short_word', 'early_ret', 'wrong_ret', 'kind', 'pc_gap', 'pc_type'):
            call = deepcopy(original)
            rows = [{key: value for key, value in row.items() if key != 'phase'}
                    for row in selected_outcomes(call)[0]['instructions'] if row['phase'] == 'return_tail']
            if change == 'unknown': rows[0]['word'] = '0xffffffff'
            elif change == 'word_type': rows[0]['word'] = 0xd503201f
            elif change == 'short_word': rows[0]['word'] = '0x0'
            elif change == 'early_ret': rows[0].update(word='0xd65f03c0', kind='ret')
            elif change == 'wrong_ret': rows[-1]['word'] = '0xd65f0000'
            elif change == 'kind': rows[-1]['kind'] = 'nop'
            elif change == 'pc_gap': rows[-1]['pc'] = rows[0]['pc']
            else: rows[0]['pc'] = int(rows[0]['pc'], 16)
            replace_tail_records(call, rows)
            with self.subTest(change=change): self.assert_unresolved(call)
        from test_swift_postindexed_scalar_tail import pop
        original = report(DIRECT[:-1] + (pop(), 0xd65f03c0))['calls'][0]
        for value in (32, 16.0, True, None):
            call = deepcopy(original)
            rows = [{key: item for key, item in row.items() if key != 'phase'}
                    for row in selected_outcomes(call)[0]['instructions'] if row['phase'] == 'return_tail']
            rows[0]['sp_writeback_bytes'] = value
            replace_tail_records(call, rows)
            with self.subTest(writeback=value): self.assert_unresolved(call)

    def test_exact_outcome_row_limit_and_proof_scopes_are_preserved(self):
        words = (0xb4000235,) + (0xd503201f,) * 15 + (0x92800000,) + (0xd503201f,) * 7 + (0xd65f03c0,)
        original = report(words)['calls'][0]
        self.assertEqual(len(original['error_constant']['instructions']), 24)
        self.assertEqual(original['return_choice']['status'], 'structural_choice_candidate')
        for which in (0, 1):
            for flag in ('runtime_value_proven', 'source_reconstruction_allowed', 'exclusive_path_proven', 'caller_return_type_proven'):
                for value in (True, 0, None):
                    call = deepcopy(original); selected_outcomes(call)[which][flag] = value
                    with self.subTest(outcome=which, flag=flag, value=value): self.assert_unresolved(call)

    def test_shared_choice_format_is_preserved_by_common_tail_validation(self):
        from test_swift_return_choice_tail_binding import shared_variants
        for name, words in shared_variants():
            with self.subTest(variant=name):
                call = report(words)['calls'][0]
                self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
                self.assertEqual(_return_choice(call), call['return_choice'])

    def test_renderer_withholds_stale_direct_tail_pair_but_retains_raw_evidence(self):
        from airs.swift_error_text import render_swift_error_text
        for name, words in direct_variants():
            value = report(words); call = value['calls'][0]
            selected_outcomes(call)[1]['instructions'][-1]['word'] = '0xd65f0000'
            with self.subTest(variant=name):
                text = render_swift_error_text(value)
                self.assertNotIn('Recorded literal outcomes', text)
                self.assertNotIn('Recorded call-result/error outcomes', text)
                self.assertIn('Return choice (structural outcomes; source disabled):', text)
                self.assertIn('Error-constant instruction:', text)

    def test_cli_exposes_current_model_and_keeps_unsupported_tail_unresolved(self):
        import contextlib, io, json
        from pathlib import Path
        from airs.cli import main
        from test_swift_error_flow import image
        from fixture_storage import temporary_directory
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            for name, words, expected in (('valid', DIRECT, True),
                                           ('invalid', DIRECT[:-1] + (0xd65f0000,), False)):
                source = Path(folder) / (name + '.macho'); source.write_bytes(image(words).data)
                for format in ('json', 'text'):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        status = main(['swift-error-flow', str(source), '--include-error-regions',
                            '--validate-region-entries', '--include-structured-presentation', '--format', format])
                    self.assertEqual(status, 0)
                    with self.subTest(name=name, format=format):
                        if format == 'json':
                            value = json.loads(output.getvalue())
                            self.assertEqual(value['return_choice_model_version'], 'swift-return-choice-v35')
                            self.assertEqual(value['calls'][0]['return_choice']['status'] == 'structural_choice_candidate', expected)
                        else:
                            self.assertIn('swift-return-choice-v35', output.getvalue())
                            self.assertEqual('Recorded call-result/error outcomes' in output.getvalue(), expected)
                            self.assertIn('Source reconstruction: disabled', output.getvalue())
