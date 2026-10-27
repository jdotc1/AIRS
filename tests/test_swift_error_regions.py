"""Bounded structural error intervals, without handler or call-return claims."""
import unittest
from airs.swift_error_flow import recover_swift_error_flow
from test_swift_error_flow import image, BASE


class SwiftErrorRegionTests(unittest.TestCase):
    def test_owned_shape_records_opaque_call_and_success_join(self):
        # BL callee; CBZ x21 -> +20; MOV x0,x21; BL +32; MOVN x0,0.
        report = recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0x94000005, 0x92800000)), include_error_regions=True)
        region = report['calls'][0]['error_region']
        self.assertEqual(region['status'], 'structural_region_candidate')
        self.assertEqual(region['start_pc'], hex(BASE + 8))
        self.assertEqual(region['join_pc'], hex(BASE + 20))
        self.assertEqual([i['kind'] for i in region['instructions']], ['mov', 'bl', 'movn'])
        self.assertEqual(region['instructions'][1]['call_target_pc'], hex(BASE + 32))
        self.assertEqual(region['opaque_call_count'], 1)
        self.assertFalse(region['call_return_proven'])
        self.assertEqual(report['summary']['recovered_error_region_count'], 1)


class SwiftErrorRegionBoundaryTests(unittest.TestCase):
    def region(self, window):
        return recover_swift_error_flow(image(window), include_error_regions=True)['calls'][0]['error_region']

    def test_default_report_remains_without_region_supplement(self):
        report = recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0xd503201f, 0x92800000)))
        self.assertNotIn('error_region', report['calls'][0])
        self.assertNotIn('error_region_model_version', report)
        self.assertNotIn('recovered_error_region_count', report['summary'])

    def test_final_direct_jump_to_join(self):
        region = self.region((0xb4000095, 0xaa1503e0, 0xd503201f, 0x14000001))
        self.assertEqual(region['status'], 'structural_region_candidate')
        self.assertEqual(region['instructions'][-1]['target_pc'], hex(BASE + 20))
        self.assertFalse(region['join_reachability_proven'])

    def test_nonjoin_and_early_branches_decline(self):
        for window in ((0xb4000095, 0xaa1503e0, 0xd503201f, 0x14000002),
                       (0xb4000095, 0x14000003, 0xd503201f, 0x92800000)):
            self.assertEqual(self.region(window)['reason'], 'error_region_control_flow_unmodeled')

    def test_conditional_indirect_return_load_and_unknown_decline(self):
        for word in (0xb4000040, 0xd61f0000, 0xd65f03c0, 0xf9400000, 0xffffffff):
            self.assertEqual(self.region((0xb4000095, word, 0xd503201f, 0x92800000))['status'], 'declined')

    def test_success_fallthrough_error_forward_declines_layout(self):
        self.assertEqual(self.region((0xb5000095, 0xaa1503e0, 0xd503201f, 0x92800000))['reason'], 'unsupported_error_region_layout')

    def test_region_sixteen_word_limit_and_seventeen_word_refusal(self):
        for count in (16, 17):
            # Test at +4; error at +8; success at +8+4*count.
            region = self.region((0xb4000015 | ((count + 1) << 5), *([0xd503201f] * count)))
            self.assertEqual(region['status'], 'structural_region_candidate' if count == 16 else 'declined')
            if count == 17: self.assertEqual(region['reason'], 'error_region_budget')

    def test_scan_prefix_refusal_does_not_read_unscanned_region(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        report = recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0x94000005, 0x92800000)),
            replace(DEFAULT_LIMITS, max_instructions_per_function=3), include_error_regions=True)
        self.assertEqual(report['calls'][0]['status'], 'recovered_candidate')
        self.assertEqual(report['calls'][0]['error_region']['reason'], 'error_region_outside_scanned_prefix')
        self.assertFalse(report['word_scan_complete'])

    def test_declined_call_is_not_promoted_by_region_request(self):
        report = recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0xd503201f, 0x92800000), symbol='ordinary'), include_error_regions=True)
        self.assertEqual(report['calls'][0]['status'], 'declined')
        self.assertNotIn('error_region', report['calls'][0])
        self.assertEqual(report['summary']['recovered_error_region_count'], 0)
        self.assertEqual(report['summary']['declined_error_region_count'], 0)

    def test_opaque_calls_do_not_acquire_target_or_return_semantics(self):
        region = self.region((0xb4000095, 0xaa1503e0, 0x94000000, 0x92800000))
        self.assertEqual(region['status'], 'structural_region_candidate')
        self.assertEqual(region['instructions'][1]['semantics'], 'opaque_call')
        self.assertFalse(region['call_return_proven'])

    def test_cli_opt_in_serializes_region_without_changing_exit_contract(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from airs.cli import main
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-error-flow'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'region.macho'
            source.write_bytes(image((0xb4000095, 0xaa1503e0, 0x94000005, 0x92800000)).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions'])
            self.assertEqual(status, 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report['error_region_model_version'], 'swift-sync-error-region-v9')
            self.assertEqual(report['calls'][0]['error_region']['join_pc'], hex(BASE + 20))
