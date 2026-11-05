"""Owned fixtures for extended scan accounting and profile boundaries."""
import struct
import unittest
from dataclasses import replace
from parser_helpers import build_macho
from airs.macho import parse_macho
from airs.types import InputError
from airs.swift_broad_flow import recover_swift_broad_flow, EXTENDED_BROAD_LIMITS

class ExtendedScanTests(unittest.TestCase):
    def test_cli_extended_profile_dispatch_and_text(self):
        import contextlib, io, tempfile
        from pathlib import Path
        from airs.cli import main
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'owned.macho'
            path.write_bytes(build_macho(symbols=(('_owned',0),)))
            out=io.StringIO()
            with contextlib.redirect_stdout(out):
                code=main(['swift-error-flow',str(path),'--swift-profile','broad-extended-v1',
                    '--include-outcome-witnesses','--include-error-regions','--validate-region-entries',
                    '--include-structured-presentation','--format','text'])
            self.assertEqual(code,0); self.assertIn('broad-extended-v1',out.getvalue())

    def test_extended_profile_retains_more_than_old_call_ceiling(self):
        count=4097
        data=build_macho(struct.pack('<I',0xd63f0100)*count,
                         function_offsets=tuple(range(0,count*4,4)),symbols=(('_owned',0),))
        report=recover_swift_broad_flow(parse_macho(data, limits=EXTENDED_BROAD_LIMITS),profile='broad-extended-v1')
        self.assertEqual(report['selected_call_candidates'],count)
        self.assertEqual(len(report['calls']),count)
        self.assertEqual(report['omitted_calls'],0)
        self.assertTrue(report['call_details_complete'])

    def test_extended_call_limit_reports_one_omission(self):
        count=8193
        data=build_macho(struct.pack('<I',0xd63f0100)*count,
                         function_offsets=tuple(range(0,count*4,4)),symbols=(('_owned',0),))
        report=recover_swift_broad_flow(parse_macho(data, limits=EXTENDED_BROAD_LIMITS),profile='broad-extended-v1')
        self.assertEqual(report['selected_call_candidates'],count)
        self.assertEqual(len(report['calls']),8192)
        self.assertEqual(report['omitted_calls'],1)
        self.assertFalse(report['call_details_complete'])

    def test_per_function_ceiling_leaves_later_function_scannable(self):
        words=262145
        data=build_macho(b'\x1f\x20\x03\xd5' * words + struct.pack('<I', 0xd63f0100),
                         function_offsets=(0,words*4), symbols=(('_owned',0),))
        report=recover_swift_broad_flow(parse_macho(data, limits=EXTENDED_BROAD_LIMITS), profile='broad-extended-v1')
        self.assertEqual(report['scanned_words'],262145)
        self.assertFalse(report['word_scan_complete'])
        self.assertEqual(report['selected_call_candidates'],1)
        self.assertEqual(report['calls'][0]['admission']['reason'],'indirect_target_unresolved')

    def test_profile_contract_is_immutable_and_text_is_profile_bound(self):
        from airs.swift_broad_flow import PROFILE_LIMITS
        from airs.swift_broad_text import render_swift_broad_text
        with self.assertRaises(TypeError): PROFILE_LIMITS['broad-extended-v1'] = EXTENDED_BROAD_LIMITS
        report={'model_version':'swift-broad-error-flow-extended-v1','profile':'broad-extended-v1','calls':[]}
        self.assertIn('broad-extended-v1',render_swift_broad_text(report))
        report['profile']='broad-large-v1'
        with self.assertRaises(InputError): render_swift_broad_text(report)

    def image(self):
        # One long function and an indirect call beyond the old total budget.
        words = 262144
        text = b'\x1f\x20\x03\xd5' * words + struct.pack('<I', 0xd63f0100)
        return parse_macho(build_macho(text, function_offsets=(0, words*4), symbols=(('_owned',0),)), limits=EXTENDED_BROAD_LIMITS)

    def test_call_after_old_scan_boundary_is_recorded(self):
        report = recover_swift_broad_flow(self.image(), profile='broad-extended-v1')
        self.assertEqual(report['scanned_words'], 262145)
        self.assertTrue(report['word_scan_complete'])
        self.assertEqual(report['selected_call_candidates'], 1)
        self.assertEqual(report['calls'][0]['admission']['reason'], 'indirect_target_unresolved')
        self.assertEqual(report['model_version'], 'swift-broad-error-flow-extended-v1')

    def test_lowered_scan_limit_is_explicitly_partial(self):
        limits=replace(EXTENDED_BROAD_LIMITS, max_total_instructions=262144)
        report=recover_swift_broad_flow(self.image(), limits, profile='broad-extended-v1')
        self.assertEqual(report['scanned_words'], 262144)
        self.assertFalse(report['word_scan_complete'])
        self.assertEqual(report['selected_call_candidates'], 0)

    def test_extended_profile_ceiling_and_independent_omission(self):
        with self.assertRaises(InputError) as error:
            recover_swift_broad_flow(None, replace(EXTENDED_BROAD_LIMITS, max_total_instructions=2097153), profile='broad-extended-v1')
        self.assertEqual(error.exception.code, 'swift_broad_limit')
        limits=replace(EXTENDED_BROAD_LIMITS, max_total_evidence=0)
        report=recover_swift_broad_flow(self.image(), limits, profile='broad-extended-v1')
        self.assertTrue(report['word_scan_complete'])
        self.assertEqual(report['omitted_calls'], 1)
        self.assertFalse(report['call_details_complete'])
        self.assertFalse(report['outcome_witnesses_complete'])
