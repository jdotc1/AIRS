"""Independent, bounded byte replay for broad Swift candidates.

Only wire primitives, the instruction decoder, exact syntax parser and frozen
qualification records are shared with producers. Cached CFG, value and admission
ledgers are assertions to check, never proof. Existing admitted image digests are
reused; this module neither hashes sealed sources nor executes the image.
"""
from dataclasses import asdict, replace, dataclass
import re
import struct
from .swift_outcome_witness_v2_models import BroadWitnessLimits, preflight_broad_json


class _Stop(Exception):
    def __init__(self, reason, status='declined'):
        self.reason, self.status = reason, status



_LEDGER_AUTHORITY=object()  # issuer identity, never a cache or retained image


@dataclass(frozen=True,slots=True)
class _IndependentImageLedger:
    _issuer: object
    _image: object
    _data: object
    _functions: object
    _sections: object
    _seal: object
    status: str
    reason: str | None
    initial_work_steps: int
    sections: object
    starts: tuple
    boundaries: object
    function_index: object
    symbol_table: tuple | None
    symbols: object
    _receipt: object = None

    def matches(self,image):
        return (type(self._receipt) is tuple and len(self._receipt)==10 and self._receipt[0] is self
            and self._receipt[1] is self.sections and self._receipt[2] is self.boundaries
            and self._receipt[3] is self.function_index and self._receipt[4] is self.symbol_table
            and self._receipt[5] is self.symbols and self._receipt[6] is self.starts
            and self._receipt[7:]==(self.status,self.reason,self.initial_work_steps)
            and self._issuer is _LEDGER_AUTHORITY and self._image is image and self._data is image.data
            and self._functions is image.functions and self._sections is image.sections
            and self._seal is image._admission_seal and image.has_valid_admission())


def create_independent_swift_image_ledger(image,*,max_work=262144):
    """Build one invocation-owned raw directory ledger; no producer facts/hash.

    The opaque object is a local capability for one exact admitted image. JSON,
    dictionaries and reconstructed lookalikes are not accepted by validation.
    Initial work is separately bounded and exposed once to the invocation owner.
    No global image/session cache exists. Selected strings and all call/value/
    context/CFG facts remain independently read and checked for each witness.
    """
    from types import MappingProxyType
    from bisect import bisect_right
    work=0;sections=[];ordered=[];section_addresses=[];starts=[];boundaries={};function_index={};symbols={};table=None
    status='ready';reason=None;limits=BroadWitnessLimits(max_work=262144,max_blocks=4096)
    def need(ok,reason,status='declined'):
        if not ok:raise _Stop(reason,status)
    def charge(n=1):
        nonlocal work
        need(n>=0 and n<=max_work-work,'validator_image_work_limit','unresolved');work+=n
    def read(off,n):
        charge(n+1);need(type(off) is int and 0<=off<=len(image.data) and 0<=n<=len(image.data)-off
            and off+n<=image.slice_size,'raw_extent');return image.data[off:off+n]
    def unpack(fmt,off):return struct.unpack(fmt,read(off,struct.calcsize(fmt)))
    def mapped(pc,n=4):
        charge(max(1,len(ordered).bit_length()));need(type(pc) is int and 0<=pc<=2**64-n,'vm_extent')
        index=bisect_right(section_addresses,pc)-1
        need(index>=0 and pc+n<=ordered[index]['end'],'raw_mapping_ambiguous');section=ordered[index]
        need(section['executable'] and section['flags']&255 not in (1,8,12,18)
            and 'stub' not in section['name'].lower(),'raw_mapping_not_executable')
        return section['offset']+pc-section['address']
    try:
        need(type(max_work) is int and 0<=max_work<=262144,'invalid_image_ledger_limit')
        need(image.has_valid_admission(),'image_admission_custody','unresolved')
        need(image.architecture=='arm64' and image.cpu_subtype in (0,1),'ordinary_arm64_required')
        need(image.slice_size==len(image.data) and image.slice_offset>=0,'slice_extent')
        magic,cpu,subtype,filetype,ncmds,cmdbytes,flags,reserved=unpack('<IiiIIIII',0)
        need((magic,cpu,subtype,filetype)==(0xfeedfacf,0x100000c,image.cpu_subtype,image.file_type),'raw_header_identity')
        need(ncmds<=limits.max_blocks and cmdbytes<=len(image.data)-32,'raw_command_extent','unresolved')
        cursor=32;table=None;starts_blob=None;base=None
        for _ in range(ncmds):
            command,size=unpack('<II',cursor)
            need(size>=8 and size%8==0 and cursor+size<=32+cmdbytes,'raw_command_extent')
            if command==0x19:
                need(size>=72,'raw_segment_extent')
                name,vm,vmsize,off,filesize,maxprot,prot,count,sgflags=unpack('<16sQQQQiiII',cursor+8)
                need(count<=limits.max_blocks and size==72+80*count,'raw_section_extent')
                need(vm+vmsize<=2**64 and off+filesize<=image.slice_size,'raw_segment_extent')
                if name.rstrip(b'\0')==b'__TEXT':need(base is None,'ambiguous_text_base');base=vm
                for j in range(count):
                    raw=unpack('<16s16sQQIIIIIIII',cursor+72+j*80)
                    sn,seg,va,sz,fo,align,reloff,nrel,fl,_,_,_=raw
                    need(nrel==0,'raw_relocations_unsupported','unresolved')
                    need(vm<=va and va+sz<=vm+vmsize and va+sz<=2**64
                        and (fl&255 in (1,12,18) or off<=fo and fo+sz<=off+filesize), 'raw_section_extent')
                    s=dict(name=sn.rstrip(b'\0').decode('ascii'),segment=seg.rstrip(b'\0').decode('ascii'),
                        address=va,end=va+sz,size=sz,offset=fo,flags=fl)
                    s['executable']=s['name']=='__text' or bool(fl&0x80000400);sections.append(s)
            elif command==2:
                need(table is None and size==24,'raw_symbol_table');table=unpack('<IIII',cursor+8)
            elif command==0x26:
                need(starts_blob is None and size==16,'raw_function_starts');starts_blob=unpack('<II',cursor+8)
            elif command==0xb:
                need(size==80,'raw_dynamic_symbols')
                need(unpack('<I',cursor+68)[0]==unpack('<I',cursor+76)[0]==0,'raw_relocations_unsupported','unresolved')
            cursor+=size
        need(cursor==32+cmdbytes and base==image.preferred_base,'raw_command_geometry')
        need(len(sections)==len(image.sections),'section_metadata')
        ordered=sorted((s for s in sections if s['size']),key=lambda s:s['address'])
        section_addresses=[s['address'] for s in ordered]
        need(all(x['end']<=y['address'] for x,y in zip(ordered,ordered[1:])),'overlapping_raw_sections')
        for raw,s in zip(sections,image.sections):
            need((raw['segment'],raw['name'],raw['address'],raw['size'],raw['offset'],raw['flags'])==
                (s.segment,s.name,s.address,s.size,s.file_offset,s.flags),'section_metadata')
        need(starts_blob is not None,'raw_function_starts_missing','unresolved')
        blob=read(*starts_blob);starts=[];value=0;shift=0;pc=base;terminated=False
        for byte in blob:
            charge();need(not terminated or byte==0,'raw_function_starts_trailing')
            if terminated:continue
            need(shift<64 and (shift!=63 or byte<=1),'raw_function_starts_overflow')
            value|=(byte&127)<<shift
            if byte&128:shift+=7;continue
            if value==0:terminated=True;continue
            pc+=value;need(pc<2**64 and pc%4==0,'raw_function_starts_address');mapped(pc)
            starts.append(pc);need(len(starts)<=limits.max_work,'raw_function_starts_limit','unresolved');value=shift=0
        need(terminated,'raw_function_starts_termination')
        need(table is not None,'raw_symbols_missing')
        off,count,strings,length=table
        need(count<=max_work//17,'raw_symbols_limit','unresolved')
        need(off+16*count<=image.slice_size and strings+length<=image.slice_size,'raw_symbols_extent')
        for i in range(count):
            sx,kind,section,desc,value=unpack('<IBBHQ',off+16*i)
            symbols.setdefault(value,[]).append((sx,kind,section,desc))
        charge(len(image.functions))
        need(len(image.functions)<=max_work,'image_function_limit','unresolved')
        for i,pc in enumerate(starts):
            charge(max(1,len(ordered).bit_length())+1);section=ordered[bisect_right(section_addresses,pc)-1]
            end=starts[i+1] if i+1<len(starts) and starts[i+1]<section['end'] else section['end']
            boundaries[pc]=end
        previous_end=-1
        for f in sorted(image.functions,key=lambda f:f.start):
            charge();need(f.start>=previous_end and f.start<f.end,'overlapping_functions')
            need(f.start in boundaries and boundaries[f.start]==f.end,'raw_function_metadata')
            need(f.start not in function_index,'duplicate_function_metadata')
            function_index[f.start]=f;previous_end=f.end
        need(set(function_index)==set(starts),'raw_function_metadata')
    except _Stop as exc:status,reason=exc.status,exc.reason
    except (ValueError,TypeError,AttributeError,IndexError,UnicodeError,struct.error):status,reason='declined','malformed_image_directory'
    if status!='ready':sections=[];starts=[];boundaries={};symbols={};function_index={};table=None
    ledger=_IndependentImageLedger(_LEDGER_AUTHORITY,image,getattr(image,'data',None),getattr(image,'functions',None),
        getattr(image,'sections',None),getattr(image,'_admission_seal',None),status,reason,work,
        tuple(MappingProxyType(dict(section)) for section in sections),tuple(starts),MappingProxyType(boundaries),
        MappingProxyType(function_index),table,MappingProxyType({pc:tuple(rows) for pc,rows in symbols.items()}))
    object.__setattr__(ledger,'_receipt',(ledger,ledger.sections,ledger.boundaries,ledger.function_index,ledger.symbol_table,
        ledger.symbols,ledger.starts,ledger.status,ledger.reason,ledger.initial_work_steps))
    return ledger

def validate_broad_swift_witness(image, function, candidate: dict, *, limits=BroadWitnessLimits(), _image_ledger=None) -> dict:
    result = dict(model_version='swift-outcome-validation-v2', status='unresolved',
        reason='validation_incomplete', eligible=False, facts={},
        eligibility_scope='checked_structural_facts_only',value_fact_status='unchecked',
        symbolic_return_values_complete=False,
        completeness={'complete':False,'missing':[]},
        accounting={'work':0,'instructions':0,'edges':0,'states':0,'image_initial_work':0,'image_work_charged_here':0,'image_ledger_reused':False},
        runtime_branch_proven=False, call_return_proven=False,error_state_proven=False,
        source_reconstruction_allowed=False, handler_semantics_proven=False,
        exclusive_entry_proven=False, limitations=['structural_only','no_runtime_execution_proof',
        'no_source_or_handler_semantics','calls_have_candidate_continuations'])
    a=result['accounting']; facts=result['facts']
    def need(ok, reason, status='declined'):
        if not ok: raise _Stop(reason,status)
    def charge(n=1):
        need(n>=0 and n<=limits.max_work-a['work'],'validator_work_limit','unresolved');a['work']+=n
    def address(v):
        need(type(v) is str and re.fullmatch('0x[0-9a-f]{1,16}',v) is not None,'invalid_address')
        n=int(v,16);need(v==hex(n) and n%4==0,'invalid_address');return n
    def read(off,n):
        charge(n+1);need(type(off) is int and 0<=off<=len(image.data) and 0<=n<=len(image.data)-off
            and off+n<=image.slice_size,'raw_extent');return image.data[off:off+n]
    def unpack(fmt,off):return struct.unpack(fmt,read(off,struct.calcsize(fmt)))
    sections=[]
    def mapped(pc,n=4):
        need(type(pc) is int and 0<=pc<=2**64-n,'vm_extent')
        hits=[s for s in sections if s['address']<=pc and pc+n<=s['end']]
        charge(len(sections));need(len(hits)==1,'raw_mapping_ambiguous')
        s=hits[0];need(s['executable'] and s['flags']&255 not in (1,8,12,18)
            and 'stub' not in s['name'].lower(),'raw_mapping_not_executable')
        return s['offset']+pc-s['address']
    decoded={}
    def ins(pc):
        from .swift_broad_instructions import decode_instruction
        from .arm64 import ModelError
        charge()
        if pc not in decoded:
            need(len(decoded)<limits.max_instructions,'validator_instruction_limit','unresolved')
            word,=unpack('<I',mapped(pc))
            try:decoded[pc]=decode_instruction(word,pc)
            except ModelError:raise _Stop('unsupported_instruction','unresolved')
            a['instructions']=len(decoded)
        return decoded[pc]
    def row(pc):
        d=ins(pc);off=mapped(pc)
        return dict(pc=hex(pc),word=f'0x{d.word:08x}',slice_offset=hex(off),
            container_offset=hex(image.slice_offset+off),kind=d.kind)
    try:
        need(type(limits) is BroadWitnessLimits,'invalid_validator_limits')
        need(image.has_valid_admission(),'image_admission_custody','unresolved')
        preflight_broad_json(candidate,limits=limits)
        need(type(candidate) is dict,'candidate_object')
        need(candidate.get('model_version')=='swift-outcome-witness-v2'
            and candidate.get('validation_model')=='swift-outcome-validation-v2'
            and candidate.get('profile')=='broad-v1','candidate_model')
        need(candidate.get('status')=='unresolved' and candidate.get('eligible') is False,'candidate_scope')
        pending=[candidate]
        while pending:
            obj=pending.pop();charge()
            if type(obj) is dict:
                for k,v in obj.items():
                    if k.endswith('_proven') or k=='source_reconstruction_allowed':need(v is False,'proof_scope')
                    if type(v) in (dict,list,tuple):pending.append(v)
            elif type(obj) in (list,tuple):pending.extend(obj)
        need(candidate.get('source_models')=={'edge':'swift-broad-error-flow-v1',
            'witness':'swift-outcome-witness-v2','validation':'swift-outcome-validation-v2',
            'cfg':'swift-bounded-structural-cfg-v1','value':'swift-outcome-values-v1'},'source_models')
        identity=candidate['identity']
        expected=dict(slice_sha256=image.slice_sha256,container_sha256=image.container_sha256,
            slice_offset=hex(image.slice_offset),slice_size=hex(image.slice_size),
            architecture=image.architecture,cpu_subtype=image.cpu_subtype,uuid=image.uuid,
            preferred_base=hex(image.preferred_base),slice_index=image.slice_index,container_slice_count=image.container_slice_count)
        need(all(k in identity and type(identity.get(k)) is type(v) and identity.get(k)==v for k,v in expected.items()),'image_identity')
        need(image.architecture=='arm64' and image.cpu_subtype in (0,1),'ordinary_arm64_required')
        need(image.slice_size==len(image.data) and image.slice_offset>=0,'slice_extent')
        need(function in image.functions and function.boundary_source=='lc_function_starts','caller_membership')
        need(0<=function.start<function.end<=2**64 and function.start%4==function.end%4==0,'caller_extent')
        need(function.size//4<=limits.max_instructions,'validator_instruction_limit','unresolved')
        ledger=create_independent_swift_image_ledger(image) if _image_ledger is None else _image_ledger
        need(type(ledger) is _IndependentImageLedger and ledger.matches(image),'independent_image_ledger_custody','unresolved')
        a['image_initial_work']=ledger.initial_work_steps
        a['image_work_charged_here']=ledger.initial_work_steps if _image_ledger is None else 0
        a['image_ledger_reused']=_image_ledger is not None
        need(ledger.status=='ready',ledger.reason or 'independent_image_ledger_not_ready',ledger.status)
        sections=ledger.sections;starts=ledger.starts;table=ledger.symbol_table
        def raw_boundary(f):
            charge();need(ledger.function_index.get(f.start) is f,'raw_function_membership')
            need(ledger.boundaries.get(f.start)==f.end,'raw_boundary_end')
            return dict(start_pc=hex(f.start),end_pc_exclusive=hex(f.end),boundary_source='lc_function_starts')
        need(identity['caller']==raw_boundary(function),'caller_identity')
        cp=address(identity['call_pc']);need(function.start<=cp<function.end,'call_outside_caller')
        call=candidate['call'];d=ins(cp)
        need(d.kind=='bl' and call['pc']==hex(cp) and call['word']==f'0x{d.word:08x}','direct_call_word')
        target=cp+d.immediate;need(0<=target<2**64,'direct_target_overflow')
        need(call['callee_pc']==hex(target),'direct_target')
        callee=ledger.function_index.get(target)
        need(callee is not None and callee.boundary_source=='lc_function_starts','callee_exact_entry')
        need(identity['callee']==raw_boundary(callee),'callee_identity');mapped(target)
        for name,pc in (('call',cp),('callee_entry',target)):
            rawword,=unpack('<I',mapped(pc));off=mapped(pc)
            need(call.get('provenance',{}).get(name)==dict(pc=hex(pc),word=f'0x{rawword:08x}',
                slice_file_offset=hex(off),container_file_offset=hex(image.slice_offset+off)), 'call_provenance')
        facts['identity']='checked_against_raw_header_sections_and_function_starts'
        need(table is not None,'raw_symbols_missing')
        off,count,strings,length=table;names=[];visibility_records=[]
        for sx,kind,section,desc in ledger.symbols.get(target,()):
            charge();visibility_records.append((kind,desc))
            need(1<=section<=len(sections) and sections[section-1]['address']<=target<sections[section-1]['end'],'symbol_section')
            need(0<sx<length,'symbol_string_extent');raw=read(strings+sx,min(length-sx,limits.max_string+1));end=raw.find(b'\0')
            need(0<end<=limits.max_string,'symbol_string_extent');names.append(raw[:end].decode('ascii'))
        need(len(names)==1,'symbol_aliases')
        from .swift_declaration_profiles import parse_broad_declaration, CallableKind
        declaration=parse_broad_declaration(names[0]);need(declaration.supported,'declaration_unqualified','unresolved')
        decl=declaration.identity
        need(_symbol_visibility_allowed(*visibility_records[0],decl,d.kind),'symbol_visibility')
        retained=call['declaration'];expected_decl=dict(status='syntax_admitted',identity=asdict(decl),reason=None)
        # JSON tuples/enums are normalized through the standard representation.
        import json
        need(json.dumps(retained,sort_keys=True)==json.dumps(expected_decl,sort_keys=True),'declaration_identity')
        facts['call']='checked_direct_target_and_exact_symbol_syntax'
        # Registry is private input, never a qualification supplied by a caller.
        from .swift_abi_profiles import LOWERING_QUALIFICATIONS, SYNC_ARM64_SWIFT6
        abi=call['abi'];qid=abi.get('evidence',{}).get('lowering',{}).get('qualification_id')
        stable_profile=abi.get('profile')=='swift6-arm64-sync-untyped-stable-research-v2'
        if stable_profile:
            storage,caller_error_state=_validate_stable_abi(image,function,callee,cp,decl,abi,read,mapped,ins,charge,need,limits)
            result['caller_error_state']=caller_error_state
            result['outcome_scope']='byte_zero_nonzero_geometry_with_conditional_abi_roles'
            result['outcome_preconditions']=['well_formed_swift_stable_arm64_calling_convention',
                'synchronous_untyped_throws','incoming_x21_zero_required_by_selected_convention']
            result['abi_assumption']='explicit_selected_swift6_stable_arm64_sync_untyped'
            result['compiler_verified']=False
        else:
            need(type(qid) is str and qid in LOWERING_QUALIFICATIONS,'abi_qualification_unknown','unresolved')
            q=LOWERING_QUALIFICATIONS[qid]
            need(q.slice_sha256==image.slice_sha256 and q.source_sha256 and q.source_capture and q.disassembly_capture,
                'abi_source_identity','unresolved')
            need(replace(decl,symbol=q.symbol)==parse_broad_declaration(q.symbol).identity
                and decl.symbol.lstrip('_')==q.symbol.lstrip('_') and decl.callable_kind==q.callable_kind
                and tuple((c.name,c.kind) for c in decl.context)==q.context
                and tuple(t.name for t in decl.parameter_types)==q.parameter_types and decl.result_type.name==q.result_type
                and decl.throws and not decl.generic_parameter_counts and not decl.generic_requirements
                and all(not t.inout and not t.arguments and t.generic_depth is None for t in (*decl.parameter_types,decl.result_type)),
                'abi_tuple_identity','unresolved')
            need(q.result_location=='x0' and q.result_type in ('Swift.Int','Swift.UInt','Swift.Bool','Swift.Int32','Swift.UInt32'),
                'abi_result_subset','unresolved')
            if 'argument_locations' in abi:need(abi['argument_locations']==list(q.parameter_locations),'abi_argument_locations')
            if 'receiver_location' in abi:need(abi['receiver_location']==q.receiver_location,'abi_receiver_location')
            if 'result_location' in abi:need(abi['result_location']==q.result_location,'abi_result_location')
            need(abi.get('status')=='admitted' and abi.get('profile')==SYNC_ARM64_SWIFT6.identifier
                and abi.get('error_register')=='x21' and abi.get('research_only') is True,'abi_claim')
            lowering=abi['evidence']['lowering']
            for key,expected in dict(source_sha256=q.source_sha256,slice_sha256=q.slice_sha256,
                    compiler=q.compiler,target=q.target,optimization=q.optimization,
                    source_capture=q.source_capture,disassembly_capture=q.disassembly_capture).items():
                if key in lowering:need(lowering[key]==expected,'qualification_retained_identity')
            if 'observations' in lowering:
                need(lowering['observations']==[dict(pc=hex(pc),raw_bytes=raw,meaning=meaning)
                    for pc,raw,meaning in q.observations],'qualification_retained_observations')
            for pc,raw,_ in q.observations:
                expected=bytes.fromhex(raw);need(bool(expected),'empty_qualification')
                need(read(mapped(pc,len(expected)),len(expected))==expected,'qualification_bytes_changed','unresolved')
            storage=dict(locations=['x0'],category='integer',bit_width=64,indirect=False)
        if decl.context:
            context=_validate_nominal_context(image,decl,sections,read,charge,need,limits)
            retained_context=abi.get('evidence',{}).get('nominal_context')
            if retained_context is not None:
                need(all(retained_context.get(k)==v for k,v in context.items()),'nominal_retained_records')
                if 'slice' in retained_context:
                    need(retained_context['slice']==dict(sha256=image.slice_sha256,offset=image.slice_offset,
                        size=image.slice_size,architecture=image.architecture),'nominal_retained_slice')
        if 'binding' in abi:
            binding=abi['binding']
            need(binding.get('schema')=='airs.swift-abi-binding.v1'
                and binding.get('slice')==dict(sha256=image.slice_sha256,offset=image.slice_offset,size=image.slice_size,architecture=image.architecture)
                and binding.get('sections')==[dict(segment=s.segment,name=s.name,address=s.address,size=s.size,
                    file_offset=s.file_offset,flags=s.flags) for s in image.sections], 'abi_binding_identity')
            for span in binding['ranges']:
                pc=span['pc'];raw=bytes.fromhex(span['raw']);need(type(pc) is int and bool(raw),'abi_binding_range')
                hits=[s for s in sections if s['address']<=pc and pc+len(raw)<=s['end']]
                charge(len(sections));need(len(hits)==1,'abi_binding_mapping');s=hits[0]
                need(s['flags']&255 not in (1,12,18) and read(s['offset']+pc-s['address'],len(raw))==raw,'abi_binding_bytes')
        facts['abi']='checked_selected_abi_assumption_and_raw_patterns' if stable_profile else 'checked_registry_identity_and_observation_bytes'
        # Rebuild every lexical instruction, direct edge and leader independently.
        ds={pc:ins(pc) for pc in range(function.start,function.end,4)}
        branches={'b','bcond','xcbz','xcbnz','wcbz','wcbnz','xtbz','xtbnz','wtbz','wtbnz'}
        edges=[];leaders={function.start};terminals=set()
        def edge(pc,kind,dest=None):
            charge();need(len(edges)<limits.max_edges,'validator_edge_limit','unresolved')
            if dest is not None:need(function.start<=dest<function.end and dest%4==0,'cfg_target_outside_caller');leaders.add(dest)
            e=row(pc);e.update(source_pc=hex(pc),target_pc=hex(dest) if dest is not None else None,kind=kind);edges.append(e);terminals.add(pc)
        for pc,d in ds.items():
            if d.kind in branches:
                edge(pc,'branch' if d.kind=='b' else 'conditional_taken',pc+d.immediate)
                if d.kind!='b':edge(pc,'conditional_fallthrough',pc+4)
            elif d.kind=='bl':edge(pc,'call_return_candidate',pc+4)
            elif d.kind=='ret':edge(pc,'return')
            elif d.kind=='brk':edge(pc,'exception_transfer')
            else:need(pc+4<function.end,'cfg_fallthrough_outside_caller')
            if pc in terminals and pc+4<function.end:leaders.add(pc+4)
        need(len(leaders)<=limits.max_blocks,'validator_block_limit','unresolved')
        blocks=[]
        for pc in ds:
            if pc in leaders:blocks.append(dict(start_pc=hex(pc),end_pc_exclusive=None,instructions=[],successors=[],predecessors=[]))
            blocks[-1]['instructions'].append(row(pc));blocks[-1]['end_pc_exclusive']=hex(pc+4)
        for b in blocks:
            pc=int(b['instructions'][-1]['pc'],16)
            if pc not in terminals:edge(pc,'fallthrough',pc+4)
        owner={int(r['pc'],16):b for b in blocks for r in b['instructions']}
        for e in edges:
            owner[int(e['source_pc'],16)]['successors'].append(e)
            if e['target_pc'] is not None:owner[int(e['target_pc'],16)]['predecessors'].append(e)
        cfg=candidate['cfg'];need(cfg.get('blocks')==blocks and cfg.get('edges')==edges,'cfg_replay_mismatch')
        need(cfg.get('completeness',{}).get('complete') is True
            and cfg.get('completeness',{}).get('all_words_classified') is True,'cfg_partial','unresolved')
        returns=[row(pc) for pc,d in ds.items() if d.kind=='ret']
        calls=[dict(**row(pc),callee_pc=hex(pc+d.immediate),continuation_pc=hex(pc+4),runtime_return_proven=False)
               for pc,d in ds.items() if d.kind=='bl']
        need(cfg.get('returns')==returns and cfg.get('call_return_candidates')==calls,'cfg_auxiliary_facts')
        exceptions=[dict(**row(pc),exception='breakpoint',resume_proven=False) for pc,d in ds.items() if d.kind=='brk']
        if exceptions or any(key in cfg for key in ('exception_transfers','external_exception_handling_unmodeled','exception_resume_proven')):
            need(cfg.get('exception_transfers')==exceptions and cfg.get('external_exception_handling_unmodeled') is True
                and cfg.get('exception_resume_proven') is False,'cfg_exception_facts')
        need(cfg.get('function_pc')==hex(function.start) and cfg.get('model')=='swift-bounded-structural-cfg-v1'
            and cfg.get('status')=='eligible_structural_only','cfg_model')
        seen=set();depth_max=0
        for root in blocks:
            if root['start_pc'] in seen:continue
            seen.add(root['start_pc']);stack=[(root,1)]
            while stack:
                b,depth=stack.pop();charge();need(depth<=limits.max_depth,'cfg_depth_limit','unresolved');depth_max=max(depth_max,depth)
                for e in reversed(b['successors']):
                    dst=e['target_pc']
                    if dst is not None and dst not in seen:
                        need(depth<limits.max_depth,'cfg_depth_limit','unresolved');seen.add(dst);stack.append((owner[int(dst,16)],depth+1))
        ledger=cfg.get('accounting',{})
        need(all(type(ledger.get(k)) is int and ledger[k]==v for k,v in
            dict(retained_words=len(ds),blocks=len(blocks),edges=len(edges),max_discovery_depth=depth_max).items()),'cfg_accounting')
        a['edges']=len(edges);facts['cfg']='independently_rebuilt_all_caller_words_and_edges'
        post=candidate['post_call'];tp=address(post['test_pc']);need(tp in ds,'postcall_test_outside_caller')
        need(limits.max_state_entries>=2 and limits.max_provenance_nodes>=2,'value_seed_limit','unresolved')
        scalar=_ScalarReplay(cp,limits,charge)
        if stable_profile:scalar.registers[21]=('raw_postcall_x21',hex(cp),64)
        error_origin=scalar.registers[21]
        wire_origin='raw_post_call_register:x21' if stable_profile else 'abi_post_call_error:x21'
        scalar.registers.pop(0,None)
        for location in storage['locations']:
            if re.fullmatch('[xw][0-9]+',location):
                register=int(location[1:]);bits=32 if location.startswith('w') else 64
                scalar.write(register,('call_result',hex(cp),bits) if register==0 else
                    ('call_result_component',hex(cp),location,bits),bits)
        # Recover only a straight-line frame prefix. Argument values are not
        # post-call results and never seed return dependencies.
        frame=_ScalarReplay(cp,limits,charge);frame.registers={}
        for pc,d in ds.items():
            if pc>=cp:break
            if d.kind in branches or d.kind in ('bl','ret','brk'):
                frame.sp=None;frame.registers={};frame.cells={};break
            try:frame.step(d)
            except _Stop as exc:
                if exc.reason!='value_transfer_unqualified':raise
                if d.changes_sp:frame.sp=None
                frame.registers.pop(d.rd,None);frame.cells={}
        scalar.sp=frame.sp
        scalar.cells={}  # The call is a clobber boundary for prior local cells.
        trace=[];alias_observations=[];cursor=cp+4;visited={cp};comparison=None
        while cursor!=tp:
            charge();need(len(trace)<limits.post_call_window,'postcall_window','unresolved')
            need(cursor in ds and cursor not in visited,'postcall_cycle_or_target','unresolved');visited.add(cursor)
            d=ds[cursor];trace.append(hex(cursor))
            if d.word&0xfffffc1f==0xf100001f:
                need(comparison is None,'multiple_error_comparisons','unresolved');comparison=d
                cursor+=4;continue
            need(comparison is None,'comparison_not_adjacent','unresolved')
            if d.kind=='b':cursor+=d.immediate;continue
            need(d.kind not in branches and d.kind not in ('ret','bl','brk'),'postcall_control_unqualified','unresolved')
            scalar.step(d)
            aliases=sorted(r for r,v in scalar.registers.items() if v==error_origin)
            origins=[dict(register=f'x{r}',kind='register_copy',origin=wire_origin) for r in aliases]
            for slot,(size,epoch,value) in sorted(scalar.cells.items()):
                if value==error_origin:origins.append(dict(stack_slot=slot,epoch=epoch,kind='stack_slot',origin=wire_origin))
            alias_observations.append(dict(pc=hex(cursor),origins=origins));cursor+=4
        need(len(trace)<limits.post_call_window,'postcall_window','unresolved')
        test=ds[tp];trace.append(hex(tp))
        if comparison is None:
            need(test.kind in ('xcbz','xcbnz'),'error_test_unqualified','unresolved');reg=test.rn;zero=test.kind=='xcbz'
            need('test_kind' not in post,'test_encoding')
        else:
            need(test.kind=='bcond' and test.addressing in ('0','1') and comparison.address+4==tp,'error_comparison_condition','unresolved')
            need(post.get('test_kind')=='cmp_zero_bcond' and post.get('comparison_pc')==hex(comparison.address)
                and post.get('comparison_word')==f'0x{comparison.word:08x}'
                and post.get('test_condition')==('eq' if test.addressing=='0' else 'ne'),'comparison_facts')
            reg=comparison.rn;zero=test.addressing=='0'
        need(scalar.read(reg)==error_origin,'error_register_alias','unresolved')
        success,error=(tp+test.immediate,tp+4) if zero else (tp+4,tp+test.immediate)
        need(post.get('test_word')==f'0x{test.word:08x}' and post.get('test_register')==f'x{reg}'
            and post.get('success_successor_pc')==hex(success) and post.get('error_successor_pc')==hex(error),'test_polarity')
        need(post.get('trace')==trace and post.get('status')=='candidate'
            and post.get('reason') in ('qualified_error_alias_zero_test','qualified_error_alias_compare_zero'),'postcall_trace')
        facts['post_call']='checked_error_alias_epoch_flags_and_branch_polarity'
        # Explore both successors of every direct condition. A retained path is
        # structural possibility, never an assertion that its condition occurs.
        def paths(start):
            pending=[(start,[],set())];complete=[];walked=0
            while pending:
                pc,out,seen=pending.pop();charge();walked+=1
                need(walked<=limits.max_provenance_nodes,'arm_path_limit','unresolved')
                need(pc in ds and pc not in seen,'cyclic_or_external_arm','unresolved')
                need(len(out)<limits.max_depth,'path_depth_limit','unresolved')
                d=ds[pc];out=out+[row(pc)];seen=seen|{pc}
                if d.kind in ('ret','brk'):complete.append(out);continue
                destinations=[pc+d.immediate] if d.kind=='b' else ([pc+d.immediate,pc+4] if d.kind in branches else [pc+4])
                for dst in reversed(destinations):pending.append((dst,out,seen))
            return complete
        success_paths,error_paths=paths(success),paths(error)
        success_set={int(r['pc'],16) for p in success_paths for r in p};error_set={int(r['pc'],16) for p in error_paths for r in p}
        partition=dict(success_only_pcs=[hex(x) for x in sorted(success_set-error_set)],
            error_only_pcs=[hex(x) for x in sorted(error_set-success_set)],shared_pcs=[hex(x) for x in sorted(success_set&error_set)],
            unreachable_pcs=[hex(x) for x in sorted(set(ds)-success_set-error_set)])
        regions=candidate['regions']
        need(regions.get('status')=='structural_candidates' and regions.get('success_entry_pc')==hex(success)
            and regions.get('error_entry_pc')==hex(error),'region_entries')
        need(regions.get('paths')==[dict(outcome=name,entry_pc=hex(pc),reachability='unproven')
            for name,pc in (('success',success),('error',error))],'region_paths')
        if 'partition' in regions:
            need(regions['partition']==partition,'region_partition')
            def outcome(pc):
                return 'shared' if pc in success_set&error_set else ('success' if pc in success_set else ('error' if pc in error_set else 'unreachable'))
            need(regions.get('tails')==[dict(pc=r['pc'],kind='return',outcome=outcome(int(r['pc'],16))) for r in returns],'region_return_tails')
        else:
            need(regions.get('tails')==[dict(pc=r['pc'],kind='return',outcome='unknown') for r in returns],'region_return_tails')
        protected={int(pc,16) for pc in trace}|success_set|error_set
        for e in edges:
            if e['target_pc'] is None:continue
            src,dst=int(e['source_pc'],16),int(e['target_pc'],16)
            need(dst not in protected or src in protected or (src==cp and dst==cp+4),'unexpected_incoming_edge','blocked')
        facts['regions']='checked_all_arm_paths_returns_partitions_and_direct_incoming_edges'
        values=candidate['value_facts'];observations=[];exception_observations=[]
        retained_items,retained_bytes=_retention_cost(partition,limits,charge)
        retained_bytes+=4096  # bounded result metadata, accounting and statuses
        retained_items+=256
        for arm,arm_paths in (('success',success_paths),('error',error_paths)):
            for rows in arm_paths:
                state=scalar.clone()
                for r in rows:
                    if ds[int(r['pc'],16)].kind=='brk':break
                    state.step(ds[int(r['pc'],16)]);a['states']+=1
                if ds[int(rows[-1]['pc'],16)].kind=='brk':
                    record=dict(arm=arm,pc=rows[-1]['pc'],exception='breakpoint',resume_proven=False)
                    if record not in exception_observations:
                        items,size=_retention_cost(record,limits,charge)
                        need(items<=limits.max_container_items-retained_items and size<=limits.max_bytes-retained_bytes,
                            'validator_output_limit','unresolved')
                        retained_items+=items;retained_bytes+=size;exception_observations.append(record)
                    continue
                v=state.read(0)
                record=dict(arm=arm,return_pc=rows[-1]['pc'],register='x0',
                    value=list(v) if v is not None else ['unknown',64],
                    status='modeled_symbolic_value' if v is not None else 'unknown',
                    reason='independent_instruction_replay' if v is not None else 'no_supported_scalar_origin',
                    raw_error_register_value=list(state.read(21)) if state.read(21) is not None else ['unknown',64],
                    error_role='conditional_on_selected_abi_preconditions',
                    runtime_propagation_proven=False,source_handler_proven=False)
                if record not in observations:
                    items,size=_retention_cost(record,limits,charge)
                    need(items<=limits.max_container_items-retained_items and size<=limits.max_bytes-retained_bytes,
                        'validator_output_limit','unresolved')
                    retained_items+=items;retained_bytes+=size;observations.append(record)
        need(values.get('seed')==dict(register='x21',kind='register_copy',origin=wire_origin,width=64),'value_seed')
        need(values.get('observations')==alias_observations,'value_observations')
        result['return_observations']=observations
        result['exception_observations']=exception_observations
        result['exception_resume_proven']=False
        result['external_exception_handling_unmodeled']=True
        result['region_partition']=partition
        result['symbolic_return_values_complete']=bool(observations) and all(o['status']!='unknown' for o in observations)
        result['value_fact_status']=('checked_symbolic_values' if result['symbolic_return_values_complete'] else (
            'not_applicable_no_return_paths' if not observations else 'checked_with_explicit_unknowns'))
        facts['values']='independently_replayed_scalar_call_result_epoch'
        need(candidate.get('completeness')==dict(complete=True,missing=[]),'candidate_partial','unresolved')
        ledger=candidate.get('accounting',{})
        need(all(type(ledger.get(k)) is int and ledger[k]==v for k,v in
            dict(instructions=len(ds),blocks=len(blocks),edges=len(edges),value_steps=len(alias_observations)).items()),'candidate_accounting')
        need(type(ledger.get('work')) is int and 0<=ledger['work']<=limits.max_work,'candidate_work_accounting')
        encoded=len(json.dumps(candidate,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii'))
        need(type(ledger.get('encoded_bytes')) is int and ledger['encoded_bytes']==encoded,'candidate_size_accounting')
        try:preflight_broad_json(result,limits=limits)
        except ValueError:raise _Stop('validator_output_limit','unresolved')
        result.update(status='eligible_structural_only',eligible=True,reason='independent_bounded_byte_replay')
        result['completeness']={'complete':True,'missing':[]}
    except _Stop as exc:
        result.update(status=exc.status,reason=exc.reason);result['completeness']['missing']=[exc.reason]
        if hasattr(exc,'instruction'):
            future_statuses={key:('checked' if key in facts else 'unchecked')
                for key in ('identity','call','abi','cfg','post_call','regions','values')}
            if 'values' in facts:future_statuses['values']=result['value_fact_status']
            diagnostic={**result,'unresolved_instruction':exc.instruction,'fact_statuses':future_statuses}
            try:preflight_broad_json(diagnostic,limits=limits)
            except ValueError:pass
            else:result['unresolved_instruction']=exc.instruction
    except (KeyError,TypeError,ValueError,AttributeError,IndexError,UnicodeError,struct.error) as exc:
        result.update(status='declined',reason='malformed_candidate_or_image');result['completeness']['missing']=['malformed_candidate_or_image']
    result['fact_statuses']={key:('checked' if key in facts else 'unchecked')
        for key in ('identity','call','abi','cfg','post_call','regions','values')}
    if 'values' in facts:result['fact_statuses']['values']=result['value_fact_status']
    return result


def _validate_nominal_context(image,decl,sections,read,charge,need,limits):
    """Independent direct nominal descriptor traversal; no admission helper."""
    from bisect import bisect_right
    need(len(sections)<=4096,'nominal_section_limit','unresolved')
    charge(len(sections)*max(1,len(sections).bit_length()))
    ordered=sorted((section for section in sections if section['size']),key=lambda section:section['address'])
    addresses=[section['address'] for section in ordered]
    need(all(left['end']<=right['address'] for left,right in zip(ordered,ordered[1:])),
        'nominal_mapping_ambiguous','unresolved')
    typed=[section for section in sections if section['segment']=='__TEXT' and section['name']=='__swift5_types']
    need(len(typed)==1,'nominal_context_missing','unresolved');s=typed[0]
    need(s['size']%4==0 and s['size']//4<=limits.max_blocks,'nominal_context_limit','unresolved')
    def locate(pc,n):
        charge(max(1,len(ordered).bit_length()))
        need(type(pc) is int and 0<=pc and 0<=n and pc+n<=1<<64,'nominal_mapping','unresolved')
        index=bisect_right(addresses,pc)-1
        need(index>=0 and pc+n<=ordered[index]['end'],'nominal_mapping','unresolved')
        section=ordered[index]
        need(section['flags']&255 not in (1,12,18),'nominal_zero_fill','unresolved')
        return section
    def raw(pc,n):
        section=locate(pc,n)
        return read(section['offset']+pc-section['address'],n)
    def word(pc):return struct.unpack('<I',raw(pc,4))[0]
    def relative(pc,*,context=False):
        off=struct.unpack('<i',raw(pc,4))[0]
        need(off!=0 and not (context and off&1),'nominal_indirect_parent','unresolved');return pc+off
    def name(pc):
        # A direct CString is byte aligned. Locate its unique mapping once,
        # read bounded chunks, and never join a string across section borders.
        capacity=min(limits.max_string,256)
        need(capacity>0,'nominal_name_limit','unresolved')
        section=locate(pc,1);output=bytearray();cursor=pc
        while len(output)<capacity:
            need(cursor<section['end'],'nominal_name_extent','unresolved')
            size=min(32,capacity-len(output),section['end']-cursor)
            chunk=read(section['offset']+cursor-section['address'],size);charge()
            need(len(chunk)==size,'nominal_name_extent','unresolved')
            zero=chunk.find(b'\0')
            if zero>=0:
                output.extend(chunk[:zero]);need(bool(output),'nominal_empty_name','unresolved')
                try:return output.decode('ascii')
                except UnicodeDecodeError:raise _Stop('nominal_name_encoding','unresolved')
            output.extend(chunk);cursor+=size
        raise _Stop('nominal_name_limit','unresolved')
    matches={};visited=set()
    for off in range(0,s['size'],4):
        pc=relative(s['address']+off,context=True)
        if pc in visited:continue
        visited.add(pc);leaf=pc;chain=[];seen=set();records=[]
        leaf_flags=word(pc)
        if leaf_flags&31 in (16,17,18) and not leaf_flags&0xff00:
            if name(relative(pc+8))!=decl.context[-1].name:continue
        for _ in range(limits.max_depth):
            charge();need(pc not in seen,'nominal_cycle','unresolved');seen.add(pc)
            need(pc%4==0,'nominal_descriptor_alignment','unresolved')
            flags=word(pc);kind=flags&31
            need(kind in (0,16,17,18),'nominal_kind','unresolved')
            need(not flags&~(0x5f|(0x80000000 if kind==16 else 0)),'nominal_flags','unresolved')
            descriptor=raw(pc,{0:12,16:44,17:28,18:28}[kind]);namepc=relative(pc+8);n=name(namepc)
            record=dict(descriptor_pc=hex(pc),descriptor_flags=hex(flags),
                kind={0:'module',16:'class',17:'struct',18:'enum'}[kind],name=n,name_pc=hex(namepc),
                raw_name=(n.encode('ascii')+b'\0').hex(),raw_descriptor=descriptor.hex())
            if kind==0:
                need(word(pc+4)==0,'nominal_module_parent','unresolved')
                if n==decl.module and tuple(reversed(chain))==tuple((c.name,c.kind) for c in decl.context):
                    matches[leaf]=dict(status='admitted_nominal_context',entry_pc=hex(s['address']+off),
                        raw_entry=raw(s['address']+off,4).hex(),records=list(reversed(records)),module=record)
                break
            records.append(record);chain.append((n,{16:'class',17:'struct',18:'enum'}[kind]));pc=relative(pc+4,context=True)
        else:raise _Stop('nominal_depth_limit','unresolved')
    need(len(matches)==1,'nominal_context_ambiguous_or_missing','unresolved')
    return next(iter(matches.values()))


class _ScalarReplay:
    """Independent scalar/stack equations; expressions keep width transformations.

    Cells use entry-SP-relative addresses. Unknown loads kill their destination;
    overlapping stores and frame retirement invalidate cells before reuse.
    No transfer establishes execution or reconstructs a Swift source value.
    """
    def __init__(self,call_pc,limits,charge=lambda n=1:None):
        self.registers={0:('call_result',hex(call_pc),64),21:('error_result',hex(call_pc),64)}
        self.cells={};self.sp=0;self.epoch=0;self.limits=limits;self.charge=charge
    def clone(self):
        other=object.__new__(type(self));other.__dict__=self.__dict__.copy()
        other.registers=dict(self.registers);other.cells=dict(self.cells);return other
    def fail(self,reason):
        refusal=_Stop(reason,'unresolved')
        if reason=='value_transfer_unqualified' and hasattr(self,'current_instruction'):
            refusal.instruction=self.current_instruction
        raise refusal
    @staticmethod
    def width(value):return value[-1]
    @classmethod
    def resized(cls,value,bits):
        if value is None:return None
        if value[0]=='constant':return ('constant',value[1]&((1<<bits)-1),bits)
        if cls.width(value)==bits:return value
        return ('truncate' if bits<cls.width(value) else 'zero_extend',value,bits)
    def read(self,reg,bits=64):
        return ('constant',0,bits) if reg==31 else self.resized(self.registers.get(reg),bits)
    def write(self,reg,value,bits=64):
        if value is not None and value[0]=='stack_address':self.checked_stack_offset(value[1])
        if reg==31:return
        if value is None:self.registers.pop(reg,None)
        else:self.registers[reg]=self.resized(self.resized(value,bits),64)
        self.bound()
    def bound(self):
        if len(self.registers)+len(self.cells)>self.limits.max_state_entries:self.fail('value_state_limit')
        work=[(v,1) for v in self.registers.values()]+[(c[2],1) for c in self.cells.values() if c[2] is not None]
        count=0
        while work:
            v,depth=work.pop();count+=1
            if count>self.limits.max_provenance_nodes or depth>self.limits.max_depth:self.fail('value_provenance_limit')
            work.extend((x,depth+1) for x in v if isinstance(x,tuple))
    def checked_stack_offset(self,value):
        if type(value) is not int or not -(1<<63)<=value<(1<<63):self.fail('stack_offset_unqualified')
        return value
    def adjust(self,new):
        self.checked_stack_offset(new)
        if self.sp is None:self.fail('unknown_stack_frame')
        if new>self.sp:
            self.cells={k:v for k,v in self.cells.items() if k>=new};self.epoch+=1
        self.sp=new
    def shifted(self,value,bits,mode,amount):
        if mode not in ('lsl','lsr','asr','ror') or type(amount) is not int or not 0<=amount<bits:
            self.fail('register_shift_unqualified')
        if value is None:return None
        if amount==0:return value
        if value[0]=='constant':
            number=value[1]&((1<<bits)-1)
            if mode=='lsl':number<<=amount
            elif mode=='lsr':number>>=amount
            elif mode=='asr':number=(number-(1<<bits) if number&(1<<(bits-1)) else number)>>amount
            else:number=(number>>amount)|(number<<(bits-amount))
            return ('constant',number&((1<<bits)-1),bits)
        return (mode,value,('constant',amount,bits),bits)
    def step(self,d):
        self.charge();k=d.kind;bits=32 if k.startswith('w') else 64;mask=(1<<bits)-1
        self.current_instruction=dict(pc=hex(d.address),word=f'0x{d.word:08x}',kind=k)
        rd,rn=d.rd,d.rn
        from .swift_broad_instructions import FP_DESTINATION_KINDS,GPR_DESTINATION_KINDS,FP_FLAG_KINDS,MEMORY_WIDTHS,FP_MEMORY_STORES
        # FP values are explicitly outside this integer domain. Bank-aware
        # descriptors prevent v0 writes from changing x0 and FP→GPR transfers
        # from retaining stale integer origins. No floating value is fabricated.
        if k in FP_DESTINATION_KINDS or k in FP_FLAG_KINDS:return
        if k in GPR_DESTINATION_KINDS and k not in ('adr','adrp','wldrb','wldrh','xadd_reg','xsub_reg','wadd_reg','wsub_reg','xadd_ext','xsub_ext','xldr_raw','xldur','wldr_raw','wldur'):
            self.write(rd,None);return
        if k in ('xadd_ext','xsub_ext'):
            extensions={'uxtb':(8,False),'uxth':(16,False),'uxtw':(32,False),'uxtx':(64,False),
                'sxtb':(8,True),'sxth':(16,True),'sxtw':(32,True),'sxtx':(64,True)}
            if d.addressing not in extensions or type(d.immediate) is not int or not 0<=d.immediate<=4:
                self.fail('extended_register_unqualified')
            width,signed=extensions[d.addressing];right=self.read(d.rt2)
            if right is not None and width<64:
                if right[0]=='constant':
                    number=right[1]&((1<<width)-1)
                    if signed and number&(1<<(width-1)):number-=1<<width
                    right=('constant',number&((1<<64)-1),64)
                else:right=('sign_extend_low_bits' if signed else 'zero_extend_low_bits',right,('constant',width,64),64)
            right=self.shifted(right,64,'lsl',d.immediate)
            left=(('stack_address',self.sp,64) if self.sp is not None else None) if rn==31 else self.read(rn)
            operation='add' if k=='xadd_ext' else 'sub'
            if left is None or right is None:value=None
            elif left[0]=='stack_address' and right[0]=='constant':
                number=right[1]-(1<<64) if right[1]&(1<<63) else right[1]
                value=('stack_address',left[1]+(number if operation=='add' else -number),64)
            elif left[0]==right[0]=='constant':
                value=('constant',(left[1]+right[1] if operation=='add' else left[1]-right[1])&((1<<64)-1),64)
            else:value=(operation,left,right,64)
            if rd==31:
                if value is not None and value[0]=='stack_address':
                    self.checked_stack_offset(value[1])
                    if self.sp is None:self.cells={};self.epoch+=1;self.sp=value[1]
                    else:self.adjust(value[1])
                else:self.sp=None;self.cells={};self.epoch+=1
            else:self.write(rd,value)
            return
        if k in ('nop','ret','b','bcond','wcbz','wcbnz','xcbz','xcbnz','wtbz','wtbnz','xtbz','xtbnz'):return
        # CMP Xn,#0 is a flag write, not an integer-register write.
        if d.word&0xfffffc1f==0xf100001f:return
        if k in ('adr','adrp'):
            self.write(rd,None);return
        if k=='bl':
            # An opaque target has no admitted Swift/non-Swift preservation or
            # error convention. No prior scalar origin survives that boundary.
            self.registers={};self.cells={};self.sp=None;self.epoch+=1;return
        if k in ('mov','wmov'):self.write(rd,self.read(rn,bits),bits);return
        if k in ('movz','wmovz','movn','wmovn'):
            v=d.immediate if k.endswith('movz') else ~d.immediate
            self.write(rd,('constant',v&mask,bits),bits);return
        if k in ('xmovk','wmovk'):
            try:shift=int(d.addressing)
            except ValueError:self.fail('move_lane_unqualified')
            if shift not in range(0,bits,16):self.fail('move_lane_unqualified')
            old=self.read(rd,bits)
            value=('constant',((old[1]&~(0xffff<<shift))|(d.immediate<<shift))&mask,bits) if old and old[0]=='constant' else (
                ('insert_lane',old,('constant',d.immediate,bits),('constant',shift,bits),bits) if old else None)
            self.write(rd,value,bits);return
        if k in ('wand_imm','worr_imm','weor_imm','wands_imm','xand_imm','xorr_imm','xeor_imm','xands_imm'):
            source=self.read(rn,bits);literal=d.immediate&mask
            operation='orr' if 'orr' in k else ('eor' if 'eor' in k else 'and')
            if source is None:value=None
            elif source[0]=='constant':
                number=(source[1]|literal) if operation=='orr' else ((source[1]^literal) if operation=='eor' else source[1]&literal)
                value=('constant',number&mask,bits)
            else:value=(operation,source,('constant',literal,bits),bits)
            # ANDS also changes NZCV, which this value domain does not model.
            # Rd31 is ZR in every logical form, never SP.
            self.write(rd,value,bits);return
        if k in ('wcsel','wcsinc','wcsinv','wcsneg','xcsel','xcsinc','xcsinv','xcsneg'):
            # Without NZCV no input arm or increment/inversion/negation is
            # selected. Kill any old destination origin instead of guessing.
            self.write(rd,None,bits);return
        if k in ('wadds_reg','wsubs_reg','xadds_reg','xsubs_reg','wadd_reg','wsub_reg'):
            mode=d.addressing or 'lsl'
            if mode not in ('lsl','lsr','asr'):self.fail('register_shift_unqualified')
            right=self.shifted(self.read(d.rt2,bits),bits,mode,d.immediate)
            if rd==31:return  # flag-setting Rd31 is ZR, never SP
            left=self.read(rn,bits);operation='sub' if 'sub' in k else 'add'
            if left is None or right is None:value=None
            elif left[0]==right[0]=='constant':
                value=('constant',(left[1]+right[1] if operation=='add' else left[1]-right[1])&mask,bits)
            else:value=(operation,left,right,bits)
            self.write(rd,value,bits);return
        if k in tuple(prefix+operation+'_reg' for prefix in ('w','x')
                for operation in ('and','bic','orr','orn','eor','eon','ands','bics')):
            left=self.read(rn,bits);right=self.shifted(self.read(d.rt2,bits),bits,d.addressing,d.immediate)
            if rd==31:return
            operation=k[1:-4]
            if operation in ('bic','orn','eon','bics') and right is not None:
                right=('constant',(~right[1])&mask,bits) if right[0]=='constant' else ('bitwise_not',right,bits)
            operation='orr' if operation in ('orr','orn') else ('eor' if operation in ('eor','eon') else 'and')
            if left is None or right is None:value=None
            elif left[0]==right[0]=='constant':
                number=(left[1]|right[1]) if operation=='orr' else ((left[1]^right[1]) if operation=='eor' else left[1]&right[1])
                value=('constant',number&mask,bits)
            else:value=(operation,left,right,bits)
            self.write(rd,value,bits);return
        if k in ('xadd_reg','xsub_reg'):
            left,right=self.read(rn),self.read(d.rt2);operation='add' if k=='xadd_reg' else 'sub'
            if left is None or right is None:value=None
            elif left[0]==right[0]=='constant':
                value=('constant',(left[1]+right[1] if operation=='add' else left[1]-right[1])&((1<<64)-1),64)
            elif left[0]=='stack_address' and right[0]=='constant':
                value=('stack_address',left[1]+(right[1] if operation=='add' else -right[1]),64)
            elif operation=='add' and left[0]=='constant' and right[0]=='stack_address':
                value=('stack_address',left[1]+right[1],64)
            else:value=(operation,left,right,64)
            self.write(rd,value);return
        if k in ('add','sub','wadd','wadds','wsubs','xadds','xsubs','wlsl'):
            if k in ('add','sub') and rn==31:
                if self.sp is None:
                    self.write(rd,None);return
                value=self.sp+(d.immediate if k=='add' else -d.immediate)
                if rd==31:self.adjust(value)
                else:self.write(rd,('stack_address',value,64))
                return
            if rd==31:
                if k in ('wadds','wsubs','xadds','xsubs'):return
                self.fail('unsupported_stack_or_flag_effect')
            source=self.read(rn,bits);op='lsl' if k=='wlsl' else ('sub' if 'sub' in k else 'add')
            if source and source[0]=='stack_address' and k in ('add','sub'):
                value=('stack_address',source[1]+(d.immediate if k=='add' else -d.immediate),64)
            elif source and source[0]=='constant':
                value=source[1]<<d.immediate if op=='lsl' else source[1]+(d.immediate if op=='add' else -d.immediate)
                value=('constant',value&mask,bits)
            else:value=(op,source,('constant',d.immediate&mask,bits),bits) if source else None
            self.write(rd,value,bits);return
        if k in ('xubfm','wubfm'):
            try:immr=int(d.addressing)
            except ValueError:self.fail('unsigned_bitfield_unqualified')
            imms=d.immediate
            if not 0<=immr<bits or not 0<=imms<bits:self.fail('unsigned_bitfield_unqualified')
            source=self.read(rn,bits)
            if source is None:value=None
            elif source[0]=='constant':
                number=((source[1]>>immr)&((1<<(imms-immr+1))-1)) if imms>=immr else (
                    (source[1]&((1<<(imms+1))-1))<<(bits-immr))
                value=('constant',number&mask,bits)
            else:value=('unsigned_bitfield',source,('constant',immr,bits),('constant',imms,bits),bits)
            self.write(rd,value,bits);return
        if k in ('xsbfm','wsbfm') and d.addressing=='0' and 0<=d.immediate<bits:
            source=self.read(rn,bits);n=d.immediate+1
            if source and source[0]=='constant':
                v=source[1]&((1<<n)-1)
                if v&(1<<(n-1)):v-=1<<n
                value=('constant',v&mask,bits)
            else:value=('sign_extend',source,('constant',n,bits),bits) if source else None
            self.write(rd,value,bits);return
        if k in ('xstr','wstr','xldr','wldr','xldr_post','stp','ldp','wstrb','wldrb','wstrh','wldrh','xstr_raw','xldr_raw','xstur','xldur','qstr','wstr_raw','wldr_raw','wstur','wldur') or k in FP_MEMORY_STORES:
            mode=d.addressing or 'offset';pair=k in ('stp','ldp')
            load=k in ('xldr','wldr','xldr_post','ldp','wldrb','wldrh','xldr_raw','xldur','wldr_raw','wldur')
            regs=(rd,d.rt2) if pair else (rd,)
            if mode not in ('offset','pre','post'):self.fail('memory_mode_unqualified')
            if load and len(set(regs))!=len(regs):self.fail('memory_register_overlap')
            if mode!='offset' and rn!=31 and rn in regs:self.fail('memory_writeback_overlap')
            source=self.read(rn);base=self.sp if rn==31 else (source[1] if source and source[0]=='stack_address' else None)
            if base is None or self.sp is None:
                if load:
                    for reg in regs:self.write(reg,None)
                else:self.cells={};self.epoch+=1
                # The unknown memory address does not suppress architectural
                # base writeback. Conservatively discard even known non-stack
                # constants/results/error aliases; no old origin may survive.
                if mode in ('pre','post'):
                    if rn==31:self.sp=None
                    else:self.write(rn,None)
                return
            size=8 if pair else MEMORY_WIDTHS.get(k,bits//8)
            offset=base+(0 if mode=='post' else d.immediate)
            if mode=='pre' and rn==31:self.adjust(offset)
            if offset<self.sp or offset+size*len(regs)>0:self.fail('memory_outside_frame')
            if load:
                for i,reg in enumerate(regs):
                    cell=self.cells.get(offset+i*size)
                    self.write(reg,cell[2] if cell and cell[0]==size else None,size*8)
            else:
                end=offset+size*len(regs)
                self.cells={p:c for p,c in self.cells.items() if p+c[0]<=offset or p>=end};self.epoch+=1
                for i,reg in enumerate(regs):self.cells[offset+i*size]=(size,self.epoch,None if k in FP_MEMORY_STORES else self.read(reg,size*8))
                self.bound()
            if mode in ('pre','post'):
                if rn==31:
                    if mode=='post':self.adjust(base+d.immediate)
                else:self.write(rn,('stack_address',base+d.immediate,64))
            return
        self.fail('value_transfer_unqualified')


def _validate_stable_abi(image,caller,callee,cp,decl,abi,read,mapped,ins,charge,need,limits):
    """Reproduce selected stable-ABI capability checks without its admitter.

    Frozen storage capabilities are assumptions with retained evidence identities;
    independent raw checks corroborate only register/store forms, never source
    implementation, execution, receiver ownership, or compiler verification.
    """
    from .swift_abi_profiles import (STABLE_STORAGE_CAPABILITIES,STABLE_LOWERING_OBSERVATIONS,
        _V2_SLICES,_V2_SOURCE,ABI_REFERENCES,_COMPILER,OWNED_SOURCE_BY_SLICE)
    import json
    need(abi.get('status')=='admitted' and abi.get('error_register')=='x21'
        and abi.get('research_only') is True and abi.get('compiler_verified') is False
        and abi.get('profile_assumption')=='explicit_selected_swift6_stable_arm64_sync_untyped','stable_profile_assumption')
    need(decl.throws,'stable_throws_required','unresolved')
    selected_source=OWNED_SOURCE_BY_SLICE.get(image.slice_sha256);owned=selected_source is not None
    parameters,output=decl.parameter_types,decl.result_type
    specialization=decl.specialization
    if specialization:
        need(owned and not specialization.async_removed and not specialization.representation_changed
            and specialization.kind.value=='generic_reabstracted'
            and all(b.replacement.name=='Swift.Int' and not b.replacement.arguments for b in specialization.bindings),
            'stable_specialization_unqualified','unresolved')
        parameters,output=specialization.substituted_parameter_types,specialization.substituted_result_type
    else:need(not decl.generic_parameter_counts and not decl.generic_requirements,'stable_generic_unqualified','unresolved')
    def key(node):return node.name+('<'+','.join(key(a) for a in node.arguments)+'>' if node.arguments else '')
    shape=key(output);cap=STABLE_STORAGE_CAPABILITIES.get(shape)
    need(cap is not None and not output.inout and output.generic_depth is None
        and (not shape.startswith('BroadOwned.') or owned),'stable_result_shape','unresolved')
    expected_storage=asdict(cap);expected_storage['locations']=list(cap.locations)
    need(abi.get('result_storage')==expected_storage and abi.get('result_type')==shape
        and abi.get('result_location')==(cap.locations[0] if cap.locations else None),'stable_result_storage')
    arguments=[];integer=floating=0
    for node in parameters:
        shape_arg=key(node);need(node.generic_depth is None,'stable_argument_generic','unresolved')
        if node.inout:
            need(shape_arg=='Swift.Int','stable_inout_shape','unresolved')
            loc=[f'indirect x{integer}'];integer+=1;evidence='swift-stable-v2-inout-int'
        elif shape_arg in ('Swift.Float','Swift.Double'):
            loc=[('s' if shape_arg=='Swift.Float' else 'd')+str(floating)];floating+=1
            evidence=STABLE_STORAGE_CAPABILITIES[shape_arg].evidence_id
        elif shape_arg in STABLE_STORAGE_CAPABILITIES and shape_arg.startswith('Swift.') and shape_arg!='Swift.Void':
            argcap=STABLE_STORAGE_CAPABILITIES[shape_arg];loc=[('w' if argcap.bit_width<64 else 'x')+str(integer)]
            integer+=1;evidence=argcap.evidence_id
        elif shape_arg=='Tuple<Swift.Int,Swift.Bool>':
            loc=[f'x{integer}',f'w{integer+1}'];integer+=2;evidence='swift-stable-v2-tuple-int-bool'
        elif owned and shape_arg in ('BroadOwned.BroadSmall','BroadOwned.BroadLarge'):
            loc=[f'indirect x{integer}'];integer+=1;evidence='owned-v2-resilient-argument'
        elif owned and shape_arg in ('Swift.String','Swift.Array<Swift.Int>'):
            n=2 if shape_arg=='Swift.String' else 1;loc=[f'x{i}' for i in range(integer,integer+n)]
            integer+=n;evidence='owned-v2-string-array-argument'
        else:raise _Stop('stable_argument_shape','unresolved')
        need(integer<=8 and floating<=8,'stable_argument_capacity','unresolved')
        arguments.append(dict(type=shape_arg,locations=loc,evidence_id=evidence,inout=node.inout))
    need(abi.get('argument_storage')==arguments and abi.get('argument_locations')==[a['locations'] for a in arguments],
        'stable_argument_storage')
    if specialization:need(specialization.pass_id==5 and not specialization.serialized
        and specialization.dropped_argument_ordinals in ((),(2,),(3,),(4,)),
        'stable_specialization_arguments','unresolved')
    original=decl.original_callable_kind or decl.callable_kind;receiver=None
    if original.value in ('struct_instance_method','enum_instance_method'):
        need(owned,'stable_value_receiver_unqualified','unresolved');receiver='indirect x20'
    elif original.value=='class_instance_method':receiver='reference x20'
    need(abi.get('receiver_location')==receiver,'stable_receiver_storage')
    lowering=abi.get('evidence',{}).get('lowering',{})
    expected_observations=[dict(pc=hex(pc),raw_bytes=raw,meaning=meaning,source_case=case)
        for pc,raw,meaning,case in STABLE_LOWERING_OBSERVATIONS]
    need(lowering.get('qualification_id')==cap.evidence_id
        and lowering.get('source_evidence_id')=='owned-v2-fixed-initial-lowering-observations'
        and lowering.get('source_sha256')==_V2_SOURCE
        and 'selected_source_sha256' in lowering and lowering['selected_source_sha256']==selected_source
        and lowering.get('selected_slice_sha256')==image.slice_sha256
        and lowering.get('compiler')==_COMPILER and lowering.get('target')=='arm64-apple-macosx14.0'
        and lowering.get('reference_slice_sha256') in _V2_SLICES
        and lowering.get('public_abi_references')==list(ABI_REFERENCES)
        and lowering.get('observations')==expected_observations
        and lowering.get('assumption')==abi['profile_assumption'] and lowering.get('compiler_verified') is False,
        'stable_evidence_identity')
    need(json.dumps(lowering.get('specialization'),sort_keys=True)==json.dumps(asdict(specialization) if specialization else None,sort_keys=True),
        'stable_specialization_identity')
    preconditions=['well_formed_swift_stable_arm64_calling_convention','synchronous_untyped_throws',
        'caller_supplies_error_register_state_required_by_convention']
    if 'profile_preconditions' in abi:need(abi['profile_preconditions']==preconditions,'stable_profile_preconditions')
    if 'family' in abi or 'family_evidence' in abi:
        if specialization:family='concrete_generic_specialization'
        elif not decl.context:family='free'
        else:
            leaf=decl.context[-1];family=None
            if owned and decl.module=='BroadOwned' and leaf.name.startswith('BroadOwner'):
                suffix=leaf.name[len('BroadOwner'):]
                if len(suffix)==4 and suffix.isdigit():
                    index=int(suffix)
                    if index in range(297,340,3):family='extension'
                    elif index in range(235,295,2):family='direct_final_class'
            if family is None:
                family='enum' if leaf.kind=='enum' else ('static_type' if decl.callable_kind.value=='static_method' else (
                    'struct' if leaf.kind=='struct' else 'direct_class_research'))
        if 'family' in abi:need(abi['family']==family,'stable_family_lineage')
        if 'family_evidence' in abi:need(abi['family_evidence']==dict(source_sha256=selected_source,
            compiled_target_pc=hex(callee.start),direct_call_pc=hex(cp),
            scope='source_lineage_plus_exact_emitted_target_not_runtime_dispatch'),'stable_family_evidence')
    if 'abi_shape' in abi:
        shape_expected=dict(arguments=arguments,receiver=receiver,result=asdict(cap),error_register='x21',specialized=specialization is not None)
        need(json.dumps(abi['abi_shape'],sort_keys=True)==json.dumps(shape_expected,sort_keys=True),'stable_abi_shape')
    if 'caller_error_observations' in abi:
        before_start=max(caller.start,cp-128);after_end=min(caller.end,cp+68)
        observation=dict(clear_instruction_pcs=[hex(pc) for pc in range(before_start,cp,4)
            if ins(pc).word in (0xd2800015,0x52800015,0xaa1f03f5)],
            test_instruction_pcs=[hex(pc) for pc in range(cp+4,after_end,4) if ins(pc).word&0x7e00001f==0x34000015],
            incoming_state_proven=False,scope='instruction_presence_not_path_or_state_proof')
        need(abi['caller_error_observations']==observation,'stable_caller_instruction_observations')
    # A raw zero must survive the bounded straight-line prefix. Copying a known
    # zero is accepted; intervening branches/calls or unknown writes are not.
    state=_ScalarReplay(cp,limits,charge);state.registers={};state.sp=None
    for pc in range(max(caller.start,cp-128),cp,4):
        d=ins(pc)
        if d.kind in ('bl','b','ret','brk','bcond','xcbz','xcbnz','wcbz','wcbnz','xtbz','xtbnz','wtbz','wtbnz'):
            state.registers={};break
        try:state.step(d)
        except _Stop as exc:
            if exc.reason!='value_transfer_unqualified':raise
            state.registers.pop(d.rd,None)
    incoming=state.read(21)
    need(not incoming or incoming[0]!='constant' or incoming[1]==0,'caller_error_contract_contradiction','blocked')
    # A lexical suffix has no dominance proof: earlier branches may bypass a
    # visible clear. Preserve the convention as an explicit precondition.
    caller_error_state='unproven_profile_precondition'
    need(callee.size//4<=limits.max_instructions,'stable_callee_budget','unresolved')
    raw=read(mapped(callee.start,callee.size),callee.size);words=struct.unpack('<'+'I'*(len(raw)//4),raw)
    transport_copy=any(_is_error_transport_instruction(word) for word in words)
    preserved_leaf=not transport_copy and _independent_leaf_preserves_x21(words,charge=charge)
    need(transport_copy or preserved_leaf,'stable_error_transport','unresolved')
    error_observation=dict(mode='distinct_nonzero_gpr_copy' if transport_copy else 'preserved_x21_leaf',register='x21',
        scope='instruction_effects_if_normal_return_not_incoming_state_or_object_type',entry_pc=hex(callee.start),
        return_pc=hex(callee.end-4) if preserved_leaf else None,word_count=len(words),
        preserves_incoming_x21=True if preserved_leaf else None,incoming_state_proven=False,error_object_type_proven=False)
    need(lowering.get('callee_error_observation')==error_observation
        and lowering.get('callee_error_transport_observation')==('mov_to_x21_from_distinct_nonzero_gpr_presence' if transport_copy
            else 'x21_preserved_by_exact_straightline_leaf_effects') and lowering.get('error_object_type_proven') is False,
        'stable_error_observation')
    if specialization:
        formal_locations=[location for argument in arguments for location in argument['locations']]
        need(_formal_prefix_inputs(words,formal_locations,charge=charge),'stable_specialization_formal_inputs','unresolved')
    if cap.category=='void':corroborated=0xd65f03c0 in words
    elif cap.indirect:
        corroborated=any(_is_direct_result_store(w) for w in words)
    elif cap.locations in (('s0',),('d0',)):
        double=cap.locations==('d0',)
        unary=(0x9e670000,0x9e620000) if double else (0x1e270000,0x9e220000)
        binary=(0x1e611800,0x1e612800) if double else (0x1e211800,0x1e212800)
        corroborated=any(w&31==0 and (w&0xfffffc00 in unary or
            w&0xffe0fc00 in tuple(base&0xffe0fc00 for base in binary)) for w in words)
    else:
        corroborated=all(any(_allocated_result_gpr_write(w,int(loc[1:])) for w in words) for loc in cap.locations)
    need(corroborated,'stable_result_bytes','unresolved')
    # The selected reference slice can corroborate the frozen source observation
    # bytes directly without any source or digest verification rerun.
    if image.slice_sha256 in _V2_SLICES and image.slice_sha256==lowering['reference_slice_sha256']:
        for pc,raw,_,_ in STABLE_LOWERING_OBSERVATIONS:
            expected=bytes.fromhex(raw);need(read(mapped(pc,len(expected)),len(expected))==expected,'stable_reference_bytes','unresolved')
    return expected_storage,caller_error_state


def _retention_cost(value,limits,charge):
    """Charge retained JSON expansion before appending a potentially shared tree."""
    todo=[(value,0)];items=size=0
    while todo:
        node,depth=todo.pop();charge();items+=1
        if items>limits.max_container_items or depth>limits.max_depth:raise _Stop('validator_output_limit','unresolved')
        if isinstance(node,dict):
            size+=2+2*len(node)
            for key,child in node.items():size+=2+6*len(key);todo.append((child,depth+1))
        elif isinstance(node,(tuple,list)):
            size+=2+2*len(node);todo.extend((child,depth+1) for child in node)
        elif isinstance(node,str):size+=2+6*len(node)
        else:size+=21
        if size>limits.max_bytes:raise _Stop('validator_output_limit','unresolved')
    return items,size


def _is_error_transport_instruction(word):
    """Presence of a genuine X-register copy into x21; no pointer semantics."""
    return word&0xffe0ffff==0xaa0003f5 and (word>>16)&31 not in (21,31)


def _is_direct_result_store(word):
    """Exact ordinary stores addressed by x8, excluding loads and prefetches."""
    if (word>>5)&31!=8:return False
    vector=bool(word&0x04000000);size=(word>>30)&3
    if word&0x3b000000==0x39000000:
        opc=(word>>22)&3
        return opc==0 or vector and opc==2 and size==0
    if word&0x3b000000==0x29000000 and not word&0x00400000 and (word>>23)&3==2:
        return size in ((0,1,2) if vector else (0,2))
    return False


def _prefix_operand_effects(word):
    """Raw GPR operands for the independently qualified entry-prefix subset.

    Reads use the original register bank and precede writes in one instruction.
    Unknown encodings terminate the prefix; no guessed destination can preserve
    some other unseen formal input across an unclassified effect.
    """
    rd,rn,rm=word&31,(word>>5)&31,(word>>16)&31
    if (word&0x7c000000==0x14000000 or word&0xff000000==0x54000000
        or word&0x7e000000 in (0x34000000,0x36000000) or word&0xfe000000==0xd6000000):
        return set(),set(),True,True
    if not _prefix_encoding_allocated(word):return set(),set(),False,False
    reads=set();writes=set();known=True
    if word&0x1f000000==0x11000000:
        reads.add(rn);writes.add(rd)
    elif word&0x1f000000 in (0x0a000000,0x0b000000):
        reads.update((rn,rm));writes.add(rd)
    elif word&0x1f800000 in (0x12000000,0x13000000):
        reads.add(rn);writes.add(rd)
    elif word&0x1f800000==0x12800000 or word&0x1f000000==0x10000000:
        writes.add(rd)
    elif word&0x3a000000==0x28000000:
        reads.add(rn)
        if not word&0x04000000:
            if word&0x00400000:writes.update((rd,(word>>10)&31))
            else:reads.update((rd,(word>>10)&31))
        if (word>>23)&3 in (1,3):
            writes.add(rn)
            if rn!=31:known=False
    elif word&0x3a000000==0x38000000:
        reads.add(rn)
        if not word&0x04000000:
            # opc00 is an integer store. opc10/11 include signed loads;
            # testing only bit22 would mistake them for stores.
            if (word>>22)&3==0:reads.add(rd)
            elif not ((word>>22)&3==2 and (word>>30)&3==3):writes.add(rd)
        if word&0x3b200c00==0x38200800:reads.add(rm)
        if not word&0x01000000 and not word&0x00200000 and (word>>10)&3 in (1,3):
            writes.add(rn)
            if rn!=31:known=False
    elif word==0xd503201f:pass
    else:known=False
    return reads-{31},writes-{31},False,known


def _formal_prefix_inputs(words,locations,*,charge=lambda n=1:None):
    """Corroborate original physical formals before clobber/control transfer.

    Raw specialization drop ordinals are never mapped to source argument indices.
    No hidden metadata/context location is inferred. FP locations are not GPRs.
    """
    wanted=set()
    for location in locations:
        match=re.fullmatch(r'(?:indirect )?[xw]([0-9]|[12][0-9]|30)',location)
        if match:wanted.add(int(match[1]))
    live=set(wanted);observed=set()
    for word in words:
        charge();reads,writes,control,known=_prefix_operand_effects(word)
        if control or not known:break
        observed.update(reads&live);live-=writes
        if wanted<=observed:return True
    return wanted<=observed


def _prefix_encoding_allocated(word):
    """Allocation guards for exactly the raw classes used by prefix evidence.

    This is intentionally narrower than architectural disassembly. Register use
    cannot be inferred from a major opcode when reserved width/control bits
    would make the word undefined or a different instruction family.
    """
    wide=bool(word&0x80000000)
    if word&0x1f000000==0x11000000:
        return not word&0x00800000
    if word&0x1f000000==0x0b000000:
        if word&0x00200000:
            return (word>>22)&3==0 and (word>>10)&7<=4 and (wide or (word>>13)&7 not in (3,7))
        return (word>>22)&3!=3 and (wide or (word>>10)&63<32)
    if word&0x1f000000==0x0a000000:
        return wide or (word>>10)&63<32
    if word&0x1f800000==0x12000000:
        n,imms=(word>>22)&1,(word>>10)&63
        length=((n<<6)|(~imms&63)).bit_length()-1
        if not wide and n or length<1:return False
        levels=(1<<length)-1
        return 1<<length<=(64 if wide else 32) and imms&levels!=levels
    if word&0x1f800000==0x13000000:
        return (word>>29)&3!=3 and (word>>22)&1==int(wide) and (
            wide or ((word>>16)&63<32 and (word>>10)&63<32))
    if word&0x1f800000==0x12800000:
        return (word>>29)&3!=1 and (wide or (word>>21)&3<2)
    if word&0x1f000000==0x10000000:return True
    size,vector,opc=(word>>30)&3,bool(word&0x04000000),(word>>22)&3
    if word&0x3a000000==0x28000000:
        # Signed-word pair loads are conservatively outside the prefix subset.
        return size in ((0,1,2) if vector else (0,2))
    if word&0x3a000000==0x38000000:
        if vector:
            if opc in (2,3) and size!=0:return False
        elif opc==3 and size>=2:return False
        unsigned=word&0x3b000000==0x39000000
        if unsigned:return True
        if word&0x3b000000!=0x38000000:return False
        mode=(word>>10)&3
        if word&0x00200000:
            return mode==2 and (word>>13)&7 in (2,3,6,7)
        if vector and mode==2:return False
        if not vector and size==3 and opc==2 and mode!=0:return False
        return True
    return word==0xd503201f


def _allocated_result_gpr_write(word,register):
    """A real allocated GPR destination, not a guessed major-opcode field."""
    if word&31!=register:return False
    if (word&0x1f000000 in (0x11000000,0x0b000000,0x0a000000)
        or word&0x1f800000 in (0x12000000,0x12800000,0x13000000)):
        return _prefix_encoding_allocated(word)
    if word&0x1fe00000==0x1a800000:
        from .swift_broad_instructions import decode_instruction
        from .arm64 import ModelError
        try:instruction=decode_instruction(word)
        except ModelError:return False
        return instruction.kind in ('wcsel','wcsinc','wcsinv','wcsneg','xcsel','xcsinc','xcsinv','xcsneg')
    # Same-width MADD/MSUB only; reserved S/opcode bits cannot denote writes.
    return word&0x7fe00000==0x1b000000


def _symbol_visibility_allowed(kind,desc,declaration,call_kind):
    """Exact raw nlist visibility coupled to the independently parsed identity.

    The caller already requires a sole raw entry alias and exact local target.
    Private weak visibility is confined to direct-BL concrete specializations;
    it is never authority inferred from an admission report or symbol spelling.
    """
    if kind==15 and not desc&0x380:return True
    if (kind==30 and desc==0 and call_kind=='bl' and declaration.throws
        and declaration.callable_kind.value=='static_method' and declaration.context
        and declaration.context[-1].kind=='class' and declaration.specialization is None):return True
    restricted=(kind==14 and desc==0) or (kind==0x1e and desc==0x80 and call_kind=='bl')
    specialization=declaration.specialization
    return (restricted and declaration.callable_kind.value=='generic_specialization'
        and specialization is not None and bool(specialization.bindings))


def _independent_leaf_preserves_x21(words,*,charge=lambda n=1:None):
    """Exact local instruction effects, conditional on normal single-leaf RET.

    This establishes neither the incoming x21 value nor an error object's type.
    All reads come from the independently selected callee bytes. Unknown or
    reserved effects, calls, exceptions, other control and every GPR21 write
    refuse this alternative to a distinct-register transport copy.
    """
    from .arm64 import ModelError,_FP_DESTINATION_KINDS
    from .swift_broad_instructions import (decode_instruction,destination_register_bank,
        FP_FLAG_KINDS,MEMORY_WIDTHS)
    if not words or len(words)>256 or words[-1]!=0xd65f03c0:return False
    loads={'ldp','xldr','wldr','xldr_post','xldr_raw','xldur','wldr_raw','wldur','wldrb','wldrh'}
    memory=set(MEMORY_WIDTHS)|{'stp','ldp','xldr','wldr','xstr','wstr','xldr_post'}
    for word in words[:-1]:
        charge()
        if type(word) is not int or not 0<=word<=0xffffffff:return False
        reads,writes,control,known=_prefix_operand_effects(word)
        if control:return False
        if known:
            if 21 in writes:return False
            continue
        prefix_class=(word&0x1f000000 in (0x11000000,0x0a000000,0x0b000000,0x10000000)
            or word&0x1f800000 in (0x12000000,0x13000000,0x12800000)
            or word&0x3a000000 in (0x28000000,0x38000000))
        if prefix_class and not _prefix_encoding_allocated(word):return False
        try:instruction=decode_instruction(word)
        except ModelError:return False
        if instruction.kind in ('ret','bl','brk','b','bcond','wcbz','wcbnz','xcbz','xcbnz','wtbz','wtbnz','xtbz','xtbnz'):return False
        if instruction.addressing in ('pre','post') and instruction.rn==21:return False
        bank=destination_register_bank(instruction)
        if bank=='fp' or instruction.kind in FP_FLAG_KINDS or instruction.kind=='nop':continue
        if instruction.kind in memory:
            if instruction.addressing not in ('','offset','pre','post'):return False
            if instruction.kind in loads and (instruction.rd==21 or instruction.kind=='ldp' and instruction.rt2==21):return False
            continue
        if bank=='gpr' or instruction.kind in _FP_DESTINATION_KINDS:
            if instruction.rd==21:return False
            continue
        return False
    return True
