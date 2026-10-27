"""Owned assembled CMP/B.NE window relocated for regression; no runtime claim."""
import unittest
from airs.swift_error_flow import recover_swift_error_flow
from test_swift_error_flow import image

WORDS = (0xf10002bf, 0x54000061, 0x52824680, 0x14000004,
         0xaa1503e0, 0x94000021, 0x92800000, 0xd65f03c0)
SYMBOL = '_$s13AIRSEpilogues8validateyyKF'


def report(words=WORDS):
    return recover_swift_error_flow(image(words, symbol=SYMBOL), include_error_regions=True,
        validate_region_entries=True, include_structured_presentation=True)


class OwnedCmpNeFixtureTests(unittest.TestCase):
    def test_assembled_window_recovers_both_literals(self):
        call = report()['calls'][0]
        self.assertEqual(call['return_choice']['success']['constant_bits'], '0x0000000000001234')
        self.assertEqual(call['return_choice']['error']['constant_bits'], '0xffffffffffffffff')
        self.assertEqual(call['return_choice']['condition']['test_condition'], 'ne')
        self.assertFalse(call['return_choice']['runtime_value_proven'])
        self.assertFalse(call['error_region']['shared_epilogue']['restore_state_proven'])

    def test_removed_success_seed_does_not_invent_literal(self):
        call = report((*WORDS[:2], 0xd503201f, *WORDS[3:]))['calls'][0]
        self.assertEqual(call['success_constant']['reason'], 'success_x0_constant_not_known')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_error_seed_before_opaque_call_is_invalidated(self):
        call = report((*WORDS[:4], 0x92800000, WORDS[5], 0xd503201f, WORDS[7]))['calls'][0]
        self.assertEqual(call['error_constant']['reason'], 'error_x0_constant_not_known')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_side_entry_into_success_or_tail_blocks_choice(self):
        for target in (12, 32):
            branch = 0x14000000 | (((target - 36)//4) & 0x3ffffff)
            call = report((*WORDS, branch))['calls'][0]
            self.assertEqual(call['presentation']['status'], 'blocked')
            self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_cli_retains_ne_choice_and_false_proof(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from airs.cli import main
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder) / 'assembled.macho'; source.write_bytes(image(WORDS, symbol=SYMBOL).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            choice = json.loads(output.getvalue())['calls'][0]['return_choice']
            self.assertEqual(choice['status'], 'structural_choice_candidate')
            self.assertFalse(choice['source_reconstruction_allowed'])
