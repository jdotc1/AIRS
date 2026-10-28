"""Structural Swift synchronous throw-return edges, independently of unwind audits.

Reuse AIRS decoding/admission and MacScope's ordinary SwiftCC x21 error rule.
Declaration recognition implements only a complete documented bounded free-function
mangling subset. Symbols and bytes are evidence, not runtime authentication.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path
import re
import struct
from types import SimpleNamespace

from .cfg import decode_instruction as decode_cfg_instruction, BRANCHES
from .arm64 import ModelError, _signed
from .decode_inventory import DEFAULT_LIMITS
from .engine import resolve_input
from .macho import parse_macho
from .types import InputError, Limits, MachOImage

MODEL = 'swift-sync-error-edges-v26'
FLAG_ENTRY_MODEL = 'swift-compare-flag-entries-v1'
WINDOW_WORDS = 8
REGION_MODEL = 'swift-sync-error-region-v17'
REGION_WORDS = 16
INCOMING_MODEL = 'swift-region-direct-entries-v7'
INCOMING_EVIDENCE_LIMIT = 16
PRESENTATION_MODEL = 'swift-structural-presentation-v6'
SUCCESS_RESULT_MODEL = 'swift-success-result-v15'
SUCCESS_CONSTANT_MODEL = 'swift-success-constant-v16'
ERROR_CONSTANT_MODEL = 'swift-error-constant-v18'
RETURN_CHOICE_MODEL = 'swift-return-choice-v22'
SHARED_WORDS = 8


def decode_instruction(word: int, address: int = 0):
    """Swift-local bounded forms; core decoding is unchanged."""
    if not 0 <= word <= 0xffffffff:
        return decode_cfg_instruction(word, address)
    # Swift-only, nonexecuting descriptor: core SP-effect/state models do not consume this kind.
    if word & 0xffe00fe0 == 0xf84007e0:
        decoded = decode_cfg_instruction(0xf9400000 | (word & 0x3ff), address)
        return replace(decoded, word=word, kind='xldr_post',
                       immediate=_signed((word >> 12) & 0x1ff, 9), addressing='post')
    if word & 0xffe0ffe0 == 0x2a0003e0:
        decoded = decode_cfg_instruction(word, address)
        return replace(decoded, kind='wmov', rn=decoded.rt2, rt2=0, addressing='')
    if word & 0xff800000 in (0x52800000, 0x12800000):
        if ((word >> 21) & 3) >= 2:
            raise ModelError('swift_wide_shift', 'W move-wide permits shifts 0 and 16 only', address)
        # Reuse existing X move-wide field extraction, retaining the original word.
        decoded = decode_cfg_instruction(word | 0x80000000, address)
        return replace(decoded, word=word, kind='w' + decoded.kind)
    return decode_cfg_instruction(word, address)


def throwing_declaration(symbol: str) -> dict | None:
    """Exact ASCII free-function subset: Int -> Int/Void or () -> Int/Void, untyped throws.

    Swift Mangling.rst's identifiers, standard Int substitution and throws suffix;
    qualified methods, specializations, typed/async/generic/thunk forms refuse.
    """
    name = symbol[1:] if symbol.startswith('_$s') else symbol
    if not name.startswith('$s') or len(name) > 512:
        return None
    cursor = 2
    identifiers = []
    for _ in range(2):
        match = re.match(r'[1-9][0-9]{0,2}', name[cursor:])
        if match is None:
            return None
        size = int(match.group()); cursor += len(match.group())
        if size > 128:
            return None
        value = name[cursor:cursor + size]; cursor += size
        if len(value) != size or re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', value) is None:
            return None
        identifiers.append(value)
    signature = {'yS2iKF': (('Swift.Int',), 'Swift.Int'),
                 'yySiKF': (('Swift.Int',), 'Swift.Void'),
                 'yyKF': ((), 'Swift.Void'),
                 'SiyKF': ((), 'Swift.Int')}.get(name[cursor:])
    if signature is None:
        return None
    parameters, result = signature
    return {'module': identifiers[0], 'name': identifiers[1],
            'parameters': list(parameters), 'result': result,
            'convention': 'swift_sync_untyped_throws', 'error_register': 'x21',
            'source': 'exact_external_symbol_grammar'}


def _symbol_groups(image: MachOImage) -> dict:
    """Read all aliases at admitted entries instead of the display-name winner.

    Mach-O admission already bounds commands, symbol records and string extents.
    Keep at most one record per address; a second alias makes that entry ambiguous.
    """
    data = image.data
    if len(data) < 32 or data[:4] != b'\xcf\xfa\xed\xfe':
        raise InputError('swift_flow_image', 'Expected an admitted little-endian Mach-O image')
    cursor = 32; table = None
    for _ in range(struct.unpack_from('<I', data, 16)[0]):
        command, size = struct.unpack_from('<II', data, cursor)
        if command == 2:
            table = struct.unpack_from('<IIII', data, cursor + 8)
        cursor += size
    if table is None:
        return {}
    symoff, count, stroff, strsize = table
    entries = {f.start for f in image.functions}
    groups = {}
    for index in range(count):
        strx, kind, section, desc, address = struct.unpack_from('<IBBHQ', data, symoff + index * 16)
        if kind & 0xe0 or kind & 0x0e != 0x0e or address not in entries:
            continue
        if not 1 <= section <= len(image.sections) or not image.sections[section - 1].executable:
            continue
        attributed = image.sections[section - 1]
        if not attributed.address <= address < attributed.end or attributed.flags & 0xff in (1, 0x0c, 0x12):
            continue
        end = data.find(b'\0', stroff + strx, min(stroff + strsize, stroff + strx + 4097))
        if end < 0:
            value = None
        else:
            try:
                name = data[stroff + strx:end].decode('utf-8', errors='strict')
            except UnicodeDecodeError:
                name = None
            value = (name, kind == 0x0f and not desc & 0x300)
        groups[address] = value if address not in groups else None
    return groups


def _edges(data: bytes, function, call_offset: int) -> dict:
    aliases = {21}; window = []; comparison = None; literal_prefix = False
    for offset in range(call_offset + 4, min(len(data), call_offset + 4 + WINDOW_WORDS * 4), 4):
        address = function.start + offset
        word = struct.unpack_from('<I', data, offset)[0]
        try:
            instruction = decode_instruction(word, address)
        except ModelError:
            return {'reason': 'comparison_branch_unmodeled' if comparison else 'intervening_instruction_unmodeled', 'window': window}
        window.append({'pc': hex(address), 'word': f'0x{word:08x}', 'kind': instruction.kind})
        metadata = {}
        if comparison is not None:
            if instruction.kind != 'bcond' or instruction.addressing not in ('0', '1'):
                return {'reason': 'comparison_branch_not_adjacent_or_supported', 'window': window}
            register, comparison_pc = comparison
            zero_target = instruction.addressing == '0'
            metadata = {'test_kind': 'cmp_zero_bcond', 'comparison_pc': hex(comparison_pc),
                        'test_condition': 'eq' if zero_target else 'ne'}
        else:
            if instruction.kind == 'nop':
                continue
            if instruction.kind in ('movz', 'movn', 'xmovk', 'wmovz', 'wmovn', 'wmovk', 'wmov'):
                literal_prefix = True
                aliases.discard(instruction.rd)
                if not aliases:
                    return {'reason': 'error_value_clobbered', 'window': window}
                continue
            if instruction.kind == 'mov':
                if instruction.rd != 31:
                    if instruction.rn in aliases:
                        aliases.add(instruction.rd)
                    else:
                        aliases.discard(instruction.rd)
                if not aliases:
                    return {'reason': 'error_value_clobbered', 'window': window}
                continue
            # Exact SUBS XZR,Xn,#0, unshifted. No general flag-state recovery.
            if word & 0xfffffc1f == 0xf100001f:
                if instruction.rn not in aliases:
                    return {'reason': 'not_error_result_comparison', 'window': window}
                comparison = (instruction.rn, address)
                continue
            if instruction.kind in ('wcbz', 'wcbnz'):
                return {'reason': 'narrow_error_test', 'window': window}
            if literal_prefix:
                return {'reason': 'literal_prefix_requires_compare_test', 'window': window}
            if instruction.kind not in ('xcbz', 'xcbnz'):
                return {'reason': 'intervening_instruction_unmodeled', 'window': window}
            if instruction.rn not in aliases:
                return {'reason': 'not_error_result_test', 'window': window}
            register = instruction.rn
            zero_target = instruction.kind == 'xcbz'
        target = address + instruction.immediate
        fallthrough = address + 4
        if (target <= address or target == fallthrough or target % 4
                or not function.start <= target < function.end or not function.start <= fallthrough < function.end):
            return {'reason': 'unsupported_successor_region', 'window': window}
        success, error = (target, fallthrough) if zero_target else (fallthrough, target)
        return {'status': 'recovered_candidate', 'test_pc': hex(address),
                'tested_register': f'x{register}', 'success_pc': hex(success),
                'error_pc': hex(error), 'window': window, **metadata}
    return {'reason': 'comparison_branch_missing_or_outside_window' if comparison else 'postcall_window_exhausted', 'window': window}


def _bounded_instruction(data: bytes, function, pc: int):
    if pc % 4 or not function.start <= pc < function.end or pc + 4 - function.start > len(data):
        raise ValueError('Shared interval outside scanned caller')
    word = struct.unpack_from('<I', data, pc - function.start)[0]
    return decode_instruction(word, pc), {'pc': hex(pc), 'word': f'0x{word:08x}'}


def _shared_return_tail(data: bytes, function, join: int) -> dict | None:
    """Existing bounded restore/return shapes, independent of arm placement."""
    tail = []
    try:
        for index in range(SHARED_WORDS):
            pc = join + index * 4
            instruction, row = _bounded_instruction(data, function, pc)
            tail.append({**row, 'kind': instruction.kind})
            if instruction.kind == 'ret':
                return {'start_pc': hex(join), 'end_pc_exclusive': hex(pc + 4),
                        'instructions': tail, 'restore_state_proven': False}
            if instruction.kind == 'nop':
                continue
            if (instruction.kind == 'xldr' and instruction.rn == 31
                    and 19 <= instruction.rd <= 30 and 0 <= instruction.immediate <= 4096
                    and instruction.immediate % 8 == 0):
                continue
            if (instruction.kind == 'xldr_post' and instruction.rn == 31
                    and 19 <= instruction.rd <= 30 and 0 < instruction.immediate <= 240
                    and instruction.immediate % 16 == 0 and index + 1 < SHARED_WORDS):
                following, _ = _bounded_instruction(data, function, pc + 4)
                if following.kind != 'ret':
                    return None
                tail[-1]['sp_writeback_bytes'] = instruction.immediate
                continue
            if (instruction.kind == 'ldp' and instruction.rn == 31 and instruction.addressing == 'offset'
                    and instruction.immediate >= 0 and 19 <= instruction.rd <= 30 and 19 <= instruction.rt2 <= 30):
                continue
            if (instruction.kind == 'ldp' and instruction.rn == 31 and instruction.addressing == 'post'
                    and 0 < instruction.immediate <= 496 and instruction.immediate % 16 == 0
                    and 19 <= instruction.rd <= 30 and 19 <= instruction.rt2 <= 30
                    and index + 1 < SHARED_WORDS):
                following, _ = _bounded_instruction(data, function, pc + 4)
                if following.kind == 'ret':
                    continue
                return None
            if instruction.word == 0x910003bf and index + 2 < SHARED_WORDS:
                restore, _ = _bounded_instruction(data, function, pc + 4)
                terminal, _ = _bounded_instruction(data, function, pc + 8)
                if (restore.kind == 'ldp' and restore.rn == 31 and restore.addressing == 'post'
                        and restore.rd == 29 and restore.rt2 == 30
                        and 0 < restore.immediate <= 496 and restore.immediate % 16 == 0
                        and terminal.kind == 'ret'):
                    continue
                # Split pair: LR from SP+8, then pop FP from SP+0 and advance by 16.
                if (restore.kind == 'xldr' and restore.rn == 31 and restore.rd == 30
                        and restore.immediate == 8 and terminal.kind == 'xldr_post'
                        and terminal.rn == 31 and terminal.rd == 29 and terminal.immediate == 16
                        and index + 3 < SHARED_WORDS):
                    following, _ = _bounded_instruction(data, function, pc + 12)
                    if following.kind == 'ret':
                        continue
                return None
            if (instruction.kind == 'add' and instruction.rd == instruction.rn == 31
                    and 0 < instruction.immediate <= 4096 and instruction.immediate % 16 == 0):
                continue
            return None
    except (ModelError, ValueError):
        return None
    return None


def _shared_epilogue(data: bytes, function, success: int, join: int, *, allow_result_arithmetic: bool = False) -> dict | None:
    """Bounded straight-line success arm and shared restore/return shape."""
    if not success < join < function.end or (success | join) % 4 or join - success > SHARED_WORDS * 4:
        return None
    words = []; has_arithmetic = False
    try:
        for pc in range(success, join, 4):
            instruction, row = _bounded_instruction(data, function, pc)
            is_arithmetic = (allow_result_arithmetic and instruction.kind in ('add', 'sub')
                      and instruction.word & 0xffc003ff == (0x91000000 if instruction.kind == 'add' else 0xd1000000)
                      and 1 <= instruction.immediate <= 4095)
            if is_arithmetic:
                if has_arithmetic:
                    return None
                has_arithmetic = True
            elif instruction.kind not in ('nop', 'mov', 'movz', 'movn', 'xmovk', 'wmovz', 'wmovn', 'wmovk', 'wmov'):
                return None
            words.append({**row, 'kind': instruction.kind})
        if has_arithmetic and any(row['kind'] not in ('nop', 'add', 'sub') for row in words):
            return None
    except (ModelError, ValueError):
        return None
    tail = _shared_return_tail(data, function, join)
    if tail is None:
        return None
    return {'success_interval': {'start_pc': hex(success), 'end_pc_exclusive': hex(join), 'instructions': words},
            'shared_epilogue': tail}


def _forward_error_region(data: bytes, function, edge: dict) -> dict:
    """Success fallthrough ending in B over a bounded out-of-line error arm."""
    result = {'status': 'declined', 'instructions': []}
    start, success, test = (int(edge[key], 16) for key in ('error_pc', 'success_pc', 'test_pc'))
    if success != test + 4 or not function.start <= success < start < function.end or (success | start) % 4:
        return {**result, 'reason': 'unsupported_error_region_layout'}
    if start - success > SHARED_WORDS * 4:
        return {**result, 'reason': 'success_region_budget'}
    words = []; calls = 0
    success_evidence = {'start_pc': hex(success), 'end_pc_exclusive': hex(start),
                        'instructions': words, 'instructions_complete': False}
    result['success_interval'] = success_evidence
    try:
        for pc in range(success, start, 4):
            try:
                instruction, row = _bounded_instruction(data, function, pc)
            except ModelError:
                word = struct.unpack_from('<I', data, pc - function.start)[0]
                words.append({'pc': hex(pc), 'word': f'0x{word:08x}', 'kind': 'unclassified'})
                success_evidence['instructions_complete'] = len(words) * 4 == start - success
                return {**result, 'reason': 'success_region_instruction_unmodeled'}
            row['kind'] = instruction.kind; words.append(row)
            success_evidence['instructions_complete'] = len(words) * 4 == start - success
            if pc + 4 == start:
                if instruction.kind != 'b':
                    return {**result, 'reason': 'unsupported_error_region_layout'}
                join = pc + instruction.immediate
                if 0 <= join < (1 << 64):
                    row['target_pc'] = hex(join)
                else:
                    row['target_reason'] = 'outside_vm_address_space'
            elif instruction.kind not in ('nop', 'mov', 'movz', 'movn', 'xmovk', 'wmovz', 'wmovn', 'wmovk', 'wmov'):
                return {**result, 'reason': 'success_region_control_flow_unmodeled'}
        if not start < join < function.end or join % 4:
            return {**result, 'reason': 'unsupported_error_region_layout'}
        if join - start > REGION_WORDS * 4:
            return {**result, 'reason': 'error_region_budget'}
        for pc in range(start, join, 4):
            instruction, row = _bounded_instruction(data, function, pc)
            row['kind'] = instruction.kind; result['instructions'].append(row)
            if instruction.kind == 'bl':
                target = pc + instruction.immediate
                if not 0 <= target < (1 << 64) or target % 4:
                    return {**result, 'reason': 'error_region_call_target_invalid'}
                row.update(call_target_pc=hex(target), semantics='opaque_call'); calls += 1
            elif instruction.kind not in ('nop', 'mov', 'movz', 'movn', 'xmovk', 'wmovz', 'wmovn', 'wmovk', 'wmov'):
                return {**result, 'reason': 'error_region_instruction_unmodeled'}
    except ModelError:
        return {**result, 'reason': 'error_region_instruction_unmodeled'}
    except ValueError:
        return {**result, 'reason': 'error_region_outside_scanned_prefix'}
    tail = _shared_return_tail(data, function, join)
    if tail is None:
        return {**result, 'reason': 'shared_epilogue_unmodeled'}
    return {**result, 'status': 'structural_region_candidate', 'layout': 'success_fallthrough_error_forward',
            'start_pc': hex(start), 'end_pc_exclusive': hex(join), 'join_pc': hex(join),
            'success_interval': success_evidence,
            'shared_epilogue': tail, 'opaque_call_count': calls,
            'call_return_proven': False, 'join_reachability_proven': False}


def _error_region(data: bytes, function, edge: dict) -> dict:
    """Describe a local error interval; calls are opaque and may not return.

    The forward success entry bounds the error interval. A separately qualified
    shared restore/return tail may lie later; neither boundary proves a postdominator. Input data is the already bounded caller scan prefix.
    """
    result = {'status': 'declined', 'instructions': []}
    if edge.get('test_kind') == 'cmp_zero_bcond':
        if edge.get('test_condition') not in ('eq', 'ne'):
            return {**result, 'reason': 'compare_handler_layout_not_qualified'}
        entry = edge.get('flag_entry_validation')
        if not isinstance(entry, dict):
            return {**result, 'reason': 'compare_flag_entries_required'}
        if (entry.get('status') != 'no_unexpected_direct_entries'
                or entry.get('scope') != 'caller_local_direct_edges_into_postcall_flag_window'
                or entry.get('protected_start_pc') != hex(int(edge['call_pc'], 16) + 4)
                or entry.get('protected_end_pc_exclusive') != hex(int(edge['test_pc'], 16) + 4)
                or edge.get('comparison_pc') != hex(int(edge['test_pc'], 16) - 4)
                or entry.get('caller_scan_complete') is not True
                or entry.get('entry_details_complete') is not True
                or entry.get('unclassified_details_complete') is not True
                or any(type(entry.get(key)) is not int or entry[key] != 0
                       for key in ('unexpected_entry_count', 'unclassified_word_count'))
                or entry.get('exclusive_entry_proven') is not False
                or entry.get('flag_state_proven') is not False):
            return {**result, 'reason': 'compare_flag_entries_not_clear'}
    start, join, test = (int(edge[key], 16) for key in ('error_pc', 'success_pc', 'test_pc'))
    if edge.get('test_kind') == 'cmp_zero_bcond':
        if edge.get('test_condition') == 'eq' and (start != test + 4 or join <= start):
            return {**result, 'reason': 'compare_handler_layout_not_qualified'}
        if edge.get('test_condition') == 'ne':
            if join != test + 4 or start <= join:
                return {**result, 'reason': 'compare_handler_layout_not_qualified'}
            try:
                comparison, comparison_row = _bounded_instruction(data, function, test - 4)
                branch, branch_row = _bounded_instruction(data, function, test)
                recorded_comparison, recorded_branch = edge['window'][-2:]
                if (comparison.word & 0xfffffc1f != 0xf100001f
                        or edge['tested_register'] != f'x{comparison.rn}'
                        or branch.kind != 'bcond' or branch.addressing != '1'
                        or test + branch.immediate != start
                        or any(recorded_comparison.get(k) != v for k, v in comparison_row.items())
                        or any(recorded_branch.get(k) != v for k, v in branch_row.items())
                        or recorded_comparison.get('kind') != comparison.kind
                        or recorded_branch.get('kind') != branch.kind):
                    return {**result, 'reason': 'compare_forward_words_inconsistent'}
            except (KeyError, TypeError, ValueError, IndexError, ModelError):
                return {**result, 'reason': 'compare_forward_words_inconsistent'}
    if join == test + 4 and start > join:
        return _forward_error_region(data, function, edge)
    if start != test + 4 or not function.start <= start < join < function.end or (start | join) % 4:
        return {**result, 'reason': 'unsupported_error_region_layout'}
    if join - start > REGION_WORDS * 4:
        return {**result, 'reason': 'error_region_budget'}
    if join - function.start > len(data):
        return {**result, 'reason': 'error_region_outside_scanned_prefix'}
    calls = 0; boundary = join; shared = {}
    for pc in range(start, boundary, 4):
        word = struct.unpack_from('<I', data, pc - function.start)[0]
        try:
            instruction = decode_instruction(word, pc)
        except ModelError:
            return {**result, 'reason': 'error_region_instruction_unmodeled'}
        row = {'pc': hex(pc), 'word': f'0x{word:08x}', 'kind': instruction.kind}
        result['instructions'].append(row)
        if instruction.kind == 'bl':
            target = pc + instruction.immediate
            if not 0 <= target < (1 << 64) or target % 4:
                return {**result, 'reason': 'error_region_call_target_invalid'}
            row['call_target_pc'] = hex(target)
            row['semantics'] = 'opaque_call'
            calls += 1
        elif instruction.kind == 'b':
            target = pc + instruction.immediate
            if pc + 4 != boundary:
                return {**result, 'reason': 'error_region_control_flow_unmodeled'}
            if target != boundary:
                shared = _shared_epilogue(data, function, boundary, target,
                    allow_result_arithmetic=edge.get('test_kind') != 'cmp_zero_bcond' and edge.get('window', [{}])[-1].get('kind') == 'xcbz')
                if shared is None:
                    return {**result, 'reason': 'error_region_control_flow_unmodeled'}
                join = target
            row['target_pc'] = hex(join)
        elif instruction.kind not in ('nop', 'mov', 'movz', 'movn', 'xmovk', 'wmovz', 'wmovn', 'wmovk', 'wmov'):
            return {**result, 'reason': 'error_region_instruction_unmodeled'}
    return {**result, 'status': 'structural_region_candidate', 'start_pc': hex(start),
            'join_pc': hex(join), 'end_pc_exclusive': hex(boundary), 'opaque_call_count': calls, **shared,
            'call_return_proven': False, 'join_reachability_proven': False}


def _caller_direct_edges(data: bytes, function) -> dict:
    """Classify the admitted scan prefix once; retain no target execution claims."""
    direct = []; unknown = []; unknown_count = 0
    for offset in range(0, len(data), 4):
        pc = function.start + offset
        word = struct.unpack_from('<I', data, offset)[0]
        try:
            instruction = decode_instruction(word, pc)
            if instruction.kind in BRANCHES or instruction.kind == 'bl':
                target = pc + instruction.immediate
                if not 0 <= target < (1 << 64):
                    raise ModelError('direct_target_out_of_range', 'Direct target outside VM address space', pc)
                direct.append({'source_pc': hex(pc), 'target_pc': hex(target),
                               'word': f'0x{word:08x}', 'kind': instruction.kind})
        except ModelError:
            unknown_count += 1
            if len(unknown) < INCOMING_EVIDENCE_LIMIT:
                unknown.append({'pc': hex(pc), 'word': f'0x{word:08x}'})
    return {'direct_edges': direct, 'unclassified_word_count': unknown_count,
            'unclassified_words': unknown, 'scanned_word_count': len(data) // 4,
            'caller_scan_complete': len(data) == function.size}


def _flag_entries(scan: dict, call: dict) -> dict:
    """Observe direct entries into the alias/flag window; never prove NZCV state."""
    start, end = int(call['call_pc'], 16) + 4, int(call['test_pc'], 16) + 4
    entries = []; count = 0
    for edge in scan['direct_edges']:
        if start <= int(edge['target_pc'], 16) < end:
            count += 1
            if len(entries) < INCOMING_EVIDENCE_LIMIT:
                entries.append(edge)
    status = ('unexpected_direct_entries' if count else
              'unresolved' if not scan['caller_scan_complete'] or scan['unclassified_word_count'] else
              'no_unexpected_direct_entries')
    return {'status': status, 'scope': 'caller_local_direct_edges_into_postcall_flag_window',
            'protected_start_pc': hex(start), 'protected_end_pc_exclusive': hex(end),
            'caller_scan_complete': scan['caller_scan_complete'],
            'scanned_word_count': scan['scanned_word_count'],
            'unclassified_word_count': scan['unclassified_word_count'],
            'unclassified_words': scan['unclassified_words'],
            'unclassified_details_complete': scan['unclassified_word_count'] == len(scan['unclassified_words']),
            'unexpected_entry_count': count, 'unexpected_entries': entries,
            'entry_details_complete': count == len(entries),
            'exclusive_entry_proven': False, 'flag_state_proven': False}


def _region_incoming(scan: dict, region: dict, call: dict | None = None) -> dict:
    """Only absence of observed unexpected caller-local direct edges is eligible."""
    start, end = int(region['start_pc'], 16), int(region['end_pc_exclusive'], 16)
    entries = []; count = 0
    for edge in scan['direct_edges']:
        source, target = int(edge['source_pc'], 16), int(edge['target_pc'], 16)
        conflict = not start <= source < end and start <= target < end
        if 'shared_epilogue' in region:
            join = int(region['join_pc'], 16)
            tail_end = int(region['shared_epilogue']['end_pc_exclusive'], 16)
            forward = region.get('layout') == 'success_fallthrough_error_forward'
            success = int(region['success_interval']['start_pc'], 16)
            success_end = int(region['success_interval']['end_pc_exclusive'], 16)
            expected_test = (call is not None and call.get('test_kind') != 'cmp_zero_bcond'
                             and source == int(call['test_pc'], 16)
                             and edge['kind'] == ('xcbnz' if forward else 'xcbz')
                             and target == (start if forward else success))
            if (call is not None and not forward and call.get('test_kind') == 'cmp_zero_bcond'
                    and call.get('test_condition') == 'eq' and source == int(call['test_pc'], 16)
                    and target == success and edge['kind'] == 'bcond'):
                try:
                    recorded = call['window'][-1]
                    word = edge['word']
                    expected_test = (recorded['pc'] == call['test_pc'] and recorded['word'] == word
                                     and re.fullmatch(r'0x[0-9a-f]{8}', word) is not None
                                     and int(word, 16) & 0xff00001f == 0x54000000
                                     and source + decode_instruction(int(word, 16), source).immediate == target)
                except (KeyError, TypeError, IndexError, ValueError, ModelError):
                    expected_test = False
            if (call is not None and forward and call.get('test_kind') == 'cmp_zero_bcond'
                    and call.get('test_condition') == 'ne' and source == int(call['test_pc'], 16)
                    and target == start and edge['kind'] == 'bcond'):
                try:
                    recorded = call['window'][-1]
                    word = edge['word']
                    expected_test = (recorded['pc'] == call['test_pc'] and recorded['word'] == word
                                     and re.fullmatch(r'0x[0-9a-f]{8}', word) is not None
                                     and int(word, 16) & 0xff00001f == 0x54000001
                                     and source + decode_instruction(int(word, 16), source).immediate == target)
                except (KeyError, TypeError, IndexError, ValueError, ModelError):
                    expected_test = False
            expected_exit = (source == (success_end - 4 if forward else end - 4)
                             and edge['kind'] == 'b' and target == join)
            if expected_test:
                conflict = False
            if ((success <= target < success_end or join <= target < tail_end)
                    and not (expected_test or expected_exit)):
                conflict = True
        if conflict:
            count += 1
            if len(entries) < INCOMING_EVIDENCE_LIMIT:
                entries.append(edge)
    status = ('unexpected_direct_entries' if count else
              'unresolved' if not scan['caller_scan_complete'] or scan['unclassified_word_count'] else
              'no_unexpected_direct_entries')
    return {'status': status, 'scope': 'caller_local_direct_edges',
            'caller_scan_complete': scan['caller_scan_complete'],
            'scanned_word_count': scan['scanned_word_count'],
            'unclassified_word_count': scan['unclassified_word_count'],
            'unclassified_words': scan['unclassified_words'],
            'unclassified_details_complete': scan['unclassified_word_count'] == len(scan['unclassified_words']),
            'unexpected_entry_count': count, 'unexpected_entries': entries,
            'entry_details_complete': count == len(entries), 'exclusive_entry_proven': False}


def _presentation_eligibility(call: dict, data: bytes | None = None, function=None) -> dict:
    """Consume in-process producer results; this is not a saved-report decoder."""
    result = {'status': 'unresolved', 'source_reconstruction_allowed': False,
              'limitations': ['Structural candidate only; not reconstructed Swift source.',
                              'Calls remain opaque; displayed targets do not identify runtime behavior.',
                              'Caller-local direct-edge checks do not exclude indirect or external entries.',
                              'Reachability, exclusive entry, call return and handler semantics remain unproven.']}
    if call.get('status') != 'recovered_candidate':
        return {**result, 'status': 'blocked', 'reason': 'edge_not_recovered'}
    region = call.get('error_region')
    if not isinstance(region, dict) or region.get('status') != 'structural_region_candidate':
        return {**result, 'status': 'blocked', 'reason': 'region_not_recovered'}
    entry = region.get('incoming_validation')
    if not isinstance(entry, dict):
        return {**result, 'reason': 'incoming_validation_missing'}
    if entry.get('status') == 'unexpected_direct_entries':
        return {**result, 'status': 'blocked', 'reason': 'unexpected_direct_entries'}
    if (entry.get('status') != 'no_unexpected_direct_entries'
            or entry.get('scope') != 'caller_local_direct_edges'
            or entry.get('caller_scan_complete') is not True
            or entry.get('entry_details_complete') is not True
            or entry.get('unclassified_details_complete') is not True
            or any(type(entry.get(key)) is not int or entry[key] != 0
                   for key in ('unexpected_entry_count', 'unclassified_word_count'))
            or entry.get('exclusive_entry_proven') is not False
            or region.get('call_return_proven') is not False
            or region.get('join_reachability_proven') is not False):
        return {**result, 'reason': 'incoming_validation_not_complete_or_consistent'}
    try:
        def address(value):
            if not isinstance(value, str) or re.fullmatch(r'0x[0-9a-f]{1,16}', value) is None:
                raise ValueError('Invalid presentation VM address')
            return int(value, 16)
        start, success, test = (address(call[key]) for key in ('error_pc', 'success_pc', 'test_pc'))
        forward = region.get('layout') == 'success_fallthrough_error_forward'
        if call.get('test_kind') == 'cmp_zero_bcond':
            flag = call.get('flag_entry_validation', {})
            if not isinstance(flag, dict):
                raise ValueError('Missing compare flag-entry evidence')
            cmp_ne_forward = call.get('test_condition') == 'ne' and forward
            cmp_eq_fallthrough = call.get('test_condition') == 'eq' and not forward
            if (not (cmp_ne_forward or cmp_eq_fallthrough)
                    or (cmp_ne_forward and not (success == test + 4 and success < start))
                    or (cmp_eq_fallthrough and not (start == test + 4 and start < success))
                    or address(call['comparison_pc']) != test - 4
                    or flag.get('status') != 'no_unexpected_direct_entries'
                    or flag.get('scope') != 'caller_local_direct_edges_into_postcall_flag_window'
                    or flag.get('protected_start_pc') != hex(address(call['call_pc']) + 4)
                    or flag.get('protected_end_pc_exclusive') != hex(test + 4)
                    or any(flag.get(key) is not True for key in
                           ('caller_scan_complete', 'entry_details_complete', 'unclassified_details_complete'))
                    or any(type(flag.get(key)) is not int or flag[key] != 0 for key in
                           ('unexpected_entry_count', 'unclassified_word_count'))
                    or flag.get('flag_state_proven') is not False
                    or flag.get('exclusive_entry_proven') is not False):
                raise ValueError('Inconsistent compare flag-entry evidence')
            comparison, branch = call['window'][-2:]
            if (address(comparison['pc']) != test - 4 or address(branch['pc']) != test
                    or re.fullmatch(r'0x[0-9a-f]{8}', comparison['word']) is None
                    or re.fullmatch(r'0x[0-9a-f]{8}', branch['word']) is None):
                raise ValueError('Inconsistent compare instruction evidence')
            compare_word, branch_word = int(comparison['word'], 16), int(branch['word'], 16)
            decoded = decode_instruction(branch_word, test)
            if (compare_word & 0xfffffc1f != 0xf100001f
                    or call['tested_register'] != f'x{(compare_word >> 5) & 31}'
                    or branch_word & 0xff00001f != (0x54000001 if cmp_ne_forward else 0x54000000)
                    or decoded.kind != 'bcond' or decoded.addressing != ('1' if cmp_ne_forward else '0')
                    or test + decoded.immediate != (start if cmp_ne_forward else success)):
                raise ValueError('Inconsistent compare branch meaning')
        end = address(region['end_pc_exclusive']) if forward else success
        if forward and ('shared_epilogue' not in region
                        or region.get('success_interval', {}).get('instructions_complete') is not True):
            raise ValueError('Forward layout requires complete success and shared-tail evidence')
        words = region['instructions']
        if ((not (success == test + 4 and success < start < end) if forward else
             not (start == test + 4 and start < end)) or (start | end) % 4
                or address(region['start_pc']) != start or address(region['end_pc_exclusive']) != end
                or (address(region['join_pc']) != end and 'shared_epilogue' not in region)
                or not isinstance(words, list) or not 1 <= len(words) <= REGION_WORDS
                or len(words) * 4 != end - start
                or re.fullmatch(r'x(?:[0-9]|[12][0-9]|30)', call['tested_register']) is None):
            raise ValueError('Inconsistent presentation interval')
        for index, word in enumerate(words):
            if (address(word['pc']) != start + index * 4
                    or re.fullmatch(r'0x[0-9a-f]{8}', word['word']) is None):
                raise ValueError('Inconsistent presentation word')
        if 'shared_epilogue' in region:
            join = address(region['join_pc'])
            for interval, lower, upper in ((region['success_interval'], success, start if forward else join),
                    (region['shared_epilogue'], join, address(region['shared_epilogue']['end_pc_exclusive']))):
                evidence = interval['instructions']
                if (address(interval['start_pc']) != lower or address(interval['end_pc_exclusive']) != upper
                        or not 1 <= len(evidence) <= SHARED_WORDS or len(evidence) * 4 != upper - lower):
                    raise ValueError('Inconsistent shared interval')
                for index, word in enumerate(evidence):
                    if address(word['pc']) != lower + 4 * index or re.fullmatch(r'0x[0-9a-f]{8}', word['word']) is None:
                        raise ValueError('Inconsistent shared evidence')
            exit_word = region['success_interval']['instructions'][-1] if forward else words[-1]
            if ((join != end if forward else join <= end)
                    or exit_word.get('kind') != 'b' or address(exit_word['target_pc']) != join
                    or region['shared_epilogue']['instructions'][-1].get('kind') != 'ret'
                    or region['shared_epilogue'].get('restore_state_proven') is not False):
                raise ValueError('Inconsistent shared join')
            if call.get('test_kind') == 'cmp_zero_bcond':
                exit_pc = address(exit_word['pc'])
                decoded_exit = decode_instruction(int(exit_word['word'], 16), exit_pc)
                if decoded_exit.kind != 'b' or exit_pc + decoded_exit.immediate != join:
                    raise ValueError('Inconsistent encoded error exit')
                success_words = region['success_interval']['instructions']
                tail_words = region['shared_epilogue']['instructions']
                synthetic = SimpleNamespace(start=success, end=address(region['shared_epilogue']['end_pc_exclusive']))
                if forward:
                    if data is None or function is None:
                        raise ValueError('Missing forward caller bytes')
                    for item in (*call['window'][-2:], *success_words, *words, *tail_words):
                        _, actual = _bounded_instruction(data, function, address(item['pc']))
                        if actual['word'] != item['word']:
                            raise ValueError('Forward instruction differs from caller')
                    packed = b''.join(struct.pack('<I', int(item['word'], 16))
                                      for item in (*success_words, *words, *tail_words))
                    rebuilt = _forward_error_region(packed, synthetic, call)
                    expected = {key: value for key, value in region.items() if key != 'incoming_validation'}
                    if rebuilt != expected:
                        raise ValueError('Inconsistent encoded forward intervals')
                else:
                    packed = b''.join(struct.pack('<I', int(item['word'], 16))
                                      for item in (*success_words, *tail_words))
                    if _shared_epilogue(packed, synthetic, success, join) != {
                            'success_interval': region['success_interval'], 'shared_epilogue': region['shared_epilogue']}:
                        raise ValueError('Inconsistent encoded shared intervals')
    except (KeyError, TypeError, ValueError, ModelError):
        return {**result, 'reason': 'presentation_evidence_inconsistent'}
    return {**result, 'status': 'eligible_structural_only', 'reason': 'complete_caller_local_direct_validation',
            'display_plan': {'kind': 'structural_error_interval', 'label': 'Structural error-path candidate',
                             'condition': {'test_pc': call['test_pc'], 'register': call['tested_register'],
                                           'error_when': 'nonzero',
                                           **({key: call[key] for key in ('comparison_pc', 'test_kind', 'test_condition')}
                                              if call.get('test_kind') == 'cmp_zero_bcond' else {})},
                             'error_interval': {'start_pc': region['start_pc'], 'end_pc_exclusive': region['end_pc_exclusive'],
                                                'instructions': [dict(word) for word in words]},
                             'success_entry_pc': call['success_pc'],
                             **({'shared_epilogue': {**region['shared_epilogue'], 'instructions': [dict(w) for w in region['shared_epilogue']['instructions']]},
                                 'success_interval': {**region['success_interval'], 'instructions': [dict(w) for w in region['success_interval']['instructions']]}}
                                if 'shared_epilogue' in region else {})}}


def _success_result(data: bytes, function, call: dict, scan: dict | None) -> dict:
    """In-process bounded selected-path register evidence, not a saved-report decoder."""
    result = {'status': 'declined', 'register': 'x0',
              'runtime_value_proven': False, 'source_reconstruction_allowed': False,
              'exclusive_path_proven': False, 'caller_return_type_proven': False}
    cmp_ne = call.get('test_kind') == 'cmp_zero_bcond' and call.get('test_condition') == 'ne'
    if cmp_ne:
        try:
            fresh_scan = _caller_direct_edges(data, function)
            region = call['error_region']
            if (_flag_entries(fresh_scan, call) != call['flag_entry_validation']
                    or _region_incoming(fresh_scan, region, call) != region['incoming_validation']
                    or _presentation_eligibility(call, data, function).get('status') != 'eligible_structural_only'):
                return {**result, 'reason': 'compare_ne_success_evidence_inconsistent'}
        except (KeyError, TypeError, ValueError, IndexError, ModelError):
            return {**result, 'reason': 'compare_ne_success_evidence_inconsistent'}
    if call.get('callee', {}).get('result') != 'Swift.Int':
        return {**result, 'reason': 'callee_result_not_scalar_int'}
    if call.get('presentation', {}).get('status') != 'eligible_structural_only':
        return {**result, 'reason': 'structural_presentation_not_eligible'}
    region = call['error_region']
    shared = 'shared_epilogue' in region
    evidence = []
    aliases = {0}
    copied = False
    adjustment = None
    adjustment_operation = None

    def transfer(instruction):
        nonlocal copied
        destination = instruction.rd
        # MOV's register 31 is XZR, never a live result location.
        if destination == 31:
            return
        if instruction.kind == 'mov' and instruction.rn in aliases:
            if destination == 0 and instruction.rn != 0:
                copied = True
            aliases.add(destination)
        else:
            aliases.discard(destination)

    try:
        test = int(call['test_pc'], 16)
        first = int(call['call_pc'], 16) + 4
        compare = call.get('test_kind') == 'cmp_zero_bcond'
        if not 0 <= test - first < WINDOW_WORDS * 4:
            raise ValueError('Post-call bound')
        # Reuse exact admitted caller bytes; never infer writes from rendered labels.
        for pc in range(first, test + 4, 4):
            instruction, row = _bounded_instruction(data, function, pc)
            evidence.append({**row, 'phase': 'post_call'})
            if pc == test:
                if compare:
                    if (call.get('test_condition') not in ('eq', 'ne') or instruction.kind != 'bcond'
                            or instruction.addressing != ('1' if cmp_ne else '0') or call['tested_register'] == 'x0'
                            or pc + instruction.immediate != int(call['error_pc' if cmp_ne else 'success_pc'], 16)):
                        return {**result, 'reason': 'unsupported_result_test', 'instructions': evidence}
                elif instruction.kind not in ('xcbz', 'xcbnz') or instruction.rn == 0:
                    return {**result, 'reason': 'unsupported_result_test', 'instructions': evidence}
            elif compare and pc == test - 4:
                if (int(call['comparison_pc'], 16) != pc
                        or instruction.word & 0xfffffc1f != 0xf100001f
                        or call['tested_register'] != f'x{instruction.rn}'):
                    return {**result, 'reason': 'unsupported_result_comparison', 'instructions': evidence}
            elif instruction.kind == 'nop':
                continue
            elif instruction.kind == 'mov':
                transfer(instruction)
                if aliases:
                    continue
                return {**result, 'reason': 'post_call_result_not_preserved', 'instructions': evidence}
            else:
                return {**result, 'reason': 'post_call_result_not_preserved', 'instructions': evidence}
        interval = region['success_interval'] if shared else {'start_pc': call['success_pc'], 'end_pc_exclusive': call['success_pc']}
        start, end = int(interval['start_pc'], 16), int(interval['end_pc_exclusive'], 16)
        if (not shared and int(region['join_pc'], 16) != start) or not (1 if shared else 0) <= (end - start) // 4 <= SHARED_WORDS:
            raise ValueError('Success bound')
        join = int(region['join_pc'], 16)
        has_arithmetic = shared and any(row.get('kind') in ('add', 'sub') for row in interval['instructions'])
        if has_arithmetic:
            if compare or call['window'][-1].get('kind') != 'xcbz' or scan is None:
                return {**result, 'reason': 'success_add_layout_not_qualified', 'instructions': evidence}
            fresh_scan = _caller_direct_edges(data, function)
            decoded = _shared_epilogue(data, function, start, join, allow_result_arithmetic=True)
            if (fresh_scan != scan or _region_incoming(fresh_scan, region, call) != region['incoming_validation']
                    or decoded is None or decoded['success_interval'] != interval
                    or decoded['shared_epilogue'] != region['shared_epilogue']):
                return {**result, 'reason': 'success_add_evidence_inconsistent', 'instructions': evidence}
            recorded = call['window']
            if len(recorded) != (test - first) // 4 + 1:
                return {**result, 'reason': 'success_add_evidence_inconsistent', 'instructions': evidence}
            for index, item in enumerate(recorded):
                ins, raw = _bounded_instruction(data, function, first + index * 4)
                if item != {**raw, 'kind': ins.kind}:
                    return {**result, 'reason': 'success_add_evidence_inconsistent', 'instructions': evidence}
            test_ins, _ = _bounded_instruction(data, function, test)
            if (test_ins.kind != 'xcbz' or call['tested_register'] != f'x{test_ins.rn}'
                    or test + test_ins.immediate != start or int(call['error_pc'], 16) != test + 4):
                return {**result, 'reason': 'success_add_evidence_inconsistent', 'instructions': evidence}
        for pc in range(start, end, 4):
            instruction, row = _bounded_instruction(data, function, pc)
            evidence.append({**row, 'phase': 'success'})
            if has_arithmetic and instruction.kind in ('add', 'sub'):
                if 0 not in aliases or adjustment is not None:
                    return {**result, 'reason': 'success_result_not_preserved', 'instructions': evidence}
                adjustment = instruction.immediate
                adjustment_operation = instruction.kind
                aliases = {0}
                continue
            if instruction.kind == 'nop':
                continue
            if instruction.kind in ('mov', 'movz', 'movn', 'xmovk', 'wmovz', 'wmovn', 'wmovk', 'wmov'):
                transfer(instruction)
                if aliases:
                    continue
                return {**result, 'reason': 'success_result_not_preserved', 'instructions': evidence}
            if instruction.kind == 'b' and pc == end - 4 and pc + instruction.immediate == join:
                continue
            return {**result, 'reason': 'success_result_not_preserved', 'instructions': evidence}
        if 0 not in aliases:
            return {**result, 'reason': 'result_not_restored_to_x0', 'instructions': evidence}
        tail = _shared_return_tail(data, function, join)
        if tail is None or (shared and tail != region['shared_epilogue']):
            return {**result, 'reason': 'bounded_return_tail_missing', 'instructions': evidence}
        # Retain the inspected tail even when its entry check withholds recovery.
        evidence.extend({**row, 'phase': 'return_tail'} for row in tail['instructions'])
        if not shared:
            if (scan is None or scan.get('caller_scan_complete') is not True
                    or scan.get('unclassified_word_count') != 0):
                return {**result, 'reason': 'return_tail_entries_unresolved', 'instructions': evidence}
            tail_end = int(tail['end_pc_exclusive'], 16)
            conflicts = []; conflict_count = 0
            for edge in scan['direct_edges']:
                source, target = int(edge['source_pc'], 16), int(edge['target_pc'], 16)
                expected_test = (source == test and target == join
                                 and edge['kind'] == ('bcond' if compare else 'xcbz'))
                expected_error_exit = (source == int(region['end_pc_exclusive'], 16) - 4
                                       and edge['kind'] == 'b' and target == join)
                if join <= target < tail_end and not (expected_test or expected_error_exit):
                    conflict_count += 1
                    if len(conflicts) < INCOMING_EVIDENCE_LIMIT:
                        conflicts.append(edge)
            if conflicts:
                return {**result, 'reason': 'unexpected_return_tail_entry',
                        'unexpected_tail_entry_count': conflict_count,
                        'tail_entry_details_complete': conflict_count == len(conflicts),
                        'unexpected_tail_entries': conflicts, 'instructions': evidence}

        return {**result, 'status': ('adjusted_register_candidate' if adjustment is not None else
                                      'copied_register_candidate' if copied else 'preserved_register_candidate'),
                'reason': (f'recorded_success_path_{adjustment_operation}s_immediate' if adjustment is not None else
                           'recorded_success_path_restores_x0_copy' if copied else 'recorded_success_path_preserves_x0'),
                **({'operation': f'{adjustment_operation}_immediate_modulo', 'immediate': adjustment, 'bit_width': 64}
                   if adjustment is not None else {}),
                'result_registers_before_tail': [f'x{register}' for register in sorted(aliases)],
                'return_tail_layout': 'shared_epilogue' if shared else 'success_entry',
                'call_pc': call['call_pc'], 'success_pc': call['success_pc'],
                'return_pc': tail['instructions'][-1]['pc'], 'instructions': evidence}
    except (KeyError, TypeError, ValueError, ModelError):
        return {**result, 'reason': 'bounded_result_evidence_unavailable', 'instructions': evidence}


def _path_constant(data: bytes, function, call: dict, *, error: bool = False, scan: dict | None = None) -> dict:
    """Constants assigned along a recorded path, not caller or runtime facts."""
    path = 'error' if error else 'success'
    result = {'status': 'declined', 'register': 'x0', 'runtime_value_proven': False,
              'source_reconstruction_allowed': False, 'exclusive_path_proven': False,
              'caller_return_type_proven': False}
    if error:
        result.update(call_return_proven=False, handler_semantics_proven=False)
    cmp_ne = call.get('test_kind') == 'cmp_zero_bcond' and call.get('test_condition') == 'ne'
    if cmp_ne:
        try:
            fresh_scan = _caller_direct_edges(data, function)
            region = call['error_region']
            if not error:
                first = int(call['call_pc'], 16) + 4
                last = int(call['test_pc'], 16)
                recorded = call['window']
                if len(recorded) != (last - first) // 4 + 1:
                    return {**result, 'reason': 'compare_ne_success_evidence_inconsistent'}
                for index, item in enumerate(recorded):
                    instruction, row = _bounded_instruction(data, function, first + 4 * index)
                    if item != {**row, 'kind': instruction.kind}:
                        return {**result, 'reason': 'compare_ne_success_evidence_inconsistent'}
                scan = fresh_scan
            if (_flag_entries(fresh_scan, call) != call['flag_entry_validation']
                    or _region_incoming(fresh_scan, region, call) != region['incoming_validation']
                    or _presentation_eligibility(call, data, function).get('status') != 'eligible_structural_only'):
                return {**result, 'reason': f'compare_ne_{path}_evidence_inconsistent'}
        except (KeyError, TypeError, ValueError, IndexError, ModelError):
            return {**result, 'reason': f'compare_ne_{path}_evidence_inconsistent'}
    cmp_success = call.get('test_kind') == 'cmp_zero_bcond' and not error
    if call.get('callee', {}).get('result') not in ('Swift.Int', 'Swift.Void'):
        return {**result, 'reason': 'callee_result_outside_admitted_subset'}
    if call.get('presentation', {}).get('status') != 'eligible_structural_only':
        return {**result, 'reason': 'structural_presentation_not_eligible'}
    region = call['error_region']
    shared = 'shared_epilogue' in region
    if not shared and not error and not cmp_success:
        return {**result, 'reason': f'bounded_{path}_interval_missing'}
    if not shared and not cmp_success:
        success_result = call.get('success_result', {})
        if (call.get('test_kind') == 'cmp_zero_bcond'
                and success_result.get('status') not in ('preserved_register_candidate', 'copied_register_candidate')):
            success_result = call.get('success_constant', {})
        if (success_result.get('status') not in ('preserved_register_candidate', 'copied_register_candidate')
                and not (call.get('test_kind') == 'cmp_zero_bcond'
                         and success_result.get('status') == 'constant_register_candidate')):
            return {**result, 'reason': 'validated_success_return_tail_missing'}
        if success_result.get('return_tail_layout') != 'success_entry':
            return {**result, 'reason': 'validated_success_return_tail_missing'}
    evidence = []; constants = {}; opaque_calls = 0
    try:
        interval = ({'start_pc': hex(int(call['call_pc'], 16) + 4),
                     'end_pc_exclusive': hex(int(call['test_pc'], 16) + 4)} if cmp_success else
                    region if error else region['success_interval'])
        start, end = int(interval['start_pc'], 16), int(interval['end_pc_exclusive'], 16)
        join = int(region['join_pc'], 16)
        if cmp_success and not shared and join != int(call['success_pc'], 16):
            return {**result, 'reason': 'success_entry_binding_inconsistent', 'instructions': evidence}
        if not 1 <= (end - start) // 4 <= (REGION_WORDS if error else SHARED_WORDS):
            raise ValueError('Success interval bound')
        intervals = [(start, end, 'post_call' if cmp_success else path)]
        if cmp_success and shared:
            arm = region['success_interval']
            arm_start, arm_end = int(arm['start_pc'], 16), int(arm['end_pc_exclusive'], 16)
            if (arm_start != int(call['success_pc'], 16)
                    or arm_end != (int(call['error_pc'], 16) if cmp_ne else join)
                    or not 1 <= (arm_end - arm_start) // 4 <= SHARED_WORDS):
                raise ValueError('Shared success interval binding')
            if not cmp_ne:
                decoded = _shared_epilogue(data, function, arm_start, arm_end)
                if (decoded is None or decoded['success_interval']['instructions'] != arm['instructions']
                        or decoded['shared_epilogue'] != region['shared_epilogue']):
                    return {**result, 'reason': 'shared_success_evidence_inconsistent', 'instructions': evidence}
            intervals.append((arm_start, arm_end, 'success'))
        for pc, phase in ((pc, phase) for lo, hi, phase in intervals for pc in range(lo, hi, 4)):
            instruction, row = _bounded_instruction(data, function, pc)
            evidence.append({**row, 'phase': phase})
            if cmp_success and phase == 'post_call' and pc == int(call['test_pc'], 16) - 4:
                if (pc != int(call['comparison_pc'], 16)
                        or instruction.word & 0xfffffc1f != 0xf100001f
                        or call['tested_register'] != f'x{instruction.rn}'):
                    return {**result, 'reason': 'unsupported_success_comparison', 'instructions': evidence}
                continue
            if cmp_success and phase == 'post_call' and pc == int(call['test_pc'], 16):
                if (call.get('test_condition') not in ('eq', 'ne') or instruction.kind != 'bcond'
                        or instruction.addressing != ('1' if cmp_ne else '0')
                        or pc + instruction.immediate != int(call['error_pc' if cmp_ne else 'success_pc'], 16)):
                    return {**result, 'reason': 'unsupported_success_test', 'instructions': evidence}
                continue
            if cmp_ne and cmp_success and phase == 'success' and pc == arm_end - 4 and instruction.kind == 'b' and pc + instruction.immediate == join:
                continue
            if cmp_success and instruction.kind not in ('nop', 'mov', 'movz', 'movn', 'xmovk', 'wmovz', 'wmovn', 'wmovk', 'wmov'):
                return {**result, 'reason': 'success_constant_instruction_unsupported', 'instructions': evidence}
            if instruction.kind == 'nop':
                continue
            if instruction.kind == 'b' and pc == end - 4 and pc + instruction.immediate == join:
                continue
            if error and instruction.kind == 'bl':
                constants.clear()
                opaque_calls += 1
                evidence[-1]['constant_state'] = 'cleared_after_opaque_call'
                continue
            if instruction.kind not in ('mov', 'movz', 'movn', 'xmovk', 'wmovz', 'wmovn', 'wmovk', 'wmov'):
                return {**result, 'reason': f'{path}_constant_instruction_unsupported', 'instructions': evidence}
            destination = instruction.rd
            if destination == 31:
                continue  # XZR discards writes; it is not a storage location.
            if instruction.kind in ('movz', 'movn', 'wmovz', 'wmovn'):
                width = 32 if instruction.kind.startswith('w') else 64
                constants[destination] = (instruction.immediate if instruction.kind.endswith('movz')
                                          else ~instruction.immediate) & ((1 << width) - 1)
            elif instruction.kind in ('xmovk', 'wmovk'):
                if destination in constants:
                    shift = int(instruction.addressing)
                    mask = 0xffff << shift
                    constants[destination] = ((constants[destination] & ~mask)
                                               | (instruction.immediate << shift)) & ((1 << (32 if instruction.kind == 'wmovk' else 64)) - 1)
                # Partial update of an unknown register does not create known bits.
            elif instruction.rn == 31:
                constants[destination] = 0
            elif instruction.rn in constants:
                constants[destination] = (constants[instruction.rn] & 0xffffffff if instruction.kind == 'wmov'
                                          else constants[instruction.rn])
            else:
                constants.pop(destination, None)
        tail = _shared_return_tail(data, function, join)
        if tail is None or (shared and tail != region['shared_epilogue']):
            return {**result, 'reason': 'bounded_return_tail_missing', 'instructions': evidence}
        if cmp_success:
            evidence.extend({**row, 'phase': 'return_tail'} for row in tail['instructions'])
            if (scan is None or scan.get('caller_scan_complete') is not True
                    or scan.get('unclassified_word_count') != 0):
                return {**result, 'reason': 'return_tail_entries_unresolved', 'instructions': evidence}
            tail_end = int(tail['end_pc_exclusive'], 16)
            conflicts = []; conflict_count = 0
            for edge in scan['direct_edges']:
                source, target = int(edge['source_pc'], 16), int(edge['target_pc'], 16)
                expected_test = source == int(call['test_pc'], 16) and edge['kind'] == 'bcond' and target == join
                expected_exit = (source == (int(region['success_interval']['end_pc_exclusive'], 16) if cmp_ne else int(region['end_pc_exclusive'], 16)) - 4
                                 and edge['kind'] == 'b' and target == join)
                if join <= target < tail_end and not (expected_test or expected_exit):
                    conflict_count += 1
                    if len(conflicts) < INCOMING_EVIDENCE_LIMIT:
                        conflicts.append(edge)
            if conflicts:
                return {**result, 'reason': 'unexpected_return_tail_entry',
                        'unexpected_tail_entries': conflicts,
                        'unexpected_tail_entry_count': conflict_count,
                        'tail_entry_details_complete': conflict_count == len(conflicts), 'instructions': evidence}
        elif not shared:
            captured_tail = [{key: value for key, value in row.items() if key != 'phase'}
                             for row in success_result.get('instructions', []) if row.get('phase') == 'return_tail']
            if (success_result.get('register') != 'x0'
                    or success_result.get('call_pc') != call['call_pc']
                    or success_result.get('success_pc') != call['success_pc']
                    or region['join_pc'] != call['success_pc']
                    or success_result.get('return_pc') != tail['instructions'][-1]['pc']
                    or captured_tail != tail['instructions']
                    or any(success_result.get(key) is not False for key in ('runtime_value_proven',
                        'source_reconstruction_allowed', 'exclusive_path_proven', 'caller_return_type_proven'))):
                return {**result, 'reason': 'validated_success_return_tail_inconsistent', 'instructions': evidence}
        if not cmp_success:
            evidence.extend({**row, 'phase': 'return_tail'} for row in tail['instructions'])
        if 0 not in constants:
            return {**result, 'reason': f'{path}_x0_constant_not_known', 'instructions': evidence}
        return {**result, 'status': 'constant_register_candidate',
                'reason': f'recorded_{path}_path_assigns_constant',
                'constant_bits': f'0x{constants[0]:016x}', 'bit_width': 64,
                'depends_on_call_result': False, 'call_pc': call['call_pc'],
                path + '_pc': call[path + '_pc'],
                **({'return_tail_layout': 'shared_epilogue' if shared else 'success_entry'} if cmp_success else {}),
                **({'opaque_call_count': opaque_calls} if error else {}), 'return_pc': tail['instructions'][-1]['pc'],
                'instructions': evidence}
    except (KeyError, TypeError, ValueError, ModelError):
        return {**result, 'reason': 'bounded_constant_evidence_unavailable', 'instructions': evidence}


def _return_choice(call: dict) -> dict:
    """Join in-process producer facts only; this does not admit saved reports."""
    result = {'status': 'unresolved', 'source_reconstruction_allowed': False,
              'runtime_value_proven': False, 'exclusive_path_proven': False,
              'caller_return_type_proven': False, 'call_return_proven': False,
              'handler_semantics_proven': False}
    cmp_ne = call.get('test_kind') == 'cmp_zero_bcond' and call.get('test_condition') == 'ne'
    if call.get('presentation', {}).get('status') != 'eligible_structural_only':
        return {**result, 'reason': 'structural_presentation_not_eligible'}
    error = call.get('error_constant', {})
    constant = call.get('success_constant', {})
    returned = call.get('success_result', {})
    error_known = error.get('status') == 'constant_register_candidate'
    constant_known = constant.get('status') == 'constant_register_candidate'
    returned_known = returned.get('status') in ('preserved_register_candidate', 'copied_register_candidate', 'adjusted_register_candidate')
    if not error_known or constant_known == returned_known:
        return {**result, 'reason': 'outcome_evidence_missing_or_conflicting'}
    success = constant if constant_known else returned
    if returned_known and call.get('callee', {}).get('result') != 'Swift.Int':
        return {**result, 'reason': 'outcome_evidence_inconsistent'}
    try:
        plan = call['presentation']['display_plan']
        expected_condition = {'test_pc': call['test_pc'], 'register': call['tested_register'], 'error_when': 'nonzero'}
        if call.get('test_kind') == 'cmp_zero_bcond':
            expected_condition.update({key: call[key] for key in ('comparison_pc', 'test_kind', 'test_condition')})
        if (call['presentation'].get('source_reconstruction_allowed') is not False
                or plan['condition'] != expected_condition
                or plan['success_entry_pc'] != call['success_pc']
                or plan['error_interval']['start_pc'] != call['error_pc']):
            raise ValueError('Presentation binding')
        region = call['error_region']
        if cmp_ne and (region.get('layout') != 'success_fallthrough_error_forward'
                       or 'shared_epilogue' not in region
                       or success.get('return_tail_layout') != 'shared_epilogue'):
            raise ValueError('NE forward shared outcome source')
        if ('shared_epilogue' not in region
                and not ((returned_known and not constant_known and returned.get('return_tail_layout') == 'success_entry')
                         or (call.get('test_kind') == 'cmp_zero_bcond' and constant_known and not returned_known
                             and constant.get('return_tail_layout') == 'success_entry'))):
            raise ValueError('Success-entry outcome source')
        return_pc = (region['shared_epilogue']['instructions'][-1]['pc'] if 'shared_epilogue' in region
                     else success['return_pc'])
        for path, outcome in (('success', success), ('error', error)):
            if (outcome['register'] != 'x0' or outcome['call_pc'] != call['call_pc']
                    or outcome[path + '_pc'] != call[path + '_pc']
                    or outcome['return_pc'] != return_pc
                    or any(outcome.get(key) is not False for key in ('source_reconstruction_allowed',
                        'runtime_value_proven', 'exclusive_path_proven', 'caller_return_type_proven'))):
                raise ValueError('Outcome binding')
        if error.get('call_return_proven') is not False or error.get('handler_semantics_proven') is not False:
            raise ValueError('Error proof scope')
        def literal(outcome):
            bits = outcome['constant_bits']
            if (type(outcome['bit_width']) is not int or outcome['bit_width'] != 64
                    or not isinstance(bits, str) or re.fullmatch(r'0x[0-9a-f]{16}', bits) is None
                    or outcome.get('depends_on_call_result') is not False):
                raise ValueError('Literal bits')
            return {'kind': 'constant_bits', 'bit_width': 64, 'constant_bits': bits}
        if returned_known and success['status'] == 'adjusted_register_candidate':
            operation = success.get('operation')
            if (operation not in ('add_immediate_modulo', 'sub_immediate_modulo')
                    or type(success.get('immediate')) is not int or not 1 <= success['immediate'] <= 4095
                    or type(success.get('bit_width')) is not int or success['bit_width'] != 64
                    or success.get('return_tail_layout') != 'shared_epilogue'):
                raise ValueError('Adjusted result')
            instruction_rows = success['instructions']
            interval = region['success_interval']
            captured = interval['instructions']
            if (not isinstance(instruction_rows, list) or len(instruction_rows) > 3 * SHARED_WORDS
                    or not isinstance(captured, list) or not 1 <= len(captured) <= SHARED_WORDS
                    or any(not isinstance(row, dict) for row in instruction_rows + captured)):
                raise ValueError('Adjusted arm row types')
            selected = [row for row in instruction_rows if row.get('phase') == 'success']
            if (plan.get('success_interval') != interval or len(selected) != len(captured)
                    or any((row.get('pc'), row.get('word')) != (record.get('pc'), record.get('word'))
                           for row, record in zip(selected, captured))):
                raise ValueError('Adjusted arm binding')
            expected = (0x91000000 if operation == 'add_immediate_modulo' else 0xd1000000) | (success['immediate'] << 10)
            if sum(row.get('word') == f'0x{expected:08x}' for row in selected) != 1:
                raise ValueError('Adjusted instruction binding')
            success_description = {'kind': 'call_result_add_immediate' if operation == 'add_immediate_modulo' else 'call_result_sub_immediate',
                                   'register': 'x0', 'immediate': success['immediate'], 'bit_width': 64,
                                   'operation': operation}
        else:
            success_description = literal(success) if constant_known else {
                'kind': 'call_result', 'register': 'x0', 'candidate_status': success['status']}
        error_description = literal(error)
        return {**result, 'status': 'structural_choice_candidate',
                'reason': 'bound_selected_path_outcomes', 'call_pc': call['call_pc'],
                'condition': dict(expected_condition),
                'success': success_description, 'error': error_description, 'return_pc': return_pc,
                'same_constant_bits': success['constant_bits'] == error['constant_bits'] if constant_known else None}
    except (KeyError, TypeError, ValueError):
        return {**result, 'reason': 'outcome_evidence_inconsistent'}


def recover_swift_error_flow(image: MachOImage, limits: Limits = DEFAULT_LIMITS, *, include_error_regions: bool = False, validate_region_entries: bool = False, include_structured_presentation: bool = False) -> dict:
    if include_structured_presentation and not (include_error_regions and validate_region_entries):
        raise InputError('swift_presentation_option', 'Structured presentation requires error regions and entry validation')
    if validate_region_entries and not include_error_regions:

        raise InputError('swift_region_option', 'Entry validation requires error-region recovery')
    if image.architecture != 'arm64' or image.cpu_subtype not in (0, 1):
        raise InputError('swift_flow_architecture', 'Only exact ordinary ARM64 subtypes are admitted')
    if len(image.data) > limits.max_file_bytes or len(image.functions) > limits.max_functions:
        raise InputError('swift_flow_limit', 'Image exceeds bounded Swift flow limits')
    functions = {f.start: f for f in image.functions}
    if len(functions) != len(image.functions):
        raise InputError('swift_flow_boundaries', 'Function entries must be unique')
    groups = _symbol_groups(image)
    remaining = limits.max_total_instructions
    calls = []; scans = []; reasons = Counter(); observed = omitted = scanned = 0
    word_complete = True
    for function in image.functions:
        scan = {'function_pc': hex(function.start), 'name': function.name, 'scanned_words': 0}
        scans.append(scan)
        if (function.boundary_source != 'lc_function_starts' or function.size <= 0
                or function.start % 4 or function.size % 4):
            scan['status'] = 'excluded_boundary'; word_complete = False; continue
        count = min(function.size // 4, limits.max_instructions_per_function, remaining)
        scan['status'] = 'complete' if count * 4 == function.size else 'partial_budget'
        word_complete &= count * 4 == function.size
        data = image.bytes_at(function.start, count * 4) if count else b''
        retained_here = 0
        direct_scan = None
        for offset in range(0, len(data), 4):
            scanned += 1; remaining -= 1; scan['scanned_words'] += 1
            word = struct.unpack_from('<I', data, offset)[0]
            if word & 0xfc000000 != 0x94000000:
                continue
            observed += 1
            if retained_here >= limits.max_evidence_per_function or len(calls) >= limits.max_total_evidence:
                omitted += 1; continue
            retained_here += 1
            pc = function.start + offset
            instruction = decode_instruction(word, pc)
            target = pc + instruction.immediate
            row = {'call_pc': hex(pc), 'call_image_offset': hex(pc - image.preferred_base),
                   'call_word': f'0x{word:08x}', 'caller_pc': hex(function.start),
                   'callee_pc': hex(target) if 0 <= target < (1 << 64) else None, 'status': 'declined'}
            calls.append(row)
            callee = functions.get(target)
            if not 0 <= target < (1 << 64):
                row['reason'] = 'callee_target_out_of_range'
            elif callee is None or callee.boundary_source != 'lc_function_starts':
                row['reason'] = 'callee_not_exact_function_entry'
            elif target not in groups or groups[target] is None:
                row['reason'] = 'callee_symbol_absent_or_ambiguous'
            else:
                symbol, public = groups[target]
                declaration = throwing_declaration(symbol) if symbol and public else None
                if declaration is None:
                    row['reason'] = 'callee_declaration_outside_subset'
                else:
                    row['callee'] = {'symbol': symbol, 'image_offset': hex(target - image.preferred_base), **declaration}
                    row.update(_edges(data, function, offset))
                    if validate_region_entries and row.get('test_kind') == 'cmp_zero_bcond':
                        if direct_scan is None:
                            direct_scan = _caller_direct_edges(data, function)
                        row['flag_entry_validation'] = _flag_entries(direct_scan, row)
                    if include_error_regions and row['status'] == 'recovered_candidate':
                        row['error_region'] = _error_region(data, function, row)
                        if validate_region_entries and row['error_region']['status'] == 'structural_region_candidate':
                            if direct_scan is None:
                                direct_scan = _caller_direct_edges(data, function)
                            row['error_region']['incoming_validation'] = _region_incoming(direct_scan, row['error_region'], row)
            if row['status'] == 'declined':
                reasons[row['reason']] += 1
            if include_structured_presentation:
                row['presentation'] = _presentation_eligibility(row, data, function)
                row['success_result'] = _success_result(data, function, row, direct_scan)
                row['success_constant'] = _path_constant(data, function, row, scan=direct_scan)
                row['error_constant'] = _path_constant(data, function, row, error=True)
                row['return_choice'] = _return_choice(row)
    recovered = sum(row['status'] == 'recovered_candidate' for row in calls)
    report = {'schema_version': 1, 'report_kind': 'airs.swift_error_flow', 'model_version': MODEL,
            'scope': 'structural_call_return_edges', 'address_space': 'preferred_vm',
            'image': {'architecture': image.architecture, 'cpu_subtype': image.cpu_subtype,
                      'uuid': image.uuid, 'slice_sha256': image.slice_sha256,
                      'container_sha256': image.container_sha256, 'slice_offset': image.slice_offset,
                      'slice_size': image.slice_size, 'preferred_base': hex(image.preferred_base)},
            'word_scan_complete': bool(word_complete), 'call_details_complete': omitted == 0,
            'summary': {'scanned_word_count': scanned, 'observed_direct_call_count': observed,
                        'retained_call_count': len(calls), 'omitted_call_count': omitted,
                        'recovered_candidate_count': recovered, 'declined_retained_call_count': len(calls) - recovered},
            'reasons': [{'code': code, 'count': count} for code, count in sorted(reasons.items())],
            'input_issues': [{'code': item.code, 'message': item.message, **({'offset': item.offset} if item.offset is not None else {})} for item in image.issues],
            'functions': scans, 'calls': calls,
            'limitations': ['Structural instruction-word candidates, not runtime reachability or dominance proof.',
                            'Exact symbol declarations are not authenticated runtime targets or function identity.',
                            'Only ordinary synchronous untyped Swift Int-to-Int, Int-to-Void or parameterless Int/Void free-function declarations are admitted.',
                            'Only bounded 64-bit MOV/NOP, CMP-only W MOV and X/W MOVZ/MOVN/MOVK prefixes, and forward CBZ/CBNZ or adjacent CMP-zero EQ/NE return windows are recovered.',
                            'Embedded-data, relocation and symbol-only function boundaries are excluded by existing admission tags.',
                            'No catch type, handler semantics, source equivalence, unwind verdict or async claim is made.']}
    if include_error_regions:
        regions = [row['error_region'] for row in calls if 'error_region' in row]
        report['error_region_model_version'] = REGION_MODEL
        report['summary']['recovered_error_region_count'] = sum(r['status'] == 'structural_region_candidate' for r in regions)
        report['summary']['declined_error_region_count'] = sum(r['status'] == 'declined' for r in regions)
        report['limitations'].append('Error intervals are structural candidates; opaque calls may not return and joins are not proven reachable.')
    if validate_region_entries:
        report['region_incoming_model_version'] = INCOMING_MODEL
        report['flag_entry_model_version'] = FLAG_ENTRY_MODEL
        report['limitations'].append('Entry validation covers only direct edges in the bounded caller; indirect and external entries, reachability and exclusivity remain unproven.')
    if include_structured_presentation:
        report['structured_presentation_model_version'] = PRESENTATION_MODEL
        report['success_result_model_version'] = SUCCESS_RESULT_MODEL
        report['success_constant_model_version'] = SUCCESS_CONSTANT_MODEL
        report['error_constant_model_version'] = ERROR_CONSTANT_MODEL
        report['return_choice_model_version'] = RETURN_CHOICE_MODEL
        for status in ('eligible_structural_only', 'blocked', 'unresolved'):
            report['summary']['presentation_' + status + '_count'] = sum(row['presentation']['status'] == status for row in calls)
    if any(row.get('test_kind') == 'cmp_zero_bcond' for row in calls):
        report['limitations'].append('Adjacent CMP/B.cond evidence is selected-word only; optional flag-entry inspection covers caller-local direct edges, not NZCV state or exclusive entry. Screened EQ shared tails may pair a preserved call result or success literal with error literal bits; screened NE forward presentation, preserved Int call results and error literals are structural only; Screened NE success literals and choices are structural only.')
    return report


def recover_swift_error_flow_path(path: Path | str, *, requested_arch: str = 'auto', limits: Limits = DEFAULT_LIMITS, include_error_regions: bool = False, validate_region_entries: bool = False, include_structured_presentation: bool = False) -> dict:
    source = resolve_input(path)
    try:
        with source.open('rb') as handle:
            data = handle.read(limits.max_file_bytes + 1)
    except OSError as error:
        raise InputError('unreadable_input', f'Cannot read Swift-flow input: {error}') from error
    if len(data) > limits.max_file_bytes:
        raise InputError('file_size_limit', 'Input exceeds the bounded Swift flow file limit')
    return recover_swift_error_flow(parse_macho(data, str(source), limits, requested_arch), limits, include_error_regions=include_error_regions, validate_region_entries=validate_region_entries, include_structured_presentation=include_structured_presentation)
