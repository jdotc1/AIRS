"""Relocated Swift-frontend arithmetic window and refusal boundaries."""
import unittest
from airs.swift_error_flow import recover_swift_error_flow
from test_swift_error_flow import image

WORDS = (0xb40000b5, 0xaa1503e0, 0x94000070, 0x928000c0, 0x14000002,
         0x91001400, 0xa9427bfd, 0xa94157f6, 0x9100c3ff, 0xd65f03c0)
SYMBOL = '_$s14AIRSArithmetic9readValueSiyKF'


def report(words=WORDS):
    return recover_swift_error_flow(image(words, symbol=SYMBOL), include_error_regions=True,
        validate_region_entries=True, include_structured_presentation=True)


class OwnedPostCallArithmeticTests(unittest.TestCase):
    def test_frontend_add_yields_structural_adjusted_choice(self):
        call = report()['calls'][0]
        self.assertEqual(call['status'], 'recovered_candidate')
        self.assertEqual(call['window'][0]['kind'], 'xcbz')
        self.assertEqual(call['error_region']['status'], 'structural_region_candidate')
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result_add_immediate')
        self.assertEqual(call['return_choice']['success']['immediate'], 5)
        self.assertFalse(call['return_choice']['runtime_value_proven'])
        self.assertFalse(call['return_choice']['source_reconstruction_allowed'])

    def test_removing_add_allows_supported_shared_result_control(self):
        call = report((*WORDS[:5], 0xd503201f, *WORDS[6:]))['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result')
        self.assertEqual(call['return_choice']['error']['constant_bits'], '0xfffffffffffffff9')

    def test_unsupported_arithmetic_does_not_become_noop(self):
        for word in (0x91000401, 0xd1000401):
            call = report((*WORDS[:5], word, *WORDS[6:]))['calls'][0]
            self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_cli_retains_adjusted_choice(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from airs.cli import main
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder)/'frontend.macho'; source.write_bytes(image(WORDS, symbol=SYMBOL).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            call = json.loads(output.getvalue())['calls'][0]
            self.assertEqual(call['return_choice']['success']['kind'], 'call_result_add_immediate')
            self.assertEqual(call['return_choice']['success']['immediate'], 5)
