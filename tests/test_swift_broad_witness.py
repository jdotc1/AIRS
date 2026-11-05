"""Synthetic candidate tests; no compiler or ABI qualification claim."""
import json
import struct
import unittest
from pathlib import Path
try:
    import jsonschema
except ImportError:
    jsonschema=None
from dataclasses import replace
from test_swift_broad_callsite import image
from airs.swift_callsite_admission import admit_broad_swift_callsite
from airs.swift_outcome_witness_v2 import build_broad_swift_witness
from airs.swift_outcome_witness_v2_models import BroadWitnessLimits, encode_broad_witness, parse_broad_witness


def candidate(test_word=0xb4000055):
    im, fn = image()
    data=bytearray(im.data)
    for offset,word in ((260,test_word),(264,0xd65f03c0),(268,0xd65f03c0)):
        struct.pack_into('<I',data,offset,word)
    im=replace(im,data=bytes(data))
    call=admit_broad_swift_callsite(im,fn,fn.start)
    call['abi']={'status':'admitted','profile':'swift6-arm64-sync-untyped-research-v1',
                 'error_register':'x21','research_only':True,
                 'evidence':{'lowering':{'qualification_id':'synthetic-only'}}}
    return im,fn,call


class BroadWitnessTests(unittest.TestCase):
    def test_candidate_only_and_raw_geometry(self):
        im,fn,call=candidate()
        result=build_broad_swift_witness(im,fn,call)
        self.assertEqual(result['status'],'unresolved')
        self.assertFalse(result['eligible'])
        self.assertEqual(result['reason'],'validation_required',result)
        self.assertEqual(result['post_call']['error_successor_pc'],'0x1008')
        self.assertEqual(result['post_call']['success_successor_pc'],'0x100c')
        self.assertEqual(result['call']['word'],'0x94000004')
        self.assertNotIn('binding',result['call'])
        self.assertEqual(result['identity']['slice_offset'],'0x1000')

    def test_no_test_and_unqualified_abi_unknown(self):
        im,fn,call=candidate(0xd65f03c0)
        result=build_broad_swift_witness(im,fn,call)
        self.assertEqual(result['post_call']['status'],'unknown')
        self.assertFalse(result['completeness']['complete'])
        call['abi']['status']='unresolved'
        result=build_broad_swift_witness(im,fn,call)
        self.assertIn('abi_unqualified',result['completeness']['missing'])

    def test_deterministic_bounded_roundtrip(self):
        im,fn,call=candidate()
        first=build_broad_swift_witness(im,fn,call)
        self.assertEqual(first,build_broad_swift_witness(im,fn,call))
        raw=encode_broad_witness(first)
        self.assertEqual(parse_broad_witness(raw),first)
        self.assertLessEqual(len(raw),262144)

    def test_limits_and_malformed(self):
        im,fn,call=candidate()
        result=build_broad_swift_witness(im,fn,call,limits=BroadWitnessLimits(max_instructions=0))
        self.assertFalse(result['completeness']['complete'])
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"pc":1.5}', '['*70+'0'+']'*70):
            with self.assertRaises(ValueError):parse_broad_witness(raw)
        with self.assertRaises(ValueError):BroadWitnessLimits(max_bytes=999999999)
        with self.assertRaises(ValueError):encode_broad_witness({'status':'eligible'})

    def test_alias_copy_and_clobber(self):
        im,fn,call=candidate()
        data=bytearray(im.data)
        # MOV x19,x21; CBNZ x19,+4 (both structural successors retained).
        struct.pack_into('<II',data,260,0xaa1503f3,0xb5000033)
        im=replace(im,data=bytes(data));call=admit_broad_swift_callsite(im,fn,fn.start)|{'abi':call['abi']}
        result=build_broad_swift_witness(im,fn,call)
        self.assertEqual(result['post_call']['test_register'],'x19')
        self.assertEqual(result['reason'],'validation_required')

    @unittest.skipIf(jsonschema is None,"Optional jsonschema validator is unavailable")
    def test_schema_and_encoded_accounting(self):
        im,fn,call=candidate()
        result=build_broad_swift_witness(im,fn,call)
        schema=json.loads((Path(__file__).parents[1]/'schemas/swift-outcome-witness-v2.schema.json').read_text())
        jsonschema.Draft202012Validator(schema).validate(result)
        self.assertEqual(result['accounting']['encoded_bytes'],len(encode_broad_witness(result)))
        call['abi']['evidence']['lowering']['qualification_id']='changed'
        self.assertEqual(result['call']['abi']['evidence']['lowering']['qualification_id'],'synthetic-only')

    def test_preflight_cycles_huge_integers_and_item_caps(self):
        from airs.swift_outcome_witness_v2_models import preflight_broad_json
        cyclic=[];cyclic.append(cyclic)
        with self.assertRaises(ValueError):preflight_broad_json(cyclic)
        for raw in ('{"n":'+ '9'*1000 +'}','{"values":[1,2,3,4]}'):
            with self.assertRaises(ValueError):parse_broad_witness(raw,limits=BroadWitnessLimits(max_container_items=3))
        im,fn,call=candidate()
        result=build_broad_swift_witness(im,fn,call,limits=BroadWitnessLimits(max_bytes=256))
        self.assertEqual(result['completeness']['missing'],['witness_output_limit'])
        self.assertFalse(result['eligible'])

    def test_foreign_call_and_oversize_metadata(self):
        im,fn,call=candidate()
        for changed in (call|{'call_pc':True},call|{'callee_pc':0x1004},call|{'status':'eligible'},
                        call|{'declaration':{'x':'z'*4000}}):
            result=build_broad_swift_witness(im,fn,changed)
            self.assertFalse(result['completeness']['complete'])
            self.assertFalse(result['eligible'])

if __name__=='__main__':unittest.main()


def region_candidate(words, call_index=0):
    """Independent synthetic words; no compiler qualification claim."""
    im,oldfn,call=candidate()
    fn=replace(oldfn,end=0x1040)
    callee=replace(im.functions[1],start=0x1040,end=0x1050)
    data=bytearray(im.data)
    for index in range(20):struct.pack_into('<I',data,256+index*4,0xd503201f)
    for index,word in enumerate(words):struct.pack_into('<I',data,256+index*4,word)
    struct.pack_into('<I',data,316,0xd65f03c0)
    pc=0x1000+call_index*4;word=0x94000000+(0x1040-pc)//4
    struct.pack_into('<I',data,256+call_index*4,word)
    im=replace(im,data=bytes(data),functions=(fn,callee),
               sections=(replace(im.sections[0],size=80),))
    call.update(call_pc=pc,callee_pc=0x1040)
    call['provenance']['call'].update(pc=pc,word=f'0x{word:08x}')
    return im,fn,call


class BroadRegionBreadthTests(unittest.TestCase):
    def test_prior_opaque_call_does_not_qualify_postcall_stack_origin(self):
        im,fn,call=region_candidate([0x94000010,0,0xf90003f5,0xb4000055,
                                    0xd65f03c0,0xd65f03c0],call_index=1)
        result=build_broad_swift_witness(im,fn,call)
        self.assertEqual(result['reason'],'validation_required',result)
        self.assertEqual(result['post_call']['test_register'],'x21')
        observations=result['value_facts']['observations']
        self.assertTrue(observations)
        self.assertFalse(any('stack_slot' in origin for row in observations for origin in row['origins']))

    @unittest.skipIf(jsonschema is None,'Optional jsonschema is unavailable')
    def test_exception_candidate_schema_keeps_resumption_unproven(self):
        im,fn,call=region_candidate([0,0xb4000055,0xd4200020,0xd65f03c0])
        result=build_broad_swift_witness(im,fn,call)
        self.assertEqual(result['reason'],'validation_required',result)
        self.assertEqual(result['cfg']['exception_transfers'][0]['exception'],'breakpoint')
        self.assertFalse(result['cfg']['exception_resume_proven'])
        self.assertFalse(result['cfg']['exception_transfers'][0]['resume_proven'])
        schema=json.loads((Path(__file__).parents[1]/'schemas/swift-outcome-witness-v2.schema.json').read_text())
        jsonschema.Draft202012Validator(schema).validate(result)

    def test_selected_stable_origin_and_private_custody_are_separate(self):
        im,fn,call=region_candidate([0,0x9e670115,0xb4000055,0xd65f03c0,0xd65f03c0])
        call['abi']['profile']='swift6-arm64-sync-untyped-stable-research-v2'
        hidden=[];hidden.append(hidden)
        call['abi']['binding']=hidden
        call['abi']['callsite_binding']={'private':hidden}
        call['abi']['evidence']['nominal_context']={'binding':hidden}
        result=build_broad_swift_witness(im,fn,call)
        self.assertEqual(result['reason'],'validation_required',result)
        self.assertEqual(result['value_facts']['seed']['origin'],'raw_post_call_register:x21')
        self.assertNotIn('binding',str(result['call']['abi']))
        self.assertEqual(result['post_call']['test_register'],'x21')

    def test_compare_eq_and_ne_and_flag_clobber(self):
        for cond,error,success in ((0,'0x100c','0x1010'),(1,'0x1010','0x100c')):
            im,fn,call=region_candidate([0,0xf10002bf,0x54000040|cond,0xd65f03c0,0xd65f03c0])
            r=build_broad_swift_witness(im,fn,call)
            self.assertEqual(r['reason'],'validation_required',r)
            self.assertEqual(r['post_call']['test_kind'],'cmp_zero_bcond')
            self.assertEqual(r['post_call']['error_successor_pc'],error)
            self.assertEqual(r['post_call']['success_successor_pc'],success)
        im,fn,call=region_candidate([0,0xf10002bf,0xd503201f,0x54000040,0xd65f03c0])
        self.assertFalse(build_broad_swift_witness(im,fn,call)['completeness']['complete'])

    def test_shared_and_multiple_return_partition(self):
        im,fn,call=region_candidate([0,0xb5000075,0xb4000040,0xd65f03c0,
                                     0x14000002,0xd65f03c0,0xd65f03c0])
        r=build_broad_swift_witness(im,fn,call)
        self.assertEqual(r['regions']['partition']['shared_pcs'],['0x1010','0x1018'])
        tails={t['pc']:t['outcome'] for t in r['regions']['tails']}
        self.assertEqual(tails['0x100c'],'success')
        self.assertEqual(tails['0x1018'],'shared')
        self.assertEqual(tails['0x1014'],'unreachable')
        self.assertFalse(r['eligible'])

    def test_unconditional_hop_and_loop_refusal(self):
        im,fn,call=region_candidate([0,0x14000002,0xd503201f,0xb4000055,0xd65f03c0,0xd65f03c0])
        r=build_broad_swift_witness(im,fn,call)
        self.assertEqual(r['post_call']['trace'],['0x1004','0x100c'])
        self.assertEqual(r['reason'],'validation_required',r)
        im,fn,call=region_candidate([0,0x14000000])
        r=build_broad_swift_witness(im,fn,call)
        self.assertEqual(r['post_call']['reason'],'post_call_cycle')

    def test_stack_error_alias_after_known_frame(self):
        im,fn,call=region_candidate([0xd10043ff,0,0xf90003f5,0xf94003f3,
                                     0xb5000053,0xd65f03c0,0xd65f03c0],call_index=1)
        r=build_broad_swift_witness(im,fn,call)
        self.assertEqual(r['reason'],'validation_required',r)
        self.assertEqual(r['post_call']['test_register'],'x19')
        self.assertTrue(any('stack_slot' in o for step in r['value_facts']['observations'] for o in step['origins']))

    def test_frame_prefix_address_materialization(self):
        im,fn,call=region_candidate([0xd10043ff,0x90000000,0,0xf90003f5,
                                     0xb5000055,0xd65f03c0,0xd65f03c0],call_index=2)
        r=build_broad_swift_witness(im,fn,call)
        self.assertEqual(r['reason'],'validation_required',r)
