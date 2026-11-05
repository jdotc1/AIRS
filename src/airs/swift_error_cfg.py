"""Bounded byte-derived ARM64 structural CFG; no runtime or Swift semantics.

Every admitted word is classified, including words after an apparent return.
Calls retain only a candidate continuation. No dominance, exclusivity, execution,
termination, async, or source reconstruction claim follows from this graph.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct

from .arm64 import ModelError
from .cfg import BRANCHES
from .swift_broad_instructions import decode_instruction
from .types import MachOImage, FunctionRange

MODEL = 'swift-bounded-structural-cfg-v1'
_CAPS = {'max_work': 262144, 'max_blocks': 8192, 'max_edges': 32768,
         'max_depth': 8192, 'max_retained_words': 16384}


@dataclass(frozen=True)
class SwiftCFGLimits:
    max_work: int = 65536
    max_blocks: int = 4096
    max_edges: int = 16384
    max_depth: int = 4096
    max_retained_words: int = 4096

    def __post_init__(self):
        for name, cap in _CAPS.items():
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= cap:
                raise ValueError(f'{name} must be an integer in 0..{cap}')


class _Refusal(Exception):
    pass


def build_swift_cfg(image: MachOImage, function: FunctionRange, *,
                    limits: SwiftCFGLimits = SwiftCFGLimits()) -> dict:
    """Build exact-function structural blocks from admitted bytes, without execution.

    Preferred VM addresses and slice/container file offsets are separate fields.
    Resource exhaustion never returns a complete eligible graph. Depth bounds a
    deterministic DFS discovery tree, not runtime stack or loop iterations.
    """
    if not isinstance(limits, SwiftCFGLimits):
        raise TypeError('limits must be SwiftCFGLimits')
    result = {'model': MODEL, 'status': 'blocked', 'reason': None,
              'function_pc': hex(function.start), 'blocks': [], 'edges': [],
              'call_return_candidates': [], 'returns': [], 'exception_transfers': [],
              'external_exception_handling_unmodeled': True,
              'exception_resume_proven': False,
              'runtime_return_proven': False, 'dominance_proven': False,
              'exclusive_path_proven': False, 'source_reconstruction_allowed': False,
              'completeness': {'all_words_classified': False, 'complete': False,
                               'reason': None},
              'accounting': {'work': 0, 'retained_words': 0, 'blocks': 0, 'edges': 0,
                             'max_discovery_depth': 0}}
    accounting = result['accounting']

    def finish(status, reason):
        result['status'] = status
        result['reason'] = reason
        result['completeness']['reason'] = reason
        result['completeness']['complete'] = status == 'eligible_structural_only'
        return result

    def work():
        if accounting['work'] >= limits.max_work:
            raise _Refusal('work_limit')
        accounting['work'] += 1

    try:
        if image.architecture != 'arm64' or image.cpu_subtype not in (0, 1):
            return finish('declined', 'ordinary_arm64_required')
        # Equality includes exact start/end/name/boundary evidence; no caller-made
        # substitute range may silently change the admitted image membership.
        matches = 0
        for member in image.functions:
            work()
            if member == function:
                matches += 1
            elif member.start < function.end and function.start < member.end:
                return finish('blocked', 'overlapping_function_membership')
        if matches != 1:
            return finish('blocked', 'exact_function_membership_required')
        if function.boundary_source != 'lc_function_starts':
            return finish('declined', 'exact_lc_function_starts_required')
        if (function.start < 0 or function.end > 1 << 64 or function.size <= 0
                or function.start % 4 or function.size % 4):
            return finish('blocked', 'invalid_function_extent')
        count = function.size // 4
        if count > limits.max_retained_words:
            return finish('blocked', 'retained_words_limit')
        if count > limits.max_work - accounting['work']:
            return finish('blocked', 'work_limit')
        section = None
        for candidate in image.sections:
            work()
            if candidate.address <= function.start and function.end <= candidate.end:
                if section is not None:
                    return finish('blocked', 'ambiguous_file_mapping')
                section = candidate
        if section is None or not section.executable or section.flags & 0xff in (1, 12, 18):
            return finish('blocked', 'executable_file_mapping_required')
        offset = section.file_offset + function.start - section.address
        if (offset < 0 or offset + function.size > len(image.data)
                or offset + function.size > image.slice_size or image.slice_offset < 0):
            return finish('blocked', 'truncated_file_mapping')
        if limits.max_blocks == 0:
            return finish('blocked', 'blocks_limit')
        if limits.max_depth == 0:
            return finish('blocked', 'depth_limit')
        rows = []
        leaders = {function.start}

        def leader(pc):
            if pc not in leaders:
                if len(leaders) >= limits.max_blocks:
                    raise _Refusal('blocks_limit')
                leaders.add(pc)
        unresolved = False
        # Edges initially refer to instruction PCs; block assignment follows the
        # complete lexical pass so backward/side entries split blocks correctly.
        def edge(row, kind, target=None):
            if len(result['edges']) >= limits.max_edges:
                raise _Refusal('edges_limit')
            work()
            if target is not None and (not 0 <= target < 1 << 64 or target % 4):
                raise _Refusal('invalid_branch_target')
            if target is not None and not function.start <= target < function.end:
                raise _Refusal('branch_outside_function')
            record = {key: row[key] for key in ('pc', 'word', 'slice_offset', 'container_offset')}
            record.update(source_pc=row['pc'], target_pc=hex(target) if target is not None else None, kind=kind)
            result['edges'].append(record)
            accounting['edges'] += 1
            if target is not None:
                leader(target)

        for index in range(count):
            work()
            pc = function.start + index * 4
            word = struct.unpack_from('<I', image.data, offset + index * 4)[0]
            row = {'pc': hex(pc), 'word': f'0x{word:08x}',
                   'slice_offset': hex(offset + index * 4),
                   'container_offset': hex(image.slice_offset + offset + index * 4)}
            try:
                instruction = decode_instruction(word, pc)
                kind = instruction.kind
            except ModelError as error:
                row['unresolved_reason'] = error.code
                instruction = None
                kind = 'unresolved'
            row['kind'] = kind
            rows.append(row)
            accounting['retained_words'] += 1
            following = pc + 4
            if kind in BRANCHES:
                edge(row, 'branch' if kind == 'b' else 'conditional_taken', pc + instruction.immediate)
                if kind != 'b':
                    edge(row, 'conditional_fallthrough', following)
            elif kind == 'bl':
                target = pc + instruction.immediate
                if not 0 <= target < 1 << 64 or target % 4:
                    raise _Refusal('invalid_call_target')
                edge(row, 'call_return_candidate', following)
                result['call_return_candidates'].append({**row, 'callee_pc': hex(target),
                    'continuation_pc': hex(following), 'runtime_return_proven': False})
            elif kind == 'ret':
                edge(row, 'return')
                result['returns'].append(dict(row))
            elif kind == 'brk':
                # A synchronous exception is an explicit external transfer.
                # Later handler-directed resumption is not a normal CFG edge
                # and is neither modeled nor ruled out by these local bytes.
                edge(row, 'exception_transfer')
                result['exception_transfers'].append({**row,
                    'exception': 'breakpoint', 'resume_proven': False})
            elif kind == 'unresolved':
                unresolved = True
                edge(row, 'unresolved')
            elif following == function.end:
                raise _Refusal('fallthrough_outside_function')
            else:
                continue
            if following < function.end:
                leader(following)
        result['completeness']['all_words_classified'] = not unresolved
        blocks = result['blocks']
        owner = {}
        for row in rows:
            work()
            pc = int(row['pc'], 16)
            if pc in leaders:
                if len(blocks) >= limits.max_blocks:
                    raise _Refusal('blocks_limit')
                blocks.append({'start_pc': row['pc'], 'end_pc_exclusive': None,
                               'instructions': [], 'successors': [], 'predecessors': []})
                accounting['blocks'] += 1
            block = blocks[-1]
            block['instructions'].append(row)
            block['end_pc_exclusive'] = hex(pc + 4)
            owner[pc] = block
        # Lexical instructions crossing a leader need an explicit raw-word edge.
        terminal_sources = {int(e['source_pc'], 16) for e in result['edges']}
        for block in blocks:
            row = block['instructions'][-1]
            pc = int(row['pc'], 16)
            if pc not in terminal_sources:
                edge(row, 'fallthrough', pc + 4)
        for item in result['edges']:
            work()
            source = owner[int(item['source_pc'], 16)]
            source['successors'].append(item)
            if item['target_pc'] is not None:
                owner[int(item['target_pc'], 16)]['predecessors'].append(item)
        # Bound discovery across all lexical components, retaining unreachable
        # code without claiming function-entry reachability.
        seen = set()
        for root in blocks:
            if root['start_pc'] in seen:
                continue
            stack = [(root, 1)]
            seen.add(root['start_pc'])
            while stack:
                work()
                block, depth = stack.pop()
                if depth > limits.max_depth:
                    raise _Refusal('depth_limit')
                accounting['max_discovery_depth'] = max(accounting['max_discovery_depth'], depth)
                for item in reversed(block['successors']):
                    target = item['target_pc']
                    if target is not None and target not in seen:
                        if depth >= limits.max_depth:
                            raise _Refusal('depth_limit')
                        seen.add(target)
                        stack.append((owner[int(target, 16)], depth + 1))
        return finish('unresolved' if unresolved else 'eligible_structural_only',
                      'unclassified_instruction_edges' if unresolved else 'bounded_classified_subset')
    except _Refusal as refusal:
        return finish('blocked', str(refusal))
