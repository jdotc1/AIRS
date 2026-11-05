"""Independent manually chosen Mach-O bytes; no candidate-builder oracle."""
from copy import deepcopy
from dataclasses import replace
from types import MappingProxyType
from unittest.mock import patch
import struct
import unittest
from airs.types import MachOImage, Section, FunctionRange
from airs.swift_abi_profiles import LoweringObservation
from airs.swift_declaration_profiles import parse_broad_declaration
from dataclasses import asdict
from airs.swift_outcome_validator_v2 import validate_broad_swift_witness
from airs.swift_outcome_witness_v2_models import BroadWitnessLimits


from functools import lru_cache


@lru_cache(maxsize=1)
def _manual_fixture():
    data=bytearray(1024);symbol='_$s4Test3fooyS2iKF'
    struct.pack_into('<IiiIIIII',data,0,0xfeedfacf,0x100000c,0,2,3,192,0,0)
    struct.pack_into('<II16sQQQQiiII',data,32,0x19,152,b'__TEXT',0xf00,8192,0,1024,7,5,1,0)
    struct.pack_into('<16s16sQQIIIIIIII',data,104,b'__text',b'__TEXT',0x1000,32,256,2,0,0,0x80000400,0,0,0)
    strings=b'\0'+symbol.encode()+b'\0'
    struct.pack_into('<IIIIII',data,184,2,24,512,1,768,len(strings))
    struct.pack_into('<IIII',data,208,0x26,16,900,4)
    data[900:904]=b'\x80\x02\x10\0'
    struct.pack_into('<IBBHQ',data,512,1,15,1,0,0x1010);data[768:768+len(strings)]=strings
    words=[0x94000004,0xb4000055,0xd65f03c0,0xd65f03c0]+[0xd65f03c0]*4
    for i,w in enumerate(words):struct.pack_into('<I',data,256+4*i,w)
    fn=FunctionRange(0x1000,0x1010,'caller','lc_function_starts');callee=FunctionRange(0x1010,0x1020,symbol,'lc_function_starts')
    from airs.macho import parse_macho
    im=parse_macho(bytes(data),path='manual fixture');fn,callee=im.functions
    qualification=LoweringObservation('manual-reviewed',im.slice_sha256,'source-fixture','test compiler',
        'arm64-apple-macosx14.0','-O',symbol.lstrip('_'),('Swift.Int',),'Swift.Int',('x0',),'x0',
        ((0x1010,'c0035fd6','manual observed return byte'),),'manual-source:1','manual-disassembly:1')
    def row(pc,kind):
        i=(pc-0x1000)//4;off=256+4*i
        return dict(pc=hex(pc),word=f'0x{words[i]:08x}',slice_offset=hex(off),container_offset=hex(off),kind=kind)
    rows=[row(0x1000,'bl'),row(0x1004,'xcbz'),row(0x1008,'ret'),row(0x100c,'ret')]
    edges=[dict({k:v for k,v in rows[0].items() if k!='kind'},source_pc='0x1000',target_pc='0x1004',kind='call_return_candidate'),
        dict({k:v for k,v in rows[1].items() if k!='kind'},source_pc='0x1004',target_pc='0x100c',kind='conditional_taken'),
        dict({k:v for k,v in rows[1].items() if k!='kind'},source_pc='0x1004',target_pc='0x1008',kind='conditional_fallthrough'),
        dict({k:v for k,v in rows[2].items() if k!='kind'},source_pc='0x1008',target_pc=None,kind='return'),
        dict({k:v for k,v in rows[3].items() if k!='kind'},source_pc='0x100c',target_pc=None,kind='return')]
    blocks=[dict(start_pc=r['pc'],end_pc_exclusive=hex(int(r['pc'],16)+4),instructions=[r],
        successors=[e for e in edges if e['source_pc']==r['pc']],predecessors=[e for e in edges if e['target_pc']==r['pc']]) for r in rows]
    def boundary(f):return dict(start_pc=hex(f.start),end_pc_exclusive=hex(f.end),boundary_source=f.boundary_source)
    def provenance(pc,w):return dict(pc=hex(pc),word=f'0x{w:08x}',slice_file_offset=hex(256+pc-0x1000),container_file_offset=hex(256+pc-0x1000))
    c=dict(model_version='swift-outcome-witness-v2',validation_model='swift-outcome-validation-v2',profile='broad-v1',
        source_models=dict(edge='swift-broad-error-flow-v1',witness='swift-outcome-witness-v2',validation='swift-outcome-validation-v2',cfg='swift-bounded-structural-cfg-v1',value='swift-outcome-values-v1'),
        status='unresolved',eligible=False,reason='validation_required',
        identity=dict(slice_sha256=im.slice_sha256,container_sha256=im.container_sha256,slice_offset='0x0',slice_size='0x400',architecture='arm64',cpu_subtype=0,uuid=im.uuid,preferred_base=hex(im.preferred_base),slice_index=im.slice_index,container_slice_count=im.container_slice_count,caller=boundary(fn),callee=boundary(callee),call_pc='0x1000'),
        call=dict(pc='0x1000',word='0x94000004',callee_pc='0x1010',
            provenance=dict(call=provenance(0x1000,words[0]),callee_entry=provenance(0x1010,words[4])),
            declaration=dict(status='syntax_admitted',identity=asdict(parse_broad_declaration(symbol).identity),reason=None),
            abi=dict(status='admitted',profile='swift6-arm64-sync-untyped-research-v1',error_register='x21',research_only=True,evidence=dict(lowering=dict(qualification_id='manual-reviewed')))),
        cfg=dict(model='swift-bounded-structural-cfg-v1',status='eligible_structural_only',function_pc='0x1000',blocks=blocks,edges=edges,
            returns=rows[2:],call_return_candidates=[dict(**rows[0],callee_pc='0x1010',continuation_pc='0x1004',runtime_return_proven=False)],
            completeness=dict(complete=True,all_words_classified=True),accounting=dict(work=20,retained_words=4,blocks=4,edges=5,max_discovery_depth=3)),
        post_call=dict(status='candidate',reason='qualified_error_alias_zero_test',test_pc='0x1004',test_word='0xb4000055',test_register='x21',error_successor_pc='0x1008',success_successor_pc='0x100c',trace=['0x1004']),
        regions=dict(status='structural_candidates',success_entry_pc='0x100c',error_entry_pc='0x1008',
            paths=[dict(outcome=o,entry_pc=p,reachability='unproven') for o,p in [('success','0x100c'),('error','0x1008')]],
            tails=[dict(pc=p,kind='return',outcome='unknown') for p in ['0x1008','0x100c']]),
        value_facts=dict(seed=dict(register='x21',kind='register_copy',origin='abi_post_call_error:x21',width=64),observations=[]),
        completeness=dict(complete=True,missing=[]),accounting=dict(work=20,instructions=4,blocks=4,edges=5,value_steps=0,encoded_bytes=1),limitations=['research_only'])
    import json
    for _ in range(4):c['accounting']['encoded_bytes']=len(json.dumps(c,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii'))
    return im,fn,c,qualification


def manual_fixture():
    im,fn,c,q=_manual_fixture()
    return im,fn,deepcopy(c),q


def assign(obj,path,value):
    for k in path[:-1]:obj=obj[k]
    obj[path[-1]]=value


# Each mutation attacks a distinct retained claim; every test invokes exactly one
# new validation against changed inputs. The manual fixture never uses a builder.
ATTACKS=[
    (('model_version',),'swift-outcome-witness-v1'),(('validation_model',),'v1'),(('profile',),'methods'),
    (('eligible',),True),(('status',),'eligible_structural_only'),(('source_models','value'),'fake'),
    (('identity','slice_sha256'),'other'),(('identity','container_sha256'),'other'),(('identity','slice_offset'),'0x1000'),
    (('identity','slice_size'),'0x3ff'),(('identity','architecture'),'arm64e'),(('identity','cpu_subtype'),True),
    (('identity','caller','start_pc'),'0x1004'),(('identity','caller','end_pc_exclusive'),'0x100c'),
    (('identity','callee','start_pc'),'0x1014'),(('identity','callee','end_pc_exclusive'),'0x101c'),
    (('identity','caller','boundary_source'),'symbol'),(('identity','call_pc'),'0x1002'),
    (('call','pc'),'0x1004'),(('call','word'),'0x94000005'),(('call','callee_pc'),'0x1014'),
    (('call','provenance','call','slice_file_offset'),'0x104'),(('call','provenance','callee_entry','word'),'0x00000000'),
    (('call','declaration','identity','function_name'),'evil'),(('call','declaration','status'),'syntax_unresolved'),
    (('call','abi','evidence','lowering','qualification_id'),'forged'),(('call','abi','error_register'),'x20'),
    (('call','abi','profile'),'universal'),(('call','abi','research_only'),False),(('call','abi','status'),'unresolved'),
    (('cfg','blocks',0,'instructions',0,'word'),'0x94000005'),(('cfg','blocks',1,'predecessors'),[]),
    (('cfg','edges',1,'target_pc'),'0x1008'),(('cfg','returns'),[]),(('cfg','call_return_candidates'),[]),
    (('cfg','completeness','complete'),False),(('cfg','accounting','edges'),4),(('cfg','model'),'fake'),
    (('post_call','test_pc'),'0x1008'),(('post_call','test_word'),'0xb5000055'),(('post_call','test_register'),'x20'),
    (('post_call','error_successor_pc'),'0x100c'),(('post_call','trace'),[]),(('post_call','status'),'unknown'),
    (('regions','paths',0,'outcome'),'error'),(('regions','tails'),[]),(('regions','success_entry_pc'),'0x1008'),
    (('value_facts','seed','register'),'x0'),(('value_facts','seed','width'),32),(('value_facts','observations'),[{}]),
    (('completeness','complete'),False), (('call_return_proven',),True),
]


class B11MemoryWritebackTests(unittest.TestCase):
    """New writeback transfers only; no real compiler inputs or old selectors."""
    def state(self):
        from airs.swift_outcome_validator_v2 import _ScalarReplay
        return _ScalarReplay(0x2000, BroadWitnessLimits())

    def step(self, state, word):
        from airs.swift_broad_instructions import decode_instruction
        state.step(decode_instruction(word, 0x2004))

    def test_unknown_memory_base_writeback_kills_each_retained_origin(self):
        # x29 is a constant, result, error alias, or unknown; it is never a
        # known stack address. Every admitted LDP/STP pre/post changes x29.
        for origin in (('constant', 0x2000, 64), ('call_result', '0x2000', 64),
                       ('error_result', '0x2000', 64), None):
            for op in (0xa8c00000, 0xa9c00000, 0xa8800000, 0xa9800000):
                state = self.state(); state.write(29, origin)
                state.write(1, ('constant', 7, 64)); state.write(2, ('constant', 8, 64))
                state.cells[-8] = (8, 0, ('call_result', '0x2000', 64))
                self.step(state, op | (2 << 15) | (2 << 10) | (29 << 5) | 1)
                self.assertIsNone(state.read(29))
                self.step(state, 0xaa1d03e0)  # MOV x0,x29 cannot resurrect it.
                self.assertIsNone(state.read(0))
                if op in (0xa8c00000, 0xa9c00000):
                    self.assertIsNone(state.read(1)); self.assertIsNone(state.read(2))
                else:
                    self.assertEqual(state.cells, {})

    def test_unknown_sp_does_not_preserve_frame_alias_writeback(self):
        for base in (29, 31):
            for op in (0xa8c00000, 0xa9c00000, 0xa8800000, 0xa9800000):
                state = self.state(); state.sp = None
                state.write(29, ('stack_address', -32, 64))
                self.step(state, op | (2 << 15) | (2 << 10) | (base << 5) | 1)
                self.assertIsNone(state.sp)
                if base == 29: self.assertIsNone(state.read(29))

    def test_unknown_load_destinations_and_writeback_overlap_refuse(self):
        from airs.arm64 import Instruction
        from airs.swift_outcome_validator_v2 import _Stop
        # Direct descriptors exercise replay's own fail-closed checks, even
        # though the byte decoder also refuses these constrained encodings.
        for rd, rt2 in ((1, 1), (29, 2), (1, 29)):
            state = self.state(); state.write(29, ('constant', 0x2000, 64))
            with self.assertRaises(_Stop):
                state.step(Instruction(0x2004, 0, 'ldp', rd, 29, rt2, 16, 'post'))
        state = self.state(); state.write(29, ('constant', 0x2000, 64))
        # Offset LDP may load its base. The load must kill that origin.
        self.step(state, 0xa9400000 | (2 << 10) | (29 << 5) | 29)
        self.assertIsNone(state.read(29)); self.assertIsNone(state.read(2))

    def test_known_sp_pre_store_post_load_retains_only_actual_cells(self):
        state = self.state(); state.write(1, ('constant', 9, 64))
        self.step(state, 0xa9bf07e0)  # STP x0,x1,[SP,#-16]!
        self.assertEqual(state.sp, -16)
        state.write(0, None); state.write(1, None)
        self.step(state, 0xa8c107e0)  # LDP x0,x1,[SP],#16
        self.assertEqual(state.sp, 0); self.assertEqual(state.cells, {})
        self.assertEqual(state.read(0), ('call_result', '0x2000', 64))
        self.assertEqual(state.read(1), ('constant', 9, 64))


class BroadValidationTests(unittest.TestCase):
    def check(self,im,fn,c,q,**kwargs):
        with patch('airs.swift_abi_profiles.LOWERING_QUALIFICATIONS',MappingProxyType({q.evidence_id:q})):
            return validate_broad_swift_witness(im,fn,c,**kwargs)
    def test_manually_chosen_qualified_fixture(self):
        im,fn,c,q=manual_fixture();r=self.check(im,fn,c,q)
        self.assertEqual(r['status'],'eligible_structural_only',r)
        self.assertFalse(r['call_return_proven']);self.assertFalse(r['source_reconstruction_allowed'])
        self.assertEqual(r['return_observations'][0]['value'],['call_result','0x1000',64])
    def test_differentiated_candidate_attacks(self):
        for path,value in ATTACKS:
            with self.subTest(path=path):
                im,fn,c,q=manual_fixture();assign(c,path,value);r=self.check(im,fn,c,q)
                self.assertFalse(r['eligible'],r)
    def test_changed_raw_bytes_geometry_symbols(self):
        mutations=[(256,'<I',0x94000005),(260,'<I',0xb5000055),(264,'<I',0xd63f0200),
            (272,'<I',0xd503201f),(0,'<I',0),(4,'<I',0),(8,'<I',2),(16,'<I',50),
            (36,'<I',0),(128,'<Q',0x1004),(136,'<Q',28),(144,'<I',260),
            (516,'<B',14),(517,'<B',2),(518,'<H',0x200),(520,'<Q',0x1014),
            (900,'<B',0x84),(903,'<B',1)]
        for off,fmt,value in mutations:
            with self.subTest(offset=off):
                im,fn,c,q=manual_fixture();data=bytearray(im.data);struct.pack_into(fmt,data,off,value)
                self.assertFalse(self.check(replace(im,data=bytes(data)),fn,c,q)['eligible'])
    def test_unknown_registry_even_if_caller_claims_admitted(self):
        im,fn,c,q=manual_fixture()
        self.assertEqual(validate_broad_swift_witness(im,fn,c)['reason'],'abi_qualification_unknown')
    def test_limits_no_false_eligible(self):
        for field in ('max_instructions','max_blocks','max_edges','max_work','max_depth','max_state_entries','max_bytes','max_container_items','post_call_window'):
            with self.subTest(field=field):
                im,fn,c,q=manual_fixture();limits=replace(BroadWitnessLimits(),**{field:0})
                self.assertFalse(self.check(im,fn,c,q,limits=limits)['eligible'])
    def test_coordinated_polarity_and_all_retained_facts_cannot_reuse_old_image_custody(self):
        import json
        im,fn,c,q=manual_fixture();data=bytearray(im.data);struct.pack_into('<I',data,260,0xb5000055)
        def rewrite(node):
            if isinstance(node,dict):
                if node.get('pc')=='0x1004' and 'word' in node:
                    node['word']='0xb5000055'
                    if node.get('kind')=='xcbz':node['kind']='xcbnz'
                for value in node.values():rewrite(value)
            elif isinstance(node,list):
                for value in node:rewrite(value)
        rewrite(c)
        c['post_call'].update(test_word='0xb5000055',error_successor_pc='0x100c',success_successor_pc='0x1008')
        c['regions'].update(success_entry_pc='0x1008',error_entry_pc='0x100c',paths=[
            dict(outcome='success',entry_pc='0x1008',reachability='unproven'),
            dict(outcome='error',entry_pc='0x100c',reachability='unproven')])
        for _ in range(4):c['accounting']['encoded_bytes']=len(json.dumps(c,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii'))
        r=self.check(replace(im,data=bytes(data)),fn,c,q)
        self.assertFalse(r['eligible']);self.assertEqual(r['reason'],'image_admission_custody')
    def test_unadmitted_manually_constructed_image_cannot_claim_existing_digest(self):
        im,fn,c,q=manual_fixture()
        self.assertEqual(self.check(replace(im,_admission_seal=None),fn,c,q)['reason'],'image_admission_custody')
    def test_partial_truncated_and_hostile_objects(self):
        im,fn,c,q=manual_fixture()
        for size in (0,31,200,260,520,902):
            self.assertFalse(self.check(replace(im,data=im.data[:size]),fn,c,q)['eligible'])
        for bad in ({},None,[],{'loop':None}):
            self.assertFalse(self.check(im,fn,bad,q)['eligible'])
    def test_coordinated_call_change_cannot_use_old_source_receipt(self):
        im,fn,c,q=manual_fixture();data=bytearray(im.data);struct.pack_into('<I',data,256,0x94000005)
        c['call']['word']='0x94000005';c['call']['callee_pc']='0x1014'
        c['identity']['callee']['start_pc']='0x1014'
        self.assertFalse(self.check(replace(im,data=bytes(data)),fn,c,q)['eligible'])

class NominalReplayTests(unittest.TestCase):
    def fixture(self,kind):
        from types import SimpleNamespace
        data=bytearray(256)
        # Types entry -> nominal leaf -> module. All offsets independently chosen.
        struct.pack_into('<i',data,0,32)
        struct.pack_into('<Iii',data,32,kind,60,104)
        struct.pack_into('<IIi',data,96,0,0,24)
        data[128:133]=b'Test\0';data[144:150]=b'Owner\0'
        sections=[dict(segment='__TEXT',name='__swift5_types',address=0x2000,end=0x2004,size=4,offset=0,flags=0),
            dict(segment='__TEXT',name='__const',address=0x2004,end=0x2100,size=252,offset=4,flags=0)]
        decl=SimpleNamespace(module='Test',context=(SimpleNamespace(name='Owner',kind={16:'class',17:'struct',18:'enum'}[kind]),))
        return data,sections,decl
    def replay(self,data,sections,decl):
        from airs.swift_outcome_validator_v2 import _validate_nominal_context,_Stop
        def need(ok,reason,status='declined'):
            if not ok:raise _Stop(reason,status)
        def read(off,n):
            need(0<=off and off+n<=len(data),'extent');return bytes(data[off:off+n])
        _validate_nominal_context(None,decl,sections,read,lambda n=1:None,need,BroadWitnessLimits())
    def test_primary_nominal_kinds_from_independent_descriptor_bytes(self):
        for kind in (16,17,18):
            with self.subTest(kind=kind):self.replay(*self.fixture(kind))
    def test_nominal_descriptor_mutations(self):
        from airs.swift_outcome_validator_v2 import _Stop
        attacks=[(0,'<i',0),(0,'<i',33),(32,'<I',0x80|17),(32,'<I',0x10000|17),
            (32,'<I',1),(36,'<i',0),(36,'<i',-4),(36,'<i',1),(40,'<i',0),
            (40,'<i',900),(96,'<I',17),(100,'<I',4),(128,'<B',88),(144,'<B',88)]
        for offset,fmt,value in attacks:
            with self.subTest(offset=offset,value=value):
                data,sections,decl=self.fixture(17);struct.pack_into(fmt,data,offset,value)
                with self.assertRaises(_Stop):self.replay(data,sections,decl)



class IndependentReplayBreadthTests(unittest.TestCase):
    def replay(self, words, state=None):
        from airs.swift_outcome_validator_v2 import _ScalarReplay
        from airs.swift_broad_instructions import decode_instruction
        state=state or _ScalarReplay(0x1000,BroadWitnessLimits())
        for i,word in enumerate(words):state.step(decode_instruction(word,0x1004+i*4))
        return state
    def test_postcall_x0_error_copy_cannot_retain_result(self):
        state=self.replay([0xaa1503e0])  # MOV x0,x21.
        self.assertNotEqual(state.registers.get(0),('call_result','0x1000',64))
    def test_postcall_unknown_copy_kills_result(self):
        state=self.replay([0xaa0103e0])
        self.assertNotIn(0,state.registers)
    def test_narrow_then_wide_does_not_resurrect_result(self):
        state=self.replay([0x2a0003e1,0xaa0103e0])
        self.assertNotEqual(state.registers[0],('call_result','0x1000',64))
        self.assertEqual(state.registers[0][0],'zero_extend')
    def test_wide_copy_preserves_result(self):
        state=self.replay([0xaa0003e1,0xaa0103e0])
        self.assertEqual(state.registers[0],('call_result','0x1000',64))
    def test_constant_lane_and_arithmetic(self):
        state=self.replay([0xd2800020,0xf2a00040,0x91000400])
        self.assertEqual(state.registers[0],('constant',0x20002,64))
    def test_stack_result_spill_reload_with_frame(self):
        state=self.replay([0xd10043ff,0xf90003e0,0xd2800000,0xf94003e0,0x910043ff])
        self.assertEqual(state.registers[0],('call_result','0x1000',64))
        self.assertEqual(state.sp,0);self.assertEqual(state.cells,{})
    def test_stack_overlapping_store_invalidates_old_wide_cell(self):
        state=self.replay([0xd10043ff,0xf90003e0,0xb90007ff,0xf94003e0])
        self.assertNotIn(0,state.registers)
    def test_call_clobber_cannot_retain_old_result_or_stack(self):
        state=self.replay([0xd10043ff,0xf90003e0,0x94000001])
        self.assertNotIn(0,state.registers);self.assertEqual(state.cells,{})
    def test_opaque_call_kills_error_and_saved_aliases(self):
        state=self.replay([0xaa1503f3,0x94000001])
        self.assertNotIn(19,state.registers);self.assertNotIn(21,state.registers)
    def test_narrow_literal_is_zero_extended(self):
        state=self.replay([0x12800000])
        self.assertEqual(state.registers[0],('constant',0xffffffff,64))


def expanded_manual_fixture(specs,branches,success,error,*,prefix_observations=(),comparison=None,call_index=0):
    """Author a wire witness from explicit test-chosen words/kinds/edge indices.

    All branch and arm expectations come from the test case. No producer, decoder,
    ABI admission routine, value transfer or outcome helper constructs this fixture.
    """
    import json
    from airs.macho import parse_macho
    old,_,c,q=manual_fixture();data=bytearray(old.data);count=len(specs);target=0x1000+count*4
    specs=list(specs);specs[call_index]=(0x94000000|(count-call_index),'bl')
    struct.pack_into('<Q',data,144,4*(count+4))
    # Correct record offsets: section at104, address136, size144, fileoff152.
    struct.pack_into('<Q',data,136,0x1000)
    struct.pack_into('<I',data,152,256)
    for i,(word,_) in enumerate(specs+[(0xd65f03c0,'ret')]*4):struct.pack_into('<I',data,256+4*i,word)
    struct.pack_into('<Q',data,520,target);data[900:904]=bytes((0x80,2,count*4,0))
    im=parse_macho(bytes(data),'fresh manual breadth fixture');fn,callee=im.functions
    q=replace(q,slice_sha256=im.slice_sha256,observations=((target,'c0035fd6','manual return'),))
    c['identity'].update(slice_sha256=im.slice_sha256,container_sha256=im.container_sha256,
        caller=dict(start_pc=hex(fn.start),end_pc_exclusive=hex(fn.end),boundary_source='lc_function_starts'),
        callee=dict(start_pc=hex(callee.start),end_pc_exclusive=hex(callee.end),boundary_source='lc_function_starts'),call_pc=hex(0x1000+4*call_index))
    c['call'].update(pc=hex(0x1000+4*call_index),word=f'0x{specs[call_index][0]:08x}',callee_pc=hex(target))
    for name,pc,word in [('call',0x1000+4*call_index,specs[call_index][0]),('callee_entry',target,0xd65f03c0)]:
        off=256+pc-0x1000;c['call']['provenance'][name]=dict(pc=hex(pc),word=f'0x{word:08x}',slice_file_offset=hex(off),container_file_offset=hex(off))
    rows=[dict(pc=hex(0x1000+4*i),word=f'0x{w:08x}',slice_offset=hex(256+4*i),container_offset=hex(256+4*i),kind=k) for i,(w,k) in enumerate(specs)]
    edges=[];leaders={0};terminals=set()
    def edge(i,kind,dest=None):
        e=dict(rows[i]);e.update(kind=kind,source_pc=rows[i]['pc'],target_pc=rows[dest]['pc'] if dest is not None else None);edges.append(e);terminals.add(i)
        if dest is not None:leaders.add(dest)
    for i,(_,kind) in enumerate(specs):
        if i==call_index:edge(i,'call_return_candidate',i+1)
        elif kind=='ret':edge(i,'return')
        elif kind=='brk':edge(i,'exception_transfer')
        elif i in branches:
            choices=branches[i];edge(i,'branch' if kind=='b' else 'conditional_taken',choices[0])
            if kind!='b':edge(i,'conditional_fallthrough',choices[1])
        if i in terminals and i+1<count:leaders.add(i+1)
    blocks=[];owner={}
    for i,r in enumerate(rows):
        if i in leaders:blocks.append(dict(start_pc=r['pc'],end_pc_exclusive=None,instructions=[],successors=[],predecessors=[]))
        blocks[-1]['instructions'].append(r);blocks[-1]['end_pc_exclusive']=hex(0x1000+4*i+4);owner[i]=blocks[-1]
    for b in blocks:
        i=(int(b['instructions'][-1]['pc'],16)-0x1000)//4
        if i not in terminals:edge(i,'fallthrough',i+1)
    for e in edges:
        owner[(int(e['source_pc'],16)-0x1000)//4]['successors'].append(e)
        if e['target_pc']:owner[(int(e['target_pc'],16)-0x1000)//4]['predecessors'].append(e)
    seen=set();depthmax=0
    for b in blocks:
        if b['start_pc'] in seen:continue
        seen.add(b['start_pc']);stack=[(b,1)]
        while stack:
            block,depth=stack.pop();depthmax=max(depthmax,depth)
            for e in reversed(block['successors']):
                if e['target_pc'] and e['target_pc'] not in seen:
                    seen.add(e['target_pc']);stack.append((owner[(int(e['target_pc'],16)-0x1000)//4],depth+1))
    returns=[r for r in rows if r['kind']=='ret']
    c['cfg'].update(blocks=blocks,edges=edges,returns=returns,
        call_return_candidates=[dict(**rows[call_index],callee_pc=hex(target),continuation_pc=hex(0x1000+4*(call_index+1)),runtime_return_proven=False)],
        accounting=dict(work=100,retained_words=count,blocks=len(blocks),edges=len(edges),max_discovery_depth=depthmax))
    if any(kind=='brk' for _,kind in specs):
        c['cfg'].update(exception_transfers=[dict(**r,exception='breakpoint',resume_proven=False) for r in rows if r['kind']=='brk'],
            external_exception_handling_unmodeled=True,exception_resume_proven=False)
    test=next(i for i in branches if specs[i][1] in ('xcbz','xcbnz','bcond'))
    trace=[];i=call_index+1
    while True:
        trace.append(rows[i]['pc'])
        if i==test:break
        i=branches[i][0] if specs[i][1]=='b' else i+1
    c['post_call'].update(test_pc=rows[test]['pc'],test_word=rows[test]['word'],trace=trace,
        success_successor_pc=rows[success]['pc'],error_successor_pc=rows[error]['pc'])
    if comparison is not None:
        c['post_call'].update(test_kind='cmp_zero_bcond',comparison_pc=rows[comparison]['pc'],comparison_word=rows[comparison]['word'],
            test_condition='eq' if specs[test][0]&15==0 else 'ne')
    def reached(start):
        found=set();todo=[start]
        while todo:
            i=todo.pop()
            if i in found:continue
            found.add(i)
            if specs[i][1] in ('ret','brk'):continue
            todo.extend(branches.get(i,[i+1]))
        return found
    ss,es=reached(success),reached(error)
    c['regions'].update(success_entry_pc=rows[success]['pc'],error_entry_pc=rows[error]['pc'],
        paths=[dict(outcome=o,entry_pc=rows[i]['pc'],reachability='unproven') for o,i in [('success',success),('error',error)]],
        partition=dict(success_only_pcs=[rows[i]['pc'] for i in sorted(ss-es)],error_only_pcs=[rows[i]['pc'] for i in sorted(es-ss)],
            shared_pcs=[rows[i]['pc'] for i in sorted(ss&es)],unreachable_pcs=[rows[i]['pc'] for i in sorted(set(range(count))-ss-es)]),
        tails=[dict(pc=r['pc'],kind='return',outcome='shared' if i in ss&es else ('success' if i in ss else ('error' if i in es else 'unreachable')))
            for i,r in enumerate(rows) if r['kind']=='ret'])
    c['value_facts']['observations']=list(prefix_observations)
    c['accounting'].update(work=100,instructions=count,blocks=len(blocks),edges=len(edges),value_steps=len(prefix_observations))
    for _ in range(4):c['accounting']['encoded_bytes']=len(json.dumps(c,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii'))
    return im,fn,c,q


class IntegratedBreadthTests(unittest.TestCase):
    check=BroadValidationTests.check
    # Focused new selectors do not inherit earlier baseline tests.
    def test_cmp_eq_zero_and_shared_tail(self):
        specs=[(0,'bl'),(0xf10002bf,'xsubs'),(0x54000060,'bcond'),(0xd2800020,'movz'),(0x14000002,'b'),(0xd2800040,'movz'),(0xd65f03c0,'ret')]
        im,fn,c,q=expanded_manual_fixture(specs,{2:[5,3],4:[6]},5,3,comparison=1)
        r=self.check(im,fn,c,q);self.assertTrue(r['eligible'],r)
        self.assertEqual([o['value'] for o in r['return_observations']],[['constant',2,64],['constant',1,64]])
        self.assertEqual(r['region_partition']['shared_pcs'],['0x1018'])
    def test_postcall_result_clobber_flows_to_return(self):
        origins=[dict(register='x0',kind='register_copy',origin='abi_post_call_error:x21'),dict(register='x21',kind='register_copy',origin='abi_post_call_error:x21')]
        specs=[(0,'bl'),(0xaa1503e0,'mov'),(0xb4000055,'xcbz'),(0xd65f03c0,'ret'),(0xd65f03c0,'ret')]
        im,fn,c,q=expanded_manual_fixture(specs,{2:[4,3]},4,3,prefix_observations=[dict(pc='0x1004',origins=origins)])
        r=self.check(im,fn,c,q);self.assertTrue(r['eligible'],r)
        self.assertEqual(r['return_observations'][0]['value'][0],'error_result')
    def test_postcall_unknown_clobber_cannot_report_call_result(self):
        specs=[(0,'bl'),(0xaa0103e0,'mov'),(0xb4000055,'xcbz'),(0xd65f03c0,'ret'),(0xd65f03c0,'ret')]
        obs=[dict(pc='0x1004',origins=[dict(register='x21',kind='register_copy',origin='abi_post_call_error:x21')])]
        im,fn,c,q=expanded_manual_fixture(specs,{2:[4,3]},4,3,prefix_observations=obs)
        r=self.check(im,fn,c,q);self.assertTrue(r['eligible'],r)
        self.assertEqual(r['value_fact_status'],'checked_with_explicit_unknowns')
        self.assertFalse(r['symbolic_return_values_complete'])
        self.assertEqual(r['return_observations'][0]['value'],['unknown',64])
        self.assertEqual(r['eligibility_scope'],'checked_structural_facts_only')
        self.assertFalse(r['call_return_proven'])
    def test_narrow_wide_arm_preserves_transformation(self):
        specs=[(0,'bl'),(0xb4000095,'xcbz'),(0x2a0003e1,'wmov'),(0xaa0103e0,'mov'),(0xd65f03c0,'ret'),(0xd65f03c0,'ret')]
        im,fn,c,q=expanded_manual_fixture(specs,{1:[5,2]},5,2)
        r=self.check(im,fn,c,q);self.assertTrue(r['eligible'],r)
        self.assertEqual(r['return_observations'][1]['value'][0],'zero_extend')
    def test_fresh_admission_stale_raw_call_fact_is_rejected(self):
        im,fn,c,q=expanded_manual_fixture([(0,'bl'),(0xb4000055,'xcbz'),(0xd65f03c0,'ret'),(0xd65f03c0,'ret')],{1:[3,2]},3,2)
        from airs.macho import parse_macho
        data=bytearray(im.data);struct.pack_into('<I',data,260,0xb5000055)
        changed=parse_macho(bytes(data),'fresh changed raw fixture')
        c['identity'].update(slice_sha256=changed.slice_sha256,container_sha256=changed.container_sha256)
        q=replace(q,slice_sha256=changed.slice_sha256)
        r=self.check(changed,changed.functions[0],c,q);self.assertFalse(r['eligible']);self.assertEqual(r['reason'],'cfg_replay_mismatch')

class AdditionalGeometryTests(unittest.TestCase):
    check=BroadValidationTests.check
    def test_cmp_ne_polarity(self):
        specs=[(0,'bl'),(0xf10002bf,'xsubs'),(0x54000041,'bcond'),(0xd65f03c0,'ret'),(0xd65f03c0,'ret')]
        im,fn,c,q=expanded_manual_fixture(specs,{2:[4,3]},3,4,comparison=1)
        r=self.check(im,fn,c,q);self.assertTrue(r['eligible'],r)
    def test_postcall_direct_hop_over_unreachable_return(self):
        specs=[(0,'bl'),(0x14000002,'b'),(0xd65f03c0,'ret'),(0xb4000055,'xcbz'),(0xd65f03c0,'ret'),(0xd65f03c0,'ret')]
        im,fn,c,q=expanded_manual_fixture(specs,{1:[3],3:[5,4]},5,4)
        r=self.check(im,fn,c,q);self.assertTrue(r['eligible'],r)
        self.assertIn('0x1008',r['region_partition']['unreachable_pcs'])
    def test_multiple_conditional_return_arms(self):
        specs=[(0,'bl'),(0xb40000d5,'xcbz'),(0xb4000060,'xcbz'),(0xd2800020,'movz'),(0xd65f03c0,'ret'),(0xd2800040,'movz'),(0xd65f03c0,'ret'),(0xd65f03c0,'ret')]
        im,fn,c,q=expanded_manual_fixture(specs,{1:[7,2],2:[5,3]},7,2)
        r=self.check(im,fn,c,q);self.assertTrue(r['eligible'],r)
        self.assertEqual(len(r['return_observations']),3)
    def test_stack_result_restore_shared_tail(self):
        specs=[(0,'bl'),(0xd10043ff,'sub'),(0xf90003e0,'xstr'),(0xb4000055,'xcbz'),(0x14000002,'b'),(0xd503201f,'nop'),(0xf94003e0,'xldr'),(0x910043ff,'add'),(0xd65f03c0,'ret')]
        origin=[dict(register='x21',kind='register_copy',origin='abi_post_call_error:x21')]
        obs=[dict(pc=p,origins=origin) for p in ['0x1004','0x1008']]
        im,fn,c,q=expanded_manual_fixture(specs,{3:[5,4],4:[6]},5,4,prefix_observations=obs)
        r=self.check(im,fn,c,q);self.assertTrue(r['eligible'],r)
        self.assertEqual(r['return_observations'][1]['value'],['call_result','0x1000',64])
    def test_cycle_remains_explicitly_unresolved(self):
        specs=[(0,'bl'),(0xb4000055,'xcbz'),(0x14000000,'b'),(0xd65f03c0,'ret')]
        im,fn,c,q=expanded_manual_fixture(specs,{1:[3,2],2:[2]},3,2)
        r=self.check(im,fn,c,q);self.assertFalse(r['eligible']);self.assertEqual(r['reason'],'cyclic_or_external_arm')
    def test_scalar_arithmetic_keeps_derived_result(self):
        specs=[(0,'bl'),(0xb4000075,'xcbz'),(0x91000400,'add'),(0xd65f03c0,'ret'),(0xd65f03c0,'ret')]
        im,fn,c,q=expanded_manual_fixture(specs,{1:[4,2]},4,2)
        r=self.check(im,fn,c,q);self.assertTrue(r['eligible'],r)
        self.assertEqual(r['return_observations'][1]['value'][0],'add')


def stable_manual_record(key,selected_slice='fresh synthetic non-owned source',*,entry_pc=0x1020,word_count=3):
    from airs.swift_abi_profiles import STABLE_STORAGE_CAPABILITIES,STABLE_LOWERING_OBSERVATIONS,_V2_SOURCE,_V2_SLICES,ABI_REFERENCES,_COMPILER,OWNED_SOURCE_BY_SLICE
    capability=STABLE_STORAGE_CAPABILITIES[key]
    storage=asdict(capability);storage['locations']=list(capability.locations)
    abi=dict(status='admitted',profile='swift6-arm64-sync-untyped-stable-research-v2',
        error_register='x21',research_only=True,compiler_verified=False,
        profile_assumption='explicit_selected_swift6_stable_arm64_sync_untyped',
        result_storage=storage,result_type=key,result_location=capability.locations[0] if capability.locations else None,
        argument_storage=[],argument_locations=[],receiver_location=None,
        evidence=dict(lowering=dict(qualification_id=capability.evidence_id,
            source_evidence_id='owned-v2-fixed-initial-lowering-observations',source_sha256=_V2_SOURCE,compiler=_COMPILER,target='arm64-apple-macosx14.0',
            selected_source_sha256=OWNED_SOURCE_BY_SLICE.get(selected_slice),selected_slice_sha256=selected_slice,
            reference_slice_sha256=sorted(_V2_SLICES)[0],public_abi_references=list(ABI_REFERENCES),
            observations=[dict(pc=hex(pc),raw_bytes=raw,meaning=meaning,source_case=case)
                for pc,raw,meaning,case in STABLE_LOWERING_OBSERVATIONS],specialization=None,
            assumption='explicit_selected_swift6_stable_arm64_sync_untyped',compiler_verified=False)))
    abi['evidence']['lowering'].update(error_object_type_proven=False,callee_error_transport_observation='mov_to_x21_from_distinct_nonzero_gpr_presence',
        callee_error_observation=dict(mode='distinct_nonzero_gpr_copy',register='x21',
            scope='instruction_effects_if_normal_return_not_incoming_state_or_object_type',entry_pc=hex(entry_pc),return_pc=None,
            word_count=word_count,preserves_incoming_x21=None,incoming_state_proven=False,error_object_type_proven=False))
    return abi


class StableStorageIndependentTests(unittest.TestCase):
    def check_storage(self,key,words,*,mutate=None,selected_slice='fresh synthetic non-owned source',observed_reads=None):
        from types import SimpleNamespace
        from airs.swift_outcome_validator_v2 import _validate_stable_abi,_Stop
        from airs.swift_abi_profiles import STABLE_STORAGE_CAPABILITIES,STABLE_LOWERING_OBSERVATIONS,_V2_SOURCE,_V2_SLICES,ABI_REFERENCES,_COMPILER
        from airs.swift_declaration_profiles import SwiftType
        from airs.swift_broad_instructions import decode_instruction
        capability=STABLE_STORAGE_CAPABILITIES[key]
        if key=='Optional<Swift.Int>':node=SwiftType('Optional',(SwiftType('Swift.Int'),))
        elif key=='Tuple<Swift.Int,Swift.Bool>':node=SwiftType('Tuple',(SwiftType('Swift.Int'),SwiftType('Swift.Bool')))
        else:node=SwiftType(key)
        decl=replace(parse_broad_declaration('_$s4Test3fooyS2iKF').identity,result_type=node,parameter_types=())
        callee=FunctionRange(0x1020,0x1020+4*len(words),'test target','lc_function_starts')
        caller=FunctionRange(0x1000,0x1010,'test caller','lc_function_starts')
        im=SimpleNamespace(slice_sha256=selected_slice)
        storage=asdict(capability);storage['locations']=list(capability.locations)
        abi=stable_manual_record(key,selected_slice=selected_slice,entry_pc=callee.start,word_count=len(words))
        raw=struct.pack('<'+'I'*len(words),*words)
        def need(ok,reason,status='declined'):
            if not ok:raise _Stop(reason,status)
        def read(offset,size):
            if observed_reads is not None:observed_reads.append((offset,size))
            return raw[offset-0x1020:offset-0x1020+size]
        if mutate:mutate(abi)
        result,caller_state=_validate_stable_abi(im,caller,callee,0x1004,decl,abi,read,lambda pc,n=4:pc,
            lambda pc:decode_instruction(0xd2800015,pc),lambda n=1:None,need,BroadWitnessLimits())
        self.assertEqual(result,storage);self.assertEqual(caller_state,'unproven_profile_precondition')
    def test_eight_distinct_selected_storage_forms_independent_raw_patterns(self):
        cases=[('Swift.Void',[0xaa0003f5,0xd65f03c0]),
            ('Swift.Int8',[0xaa0003f5,0x52800020,0xd65f03c0]),
            ('Swift.UInt16',[0xaa0003f5,0x52800040,0xd65f03c0]),
            ('Swift.Int64',[0xaa0003f5,0xd2800060,0xd65f03c0]),
            ('Swift.Bool',[0xaa0003f5,0x52800020,0xd65f03c0]),
            ('Swift.Float',[0xaa0003f5,0x1e270000,0xd65f03c0]),
            ('Swift.Double',[0xaa0003f5,0x9e620000,0xd65f03c0]),
            ('Optional<Swift.Int>',[0xaa0003f5,0xd2800020,0x52800001,0xd65f03c0]),
            ('Tuple<Swift.Int,Swift.Bool>',[0xaa0003f5,0xd2800020,0x52800001,0xd65f03c0])]
        for key,words in cases:
            with self.subTest(storage=key):self.check_storage(key,words)
    def test_forged_storage_profile_and_source_evidence_refused(self):
        from airs.swift_outcome_validator_v2 import _Stop
        mutations=[lambda a:a.update(compiler_verified=True),lambda a:a['result_storage'].update(bit_width=64),
            lambda a:a['evidence']['lowering'].update(source_sha256='forged'),
            lambda a:a['evidence']['lowering'].update(qualification_id='caller-made'),
            lambda a:a['evidence']['lowering'].update(observations=[])]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(_Stop):self.check_storage('Swift.Int8',[0xaa0003f5,0x52800020,0xd65f03c0],mutate=mutation)
    def test_frozen_compiler_and_target_evidence_are_exact_metadata(self):
        from airs.swift_outcome_validator_v2 import _Stop
        self.check_storage('Swift.Int16',[0xaa0003f5,0x52800020,0xd65f03c0])
        for key,value in [('compiler','caller-made'),('target','arm64e-apple-macosx14.0')]:
            with self.subTest(key=key):
                with self.assertRaises(_Stop):self.check_storage('Swift.Int16',[0xaa0003f5,0x52800020,0xd65f03c0],
                    mutate=lambda abi:abi['evidence']['lowering'].update({key:value}))
    def test_presence_preconditions_and_family_are_checked_without_semantic_upgrade(self):
        def selected(abi):
            abi.update(profile_preconditions=['well_formed_swift_stable_arm64_calling_convention','synchronous_untyped_throws',
                'caller_supplies_error_register_state_required_by_convention'],family='free',
                family_evidence=dict(source_sha256=None,compiled_target_pc='0x1020',direct_call_pc='0x1004',
                    scope='source_lineage_plus_exact_emitted_target_not_runtime_dispatch'),
                caller_error_observations=dict(clear_instruction_pcs=['0x1000'],test_instruction_pcs=[],
                    incoming_state_proven=False,scope='instruction_presence_not_path_or_state_proof'))
        self.check_storage('Swift.Int32',[0xaa0003f5,0x52800020,0xd65f03c0],mutate=selected)
        from airs.swift_outcome_validator_v2 import _Stop
        for key,value in [('profile_preconditions',[]),('family','extension')]:
            def forged(abi):selected(abi);abi[key]=value
            with self.subTest(key=key):
                with self.assertRaises(_Stop):self.check_storage('Swift.Int32',[0xaa0003f5,0x52800020,0xd65f03c0],mutate=forged)
    def test_result_and_error_transport_are_separate_required_byte_facts(self):
        from airs.swift_outcome_validator_v2 import _Stop
        for words in ([0xd2800020,0xd65f03c0],[0xaa0003f5,0xd65f03c0]):
            with self.subTest(words=words):
                with self.assertRaises(_Stop):self.check_storage('Swift.Int64',words)


class CallBoundaryRegressionTests(unittest.TestCase):
    check=BroadValidationTests.check
    def test_precall_frame_alias_cannot_overwrite_main_call_result_seed(self):
        specs=[(0x910003e0,'add'),(0,'bl'),(0xb4000055,'xcbz'),(0xd65f03c0,'ret'),(0xd65f03c0,'ret')]
        im,fn,c,q=expanded_manual_fixture(specs,{2:[4,3]},4,3,call_index=1)
        r=self.check(im,fn,c,q);self.assertTrue(r['eligible'],r)
        self.assertEqual(r['return_observations'][0]['value'],['call_result','0x1004',64])
    def test_opaque_call_does_not_preserve_sp_origin(self):
        from airs.swift_outcome_validator_v2 import _ScalarReplay
        from airs.swift_broad_instructions import decode_instruction
        state=_ScalarReplay(0x1000,BroadWitnessLimits())
        for word in (0x94000001,0x910003e0):state.step(decode_instruction(word,0x1004))
        self.assertIsNone(state.sp);self.assertNotIn(0,state.registers)
    def test_retained_expression_budget_is_charged_before_append(self):
        from airs.swift_outcome_validator_v2 import _retention_cost,_Stop
        tree=('call_result','0x1000',64)
        for _ in range(8):tree=('add',tree,tree,64)
        with self.assertRaises(_Stop):_retention_cost(tree,replace(BroadWitnessLimits(),max_bytes=1000),lambda n=1:None)


class StableIntegratedWitnessTests(unittest.TestCase):
    check=BroadValidationTests.check
    def fixture(self,prefix=0xd2800015):
        import json
        from airs.macho import parse_macho
        specs=[(prefix,'movz' if prefix!=0xd503201f else 'nop'),(0,'bl'),(0xb4000055,'xcbz'),(0xd65f03c0,'ret'),(0xd65f03c0,'ret')]
        im,fn,c,q=expanded_manual_fixture(specs,{2:[4,3]},4,3,call_index=1)
        data=bytearray(im.data);target=im.functions[1].start
        struct.pack_into('<III',data,256+target-0x1000,0xaa0003f5,0xd2800020,0xd65f03c0)
        im=parse_macho(bytes(data),'new independent stable profile fixture');fn=im.functions[0]
        c['identity'].update(slice_sha256=im.slice_sha256,container_sha256=im.container_sha256)
        c['call']['provenance']['callee_entry']['word']='0xaa0003f5'
        c['call']['abi']=stable_manual_record('Swift.Int',selected_slice=im.slice_sha256,entry_pc=im.functions[1].start,word_count=im.functions[1].size//4)
        c['value_facts']['seed']['origin']='raw_post_call_register:x21'
        c['call']['abi']['argument_storage']=[dict(type='Swift.Int',locations=['x0'],evidence_id='swift-stable-v2-int',inout=False)]
        c['call']['abi']['argument_locations']=[['x0']]
        for _ in range(4):c['accounting']['encoded_bytes']=len(json.dumps(c,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii'))
        return im,fn,c,q
    def test_selected_stable_rule_is_independently_checked_end_to_end(self):
        im,fn,c,q=self.fixture()
        r=self.check(im,fn,c,q);self.assertTrue(r['eligible'],r)
        self.assertFalse(r['compiler_verified']);self.assertFalse(r['call_return_proven'])
        self.assertEqual(r['abi_assumption'],'explicit_selected_swift6_stable_arm64_sync_untyped')


class ConditionalStableScopeTests(unittest.TestCase):
    check=BroadValidationTests.check
    fixture=StableIntegratedWitnessTests.fixture
    # Only these new cases are selected for their first targeted run.
    def test_unknown_incoming_state_permits_only_explicit_conditional_roles(self):
        im,fn,c,q=self.fixture(prefix=0xd503201f)
        r=self.check(im,fn,c,q);self.assertTrue(r['eligible'],r)
        self.assertEqual(r['caller_error_state'],'unproven_profile_precondition')
        self.assertEqual(r['outcome_scope'],'byte_zero_nonzero_geometry_with_conditional_abi_roles')
        self.assertIn('incoming_x21_zero_required_by_selected_convention',r['outcome_preconditions'])
        self.assertFalse(r['error_state_proven']);self.assertFalse(r['runtime_branch_proven'])
    def test_known_nonzero_incoming_state_is_contradictory(self):
        im,fn,c,q=self.fixture(prefix=0xd2800035)
        r=self.check(im,fn,c,q);self.assertFalse(r['eligible'])
        self.assertEqual(r['status'],'blocked');self.assertEqual(r['reason'],'caller_error_contract_contradiction')


class DecoderEffectBreadthTests(unittest.TestCase):
    replay=IndependentReplayBreadthTests.replay
    def test_fp_destination_zero_does_not_clobber_gpr_zero(self):
        state=self.replay([0x1e270000])
        self.assertEqual(state.registers[0],('call_result','0x1000',64))
    def test_fp_to_gpr_zero_cannot_preserve_result_origin(self):
        state=self.replay([0x1e260000])
        self.assertNotIn(0,state.registers)
    def test_narrow_byte_store_invalidates_overlapping_wide_cell(self):
        state=self.replay([0xd10043ff,0xf90003e0,0x390007ff,0xf94003e0])
        self.assertNotIn(0,state.registers)
    def test_narrow_halfword_literal_store_load_zero_extends(self):
        state=self.replay([0xd10043ff,0x12800000,0x790003e0,0x794003e1])
        self.assertEqual(state.registers[1],('constant',0xffff,64))


class StableOriginWireTests(unittest.TestCase):
    check=BroadValidationTests.check
    fixture=StableIntegratedWitnessTests.fixture
    def test_old_semantic_seed_cannot_validate_under_selected_stable_profile(self):
        im,fn,c,q=self.fixture()
        self.assertEqual(c['value_facts']['seed']['origin'],'raw_post_call_register:x21')
        c['value_facts']['seed']['origin']='abi_post_call_error:x21'
        result=self.check(im,fn,c,q)
        self.assertFalse(result['eligible']);self.assertEqual(result['reason'],'value_seed')


class GenericPhysicalPrefixTests(unittest.TestCase):
    def test_original_three_formal_registers_are_used_before_control(self):
        from airs.swift_outcome_validator_v2 import _formal_prefix_inputs
        words=(0xa9be4ff4,0x910003fd,0x92400009,0x8b210129,0x8b020134,0x540001ca)
        self.assertTrue(_formal_prefix_inputs(words,['x0','w1','x2']))
    def test_clobbered_formal_register_is_not_recovered_from_later_use(self):
        from airs.swift_outcome_validator_v2 import _formal_prefix_inputs
        words=(0xd2800002,0x92400009,0x8b210129,0x8b020134)
        self.assertFalse(_formal_prefix_inputs(words,['x0','w1','x2']))
    def test_simd_store_data_cannot_attest_integer_formals(self):
        from airs.swift_outcome_validator_v2 import _formal_prefix_inputs
        self.assertFalse(_formal_prefix_inputs((0x3d8003e0,0x3d8007e1,0xd65f03c0),['x0','x1']))
    def test_signed_load_is_destination_write_not_source_store(self):
        from airs.swift_outcome_validator_v2 import _prefix_operand_effects
        reads,writes,control,known=_prefix_operand_effects(0x398003e0)
        self.assertNotIn(0,reads);self.assertIn(0,writes);self.assertTrue(known)
    def test_memory_writeback_invalidates_base_origin(self):
        from airs.swift_outcome_validator_v2 import _prefix_operand_effects
        for word in (0xf8410401,0xa8c10401):
            with self.subTest(word=word):self.assertIn(0,_prefix_operand_effects(word)[1])
    def test_bc_cond_stops_physical_formal_walk(self):
        from airs.swift_outcome_validator_v2 import _formal_prefix_inputs
        self.assertFalse(_formal_prefix_inputs((0x54000010,0xaa0003e1),['x0']))
    def test_unknown_instruction_stops_prefix_instead_of_preserving_unseen_inputs(self):
        from airs.swift_outcome_validator_v2 import _formal_prefix_inputs
        self.assertFalse(_formal_prefix_inputs((0xffffffff,0xaa0003e1),['x0']))
    def test_self_and_zero_error_moves_do_not_corroborate_object_transport(self):
        from airs.swift_outcome_validator_v2 import _is_error_transport_instruction
        self.assertFalse(_is_error_transport_instruction(0xaa1503f5))
        self.assertFalse(_is_error_transport_instruction(0xaa1f03f5))
        self.assertTrue(_is_error_transport_instruction(0xaa0003f5))
    def test_only_store_encodings_corroborate_indirect_result_buffer(self):
        from airs.swift_outcome_validator_v2 import _is_direct_result_store
        for word in (0xf9800100,0x39800100,0x39c00100,0xf9400100,0x3dc00100):
            with self.subTest(negative=word):self.assertFalse(_is_direct_result_store(word))
        for word in (0xf9000100,0x39000100,0xa9000500,0x3d800100):
            with self.subTest(positive=word):self.assertTrue(_is_direct_result_store(word))


class PrefixReviewFollowupTests(unittest.TestCase):
    check=BroadValidationTests.check
    fixture=StableIntegratedWitnessTests.fixture
    def test_visible_zero_does_not_promote_suffix_to_dominance_proof(self):
        im,fn,c,q=self.fixture()
        result=self.check(im,fn,c,q);self.assertTrue(result['eligible'],result)
        self.assertEqual(result['caller_error_state'],'unproven_profile_precondition')
        self.assertFalse(result['error_state_proven'])
    def test_non_sp_writeback_does_not_establish_formal_prefix_evidence(self):
        from airs.swift_outcome_validator_v2 import _formal_prefix_inputs
        self.assertFalse(_formal_prefix_inputs((0xf8410401,0xaa0003e2),['x0']))
    def test_result_store_qualification_excludes_writeback_and_pair_load(self):
        from airs.swift_outcome_validator_v2 import _is_direct_result_store
        for word in (0xa9400500,0xa9800500,0xa8800500):
            with self.subTest(word=word):self.assertFalse(_is_direct_result_store(word))


class PrefixAllocationTests(unittest.TestCase):
    def test_reserved_integer_encodings_cannot_attest_formal_reads(self):
        from airs.swift_outcome_validator_v2 import _formal_prefix_inputs,_prefix_operand_effects
        # W shifted amount63; ADD shiftROR; extend amount7; W UXTX;
        # ordinary-immediate reserved bit23; reserved bitfield/move-wide controls;
        # logical immediate N/width and all-ones masks; W logical shift32.
        words=(0x0b00fc00,0x8bc00000,0x8b201c00,0x0b206000,0x11800000,
            0x73400000,0x33008000,0x32800000,0x52c00000,0x12400000,0x1200fc00,0x0a008000)
        for word in words:
            with self.subTest(word=hex(word)):
                self.assertFalse(_prefix_operand_effects(word)[3])
                self.assertFalse(_formal_prefix_inputs((word,0xaa0003e1),['x0']))
    def test_allocated_nonflag_shift_and_extend_forms_keep_real_inputs(self):
        from airs.swift_outcome_validator_v2 import _formal_prefix_inputs
        for word in (0x0b007c01,0x8b00fc01,0x8b201001,0x0a00fc01|0x80000000):
            with self.subTest(word=hex(word)):self.assertTrue(_formal_prefix_inputs((word,),['x0']))
    def test_reserved_memory_operand_forms_do_not_attest_input(self):
        from airs.swift_outcome_validator_v2 import _prefix_operand_effects
        for word in (0x39c00100|0x80000000,0x7d800100,0xec000100,0x68000500):
            with self.subTest(word=hex(word)):self.assertFalse(_prefix_operand_effects(word)[3])


class IndependentDirectoryLedgerTests(unittest.TestCase):
    check=BroadValidationTests.check
    def test_raw_directory_charged_once_for_distinct_witness_requests_without_hash(self):
        import json
        import airs.swift_outcome_validator_v2 as validator
        im,fn,c,q=manual_fixture()
        with patch('hashlib.sha256',side_effect=AssertionError('no source hash allowed')):
            with patch.object(validator,'create_independent_swift_image_ledger',wraps=validator.create_independent_swift_image_ledger) as factory:
                ledger=factory(im);first=self.check(im,fn,c,q,_image_ledger=ledger)
                second_candidate=deepcopy(c);second_candidate['limitations'].append('separate_request')
                for _ in range(4):second_candidate['accounting']['encoded_bytes']=len(json.dumps(second_candidate,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii'))
                second=self.check(im,fn,second_candidate,q,_image_ledger=ledger)
                self.assertEqual(factory.call_count,1)
        self.assertTrue(first['eligible'],first);self.assertTrue(second['eligible'],second)
        self.assertGreater(ledger.initial_work_steps,0)
        for result in (first,second):
            self.assertEqual(result['accounting']['image_initial_work'],ledger.initial_work_steps)
            self.assertEqual(result['accounting']['image_work_charged_here'],0)
            self.assertTrue(result['accounting']['image_ledger_reused'])
    def test_standalone_reports_separate_directory_and_witness_budgets(self):
        im,fn,c,q=manual_fixture()
        with patch('hashlib.sha256',side_effect=AssertionError('no source hash allowed')):
            result=self.check(im,fn,c,q)
        self.assertTrue(result['eligible'],result)
        self.assertEqual(result['accounting']['image_work_charged_here'],result['accounting']['image_initial_work'])
        self.assertGreater(result['accounting']['image_work_charged_here'],0)
        self.assertFalse(result['accounting']['image_ledger_reused'])
    def test_directory_is_for_exact_image_object_not_an_equal_copy(self):
        from airs.swift_outcome_validator_v2 import create_independent_swift_image_ledger
        im,fn,c,q=manual_fixture();ledger=create_independent_swift_image_ledger(im)
        copied=replace(im,path='another path')
        self.assertTrue(copied.has_valid_admission())
        result=self.check(copied,fn,c,q,_image_ledger=ledger)
        self.assertFalse(result['eligible']);self.assertEqual(result['reason'],'independent_image_ledger_custody')
    def test_serialized_lookalike_and_copied_ledger_are_not_capabilities(self):
        from types import SimpleNamespace
        from airs.swift_outcome_validator_v2 import create_independent_swift_image_ledger
        im,fn,c,q=manual_fixture();ledger=create_independent_swift_image_ledger(im)
        for fake in (dict(status='ready',initial_work_steps=ledger.initial_work_steps),SimpleNamespace(status='ready'),replace(ledger)):
            with self.subTest(kind=type(fake).__name__):
                result=self.check(im,fn,c,q,_image_ledger=fake)
                self.assertFalse(result['eligible']);self.assertEqual(result['reason'],'independent_image_ledger_custody')
    def test_source_change_cannot_reuse_a_directory_or_mint_without_admission(self):
        from airs.swift_outcome_validator_v2 import create_independent_swift_image_ledger
        im,fn,c,q=manual_fixture();ledger=create_independent_swift_image_ledger(im)
        data=bytearray(im.data);data[256]^=1;changed=replace(im,data=bytes(data))
        with patch('hashlib.sha256',side_effect=AssertionError('no source hash allowed')):
            refused=create_independent_swift_image_ledger(changed)
            result=self.check(changed,fn,c,q,_image_ledger=ledger)
        self.assertEqual(refused.reason,'image_admission_custody');self.assertFalse(result['eligible'])
    def test_factory_limits_and_partial_directories_never_validate(self):
        from airs.swift_outcome_validator_v2 import create_independent_swift_image_ledger
        im,fn,c,q=manual_fixture()
        for budget in (0,20,100):
            with self.subTest(budget=budget):
                ledger=create_independent_swift_image_ledger(im,max_work=budget)
                self.assertNotEqual(ledger.status,'ready');self.assertLessEqual(ledger.initial_work_steps,budget)
                result=self.check(im,fn,c,q,_image_ledger=ledger);self.assertFalse(result['eligible'])
        for invalid in (-1,262145,True):
            self.assertNotEqual(create_independent_swift_image_ledger(im,max_work=invalid).status,'ready')
    def test_directory_retains_only_immutable_raw_metadata(self):
        from dataclasses import FrozenInstanceError
        from airs.swift_outcome_validator_v2 import create_independent_swift_image_ledger
        im,fn,c,q=manual_fixture();ledger=create_independent_swift_image_ledger(im)
        with self.assertRaises(TypeError):ledger.boundaries[fn.start]=fn.end+4
        with self.assertRaises(TypeError):ledger.sections[0]['offset']=0
        with self.assertRaises(FrozenInstanceError):ledger.initial_work_steps=0
        self.assertNotIn('cfg',ledger.__dataclass_fields__);self.assertNotIn('abi',ledger.__dataclass_fields__)


class ScalarResultAllocationTests(unittest.TestCase):
    def test_reserved_scalar_result_encodings_do_not_count_as_writes(self):
        from airs.swift_outcome_validator_v2 import _allocated_result_gpr_write
        for word in (0x0b00fc00,0x8bc00000,0x32800000,0x0a00fc00,0x1a800800,0x1a80f000,0x3b000000):
            with self.subTest(word=hex(word)):self.assertFalse(_allocated_result_gpr_write(word,0))
    def test_allocated_csel_madd_and_move_are_separate_result_writes(self):
        from airs.swift_outcome_validator_v2 import _allocated_result_gpr_write
        for word in (0x1a800000,0x1b000000,0xd2800020,0x8b00fc00):
            with self.subTest(word=hex(word)):self.assertTrue(_allocated_result_gpr_write(word,0))


class NewPrimitiveConsumerTests(unittest.TestCase):
    replay=IndependentReplayBreadthTests.replay
    def test_xadd_register_retains_both_input_origins(self):
        state=self.replay([0xd2800021,0x8b010000])
        self.assertEqual(state.registers[0][0],'add')
        self.assertEqual(state.registers[0][1],('call_result','0x1000',64))
    def test_unknown_raw_base_load_kills_destination_and_store_invalidates_cells(self):
        state=self.replay([0xd10043ff,0xf90003e0,0xf9000101,0xf9400100])
        self.assertNotIn(0,state.registers);self.assertEqual(state.cells,{})
    def test_signed_unscaled_frame_spill_reloads_original_result(self):
        state=self.replay([0xd10083ff,0x910083fd,0xf81f83a0,0xd2800000,0xf85f83a0])
        self.assertEqual(state.registers[0],('call_result','0x1000',64))
    def test_q_store_invalidates_scalar_stack_origin(self):
        state=self.replay([0xd10083ff,0xf90003e0,0x3d8003e0,0xf94003e0])
        self.assertNotIn(0,state.registers)
    def test_movi_v0_leaves_x0_origin_untouched(self):
        state=self.replay([0x0f0267e0])
        self.assertEqual(state.registers[0],('call_result','0x1000',64))


class BrkTerminalIndependentTests(unittest.TestCase):
    check=BroadValidationTests.check
    def fixture(self):
        return expanded_manual_fixture([(0,'bl'),(0xb4000075,'xcbz'),(0xd4200020,'brk'),
            (0xd65f03c0,'ret'),(0xd65f03c0,'ret')],{1:[4,2]},4,2)
    def test_brk_is_external_terminal_without_return_or_fallthrough_claim(self):
        im,fn,c,q=self.fixture();result=self.check(im,fn,c,q)
        self.assertTrue(result['eligible'],result)
        self.assertEqual(result['exception_observations'],[dict(arm='error',pc='0x1008',exception='breakpoint',resume_proven=False)])
        self.assertTrue(all(record['arm']!='error' for record in result['return_observations']))
        self.assertFalse(result['exception_resume_proven'])
    def test_exception_handling_cannot_be_claimed_modeled(self):
        im,fn,c,q=self.fixture();c['cfg']['external_exception_handling_unmodeled']=False
        result=self.check(im,fn,c,q);self.assertFalse(result['eligible'])
        self.assertEqual(result['reason'],'cfg_exception_facts')
    def test_forged_exception_word_and_resume_claim_cannot_validate(self):
        for path,value in [(('cfg','exception_transfers',0,'word'),'0xd4200040'),
            (('cfg','exception_transfers',0,'resume_proven'),True),
            (('cfg','edges',3,'target_pc'),'0x100c')]:
            with self.subTest(path=path):
                im,fn,c,q=self.fixture();assign(c,path,value);result=self.check(im,fn,c,q)
                self.assertFalse(result['eligible'])


class BroadFullIdentityTests(unittest.TestCase):
    check=BroadValidationTests.check
    def test_all_four_new_identity_coordinates_match_admitted_image(self):
        im,fn,c,q=manual_fixture();result=self.check(im,fn,c,q)
        self.assertTrue(result['eligible'],result)
        self.assertIsNone(c['identity']['uuid'])
        self.assertEqual(c['identity']['preferred_base'],hex(im.preferred_base))
        self.assertEqual((c['identity']['slice_index'],c['identity']['container_slice_count']),(0,1))
    def test_new_coordinates_and_explicit_nullable_uuid_are_mandatory(self):
        for field,value in [('uuid','forged-uuid'),('preferred_base','0x1000'),('slice_index',1),('slice_index',False),
            ('container_slice_count',2),('container_slice_count',True)]:
            with self.subTest(field=field,value=value):
                im,fn,c,q=manual_fixture();c['identity'][field]=value;result=self.check(im,fn,c,q)
                self.assertFalse(result['eligible']);self.assertEqual(result['reason'],'image_identity')
        im,fn,c,q=manual_fixture();del c['identity']['uuid'];result=self.check(im,fn,c,q)
        self.assertFalse(result['eligible']);self.assertEqual(result['reason'],'image_identity')


class SixIntegrationResidualTests(unittest.TestCase):
    replay=IndependentReplayBreadthTests.replay
    def test_unsigned_bitfield_exact_literal_wrap_and_symbolic_unknown(self):
        from airs.swift_outcome_validator_v2 import _ScalarReplay
        from airs.swift_broad_instructions import decode_instruction
        for immr,imms,expected in [(4,7,15),(63,62,486)]:
            with self.subTest(immr=immr):
                word=0xd3400000|(immr<<16)|(imms<<10)
                state=self.replay([0xd2801e60,word])
                self.assertEqual(state.registers[0],('constant',expected,64))
        state=self.replay([0xd37ff800]);self.assertEqual(state.registers[0][0],'unsigned_bitfield')
        unknown=self.replay([0xd340fc20]);self.assertNotIn(0,unknown.registers)
    def test_unsigned_word_bitfield_zero_extends_without_source_value_invention(self):
        state=self.replay([0xd2801e60,0x53041c00])
        self.assertEqual(state.registers[0],('constant',15,64))
    def test_private_weak_visibility_requires_exact_flags_bl_and_concrete_bindings(self):
        from airs.swift_outcome_validator_v2 import _symbol_visibility_allowed
        from airs.swift_declaration_profiles import parse_broad_declaration
        symbol='_$s10BroadOwned0A9Owner0363V15broad_case_0363ySis5Int32V_s6UInt64VSixtKSzRzlFZSi_Tt3g5'
        concrete=parse_broad_declaration(symbol).identity
        ordinary=parse_broad_declaration('_$s4Test3fooyS2iKF').identity
        self.assertTrue(_symbol_visibility_allowed(0x1e,0x80,concrete,'bl'))
        for kind,desc,decl,call_kind in [(0x1e,0,concrete,'bl'),(0x1e,0x81,concrete,'bl'),
            (0x1e,0x80,ordinary,'bl'),(0x1e,0x80,concrete,'b'),(0xf,0x80,ordinary,'bl')]:
            with self.subTest(kind=kind,desc=desc,call=call_kind):self.assertFalse(_symbol_visibility_allowed(kind,desc,decl,call_kind))
    def test_unrelated_indirect_parent_is_skipped_but_matching_raw_chain_is_exact(self):
        from types import SimpleNamespace
        from airs.swift_outcome_validator_v2 import _validate_nominal_context,_Stop
        data=bytearray(256)
        struct.pack_into('<ii',data,0,32,60)
        struct.pack_into('<Iii',data,32,17,1,168)  # Other leaf: unsupported indirect parent.
        struct.pack_into('<Iii',data,64,17,28,73)  # Owner name at odd address0x2091.
        struct.pack_into('<IIi',data,96,0,0,24)
        data[128:133]=b'Test\0';data[145:151]=b'Owner\0';data[208:214]=b'Other\0'
        sections=[dict(segment='__TEXT',name='__swift5_types',address=0x2000,end=0x2008,size=8,offset=0,flags=0),
            dict(segment='__TEXT',name='__const',address=0x2008,end=0x2100,size=248,offset=8,flags=0)]
        decl=SimpleNamespace(module='Test',context=(SimpleNamespace(name='Owner',kind='struct'),))
        def need(ok,reason,status='declined'):
            if not ok:raise _Stop(reason,status)
        result=_validate_nominal_context(None,decl,sections,lambda off,n:bytes(data[off:off+n]),lambda n=1:None,need,BroadWitnessLimits())
        self.assertEqual(result['entry_pc'],'0x2004');self.assertEqual(result['records'][0]['name_pc'],'0x2091')
        self.assertEqual(result['records'][0]['raw_descriptor'],bytes(data[64:92]).hex())
        self.assertEqual(result['records'][0]['raw_name'],b'Owner\0'.hex())
        struct.pack_into('<i',data,68,1)
        with self.assertRaises(_Stop):_validate_nominal_context(None,decl,sections,lambda off,n:bytes(data[off:off+n]),lambda n=1:None,need,BroadWitnessLimits())


class PrivateWeakRawImageRegressionTests(unittest.TestCase):
    check=BroadValidationTests.check
    def fixture(self,kind=0x1e,desc=0x80,aliases=1):
        from airs.macho import parse_macho
        im,fn,c,q=manual_fixture();data=bytearray(im.data)
        symbol='_$s10BroadOwned0A9Owner0363V15broad_case_0363ySis5Int32V_s6UInt64VSixtKSzRzlFZSi_Tt3g5'
        raw=symbol.encode()+b'\0'
        data[769:769+len(raw)]=raw;struct.pack_into('<I',data,204,len(raw)+1)
        struct.pack_into('<I',data,196,aliases)
        for i in range(aliases):struct.pack_into('<IBBHQ',data,512+16*i,1,kind,1,desc,0x1010)
        # Keep the function-start payload distinct from the longer symbol.
        data[960:964]=data[900:904];struct.pack_into('<I',data,216,960)
        im=parse_macho(bytes(data),'fresh exact weak-private nlist fixture');fn=im.functions[0]
        c['identity'].update(slice_sha256=im.slice_sha256,container_sha256=im.container_sha256)
        c['call']['declaration']=dict(status='syntax_admitted',identity=asdict(parse_broad_declaration(symbol).identity),reason=None)
        q=replace(q,slice_sha256=im.slice_sha256)
        return im,fn,c,q
    def test_sole_raw_private_weak_specialization_reaches_independent_abi_check(self):
        im,fn,c,q=self.fixture();result=self.check(im,fn,c,q)
        self.assertEqual(result['facts']['call'],'checked_direct_target_and_exact_symbol_syntax')
        self.assertFalse(result['eligible']);self.assertEqual(result['reason'],'abi_tuple_identity')
    def test_other_visibility_and_all_entry_aliases_remain_rejected(self):
        for kind,desc,aliases,reason in [(0x1e,0,1,'symbol_visibility'),(0x1f,0x80,1,'symbol_visibility'),
            (0x1e,0x80,2,'symbol_aliases')]:
            with self.subTest(kind=kind,aliases=aliases):
                im,fn,c,q=self.fixture(kind,desc,aliases);result=self.check(im,fn,c,q)
                self.assertFalse(result['eligible']);self.assertEqual(result['reason'],reason)


class BoundedNominalCStringTests(unittest.TestCase):
    def read_context(self,data,sections,*,limits=None):
        from types import SimpleNamespace
        from airs.swift_outcome_validator_v2 import _validate_nominal_context,_Stop
        work=[0];reads=[]
        def charge(n=1):
            work[0]+=n
            if work[0]>65536:raise _Stop('test_nominal_work_limit','unresolved')
        def read(offset,n):
            charge(n+1);reads.append((offset,n))
            if not 0<=offset<=len(data)-n:raise _Stop('test_extent','unresolved')
            return bytes(data[offset:offset+n])
        def need(ok,reason,status='declined'):
            if not ok:raise _Stop(reason,status)
        decl=SimpleNamespace(module='Test',context=(SimpleNamespace(name='Owner',kind='struct'),))
        result=_validate_nominal_context(None,decl,sections,read,charge,need,limits or BroadWitnessLimits())
        return result,work[0],reads
    def test_many_unrelated_names_have_bounded_directory_and_chunk_work(self):
        count=441;descriptor_offset=2048;name_offset=18000
        data=bytearray(33000)
        for i in range(count):
            entry=0x2000+4*i;descriptor=0x10000+32*i;name=0x20000+32*i
            struct.pack_into('<i',data,4*i,descriptor-entry)
            parent=(0x10000+32*count)-(descriptor+4) if i==count-1 else 1
            struct.pack_into('<Iii',data,descriptor_offset+32*i,17,parent,name-(descriptor+8))
            raw=(b'Owner' if i==count-1 else f'UnrelatedOwner_{i:04d}'.encode())+b'\0'
            data[name_offset+32*i:name_offset+32*i+len(raw)]=raw
        module=0x10000+32*count;module_name=0x20000+32*count
        struct.pack_into('<IIi',data,descriptor_offset+32*count,0,0,module_name-(module+8))
        data[name_offset+32*count:name_offset+32*count+5]=b'Test\0'
        sections=[dict(segment='__TEXT',name='__swift5_types',address=0x2000,end=0x2000+4*count,size=4*count,offset=0,flags=0),
            dict(segment='__TEXT',name='__const',address=0x10000,end=module+16,size=32*count+16,offset=descriptor_offset,flags=0),
            dict(segment='__TEXT',name='__cstring',address=0x20000,end=module_name+32,size=32*(count+1),offset=name_offset,flags=0)]
        sections.extend(dict(segment='__TEXT',name=f'__other{i}',address=0x30000+0x1000*i,end=0x30008+0x1000*i,size=8,offset=0,flags=0) for i in range(20))
        result,work,reads=self.read_context(data,sections)
        self.assertLess(work,40000)
        self.assertEqual(result['records'][0]['raw_name'],b'Owner\0'.hex())
        self.assertEqual(result['records'][0]['raw_descriptor'],bytes(data[descriptor_offset+32*(count-1):descriptor_offset+32*(count-1)+28]).hex())
        self.assertLess(len(reads),2000)
    def string_fixture(self,raw,name_size):
        data=bytearray(800)
        struct.pack_into('<i',data,0,32);struct.pack_into('<Iii',data,32,17,60,104)
        struct.pack_into('<IIi',data,96,0,0,24);data[128:133]=b'Test\0';data[144:144+len(raw)]=raw
        sections=[dict(segment='__TEXT',name='__swift5_types',address=0x2000,end=0x2004,size=4,offset=0,flags=0),
            dict(segment='__TEXT',name='__const',address=0x2004,end=0x2090,size=140,offset=4,flags=0),
            dict(segment='__TEXT',name='__cstring',address=0x2090,end=0x2090+name_size,size=name_size,offset=144,flags=0),
            dict(segment='__TEXT',name='__after',address=0x2090+name_size,end=0x2300,size=0x270-name_size,offset=144+name_size,flags=0)]
        return data,sections
    def test_final_section_byte_nul_is_retained_exactly(self):
        result,work,reads=self.read_context(*self.string_fixture(b'Owner\0',6))
        self.assertEqual(result['records'][0]['raw_name'],b'Owner\0'.hex())
        self.assertTrue(all(not (offset==144 and n>6) for offset,n in reads))
    def test_cstring_cannot_cross_mapping_even_to_adjacent_nul(self):
        from airs.swift_outcome_validator_v2 import _Stop
        with self.assertRaises(_Stop) as refused:self.read_context(*self.string_fixture(b'Owner\0',3))
        self.assertEqual(refused.exception.reason,'nominal_name_extent')
    def test_malformed_and_unterminated_names_stay_unresolved(self):
        from airs.swift_outcome_validator_v2 import _Stop
        for raw,size,reason in [(b'\0',1,'nominal_empty_name'),(b'\xff\0',2,'nominal_name_encoding'),
            (b'A'*256+b'\0',257,'nominal_name_limit')]:
            with self.subTest(reason=reason):
                with self.assertRaises(_Stop) as refused:self.read_context(*self.string_fixture(raw,size))
                self.assertEqual(refused.exception.reason,reason)


class TypedLogicalAndSelectTests(unittest.TestCase):
    replay=IndependentReplayBreadthTests.replay
    def test_decoded_logical_immediate_literals_and_word_zero_extension(self):
        state=self.replay([0xd2801e60,0x12000000,0x32001c00,0x52000000])
        self.assertEqual(state.registers[0],('constant',254,64))
        state=self.replay([0x12800000,0x72000000])
        self.assertEqual(state.registers[0],('constant',1,64))
    def test_logical_symbolic_transform_and_unknown_are_distinct(self):
        state=self.replay([0x92400000])
        self.assertEqual(state.registers[0],('and',('call_result','0x1000',64),('constant',1,64),64))
        state=self.replay([0x92400020]);self.assertNotIn(0,state.registers)
    def test_flag_only_add_sub_and_logical_to_zr_do_not_write_sp_or_result(self):
        for word in (0x7100011f,0xb100041f,0xf100041f,0x3100041f,0x7200001f):
            with self.subTest(word=hex(word)):
                state=self.replay([word]);self.assertEqual(state.sp,0)
                self.assertEqual(state.registers[0],('call_result','0x1000',64))
                self.assertNotIn(31,state.registers)
    def test_all_select_family_destinations_are_unknown_without_nzcv(self):
        for word in (0x1a800000,0x1a800400,0x5a800000,0x5a800400,
            0x9a800000,0x9a880500,0xda800000,0xda800400):
            with self.subTest(word=hex(word)):
                state=self.replay([word]);self.assertNotIn(0,state.registers)
    def test_value_refusal_retains_one_bounded_raw_instruction_diagnostic(self):
        from airs.swift_outcome_validator_v2 import _Stop
        with self.assertRaises(_Stop) as refused:self.replay([0x9ac00800])
        self.assertEqual(refused.exception.instruction,dict(pc='0x1004',word='0x9ac00800',kind='xudiv'))


class ValueRefusalDiagnosticIntegrationTests(unittest.TestCase):
    check=BroadValidationTests.check
    def test_unmodeled_value_operator_has_raw_diagnostic_within_result_cap(self):
        import json
        im,fn,c,q=expanded_manual_fixture([(0,'bl'),(0xb4000075,'xcbz'),(0x9ac00800,'xudiv'),
            (0xd65f03c0,'ret'),(0xd65f03c0,'ret')],{1:[4,2]},4,2)
        result=self.check(im,fn,c,q)
        self.assertFalse(result['eligible']);self.assertEqual(result['reason'],'value_transfer_unqualified')
        self.assertEqual(result['unresolved_instruction'],dict(pc='0x1008',word='0x9ac00800',kind='xudiv'))
        self.assertLessEqual(len(json.dumps(result).encode()),BroadWitnessLimits().max_bytes)


class IndependentSelectedLineageTests(unittest.TestCase):
    check_storage=StableStorageIndependentTests.check_storage
    def second_slice(self):
        from airs.swift_abi_profiles import OWNED_SOURCE_BY_SLICE,_V2_SLICES
        return next(digest for digest in OWNED_SOURCE_BY_SLICE if digest not in _V2_SLICES)
    def test_second_selected_custom_storage_uses_its_actual_source_without_reference_pc_reads(self):
        from airs.swift_abi_profiles import OWNED_SOURCE_BY_SLICE,_V2_SOURCE
        selected=self.second_slice();reads=[]
        self.assertNotEqual(OWNED_SOURCE_BY_SLICE[selected],_V2_SOURCE)
        def family(abi):abi.update(family='free',family_evidence=dict(source_sha256=OWNED_SOURCE_BY_SLICE[selected],
            compiled_target_pc='0x1020',direct_call_pc='0x1004',scope='source_lineage_plus_exact_emitted_target_not_runtime_dispatch'))
        self.check_storage('BroadOwned.BroadSmall',[0xaa0003f5,0xa9000500,0xd65f03c0],selected_slice=selected,mutate=family,observed_reads=reads)
        self.assertEqual(reads,[(0x1020,12)])
    def test_selected_and_reference_lineage_cannot_be_swapped_or_omitted(self):
        from airs.swift_abi_profiles import OWNED_SOURCE_BY_SLICE,_V2_SOURCE,_V2_SLICES
        from airs.swift_outcome_validator_v2 import _Stop
        selected=self.second_slice();actual=OWNED_SOURCE_BY_SLICE[selected];reference=sorted(_V2_SLICES)[0]
        changes=[('selected_source_sha256',_V2_SOURCE),('selected_slice_sha256',reference),
            ('source_sha256',actual),('reference_slice_sha256',selected),('selected_source_sha256',None)]
        for key,value in changes:
            with self.subTest(key=key,value=value):
                with self.assertRaises(_Stop):self.check_storage('Swift.Int',[0xaa0003f5,0xd2800020,0xd65f03c0],
                    selected_slice=selected,mutate=lambda abi:abi['evidence']['lowering'].update({key:value}))
        for missing in ('selected_source_sha256','selected_slice_sha256'):
            with self.subTest(missing=missing):
                with self.assertRaises(_Stop):self.check_storage('Swift.Int',[0xaa0003f5,0xd2800020,0xd65f03c0],
                    selected_slice=selected,mutate=lambda abi:abi['evidence']['lowering'].pop(missing))
    def test_second_family_source_cannot_claim_primary_lineage(self):
        from airs.swift_abi_profiles import _V2_SOURCE
        from airs.swift_outcome_validator_v2 import _Stop
        selected=self.second_slice()
        def wrong_family(abi):abi.update(family='free',family_evidence=dict(source_sha256=_V2_SOURCE,
            compiled_target_pc='0x1020',direct_call_pc='0x1004',scope='source_lineage_plus_exact_emitted_target_not_runtime_dispatch'))
        with self.assertRaises(_Stop):self.check_storage('Swift.Int',[0xaa0003f5,0xd2800020,0xd65f03c0],selected_slice=selected,mutate=wrong_family)
    def test_second_generic_rule_still_requires_real_formal_reads_and_tag_store(self):
        from types import SimpleNamespace
        from airs.swift_outcome_validator_v2 import _validate_stable_abi,_Stop
        from airs.swift_broad_instructions import decode_instruction
        from airs.swift_abi_profiles import OWNED_SOURCE_BY_SLICE
        selected=self.second_slice()
        symbol='_$s10BroadOwned0A9Owner0340V15broad_case_0340yAA0A3TagOSb_s5UInt8VxtKSzRzlFZSi_Tt3g5'
        declaration=parse_broad_declaration(symbol).identity
        self.assertIsNotNone(declaration.specialization)
        abi=stable_manual_record('BroadOwned.BroadTag',selected_slice=selected,word_count=6)
        abi['evidence']['lowering']['specialization']=asdict(declaration.specialization)
        abi['argument_storage']=[dict(type=t,locations=[loc],evidence_id=evidence,inout=False) for t,loc,evidence in
            [('Swift.Bool','w0','swift-stable-v2-bool'),('Swift.UInt8','w1','swift-stable-v2-uint8'),('Swift.Int','x2','swift-stable-v2-int')]]
        abi['argument_locations']=[['w0'],['w1'],['x2']]
        abi.update(family='concrete_generic_specialization',family_evidence=dict(source_sha256=OWNED_SOURCE_BY_SLICE[selected],
            compiled_target_pc='0x1020',direct_call_pc='0x1004',scope='source_lineage_plus_exact_emitted_target_not_runtime_dispatch'))
        words=(0x92400009,0x8b210129,0x8b020134,0xaa0003f5,0x39000109,0xd65f03c0)
        raw=struct.pack('<'+'I'*len(words),*words);reads=[]
        def need(ok,reason,status='declined'):
            if not ok:raise _Stop(reason,status)
        def read(pc,n):reads.append((pc,n));return raw[pc-0x1020:pc-0x1020+n]
        result,_=_validate_stable_abi(SimpleNamespace(slice_sha256=selected),FunctionRange(0x1000,0x1010,'caller','lc_function_starts'),
            FunctionRange(0x1020,0x1038,'target','lc_function_starts'),0x1004,declaration,abi,read,lambda pc,n=4:pc,
            lambda pc:decode_instruction(0xd2800015,pc),lambda n=1:None,need,BroadWitnessLimits())
        self.assertEqual(result['category'],'resilient_tag_enum');self.assertEqual(reads,[(0x1020,24)])
        raw=struct.pack('<'+'I'*len(words),0xd2800002,*words[1:])
        with self.assertRaises(_Stop):_validate_stable_abi(SimpleNamespace(slice_sha256=selected),FunctionRange(0x1000,0x1010,'caller','lc_function_starts'),
            FunctionRange(0x1020,0x1038,'target','lc_function_starts'),0x1004,declaration,abi,read,lambda pc,n=4:pc,
            lambda pc:decode_instruction(0xd2800015,pc),lambda n=1:None,need,BroadWitnessLimits())
    def test_unowned_selected_source_none_is_explicit_and_does_not_grant_custom_storage(self):
        from airs.swift_outcome_validator_v2 import _Stop
        self.check_storage('Swift.UInt8',[0xaa0003f5,0x52800020,0xd65f03c0])
        with self.assertRaises(_Stop):self.check_storage('Swift.UInt8',[0xaa0003f5,0x52800020,0xd65f03c0],
            mutate=lambda abi:abi['evidence']['lowering'].pop('selected_source_sha256'))
        with self.assertRaises(_Stop):self.check_storage('BroadOwned.BroadSmall',[0xaa0003f5,0xa9000500,0xd65f03c0])

class B11SelectedArmWritebackTests(unittest.TestCase):
    def test_unknown_constant_writeback_return_is_explicit_unknown(self):
        specs=[(0,'bl'),(0xb4000055,'xcbz'),(0xd65f03c0,'ret'),
            (0xd284001d,'movz'),(0xa8c10ba1,'ldp'),(0xaa1d03e0,'mov'),(0xd65f03c0,'ret')]
        image,fn,candidate,q=expanded_manual_fixture(specs,{1:[3,2]},3,2)
        with patch('airs.swift_abi_profiles.LOWERING_QUALIFICATIONS',MappingProxyType({q.evidence_id:q})):
            result=validate_broad_swift_witness(image,fn,candidate)
        self.assertTrue(result['eligible'],result)
        success=next(row for row in result['return_observations'] if row['arm']=='success')
        self.assertEqual(success['value'],['unknown',64])
        self.assertEqual(success['raw_error_register_value'],['error_result','0x1000',64])
        self.assertFalse(success['runtime_propagation_proven']);self.assertFalse(success['source_handler_proven'])

    def test_writeback_error_alias_cannot_qualify_selected_zero_test(self):
        specs=[(0,'bl'),(0xaa1503fd,'mov'),(0xa8c10ba1,'ldp'),
            (0xb400005d,'xcbz'),(0xd65f03c0,'ret'),(0xd65f03c0,'ret')]
        image,fn,candidate,q=expanded_manual_fixture(specs,{3:[5,4]},5,4)
        candidate['post_call']['test_register']='x29'
        # The replay rejects the stale alias before candidate observation/size
        # comparison; the independent reason pins the repaired transfer.
        with patch('airs.swift_abi_profiles.LOWERING_QUALIFICATIONS',MappingProxyType({q.evidence_id:q})):
            result=validate_broad_swift_witness(image,fn,candidate)
        self.assertFalse(result['eligible']);self.assertEqual(result['reason'],'error_register_alias')



class Repair2RegisterArithmeticTests(unittest.TestCase):
    replay=IndependentReplayBreadthTests.replay
    def test_shifted_flag_arithmetic_to_zr_has_no_gpr_or_sp_destination(self):
        for word in (0xeb09011f,0xab01001f,0x6b01001f,0x2b01001f):
            with self.subTest(word=hex(word)):
                state=self.replay([word]);self.assertEqual(state.sp,0)
                self.assertEqual(state.registers[0],('call_result','0x1000',64));self.assertNotIn(31,state.registers)
    def test_shifted_flag_arithmetic_literals_sign_and_word_width(self):
        state=self.replay([0xd2800060,0xd2800041,0xab010800])
        self.assertEqual(state.registers[0],('constant',11,64))
        state=self.replay([0xd2800060,0x92800001,0xeb810800])
        self.assertEqual(state.registers[0],('constant',4,64))
        state=self.replay([0x12800000,0x52800021,0x2b010000])
        self.assertEqual(state.registers[0],('constant',0,64))
    def test_shifted_arithmetic_origins_and_unknown_are_not_interchangeable(self):
        state=self.replay([0xd2800041,0xab010000])
        self.assertEqual(state.registers[0],('add',('call_result','0x1000',64),('constant',2,64),64))
        state=self.replay([0xab020020]);self.assertNotIn(0,state.registers)
    def test_logical_register_width_and_inverted_operand_are_exact(self):
        state=self.replay([0xd2801e60,0xd28001e1,0x0a010000])
        self.assertEqual(state.registers[0],('constant',3,64))
        state=self.replay([0xd2801e60,0xd28001e1,0x0a210000])
        self.assertEqual(state.registers[0],('constant',240,64))
    def test_raw_invalid_shift_encodings_remain_decoder_refusals(self):
        from airs.swift_broad_instructions import decode_instruction
        from airs.arm64 import ModelError
        for word in (0x2b00fc00,0xabc00000,0x0a00fc00):
            with self.subTest(word=hex(word)):
                with self.assertRaises(ModelError):decode_instruction(word,0x1004)


class Repair2BoundedSuffixAndVisibilityTests(unittest.TestCase):
    def test_midframe_abi_suffix_has_unknown_sp_and_retains_nonzero_refusal(self):
        from types import SimpleNamespace
        from airs.swift_outcome_validator_v2 import _validate_stable_abi,_Stop
        from airs.swift_broad_instructions import decode_instruction
        declaration=replace(parse_broad_declaration('_$s4Test3fooyS2iKF').identity,parameter_types=())
        abi=stable_manual_record('Swift.Int',entry_pc=0x1200);raw=struct.pack('<III',0xaa0003f5,0xd2800020,0xd65f03c0)
        def need(ok,reason,status='declined'):
            if not ok:raise _Stop(reason,status)
        def check(last):
            def instruction(pc):return decode_instruction(0xb90033e0 if pc==0x1070 else (last if pc==0x10ec else 0xd503201f),pc)
            return _validate_stable_abi(SimpleNamespace(slice_sha256='fresh synthetic non-owned source'),
                FunctionRange(0x1000,0x1100,'caller','lc_function_starts'),FunctionRange(0x1200,0x120c,'callee','lc_function_starts'),
                0x10f0,declaration,abi,lambda pc,n:raw[pc-0x1200:pc-0x1200+n],lambda pc,n=4:pc,instruction,lambda n=1:None,need,BroadWitnessLimits())
        result,state=check(0xd2800015);self.assertEqual(state,'unproven_profile_precondition')
        with self.assertRaises(_Stop) as refused:check(0xd2800035)
        self.assertEqual(refused.exception.reason,'caller_error_contract_contradiction')
    def test_private_ordinary_class_static_is_narrow_direct_throwing_implementation(self):
        from airs.swift_outcome_validator_v2 import _symbol_visibility_allowed
        from airs.swift_declaration_profiles import CallableKind
        symbol='_$s10BroadOwned0A9Owner0296C15broad_case_0296AA0A9ReferenceCyKFZ'
        declaration=parse_broad_declaration(symbol).identity;self.assertIsNotNone(declaration)
        self.assertTrue(_symbol_visibility_allowed(30,0,declaration,'bl'))
        variants=[(30,0,declaration,'b'),(14,0,declaration,'bl'),(30,0,replace(declaration,throws=False),'bl'),
            (30,0,replace(declaration,callable_kind=CallableKind.CLASS_INSTANCE_METHOD),'bl'),
            (30,0,replace(declaration,context=()),'bl'),(30,0x80,declaration,'bl')]
        for kind,desc,decl,call in variants:
            with self.subTest(kind=kind,desc=desc,call=call):self.assertFalse(_symbol_visibility_allowed(kind,desc,decl,call))


class Repair2MemoryAndExtendedTests(unittest.TestCase):
    replay=IndependentReplayBreadthTests.replay
    def test_extended_add_sub_sp_and_sign_rules_are_explicit(self):
        state=self.replay([0xd10083ff,0xd2800201,0x8b2143e2,0xcb2143ff])
        self.assertEqual(state.sp,-48);self.assertEqual(state.registers[2],('stack_address',-16,64))
        state=self.replay([0xd28000a0,0x12800001,0x8b21c400])
        self.assertEqual(state.registers[0],('constant',3,64))
    def test_extended_sp_offset_cannot_escape_unique_signed_arm64_coordinate_domain(self):
        from airs.swift_outcome_validator_v2 import _Stop
        with self.assertRaises(_Stop) as refused:self.replay([0xd2f00001,0xcb2163ff])
        self.assertEqual(refused.exception.reason,'stack_offset_unqualified')
    def test_raw_and_unscaled_word_memory_zero_extend_real_cells(self):
        state=self.replay([0xd10043ff,0x910003e9,0x12800000,0xb9000520,0xd2800000,0xb9400520])
        self.assertEqual(state.registers[0],('constant',0xffffffff,64))
        state=self.replay([0xd10043ff,0x910043fd,0xd2824680,0xb81fc3a0,0xd2800000,0xb85fc3a0])
        self.assertEqual(state.registers[0],('constant',0x1234,64))
    def test_scalar_fp_stores_invalidate_overlaps_without_gpr_number_alias(self):
        for store in (0xbd0003e0,0xfd0003e0):
            with self.subTest(store=hex(store)):
                state=self.replay([0xd10043ff,0xf90003e0,store,0xf94003e0])
                self.assertNotIn(0,state.registers)
    def test_fp_load_destinations_are_not_integer_registers(self):
        for load in (0xbd4003e0,0xfd4003e0):
            with self.subTest(load=hex(load)):
                state=self.replay([load]);self.assertEqual(state.registers[0],('call_result','0x1000',64))
    def test_known_sp_writeback_spill_and_reload_retire_the_cell(self):
        state=self.replay([0xf81f0fe0,0xd2800000,0xf84107e0])
        self.assertEqual(state.registers[0],('call_result','0x1000',64));self.assertEqual(state.sp,0);self.assertEqual(state.cells,{})
    def test_known_non_sp_writeback_updates_only_the_pointer(self):
        state=self.replay([0xd10083ff,0x910043e9,0xf81f8d20,0xd2800000,0xf8408520])
        self.assertEqual(state.registers[0],('call_result','0x1000',64));self.assertEqual(state.sp,-32)
        self.assertEqual(state.registers[9],('stack_address',-16,64))


class Repair2LeafErrorConventionTests(unittest.TestCase):
    def test_exact_authored_leaf_preserves_only_the_register_not_its_input_value(self):
        from airs.swift_outcome_validator_v2 import _independent_leaf_preserves_x21
        words=(0x7200005f,0x528000a3,0x1a850083,0x0b020060,0xd65f03c0)
        self.assertTrue(_independent_leaf_preserves_x21(words))
    def test_leaf_predicate_refuses_controls_unknown_and_every_gpr21_write(self):
        from airs.swift_outcome_validator_v2 import _independent_leaf_preserves_x21
        for word in (0x14000000,0x94000000,0x54000000,0xd4200020,0xffffffff,0x0b00fc00,
            0xd2800015,0x1e260015,0xf94007f5,0xa94057f4,0xf8008ea0):
            with self.subTest(word=hex(word)):self.assertFalse(_independent_leaf_preserves_x21((word,0xd65f03c0)))
        self.assertFalse(_independent_leaf_preserves_x21((0xd65f03c0,0xd65f03c0)))
    def test_fp21_and_integer_store21_are_reads_of_different_banks(self):
        from airs.swift_outcome_validator_v2 import _independent_leaf_preserves_x21
        self.assertTrue(_independent_leaf_preserves_x21((0x1e270015,0xf90007f5,0xd65f03c0)))
    def test_copy_mode_metadata_cannot_claim_leaf_or_incoming_state(self):
        from airs.swift_outcome_validator_v2 import _Stop
        check=StableStorageIndependentTests.check_storage
        words=[0xaa0003f5,0x528002e0,0xd65f03c0]
        check(self,'Swift.UInt32',words)
        for key,value in [('mode','preserved_x21_leaf'),('return_pc','0x1028'),('preserves_incoming_x21',True),
            ('incoming_state_proven',True),('word_count',2)]:
            with self.subTest(key=key):
                with self.assertRaises(_Stop):check(self,'Swift.UInt32',words,
                    mutate=lambda abi:abi['evidence']['lowering']['callee_error_observation'].update({key:value}))
    def test_leaf_error_observation_is_independently_recomputed_and_scope_checked(self):
        from types import SimpleNamespace
        from airs.swift_outcome_validator_v2 import _validate_stable_abi,_Stop
        from airs.swift_broad_instructions import decode_instruction
        declaration=replace(parse_broad_declaration('_$s4Test3fooyS2iKF').identity,parameter_types=())
        words=(0xd2800060,0xd65f03c0);raw=struct.pack('<II',*words)
        abi=stable_manual_record('Swift.Int',word_count=2)
        observation=dict(mode='preserved_x21_leaf',register='x21',scope='instruction_effects_if_normal_return_not_incoming_state_or_object_type',
            entry_pc='0x1020',return_pc='0x1024',word_count=2,preserves_incoming_x21=True,incoming_state_proven=False,error_object_type_proven=False)
        abi['evidence']['lowering'].update(callee_error_observation=observation,
            callee_error_transport_observation='x21_preserved_by_exact_straightline_leaf_effects')
        def need(ok,reason,status='declined'):
            if not ok:raise _Stop(reason,status)
        def check(record):return _validate_stable_abi(SimpleNamespace(slice_sha256='fresh synthetic non-owned source'),
            FunctionRange(0x1000,0x1010,'caller','lc_function_starts'),FunctionRange(0x1020,0x1028,'callee','lc_function_starts'),0x1004,
            declaration,record,lambda pc,n:raw[pc-0x1020:pc-0x1020+n],lambda pc,n=4:pc,
            lambda pc:decode_instruction(0xd2800015,pc),lambda n=1:None,need,BroadWitnessLimits())
        result,state=check(abi);self.assertEqual(state,'unproven_profile_precondition')
        forged=deepcopy(abi);forged['evidence']['lowering']['callee_error_observation']['incoming_state_proven']=True
        with self.assertRaises(_Stop):check(forged)

if __name__=='__main__':unittest.main()
