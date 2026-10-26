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

from .cfg import decode_instruction, BRANCHES
from .arm64 import ModelError
from .decode_inventory import DEFAULT_LIMITS
from .engine import resolve_input
from .macho import parse_macho
from .types import InputError, Limits, MachOImage

MODEL = 'swift-sync-error-edges-v2'
WINDOW_WORDS = 8
REGION_MODEL = 'swift-sync-error-region-v2'
REGION_WORDS = 16
INCOMING_MODEL = 'swift-region-direct-entries-v2'
INCOMING_EVIDENCE_LIMIT = 16
PRESENTATION_MODEL = 'swift-structural-presentation-v2'
SHARED_WORDS = 8


def throwing_declaration(symbol: str) -> dict | None:
    """Exact ASCII module/free-name, one unlabeled Int -> Int or Void, untyped throws.

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
    result = {'yS2iKF': 'Swift.Int', 'yySiKF': 'Swift.Void'}.get(name[cursor:])
    if result is None:
        return None
    return {'module': identifiers[0], 'name': identifiers[1],
            'parameters': ['Swift.Int'], 'result': result,
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


def _shared_epilogue(data: bytes, function, success: int, join: int) -> dict | None:
    """Bounded straight-line success arm and SP restore/return shape only."""
    if not success < join < function.end or (success | join) % 4 or join - success > SHARED_WORDS * 4:
        return None
    def word_at(pc):
        if not function.start <= pc < function.end or pc + 4 - function.start > len(data):
            raise ValueError('Shared interval outside scanned caller')
        word = struct.unpack_from('<I', data, pc - function.start)[0]
        return decode_instruction(word, pc), {'pc': hex(pc), 'word': f'0x{word:08x}'}
    success_words = []; tail = []
    try:
        for pc in range(success, join, 4):
            instruction, row = word_at(pc)
            if instruction.kind not in ('nop', 'mov', 'movz', 'movn'):
                return None
            success_words.append({**row, 'kind': instruction.kind})
        for index in range(SHARED_WORDS):
            pc = join + index * 4
            instruction, row = word_at(pc)
            tail.append({**row, 'kind': instruction.kind})
            if instruction.kind == 'ret':
                return {'success_interval': {'start_pc': hex(success), 'end_pc_exclusive': hex(join),
                                            'instructions': success_words},
                        'shared_epilogue': {'start_pc': hex(join), 'end_pc_exclusive': hex(pc + 4),
                                            'instructions': tail, 'restore_state_proven': False}}
            if instruction.kind == 'nop':
                continue
            if (instruction.kind == 'ldp' and instruction.rn == 31 and instruction.addressing == 'offset'
                    and instruction.immediate >= 0 and 19 <= instruction.rd <= 30 and 19 <= instruction.rt2 <= 30):
                continue
            if (instruction.kind == 'add' and instruction.rd == instruction.rn == 31
                    and 0 < instruction.immediate <= 4096 and instruction.immediate % 16 == 0):
                continue
            return None
    except (ModelError, ValueError):
        return None
    return None


def _error_region(data: bytes, function, edge: dict) -> dict:
    """Describe a local error interval; calls are opaque and may not return.

    The forward success entry bounds the error interval. A separately qualified
    shared restore/return tail may lie later; neither boundary proves a postdominator. Input data is the already bounded caller scan prefix.
    """
    result = {'status': 'declined', 'instructions': []}
    start, join, test = (int(edge[key], 16) for key in ('error_pc', 'success_pc', 'test_pc'))
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
                shared = _shared_epilogue(data, function, boundary, target)
                if shared is None:
                    return {**result, 'reason': 'error_region_control_flow_unmodeled'}
                join = target
            row['target_pc'] = hex(join)
        elif instruction.kind not in ('nop', 'mov', 'movz', 'movn'):
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
            expected_test = (call is not None and source == int(call['test_pc'], 16)
                             and edge['kind'] == 'xcbz' and target == end)
            expected_exit = source == end - 4 and edge['kind'] == 'b' and target == join
            if end <= target < tail_end and not (expected_test or expected_exit):
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


def _presentation_eligibility(call: dict) -> dict:
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
        start, end, test = (address(call[key]) for key in ('error_pc', 'success_pc', 'test_pc'))
        words = region['instructions']
        if (start != test + 4 or not start < end or (start | end) % 4
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
            for interval, lower, upper in ((region['success_interval'], end, join),
                    (region['shared_epilogue'], join, address(region['shared_epilogue']['end_pc_exclusive']))):
                evidence = interval['instructions']
                if (address(interval['start_pc']) != lower or address(interval['end_pc_exclusive']) != upper
                        or not 1 <= len(evidence) <= SHARED_WORDS or len(evidence) * 4 != upper - lower):
                    raise ValueError('Inconsistent shared interval')
                for index, word in enumerate(evidence):
                    if address(word['pc']) != lower + 4 * index or re.fullmatch(r'0x[0-9a-f]{8}', word['word']) is None:
                        raise ValueError('Inconsistent shared evidence')
            if (join <= end or words[-1].get('kind') != 'b' or address(words[-1]['target_pc']) != join
                    or region['shared_epilogue']['instructions'][-1].get('kind') != 'ret'
                    or region['shared_epilogue'].get('restore_state_proven') is not False):
                raise ValueError('Inconsistent shared join')
    except (KeyError, TypeError, ValueError):
        return {**result, 'reason': 'presentation_evidence_inconsistent'}
    return {**result, 'status': 'eligible_structural_only', 'reason': 'complete_caller_local_direct_validation',
            'display_plan': {'kind': 'structural_error_interval', 'label': 'Structural error-path candidate',
                             'condition': {'test_pc': call['test_pc'], 'register': call['tested_register'],
                                           'error_when': 'nonzero'},
                             'error_interval': {'start_pc': region['start_pc'], 'end_pc_exclusive': region['end_pc_exclusive'],
                                                'instructions': [dict(word) for word in words]},
                             'success_entry_pc': call['success_pc'],
                             **({'shared_epilogue': {**region['shared_epilogue'], 'instructions': [dict(w) for w in region['shared_epilogue']['instructions']]},
                                 'success_interval': {**region['success_interval'], 'instructions': [dict(w) for w in region['success_interval']['instructions']]}}
                                if 'shared_epilogue' in region else {})}}


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
                    if include_error_regions and row['status'] == 'recovered_candidate':
                        row['error_region'] = _error_region(data, function, row)
                        if validate_region_entries and row['error_region']['status'] == 'structural_region_candidate':
                            if direct_scan is None:
                                direct_scan = _caller_direct_edges(data, function)
                            row['error_region']['incoming_validation'] = _region_incoming(direct_scan, row['error_region'], row)
            if row['status'] == 'declined':
                reasons[row['reason']] += 1
            if include_structured_presentation:
                row['presentation'] = _presentation_eligibility(row)
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
                            'Only ordinary synchronous untyped Swift Int-to-Int or Int-to-Void free-function declarations are admitted.',
                            'Only bounded 64-bit MOV/NOP and forward CBZ/CBNZ return windows are recovered.',
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
        report['limitations'].append('Entry validation covers only direct edges in the bounded caller; indirect and external entries, reachability and exclusivity remain unproven.')
    if include_structured_presentation:
        report['structured_presentation_model_version'] = PRESENTATION_MODEL
        for status in ('eligible_structural_only', 'blocked', 'unresolved'):
            report['summary']['presentation_' + status + '_count'] = sum(row['presentation']['status'] == status for row in calls)
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
