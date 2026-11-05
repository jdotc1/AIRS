"""Shared v2 wire primitives, without producer or validator semantics.

Initial hard ceilings: 256 KiB/witness and 16 MiB/aggregate. Callers collecting
witnesses must charge each encoded byte against the aggregate ceiling before
append. Defaults retain at most 512 instructions, 512 blocks, 2048 edges and a
16-instruction post-call window. No model here certifies eligibility.
"""
from __future__ import annotations
from dataclasses import dataclass, fields
import json

WITNESS_MODEL = 'swift-outcome-witness-v2'
VALIDATION_MODEL = 'swift-outcome-validation-v2'


@dataclass(frozen=True, slots=True)
class BroadWitnessLimits:
    max_instructions: int = 512
    max_blocks: int = 512
    max_edges: int = 2048
    max_work: int = 65536
    max_depth: int = 32
    max_state_entries: int = 64
    max_provenance_nodes: int = 512
    max_container_items: int = 16384
    max_string: int = 2048
    max_bytes: int = 262144
    max_aggregate_bytes: int = 16777216
    post_call_window: int = 16

    def __post_init__(self):
        caps = dict(max_instructions=4096,max_blocks=4096,max_edges=16384,
                    max_work=262144,max_depth=64,max_state_entries=128,
                    max_provenance_nodes=4096,max_container_items=65536,
                    max_string=8192,max_bytes=262144,max_aggregate_bytes=16777216,
                    post_call_window=16)
        for f in fields(self):
            v=getattr(self,f.name)
            if type(v) is not int or not 0 <= v <= caps[f.name]:
                raise ValueError('invalid_broad_witness_limit:'+f.name)


@dataclass(frozen=True, slots=True)
class BroadWitnessIdentity:
    slice_sha256: str
    container_sha256: str
    call_pc: str
    caller_start_pc: str
    callee_start_pc: str


@dataclass(frozen=True, slots=True)
class BroadInstruction:
    pc: str
    word: str
    slice_offset: str
    container_offset: str
    kind: str


def preflight_broad_json(value, *, limits=BroadWitnessLimits()):
    """Iterative pre-allocation bounds; reject cycles, floats and foreign objects.

    The byte estimate is a conservative UTF-8/JSON upper bound, charging keys,
    separators and escaping before calling the standard encoder.
    """
    todo=[(value,0)];items=0;budget=0
    while todo:
        node,depth=todo.pop();items+=1
        if items>limits.max_container_items or depth>limits.max_depth:
            raise ValueError('witness_structure_limit')
        if type(node) in (dict,list,tuple):
            size=len(node)
            if size>limits.max_container_items-items-len(todo):
                raise ValueError('witness_structure_limit')
            budget+=2+size*2
            if type(node) is dict:
                for key,child in node.items():
                    if type(key) is not str or len(key)>limits.max_string:
                        raise ValueError('witness_key_limit')
                    budget+=2+len(key)*6
                    todo.append((child,depth+1))
            else:
                todo.extend((child,depth+1) for child in node)
        elif isinstance(node,str):
            if len(node)>limits.max_string:raise ValueError('witness_string_limit')
            budget+=2+len(node)*6
        elif type(node) is int:
            if not -(1<<64)<=node<(1<<64):raise ValueError('witness_integer_limit')
            budget+=21
        elif node is None or type(node) is bool:budget+=5
        else:raise ValueError('witness_json_type')
        if budget>limits.max_bytes:raise ValueError('witness_byte_limit')
    return items


def encode_broad_witness(value, *, limits=BroadWitnessLimits()):
    preflight_broad_json(value,limits=limits)
    if (type(value) is not dict or value.get('model_version')!=WITNESS_MODEL
            or value.get('status')!='unresolved' or value.get('eligible') is not False):
        raise ValueError('candidate_only_contract')
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
    if len(raw)>limits.max_bytes:raise ValueError('witness_byte_limit')
    return raw


def public_broad_record(value, *, limits=BroadWitnessLimits()):
    """Bounded detached wire copy, excluding process-local custody arrays.

    Skipped bindings are never traversed, copied or converted to authority.
    Remaining cycles exhaust the bounded walk before JSON encoding.
    """
    holder=[None];pending=[(holder,0,value,0)];count=0
    while pending:
        parent,key,node,depth=pending.pop();count+=1
        if count>limits.max_container_items or depth>limits.max_depth:
            raise ValueError('witness_structure_limit')
        if type(node) is dict:
            if len(node)>limits.max_container_items-count-len(pending):raise ValueError('witness_structure_limit')
            out={};parent[key]=out
            for name,child in node.items():
                if type(name) is not str or len(name)>limits.max_string:raise ValueError('witness_key_limit')
                if name=='binding' or name.endswith('_binding'):continue
                pending.append((out,name,child,depth+1))
        elif type(node) in (tuple,list):
            if len(node)>limits.max_container_items-count-len(pending):raise ValueError('witness_structure_limit')
            out=[None]*len(node);parent[key]=out
            pending.extend((out,i,child,depth+1) for i,child in enumerate(node))
        else:parent[key]=node
    preflight_broad_json(holder[0],limits=limits)
    return holder[0]


def parse_broad_witness(raw, *, limits=BroadWitnessLimits()):
    if type(raw) not in (str,bytes):raise ValueError('witness_json_type')
    if len(raw)>limits.max_bytes:raise ValueError('witness_byte_limit')
    try:
        if isinstance(raw,bytes):raw=raw.decode('utf-8')
        depth=0;quoted=False;escape=False;tokens=0;atom=False
        for char in raw:
            if quoted:
                if escape:escape=False
                elif char=='\\':escape=True
                elif char=='"':quoted=False
            elif char=='"':
                quoted=True;tokens+=1;atom=False
            elif char in '[{':
                tokens+=1;atom=False
                depth+=1
                if depth>limits.max_depth:raise ValueError('witness_structure_limit')
            elif char in ']}':depth-=1;atom=False
            elif char in ',: \t\r\n':atom=False
            elif not atom:
                tokens+=1;atom=True
            if tokens>limits.max_container_items:raise ValueError('witness_structure_limit')
        def pairs(rows):
            result={}
            for key,val in rows:
                if key in result:raise ValueError('duplicate_json_key')
                result[key]=val
            return result
        def invalid(_):raise ValueError('non_integer_json_number')
        def integer(text):
            if len(text)>21:raise ValueError('witness_integer_limit')
            value=int(text)
            if not -(1<<64)<=value<(1<<64):raise ValueError('witness_integer_limit')
            return value
        result=json.loads(raw,object_pairs_hook=pairs,parse_float=invalid,parse_constant=invalid,parse_int=integer)
        preflight_broad_json(result,limits=limits)
        if type(result) is not dict:raise ValueError('witness_object_required')
        return result
    except (UnicodeError,RecursionError,json.JSONDecodeError) as exc:
        raise ValueError('malformed_witness_json') from exc
