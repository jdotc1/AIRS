"""Independent bounded fixtures for the explicit larger inventory profile."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from parser_helpers import build_macho
from airs.cli import main
from airs.swift_broad_flow import recover_swift_broad_flow_path
from airs.types import InputError

FLAGS = ['--include-outcome-witnesses', '--include-error-regions',
         '--validate-region-entries', '--include-structured-presentation']

class LargeBroadProfileTests(unittest.TestCase):
    def test_registry_binds_resource_profile_to_explicit_model(self):
        from airs.swift_broad_profiles import PROFILES
        self.assertEqual(PROFILES['broad-large-v1'].edge_model, 'swift-broad-error-flow-large-v1')

    def test_profile_rejects_limits_raised_above_its_ceiling(self):
        from dataclasses import replace
        from airs.swift_broad_flow import BROAD_LIMITS, LARGE_BROAD_LIMITS
        for profile, limits in [('broad-v1', replace(BROAD_LIMITS, max_functions=8193)),
                                ('broad-large-v1', replace(LARGE_BROAD_LIMITS, max_file_bytes=LARGE_BROAD_LIMITS.max_file_bytes+1))]:
            with self.subTest(profile=profile), self.assertRaises(InputError) as error:
                recover_swift_broad_flow_path('/not-read', profile=profile, limits=limits)
            self.assertEqual(error.exception.code, 'swift_broad_limit')

    def test_direct_admitted_image_uses_selected_profile_ceiling(self):
        from airs.macho import parse_macho
        from airs.swift_broad_flow import recover_swift_broad_flow, LARGE_BROAD_LIMITS
        image = parse_macho(self.fixture(8617), limits=LARGE_BROAD_LIMITS)
        self.assertEqual(recover_swift_broad_flow(image, profile='broad-large-v1')['profile'], 'broad-large-v1')

    def test_large_image_replays_call_with_mocked_abi_qualification(self):
        import struct
        from types import MappingProxyType
        from unittest.mock import patch
        from airs.macho import parse_macho
        from airs.swift_abi_profiles import LoweringObservation
        from airs.swift_broad_flow import recover_swift_broad_flow, LARGE_BROAD_LIMITS
        symbol = '_$s4Test3fooyS2iKF'
        words = [0x94000004, 0xb4000055, 0xd65f03c0, 0xd65f03c0] + [0xd65f03c0] * 8616
        data = build_macho(b''.join(struct.pack('<I', word) for word in words),
            function_offsets=(0, *range(16, len(words)*4, 4)), symbols=((symbol, 16),))
        image = parse_macho(data, limits=LARGE_BROAD_LIMITS)
        callee = image.functions[1].start
        qualification = LoweringObservation('large-owned', image.slice_sha256, 'owned fixture', 'fixture compiler',
            'arm64-apple-macosx14.0', '-O', symbol.lstrip('_'), ('Swift.Int',), 'Swift.Int', ('x0',), 'x0',
            ((callee, 'c0035fd6', 'owned fixture return'),), 'fixture-source:1', 'fixture-disassembly:1')
        with patch('airs.swift_abi_profiles.LOWERING_QUALIFICATIONS', MappingProxyType({'large-owned': qualification})):
            report = recover_swift_broad_flow(image, profile='broad-large-v1')
        self.assertEqual(report['calls'][0]['validation']['status'], 'eligible_structural_only')
        self.assertFalse(report['calls'][0]['validation']['call_return_proven'])
        self.assertEqual(report['calls'][0]['candidate']['profile'], 'broad-v1')

    def fixture(self, count):
        return build_macho(b'\xc0\x03\x5f\xd6' * count,
                           function_offsets=tuple(range(0, count * 4, 4)), symbols=(("_owned", 0),))

    def test_larger_profile_admits_8617_without_changing_broad_v1(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'owned.macho'; path.write_bytes(self.fixture(8617))
            with self.assertRaises(InputError) as error:
                recover_swift_broad_flow_path(path)
            self.assertEqual(error.exception.code, 'function_limit')
            report = recover_swift_broad_flow_path(path, profile='broad-large-v1')
            self.assertEqual((report['profile'], report['model_version']),
                             ('broad-large-v1', 'swift-broad-error-flow-large-v1'))
            self.assertEqual(report['scanned_words'], 8617)
            self.assertTrue(report['word_scan_complete'])
            self.assertFalse(report['runtime_reachability_proven'])

    def test_larger_profile_refuses_above_its_ceiling(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'owned.macho'; path.write_bytes(self.fixture(9217))
            with self.assertRaises(InputError) as error:
                recover_swift_broad_flow_path(path, profile='broad-large-v1')
            self.assertEqual(error.exception.code, 'function_limit')

    def test_cli_dispatch_and_invalid_prerequisites(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'owned.macho'; path.write_bytes(self.fixture(1))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(['swift-error-flow', str(path), '--swift-profile', 'broad-large-v1', *FLAGS]), 0)
            self.assertEqual(json.loads(output.getvalue())['profile'], 'broad-large-v1')
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                self.assertEqual(main(['swift-error-flow', str(path), '--swift-profile', 'broad-large-v1']), 2)
            self.assertEqual(json.loads(errors.getvalue())['error']['code'], 'swift_broad_options')

    def test_large_text_output_and_mixed_model_refusal(self):
        from airs.swift_broad_text import render_swift_broad_text
        record = {'model_version': 'swift-broad-error-flow-large-v1', 'profile': 'broad-large-v1', 'calls': []}
        self.assertIn('broad-large-v1', render_swift_broad_text(record))
        record['profile'] = 'broad-v1'
        with self.assertRaises(InputError): render_swift_broad_text(record)
