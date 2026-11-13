"""Bounded broad coordinator; candidate construction never grants proof."""
from collections import Counter
from pathlib import Path
from typing import NamedTuple
import json
from .engine import resolve_input
from .macho import parse_macho
from .types import InputError, Limits, MachOImage
from .swift_broad_profiles import (BROAD_MODEL, BROAD_PROFILE, BROAD_LARGE_PROFILE, BROAD_LARGE_MODEL,
                                   BROAD_EXTENDED_PROFILE, BROAD_EXTENDED_MODEL,
                                   BROAD_EXTENDED_V2_PROFILE, BROAD_EXTENDED_V2_MODEL,
                                   BROAD_EXTENDED_V3_PROFILE, BROAD_EXTENDED_V3_MODEL,
                                   BROAD_EXTENDED_V4_PROFILE, BROAD_EXTENDED_V4_MODEL,
                                   BROAD_IMPORTS_PROFILE, BROAD_IMPORTS_MODEL)
from .swift_broad_profiles import BROAD_IMPORTS_GOT_PROFILE, BROAD_IMPORTS_GOT_MODEL
from .swift_caller_error_test import caller_error_test_from_bytes, _direct_entry_indices
from .swift_indirect_facts import indirect_target_facts, make_symbol_lookup, ADMITTED_REASON, SITE_WORK
from .analysis_models import SWIFT_INDIRECT_TARGET_SHAPE_MODEL, SWIFT_VALUE_WITNESS_ADMISSION_MODEL
from .macho_stubs import STUB_MODEL, attribute_import_stubs
from .macho_got import attribute_got_bindings, got_report_fields, got_callsite_admission
from .swift_callsite_admission import (CallsiteLimits, CallsiteSessionError,
    create_callsite_session, admit_callsite_capability)
from .swift_declaration_profiles import parse_broad_declaration
from .swift_import_declarations import parse_import_declaration
from . import swift_broad_accounting as accounting
from .swift_import_effect_admission import (SymbolResolver, NOT_SWIFT, caller_relation, row_treatment,
    effect_admission)
from .swift_abi_profiles import (admit_swift_abi, ABICallsiteQualification,
    STABLE_ARM64_SWIFT6)
from .swift_outcome_witness_v2 import build_broad_swift_witness
from .swift_outcome_validator_v2 import (validate_broad_swift_witness,
    create_independent_swift_image_ledger)
from .swift_outcome_witness_v2_models import BroadWitnessLimits

BROAD_LIMITS=Limits(max_file_bytes=8*1024*1024,max_functions=8192,
    max_instructions_per_function=4096,max_total_instructions=262144,
    max_observations_per_function=256,max_total_evidence=4096)
from dataclasses import replace, asdict
from types import MappingProxyType
LARGE_BROAD_LIMITS=replace(BROAD_LIMITS,max_functions=9216)
EXTENDED_BROAD_LIMITS=replace(LARGE_BROAD_LIMITS,max_total_instructions=2097152,
                              max_instructions_per_function=262144,max_total_evidence=8192)
IMPORTS_BROAD_LIMITS=EXTENDED_BROAD_LIMITS
PROFILE_LIMITS=MappingProxyType({BROAD_PROFILE:BROAD_LIMITS, BROAD_LARGE_PROFILE:LARGE_BROAD_LIMITS,
                                BROAD_EXTENDED_PROFILE:EXTENDED_BROAD_LIMITS,
                                BROAD_EXTENDED_V2_PROFILE:EXTENDED_BROAD_LIMITS,
                                BROAD_EXTENDED_V3_PROFILE:EXTENDED_BROAD_LIMITS,
                                BROAD_EXTENDED_V4_PROFILE:EXTENDED_BROAD_LIMITS,
                                BROAD_IMPORTS_PROFILE:IMPORTS_BROAD_LIMITS,
                                BROAD_IMPORTS_GOT_PROFILE:IMPORTS_BROAD_LIMITS})
PROFILE_MODELS=MappingProxyType({BROAD_PROFILE:BROAD_MODEL, BROAD_LARGE_PROFILE:BROAD_LARGE_MODEL,
                                BROAD_EXTENDED_PROFILE:BROAD_EXTENDED_MODEL,
                                BROAD_EXTENDED_V2_PROFILE:BROAD_EXTENDED_V2_MODEL,
                                BROAD_EXTENDED_V3_PROFILE:BROAD_EXTENDED_V3_MODEL,
                                BROAD_EXTENDED_V4_PROFILE:BROAD_EXTENDED_V4_MODEL,
                                BROAD_IMPORTS_PROFILE:BROAD_IMPORTS_MODEL,
                                BROAD_IMPORTS_GOT_PROFILE:BROAD_IMPORTS_GOT_MODEL})
CALLER_FACT_PROFILES=(BROAD_EXTENDED_V2_PROFILE,BROAD_EXTENDED_V3_PROFILE,BROAD_EXTENDED_V4_PROFILE)
IMPORT_CALLSITE_MODEL='swift-broad-import-callsite-v1'
IMPORT_REASON='imported_callee_abi_unqualified'
REPORT_BYTES=16*1024*1024
AGGREGATE_WORK=512*1024*1024
CALLSITE_WORK_RESERVATION=2_000_000
ABI_WORK_RESERVATION=2_032_768


def _public(value):
    # Private local custody records never become serialized capabilities.
    if type(value) is dict:return {k:_public(v) for k,v in value.items()
                                  if k!='binding' and not k.endswith('_binding')}
    if type(value) in (tuple,list):return [_public(v) for v in value]
    return value


def _abi(image,record,caller_start,capability):
    from . import swift_abi_profiles as profiles
    parsed=parse_broad_declaration(record['symbol'])
    if not parsed.supported:return {'status':'unresolved','reason':'syntax_unqualified','work_steps':32768}
    if any(o.slice_sha256==image.slice_sha256 and o.symbol==parsed.identity.symbol.lstrip('_')
           for o in profiles.LOWERING_QUALIFICATIONS.values()):
        result=admit_swift_abi(image,parsed.identity)
        result['work_steps']=32768
        return result
    request=ABICallsiteQualification(STABLE_ARM64_SWIFT6.identifier,record['call_pc'],
        caller_start,record['callee_pc'],callsite_capability=capability)
    return admit_swift_abi(image,parsed.identity,qualification=request)


def _import_admission(function,pc,word,stub,parsed):
    # Attribution and declaration syntax only: no ABI, witness or runtime claim.
    provenance=stub.record()['provenance']
    provenance.update(stub_model=STUB_MODEL,stub_section=stub.section,stub_index=stub.stub_index,
                      symbol_index=stub.symbol_index,pointer_address=stub.pointer_address,
                      pointer_section=stub.pointer_section)
    return dict(model_version=IMPORT_CALLSITE_MODEL,status='unresolved',reason=IMPORT_REASON,
        call_kind='bl' if word&0x80000000 else 'b',call_pc=pc,caller_start=function.start,
        callee_stub_pc=stub.address,symbol=stub.symbol,library_ordinal=stub.library_ordinal,
        declaration=dict(status='syntax_admitted' if parsed.supported else 'syntax_unresolved',
            identity=asdict(parsed.identity) if parsed.supported else None,
            reason=None if parsed.supported else parsed.unsupported_reason.value),
        import_provenance=provenance,details_complete=True,call_return_proven=False,
        syntactic_call_target_admitted=False,import_attribution_admitted=True,
        work_steps=16+len(stub.symbol))


def _got_site(got,function,pc,report,declarations,*,keep_nonthrowing=False,declines=None):
    # None keeps the existing path; 'skip' leaves calls[]; a tuple is a selected GOT call.
    counts=report['got_counts'];counts['blr_instructions']+=1
    found=got.classify(function,pc)
    if found is None:return None
    counts['got_candidates']+=1;kind,call=found
    if kind=='declined':
        counts['declined_got_calls']+=1;reasons=report['got_decline_counts']
        reasons[call]=reasons.get(call,0)+1
        if declines is not None:declines.append(call)
        return None
    counts['attributed_got_calls']+=1;symbol=call.binding.symbol
    if not symbol.lstrip('_').startswith('$s'):
        counts['non_swift_got_calls']+=1;return 'skip'
    if call.binding.slot_address not in declarations:
        declarations[call.binding.slot_address]=parse_import_declaration(symbol)
    parsed=declarations[call.binding.slot_address]
    if parsed.supported and not parsed.identity.throws:
        if not keep_nonthrowing:
            counts['non_throwing_swift_got_calls']+=1;return 'skip'
    return (call,parsed)


def _got_admission(function,pc,call,parsed):
    declaration=dict(status='syntax_admitted' if parsed.supported else 'syntax_unresolved',
        identity=asdict(parsed.identity) if parsed.supported else None,
        reason=None if parsed.supported else parsed.unsupported_reason.value)
    return got_callsite_admission(function,pc,call,declaration,IMPORT_REASON)


def _import_admission_v4(function,pc,word,stub,resolution,treatment):
    # Same attribution record as the first generation; the declaration is the compact v2 record and the reason is
    # the one the licence gives. No ABI, witness or runtime claim.
    provenance=stub.record()['provenance']
    provenance.update(stub_model=STUB_MODEL,stub_section=stub.section,stub_index=stub.stub_index,
                      symbol_index=stub.symbol_index,pointer_address=stub.pointer_address,
                      pointer_section=stub.pointer_section)
    return dict(model_version=IMPORT_CALLSITE_MODEL,status=treatment.status,reason=treatment.reason,
        call_kind='bl' if word&0x80000000 else 'b',call_pc=pc,caller_start=function.start,
        callee_stub_pc=stub.address,symbol=stub.symbol,library_ordinal=stub.library_ordinal,
        declaration=dict(resolution.declaration),import_provenance=provenance,details_complete=True,
        call_return_proven=False,syntactic_call_target_admitted=False,import_attribution_admitted=True,
        work_steps=16+len(stub.symbol))


def _got_site_v4(got,function,pc,report,resolver,declines):
    # None keeps the existing indirect path; otherwise (call, resolution) for an attributed GOT call.
    counts=report['got_counts'];counts['blr_instructions']+=1
    found=got.classify(function,pc)
    if found is None:return None
    counts['got_candidates']+=1;kind,call=found
    if kind=='declined':
        counts['declined_got_calls']+=1;reasons=report['got_decline_counts']
        reasons[call]=reasons.get(call,0)+1
        declines.append(call)
        return None
    counts['attributed_got_calls']+=1
    resolution=resolver.resolve(call.binding.symbol)
    if not resolution.is_swift:counts['non_swift_got_calls']+=1
    return call,resolution


class _WitnessIdentity(NamedTuple):
    entity: str


class _WitnessDeclaration(NamedTuple):
    identity: _WitnessIdentity|None
    reason: str


def _witness_parse(resolver):
    # The value-witness check reads the entity and the reason of a declaration. Under v4 it reads them from the
    # resolver's cache, so a symbol is never parsed twice in one run. A symbol the resolver does not parse
    # (not `$s`) is what the grammar itself declines: no identity and reason invalid_input.
    def parse(symbol):
        declaration=resolver.resolve(symbol).declaration
        if declaration is None:return _WitnessDeclaration(None,'invalid_input')
        entity=declaration['entity']
        return _WitnessDeclaration(_WitnessIdentity(entity) if entity is not None else None,declaration['reason'] or '')
    return parse


def recover_swift_broad_flow(image: MachOImage, limits: Limits|None=None,
                            *, witness_limits=BroadWitnessLimits(), profile=BROAD_PROFILE)->dict:
    if profile not in PROFILE_LIMITS:
        raise InputError('swift_broad_profile','Unsupported broad profile')
    ceiling = PROFILE_LIMITS[profile]
    if limits is None: limits=ceiling
    if any(getattr(limits, name) > getattr(ceiling, name) for name in limits.__dataclass_fields__):
        raise InputError('swift_broad_limit','Requested limits exceed profile bounds')
    if not isinstance(image,MachOImage) or not image.has_valid_admission():
        raise InputError('swift_broad_admission','Broad flow requires parser-admitted immutable bytes')
    if image.architecture!='arm64' or image.cpu_subtype not in (0,1):
        raise InputError('swift_broad_architecture','Broad flow requires ordinary ARM64')
    if len(image.data)>limits.max_file_bytes or len(image.functions)>limits.max_functions:
        raise InputError('swift_broad_limit','Image exceeds broad profile bounds')
    functions={f.start:f for f in image.functions}
    if len(functions)!=len(image.functions):
        raise InputError('swift_broad_boundaries','Function entries must be unique')
    report=dict(model_version=PROFILE_MODELS[profile],profile=profile,
        witness_model_version='swift-outcome-witness-v2',validation_model_version='swift-outcome-validation-v2',
        identity=dict(container_sha256=image.container_sha256,slice_sha256=image.slice_sha256,
            architecture=image.architecture,cpu_subtype=image.cpu_subtype,
            uuid=image.uuid,preferred_base=hex(image.preferred_base),
            slice_index=image.slice_index,container_slice_count=image.container_slice_count,
            slice_offset=hex(image.slice_offset),slice_size=hex(image.slice_size)),
        word_scan_complete=True,call_details_complete=True,outcome_witnesses_complete=True,
        observed_call_instructions=0,selected_call_candidates=0,omitted_calls=0,
        scanned_words=0,analysis_work=0,calls=[],status_counts={},reason_counts={},research_only=True,
        call_return_proven=False,runtime_reachability_proven=False,
        limitations=['structural_only','no_source_or_handler_semantics',
            'unsupported_abi_and_dispatch_remain_unresolved','recorded_checks_are_historical_when_saved'])
    call_limits=CallsiteLimits(max_work=CALLSITE_WORK_RESERVATION)
    try:session=create_callsite_session(image,limits=call_limits)
    except CallsiteSessionError as error:
        raise InputError('swift_broad_metadata_admission',str(error)) from error
    report['analysis_work']=session.initial_work_steps
    validation_ledger=create_independent_swift_image_ledger(image)
    report['analysis_work']+=validation_ledger.initial_work_steps
    if validation_ledger.status!='ready':
        raise InputError('swift_broad_independent_metadata',validation_ledger.reason or 'Independent metadata admission incomplete')
    caller_facts=profile in CALLER_FACT_PROFILES
    indirect_facts=profile in (BROAD_EXTENDED_V3_PROFILE,BROAD_EXTENDED_V4_PROFILE)
    v4=profile==BROAD_EXTENDED_V4_PROFILE
    shapes=Counter();caller_declines=Counter()
    # Reserve one direct-target pass plus at most twelve fact words per scanned
    # site before ordinary candidate work can consume the aggregate ceiling.
    caller_work_remaining=13*limits.max_total_instructions if caller_facts else 0
    if caller_facts:
        report.update(caller_error_test_counts={},caller_error_test_decline_counts={})
        report['limitations']+=['caller_error_test_does_not_claim_callee_behaviour']
    shape_counts=Counter();admission_counts=Counter(admitted=0,refused=0);refusal_conditions=Counter()
    if indirect_facts:
        report.update(indirect_target_shape_model=SWIFT_INDIRECT_TARGET_SHAPE_MODEL,
                      value_witness_admission_model=SWIFT_VALUE_WITNESS_ADMISSION_MODEL,
                      indirect_target_shape_counts={},value_witness_admission_counts={},
                      value_witness_refusal_condition_counts={})
        report['limitations']+=['indirect_target_shape_does_not_claim_callee_behaviour',
                                'value_witness_admission_by_abi_with_recorded_provenance']
    stubs=None
    if profile in (BROAD_IMPORTS_PROFILE,BROAD_IMPORTS_GOT_PROFILE)+CALLER_FACT_PROFILES:
        stubs=attribute_import_stubs(image)
        report['analysis_work']+=stubs.work
        report['limitations'].append('imported_callees_attribution_only')
        import_counts=dict(stubs.counts(),selected_import_calls=0,non_throwing_swift_import_calls=0,
                           non_swift_import_calls=0,declined_stub_calls=0)
        report.update(import_stub_model=STUB_MODEL,import_stubs_complete=stubs.complete,
                      import_stub_reason=stubs.reason,import_stub_counts=import_counts)
        if not stubs.complete:report['call_details_complete']=False
        declarations={}
    got=None
    if profile in (BROAD_IMPORTS_GOT_PROFILE,)+CALLER_FACT_PROFILES:
        got=attribute_got_bindings(image);got_declarations={}
        report['analysis_work']+=got.work;report.update(got_report_fields(got))
        report['limitations']+=['got_callees_attribution_only','got_window_entry_screen_syntactic']
        if not got.complete:report['call_details_complete']=False
    symbol_lookup=make_symbol_lookup(functions,stubs) if indirect_facts else None
    remaining=limits.max_total_instructions;budget=max(0,min(REPORT_BYTES,witness_limits.max_aggregate_bytes)-65536)
    if v4:
        # One shared declaration cache, the four omission causes, the unselected partition and the import table.
        # The table's byte reserve leaves the row budget, so the table cannot turn a success into the final failure.
        resolver=SymbolResolver();parse_charged=0;witness_parse=_witness_parse(resolver)
        partition=accounting.UnselectedPartition();table=accounting.ImportCallTable()
        causes=dict.fromkeys(accounting.CAUSES,0);kinds=dict.fromkeys(accounting.KINDS,0)
        budget=max(0,budget-accounting.IMPORT_TABLE_BYTE_RESERVE);row_budget=budget
        def charge_parses():
            # Parse work is charged once per distinct Swift symbol, when the resolver first parses it.
            nonlocal parse_charged
            report['analysis_work']+=resolver.work_steps-parse_charged;parse_charged=resolver.work_steps
    statuses=Counter();reasons=Counter()
    def omit(cause):
        # One omitted candidate: the legacy counter, and under v4 its one cause, its kind and its table outcome.
        report['omitted_calls']+=1;report['call_details_complete']=False
        report['outcome_witnesses_complete']=False
        if v4:
            causes[cause]+=1;kinds[kind]+=1
            if pending is not None:table.record(*pending[:4],'omitted',pending[4])
    for function in image.functions:
        if function.boundary_source!='lc_function_starts' or function.size<=0 or function.start%4 or function.size%4:
            report['word_scan_complete']=False
            if not v4:reasons['excluded_boundary']+=1
            continue
        count=min(function.size//4,limits.max_instructions_per_function,remaining)
        if count*4!=function.size:report['word_scan_complete']=False
        retained=0
        caller_data=None;caller_entries=None
        def caller_fact(call_index, *, tail=False):
            nonlocal caller_data,caller_entries,caller_work_remaining
            if caller_data is None:
                caller_data=image.bytes_at(function.start,count*4)
                report['analysis_work']+=count;caller_work_remaining-=count
                if count*4==function.size:
                    caller_entries=_direct_entry_indices(caller_data)
            report['analysis_work']+=12;caller_work_remaining-=12
            # A tail branch has no local return point; retain its pre-call fact
            # without interpreting the following bytes as a returned error test.
            data=memoryview(caller_data)[:call_index*4+4] if tail else caller_data
            return caller_error_test_from_bytes(data,function,call_index*4,caller_entries)
        for index in range(count):
            pc=function.start+index*4;remaining-=1;report['scanned_words']+=1
            word=int.from_bytes(image.bytes_at(pc,4),'little')
            direct=word&0x7c000000==0x14000000
            indirect=(word&0xfffffc1f in (0xd63f0000,0xd61f0000)
                      or word&0xfe000000==0xd6000000 and bool(word&0x00200000))
            if not (direct or indirect):continue
            target=None
            if direct:
                d=word&0x3ffffff
                if d&0x2000000:d-=0x4000000
                target=pc+d*4
                if not word&0x80000000 and function.start<=target<function.end:continue
            report['observed_call_instructions']+=1
            if v4:partition.observe()
            got_selected=None;fact=None;disagreement=False;base_declined=False;pending=None
            if got is not None and word&0xfffffc1f==0xd63f0000 and v4:
                declines=[]
                site=_got_site_v4(got,function,pc,report,resolver,declines);charge_parses()
                base_declined='got_base_not_adrp' in declines
                if site is not None:
                    call,resolution=site;symbol=call.binding.symbol
                    if not resolution.is_swift:
                        table.record(symbol,'got',NOT_SWIFT,None,'not_swift');partition.classify('non_swift_import');continue
                    fact=caller_fact(index)
                    relation=caller_relation(resolution.licence_class,fact['shape'],'bl')
                    treatment=row_treatment(resolution.licence_class,relation)
                    if not treatment.retained:
                        report['got_counts']['non_throwing_swift_got_calls']+=1
                        table.record(symbol,'got',resolution.decision,resolution.reason,'skipped_non_throwing',fact['shape'])
                        partition.classify('skipped_non_throwing');continue
                    got_selected=(call,resolution,relation,treatment)
                    pending=(symbol,'got',resolution.decision,resolution.reason,fact['shape'])
            elif got is not None and word&0xfffffc1f==0xd63f0000:
                declines=[]
                got_selected=_got_site(got,function,pc,report,got_declarations,keep_nonthrowing=caller_facts,declines=declines)
                base_declined='got_base_not_adrp' in declines
                if got_selected=='skip':continue
                if caller_facts and got_selected is not None:
                    fact=caller_fact(index)
                    parsed=got_selected[1]
                    if parsed.supported and not parsed.identity.throws:
                        if fact['shape']!='swifterror_idiom':
                            report['got_counts']['non_throwing_swift_got_calls']+=1;continue
                        disagreement=True
            callee=functions.get(target)
            imported=None
            if stubs is not None and direct and callee is None:
                found=stubs.lookup(target)
                if found is not None:
                    kind,stub=found
                    if kind=='declined':
                        import_counts['declined_stub_calls']+=1
                        if v4:partition.classify('declined_stub')
                        continue
                    if v4:
                        resolution=resolver.resolve(stub.symbol);charge_parses()
                        if not resolution.is_swift:
                            import_counts['non_swift_import_calls']+=1
                            table.record(stub.symbol,'stub',NOT_SWIFT,None,'not_swift');partition.classify('non_swift_import');continue
                        tail=not word&0x80000000
                        fact=caller_fact(index,tail=tail)
                        relation=caller_relation(resolution.licence_class,fact['shape'],'b' if tail else 'bl')
                        treatment=row_treatment(resolution.licence_class,relation)
                        if not treatment.retained:
                            import_counts['non_throwing_swift_import_calls']+=1
                            table.record(stub.symbol,'stub',resolution.decision,resolution.reason,'skipped_non_throwing',fact['shape'])
                            partition.classify('skipped_non_throwing');continue
                        imported=(stub,resolution,relation,treatment)
                        pending=(stub.symbol,'stub',resolution.decision,resolution.reason,fact['shape'])
                    else:
                        if not stub.symbol.lstrip('_').startswith('$s'):
                            import_counts['non_swift_import_calls']+=1;continue
                        if stub.address not in declarations:
                            declarations[stub.address]=parse_import_declaration(stub.symbol)
                        parsed=declarations[stub.address]
                        if caller_facts:
                            fact=caller_fact(index,tail=not bool(word&0x80000000))
                        if parsed.supported and not parsed.identity.throws:
                            if not caller_facts or fact['shape']!='swifterror_idiom' or not word&0x80000000:
                                import_counts['non_throwing_swift_import_calls']+=1;continue
                            disagreement=True
                        imported=(stub,parsed)
            # Name is only a work selector; raw admission proves attribution.
            if imported is None and direct and (callee is None or not (callee.name or '').lstrip('_').startswith('$s')):
                if v4:partition.classify('direct_target_unattributed' if callee is None else 'direct_target_not_swift_function')
                continue
            report['selected_call_candidates']+=1
            if v4:
                partition.classify('selected')
                kind=('import_got' if got_selected is not None else 'import_stub' if imported is not None
                      else 'local_swift_direct' if direct else 'indirect')
            if imported is not None:import_counts['selected_import_calls']+=1
            if got_selected is not None:report['got_counts']['selected_got_calls']+=1
            # Reserve the maximum cost before another independently bounded
            # admission/build/replay unit. This is algorithmic work, not RSS.
            # Each indirect site of a v3 report decodes its function once more for the two target models.
            indirect_reserve=function.size//4+SITE_WORK if indirect_facts and indirect and got_selected is None else 0
            # The v4 causes are assigned in the order the limits are tested: a call is charged to the first one it hits.
            if report['analysis_work']+caller_work_remaining+indirect_reserve+CALLSITE_WORK_RESERVATION+ABI_WORK_RESERVATION+3*witness_limits.max_work>AGGREGATE_WORK:
                omit('analysis_work_budget');continue
            if retained>=limits.max_observations_per_function:
                omit('per_function_limit');continue
            if len(report['calls'])>=limits.max_total_evidence:
                omit('total_row_limit');continue
            if got_selected is not None:
                capability=None
                if v4:admitted=got_callsite_admission(function,pc,got_selected[0],dict(got_selected[1].declaration),
                                                      got_selected[3].reason)
                else:admitted=_got_admission(function,pc,*got_selected)
            elif imported is not None:
                capability=None
                if v4:admitted=_import_admission_v4(function,pc,word,imported[0],imported[1],imported[3])
                else:admitted=_import_admission(function,pc,word,*imported)
            else:
                try:
                    capability=admit_callsite_capability(image,function,pc,limits=call_limits,session=session)
                    admitted=capability.record()
                except CallsiteSessionError as error:
                    capability=None
                    admitted=dict(status='unresolved',reason=error.reason,details_complete=False,
                                  work_steps=error.work_steps,call_return_proven=False)
            if disagreement:admitted['reason']='declaration_caller_disagreement'
            report['analysis_work']+=admitted['work_steps']
            shape=witness=None
            if indirect_reserve and (base_declined or admitted.get('reason')=='indirect_target_unresolved'):
                shape,witness,work=indirect_target_facts(image,function,pc,symbol_lookup,
                                                         parse=witness_parse if v4 else None)
                report['analysis_work']+=work
                if v4:charge_parses()
                # Admission changes only a row that was unresolved; shape and admission records stay on the row.
                if witness['admitted'] and admitted.get('status')=='unresolved':
                    admitted['status']='declined';admitted['reason']=ADMITTED_REASON
            row=dict(caller_pc=hex(function.start),call_pc=hex(pc),admission=None,candidate=None,validation=None)
            if admitted['status']=='admitted_callsite':
                abi=_abi(image,admitted,function.start,capability)
                report['analysis_work']+=abi.get('work_steps',ABI_WORK_RESERVATION)
                admitted['abi']=_public(abi)
                row['candidate']=build_broad_swift_witness(image,function,admitted,limits=witness_limits)
                row['validation']=validate_broad_swift_witness(image,function,row['candidate'],
                    limits=witness_limits,_image_ledger=validation_ledger)
                report['analysis_work']+=sum(x.get('accounting',{}).get('work',0)
                    for x in (row['candidate'],row['validation']))
            if fact is not None:row['caller_error_test']=fact
            if v4:
                site=got_selected if got_selected is not None else imported
                if site is not None:row['effect_admission']=effect_admission(site[1].licence_class,site[2])
            if shape is not None:row['indirect_target_shape']=shape;row['value_witness_admission']=witness
            row['admission']=_public(admitted)
            verdict=row['validation'] or admitted;status=verdict.get('status','unresolved');reason=verdict.get('reason','unknown')
            row=_public(row)
            # GOT binding provenance is public offsets, not a custody record that _public strips.
            if got_selected is not None:row['admission']['got_provenance']['binding']=admitted['got_provenance']['binding']
            # Each line of a standalone row gains four spaces inside calls[].
            rendered=json.dumps(row,ensure_ascii=True,indent=2,sort_keys=True)
            cost=len(rendered)+4*(rendered.count('\n')+1)+2
            if cost>budget:
                omit('output_budget');continue
            budget-=cost;retained+=1;report['calls'].append(row)
            if pending is not None:table.record(*pending[:4],'retained',pending[4])
            statuses[status]+=1;reasons[reason]+=1
            if fact is not None:
                shapes[fact['shape']]+=1
                if 'reason' in fact['postcall']:caller_declines[fact['postcall']['reason']]+=1
            if shape is not None:
                shape_counts[shape['class']]+=1
                admission_counts['admitted' if witness['admitted'] else 'refused']+=1
                if not witness['admitted']:refusal_conditions[str(witness['first_failing_condition'])]+=1
            if not admitted.get('details_complete',True):report['outcome_witnesses_complete']=False
            candidate=row['candidate'] or {}
            cfg=candidate.get('cfg') or {}
            missing=candidate.get('completeness',{}).get('missing',[])
            resource_reasons=[reason,candidate.get('reason',''),
                cfg.get('reason',''),cfg.get('completeness',{}).get('reason',''),*missing]
            if any(any(token in str(value) for token in ('_limit','_budget','truncated'))
                   for value in resource_reasons):report['outcome_witnesses_complete']=False
    if got is not None:report['got_decline_counts']=dict(sorted(report['got_decline_counts'].items()))
    if caller_facts:
        report['caller_error_test_counts']=dict(sorted(shapes.items()))
        report['caller_error_test_decline_counts']=dict(sorted(caller_declines.items()))
    if indirect_facts:
        report['indirect_target_shape_counts']=dict(sorted(shape_counts.items()))
        report['value_witness_admission_counts']=dict(sorted(admission_counts.items()))
        report['value_witness_refusal_condition_counts']=dict(sorted(refusal_conditions.items()))
    report['status_counts']=dict(sorted(statuses.items()));report['reason_counts']=dict(sorted(reasons.items()))
    if v4:
        # Scan words are classed once by the library, in the engine's own order; the scan marker never reaches
        # reason_counts. The loop and the split must agree on the decoded count (checker B1).
        split=accounting.split_scan([(f.size,f.boundary_source=='lc_function_starts' and f.start%4==0)
                                     for f in image.functions],
                                    limits.max_instructions_per_function,limits.max_total_instructions)
        report['word_scan_complete']=split['word_scan_complete']
        capabilities=dict(accounting.CAPABILITIES)
        capabilities['premises']=list(accounting.PREMISES);capabilities['not_claimed']=list(accounting.NOT_CLAIMED)
        report.update(capabilities=capabilities,
            limits=dict(max_total_evidence=limits.max_total_evidence,
                max_observations_per_function=limits.max_observations_per_function,
                max_instructions_per_function=limits.max_instructions_per_function,
                max_total_instructions=limits.max_total_instructions,analysis_work_ceiling=AGGREGATE_WORK,
                output_budget_bytes=row_budget,import_table_entries=accounting.IMPORT_TABLE_MAX_ENTRIES,
                import_table_byte_reserve=accounting.IMPORT_TABLE_BYTE_RESERVE),
            omission_causes=dict(causes),omitted_by_kind=dict(kinds),
            unselected_call_counts=partition.counts()['unselected_call_counts'],scan=split['scan'],
            import_calls=table.import_calls(report['word_scan_complete']),
            decision_by_shape=table.decision_by_shape(),decision_summary=table.decision_summary())
        # Fail closed: an inconsistent report is never returned.
        accounting.check_broad_v4_report(report)
    # The final profile ceiling applies to the actual public JSON representation,
    # including envelope and counters, before the coordinator returns a report.
    from .report import dumps
    dumps(report,maximum_bytes=min(REPORT_BYTES,witness_limits.max_aggregate_bytes))
    return report


def recover_swift_broad_flow_path(path: Path|str, *, requested_arch: str='auto',
                                 limits: Limits|None=None, profile: str=BROAD_PROFILE)->dict:
    if profile not in PROFILE_LIMITS:
        raise InputError('swift_broad_profile','Unsupported broad profile')
    ceiling = PROFILE_LIMITS[profile]
    if limits is None: limits=ceiling
    if any(getattr(limits, name) > getattr(ceiling, name) for name in limits.__dataclass_fields__):
        raise InputError('swift_broad_limit','Requested limits exceed profile bounds')
    source=resolve_input(path)
    try:
        with source.open('rb') as handle:data=handle.read(limits.max_file_bytes+1)
    except OSError as error:
        raise InputError('unreadable_input',f'Cannot read broad Swift input: {error}') from error
    if len(data)>limits.max_file_bytes:raise InputError('file_size_limit','Broad Swift input exceeds limit')
    return recover_swift_broad_flow(parse_macho(data,str(source),limits,requested_arch),limits,profile=profile)
