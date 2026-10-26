"""Structural Swift synchronous throw-return edges, independently of unwind audits.

Reuse AIRS decoding/admission and MacScope's ordinary SwiftCC x21 error rule.
Declaration recognition implements only a complete documented scalar free-function
mangling subset. Symbols and bytes are evidence, not runtime authentication.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import struct

from .cfg import decode_instruction
from .arm64 import ModelError
from .decode_inventory import DEFAULT_LIMITS
from .engine import resolve_input
from .macho import parse_macho
from .types import InputError, Limits, MachOImage

MODEL = 'swift-sync-error-edges-v1'
WINDOW_WORDS = 8


def throwing_declaration(symbol: str) -> dict | None:
    """Exact ASCII module/free-name, one unlabeled Int -> Int, untyped throws.

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
    if name[cursor:] != 'yS2iKF':
        return None
    return {'module': identifiers[0], 'name': identifiers[1],
            'parameters': ['Swift.Int'], 'result': 'Swift.Int',
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
    aliases = {21}; window = []
    for offset in range(call_offset + 4, min(len(data), call_offset + 4 + WINDOW_WORDS * 4), 4):
        address = function.start + offset
        word = struct.unpack_from('<I', data, offset)[0]
        try:
            instruction = decode_instruction(word, address)
        except ModelError:
            return {'reason': 'intervening_instruction_unmodeled', 'window': window}
        window.append({'pc': hex(address), 'word': f'0x{word:08x}', 'kind': instruction.kind})
        if instruction.kind == 'nop':
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
        if instruction.kind in ('wcbz', 'wcbnz'):
            return {'reason': 'narrow_error_test', 'window': window}
        if instruction.kind not in ('xcbz', 'xcbnz'):
            return {'reason': 'intervening_instruction_unmodeled', 'window': window}
        if instruction.rn not in aliases:
            return {'reason': 'not_error_result_test', 'window': window}
        target = address + instruction.immediate
        fallthrough = address + 4
        if (target <= address or target == fallthrough or target % 4
                or not function.start <= target < function.end
                or not function.start <= fallthrough < function.end):
            return {'reason': 'unsupported_successor_region', 'window': window}
        success, error = (target, fallthrough) if instruction.kind == 'xcbz' else (fallthrough, target)
        return {'status': 'recovered_candidate', 'test_pc': hex(address),
                'tested_register': f'x{instruction.rn}', 'success_pc': hex(success),
                'error_pc': hex(error), 'window': window}
    return {'reason': 'postcall_window_exhausted', 'window': window}


def recover_swift_error_flow(image: MachOImage, limits: Limits = DEFAULT_LIMITS) -> dict:
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
            if row['status'] == 'declined':
                reasons[row['reason']] += 1
    recovered = sum(row['status'] == 'recovered_candidate' for row in calls)
    return {'schema_version': 1, 'report_kind': 'airs.swift_error_flow', 'model_version': MODEL,
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
                            'Only ordinary synchronous untyped Swift Int-to-Int free-function declarations are admitted.',
                            'Only bounded 64-bit MOV/NOP and forward CBZ/CBNZ return windows are recovered.',
                            'Embedded-data, relocation and symbol-only function boundaries are excluded by existing admission tags.',
                            'No catch type, handler semantics, source equivalence, unwind verdict or async claim is made.']}


def recover_swift_error_flow_path(path: Path | str, *, requested_arch: str = 'auto', limits: Limits = DEFAULT_LIMITS) -> dict:
    source = resolve_input(path)
    try:
        with source.open('rb') as handle:
            data = handle.read(limits.max_file_bytes + 1)
    except OSError as error:
        raise InputError('unreadable_input', f'Cannot read Swift-flow input: {error}') from error
    if len(data) > limits.max_file_bytes:
        raise InputError('file_size_limit', 'Input exceeds the bounded Swift flow file limit')
    return recover_swift_error_flow(parse_macho(data, str(source), limits, requested_arch), limits)
