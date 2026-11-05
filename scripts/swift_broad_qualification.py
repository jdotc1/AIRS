#!/usr/bin/env python3
"""One-shot broad qualification; --execute-final is deliberately required.

Reads compiler receipts/indexes without hashing, compiling or disassembling them.
A start marker survives failure and forbids accidental repetition. This script
never treats source intent, names or an emitted call count as eligibility proof.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import asdict, replace
import json
import math
import re
import time
from pathlib import Path
import struct
import subprocess
import sys
from types import MappingProxyType
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
FAMILIES = ('free', 'struct', 'enum', 'static', 'extension', 'direct_final_class', 'concrete_generic')


MAX_REPORT_BYTES=128*1024*1024
MAX_RETAINED_BYTES=96*1024*1024
SCOPE_FLAGS=frozenset(('runtime_return_proven','dominance_proven','exclusive_path_proven','source_reconstruction_allowed','exception_resume_proven','resume_proven'))
SOURCE_MINIMUMS={'free':80,'struct':100,'enum':55,'class':60,
    'static_type_extension':45,'generic':35,'protocol':25,'actor_async':20}
REQUIRED_CHALLENGES=('cbz','cbnz','cmp_conditional','direct_propagation',
    'independent_success_error_arms','shared_epilogue','multiple_returns',
    'nested_handlers','local_error_conversion','nonreturning_terminator',
    'tail_call','optimized_inlined_absence')
MANDATORY_GATES=frozenset((
    'aggregate_work_complete','aggregate_retained_output_complete',
    'raw_compiler_challenge_scan_complete','unsupported_compiler_forms_disposition',
    'required_unsupported_challenges_observed','callsite_sessions_complete',
    'independent_image_ledgers_complete','source_420','source_methods_340',
    'source_category_minima','source_diversity_reconciled',
    'emitted_abi_shapes_80','physical_calls_1500','eligible_primary_witnesses_250',
    'seven_families_15_each','positive_emitted_geometries_10',
    'observed_emitted_challenges_12','result_lowerings_8',
    'negative_300_zero_false_eligible','fresh_raw_coordinate_attacks',
    'negative_attack_kind_coverage','seven_family_negative_controls',
    'stratified_100_identical','second_compiler_positive','two_whole_branch_reviews',
    'measured_latency_rss'))


def scope_flag(key):
    # Match the validator's recursive proof-scope rule, including future flags.
    return isinstance(key,str) and (key.endswith('_proven') or key=='source_reconstruction_allowed')


class PerformanceMeasurements:
    """Observations from this one pass; no timers, children or extra analysis."""
    KINDS=frozenset(('owned_image','callsite_session','independent_image_ledger',
        'physical_call','retained_negative','limit_negative','custody_negative',
        'fresh_synthetic_group','repeat_comparison'))
    def __init__(self,clock=None,rusage=None,platform=None):
        self.clock=clock or time.perf_counter;self.platform=platform or sys.platform
        if rusage is None:
            try:
                import resource
                rusage=lambda:resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            except ImportError:rusage=lambda:None
        self.rusage=rusage;self.errors=[];self.units={};self.started=self._now()
    def _now(self):
        try:
            value=self.clock()
            if not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError()
            return value
        except Exception:
            if 'monotonic_clock_unavailable' not in self.errors:self.errors.append('monotonic_clock_unavailable')
            return None
    def call(self,kind,operation,*args,**kwargs):
        if kind not in self.KINDS:raise ValueError('unknown measurement unit')
        started=self._now();failed=True
        try:
            result=operation(*args,**kwargs);failed=False;return result
        finally:
            ended=self._now()
            row=self.units.setdefault(kind,dict(count=0,failed_units=0,measured_units=0,
                total_seconds=0.0,min_seconds=None,max_seconds=None))
            row['count']+=1;row['failed_units']+=int(failed)
            if started is not None and ended is not None and ended>=started:
                elapsed=ended-started;row['measured_units']+=1;row['total_seconds']+=elapsed
                row['min_seconds']=elapsed if row['min_seconds'] is None else min(row['min_seconds'],elapsed)
                row['max_seconds']=elapsed if row['max_seconds'] is None else max(row['max_seconds'],elapsed)
            elif 'unit_timing_unavailable' not in self.errors:self.errors.append('unit_timing_unavailable')
    def snapshot(self):
        ended=self._now();elapsed=None
        if self.started is not None and ended is not None and ended>=self.started:elapsed=ended-self.started
        elif 'total_timing_unavailable' not in self.errors:self.errors.append('total_timing_unavailable')
        rss=dict(status='unavailable',raw_value=None,raw_unit=None,bytes=None,
            source='getrusage(RUSAGE_SELF).ru_maxrss',scope='Python process lifetime high-water RSS; not interval peak',
            excludes=['compiler processes','native processes','Git helper children','storage-guard parent'])
        try:
            raw=self.rusage();unit={'darwin':'bytes','linux':'KiB'}.get(self.platform)
            if unit is None or not isinstance(raw,(int,float)) or not math.isfinite(raw) or raw<=0:raise ValueError()
            rss.update(status='measured',raw_value=raw,raw_unit=unit,bytes=int(raw*(1024 if unit=='KiB' else 1)))
        except Exception:rss['reason']='RSS API/value/platform unit unavailable'
        complete=(elapsed is not None and rss['status']=='measured' and bool(self.units) and not self.errors)
        return dict(status='measured' if complete else 'unavailable_or_incomplete',complete=complete,
            total_elapsed_seconds=elapsed,clock='perf_counter',
            interval='qualification invocation start to this snapshot; final report serialization and packaging excluded',
            per_unit_summary=dict(sorted(self.units.items())),unit_summary_limit=len(self.KINDS),
            peak_rss=rss,measurement_errors=list(self.errors),
            bounds=dict(algorithmic_steps='charged local work only',
                retained_bytes='encoded retained records only',output_bytes='streamed JSON only',
                wall_time_ceiling=None,process_rss_ceiling=None))


def source_inventory(cases):
    counts=Counter(c.get('category') for c in cases)
    vectors=[canonical(c.get('feature_vector')) for c in cases]
    identities=[c.get('case_id') for c in cases]
    signatures={c.get('signature_shape') for c in cases if c.get('signature_shape')}
    valid_vectors=all(isinstance(c.get('feature_vector'),list) and len(c['feature_vector'])==8
        and c['feature_vector'][:4]==[c.get(k) for k in ('category','return_family','parameter_form','dispatch')]
        for c in cases)
    return dict(category_counts=dict(counts),category_minimums=SOURCE_MINIMUMS,
        categories_complete=all(counts[k]>=n for k,n in SOURCE_MINIMUMS.items()),
        unique_case_ids=len(set(identities)),distinct_feature_vectors=len(set(vectors)),
        source_signature_shapes=len(signatures),
        diversity_reconciled=bool(cases) and all(isinstance(x,str) and x for x in identities)
            and len(set(identities))==len(cases) and valid_vectors and len(set(vectors))==len(cases)
            and len(signatures)>=80,
        scope='reused owned source-manifest inventory; not emitted ABI diversity or new AST/compiler verification')


class JSONBoundError(ValueError):pass


def read_bounded_json(path, *, max_bytes=32*1024*1024, max_tokens=500_000, max_depth=48):
    # Refuse before deserialization; parser recursion/large strings/numbers and
    # container growth are bounded even for syntactically invalid JSON inputs.
    with Path(path).open('rb') as handle:raw=handle.read(max_bytes+1)
    if len(raw)>max_bytes:raise JSONBoundError('JSON input byte limit')
    text=raw.decode('utf-8');depth=0;tokens=0;quoted=False;escaped=False;string_size=0;scalar_size=0
    for ch in text:
        if quoted:
            string_size+=1
            if string_size>65536:raise JSONBoundError('JSON string limit')
            if escaped:escaped=False
            elif ch=='\\':escaped=True
            elif ch=='"':quoted=False
            continue
        if ch=='"':quoted=True;string_size=0;tokens+=1;scalar_size=0
        elif ch in '[{':depth+=1;tokens+=1;scalar_size=0
        elif ch in ']}':depth-=1;tokens+=1;scalar_size=0
        elif ch in ',:':tokens+=1;scalar_size=0
        elif ch.isspace():scalar_size=0
        else:
            scalar_size+=1
            if scalar_size==1:tokens+=1
            if scalar_size>128:raise JSONBoundError('JSON scalar limit')
        if depth>max_depth or depth<0:raise JSONBoundError('JSON depth limit')
        if tokens>max_tokens:raise JSONBoundError('JSON token limit')
    value=json.loads(text)
    if not isinstance(value,dict):raise JSONBoundError('JSON object required')
    return value


def validate_capture_counts(manifest,index,receipt):
    cases=manifest.get('cases');modes=index.get('modes')
    if not isinstance(cases,list) or len(cases)>1000:raise JSONBoundError('source case count limit')
    if not isinstance(modes,dict) or not 1<=len(modes)<=3:raise JSONBoundError('compiler mode count limit')
    if not isinstance(receipt.get('modes'),dict) or set(modes)!=set(receipt['modes']):raise JSONBoundError('compiler mode mismatch')
    sites=0
    for case in cases:
        calls=case.get('source_callsites')
        if not isinstance(calls,list) or len(calls)>8:raise JSONBoundError('source site count limit')
        sites+=len(calls)
    if sites>8000:raise JSONBoundError('aggregate source site count limit')
    for mode in modes.values():
        cases=mode.get('cases',[])
        if not isinstance(cases,list) or len(cases)>1000:raise JSONBoundError('indexed case count limit')
        calls=mode.get('calls')
        if not isinstance(calls,list) or len(calls)>10000:raise JSONBoundError('indexed call count limit')


def validate_capture_prerequisites(capture,manifest,index,receipt):
    """Metadata admission before consuming the one-shot analysis marker.

    The separately authorized second compiler is representative, so its index
    state and source count intentionally differ from the full primary corpus.
    No image, compiler or disassembler is invoked by this metadata check.
    """
    validate_capture_counts(manifest,index,receipt)
    if receipt.get('schema')!='airs.owned-swift-broad-compile.v2':
        raise ValueError('trusted v2 compiler receipt required')
    if receipt.get('state') not in ('compiled_unindexed','indexed'):
        raise ValueError('complete compiler receipt state required')
    if set(index['modes'])!={'Onone','O','Osize'}:
        raise ValueError('three captured optimization modes required')
    if capture=='primary':
        if index.get('state')!='indexed':raise ValueError('primary requires complete indexed corpus')
        if len(manifest['cases'])<420:raise ValueError('primary requires at least 420 source cases')
    elif capture=='second':
        if index.get('state') not in ('indexed_representative','indexed'):
            raise ValueError('second compiler requires complete representative index')
        if len(manifest['cases'])!=64:raise ValueError('second representative requires 64 source cases')
        if any(not mode['calls'] for mode in index['modes'].values()):
            raise ValueError('second representative modes must contain actual indexed calls')
    else:raise ValueError('unknown compiler capture role')
    physical=set()
    for mode,record in index['modes'].items():
        for call in record['calls']:
            if call.get('owned_target_confirmed') is True:
                pc=call.get('pc')
                if not isinstance(pc,str):raise ValueError('confirmed call PC required')
                physical.add((mode,int(pc,16)))
    minimum=1500 if capture=='primary' else 1
    if len(physical)<minimum:raise ValueError('capture confirmed physical call prerequisite not met')
    return dict(role=capture,index_state=index['state'],source_cases=len(manifest['cases']),
        confirmed_physical_calls=len(physical),minimum_required_calls=minimum,
        scope='full_primary' if capture=='primary' else 'representative_second_compiler')


def compiler_identity(directory,receipt):
    compiler=receipt.get('swiftc');version=receipt.get('toolchain')
    if not isinstance(compiler,str) or not isinstance(version,str):raise ValueError('captured compiler path/version required')
    match=re.search(r'(?:Apple )?Swift version ([^\n]+)',version)
    if not compiler or not match:raise ValueError('captured compiler version required')
    if receipt.get('output_directory')!=str(directory):raise ValueError('capture output directory mismatch')
    for mode in receipt['modes'].values():
        command=mode.get('command')
        if not isinstance(command,list) or not command or command[0]!=compiler:raise ValueError('captured compiler command mismatch')
    return dict(capture_directory=str(directory),compiler_path=str(Path(compiler).resolve()),compiler_version=match.group(1))


def distinct_compilers(first,second):
    return (first['capture_directory']!=second['capture_directory']
        and first['compiler_path']!=second['compiler_path']
        and first['compiler_version']!=second['compiler_version'])


def json_size(value, maximum):
    size=0
    for chunk in json.JSONEncoder(sort_keys=True,separators=(',',':'),ensure_ascii=True).iterencode(value):
        size+=len(chunk.encode('ascii'))
        if size>maximum:raise JSONBoundError('aggregate retained JSON byte limit')
    return size


class RetentionBudget:
    def __init__(self,limit=MAX_RETAINED_BYTES):self.limit=limit;self.used=0;self.omitted=Counter()
    def admit(self,row,extra=None,kind="physical_call_record"):
        try:
            size=json_size(row,self.limit-self.used)
            if extra is not None:size+=json_size(extra,self.limit-self.used-size)
        except JSONBoundError:
            self.omitted[kind]+=1;return False
        self.used+=size;return True


def write_bounded_json(path,value,maximum=MAX_REPORT_BYTES):
    partial=path.with_name(path.name+'.partial');size=0
    with partial.open('x',encoding='ascii') as stream:
        for chunk in json.JSONEncoder(sort_keys=True,separators=(',',':'),ensure_ascii=True).iterencode(value):
            size+=len(chunk)
            if size>maximum:raise JSONBoundError('streamed output JSON byte limit')
            stream.write(chunk)
        stream.write('\n')
    partial.replace(path)


class WorkBudget:
    def __init__(self, limit=512_000_000):
        self.limit=limit;self.used=0;self.omitted=Counter();self.units=Counter()
    def reserve(self, kind, maximum):
        if self.limit-self.used<maximum:
            self.omitted[kind]+=1
            return False
        return True
    def charge(self, kind, actual, maximum):
        if type(actual) is not int or not 0<=actual<=maximum:
            raise ValueError('Unit accounting exceeds reserved maximum: '+kind)
        self.used+=actual;self.units[kind]+=1
        if self.used>self.limit:raise ValueError('Aggregate work limit exceeded')
    def report(self):
        return dict(limit=self.limit,actual_steps=self.used,units=dict(self.units),
            omitted_units=dict(self.omitted),complete=not self.omitted)


def unit_work(admission,candidate,validation):
    abi=admission.get('abi',{})
    return admission.get('work_steps',0)+abi.get('work_steps',abi.get('work_bytes',0))+sum(
        value.get('accounting',{}).get('work',0) for value in (candidate,validation) if value)+(
        validation.get('accounting',{}).get('image_work_charged_here',0) if validation else 0)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def public(value):
    if isinstance(value, dict):
        return {k: public(v) for k, v in value.items() if k != 'binding' and not k.endswith('_binding')}
    if isinstance(value, (tuple, list)):
        return [public(v) for v in value]
    return value


def seal_size(candidate):
    # Refresh representation size so a changed semantic claim cannot pass a
    # negative solely because its serialized byte count became stale.
    for _ in range(8):
        size = len(canonical(candidate).encode('ascii'))
        if candidate['accounting']['encoded_bytes'] == size:
            return
        candidate['accounting']['encoded_bytes'] = size
    raise ValueError('candidate size did not converge')


def semantic_mutations(candidate):
    """Distinct retained field paths, without IDs/names padded into diversity.

    Only claims independently checked by replay are selected. A path appears
    once globally, even when many corpus calls contain it. Work/size counters
    and arbitrary optional producer metadata are excluded.
    """
    roots = ('identity', 'call', 'cfg', 'post_call', 'regions', 'value_facts', 'completeness')
    def walk(value, path):
        if isinstance(value, dict):
            for key in sorted(value):
                if key in ('binding', 'reason', 'work', 'encoded_bytes', 'limitations','external_exception_handling_unmodeled'):
                    continue
                yield from walk(value[key], path + (key,))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                yield from walk(item, path + (i,))
        else:
            # Deletion forces replay to notice missing evidence, rather than
            # manufacturing many different spellings of the same bad value.
            yield path
    for root in roots:
        if root not in candidate:
            continue
        for path in walk(candidate[root], (root,)):
            if path[:3] == ('call','abi','evidence'):
                continue
            if path[:2] == ('call','abi') and len(path)>2 and path[2] not in ('status','profile','error_register','research_only','argument_locations','receiver_location','result_location','result_storage','argument_storage'):
                continue
            yield path


def attack_kind(path):
    if scope_flag(path[-1]):return 'proofscope'
    if path[0]=='identity':return 'identity'
    if path[:3]==('call','declaration','identity'):
        if 'callable_kind' in path:return 'dispatch'
        if 'context' in path:return 'nominal'
        return 'ABI'
    if path[:2]==('call','abi'):return 'ABI'
    if path[0]=='call':return 'rawcall'
    if path[0]=='post_call':
        return 'polarity' if any('successor' in str(p) for p in path) else 'posttest'
    if path[0]=='cfg':return 'entry' if 'predecessors' in path else 'CFG'
    if path[0]=='value_facts':return 'valueattachment'
    if path[0]=='regions':return 'entry'
    return 'truncation'


def delete_claim(candidate, path):
    changed = deepcopy(candidate)
    parent = changed
    for key in path[:-1]:
        parent = parent[key]
    if scope_flag(path[-1]):
        if parent[path[-1]] is not False:raise ValueError('scope attack requires a false proof flag')
        parent[path[-1]]=True
    elif path[:2]==('call','abi'):
        old=parent[path[-1]]
        parent[path[-1]] = (not old if type(old) is bool else old+1 if type(old) is int else '__tampered_abi_scalar__')
    elif isinstance(parent, list):
        # Keep list positions stable; removing changes other claim coordinates.
        parent[path[-1]] = {'negative_missing_scalar': True}
    else:
        del parent[path[-1]]
    seal_size(changed)
    return changed


def declaration_family(decl, abi):
    """Syntax family plus required independent context proof; never source labels."""
    qualified = abi.get('family')
    aliases = {'static_type': 'static', 'concrete_generic_specialization': 'concrete_generic'}
    if qualified and abi.get('family_evidence', {}).get('source_sha256'):
        return aliases.get(qualified, qualified if qualified in FAMILIES else None)
    kind = decl.callable_kind.value
    if kind == 'generic_specialization' and decl.specialization is not None:
        return 'concrete_generic'
    context = abi.get('evidence', {}).get('nominal_context', {})
    # Extension/finality require explicit byte-derived ABI evidence. Absence
    # remains unproven, even when a source manifest advertises either feature.
    if context.get('extension_context_proven') is True:
        return 'extension'
    return {'free_function': 'free', 'struct_instance_method': 'struct',
            'enum_instance_method': 'enum', 'static_method': 'static',
            'class_instance_method': 'direct_final_class' if context.get('final_class_proven') is True else None}.get(kind)


def emitted_shape(decl, abi):
    if abi.get('status') != 'admitted':
        return None
    if abi.get('abi_shape'):
        return canonical(abi['abi_shape'])
    # Name-free complete type structure, physical locations and receiver model.
    def typ(t):
        return (t.name, t.inout, tuple(typ(a) for a in t.arguments))
    return canonical(dict(parameters=[typ(t) for t in decl.parameter_types],
        result=typ(decl.result_type), arguments=abi.get('argument_locations'),
        receiver=abi.get('receiver_location'), result_location=abi.get('result_location'),
        error=abi.get('error_register'), kind=decl.callable_kind.value))


def geometry(candidate, validation):
    try:return _checked_geometry(candidate,validation)
    except (KeyError,TypeError,ValueError,IndexError):return None


def _checked_geometry(candidate, validation):
    """Canonical selected-outcome CFG after successful independent replay.

    Contract data operations, padding and unconditional hops. Retain selected
    test/polarity, interior conditions/calls, terminal kinds and arm sharing.
    IDs come from rooted edge traversal, never lexical addresses or prefixes.
    """
    if not validation or validation.get('eligible') is not True:return None
    if any(validation.get('fact_statuses',{}).get(k)!='checked' for k in ('cfg','post_call','regions')):return None
    post=candidate['post_call'];cfg=candidate['cfg'];partition=validation['region_partition']
    roles={pc:role for key,role in (('success_only_pcs','success'),('error_only_pcs','error'),('shared_pcs','shared'))
        for pc in partition.get(key,[])}
    allowed=set(roles)|set(post['trace']);words={r['pc']:r for b in cfg['blocks'] for r in b['instructions'] if r['pc'] in allowed}
    if len(words)>4096:raise ValueError('geometry instruction bound')
    outgoing=defaultdict(list)
    for edge in cfg['edges']:
        if edge['source_pc'] in allowed:outgoing[edge['source_pc']].append((edge['kind'],edge['target_pc']))
    test=post['test_pc'];conditional={'xcbz','xcbnz','wcbz','wcbnz','bcond','xtbz','xtbnz','wtbz','wtbnz'}
    anchors={pc for pc,row in words.items() if pc==test or row['kind'] in conditional|{'bl','ret','brk'}}
    resolved={}
    def contract(pc):
        path=[];seen=set()
        while pc not in anchors:
            if pc in resolved:pc=resolved[pc];break
            if pc not in words or pc in seen:raise ValueError('unchecked geometry path')
            seen.add(pc);path.append(pc);edges=outgoing.get(pc)
            if edges:
                if len(edges)!=1 or edges[0][1] is None:raise ValueError('nonlinear geometry contraction')
                pc=edges[0][1]
            else:pc=hex(int(pc,16)+4)
        for old in path:resolved[old]=pc
        return pc
    roots=[contract(post['trace'][0]),contract(post['success_successor_pc']),contract(post['error_successor_pc'])]
    ids={};todo=[]
    def identify(pc):
        if pc not in ids:ids[pc]=len(ids);todo.append(pc)
        return ids[pc]
    root_ids=[identify(pc) for pc in roots];nodes=[]
    for pc in todo:
        row=words[pc];kind=row['kind'];word=int(row['word'],16)
        label=('cmp_zero_bcond_'+post['test_condition'] if pc==test and post.get('test_kind')=='cmp_zero_bcond' else kind)
        if pc!=test and kind=='bcond':label+='_'+str(word&15)
        if kind in ('xtbz','xtbnz','wtbz','wtbnz'):label+='_bit_test'  # bit number/register do not add geometry
        edges=[]
        for edge_kind,target in sorted(outgoing.get(pc,[])):
            if target is not None:
                edge_label=(('success' if target==post['success_successor_pc'] else 'error') if pc==test else edge_kind)
                edges.append((edge_label,identify(contract(target))))
            else:edges.append((edge_kind,None))
        nodes.append(dict(id=ids[pc],kind=label,partition=roles.get(pc,'selected_postcall'),edges=edges))
    # Error transport remains a row diagnostic; data/register movement does not
    # multiply the number of control-flow geometries.
    return canonical(dict(schema='selected-outcome-geometry.v2',roots=root_ids,nodes=nodes))


def source_caller_links(aliases,callers):
    tokens={m.group(0) for name in aliases for m in re.finditer(r'broad_caller_[0-9]{4}_[0-9]+(?![0-9])',name)}
    return [callers[token] for token in sorted(tokens) if token in callers]


def selected_arm_cmp_conditions(candidate,validation):
    """Adjacent allocated CMP/B.cond inside an independently checked arm.

    The comparison need not be the error-register zero test. It establishes a
    post-call selected-arm control-flow form, never flags, truth or execution.
    """
    partition=validation.get('region_partition',{})
    selected=set().union(*(set(partition.get(k,[])) for k in ('success_only_pcs','error_only_pcs','shared_pcs')))
    result=[]
    for block in candidate.get('cfg',{}).get('blocks',[]):
        rows=block.get('instructions',[])
        for left,right in zip(rows,rows[1:]):
            if left['pc'] not in selected or right['pc'] not in selected:continue
            if int(right['pc'],16)!=int(left['pc'],16)+4 or right.get('kind')!='bcond':continue
            w=int(left['word'],16);branch=int(right['word'],16)
            shifted=(w&0x7fe0001f==0x6b00001f and (w>>22)&3!=3
                and (bool(w>>31) or not (w>>15)&1))
            immediate=w&0x7f80001f==0x7100001f
            if not (shifted or immediate):continue
            if branch&0xff000010!=0x54000000 or branch&15>=14:continue
            result.append(dict(comparison_pc=left['pc'],comparison_word=left['word'],
                branch_pc=right['pc'],branch_word=right['word'],condition=branch&15,
                width=64 if w>>31 else 32,error_zero_test=False))
    return result


def required_challenge_dispositions(row):
    try:
        result=_required_challenge_dispositions(row)
        row['challenge_measurement_status']='reconciled'
        return result
    except (KeyError,TypeError,ValueError,IndexError):
        row['challenge_measurement_status']='incomplete_independent_result_contract'
        return []


def _required_challenge_dispositions(row):
    """Twelve specific compiled challenges, with separate source intent.

    This reconciles independent results already computed during the one pass.
    It cannot infer catch types, source handlers, execution or Swift noreturn.
    A source-only/collapsed/unproven record never counts as observed geometry.
    """
    links=row.get('source_callers',[])
    if not links:return []
    candidate=row.get('candidate') or {};validation=row.get('validation') or {}
    checked=(validation.get('eligible') is True and
        all(validation.get('fact_statuses',{}).get(k)=='checked' for k in ('cfg','post_call','regions')))
    records=[];intents={x['source_geometry'] for x in links}
    locator=dict(capture=row['capture'],mode=row['mode'],call_pc=row.get('call_pc'),
        caller_pc=row.get('caller_pc'),source_callers=links,
        evidence_record='positives_and_declines' if candidate else 'compiler_challenge_observations')
    identity=candidate.get('identity') or row.get('image_identity',{})
    locator['image_identity']={k:identity[k] for k in ('slice_sha256','container_sha256','uuid','slice_index') if k in identity}
    def add(key,disposition,reason,raw=(),*,observed=False,cfg=False):
        records.append(dict(challenge=key,disposition=disposition,actual_form_observed=observed,
            reason=reason,locator=locator,raw_evidence=list(raw)[:16],checked_cfg=cfg,
            independent_outcome=dict(status=validation.get('status',row.get('status')),
                reason=validation.get('reason',row.get('reason'))),
            source_semantics_recovered=False,runtime_execution_proven=False))
    if checked:
        post=candidate['post_call'];partition=validation['region_partition'];cfg=candidate['cfg']
        words={r['pc']:r for b in cfg['blocks'] for r in b['instructions']}
        selected=set(post['trace'])|set().union(*(set(partition[k]) for k in ('success_only_pcs','error_only_pcs','shared_pcs')))
        evidence=lambda pcs:[dict(pc=p,word=words[p]['word']) for p in sorted(set(pcs),key=lambda x:int(x,16))]
        test=post['test_pc'];test_kind=words[test]['kind']
        key='cmp_conditional' if post.get('test_kind')=='cmp_zero_bcond' else ('cbz' if test_kind=='xcbz' else 'cbnz')
        add(key,'observed','independently checked selected x21-origin zero test',
            evidence([test]+([post['comparison_pc']] if post.get('comparison_pc') else [])),observed=True,cfg=True)
        for comparison in selected_arm_cmp_conditions(candidate,validation):
            add('cmp_conditional','observed','adjacent allocated CMP/B.cond in independently checked selected arm; distinct from the primary error zero test; flags/truth/execution unproven',
                evidence([comparison['comparison_pc'],comparison['branch_pc']]),observed=True,cfg=True)
            records[-1]['comparison_form']=comparison
        if partition['success_only_pcs'] and partition['error_only_pcs']:
            add('independent_success_error_arms','observed','both selected arms have distinct checked instructions',
                evidence([post['success_successor_pc'],post['error_successor_pc']]),observed=True,cfg=True)
        shared_returns={r['return_pc'] for r in validation.get('return_observations',[])}&set(partition['shared_pcs'])
        if shared_returns:
            add('shared_epilogue','observed','selected success/error paths share a checked tail',
                evidence(shared_returns),observed=True,cfg=True)
        returns=[r for r in validation.get('return_observations',[]) if r['return_pc'] in selected]
        if len({r['return_pc'] for r in returns})>1:
            add('multiple_returns','observed','distinct selected-arm RET PCs',evidence(r['return_pc'] for r in returns),observed=True,cfg=True)
        errors=[r for r in returns if r['arm']=='error']
        if 'propagation' in intents:
            preserved=bool(errors) and all(r.get('raw_error_register_value') in
                (['error_result',candidate['call']['pc'],64],['raw_postcall_x21',candidate['call']['pc'],64]) for r in errors)
            add('direct_propagation','observed' if preserved else 'unproven',
                'source propagation intent; checked raw x21 origin at each error RET' if preserved else 'raw error-origin transport to RET not established',
                evidence(r['return_pc'] for r in errors),observed=preserved,cfg=True)
        if 'nested_handlers' in intents:
            nested=[pc for pc in selected-set(post['trace']) if words[pc]['kind'] in
                ('xcbz','xcbnz','wcbz','wcbnz','bcond','xtbz','xtbnz','wtbz','wtbnz')]
            add('nested_handlers','unproven' if nested else 'collapsed',
                'additional checked condition is not sufficient to establish a nested error corridor; awaiting independently checked second-call linkage'
                if nested else 'owned nested-handler intent has no additional selected-outcome conditional',
                evidence(nested),observed=False,cfg=True)
        if 'local_error_conversion' in intents:
            converted=bool(errors) and all(r.get('status')=='modeled_symbolic_value'
                and r.get('value',[None])[0] not in ('call_result','error_result','raw_postcall_x21','unknown')
                and r.get('raw_error_register_value')==['constant',0,64] for r in errors)
            add('local_error_conversion','observed' if converted else 'unproven',
                'owned conversion intent; checked distinct scalar output and cleared x21 at error returns; catch types not recovered'
                if converted else 'owned conversion intent lacks checked output/error-clear relation',
                evidence(r['return_pc'] for r in errors),observed=converted,cfg=True)
        terminals=[r['pc'] for r in validation.get('exception_observations',[]) if r['pc'] in selected]
        if terminals and 'noreturn_handler' in intents:
            add('nonreturning_terminator','observed','BRK terminal in checked selected outcome; external handling/resumption and Swift noreturn unproven',
                evidence(terminals),observed=True,cfg=True)
    # Raw observations retain exact syntax even where independent outcome replay
    # refuses. They qualify only the named raw form, never a semantic substitute.
    features={r['feature']:r for r in row.get('features',[])}
    for intent,key,names in (
        ('noreturn_handler','nonreturning_terminator',('raw_trap_brk',)),
        ('tail_return','tail_call',('raw_direct_tail_escape','raw_indirect_tail_br'))):
        if intent not in intents:continue
        matched=[f for name in names for f in features.get(name,{}).get('evidence',[])]
        if matched:
            add(key,'refused','owned intent plus raw terminal/transfer encoding; target semantics and runtime behavior unproven',matched,observed=True)
        elif not checked:add(key,'unproven','source intent without required checked/raw terminal form')
    if row.get('feature')=='owned_source_callee_call_absence' and 'inline_absence_challenge' in intents:
        callers=row.get('absence_callers',[])
        confirmed=row.get('complete') is True
        raw=[e for c in callers for e in c.get('extent_evidence',[])]
        add('optimized_inlined_absence','observed' if confirmed else 'unproven',
            'owned inline-absence intent; complete caller byte coverage and exact source-callee target mapping establish no direct source-callee transfer; unrelated indexed runtime calls permitted; inlining cause unproven'
            if confirmed else 'index absence lacks complete corresponding caller byte scans',raw,observed=confirmed)
    if not checked:
        for intent,key in (('propagation','direct_propagation'),('nested_handlers','nested_handlers'),('local_error_conversion','local_error_conversion')):
            if intent in intents:add(key,'unproven','source intent retained; independent selected-outcome replay did not establish this form')
    return records


def reconcile_nested_challenges(rows,budget,retention):
    """Join already computed independent call results, never replay an image.

    A second admitted throwing call/test with distinct error/success corridors
    must lie inside one exclusive outer arm; its tails may join outer shared
    code. An unrelated conversion/overflow branch cannot provide this link.
    """
    groups=defaultdict(list);kind='nested_challenge_reconciliation'
    def charge(amount):
        if not budget.reserve(kind,amount):return False
        budget.charge(kind,amount,amount);return True
    for row in rows:
        if not charge(1):return
        v=row.get('validation') or {};c=row.get('candidate') or {}
        if v.get('eligible') is not True or any(v.get('fact_statuses',{}).get(k)!='checked'
            for k in ('abi','cfg','post_call','regions')):continue
        identity=c.get('identity',{});caller=identity.get('caller',{})
        key=(row['capture'],row['mode'],identity.get('slice_sha256'),identity.get('container_sha256'),
            caller.get('start_pc'),caller.get('end_pc_exclusive'))
        if not all(isinstance(part,str) and part for part in key):continue
        groups[key].append(row)
    for group in groups.values():
        for outer in group:
            targets=[r for r in outer.get('required_challenge_dispositions',[]) if r['challenge']=='nested_handlers']
            if not targets:continue
            op=outer['validation'].get('region_partition',{})
            if not charge(sum(len(op.get(k,[])) for k in ('success_only_pcs','error_only_pcs','shared_pcs'))+1):return
            outer_sets={arm:set(op.get(arm+'_only_pcs',[])) for arm in ('success','error')}
            shared=set(op.get('shared_pcs',[]))
            for inner in group:
                if not charge(1):return
                if inner is outer:continue
                candidate=inner['candidate'];validation=inner['validation'];post=candidate.get('post_call',{})
                partition=validation.get('region_partition',{})
                cp=candidate.get('call',{}).get('pc')
                if not all(isinstance(value,str) for value in (cp,candidate.get('call',{}).get('word'),
                    post.get('test_pc'),post.get('test_word'),post.get('error_successor_pc'))):continue
                arm=next((arm for arm,pcs in outer_sets.items() if cp in pcs),None)
                if arm is None or not partition.get('success_only_pcs') or not partition.get('error_only_pcs'):continue
                total=sum(len(partition.get(k,[])) for k in ('success_only_pcs','error_only_pcs','shared_pcs'))+len(post.get('trace',[]))
                if total>4096 or not charge(total+1):continue
                inner_pcs=set(post.get('trace',[]))|set().union(*(set(partition.get(k,[])) for k in
                    ('success_only_pcs','error_only_pcs','shared_pcs')))
                if not inner_pcs or not inner_pcs<=outer_sets[arm]|shared or post.get('test_pc') not in outer_sets[arm]:continue
                record=dict(targets[0],disposition='observed',actual_form_observed=True,
                    reason='owned nested intent with independently checked second throwing-call/error-test corridor inside an exclusive selected arm; source catch/handler equivalence unproven',
                    raw_evidence=[dict(pc=cp,word=candidate['call']['word']),dict(pc=post['test_pc'],word=post['test_word'])],
                    nested_corridor=dict(capture=inner['capture'],mode=inner['mode'],call_pc=cp,test_pc=post['test_pc'],
                        error_entry_pc=post['error_successor_pc'],outer_arm=arm,
                        independent_result_locator='positives_and_declines',status=validation['status']))
                if retention.admit(record,kind='nested_challenge_link'):
                    targets[0].clear();targets[0].update(record)
                break
            # Missing link retains the earlier unproven/collapsed disposition.


def challenge_inventory(rows,raw_rows,cases,*,capture_role='primary',challenges=REQUIRED_CHALLENGES):
    inventory={key:dict(observed=False,dispositions={},examples=[],omitted_examples=0) for key in challenges}
    from itertools import chain
    for row in chain(rows,raw_rows):
        if row['capture']!=capture_role:continue
        for record in row.get('required_challenge_dispositions',[]):
            if record['challenge'] not in REQUIRED_CHALLENGES:raise ValueError('Unknown challenge')
            if record['challenge'] not in inventory:continue
            entry=inventory[record['challenge']];state=record['disposition']
            entry['dispositions'][state]=entry['dispositions'].get(state,0)+1
            entry['observed']|=record['actual_form_observed'] is True and state in ('observed','refused')
            if len(entry['examples'])<4:entry['examples'].append(record)
            else:entry['omitted_examples']+=1
    # Retain source-only intents even when the compiler emitted no matching row.
    for key,intent in (('direct_propagation','propagation'),('nested_handlers','nested_handlers'),
        ('local_error_conversion','local_error_conversion'),('nonreturning_terminator','noreturn_handler'),
        ('tail_call','tail_return'),('optimized_inlined_absence','inline_absence_challenge')):
        if key in inventory and not inventory[key]['dispositions']:
            inventory[key]['dispositions']['source_only' if any(site['geometry']==intent for c in cases for site in c['source_callsites']) else 'missing_source_intent']=1
    return dict(required=list(challenges),entries=inventory,
        complete=all(row['observed'] for row in inventory.values()),
        scope='owned source intent mapped to actual emitted observations; no recovered source catch types/runtime/noreturn proof')


SUPPLEMENTAL_CHALLENGES=('nested_handlers','local_error_conversion')
IMAGE_KEYS=('slice_sha256','container_sha256','slice_offset','slice_size','architecture','cpu_subtype',
    'uuid','preferred_base','slice_index','container_slice_count')


def validate_supplemental_study(study,source_revision):
    """Admit a trusted private first-validator receipt, never a byte oracle.

    Rewriting a trusted local receipt is outside this custody boundary, exactly
    as with owned compile receipts. Core validator APIs never consume this JSON.
    """
    def need(ok,reason):
        if not ok:raise ValueError('Supplemental study: '+reason)
    def pc(value):
        need(type(value) is int or isinstance(value,str),'call PC type')
        n=value if type(value) is int else int(value,16)
        need(0<=n<2**64 and n%4==0,'aligned call PC');return n
    need(study.get('schema')=='airs.swift-broad-supplemental-study.v1','schema')
    need(study.get('source_revision')==source_revision,'stale source revision')
    need(study.get('role')=='supplemental_challenge_only','role')
    need(study.get('not_primary_positive_credit') is True and study.get('not_second_compiler_credit') is True,'credit boundary')
    evidence=study.get('supplemental_capture_evidence',{})
    need(evidence.get('used') is True and evidence.get('role')=='supplemental_challenge_only','capture evidence role')
    need(isinstance(evidence.get('source_sha256'),str) and re.fullmatch('[0-9a-f]{64}',evidence['source_sha256']) is not None,'source digest')
    images=evidence.get('images',{})
    need(set(images)=={'Onone','O','Osize'} and all(isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v) for v in images.values()),'three image digests')
    rows=study.get('observations')
    need(isinstance(rows,list) and 1<=len(rows)<=18,'observation bound')
    need(type(study.get('observation_count')) is int and study['observation_count']==len(rows),'observation count')
    seen=set()
    for row in rows:
        need(row.get('capture')=='supplemental' and row.get('mode') in images,'observation role/mode')
        site=(row['mode'],pc(row.get('call_pc')));need(site not in seen,'duplicate physical observation');seen.add(site)
        c=row.get('candidate') or {};v=row.get('validation') or {};a=row.get('admission') or {}
        identity=row.get('image_identity') or c.get('identity',{})
        need(all(k in identity for k in IMAGE_KEYS),'explicit raw image identity')
        need(identity['slice_sha256']==images[row['mode']]==identity['container_sha256'],'selected image digest')
        need(identity['architecture']=='arm64' and identity['slice_index']==0 and identity['container_slice_count']==1,'thin ARM64 identity')
        need(identity['slice_offset']=='0x0','thin slice offset')
        if c:
            need(c.get('model_version')=='swift-outcome-witness-v2' and c.get('validation_model')=='swift-outcome-validation-v2','candidate model')
            ci=c.get('identity',{})
            if ci:
                need(all(ci.get(k)==identity[k] for k in IMAGE_KEYS),'candidate image binding')
                if 'call_pc' in ci:need(pc(ci['call_pc'])==site[1],'candidate identity call PC')
            call=c.get('call',{})
            if call.get('pc') is not None:need(pc(call['pc'])==site[1],'candidate call PC')
        if a.get('model_version') is not None:need(a['model_version']=='swift-broad-callsite-v1','admission model')
        if a.get('call_pc') is not None:need(pc(a['call_pc'])==site[1],'admission call PC')
        if v:need(v.get('model_version')=='swift-outcome-validation-v2','independent model')
        eligible=v.get('eligible') is True
        need(type(row.get('eligible')) is bool and row['eligible']==eligible,'independent eligibility binding')
        if eligible:
            need(v.get('status')=='eligible_structural_only' and v.get('completeness')==dict(complete=True,missing=[]),'independent completeness')
            need(c.get('completeness')==dict(complete=True,missing=[]) and c.get('eligible') is False,'candidate remains unvalidated claim')
            for key in ('identity','call','abi','cfg','post_call','regions'):
                need(v.get('fact_statuses',{}).get(key)=='checked' and bool(v.get('facts',{}).get(key)),'missing independent '+key)
            for key in ('runtime_branch_proven','call_return_proven','error_state_proven','source_reconstruction_allowed','handler_semantics_proven','exclusive_entry_proven'):
                need(v.get(key) is False,'proof scope '+key)
        raw={r['pc']:r['word'] for block in c.get('cfg',{}).get('blocks',[]) for r in block.get('instructions',[])}
        if eligible:
            need(pc(c['identity'].get('call_pc'))==site[1],'explicit candidate call identity')
            need(pc(c['identity']['caller']['start_pc'])==pc(row.get('caller_pc')),'caller boundary binding')
            need(pc(c['identity']['caller']['start_pc'])<=site[1]<pc(c['identity']['caller']['end_pc_exclusive']),'call within caller')
            need(re.fullmatch('0x[0-9a-f]{8}',c['call'].get('word','')) is not None and raw.get(c['call']['pc'])==c['call']['word'],'exact retained call word')
        for record in row.get('required_challenge_dispositions',[]):
            need(record.get('challenge') in REQUIRED_CHALLENGES,'unknown challenge')
            if record['challenge'] not in SUPPLEMENTAL_CHALLENGES:continue
            if record.get('actual_form_observed') is True:
                need(eligible and record.get('checked_cfg') is True and record.get('disposition')=='observed','unverified observed challenge')
                need(record.get('source_semantics_recovered') is False and record.get('runtime_execution_proven') is False,'challenge proof scope')
                locator=record.get('locator',{})
                need(locator.get('capture')=='supplemental' and locator.get('mode')==row['mode'],'challenge locator')
                need(pc(locator.get('call_pc'))==site[1],'challenge call locator')
                need(bool(record.get('raw_evidence')) and all(e.get('pc') in raw and raw[e['pc']]==e.get('word') for e in record['raw_evidence']),'retained challenge words')
    inventory=challenge_inventory(rows,[],[],capture_role='supplemental',challenges=SUPPLEMENTAL_CHALLENGES)
    need(study.get('required_challenge_inventory')==inventory,'challenge inventory/count/order mismatch')
    need(study.get('state')==('observed' if inventory['complete'] else 'INCOMPLETE'),'state/completeness mismatch')
    return study


def merge_supplemental_challenges(primary,study):
    """Merge only the two scoped challenge entries; no positive/count credit."""
    merged=deepcopy(primary)
    if study is None:return merged
    for key in SUPPLEMENTAL_CHALLENGES:
        supplemental=study['required_challenge_inventory']['entries'][key]
        if not supplemental['observed']:continue
        entry=merged['entries'][key]
        entry['observed']=True
        entry['supplemental_first_study_reuse']=deepcopy(supplemental)
    merged['complete']=all(e['observed'] for e in merged['entries'].values())
    return merged


def observed_features(candidate, validation, admission):
    """Challenge features certified by successful independent replay.

    These deliberately describe emitted structure, never do/catch, defer or try?
    semantics inferred from source labels. Every reported feature maps to its
    physical site in positives_and_declines.
    """
    if not candidate or not validation or not validation.get('eligible'):
        return []
    features=[];post=candidate['post_call'];cfg=candidate['cfg']
    test=int(post['test_word'],16)
    if post.get('test_kind')=='cmp_zero_bcond':
        features.append('compare_zero_eq' if test&15==0 else 'compare_zero_ne')
    else:
        features.append('error_zero_cbz' if test&0x01000000==0 else 'error_nonzero_cbnz')
    if post.get('test_register')!='x21':features.append('error_alias_register')
    words={row['pc']:row for b in cfg['blocks'] for row in b['instructions']}
    if any(words[p]['kind']=='b' for p in post['trace'] if p in words):features.append('direct_postcall_hop')
    if any('stack_slot' in origin for observation in candidate['value_facts']['observations'] for origin in observation.get('origins',[])):
        features.append('error_stack_transport')
    partition=validation.get('region_partition',{})
    if partition.get('shared_pcs'):features.append('shared_return_tail')
    if partition.get('unreachable_pcs'):features.append('unreachable_lexical_words')
    if len(cfg['returns'])>1:features.append('multiple_return_tails')
    if len(cfg['call_return_candidates'])>1:features.append('multiple_caller_calls')
    kinds={r['kind'] for r in words.values()}
    if kinds.intersection(('xstr','wstr','stp')) and kinds.intersection(('xldr','wldr','ldp')):
        features.append('caller_stack_store_reload')
    def operators(value):
        if isinstance(value,list):
            return {value[0]}|set().union(*(operators(v) for v in value[1:])) if value and isinstance(value[0],str) else set().union(*(operators(v) for v in value))
        return set()
    ops=set().union(*(operators(r.get('value')) for r in validation.get('return_observations',[])))
    if ops.intersection(('add','sub','multiply','bitwise_and','xor','arithmetic','derived','xadd','xsub')):
        features.append('return_value_arithmetic')
    if 'zero_extend' in ops:features.append('return_value_zero_extension')
    storage=admission.get('abi',{}).get('result_storage',{})
    locations=storage.get('locations',[])
    if storage.get('indirect'):features.append('indirect_result_storage')
    if any(loc.startswith(('s','d')) and loc[1:].isdigit() for loc in locations):features.append('floating_result_storage')
    if len(locations)>1:features.append('multiregister_result_storage')
    if not locations and storage:features.append('void_result_storage')
    return sorted(set(features))


def classify_raw_words(words,start):
    """Observed ARM64 syntax; never a handler, propagation or dispatch claim."""
    features={};counts=Counter();end=start+4*len(words);calls=[];tests=[];returns=[]
    def add(name,i,word):
        counts[name]+=1
        if len(features.setdefault(name,[]))<8:features[name].append(dict(pc=hex(start+4*i),word=f'0x{word:08x}'))
    for i,word in enumerate(words):
        if word&0xfc000000==0x94000000:calls.append(i);add('raw_direct_bl',i,word)
        elif word&0xfffffc1f==0xd63f0000:calls.append(i);add('raw_indirect_blr',i,word)
        if word&0xfffffc1f==0xd61f0000:add('raw_indirect_tail_br',i,word)
        if word&0xffe0001f==0xd4200000:add('raw_trap_brk',i,word)
        if word&0x7e00001f==0x34000015:
            tests.append(i);add('raw_error_cbnz' if word&0x01000000 else 'raw_error_cbz',i,word)
        if word&0xffffffe0==0xaa1503e0:add('raw_error_alias_mov',i,word)
        if word in (0xd2800015,0xaa1f03f5):add('raw_error_clear',i,word)
        if word&0xfffffc1f==0xd65f0000:returns.append(i)
        if word&0xfc000000==0x14000000:
            offset=word&0x03ffffff
            if offset&0x02000000:offset-=0x04000000
            target=start+4*i+4*offset
            if not start<=target<end:add('raw_direct_tail_escape',i,word)
    call_set=set(calls);return_set=set(returns);test_set=set(tests)
    later_return=False;later_test=False
    for i in range(len(words)-1,-1,-1):
        if i in call_set and later_return and not later_test:
            add('lexical_call_and_later_ret_without_error_test',i,words[i])
        if i in return_set:later_return=True
        if i in test_set:later_test=True
    return [dict(feature=name,occurrences=counts[name],evidence=features[name],
        scope='lexical_instruction_syntax_only_not_reachability') for name in sorted(features)]


def caller_transfer_inventory(words,start):
    """Every call or escaping branch, independent of source intent/index names."""
    rows=[];end=start+4*len(words)
    for i,w in enumerate(words):
        pc=start+4*i;kind=None;target=None
        if w&0xfc000000 in (0x94000000,0x14000000):
            delta=w&0x3ffffff
            if delta&0x2000000:delta-=0x4000000
            target=pc+4*delta
            if w&0x80000000:kind='direct_call'
            elif not start<=target<end:kind='direct_escape'
        elif w&0xfffffc1f in (0xd63f0000,0xd61f0000):kind='unresolved_indirect'
        elif w&0xfe000000==0xd6000000 and w&0xfffffc1f!=0xd65f0000:kind='unresolved_control_encoding'
        elif w&0x7e000000==0x34000000 or w&0xff000000==0x54000000:
            delta=(w>>5)&0x7ffff
            if delta&0x40000:delta-=0x80000
            target=pc+4*delta
            if not start<=target<end:kind='conditional_escape'
        elif w&0x7e000000==0x36000000:
            delta=(w>>5)&0x3fff
            if delta&0x2000:delta-=0x4000
            target=pc+4*delta
            if not start<=target<end:kind='conditional_escape'
        if kind:rows.append(dict(pc=hex(pc),word=f'0x{w:08x}',kind=kind,
            target_pc=hex(target) if target is not None else None))
    return rows


def owned_source_target_inventory(image,cases,budget):
    """Conservative source-symbol/entry mapping from the admitted image.

    Unsupported same-name compiler forms make the mapping incomplete rather
    than silently assuming they cannot be another target of the source callee.
    """
    from airs.swift_declaration_profiles import parse_broad_declaration
    tokens={c['raw_symbol_token']:c['case_id'] for c in cases if isinstance(c.get('raw_symbol_token'),str)}
    mapped_case_ids=set(tokens.values())
    result={c['case_id']:dict(complete=c['case_id'] in mapped_case_ids,targets=[]) for c in cases}
    for fn in image.functions:
        name=fn.name or '';match=re.search(r'broad_case_[0-9]{4}',name)
        if not match or match.group(0) not in tokens:continue
        cid=tokens[match.group(0)];cost=len(name)+256
        if not budget.reserve('absence_symbol_mapping',cost):result[cid]['complete']=False;continue
        parsed=parse_broad_declaration(name)
        budget.charge('absence_symbol_mapping',cost,cost)
        if (fn.boundary_source!='lc_function_starts' or not parsed.supported
                or parsed.identity.function_name!=match.group(0)):
            result[cid]['complete']=False;continue
        result[cid]['targets'].append(dict(pc=hex(fn.start),symbol=name,boundary_source=fn.boundary_source))
    return result


def source_callee_absence_observation(case,link,scan,index_calls_by_pc,target_mapping):
    """Direct source-callee call absence, including unrelated runtime BLs.

    This is an observational absence contract. It does not prove why code was
    optimized, inlined, or reached. Unknown indirect/escaping targets fail closed.
    """
    reason=None;targets={t['pc'] for t in target_mapping.get('targets',[])}
    if not case.get('inline_absence_challenge') or link.get('source_geometry')!='inline_absence_challenge':
        reason='no_inline_absence_source_intent'
    elif not target_mapping.get('complete') or not targets:reason='source_callee_target_mapping_incomplete'
    elif not scan or scan.get('complete') is not True or scan.get('control_transfer_inventory_complete') is not True:
        reason='caller_byte_coverage_incomplete'
    else:
        by_pc=index_calls_by_pc
        for transfer in scan.get('control_transfers',[]):
            if transfer['kind']!='direct_call':reason='unresolved_or_escaping_potential_target';break
            if transfer['target_pc'] in targets:reason='owned_source_callee_call_present';break
            indexed=by_pc.get(transfer['pc'])
            if (not indexed or indexed.get('instruction_word')!=transfer['word']
                    or indexed.get('target_pc')!=transfer['target_pc']
                    or indexed.get('call_kind')!='direct'):
                reason='direct_call_index_mapping_incomplete';break
            if case['case_id'] in indexed.get('owned_target_case_ids',[]):
                reason='independent_index_reports_source_callee';break
    return dict(feature='owned_source_callee_call_absence',case_id=case['case_id'],
        complete=reason is None,reason=reason or 'complete_caller_has_no_direct_source_callee_transfer',
        source_callers=[link],absence_callers=[scan] if scan else [],source_callee_target_mapping=target_mapping,
        source_semantics_recovered=False,inlining_cause_proven=False)


def index_absence_observations(cases):
    # Exact index observation only: never infer optimization, inlining, a tail
    # call or a source construct from the absence of an owned call.
    return [dict(case_id=row['case_id'],feature='indexed_owned_call_absence',
        disposition='unconfirmed_owned_call_absence_not_inlining_proof')
        for row in cases if row.get('confirmed_owned_target_calls')==0
        and row.get('actual_call_instructions')==0
        and row.get('emission_status')=='optimized_away_or_no_owned_call_observed']


def scan_source_callers(image,caller_tokens,budget):
    """Yield one bounded record at a time, before aggregate retention admission."""
    for fn in image.functions:
        name=fn.name or ''
        if not budget.reserve('caller_selection',len(name)+1):
            yield dict(caller_pc=hex(fn.start),complete=False,reason='caller_selection_work_limit')
            return
        budget.charge('caller_selection',len(name)+1,len(name)+1)
        token=re.search(r'broad_caller_[0-9]{4}_[0-9]+',name)
        if not token or token.group(0) not in caller_tokens:continue
        if fn.size<=0 or fn.size%4 or fn.size//4>4096:
            yield dict(caller_pc=hex(fn.start),complete=False,reason='raw_caller_instruction_limit')
            continue
        # Forward classification, reverse suffix classification and a complete
        # transfer-inventory pass. No uncharged call-by-return cross product.
        count=fn.size//4;work=3*count
        if not budget.reserve('raw_caller_words',work):
            yield dict(caller_pc=hex(fn.start),complete=False,reason='raw_caller_word_work_limit')
            continue
        raw=image.bytes_at(fn.start,fn.size)
        words=struct.unpack('<'+'I'*count,raw)
        facts=classify_raw_words(words,fn.start)
        transfers=caller_transfer_inventory(words,fn.start)
        budget.charge('raw_caller_words',work,work)
        yield dict(caller_pc=hex(fn.start),caller_token=token.group(0),complete=True,features=facts,
            word_count=count,control_transfer_inventory_complete=True,control_transfers=transfers,call_instruction_count=sum(f['occurrences'] for f in facts if
                f['feature'] in ('raw_direct_bl','raw_indirect_blr')),
            extent_evidence=[dict(pc=hex(fn.start+4*i),word=f'0x{words[i]:08x}') for i in sorted({0,count-1})])


def stratified_select(rows, count=100):
    buckets = defaultdict(list)
    for row in rows:
        buckets[(row['capture'], row['mode'], row['family'] or 'unproven', row['geometry'] or 'unavailable', row['lowering'])].append(row)
    for values in buckets.values():
        values.sort(key=lambda r: (r['call_pc'], r['target_pc']))
    selected = []
    keys = sorted(buckets)
    while len(selected) < count:
        progressed = False
        for key in keys:
            if buckets[key]:
                selected.append(buckets[key].pop(0)); progressed = True
                if len(selected) == count:
                    break
        if not progressed:
            break
    return selected


def analyze_call(image, fn, pc, *, session=None,image_ledger=None):
    from airs.swift_callsite_admission import admit_callsite_capability
    from airs.swift_declaration_profiles import parse_broad_declaration
    from airs.swift_abi_profiles import admit_swift_abi, ABICallsiteQualification, STABLE_ARM64_SWIFT6
    from airs.swift_outcome_witness_v2 import build_broad_swift_witness
    from airs.swift_outcome_validator_v2 import validate_broad_swift_witness
    from airs.swift_callsite_admission import CallsiteLimits,CallsiteSessionError
    try:
        capability = admit_callsite_capability(image,fn,pc,limits=CallsiteLimits(max_work=2_000_000),session=session)
        admission = capability.record()
    except CallsiteSessionError as error:
        return dict(status='unresolved',reason='callsite_capability:'+error.reason,
            details_complete=False,work_steps=error.work_steps),None,None,None
    decl = None
    candidate = validation = None
    if admission['status'] == 'admitted_callsite':
        parsed = parse_broad_declaration(admission['symbol'])
        decl = parsed.identity if parsed.supported else None
        request=ABICallsiteQualification(STABLE_ARM64_SWIFT6.identifier,pc,fn.start,admission['callee_pc'],callsite_capability=capability)
        admission['abi'] = admit_swift_abi(image, decl, qualification=request) if decl else {'status': 'unresolved', 'reason': 'syntax_unqualified'}
        # Authored synthetic fixtures exercise the separate reviewed registry.
        if image.path.startswith('qualification synthetic') and decl:
            admission['abi'] = admit_swift_abi(image, decl)
        wire_admission=public(admission)
        candidate = build_broad_swift_witness(image, fn, wire_admission)
        validation = validate_broad_swift_witness(image,fn,candidate,**(
            {'_image_ledger':image_ledger} if image_ledger is not None else {}))
    return admission, decl, candidate, validation


def raw_negatives():
    """Fresh tiny Mach-O admissions, not stale parser-custody-only mutations.

    A private matching observation is supplied only for the unchanged RET callee
    in this authored synthetic fixture. The changed caller never inherits a real
    compiler receipt. Producer output is attacked; validator remains independent.
    """
    from airs.macho import parse_macho
    from airs.swift_abi_profiles import LoweringObservation
    from airs.swift_outcome_validator_v2 import validate_broad_swift_witness
    data = bytearray(1024); symbol = '$s4Test3fooyS2iKF'
    struct.pack_into('<IiiIIIII',data,0,0xfeedfacf,0x100000c,0,2,3,192,0,0)
    struct.pack_into('<II16sQQQQiiII',data,32,0x19,152,b'__TEXT',0xf00,8192,0,1024,7,5,1,0)
    struct.pack_into('<16s16sQQIIIIIIII',data,104,b'__text',b'__TEXT',0x1000,32,256,2,0,0,0x80000400,0,0,0)
    strings=b'\0_'+symbol.encode()+b'\0'
    struct.pack_into('<IIIIII',data,184,2,24,512,1,768,len(strings))
    struct.pack_into('<IIII',data,208,0x26,16,900,4)
    data[900:904]=b'\x80\x02\x10\0'
    struct.pack_into('<IBBHQ',data,512,1,15,1,0,0x1010);data[768:768+len(strings)]=strings
    for i,w in enumerate([0x94000004,0xb4000055,0xd65f03c0,0xd65f03c0]+[0xd65f03c0]*4):
        struct.pack_into('<I',data,256+4*i,w)
    base=parse_macho(bytes(data),'qualification synthetic original')
    q=LoweringObservation('qualification-synthetic-ret',base.slice_sha256,'authored-synthetic','authored fixture',
        'arm64-apple-macosx14.0','synthetic',symbol,('Swift.Int',),'Swift.Int',('x0',),'x0',
        ((0x1010,'c0035fd6','unchanged authored return'),),'script:raw_negatives','script:raw_negatives')
    with patch('airs.swift_abi_profiles.LOWERING_QUALIFICATIONS',MappingProxyType({q.evidence_id:q})):
        baseline_admission,_,candidate,verdict=analyze_call(base,base.functions[0],0x1000)
        baseline_work=unit_work(baseline_admission,candidate,verdict)+len(data)
    if not verdict or not verdict.get('eligible'):
        return [dict(attack='synthetic_prerequisite',eligible=False,executed=False,reason=(verdict or {}).get('reason'))]
    results=[]
    # Each changes actual instruction geometry. All are parsed as newly admitted
    # inputs, with coordinated identity/raw retained facts, but stale CFG claims.
    for off,word in ((256,0x94000005),(260,0xb5000055),(260,0xb4000075),
                     (260,0xb4000054),(264,0xd503201f),(264,0xd2800020),
                     (268,0xd503201f),(268,0xd2800040)):
        changed=bytearray(data);struct.pack_into('<I',changed,off,word)
        image=parse_macho(bytes(changed),f'qualification fresh {off:x}-{word:x}')
        claim=deepcopy(candidate)
        claim['identity'].update(slice_sha256=image.slice_sha256,container_sha256=image.container_sha256)
        if off==256:
            claim['call']['word']=f'0x{word:08x}';claim['call']['provenance']['call']['word']=f'0x{word:08x}'
        elif off==260:
            claim['post_call']['test_word']=f'0x{word:08x}'
        seal_size(claim)
        matched=replace(q,slice_sha256=image.slice_sha256)
        with patch('airs.swift_abi_profiles.LOWERING_QUALIFICATIONS',MappingProxyType({q.evidence_id:matched})):
            result=validate_broad_swift_witness(image,image.functions[0],claim)
        results.append(dict(attack='rawcall' if off==256 else ('polarity' if off==260 else 'CFG'),raw_coordinate=f'{off:x}:{word:x}',executed=True,
            admission_fresh=image.has_valid_admission(),callee_unchanged=True,
            eligible=result.get('eligible',False),reason=result.get('reason'),
            work_steps=result.get('accounting',{}).get('work',0)+result.get('accounting',{}).get('image_work_charged_here',0)+len(data)+(baseline_work if not results else 0)))
    return results


def negative_plan(positives,maximum=280):
    """Reserve seven family controls inside, never on top of, the 280 units."""
    if maximum< len(FAMILIES):raise ValueError('negative plan cannot reserve family controls')
    ordered=sorted(positives,key=lambda r:(r['capture'],r['mode'],r['call_pc']))
    plan=[];used=set();pools=defaultdict(list)
    family_path=('call','declaration','identity','callable_kind')
    for family in FAMILIES:
        row=next((r for r in ordered if r['capture']=='primary' and r.get('family')==family
            and family_path in set(semantic_mutations(r['_context'][2]))),None)
        if row is not None:
            plan.append(('dispatch',row,family_path,True))
            used.add((id(row),family_path))
    global_paths={family_path} if plan else set()
    for row in ordered:
        for path in semantic_mutations(row['_context'][2]):
            if (id(row),path) in used or path in global_paths:continue
            kind=attack_kind(path)
            if len(pools[kind])>=maximum:continue
            global_paths.add(path);pools[kind].append((row,path))
    while len(plan)<maximum:
        advanced=False
        for kind in sorted(pools):
            if pools[kind]:
                row,path=pools[kind].pop(0);plan.append((kind,row,path,False));advanced=True
                if len(plan)==maximum:break
        if not advanced:break
    return plan


def run(args,metrics=None):
    metrics=metrics or PerformanceMeasurements()
    from airs.swift_owned_image import load_owned_swift_image
    from airs.swift_outcome_validator_v2 import create_independent_swift_image_ledger
    from airs.swift_callsite_admission import create_callsite_session,CallsiteLimits,CallsiteSessionError
    from airs.swift_outcome_validator_v2 import validate_broad_swift_witness
    source_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dirty=subprocess.check_output(['git','diff','--name-only','HEAD','--','src','tests','scripts','schemas','docs'],cwd=ROOT,text=True).strip()
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','--','src','tests','scripts','schemas','docs'],cwd=ROOT,text=True).strip()
    if dirty or untracked:
        raise ValueError('Commit final source before qualification; source/review identity must be exact')
    if len(args.review)!=2:
        raise ValueError('Exactly two whole-branch review records are required before final execution')
    review_inputs=[read_bounded_json(p,max_bytes=1024*1024,max_tokens=20000) for p in args.review]
    if any(r.get('source_revision')!=source_revision for r in review_inputs):
        raise ValueError('Whole-branch reviews must bind current committed source revision')
    if (len({r.get('reviewer') for r in review_inputs})!=2 or any(
            r.get('scope')!='whole_broad_branch' or r.get('decision')!='passed'
            or r.get('unresolved_findings')!=[] or not isinstance(r.get('correction_history'),list)
            or not r.get('reviewer') for r in review_inputs)):
        raise ValueError('Two independent passed whole-branch reviews with correction history are required')
    supplemental_study=None
    if getattr(args,'supplemental_study',None) is not None:
        supplemental_study=validate_supplemental_study(read_bounded_json(args.supplemental_study,
            max_bytes=4*1024*1024,max_tokens=200000,max_depth=48),source_revision)
    captures=[('primary',args.capture.resolve()),('second',args.second_capture.resolve())]
    if captures[0][1]==captures[1][1]:raise ValueError('Distinct capture directories are required')
    capture_inputs=[];compiler_evidence={};capture_prerequisites={}
    for capture,directory in captures:
        manifest=read_bounded_json(directory/'source-manifest.json',max_bytes=4*1024*1024)
        index=read_bounded_json(directory/'compiler-index.json',max_tokens=2_000_000)
        receipt=read_bounded_json(directory/'compile-receipt.json',max_bytes=1024*1024,max_tokens=20000)
        capture_prerequisites[capture]=validate_capture_prerequisites(capture,manifest,index,receipt)
        compiler_evidence[capture]=compiler_identity(directory,receipt)
        capture_inputs.append((capture,directory,manifest,index,receipt))
    if not distinct_compilers(compiler_evidence['primary'],compiler_evidence['second']):
        raise ValueError('Distinct capture directories, compiler paths and compiler versions are required')
    output=args.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    # A single marker covers partial/crashed passes. No overwrite/resume option.
    marker=output/'FINAL-PASS-STARTED.json'
    with marker.open('x') as stream:
        json.dump(dict(schema='airs.swift-broad-final-start.v1',argv=sys.argv,
            authorization='one final qualification pass; 300 negatives and 100 repeats maximum',
            no_repeat=True,source_revision=source_revision),stream,indent=2)
    positives=[];all_rows=[];contexts={};index_counts={};source={};reasons=Counter();source_challenge_presence=set();observed_challenges=set();work_budget=WorkBudget();retention=RetentionBudget();sessions={};session_failures={};independent_ledgers={};ledger_failures={};raw_challenges=[];raw_scan_complete=True;unsupported_dispositions=[];selected_counts={}
    for capture,directory,manifest,index,receipt in capture_inputs:
        source[capture]=dict(cases=manifest['cases'],generator=manifest['generator_version'],
            source_sha256=receipt['source_sha256'],provenance='reused existing compiler/source/index receipt; no hashes or recompilation')
        seen=set();index_counts[capture]=0;selected_counts[capture]=0
        challenge_callers={site['caller']:dict(case_id=case['case_id'],caller=site['caller'],
            source_geometry=site['geometry'],source_line=site.get('source_line'))
            for case in manifest['cases'] for site in case['source_callsites']}
        for mode,mode_index in sorted(index['modes'].items()):
            entry=receipt['modes'][mode]
            image=metrics.call('owned_image',load_owned_swift_image,directory/entry['library'],directory/'compile-receipt.json',mode)
            contexts[(capture,mode)]=image
            raw_by_caller={}
            owned_targets=owned_source_target_inventory(image,manifest['cases'],work_budget)
            for raw_row in scan_source_callers(image,set(challenge_callers),work_budget):
                raw_scan_complete=raw_scan_complete and raw_row['complete']
                raw_row.update(capture=capture,mode=mode,source_callers=source_caller_links([raw_row.get('caller_token','')],challenge_callers),
                    image_identity=dict(slice_sha256=image.slice_sha256,container_sha256=image.container_sha256,uuid=image.uuid,slice_index=image.slice_index))
                raw_row['required_challenge_dispositions']=required_challenge_dispositions(raw_row)
                if retention.admit(raw_row,kind="raw_challenge_record"):
                    raw_challenges.append(raw_row)
                    if raw_row.get('caller_token'):raw_by_caller[raw_row['caller_token']]=raw_row
                    if capture=='primary':observed_challenges.update(f['feature'] for f in raw_row.get('features',[]))
                else:raw_scan_complete=False
            absences=index_absence_observations(mode_index.get('cases',[]))
            for absent in absences:
                links=[x for x in challenge_callers.values() if x['case_id']==absent['case_id']]
                absent.update(capture=capture,mode=mode,source_callers=links,
                    image_identity=dict(slice_sha256=image.slice_sha256,container_sha256=image.container_sha256,uuid=image.uuid,slice_index=image.slice_index),
                    absence_callers=[{k:raw_by_caller[x['caller']].get(k) for k in
                        ('caller_pc','caller_token','complete','call_instruction_count','extent_evidence')}
                        for x in links if x['caller'] in raw_by_caller])
                absent['required_challenge_dispositions']=required_challenge_dispositions(absent)
                if retention.admit(absent,kind="indexed_absence_record"):
                    raw_challenges.append(absent)
                    if capture=='primary':observed_challenges.add(absent['feature'])
                else:raw_scan_complete=False
            absence_index_calls={};ambiguous_index_pcs=set()
            for indexed_call in mode_index['calls']:
                cost=len(indexed_call.get('pc',''))+1
                if not work_budget.reserve('absence_index_mapping',cost):continue
                work_budget.charge('absence_index_mapping',cost,cost)
                pc=indexed_call.get('pc')
                if pc in absence_index_calls:ambiguous_index_pcs.add(pc)
                absence_index_calls[pc]=indexed_call
            for pc in ambiguous_index_pcs:absence_index_calls.pop(pc,None)
            for case in manifest['cases']:
                if not case.get('inline_absence_challenge'):continue
                for site in case['source_callsites']:
                    if site['geometry']!='inline_absence_challenge':continue
                    link=challenge_callers[site['caller']]
                    absent=source_callee_absence_observation(case,link,raw_by_caller.get(site['caller']),
                        absence_index_calls,owned_targets[case['case_id']])
                    absent.update(capture=capture,mode=mode,
                        image_identity=dict(slice_sha256=image.slice_sha256,container_sha256=image.container_sha256,uuid=image.uuid,slice_index=image.slice_index))
                    absent['required_challenge_dispositions']=required_challenge_dispositions(absent)
                    if retention.admit(absent,kind='source_callee_absence_record'):raw_challenges.append(absent)
                    else:raw_scan_complete=False
            if work_budget.reserve('callsite_session',2_000_000):
                try:
                    sessions[(capture,mode)]=metrics.call('callsite_session',create_callsite_session,image,limits=CallsiteLimits(max_work=2_000_000))
                    work_budget.charge('callsite_session',sessions[(capture,mode)].initial_work_steps,2_000_000)
                except CallsiteSessionError as error:
                    work_budget.charge('callsite_session',error.work_steps,2_000_000)
                    session_failures[(capture,mode)]=error.reason
            else:session_failures[(capture,mode)]='aggregate_work_reservation'
            # A separate validator-owned raw ledger is never built from B5
            # session/capability records or producer facts.
            if work_budget.reserve('independent_image_ledger',262_144):
                ledger=metrics.call('independent_image_ledger',create_independent_swift_image_ledger,image,max_work=262_144)
                work_budget.charge('independent_image_ledger',ledger.initial_work_steps,262_144)
                independent_ledgers[(capture,mode)]=ledger
                if ledger.status!='ready':ledger_failures[(capture,mode)]=ledger.reason
            else:ledger_failures[(capture,mode)]='aggregate_work_reservation'
            for record in mode_index['calls']:
                confirmed=record.get('owned_target_confirmed') is True
                indirect_source=record.get('source_call_candidate') is True and record.get('call_kind')=='indirect'
                if not (confirmed or indirect_source):continue
                pc=int(record['pc'],16)
                if (mode,pc) in seen:
                    continue
                seen.add((mode,pc));index_counts[capture]+=int(confirmed);selected_counts[capture]+=1
                record_links=source_caller_links(record.get('caller_aliases_nm',[]),challenge_callers)
                if capture=='primary':
                    source_challenge_presence.update(link['source_geometry'] for link in record_links)
                matches=[f for f in image.functions if f.start<=pc<f.end]
                if len(matches)!=1:
                    row=dict(capture=capture,mode=mode,call_pc=pc,status='declined',reason='indexed_caller_boundary_unavailable')
                    all_rows.append(row);reasons[row['reason']]+=1;continue
                fn=matches[0]
                if (capture,mode) in session_failures:
                    all_rows.append(dict(capture=capture,mode=mode,call_pc=pc,status='unresolved',reason='callsite_session:'+session_failures[(capture,mode)],eligible=False));continue
                if (capture,mode) in ledger_failures:
                    all_rows.append(dict(capture=capture,mode=mode,call_pc=pc,status='unresolved',reason='independent_image_ledger:'+str(ledger_failures[(capture,mode)]),eligible=False));continue
                if not work_budget.reserve('physical_call',5_000_000):
                    all_rows.append(dict(capture=capture,mode=mode,call_pc=pc,status='unresolved',reason='aggregate_work_reservation',eligible=False));continue
                admission,decl,candidate,validation=metrics.call('physical_call',analyze_call,image,fn,pc,session=sessions[(capture,mode)],image_ledger=independent_ledgers[(capture,mode)])
                work_budget.charge('physical_call',unit_work(admission,candidate,validation),5_000_000)
                verdict=validation or admission
                if indirect_source:
                    raw_word=int.from_bytes(image.bytes_at(pc,4),'little')
                    disposition=dict(capture=capture,mode=mode,call_pc=hex(pc),
                        raw_indirect_verified=raw_word&0xfffffc1f==0xd63f0000 and record.get('instruction_word')==f'0x{raw_word:08x}',
                        eligible=verdict.get('eligible',False),status=verdict.get('status'),reason=verdict.get('reason'))
                    if retention.admit(disposition,kind='unsupported_disposition_record'):unsupported_dispositions.append(disposition)
                    else:raw_scan_complete=False
                row=dict(capture=capture,mode=mode,call_pc=pc,target_pc=record.get('target_pc'),
                    caller_pc=hex(fn.start),source_callers=record_links or source_caller_links([fn.name or ''],challenge_callers),
                    confirmed_owned_target=confirmed,indexed_indirect_source_candidate=indirect_source,
                    index_case_ids=record.get('owned_target_case_ids',[]),
                    source_intent_only=True,status=verdict.get('status'),reason=verdict.get('reason'),
                    eligible=verdict.get('eligible',False),admission=public(admission),
                    candidate=public(candidate),validation=public(validation),family=None,shape=None,
                    geometry=None,lowering=None)
                if decl is not None and admission.get('abi',{}).get('status')=='admitted':
                    row['shape']=emitted_shape(decl,admission['abi'])
                if verdict.get('eligible'):
                    row.update(family=declaration_family(decl,admission['abi']),
                        geometry=geometry(candidate,validation),
                        lowering=canonical(admission['abi'].get('result_storage') or dict(type=asdict(decl.result_type),
                            location=admission['abi'].get('result_location'))),
                        family_basis=public(admission['abi'].get('family_evidence',{})))
                    row['geometry_disposition']='checked_selected_outcome' if row['geometry'] is not None else 'incomplete_selected_geometry_contract'
                    row['selected_error_transport']='register_alias' if candidate.get('post_call',{}).get('test_register')!='x21' else 'direct'
                    # Runtime-only context never serialized as evidence authority.
                    pass  # Retain runtime context only after aggregate admission.
                row['observed_emitted_challenges']=observed_features(candidate,validation,admission)
                row['required_challenge_dispositions']=required_challenge_dispositions(row)
                extra=dict(candidate=candidate,admission=public(admission)) if verdict.get('eligible') else None
                if not retention.admit(row,extra):
                    all_rows.append(dict(capture=capture,mode=mode,call_pc=pc,eligible=False,status='unresolved',reason='aggregate_retained_output_limit'));continue
                if verdict.get('eligible'):
                    row['_context']=(image,fn,candidate,public(admission));positives.append(row)
                if capture=='primary':observed_challenges.update(row['observed_emitted_challenges'])
                reasons[row['reason']]+=1;all_rows.append(row)
                if len(all_rows)>10000:
                    raise ValueError('physical-call bound exceeded')
    reconcile_nested_challenges(all_rows,work_budget,retention)
    # Candidate paths are stratified by independent claim domain before any
    # negative validation. No acceptance/failure drives adaptive retry work.
    plan=negative_plan(positives)
    negatives=[]
    for kind,row,path,family_control in plan:
        image,fn,candidate,_=row['_context']
        if not work_budget.reserve('retained_negative',65_536):
            negatives.append(dict(attack=kind,executed=False,eligible=False,reason='aggregate_work_reservation'));continue
        verdict=metrics.call('retained_negative',validate_broad_swift_witness,image,fn,delete_claim(candidate,path),
            _image_ledger=independent_ledgers[(row['capture'],row['mode'])])
        work_budget.charge('retained_negative',verdict.get('accounting',{}).get('work',0),65_536)
        negatives.append(dict(attack=kind,path=list(path),executed=True,
            family=row.get('family'),family_control=family_control,
            call=dict(capture=row['capture'],mode=row['mode'],pc=hex(row['call_pc'])),
            eligible=verdict.get('eligible',False),reason=verdict.get('reason')))
    if positives:
        from airs.swift_outcome_witness_v2_models import BroadWitnessLimits
        image,fn,candidate,_=positives[0]['_context']
        negative_ledger=independent_ledgers[(positives[0]['capture'],positives[0]['mode'])]
        for field in ('max_instructions','max_blocks','max_edges','max_work','max_depth',
                      'max_state_entries','max_provenance_nodes','max_container_items',
                      'max_string','max_bytes','post_call_window'):
            if not work_budget.reserve('limit_negative',65_536):
                negatives.append(dict(attack='worklimits' if field=='max_work' else 'truncation',executed=False,eligible=False,reason='aggregate_work_reservation'));continue
            verdict=metrics.call('limit_negative',validate_broad_swift_witness,image,fn,candidate,
                limits=replace(BroadWitnessLimits(),**{field:0}),_image_ledger=negative_ledger)
            work_budget.charge('limit_negative',verdict.get('accounting',{}).get('work',0),65_536)
            negatives.append(dict(attack='worklimits' if field=='max_work' else 'truncation',
                limit=field,executed=True,eligible=verdict.get('eligible',False),reason=verdict.get('reason')))
        data=bytearray(image.data);data[0]^=1
        if work_budget.reserve('custody_negative',65_536):
            verdict=metrics.call('custody_negative',validate_broad_swift_witness,replace(image,data=bytes(data)),fn,candidate,_image_ledger=negative_ledger)
            work_budget.charge('custody_negative',verdict.get('accounting',{}).get('work',0),65_536)
            negatives.append(dict(attack='custody',executed=True,eligible=verdict.get('eligible',False),reason=verdict.get('reason')))
        else:negatives.append(dict(attack='custody',executed=False,eligible=False,reason='aggregate_work_reservation'))
    if work_budget.reserve('fresh_synthetic_group',8_000_000):
        raw_results=metrics.call('fresh_synthetic_group',raw_negatives);negatives.extend(raw_results)
        work_budget.charge('fresh_synthetic_group',sum(r.get('work_steps',0) for r in raw_results),8_000_000)
    else:
        negatives.append(dict(attack='fresh_raw',executed=False,eligible=False,reason='aggregate_work_reservation'))
    # Stratification is deterministic and retained explicitly. A comparison
    # repeats admission+construction+independent replay once, never a third run.
    repeat_rows=stratified_select(positives)
    repeats=[]
    for row in repeat_rows:
        image,fn,candidate,admission=row['_context']
        if not work_budget.reserve('repeat_comparison',5_000_000):
            repeats.append(dict(capture=row['capture'],mode=row['mode'],call_pc=hex(row['call_pc']),identical=False,executed=False,reason='aggregate_work_reservation'));continue
        a,_,c,v=metrics.call('repeat_comparison',analyze_call,image,fn,row['call_pc'],session=sessions[(row['capture'],row['mode'])],
            image_ledger=independent_ledgers[(row['capture'],row['mode'])])
        work_budget.charge('repeat_comparison',unit_work(a,c,v),5_000_000)
        expected=dict(admission=public(admission),candidate=public(candidate),validation=row['validation'])
        actual=dict(admission=public(a),candidate=public(c),validation=public(v))
        repeats.append(dict(capture=row['capture'],mode=row['mode'],call_pc=hex(row['call_pc']),
            strata=dict(family=row['family'],geometry=row['geometry'],lowering=row['lowering']),
            identical=canonical(expected)==canonical(actual)))
    reviews=[]
    for path in args.review:
        reviews.append(dict(path=str(path.resolve()),record=review_inputs[len(reviews)]))
    families=Counter(r['family'] for r in positives if r['capture']=='primary' and r['family'])
    shapes={r['shape'] for r in all_rows if r.get('shape') and r['capture']=='primary'}
    geometries={r['geometry'] for r in positives if r['capture']=='primary' and r['geometry'] is not None}
    lowerings={r['lowering'] for r in positives if r['capture']=='primary'}
    # An observed source challenge is matched to an actual independently indexed
    # call. It remains source-labelled challenge coverage, never emitted geometry.
    primary_cases={c['case_id']:c for c in source['primary']['cases']}
    source_counts=source_inventory(source['primary']['cases'])
    required_challenges=merge_supplemental_challenges(
        challenge_inventory(all_rows,raw_challenges,source['primary']['cases']),supplemental_study)
    measurements=metrics.snapshot()
    negative_families=Counter(n['family'] for n in negatives if n.get('family_control') and n.get('executed')
        and not n['eligible'] and n.get('call',{}).get('capture')=='primary')
    observed_case_ids={c for r in all_rows if r['capture']=='primary' for c in r.get('index_case_ids',[])}
    challenges=observed_challenges
    review_ok=[r for r in reviews if r['record'].get('scope')=='whole_broad_branch'
        and r['record'].get('decision')=='passed' and r['record'].get('unresolved_findings')==[]
        and r['record'].get('reviewer') and r['record'].get('source_revision')==source_revision
        and isinstance(r['record'].get('correction_history'),list)]
    gates={
        'aggregate_work_complete':not work_budget.omitted,
        'aggregate_retained_output_complete':not retention.omitted,
        'raw_compiler_challenge_scan_complete':raw_scan_complete,
        'unsupported_compiler_forms_disposition':bool(unsupported_dispositions) and all(r['raw_indirect_verified'] and not r['eligible'] for r in unsupported_dispositions),
        'required_unsupported_challenges_observed':{'raw_indirect_blr','raw_direct_tail_escape','raw_trap_brk','lexical_call_and_later_ret_without_error_test','indexed_owned_call_absence'} <= observed_challenges,
        'callsite_sessions_complete':not session_failures,
        'independent_image_ledgers_complete':not ledger_failures,
        'source_420':len(primary_cases)>=420,
        'source_methods_340':sum(c['category']!='free' for c in primary_cases.values())>=340,
        'source_category_minima':source_counts['categories_complete'],
        'source_diversity_reconciled':source_counts['diversity_reconciled'],
        'emitted_abi_shapes_80':len(shapes)>=80,
        'physical_calls_1500':index_counts['primary']>=1500,
        'eligible_primary_witnesses_250':sum(r['capture']=='primary' for r in positives)>=250,
        'seven_families_15_each':all(families[f]>=15 for f in FAMILIES),
        'positive_emitted_geometries_10':len(geometries)>=10,
        'observed_emitted_challenges_12':required_challenges['complete'],
        'result_lowerings_8':len(lowerings)>=8,
        'negative_300_zero_false_eligible':len(negatives)>=300 and all(n.get('executed') and not n['eligible'] for n in negatives),
        'fresh_raw_coordinate_attacks':sum(n.get('admission_fresh',False) for n in negatives)>=8,
        'negative_attack_kind_coverage':set(('identity','custody','rawcall','posttest','polarity','CFG','entry','nominal','ABI','valueattachment','truncation','worklimits','dispatch','proofscope')) <= {n['attack'] for n in negatives if n.get('executed')},
        'seven_family_negative_controls':all(negative_families[f]>=1 for f in FAMILIES),
        'stratified_100_identical':len(repeats)==100 and all(r['identical'] for r in repeats),
        'second_compiler_positive':distinct_compilers(compiler_evidence['primary'],compiler_evidence['second']) and any(r['capture']=='second' for r in positives),
        'two_whole_branch_reviews':len({r['record']['reviewer'] for r in review_ok})>=2,
        'measured_latency_rss':measurements['complete'],
    }
    if set(gates)!=MANDATORY_GATES:raise ValueError('qualification gate inventory mismatch')
    for row in all_rows:
        row.pop('_context',None)
    report=dict(schema='airs.swift-broad-qualification.v1',source_revision=source_revision,state='qualified' if all(gates.values()) else 'INCOMPLETE',
        gates=gates,counts=dict(source_declarations=len(primary_cases),physical_calls=index_counts,selected_source_call_sites=selected_counts,
            primary_eligible=sum(r['capture']=='primary' for r in positives),families=dict(families),
            emitted_abi_shapes=len(shapes),positive_geometries=len(geometries),
            observed_emitted_challenges=sorted(challenges),source_label_presence_only=sorted(source_challenge_presence),result_lowerings=len(lowerings),
            negatives=len(negatives),negative_family_controls=dict(negative_families),false_eligible=sum(n['eligible'] for n in negatives),repeats=len(repeats)),
        source_inventory=source_counts,required_challenge_inventory=required_challenges,measurements=measurements,
        retained_output_ledger=dict(limit=retention.limit,retained_bytes=retention.used,omitted=dict(retention.omitted),streamed_report_limit=MAX_REPORT_BYTES),compiler_evidence=compiler_evidence,capture_prerequisites=capture_prerequisites,work_ledger=work_budget.report(),reasons=dict(reasons),reuse=source,positives_and_declines=all_rows,
        compiler_challenge_observations=raw_challenges,unsupported_compiler_dispositions=unsupported_dispositions,negatives=negatives,repeats=repeats,reviews=reviews,
        limitations=['structural research only','source challenge labels are not emitted geometry',
            'no runtime reachability, handler/source reconstruction, or clinical claim',
            'B1/B9 native acceptance and final B12 completion require parent ledger evidence'])
    if supplemental_study is not None:
        report['supplemental_capture_evidence']=deepcopy(supplemental_study['supplemental_capture_evidence'])
        report['supplemental_study_reuse']=dict(scope='trusted private historical first-validator receipt; no fresh admission/replay',
            source_revision=supplemental_study['source_revision'],observation_count=supplemental_study['observation_count'],
            not_primary_positive_credit=True,not_second_compiler_credit=True,receipt=supplemental_study)
    write_qualification_outputs(output,report,reviews)
    print(json.dumps(dict(state=report['state'],gates=gates,output=str(output),
        artifact_packaging='pending_separate_sanitized_complete_handback'),indent=2))
    return 0 if all(gates.values()) else 2


def write_qualification_outputs(output,report,reviews):
    """Write private local qualification records; never package raw evidence.

    Original receipts, logs and custody records can contain machine metadata.
    A separate handback step owns complete source export, evidence relocation,
    sanitization and cross-device delivery. This function creates no archive.
    """
    report['artifact_packaging']=dict(state='pending',
        required='separate sanitized complete source and relocated evidence handback',
        local_records='private unrelocated qualification evidence')
    try:
        write_bounded_json(output/'qualification.json',report)
    except JSONBoundError:
        # Preserve the bounded partial; summarize omission without repeating any
        # verification, negative or deterministic comparison unit.
        report['state']='INCOMPLETE';report['gates']['streamed_report_complete']=False
        report['positives_and_declines_omitted']=len(report.pop('positives_and_declines',[]))
        report.pop('reuse',None)
        write_bounded_json(output/'qualification-summary.json',report)
    write_bounded_json(output/'reviews.json',reviews,2*1024*1024)
    (output/'README.txt').write_text('AIRS broad Swift qualification\nState: '+report['state']+'\n'
        'Read qualification.json gates; false gates are incomplete, not waived.\n'
        'Compiler captures and their initial receipts are reused without rehashing.\n'
        'FINAL-PASS-STARTED.json forbids unattended repeat of this authorized pass.\n'
        'Artifact packaging: PENDING separate sanitized complete handback.\n'
        'These private local records are unrelocated and may contain machine metadata.\n')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,required=True,help='Existing trusted primary compiler capture directory')
    parser.add_argument('--second-capture',type=Path,required=True,help='Existing trusted second-toolchain capture directory')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--review',type=Path,action='append',default=[])
    parser.add_argument('--supplemental-study',type=Path,help='Trusted private first-study receipt, exact frozen source revision; two challenges only')
    parser.add_argument('--execute-final',action='store_true',help='Consume the authorized one final pass; never use for readiness checks')
    args=parser.parse_args(argv)
    if not args.execute_final:
        print(json.dumps(dict(state='UNRUN',output=str(args.output),
            required='Parent pipeline readiness plus --execute-final',
            planned=dict(primary=str(args.capture),second=str(args.second_capture),
                max_negative_units=300,repeat_comparisons=100),
            no_compile_no_hash_no_disassembly=True),indent=2))
        return 0
    metrics=PerformanceMeasurements()
    try:
        return run(args,metrics)
    except Exception as error:
        failure=dict(schema='airs.swift-broad-qualification-failure.v1',state='INCOMPLETE',
            failed_action='final qualification',exception_type=type(error).__name__,reason=str(error),
            measurements=metrics.snapshot(),
            next_action='Preserve output and start marker; parent diagnoses before requesting any new execution authorization')
        if (args.output/'FINAL-PASS-STARTED.json').is_file():
            with (args.output/'FAILURE.json').open('x') as stream:json.dump(failure,stream,indent=2)
        print(json.dumps(failure,indent=2),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
