"""Final SP post-indexed restore shapes remain structural evidence only."""
import unittest
from test_swift_shared_epilogue import WORDS, report


def pop_word(amount=16, rd=29, rt2=30, rn=31, form=0xa8c00000):
    return form | (((amount // 8) & 127) << 15) | (rt2 << 10) | (rn << 5) | rd


def with_tail(tail):
    return report(WORDS[:6] + tuple(tail))['calls'][0]


class PostIndexedFirstTests(unittest.TestCase):
    def test_final_sp_pop_then_return_recovers(self):
        call = with_tail((pop_word(), 0xd65f03c0))
        self.assertEqual(call['error_region']['status'], 'structural_region_candidate')
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertEqual(call['error_region']['shared_epilogue']['instructions'][0]['word'], '0xa8c17bfd')
        self.assertFalse(call['error_region']['shared_epilogue']['restore_state_proven'])

class PostIndexedBoundaryTests(unittest.TestCase):
    def test_positive_aligned_decoder_boundaries(self):
        for amount in (16, 496):
            self.assertEqual(with_tail((pop_word(amount), 0xd65f03c0))['error_region']['status'], 'structural_region_candidate')

    def test_nonpositive_or_misaligned_adjustments_decline(self):
        for amount in (0, -16, -512, 8, 24, 504, 512):
            self.assertEqual(with_tail((pop_word(amount), 0xd65f03c0))['error_region']['status'], 'declined')

    def test_preindexed_wrong_base_and_unsupported_destinations_decline(self):
        for word in (pop_word(form=0xa9c00000), pop_word(rn=29), pop_word(rn=0),
                     pop_word(rd=0), pop_word(rt2=31), pop_word(rd=30, rt2=30)):
            self.assertEqual(with_tail((word, 0xd65f03c0))['error_region']['status'], 'declined')

    def test_pop_must_immediately_precede_exact_return(self):
        for middle in (0xd503201f, 0xaa1503e0, 0x910043ff, pop_word()):
            self.assertEqual(with_tail((pop_word(), middle, 0xd65f03c0))['error_region']['status'], 'declined')
        for terminal in (0xd65f0000, 0xd65f0bff, 0xd65f0fff, 0xd61f03c0, 0xffffffff):
            self.assertEqual(with_tail((pop_word(), terminal))['error_region']['status'], 'declined')

    def test_pop_and_return_must_both_fit_eight_word_budget(self):
        for padding in (6, 7):
            call = with_tail((0xd503201f,) * padding + (pop_word(), 0xd65f03c0))
            self.assertEqual(call['error_region']['status'], 'structural_region_candidate' if padding == 6 else 'declined')

    def test_scanned_prefix_must_include_return(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        call = report(WORDS[:6] + (pop_word(), 0xd65f03c0),
                      limits=replace(DEFAULT_LIMITS, max_instructions_per_function=8))['calls'][0]
        self.assertEqual(call['error_region']['status'], 'declined')

    def test_side_entry_into_new_tail_or_return_blocks_display(self):
        for target in (28, 32):
            branch = 0x14000000 | (((target - 36) // 4) & 0x3ffffff)
            call = with_tail((pop_word(), 0xd65f03c0, branch))
            self.assertEqual(call['error_region']['incoming_validation']['status'], 'unexpected_direct_entries')
            self.assertEqual(call['presentation']['status'], 'blocked')

    def test_region_identity_changes_without_other_component_or_proof_changes(self):
        from airs.swift_error_text import render_swift_error_text
        value = report(WORDS[:6] + (pop_word(), 0xd65f03c0))
        self.assertEqual(value['error_region_model_version'], 'swift-sync-error-region-v13')
        self.assertEqual(value['model_version'], 'swift-sync-error-edges-v12')
        self.assertEqual(value['region_incoming_model_version'], 'swift-region-direct-entries-v5')
        self.assertEqual(value['structured_presentation_model_version'], 'swift-structural-presentation-v4')
        text = render_swift_error_text(value)
        self.assertIn('0xa8c17bfd', text)
        self.assertIn('Source reconstruction: disabled', text)
        self.assertFalse(value['calls'][0]['error_region']['shared_epilogue']['restore_state_proven'])


class PostIndexedCLIControls(unittest.TestCase):
    def test_synthetic_cli_text_includes_new_tail_with_proof_limits(self):
        import contextlib
        import io
        from pathlib import Path
        from airs.cli import main
        from test_swift_error_flow import image
        from fixture_storage import temporary_directory
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder) / 'owned-pop.macho'
            source.write_bytes(image(WORDS[:6] + (pop_word(), 0xd65f03c0)).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation', '--format', 'text'])
            self.assertEqual(status, 0)
            self.assertIn('0xa8c17bfd', output.getvalue())
            self.assertIn('swift-sync-error-region-v13', output.getvalue())
            self.assertIn('Source reconstruction: disabled', output.getvalue())


class PostIndexedCompositionTests(unittest.TestCase):
    def test_offset_restore_before_final_pop_remains_separate_evidence(self):
        call = with_tail((0xa94157f6, pop_word(48), 0xd65f03c0))
        tail = call['error_region']['shared_epilogue']
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertEqual([row['kind'] for row in tail['instructions']], ['ldp', 'ldp', 'ret'])
        self.assertEqual(tail['instructions'][1]['word'], '0xa8c37bfd')
        self.assertFalse(tail['restore_state_proven'])


if __name__ == '__main__':
    unittest.main()
