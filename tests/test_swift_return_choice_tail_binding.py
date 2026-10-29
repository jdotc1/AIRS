"""Bind shared-tail choices to the same bounded recorded return evidence."""
from copy import deepcopy
import unittest

from airs.swift_error_flow import _return_choice
from test_swift_literal_outcome_summary import report
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_shared_epilogue import WORDS


def shared_variants():
    for name, layout in LAYOUTS:
        for result, prefix, arm in (
                ('literal', (), (0xd2800540,)), ('preserved', (), (0xd503201f,)),
                ('copied', (0xaa0003f3, 0xaa1f03e0), (0xaa1303e0,)),
                ('add', (), (0x91001400,)), ('sub', (), (0xd1400400,))):
            yield name + '_' + result, prefix + layout(arm)


def selected_outcomes(call):
    success = (call['success_constant'] if call['success_constant']['status'] == 'constant_register_candidate'
               else call['success_result'])
    return success, call['error_constant']


def synchronize_tail(call, tail):
    """Align records so tests isolate malformed encodings instead of disagreement."""
    call['error_region']['shared_epilogue'] = deepcopy(tail)
    call['presentation']['display_plan']['shared_epilogue'] = deepcopy(tail)
    for outcome in selected_outcomes(call):
        outcome['instructions'] = [row for row in outcome['instructions'] if row['phase'] != 'return_tail']
        outcome['instructions'].extend({**row, 'phase': 'return_tail'} for row in tail['instructions'])


class ReturnChoiceTailBindingFirstTests(unittest.TestCase):
    def test_stale_presentation_tail_cannot_supply_a_return_choice(self):
        call = deepcopy(report()['calls'][0])
        call['presentation']['display_plan']['shared_epilogue']['instructions'][0]['word'] = '0xd503201f'
        self.assertEqual(_return_choice(call)['status'], 'unresolved')


class ReturnChoiceTailOrderingTests(unittest.TestCase):
    def test_tail_must_be_a_final_contiguous_block_in_each_outcome(self):
        for name, words in shared_variants():
            original = report(words)['calls'][0]
            for which in (0, 1):
                for ordering in ('front', 'interleaved'):
                    call = deepcopy(original); outcome = selected_outcomes(call)[which]
                    prefix = [row for row in outcome['instructions'] if row['phase'] != 'return_tail']
                    tail = [row for row in outcome['instructions'] if row['phase'] == 'return_tail']
                    outcome['instructions'] = (tail + prefix if ordering == 'front'
                                               else prefix[:-1] + tail[:1] + prefix[-1:] + tail[1:])
                    with self.subTest(variant=name, outcome=which, ordering=ordering):
                        self.assertEqual(_return_choice(call)['status'], 'unresolved')


class ReturnChoiceTailBindingBoundaryTests(unittest.TestCase):
    def assert_unresolved(self, call):
        choice = _return_choice(call)
        self.assertEqual(choice['status'], 'unresolved')
        self.assertEqual(choice['reason'], 'outcome_evidence_inconsistent')
        for flag in ('source_reconstruction_allowed', 'runtime_value_proven', 'exclusive_path_proven',
                     'caller_return_type_proven', 'call_return_proven', 'handler_semantics_proven'):
            self.assertIs(choice[flag], False)

    def test_all_existing_shared_layouts_and_outcome_kinds_remain_bound(self):
        for name, words in shared_variants():
            with self.subTest(variant=name):
                call = report(words)['calls'][0]
                self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
                original = deepcopy(call)
                self.assertEqual(_return_choice(call), call['return_choice'])
                self.assertEqual(call, original)
                for outcome in selected_outcomes(call):
                    self.assertEqual(outcome['return_pc'], call['return_choice']['return_pc'])

    def test_existing_restore_shapes_and_eight_word_boundary_remain_eligible(self):
        from test_swift_scalar_restore_tail import load
        from test_swift_postindexed_scalar_tail import pop
        from test_swift_postindexed_epilogue import pop_word
        from test_swift_split_frame_tail import TAIL
        tails = ((0xd65f03c0,), (0xd503201f,) * 7 + (0xd65f03c0,),
                 (0xa9427bfd, 0x9100c3ff, 0xd65f03c0),
                 (load(19), load(30, 8), 0xd65f03c0), (pop(), 0xd65f03c0),
                 (pop_word(), 0xd65f03c0), (0x910003bf, pop_word(), 0xd65f03c0), TAIL)
        for tail in tails:
            with self.subTest(tail=tail):
                call = report(WORDS[:5] + (0xd503201f,) + tail)['calls'][0]
                self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
                self.assertEqual(_return_choice(call), call['return_choice'])
                self.assertIs(call['error_region']['shared_epilogue']['restore_state_proven'], False)

    def test_missing_mismatched_and_proven_presentation_tails_refuse(self):
        original = report()['calls'][0]
        for change in ('missing', 'word', 'end', 'true', 'integer_false'):
            call = deepcopy(original); plan = call['presentation']['display_plan']
            if change == 'missing': del plan['shared_epilogue']
            elif change == 'word': plan['shared_epilogue']['instructions'][0]['word'] = '0xd503201f'
            elif change == 'end': plan['shared_epilogue']['end_pc_exclusive'] = '0x0'
            else: plan['shared_epilogue']['restore_state_proven'] = True if change == 'true' else 0
            with self.subTest(change=change): self.assert_unresolved(call)
        for value in (True, 0, None):
            call = deepcopy(original); call['error_region']['shared_epilogue']['restore_state_proven'] = value
            self.assert_unresolved(call)

    def test_empty_malformed_or_oversized_tail_records_refuse_without_exception(self):
        original = report()['calls'][0]
        rows = original['error_region']['shared_epilogue']['instructions']
        for malformed in (None, [], {}, tuple(rows), [None], ['ret'], rows * 3):
            call = deepcopy(original); call['error_region']['shared_epilogue']['instructions'] = malformed
            with self.subTest(value=malformed): self.assert_unresolved(call)
        for malformed in (None, [], 'tail'):
            call = deepcopy(original); call['error_region']['shared_epilogue'] = malformed
            with self.subTest(tail=malformed): self.assert_unresolved(call)

    def test_join_interval_alignment_and_contiguous_pc_binding(self):
        original = report()['calls'][0]
        for change in ('join_type', 'join_format', 'join_unaligned', 'join_negative', 'join_overflow',
                       'start', 'end', 'gap', 'pc_type', 'pc_format'):
            call = deepcopy(original); region = call['error_region']; tail = region['shared_epilogue']
            if change == 'join_type': region['join_pc'] = int(region['join_pc'], 16)
            elif change == 'join_format': region['join_pc'] = '0X' + region['join_pc'][2:]
            elif change == 'join_unaligned': region['join_pc'] = hex(int(region['join_pc'], 16) + 1)
            elif change == 'join_negative': region['join_pc'] = '-0x4'
            elif change == 'join_overflow': region['join_pc'] = hex(1 << 64)
            elif change == 'start': tail['start_pc'] = '0x0'
            elif change == 'end': tail['end_pc_exclusive'] = hex(int(tail['end_pc_exclusive'], 16) + 4)
            elif change == 'gap': tail['instructions'][1]['pc'] = tail['instructions'][0]['pc']
            elif change == 'pc_type': tail['instructions'][0]['pc'] = int(tail['start_pc'], 16)
            else: tail['instructions'][0]['pc'] = '0X' + tail['start_pc'][2:]
            synchronize_tail(call, tail)
            with self.subTest(change=change): self.assert_unresolved(call)

    def test_matching_but_invalid_encoded_tails_cannot_supply_choice(self):
        original = report()['calls'][0]
        for change in ('unknown', 'short_word', 'word_type', 'wrong_kind', 'terminal_word', 'early_ret'):
            call = deepcopy(original); tail = call['error_region']['shared_epilogue']; rows = tail['instructions']
            if change == 'unknown': rows[0]['word'] = '0xffffffff'
            elif change == 'short_word': rows[0]['word'] = '0x0'
            elif change == 'word_type': rows[0]['word'] = 0xa9427bfd
            elif change == 'wrong_kind': rows[0]['kind'] = 'ret'
            elif change == 'terminal_word': rows[-1]['word'] = '0xd65f0000'
            else: rows[0].update(kind='ret', word='0xd65f03c0')
            synchronize_tail(call, tail)
            with self.subTest(change=change): self.assert_unresolved(call)

    def test_both_outcomes_require_complete_ordered_and_bounded_tail_evidence(self):
        for name, words in shared_variants():
            original = report(words)['calls'][0]
            for which in (0, 1):
                for change in ('missing', 'duplicate', 'reordered', 'word', 'kind', 'phase', 'extra', 'nondict', 'oversized'):
                    call = deepcopy(original); outcome = selected_outcomes(call)[which]
                    rows = outcome['instructions']; index = next(i for i, row in enumerate(rows) if row['phase'] == 'return_tail')
                    if change == 'reordered' and len(rows) - index < 2:
                        continue
                    if change == 'missing': del rows[index]
                    elif change == 'duplicate': rows.append(deepcopy(rows[index]))
                    elif change == 'reordered': rows[index:] = reversed(rows[index:])
                    elif change == 'word': rows[index]['word'] = '0xd503201f'
                    elif change == 'kind': rows[index]['kind'] = 'nop' if rows[index]['kind'] == 'ret' else 'ret'
                    elif change == 'phase': rows[index]['phase'] = 'success'
                    elif change == 'extra': rows[index]['unrecorded'] = True
                    elif change == 'nondict': rows[0] = None
                    else: rows.extend([{'phase': 'success'}] * 25)
                    with self.subTest(variant=name, outcome=which, change=change): self.assert_unresolved(call)

    def test_scalar_writeback_metadata_is_preserved_and_type_checked(self):
        from test_swift_postindexed_scalar_tail import pop
        original = report(WORDS[:5] + (0xd503201f, pop(), 0xd65f03c0))['calls'][0]
        for location in ('all', 'presentation', 'success', 'error'):
            for value in (32, 16.0, True, None):
                call = deepcopy(original)
                if location == 'all':
                    tail = call['error_region']['shared_epilogue']
                    tail['instructions'][0]['sp_writeback_bytes'] = value
                    synchronize_tail(call, tail)
                elif location == 'presentation':
                    call['presentation']['display_plan']['shared_epilogue']['instructions'][0]['sp_writeback_bytes'] = value
                else:
                    outcome = selected_outcomes(call)[0 if location == 'success' else 1]
                    row = next(row for row in outcome['instructions'] if row['phase'] == 'return_tail')
                    row['sp_writeback_bytes'] = value
                with self.subTest(location=location, value=value): self.assert_unresolved(call)

    def test_shared_result_cannot_claim_success_entry_tail_layout(self):
        for name, words in shared_variants():
            call = report(words)['calls'][0]
            selected_outcomes(call)[0]['return_tail_layout'] = 'success_entry'
            with self.subTest(variant=name): self.assert_unresolved(call)

    def test_existing_direct_success_entry_choices_remain_unchanged(self):
        from test_swift_preserved_result_binding import variants
        from test_swift_literal_call_binding import literal_variants
        cases = [(name, words) for name, words, _ in variants() if name.startswith('direct')]
        cases += [(name, words) for name, words, _ in literal_variants() if name.endswith('_direct')]
        for name, words in cases:
            with self.subTest(variant=name):
                call = report(words)['calls'][0]
                self.assertNotIn('shared_epilogue', call['error_region'])
                self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
                self.assertEqual(_return_choice(call), call['return_choice'])

    def test_renderer_withholds_stale_tail_pairs_and_keeps_raw_evidence(self):
        from airs.swift_error_text import render_swift_error_text
        for name, words in shared_variants():
            value = report(words); call = value['calls'][0]
            selected_outcomes(call)[1]['instructions'][-1]['word'] = '0xd65f0000'
            with self.subTest(variant=name):
                text = render_swift_error_text(value)
                for label in ('Recorded literal outcomes', 'Recorded call-result/error outcomes',
                              'Recorded adjusted-result/error outcomes'):
                    self.assertNotIn(label, text)
                self.assertIn('Error-constant instruction:', text)
                self.assertIn('Return choice (structural outcomes; source disabled):', text)

    def test_cli_reports_new_choice_model_without_broadening_instruction_support(self):
        import contextlib, io, json
        from pathlib import Path
        from airs.cli import main
        from test_swift_error_flow import image
        from fixture_storage import temporary_directory
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            for name, words, expected in (('valid', WORDS, True),
                                           ('invalid-tail', WORDS[:-1] + (0xd65f0000,), False)):
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
                            self.assertEqual('Recorded literal outcomes' in output.getvalue(), expected)
                            self.assertIn('Source reconstruction: disabled', output.getvalue())
