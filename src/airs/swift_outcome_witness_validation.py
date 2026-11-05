"""Independent bounded witness checks against an already admitted immutable image.

No builder or producer consistency/choice routine is used as a validation oracle.
The shared instruction decoder and exact declaration grammar are primitives.
"""
import re
import struct
from .swift_outcome_witness_models import (WITNESS_MODEL, VALIDATION_MODEL, PROFILES,
    DEFAULT_WITNESS_LIMITS, bounded_copy, image_identity, source_models)

class _Refusal(Exception):
    def __init__(self, reason, status='declined'):
        self.reason, self.status = reason, status


def validate_outcome_witness(image, function, witness: dict, *, limits=DEFAULT_WITNESS_LIMITS) -> dict:
    result = {'model_version': VALIDATION_MODEL, 'status': 'unresolved', 'details_complete': True,
              'call_return_proven': False, 'source_reconstruction_allowed': False,
              'runtime_branch_proven': False, 'handler_semantics_proven': False,
              'exclusive_entry_proven': False, 'checked_instruction_count': 0, 'work_steps': 0,
              'facts': {}}
    steps = 0; checked = {}; caller_words = 0; symbol_records = 0; source_steps = 0
    def need(ok, reason, status='declined'):
        if not ok: raise _Refusal(reason, status)
    def charge(n=1):
        nonlocal steps
        steps += n
        need(steps <= limits.max_steps and steps+caller_words+symbol_records+source_steps <= limits.max_total_work, 'witness_work_limit', 'unresolved')
    def source_charge():
        nonlocal source_steps
        need(steps+caller_words+symbol_records+source_steps < limits.max_total_work,'witness_total_work_limit','unresolved')
        source_steps += 1
    def addr(value):
        need(type(value) is str and re.fullmatch(r'0x[0-9a-f]{1,16}', value) is not None, 'invalid_address')
        n = int(value, 16); need(value == hex(n) and n % 4 == 0, 'invalid_address'); return n
    def ins(pc):
        charge()
        need(function.start <= pc < function.end and pc % 4 == 0, 'instruction_outside_caller')
        section = next((s for s in image.sections if s.address <= pc and pc + 4 <= s.end), None)
        need(section is not None and section.executable and section.flags & 255 not in (1, 12, 18), 'instruction_not_executable')
        offset = section.file_offset + pc - section.address
        need(0 <= offset <= len(image.data) - 4 and offset + 4 <= image.slice_size, 'instruction_mapping')
        word = struct.unpack_from('<I', image.data, offset)[0]
        checked[pc] = (word, offset)
        need(len(checked) <= limits.max_instructions, 'witness_instruction_limit', 'unresolved')
        from .swift_error_flow import decode_instruction
        try: return decode_instruction(word, pc)
        except Exception as exc:
            from .arm64 import ModelError
            if not isinstance(exc, ModelError): raise
            raise _Refusal('instruction_unmodeled', 'unresolved') from exc
    def records(rows, start, end):
        need(type(rows) is list and len(rows) <= limits.max_instructions and len(rows)*4 == end-start, 'interval_details_incomplete', 'unresolved')
        output=[]
        for i,row in enumerate(rows):
            pc=start+4*i; need(type(row) is dict and row.get('pc') == hex(pc), 'interval_address_mismatch')
            decoded=ins(pc)
            need(row.get('word') == f'0x{decoded.word:08x}', 'instruction_word_mismatch')
            if 'kind' in row: need(row['kind'] == decoded.kind, 'instruction_kind_mismatch')
            output.append(decoded)
        return output
    try:
        bounded_copy(witness, limits)
        need(type(witness) is dict, 'witness_container')
        need(witness.get('model_version') == WITNESS_MODEL and witness.get('validation_model_version') == VALIDATION_MODEL
             and type(witness.get('schema_version')) is int and witness['schema_version'] == 1, 'witness_model')
        profile=witness.get('model_profile');need(profile in PROFILES and witness.get('source_models') == source_models(profile), 'source_models')
        need(witness.get('image') == image_identity(image), 'selected_image_mismatch')
        need(image.architecture == 'arm64' and image.cpu_subtype in (0,1), 'architecture')
        need(function in image.functions and function.boundary_source == 'lc_function_starts'
             and witness.get('caller') == {'start_pc':hex(function.start),'end_pc_exclusive':hex(function.end),'boundary_source':function.boundary_source}, 'caller_identity')
        c=witness['evidence'];need(type(c) is dict, 'call_container')
        need('presentation' not in c, 'unvalidated_presentation')
        # Retained proof flags are assertions with a single permitted value.
        pending=[witness]
        while pending:
            obj=pending.pop()
            if type(obj) is dict:
                for key,value in obj.items():
                    if key.endswith('_proven') or key=='source_reconstruction_allowed':
                        need(value is False,'retained_proof_scope')
                    if type(value) in (dict,list):pending.append(value)
            elif type(obj) is list:pending.extend(obj)

        need(c.get('status') == 'recovered_candidate', 'edge_not_recovered')
        cp=addr(c['call_pc']);tp=addr(c['test_pc']);sp=addr(c['success_pc']);ep=addr(c['error_pc']);target=addr(c['callee_pc'])
        need(c.get('caller_pc') == hex(function.start) and c.get('call_image_offset') == hex(cp-image.preferred_base), 'call_identity')
        need(witness.get('witness_id') == ':'.join((WITNESS_MODEL,image.slice_sha256,hex(function.start),hex(cp))), 'witness_identity')
        call=ins(cp);need(call.kind == 'bl' and c.get('call_word') == f'0x{call.word:08x}' and cp+call.immediate == target, 'call_target_mismatch')
        callee=next((f for f in image.functions if f.start == target and f.boundary_source == 'lc_function_starts'),None)
        need(callee is not None, 'callee_entry')
        # Re-read the symbol table; all entry aliases participate, not display names.
        cursor=32; table=None
        for _ in range(struct.unpack_from('<I',image.data,16)[0]):
            source_charge()
            command,size=struct.unpack_from('<II',image.data,cursor)
            if command==2: table=struct.unpack_from('<IIII',image.data,cursor+8)
            cursor+=size
        need(table is not None,'callee_symbols')
        off,count,strings,strlen=table; found=[]
        need(count <= limits.max_caller_words, 'symbol_scan_budget', 'unresolved')
        for i in range(count):
            need(steps+caller_words+symbol_records+source_steps < limits.max_total_work,'witness_total_work_limit','unresolved')
            symbol_records += 1
            sx,kind,section,desc,pc=struct.unpack_from('<IBBHQ',image.data,off+16*i)
            if kind & 0xe0 or kind & 0x0e != 0x0e or pc != target: continue
            need(len(found)<1,'callee_aliases')
            sec=image.sections[section-1] if 1<=section<=len(image.sections) else None
            need(sec is not None and sec.executable and sec.address<=pc<sec.end and sec.flags & 255 not in (1,12,18),'callee_section')
            need(kind==15 and not desc & 0x300,'callee_visibility')
            end=image.data.find(b'\0',strings+sx,min(strings+strlen,strings+sx+513))
            need(end>=0,'callee_symbol_extent');found.append(image.data[strings+sx:end].decode('ascii'))
        need(len(found)==1,'callee_symbols')
        from .swift_throwing_declarations import parse_throwing_declaration
        declaration=parse_throwing_declaration(found[0],allow_methods=profile=='methods')
        need(declaration is not None,'callee_declaration')
        expected={'symbol':found[0],'image_offset':hex(target-image.preferred_base),**declaration.record()}
        retained=c['callee'];need(type(retained) is dict and all(type(retained.get(k)) is type(v) and retained.get(k)==v for k,v in expected.items()),'callee_declaration_mismatch')
        if declaration.callable_kind == 'struct_instance_method':
            from .swift_nominal_context import admit_struct_context
            context=admit_struct_context(image,declaration,charge=source_charge)
            need(context.get('status')=='admitted_struct_context' and declaration.parameter_types == ('Swift.Int',) and declaration.result_type == 'Swift.Int','method_context')
            need(c.get('method_context') == context, 'method_context_mismatch')
        result['facts']['call']='checked_against_image'
        need(cp < tp <= cp+32,'postcall_window')
        window=records(c['window'],cp+4,tp+4);aliases={21};cmp=None;literal_prefix=False
        for d in window[:-1]:
            if d.word & 0xfffffc1f == 0xf100001f:
                need(d.rn in aliases and d.address==tp-4,'error_compare');cmp=d;continue
            need(cmp is None,'comparison_not_adjacent')
            if d.kind=='nop': continue
            need(d.kind in ('mov','movz','movn','xmovk','wmovz','wmovn','wmovk','wmov'),'postcall_unmodeled','unresolved')
            if d.kind not in ('mov','nop'):literal_prefix=True
            if d.rd !=31:
                if d.kind=='mov' and d.rn in aliases: aliases.add(d.rd)
                else: aliases.discard(d.rd)
        branch=window[-1]
        if cmp is not None:
            need(branch.kind=='bcond' and branch.addressing in ('0','1') and c.get('test_kind')=='cmp_zero_bcond'
                 and c.get('comparison_pc')==hex(tp-4) and c.get('test_condition')==('eq' if branch.addressing=='0' else 'ne'),'test_encoding')
            reg=cmp.rn;zero=branch.addressing=='0'
        else:
            need(not literal_prefix,'literal_prefix_requires_compare')
            need(branch.kind in ('xcbz','xcbnz') and 'test_kind' not in c,'test_encoding');reg=branch.rn;zero=branch.kind=='xcbz'
        need(reg in aliases and c.get('tested_register')==f'x{reg}','error_register')
        bt=tp+branch.immediate
        need(bt>tp+4 and function.start<=bt<function.end,'successor_bounds')
        need((sp,ep)==((bt,tp+4) if zero else (tp+4,bt)),'branch_polarity_mismatch')
        result['facts']['test']='checked_against_image'
        region=c['error_region'];need(region.get('status')=='structural_region_candidate','region_missing','unresolved')
        lo=addr(region['start_pc']);hi=addr(region['end_pc_exclusive']);join=addr(region['join_pc'])
        need(lo==ep and 0<hi-lo<=64,'error_interval')
        errors=records(region['instructions'],lo,hi)
        need(region.get('call_return_proven') is False and region.get('join_reachability_proven') is False,'region_proof')
        shared=region.get('shared_epilogue');need(type(shared) is dict,'shared_tail_required','unresolved')
        success=region['success_interval'];sl=addr(success['start_pc']);sh=addr(success['end_pc_exclusive'])
        need(sl==sp and 0<sh-sl<=32,'success_interval')
        successes=records(success['instructions'],sl,sh)
        forward=sp<ep
        need((sh==ep and hi==join) if forward else (hi==sp and sh==join),'interval_geometry')
        need((region.get('layout') == 'success_fallthrough_error_forward' if forward else 'layout' not in region), 'layout_direction')
        skipping = successes if forward else errors
        need(skipping[-1].kind == 'b' and skipping[-1].address + skipping[-1].immediate == join, 'skipping_arm_join_branch')
        te=addr(shared['end_pc_exclusive']);need(shared.get('start_pc')==hex(join) and 0<te-join<=32 and shared.get('restore_state_proven') is False,'tail_geometry')
        tail=records(shared['instructions'],join,te)
        need(tail[-1].word==0xd65f03c0,'tail_return')
        for d in tail[:-1]:
            allowed=d.kind=='nop' or (d.kind=='ldp' and d.rn==31 and d.addressing=='offset' and d.immediate>=0 and 19<=d.rd<=30 and 19<=d.rt2<=30) or (d.kind=='add' and d.rd==d.rn==31 and 0<d.immediate<=4096 and d.immediate%16==0)
            need(allowed,'tail_shape_unqualified','unresolved')
        # Full caller direct-entry inspection. Does not establish external/indirect exclusivity.
        need(function.size%4==0 and function.size//4<=limits.max_caller_words,'caller_scan_budget','unresolved')
        from .swift_error_flow import decode_instruction
        unknown=0;conflicts=[]
        protected=[(lo,hi),(sl,sh),(join,te),(cp+4,tp+4)]
        allowed_sources={(tp,bt)}
        for d in errors+successes:
            if d.kind=='b' and d.address+4 in (hi,sh) and d.address+d.immediate==join: allowed_sources.add((d.address,join))
        for pc in range(function.start,function.end,4):
            # Caller scan is separately bounded; does not retain another caller-sized object graph.
            need(steps+caller_words+symbol_records+source_steps < limits.max_total_work,'witness_total_work_limit','unresolved')
            caller_words += 1
            raw=image.bytes_at(pc,4);word=struct.unpack('<I',raw)[0]
            try: d=decode_instruction(word,pc)
            except Exception as exc:
                from .arm64 import ModelError
                if not isinstance(exc,ModelError): raise
                unknown+=1;continue
            if d.kind in ('b','bl','bcond','xcbz','xcbnz','wcbz','wcbnz','xtbz','xtbnz','wtbz','wtbnz'):
                dest=pc+d.immediate
                need(0<=dest<1<<64 and dest%4==0,'caller_direct_target_out_of_range','unresolved')
                for a,b in protected:
                    if a<=dest<b and not a<=pc<b and (pc,dest) not in allowed_sources:
                        conflicts.append((pc,dest));break
        need(not conflicts,'unexpected_direct_entries','blocked')
        need(not unknown,'caller_scan_unclassified','unresolved')
        ledger=region.get('incoming_validation',{})
        need(ledger.get('caller_scan_complete') is True and ledger.get('scanned_word_count')==function.size//4
             and ledger.get('status')=='no_unexpected_direct_entries' and ledger.get('unexpected_entry_count')==0
             and ledger.get('unclassified_word_count')==0 and ledger.get('entry_details_complete') is True
             and ledger.get('unclassified_details_complete') is True,'caller_ledger_incomplete','unresolved')
        need(region.get('opaque_call_count')==sum(d.kind=='bl' for d in errors),'opaque_call_count')
        pending=[c]
        while pending:
            obj=pending.pop()
            if type(obj) is dict:
                if 'word' in obj and 'pc' in obj:
                    d=ins(addr(obj['pc']))
                    for key in ('target_pc','call_target_pc'):
                        if key in obj:
                            need(d.kind in ('b','bl') and obj[key]==hex(d.address+d.immediate),'retained_target_mismatch')
                    if 'semantics' in obj:need(d.kind=='bl' and obj['semantics']=='opaque_call','opaque_semantics')
                if 'scanned_word_count' in obj:
                    need(obj.get('status')=='no_unexpected_direct_entries' and obj.get('caller_scan_complete') is True
                         and obj.get('scanned_word_count')==function.size//4 and obj.get('unexpected_entry_count')==0
                         and obj.get('unclassified_word_count')==0 and obj.get('unexpected_entries')==[]
                         and obj.get('unclassified_words')==[] and obj.get('entry_details_complete') is True
                         and obj.get('unclassified_details_complete') is True,'retained_ledger_mismatch')
                pending.extend(v for v in obj.values() if type(v) in (dict,list))
            elif type(obj) is list:pending.extend(obj)
        result['facts']['intervals']='checked_against_image'
        # Replay scalar values independently. Symbols for call-result dependencies are tuples.
        def replay(ds,values,arm_end):
            values=dict(values)
            for d in ds:
                charge()
                if d.kind=='nop':continue
                if d.kind=='b':
                    need(d.address+4==arm_end and d.address+d.immediate==join,'arm_branch');continue
                if d.kind=='bl': values={};continue
                need(d.kind in ('mov','wmov','movz','movn','wmovz','wmovn','xmovk','wmovk'),'value_transfer_unqualified','unresolved')
                if d.rd==31:continue
                if d.kind.endswith('movz') or d.kind.endswith('movn'):
                    width=32 if d.kind.startswith('w') else 64
                    values[d.rd]=(d.immediate if d.kind.endswith('movz') else ~d.immediate)&((1<<width)-1)
                elif d.kind in ('xmovk','wmovk'):
                    v=values.get(d.rd)
                    if type(v) is int:
                        shift=int(d.addressing);values[d.rd]=((v & ~(65535<<shift)) | (d.immediate<<shift)) & ((1<<(32 if d.kind=='wmovk' else 64))-1)
                    else:values.pop(d.rd,None)
                else:
                    v=0 if d.rn==31 else values.get(d.rn)
                    if d.kind=='wmov':v=v & 0xffffffff if type(v) is int else None
                    if v is None:values.pop(d.rd,None)
                    else:values[d.rd]=v
            return values
        initial=replay(window[:-2] if cmp is not None else window[:-1],{0:('call_result',)},tp)
        ev=replay(errors,{},hi).get(0);sv=replay(successes,initial,sh).get(0)
        need(type(ev) is int and (type(sv) is int or sv==('call_result',)),'outcome_values_unresolved','unresolved')
        def outcome(path,value):
            fact=c['error_constant' if path=='error' else 'success_constant' if type(value)is int else 'success_result']
            need(all(fact.get(k) is False for k in ('source_reconstruction_allowed','runtime_value_proven','exclusive_path_proven','caller_return_type_proven')), 'value_proof_scope')
            need(fact.get('call_pc')==hex(cp) and fact.get(path+'_pc')==hex(ep if path=='error' else sp)
                 and fact.get('return_pc')==hex(tail[-1].address) and fact.get('register')=='x0','value_binding')
            if type(value)is int:
                need(fact.get('status')=='constant_register_candidate' and fact.get('constant_bits')==f'0x{value:016x}' and type(fact.get('bit_width')) is int and fact['bit_width']==64,'constant_mismatch')
                return {'kind':'constant_bits','bit_width':64,'constant_bits':f'0x{value:016x}'}
            need(fact.get('status') in ('preserved_register_candidate','copied_register_candidate') and retained.get('result')=='Swift.Int','result_mismatch')
            return {'kind':'call_result','register':'x0','candidate_status':fact['status']}
        sd=outcome('success',sv);ed=outcome('error',ev);choice=c['return_choice']
        need(choice.get('status')=='structural_choice_candidate' and choice.get('call_pc')==hex(cp)
             and choice.get('return_pc')==hex(tail[-1].address) and choice.get('success')==sd and choice.get('error')==ed,'choice_mismatch')
        condition={'test_pc':hex(tp),'register':f'x{reg}','error_when':'nonzero'}
        if cmp is not None:condition.update(comparison_pc=hex(tp-4),test_kind='cmp_zero_bcond',test_condition='eq' if zero else 'ne')
        need(choice.get('condition')==condition,'choice_condition')
        need(witness.get('runtime_branch_proven') is False,'proof_scope')
        for obj in (witness,choice):
            for key in ('source_reconstruction_allowed','call_return_proven','handler_semantics_proven'):
                need(obj.get(key) is False,'proof_scope')
        # Every retained fact's raw evidence is checked, including unselected facts.
        selected = {'success_constant': type(sv) is int, 'success_result': sv == ('call_result',), 'error_constant': True}
        for key in ('success_constant','success_result','error_constant'):
            fact=c.get(key,{})
            need(type(fact) is dict,'outcome_container')
            need(all(fact.get(k) is False for k in ('source_reconstruction_allowed','runtime_value_proven','exclusive_path_proven','caller_return_type_proven')), 'value_proof_scope')
            if fact.get('status') in ('constant_register_candidate','preserved_register_candidate','copied_register_candidate','adjusted_register_candidate'):
                need(selected[key], 'conflicting_success_values')
                need(all(fact.get(k) is False for k in ('source_reconstruction_allowed','runtime_value_proven','exclusive_path_proven','caller_return_type_proven')), 'value_proof_scope')
            path='error' if key=='error_constant' else 'success'
            expected_arm=errors if path=='error' else successes
            valid={d.address:d for d in expected_arm+tail+window}
            rows=fact.get('instructions',[])
            need(type(rows) is list and len(rows)<=64,'outcome_details','unresolved')
            if selected[key]:need(len(rows)>0,'outcome_details','unresolved')
            seen=[]
            for row in rows:
                pc=addr(row['pc']);need(pc in valid,'outcome_address')
                d=ins(pc);need(row.get('word')==f'0x{d.word:08x}','outcome_word')
                if 'kind' in row:need(row['kind']==d.kind,'outcome_kind')
                seen.append(pc)
            if selected[key]:
                need(all(d.address in seen for d in expected_arm+tail),'outcome_details','unresolved')
        need(choice.get('runtime_value_proven') is False and choice.get('exclusive_path_proven') is False
             and choice.get('caller_return_type_proven') is False,'choice_proof_scope')
        need(choice.get('same_constant_bits') == (sv==ev if type(sv)is int else None), 'choice_equality')
        result['facts']['values']='independently_replayed'
        nodes=[{'id':label,'pc':c[key]} for key,label in (('call_pc','call'),('test_pc','test'),('success_pc','success'),('error_pc','error'))]+[{'id':'join','pc':hex(join)}]
        edges=[{'from':a,'to':b,'provenance_pc':hex(tp) if a=='test' else hex(errors[-1].address) if a=='error' else hex(successes[-1].address) if a=='success' else hex(cp),'relationship':'recorded_structural'} for a,b in [('call','test'),('test','success'),('test','error'),('error','join'),('success','join')]]
        need(witness.get('graph')=={'nodes':nodes,'edges':edges} and len(nodes)<=limits.max_nodes and len(edges)<=limits.max_edges,'graph_mismatch')
        result.update(status='eligible_structural_only',reason='bounded_facts_checked')
    except _Refusal as error:
        result.update(status=error.status,reason=error.reason)
        if 'limit' in error.reason or 'budget' in error.reason:result['details_complete']=False
    except (AttributeError,KeyError,TypeError,ValueError,IndexError,struct.error,UnicodeError) as error:
        result.update(status='unresolved',reason='malformed_or_incomplete_evidence')
        if 'limit' in str(error):result.update(reason=str(error),details_complete=False)
    result.update(checked_instruction_count=len(checked),work_steps=steps + caller_words + symbol_records + source_steps, source_steps=source_steps, local_steps=steps, caller_words=caller_words, symbol_records=symbol_records)
    result['instruction_mappings']=[{'pc':hex(pc),'word':f'0x{word:08x}','slice_offset':offset,
        'container_offset':image.slice_offset+offset} for pc,(word,offset) in sorted(checked.items())]
    return result
