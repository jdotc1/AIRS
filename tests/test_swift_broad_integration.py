"""Cross-module wiring uses an independently authored synthetic byte fixture."""
from dataclasses import replace
from unittest.mock import patch
import unittest
import struct
from test_swift_broad_validation import _manual_fixture
from airs.swift_broad_flow import recover_swift_broad_flow,BROAD_LIMITS
from airs.swift_broad_text import render_swift_broad_text
from airs.types import InputError


class BroadIntegrationTests(unittest.TestCase):
    def test_independent_ledger_once_and_complete_image_coordinates(self):
        from test_swift_broad_validation import StableIntegratedWitnessTests
        from airs.swift_outcome_validator_v2 import create_independent_swift_image_ledger
        from airs.swift_outcome_witness_v2_models import BroadWitnessLimits
        image,*_=StableIntegratedWitnessTests().fixture()
        with patch('airs.swift_broad_flow.create_independent_swift_image_ledger',
                   wraps=create_independent_swift_image_ledger) as factory:
            report=recover_swift_broad_flow(image)
        factory.assert_called_once_with(image)
        self.assertEqual(BroadWitnessLimits().max_work,65536)
        self.assertEqual(report['identity']['slice_index'],0)
        self.assertEqual(report['identity']['container_slice_count'],1)
        self.assertEqual(report['identity']['preferred_base'],hex(image.preferred_base))
        row=report['calls'][0]
        self.assertTrue(row['validation']['eligible'],row)
        self.assertTrue(row['validation']['accounting']['image_ledger_reused'])
        self.assertEqual(row['validation']['accounting']['image_work_charged_here'],0)
        self.assertIn('uuid',row['candidate']['identity'])

    def test_stable_session_capability_and_raw_origin_flow_end_to_end(self):
        from test_swift_broad_validation import StableIntegratedWitnessTests
        image,*_=StableIntegratedWitnessTests().fixture()
        report=recover_swift_broad_flow(image)
        self.assertEqual(len(report['calls']),1,report)
        row=report['calls'][0]
        self.assertEqual(row['candidate']['value_facts']['seed']['origin'],'raw_post_call_register:x21',row)
        self.assertEqual(row['validation']['status'],'eligible_structural_only',row)
        self.assertFalse(row['validation']['error_state_proven'])
        self.assertIn('conditional',row['validation']['outcome_scope'])
        self.assertNotIn('binding',str(row))

    def test_text_rejects_container_scalars_and_enforces_encoded_limit(self):
        from airs.swift_broad_text import MAX_TEXT_BYTES
        huge='\x1b'*2048
        call=dict(call_pc=huge,admission={'status':huge,'reason':huge},
                  candidate={'post_call':{key:huge for key in ('test_pc','success_successor_pc','error_successor_pc')}})
        report=dict(model_version='swift-broad-error-flow-v1',profile={'nested':['never-render']},calls=[call]*256)
        text=render_swift_broad_text(report)
        self.assertLessEqual(len(text.encode()),MAX_TEXT_BYTES)
        self.assertIn('unsupported scalar',text)
        self.assertIn('Additional call rows omitted',text)
        self.assertNotIn('\x1b',text)

    def test_producer_resource_refusal_cannot_hide_behind_generic_validator_reason(self):
        image,*_=_manual_fixture()
        candidate=dict(reason='candidate_facts_incomplete',cfg={},
                       completeness={'missing':['witness_output_limit']})
        with patch('airs.swift_broad_flow.build_broad_swift_witness',return_value=candidate), \
                patch('airs.swift_broad_flow.validate_broad_swift_witness',
                      return_value=dict(status='declined',reason='malformed_candidate_or_image')):
            report=recover_swift_broad_flow(image)
        self.assertFalse(report['outcome_witnesses_complete'])
        self.assertTrue(report['word_scan_complete'])

    def test_authenticated_calls_remain_explicit_and_omission_clears_both_flags(self):
        from airs.macho import parse_macho
        image,*_=_manual_fixture()
        data=bytearray(image.data);struct.pack_into('<I',data,256,0xd73f0800)
        fresh=parse_macho(bytes(data),path='fresh authenticated-call inventory fixture')
        report=recover_swift_broad_flow(fresh)
        self.assertEqual(report['selected_call_candidates'],1)
        self.assertEqual(report['calls'][0]['admission']['reason'],'authenticated_indirect_unsupported')
        capped=recover_swift_broad_flow(fresh,replace(BROAD_LIMITS,max_total_evidence=0))
        self.assertFalse(capped['call_details_complete'])
        self.assertFalse(capped['outcome_witnesses_complete'])

    def test_private_nested_bindings_never_enter_candidate_wire_record(self):
        image,*_=_manual_fixture()
        abi=dict(status='unresolved',reason='test_private_abi',binding={'secret':'local'},
                 evidence={'nominal_context':{'binding':{'private':True}}})
        with patch('airs.swift_broad_flow._abi',return_value=abi), \
                patch('airs.swift_broad_flow.build_broad_swift_witness',return_value={}) as build:
            report=recover_swift_broad_flow(image)
        self.assertNotIn('binding',str(build.call_args.args[2]['abi']))
        self.assertNotIn('binding',str(report))
        self.assertGreaterEqual(report['analysis_work'],32768)

    def test_final_wire_ceiling_covers_envelope_and_pretty_print(self):
        image,*_=_manual_fixture()
        from airs.swift_outcome_witness_v2_models import BroadWitnessLimits
        with self.assertRaises(InputError):
            recover_swift_broad_flow(image,witness_limits=BroadWitnessLimits(max_aggregate_bytes=10))

    def test_only_independent_validator_can_grant_eligibility(self):
        image,fn,candidate,qualification=_manual_fixture()
        # The actual registry admission is supplied by the fixture's independently
        # chosen frozen observation, never a patched validator verdict.
        from types import MappingProxyType
        with patch('airs.swift_abi_profiles.LOWERING_QUALIFICATIONS',
                   MappingProxyType({'manual-reviewed':qualification})):
            report=recover_swift_broad_flow(image)
        self.assertEqual(report['model_version'],'swift-broad-error-flow-v1')
        self.assertEqual(len(report['calls']),1,report)
        row=report['calls'][0]
        self.assertFalse(row['candidate']['eligible'])
        self.assertEqual(row['validation']['status'],'eligible_structural_only',row)
        self.assertNotIn('binding',row['admission'])
        self.assertEqual(report['status_counts'],{'eligible_structural_only':1})

    def test_aggregate_and_scan_caps_cannot_imply_completeness(self):
        image,*_=_manual_fixture()
        report=recover_swift_broad_flow(image,replace(BROAD_LIMITS,max_total_evidence=0))
        self.assertFalse(report['call_details_complete'])
        self.assertEqual(report['omitted_calls'],1)
        report=recover_swift_broad_flow(image,replace(BROAD_LIMITS,max_total_instructions=0))
        self.assertFalse(report['word_scan_complete'])
        with self.assertRaises(InputError):recover_swift_broad_flow(None)

    def test_text_is_historical_bounded_and_terminal_safe(self):
        image,*_=_manual_fixture()
        report=recover_swift_broad_flow(image,replace(BROAD_LIMITS,max_total_evidence=0))
        report['profile']='broad\x1b[31m\nforged'
        text=render_swift_broad_text(report)
        self.assertIn('Recorded checks only',text)
        self.assertNotIn('\x1b',text)
        self.assertIn('\\u001b',text)
