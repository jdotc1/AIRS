"""Byte-bound witnesses over owned synthetic Mach-O; no compiler-coverage claim."""
from copy import deepcopy
from dataclasses import replace
import unittest
from test_swift_error_flow import image
from test_swift_shared_epilogue import WORDS
from airs.swift_error_flow import recover_swift_error_flow
from airs.swift_outcome_witness import build_outcome_witness
from airs.swift_outcome_witness_validation import validate_outcome_witness
from airs.swift_outcome_witness_models import DEFAULT_WITNESS_LIMITS, bounded_copy

class WitnessTests(unittest.TestCase):
    def fixture(self,words=WORDS):
        im=image(words); f=im.functions[0]
        report=recover_swift_error_flow(im,include_error_regions=True,validate_region_entries=True,include_structured_presentation=True)
        return im,f,build_outcome_witness(im,f,report['calls'][0])
    def test_positive(self):
        im,f,w=self.fixture();v=validate_outcome_witness(im,f,w)
        self.assertEqual(v['status'],'eligible_structural_only',v)
        self.assertFalse(v['call_return_proven'])
        self.assertTrue(v['instruction_mappings'])
    def test_mutation_matrix(self):
        im,f,w=self.fixture()
        changes=[('call_pc','0x0'),('call_word','0x94000001'),('callee_pc','0x0'),('success_pc',w['evidence']['error_pc']),('tested_register','x20')]
        for key,bad in changes:
            value=deepcopy(w);value['evidence'][key]=bad
            with self.subTest(key=key):self.assertNotEqual(validate_outcome_witness(im,f,value)['status'],'eligible_structural_only')
        for key in w['image']:
            value=deepcopy(w);value['image'][key]=None
            with self.subTest(image=key):self.assertNotEqual(validate_outcome_witness(im,f,value)['status'],'eligible_structural_only')
    def test_value_and_choice_coordinated_mutation(self):
        im,f,w=self.fixture()
        for key in ('success','error'):
            value=deepcopy(w);c=value['evidence'];c[key+'_constant']['constant_bits']='0x0000000000000063';c['return_choice'][key]['constant_bits']='0x0000000000000063'
            self.assertNotEqual(validate_outcome_witness(im,f,value)['status'],'eligible_structural_only')
    def test_incomplete_unknown_and_side_entry(self):
        for suffix in ((0xffffffff,), (0x17fffff7,)):
            im,f,w=self.fixture(WORDS+suffix)
            self.assertNotEqual(validate_outcome_witness(im,f,w)['status'],'eligible_structural_only')
    def test_budgets_and_malformed(self):
        im,f,w=self.fixture()
        for key in ('max_steps','max_instructions','max_caller_words','max_nodes','max_edges','max_bytes','max_container_items','max_depth'):
            v=validate_outcome_witness(im,f,w,limits=replace(DEFAULT_WITNESS_LIMITS,**{key:0}))
            with self.subTest(key=key):self.assertNotEqual(v['status'],'eligible_structural_only')
        for value in (None,[],{}, {'model_version':[]}):self.assertNotEqual(validate_outcome_witness(im,f,value)['status'],'eligible_structural_only')
        cycle=[];cycle.append(cycle)
        with self.assertRaises(ValueError):bounded_copy(cycle)
    def test_interval_and_graph(self):
        im,f,w=self.fixture()
        mutations=[lambda c:c['error_region']['instructions'][0].update(word='0xd503201f'),lambda c:c['error_region'].update(join_pc='0x0'),lambda c:c['return_choice'].update(return_pc='0x0'),lambda c:c['error_region']['incoming_validation'].update(caller_scan_complete=False)]
        for change in mutations:
            value=deepcopy(w);change(value['evidence']);self.assertNotEqual(validate_outcome_witness(im,f,value)['status'],'eligible_structural_only')
        value=deepcopy(w);value['graph']['edges']=[]
        self.assertNotEqual(validate_outcome_witness(im,f,value)['status'],'eligible_structural_only')
    def test_deterministic_and_immutable(self):
        im,f,w=self.fixture();before=deepcopy(w)
        first=validate_outcome_witness(im,f,w)
        self.assertEqual(w,before)
        self.assertEqual(first['model_version'],'swift-outcome-validation-v1')
        self.assertEqual(w,bounded_copy(w))
    def test_review_complete_models_proofs_and_escaped_budget(self):
        im,f,w=self.fixture()
        for key in w['source_models']:
            value=deepcopy(w);value['source_models'][key]='future'
            self.assertNotEqual(validate_outcome_witness(im,f,value)['status'],'eligible_structural_only')
        value=deepcopy(w);value['runtime_branch_proven']=True
        self.assertNotEqual(validate_outcome_witness(im,f,value)['status'],'eligible_structural_only')
        for key in ('success_constant','error_constant','success_result'):
            value=deepcopy(w);value['evidence'][key]['runtime_value_proven']=True
            self.assertNotEqual(validate_outcome_witness(im,f,value)['status'],'eligible_structural_only')
        with self.assertRaises(ValueError):bounded_copy({'text':'é'*100},replace(DEFAULT_WITNESS_LIMITS,max_bytes=200))
        self.assertNotEqual(validate_outcome_witness(im,f,w,limits=replace(DEFAULT_WITNESS_LIMITS,max_total_work=1))['status'],'eligible_structural_only')

    def test_coordinated_skipping_arm_fallthrough_is_refused(self):
        from airs.swift_outcome_witness_models import image_identity
        im,f,w=self.fixture()
        words=list(WORDS);words[4]=0xd503201f
        altered=image(tuple(words));af=altered.functions[0]
        w['image']=image_identity(altered)
        w['witness_id']=':'.join(('swift-outcome-witness-v1',altered.slice_sha256,hex(af.start),w['evidence']['call_pc']))
        pc=hex(f.start+20)
        def rewrite(obj):
            if isinstance(obj,dict):
                if obj.get('pc')==pc and 'word' in obj:
                    obj['word']='0xd503201f'
                    if 'kind' in obj:obj['kind']='nop'
                    obj.pop('target_pc',None)
                for v in obj.values():rewrite(v)
            elif isinstance(obj,list):
                for v in obj:rewrite(v)
        rewrite(w)
        value=validate_outcome_witness(altered,af,w)
        self.assertEqual(value['reason'],'skipping_arm_join_branch',value)

    def test_retained_proofs_targets_and_presentation(self):
        im,f,w=self.fixture()
        for mutate in (lambda c:c['error_region']['incoming_validation'].update(exclusive_entry_proven=True),
                       lambda c:c['error_constant'].update(handler_semantics_proven=True),
                       lambda c:c['error_region']['instructions'][1].update(call_target_pc='0x0'),
                       lambda c:c.update(presentation={'status':'eligible_structural_only'})):
            value=deepcopy(w);mutate(value['evidence'])
            self.assertNotEqual(validate_outcome_witness(im,f,value)['status'],'eligible_structural_only')
        self.assertNotIn('presentation',w['evidence'])

    def test_malformed_nested_containers_and_empty_builder_interval(self):
        im,f,w=self.fixture()
        for key in ('error_region','return_choice','success_constant','success_result','error_constant'):
            for bad in (None,[],1):
                value=deepcopy(w);value['evidence'][key]=bad
                self.assertNotEqual(validate_outcome_witness(im,f,value)['status'],'eligible_structural_only')
        c=deepcopy(w['evidence']);c['error_region']['instructions']=[]
        value=build_outcome_witness(im,f,c)
        self.assertEqual(value['status'],'unresolved')
