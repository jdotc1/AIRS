"""Bounded broad Swift candidate producer; never grants eligible status.

All paths and return tails are structural byte facts. A qualified x21 seed means
only the admitted ABI's post-call error value; it proves neither call return nor
execution. The independent validator must rederive the candidate's claims.
"""
from __future__ import annotations
import json
from dataclasses import replace
from .swift_broad_profiles import PROFILES
from .swift_error_cfg import SwiftCFGLimits, build_swift_cfg
from .swift_broad_instructions import decode_instruction
from .swift_outcome_values import (RegisterCopy, ValueLimits, initial_state,
                                    transfer_swift_value)
from .swift_outcome_witness_v2_models import (
    BroadWitnessLimits, WITNESS_MODEL, VALIDATION_MODEL, preflight_broad_json,
    encode_broad_witness,
    public_broad_record,
)


class _Refusal(Exception):pass


def _range(function):
    return {'start_pc':hex(function.start),'end_pc_exclusive':hex(function.end),
            'boundary_source':function.boundary_source}


def _provenance(provenance):
    result={}
    for name in ('call','callee_entry'):
        row=provenance.get(name,{})
        result[name]={key:hex(row[key]) if type(row.get(key)) is int else row.get(key)
                      for key in ('pc','word','slice_file_offset','container_file_offset')}
    return result


def build_broad_swift_witness(image, function, callsite:dict, *,
                             limits=BroadWitnessLimits(), profile='broad-v1')->dict:
    if not isinstance(limits,BroadWitnessLimits):raise TypeError('limits must be BroadWitnessLimits')
    result={'model_version':WITNESS_MODEL,'validation_model':VALIDATION_MODEL,
            'profile':profile,'source_models':{},'status':'unresolved','eligible':False,
            'reason':'candidate_facts_incomplete','identity':{},'call':{},'cfg':{},
            'post_call':{'status':'unknown','reason':'not_examined','test_pc':None,
                         'test_word':None,'test_register':None,'error_successor_pc':None,
                         'success_successor_pc':None,'trace':[]},
            'regions':{'status':'unknown','success_entry_pc':None,'error_entry_pc':None,
                       'paths':[],'tails':[]},
            'value_facts':{'seed':None,'observations':[]},
            'completeness':{'complete':False,'missing':[]},
            'accounting':{'work':0,'instructions':0,'blocks':0,'edges':0,
                          'value_steps':0,'encoded_bytes':0},
            'limitations':['candidate_requires_independent_validation',
                'research_only','runtime_call_return_unproven','paths_structural_only',
                'dominance_and_exclusivity_unproven','source_reconstruction_forbidden']}
    missing=result['completeness']['missing']
    def need(ok,reason):
        if not ok:raise _Refusal(reason)
    def work(n=1):
        need(n<=limits.max_work-result['accounting']['work'],'witness_work_limit')
        result['accounting']['work']+=n
    try:
        need(profile=='broad-v1','unsupported_profile')
        models=PROFILES[profile]
        result['source_models']={'edge':models.edge_model,'witness':models.witness_model,
            'validation':models.validation_model,'cfg':'swift-bounded-structural-cfg-v1',
            'value':'swift-outcome-values-v1'}
        need(type(callsite) is dict,'callsite_object_required')
        need(callsite.get('status')=='admitted_callsite','callsite_not_admitted')
        pc,target=callsite.get('call_pc'),callsite.get('callee_pc')
        need(type(pc) is int and type(target) is int,'integer_call_addresses_required')
        need(0<=pc<1<<64 and 0<=target<1<<64 and pc%4==target%4==0,'call_address_range')
        work(len(image.functions)+len(image.sections))
        need(len(image.functions)<=limits.max_work and len(image.sections)<=limits.max_work,'image_metadata_limit')
        need(function in image.functions and function.start<=pc<function.end,'caller_membership')
        callees=[f for f in image.functions if f.start==target]
        need(len(callees)==1,'callee_membership')
        result['identity']={'slice_sha256':image.slice_sha256,
            'container_sha256':image.container_sha256,'slice_offset':hex(image.slice_offset),
            'slice_size':hex(image.slice_size),'architecture':image.architecture,
            'uuid':image.uuid,'preferred_base':hex(image.preferred_base),
            'slice_index':image.slice_index,'container_slice_count':image.container_slice_count,
            'cpu_subtype':image.cpu_subtype,'caller':_range(function),
            'callee':_range(callees[0]),'call_pc':hex(pc)}
        # Copy only selected bounded admission/ABI facts, never the binding arrays.
        selected={'provenance':_provenance(callsite.get('provenance',{})),
                  'declaration':callsite.get('declaration',{}),
                  'abi':public_broad_record(callsite.get('abi',{}),limits=limits)}
        preflight_broad_json(selected,limits=limits)
        selected=json.loads(json.dumps(selected))
        word=int.from_bytes(image.bytes_at(pc,4),'little')
        need(word&0xfc000000==0x94000000,'direct_bl_required')
        displacement=word&0x3ffffff
        if displacement&0x2000000:displacement-=0x4000000
        need(pc+displacement*4==target,'raw_call_target_mismatch')
        need(selected['provenance']['call'].get('word')==f'0x{word:08x}', 'call_provenance_mismatch')
        result['call']={'pc':hex(pc),'word':f'0x{word:08x}','callee_pc':hex(target),**selected}
        need(selected['declaration'].get('status')=='syntax_admitted','declaration_unqualified')
        abi=selected['abi']
        qualified=(abi.get('status')=='admitted' and abi.get('profile') in (
            'swift6-arm64-sync-untyped-research-v1','swift6-arm64-sync-untyped-stable-research-v2')
            and abi.get('error_register')=='x21'
            and bool(abi.get('evidence',{}).get('lowering',{}).get('qualification_id')))
        if not qualified:missing.append('abi_unqualified')
        cfg=build_swift_cfg(image,function,limits=SwiftCFGLimits(
            max_work=limits.max_work-result['accounting']['work'],
            max_blocks=limits.max_blocks,max_edges=limits.max_edges,
            max_depth=min(limits.max_depth,4096),max_retained_words=limits.max_instructions))
        result['cfg']=cfg
        for key,source in (('instructions','retained_words'),('blocks','blocks'),('edges','edges')):
            result['accounting'][key]=cfg['accounting'][source]
        work(cfg['accounting']['work'])
        need(cfg['completeness']['complete'],'cfg_'+str(cfg['reason']))
        if qualified:
            _post_call(result,pc,limits,work)
        else:result['post_call']['reason']='abi_unqualified'
        if result['post_call']['status']!='candidate':missing.append(result['post_call']['reason'])
        result['completeness']['complete']=not missing
        if not missing:result['reason']='validation_required'
    except (_Refusal,ValueError,KeyError,TypeError,AttributeError) as exc:
        missing.append(str(exc) or 'malformed_candidate_input')
    except Exception as exc:
        # Mapping/decoder input errors are refusal, never eligibility.
        from .types import InputError
        if not isinstance(exc,InputError):raise
        missing.append(exc.code)
    # A failed serialization never returns a partial graph masquerading as complete.
    try:
        raw=encode_broad_witness(result,limits=limits)
        result['accounting']['encoded_bytes']=len(raw)
        # At most two digit-boundary adjustments are possible at this ceiling.
        for _ in range(3):
            size=len(encode_broad_witness(result,limits=limits))
            if size==result['accounting']['encoded_bytes']:break
            result['accounting']['encoded_bytes']=size
    except ValueError:
        result['cfg']={};result['call']={};result['value_facts']={'seed':None,'observations':[]}
        result['post_call'].update(status='unknown',reason='witness_output_limit',trace=[])
        result['regions']={'status':'unknown','success_entry_pc':None,'error_entry_pc':None,'paths':[],'tails':[]}
        result['completeness']={'complete':False,'missing':['witness_output_limit']}
        result['reason']='candidate_facts_incomplete'
        result['accounting']['encoded_bytes']=0
    return result


def _post_call(result,pc,limits,work):
    rows=[row for block in result['cfg']['blocks'] for row in block['instructions']]
    by_pc={int(row['pc'],16):row for row in rows}
    post=result['post_call'];post['reason']='post_call_test_unknown'
    stable=result['call']['abi'].get('profile')=='swift6-arm64-sync-untyped-stable-research-v2'
    seed=RegisterCopy('raw_post_call_register:x21' if stable else 'abi_post_call_error:x21',64)
    vl=ValueLimits(max_state_entries=limits.max_state_entries,
                   max_provenance_depth=limits.max_depth,max_steps=limits.post_call_window,
                   max_provenance_nodes=limits.max_provenance_nodes)
    state=initial_state({'x21':seed},limits=vl)
    # Recover a frame only across an exact linear function-entry prefix. A
    # conditional predecessor or unmodeled effect cannot invent stack identity.
    prefix=initial_state(limits=replace(vl,max_steps=limits.max_instructions))
    prefix_limits=replace(vl,max_steps=limits.max_instructions)
    frame_known=True
    for address in range(int(result['identity']['caller']['start_pc'],16),pc,4):
        work()
        row=by_pc.get(address)
        if row is None:frame_known=False;break
        instruction=decode_instruction(int(row['word'],16),address)
        if instruction.kind in ('ret','brk','bl','b','bcond','xcbz','xcbnz','wcbz','wcbnz',
                                'xtbz','xtbnz','wtbz','wtbnz'):
            frame_known=False;break
        if instruction.kind in ('adr','adrp'):
            # Address materialization cannot write SP. Forget a prior frame
            # alias in its destination without treating the address as a value.
            prefix=replace(prefix,registers=tuple((reg,value) for reg,value in prefix.registers
                                                  if reg!=instruction.rd))
            continue
        step=transfer_swift_value(prefix,instruction,limits=prefix_limits)
        if step.status!='resolved':frame_known=False;break
        prefix=step.state
    state=replace(state,sp_offset=prefix.sp_offset if frame_known else None)
    result['value_facts']['seed']={'register':'x21','kind':'register_copy',
                                   'origin':seed.origin,'width':64}
    cursor=pc+4;seen=set();comparison=None
    for _ in range(limits.post_call_window):
        work();row=by_pc.get(cursor)
        if row is None:break
        if cursor in seen:post['reason']='post_call_cycle';return
        seen.add(cursor)
        post['trace'].append(row['pc'])
        ins=decode_instruction(int(row['word'],16),cursor)
        value=state.read_register(ins.rn) if ins.rn is not None else None
        compare_test=(comparison is not None and ins.kind=='bcond' and ins.addressing in ('0','1'))
        if comparison is not None and not compare_test:
            post['reason']='comparison_branch_not_adjacent_or_supported';return
        if (ins.kind in ('xcbz','xcbnz') and value==seed) or compare_test:
            target=cursor+ins.immediate;fall=cursor+4
            zero_target=ins.kind=='xcbz' or (compare_test and ins.addressing=='0')
            error,success=(fall,target) if zero_target else (target,fall)
            if error not in by_pc or success not in by_pc:break
            post.update(status='candidate',reason='qualified_error_alias_zero_test',
                test_pc=hex(cursor),test_word=row['word'],test_register=f'x{comparison[0] if compare_test else ins.rn}',
                error_successor_pc=hex(error),success_successor_pc=hex(success))
            if compare_test:
                post.update(test_kind='cmp_zero_bcond',comparison_pc=hex(comparison[1]),
                    comparison_word=comparison[2],test_condition='eq' if zero_target else 'ne')
            result['regions'].update(status='structural_candidates',
                success_entry_pc=hex(success),error_entry_pc=hex(error),
                paths=[{'outcome':name,'entry_pc':hex(entry),'reachability':'unproven'}
                       for name,entry in (('success',success),('error',error))],
                tails=[])
            _partition_regions(result,by_pc,success,error,work)
            return
        # CMP Xn,#0 is SUBS XZR,Xn,#0. Only an adjacent EQ/NE branch
        # consumes these flags; no intervening write or narrowing is admitted.
        if ins.kind=='xsubs' and ins.rd==31 and ins.immediate==0 and value==seed:
            comparison=(ins.rn,cursor,row['word']);cursor+=4;continue
        if ins.kind=='b':
            cursor+=ins.immediate;continue
        # Any control transfer stops this linear candidate window. Unknown or
        # unsupported writes cannot silently preserve a register identity.
        if ins.kind in ('ret','brk','b','bl','bcond','wcbz','wcbnz','xcbz','xcbnz',
                        'wtbz','wtbnz','xtbz','xtbnz'):
            post['reason']='post_call_control_without_error_test';return
        transferred=transfer_swift_value(state,ins,limits=vl)
        result['accounting']['value_steps']+=1
        if transferred.status!='resolved':
            # An exactly decoded ordinary memory access can lack a qualified
            # frame base. It still has known GPR writes. Forget memory origins
            # rather than invent a slot or discard an untouched error register.
            memory=('xstr','wstr','xldr','wldr','xldr_post','stp','ldp')
            if transferred.reason!='stack_base_unqualified' or ins.kind not in memory:
                post['reason']=transferred.reason;return
            load=ins.kind in ('xldr','wldr','xldr_post','ldp')
            writes=set((ins.rd,ins.rt2) if ins.kind=='ldp' else (ins.rd,)) if load else set()
            writeback=ins.addressing in ('pre','post')
            if writeback and ins.rn!=31:writes.add(ins.rn)
            work(len(state.registers)+len(state.register_epochs)+len(writes)+1)
            epochs=dict(state.register_epochs)
            for register in writes:
                if register!=31:epochs[register]=epochs.get(register,0)+1
            state=replace(state,registers=tuple((r,v) for r,v in state.registers if r not in writes),
                register_epochs=tuple(sorted(epochs.items())),
                stack=state.stack if load else (),stack_epoch=state.stack_epoch+int(not load),
                sp_offset=None if writeback and ins.rn==31 else state.sp_offset,steps=state.steps+1)
        else:state=transferred.state
        observations=[]
        work(len(state.registers)+len(state.stack))
        for reg,val in state.registers:
            if val==seed:observations.append({'register':f'x{reg}','kind':'register_copy','origin':seed.origin})
        for cell in state.stack:
            if cell.value==seed:observations.append({'stack_slot':cell.slot,'epoch':cell.epoch,
                                                   'kind':'stack_slot','origin':seed.origin})
        result['value_facts']['observations'].append({'pc':row['pc'],'origins':observations})
        cursor+=4


def _partition_regions(result,by_pc,success,error,work):
    """Instruction-level may-reach sets; loops are finite graph visits.

    Call continuations remain candidates, so labels never assert execution,
    dominance, termination, or semantic exclusivity.
    """
    edges={}
    for edge in result['cfg']['edges']:
        work();edges.setdefault(int(edge['source_pc'],16),[]).append(edge['target_pc'])
    def reach(entry):
        seen=set();pending=[entry]
        while pending:
            address=pending.pop()
            if address in seen:continue
            work();seen.add(address)
            targets=edges.get(address)
            if targets is None:targets=[hex(address+4)]
            for target in targets:
                if target is not None and int(target,16) in by_pc and int(target,16) not in seen:
                    pending.append(int(target,16))
        return seen
    good,bad=reach(success),reach(error)
    partition={'success_only_pcs':good-bad,'error_only_pcs':bad-good,
               'shared_pcs':good&bad,'unreachable_pcs':set(by_pc)-good-bad}
    result['regions']['partition']={key:[hex(p) for p in sorted(values)] for key,values in partition.items()}
    for row in result['cfg']['returns']:
        address=int(row['pc'],16)
        label='shared' if address in good&bad else ('success' if address in good else ('error' if address in bad else 'unreachable'))
        result['regions']['tails'].append({'pc':row['pc'],'kind':'return','outcome':label})
