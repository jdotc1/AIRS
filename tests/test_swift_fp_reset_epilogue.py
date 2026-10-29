"""Exact FP-reset return shape; no execution or restored-state proof."""
import unittest
from test_swift_postindexed_epilogue import pop_word, with_tail

RESET = 0x910003bf
RETURN = 0xd65f03c0


class FPResetFirstTests(unittest.TestCase):
    def test_exact_reset_pop_return_recovers_as_structural_only(self):
        call = with_tail((RESET, pop_word(), RETURN))
        self.assertEqual(call['error_region']['status'], 'structural_region_candidate')
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        tail = call['error_region']['shared_epilogue']
        self.assertEqual([row['word'] for row in tail['instructions']], ['0x910003bf', '0xa8c17bfd', '0xd65f03c0'])
        self.assertFalse(tail['restore_state_proven'])
        self.assertFalse(call['presentation']['source_reconstruction_allowed'])

class FPResetBoundaryTests(unittest.TestCase):
    def test_positive_aligned_pop_boundaries(self):
        for amount in (16, 496):
            self.assertEqual(with_tail((RESET, pop_word(amount), RETURN))['presentation']['status'], 'eligible_structural_only')

    def test_only_exact_reset_encoding_is_admitted(self):
        for word in (0x914003bf, 0xd10003bf, 0x110003bf, 0x910043bf,
                     0x9100039f, 0x910003fd):
            self.assertEqual(with_tail((word, pop_word(), RETURN))['error_region']['status'], 'declined')

    def test_pop_pair_order_base_and_addressing_remain_exact(self):
        for word in (pop_word(rd=30, rt2=29), pop_word(rd=19, rt2=20),
                     pop_word(rd=29, rt2=29), pop_word(rn=29), pop_word(rn=0),
                     pop_word(form=0xa9400000), pop_word(form=0xa9c00000)):
            self.assertEqual(with_tail((RESET, word, RETURN))['error_region']['status'], 'declined')

    def test_pop_adjustments_preserve_positive_alignment_guard(self):
        for amount in (0, -16, 8, 24, 504, 512):
            self.assertEqual(with_tail((RESET, pop_word(amount), RETURN))['error_region']['status'], 'declined')

    def test_intervening_words_or_unsupported_returns_decline(self):
        for middle in (0xd503201f, 0x910043ff, pop_word()):
            for words in ((RESET, middle, pop_word(), RETURN), (RESET, pop_word(), middle, RETURN)):
                self.assertEqual(with_tail(words)['error_region']['status'], 'declined')
        for terminal in (0xd65f0000, 0xd65f0bff, 0xd65f0fff, 0xd61f03c0, 0xffffffff):
            self.assertEqual(with_tail((RESET, pop_word(), terminal))['error_region']['status'], 'declined')

    def test_all_three_words_must_fit_tail_budget(self):
        for padding in (5, 6):
            call = with_tail((0xd503201f,) * padding + (RESET, pop_word(), RETURN))
            self.assertEqual(call['error_region']['status'], 'structural_region_candidate' if padding == 5 else 'declined')

    def test_both_lookahead_words_must_fit_scanned_prefix(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        from test_swift_shared_epilogue import report, WORDS
        for limit in (8, 9):
            call = report(WORDS[:6] + (RESET, pop_word(), RETURN),
                          limits=replace(DEFAULT_LIMITS, max_instructions_per_function=limit))['calls'][0]
            self.assertEqual(call['error_region']['status'], 'declined')

    def test_partial_caller_with_complete_tail_remains_unresolved(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        from test_swift_shared_epilogue import report, WORDS
        call = report(WORDS[:6] + (RESET, pop_word(), RETURN),
                      limits=replace(DEFAULT_LIMITS, max_instructions_per_function=10))['calls'][0]
        self.assertEqual(call['error_region']['status'], 'structural_region_candidate')
        self.assertEqual(call['presentation']['status'], 'unresolved')

    def test_direct_side_entries_into_reset_pop_or_return_block(self):
        for target in (28, 32, 36):
            branch = 0x14000000 | (((target - 40) // 4) & 0x3ffffff)
            call = with_tail((RESET, pop_word(), RETURN, branch))
            self.assertEqual(call['error_region']['incoming_validation']['status'], 'unexpected_direct_entries')
            self.assertEqual(call['presentation']['status'], 'blocked')

    def test_offset_restores_and_proof_limits_compose_with_reset(self):
        from airs.swift_error_text import render_swift_error_text
        from test_swift_shared_epilogue import report, WORDS
        value = report(WORDS[:6] + (0xa94157f6, RESET, pop_word(48), RETURN))
        self.assertEqual(value['error_region_model_version'], 'swift-sync-error-region-v24')
        for key, expected in (('model_version', 'swift-sync-error-edges-v35'),
                              ('region_incoming_model_version', 'swift-region-direct-entries-v7'),
                              ('structured_presentation_model_version', 'swift-structural-presentation-v9')):
            self.assertEqual(value[key], expected)
        call = value['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertFalse(call['error_region']['shared_epilogue']['restore_state_proven'])
        text = render_swift_error_text(value)
        self.assertIn('0x910003bf', text)
        self.assertIn('Source reconstruction: disabled', text)


class FPResetCLIControls(unittest.TestCase):
    def test_synthetic_cli_retains_full_sequence_and_structural_limit(self):
        import contextlib
        import io
        from pathlib import Path
        from airs.cli import main
        from fixture_storage import temporary_directory
        from test_swift_error_flow import image
        from test_swift_shared_epilogue import WORDS
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder) / 'owned-fp-reset.macho'
            source.write_bytes(image(WORDS[:6] + (RESET, pop_word(), RETURN)).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation', '--format', 'text'])
            self.assertEqual(status, 0)
            for word in ('0x910003bf', '0xa8c17bfd', '0xd65f03c0'):
                self.assertIn(word, output.getvalue())
            self.assertIn('swift-sync-error-region-v24', output.getvalue())
            self.assertIn('Source reconstruction: disabled', output.getvalue())


if __name__ == '__main__':
    unittest.main()
