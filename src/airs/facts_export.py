"""Export saved imports reports as bounded AIRS Navigator Results v1 files."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import uuid
import unicodedata

from airs.swift_import_declarations import parse_import_declaration

PROFILE = 'broad-imports-v1'
MODEL = 'swift-broad-error-flow-imports-v1'
ROW_MODEL = 'swift-broad-import-callsite-v1'
STUB_MODEL = 'arm64-import-stub-double-binding-v1'
EXPORTER_VERSION = 1
TOOLCHAIN = 'airs-undetected/1'
CONTRACT_DIGESTS = {
    'README.md': '91439002927ff03da742098be63215197e9f75bf411bfe8d9ab602dcd9f246cd',
    'navigator-engine.schema.json': 'bbcf9e946a06a393cb458d604fb8c9d854322ffc6c54ef7c4ba1b129f60c0a6c',
    'vocabulary.json': 'ad3e2b3b6c33d08b2f478255ade0da3e5e80eea8ae42b16c1143b79acd7bbf25',
    'import/README.md': 'ca84729d95ad6566ffa44a5c833d931a5e893807226267e51d5b4d7b294f3cd0',
    'import/expected-reports.json': '3638bf933cc12bc6228b2b9afb9c731751142e53a84e6c67d8b89456e12a97c2',
}
COMPLETENESS = ('import_stubs_complete', 'word_scan_complete',
                'call_details_complete', 'outcome_witnesses_complete')
# Mirrored from swift_broad_flow.REPORT_BYTES and
# IMPORTS_BROAD_LIMITS.max_total_evidence; importing the analyzer is unnecessary.
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_ROWS = 8192
MAX_DEPTH = 32
_KEY = re.compile(r'[A-Za-z_][A-Za-z0-9_]*', re.ASCII)
_HEX = re.compile(r'0x(?:0|[1-9a-f][0-9a-f]*)', re.ASCII)


class ExportError(ValueError):
    """A stable named refusal; no report content is included in diagnostics."""
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def _fail(reason='invalid_report'):
    raise ExportError(reason)


def _json_value(value, depth=0, *, report=False):
    if depth > MAX_DEPTH:
        _fail('nesting_limit')
    t = type(value)
    if value is None or t is bool:
        return
    if t is int:
        if not -(2**63) <= value < 2**63:
            _fail('integer_range')
    elif t is str:
        try:
            value.encode('utf-8')
        except UnicodeEncodeError:
            _fail('invalid_unicode')
    elif t is list:
        for item in value:
            _json_value(item, depth + 1, report=report)
    elif t is dict:
        for key, item in value.items():
            if type(key) is not str:
                _fail('invalid_key')
            # Report counter keys can be symbols; contract object keys cannot.
            _json_value(key, depth + 1, report=report)
            if not report and not _KEY.fullmatch(key):
                _fail('invalid_key')
            if report and key.endswith('_proven') and item is not False:
                _fail('unsupported_proof_claim')
            _json_value(item, depth + 1, report=report)
    else:
        _fail('invalid_json_value')


def canonical_bytes(value):
    """Contract canonical UTF-8, including the complete subject object."""
    _json_value(value)
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def record_id(prefix, fields):
    return prefix + '-' + hashlib.sha256(canonical_bytes(fields)).hexdigest()[:32]


def _field(obj, key, kind):
    if type(obj) is not dict or key not in obj or type(obj[key]) is not kind:
        _fail('invalid_field_' + key)
    return obj[key]


def _text(obj, key):
    value = _field(obj, key, str)
    if not value:
        _fail('invalid_field_' + key)
    return value


def _int(obj, key):
    value = _field(obj, key, int)
    if value < 0:
        _fail('invalid_field_' + key)
    return value


def _hex(obj, key):
    value = _text(obj, key)
    if not _HEX.fullmatch(value) or int(value, 16) >= 2**64:
        _fail('invalid_field_' + key)
    return value


def _nullable_text(obj, key):
    if key not in obj or (obj[key] is not None and
                            (type(obj[key]) is not str or not obj[key])):
        _fail('invalid_field_' + key)
    return obj[key]


def _validate(report):
    _json_value(report, report=True)
    if _text(report, 'profile') != PROFILE:
        _fail('unsupported_profile')
    if _text(report, 'model_version') != MODEL:
        _fail('unsupported_model')
    if _text(report, 'import_stub_model') != STUB_MODEL:
        _fail('unsupported_stub_model')
    identity = _field(report, 'identity', dict)
    for key in ('container_sha256', 'slice_sha256'):
        if not re.fullmatch('[0-9a-f]{64}', _text(identity, key)):
            _fail('invalid_field_' + key)
    if _text(identity, 'architecture') != 'arm64':
        _fail('unsupported_architecture')
    subtype = _field(identity, 'cpu_subtype', int)
    if not -(2**31) <= subtype < 2**31:
        _fail('cpu_subtype_range')
    uid = _nullable_text(identity, 'uuid')
    try:
        image = str(uuid.UUID(uid)) if uid is not None else 'nouuid'
    except ValueError:
        _fail('invalid_field_uuid')
    for key in ('preferred_base', 'slice_offset', 'slice_size'):
        _hex(identity, key)
    offset, size = (int(identity[k], 16) for k in ('slice_offset', 'slice_size'))
    if offset >= 2**63 or size >= 2**63:
        _fail('slice_range')
    if size == 0:
        _fail('empty_slice')
    if offset + size >= 2**63:
        _fail('slice_extent_overflow')
    for key in ('slice_index', 'container_slice_count'):
        _int(identity, key)
    if identity['slice_index'] >= identity['container_slice_count']:
        _fail('invalid_slice_identity')
    for key in ('import_stubs_complete', 'word_scan_complete', 'call_details_complete',
                'outcome_witnesses_complete', 'call_return_proven', 'runtime_reachability_proven'):
        _field(report, key, bool)
    _nullable_text(report, 'import_stub_reason')
    if not report['import_stubs_complete'] and report['import_stub_reason'] is None:
        _fail('invalid_field_import_stub_reason')
    if report['import_stubs_complete'] and report['import_stub_reason'] is not None:
        _fail('stub_reason_with_complete_table')
    for key in ('omitted_calls', 'observed_call_instructions'):
        _int(report, key)
    counts = _field(report, 'import_stub_counts', dict)
    for key in counts:
        _int(counts, key)
    if not all(type(v) is str for v in _field(report, 'limitations', list)):
        _fail('invalid_field_limitations')
    if 'schema_version' in report:
        _int(report, 'schema_version')
    rows = _field(report, 'calls', list)
    if len(rows) > MAX_ROWS:
        _fail('row_limit')
    selected, seen_calls, seen_stubs = [], set(), {}
    symbol_indices, nlist_offsets = {}, {}
    for row in rows:
        admission = _field(row, 'admission', dict)
        # Other row models have no projection in this packet. A damaged import
        # row must not evade validation by losing its model label.
        marker = admission.get('model_version')
        if marker is not None and type(marker) is not str:
            _fail('invalid_field_model_version')
        imported = marker == ROW_MODEL or any(k in admission for k in
            ('import_attribution_admitted', 'callee_stub_pc', 'import_provenance'))
        if not imported:
            continue
        if not report['import_stubs_complete']:
            _fail('rows_with_incomplete_stub_table')
        if marker != ROW_MODEL:
            _fail('unsupported_row_model')
        if _field(admission, 'import_attribution_admitted', bool) is not True:
            _fail('import_attribution_not_admitted')
        if _text(admission, 'status') != 'unresolved' or _text(admission, 'reason') != 'imported_callee_abi_unqualified':
            _fail('unsupported_import_admission')
        if _text(admission, 'call_kind') not in ('bl', 'b'):
            _fail('unsupported_call_kind')
        for key in ('call_pc', 'caller_start', 'callee_stub_pc'):
            if _int(admission, key) % 4:
                _fail('unaligned_address')
        if admission['caller_start'] > admission['call_pc']:
            _fail('call_before_caller_start')
        if (_hex(row, 'call_pc') != hex(admission['call_pc']) or
                _hex(row, 'caller_pc') != hex(admission['caller_start'])):
            _fail('inconsistent_call_address')
        for key in ('candidate', 'validation'):
            if key not in row or row[key] is not None:
                _fail('unsupported_import_evidence')
        _field(admission, 'call_return_proven', bool)
        if _field(admission, 'syntactic_call_target_admitted', bool) is not False:
            _fail('unsupported_import_evidence')
        if _field(admission, 'details_complete', bool) is not True:
            _fail('incomplete_import_row')
        symbol = _text(admission, 'symbol')
        _safe_text(symbol)
        if any(c == ';' or c.isspace() or unicodedata.category(c) == 'Cc' for c in symbol):
            _fail('invalid_field_symbol')
        if not symbol.lstrip('_').startswith('$s'):
            _fail('unsupported_symbol')
        parsed = parse_import_declaration(symbol)
        if parsed.supported and not parsed.identity.throws:
            _fail('unsupported_symbol')
        declaration = _field(admission, 'declaration', dict)
        status = _text(declaration, 'status')
        reason = _nullable_text(declaration, 'reason')
        if status == 'syntax_admitted':
            _field(declaration, 'identity', dict)
            if reason is not None:
                _fail('invalid_declaration')
        elif status == 'syntax_unresolved':
            if reason is None or 'identity' not in declaration or declaration['identity'] is not None:
                _fail('invalid_declaration')
        else:
            _fail('invalid_declaration')
        p = _field(admission, 'import_provenance', dict)
        if _text(p, 'stub_model') != STUB_MODEL:
            _fail('unsupported_stub_model')
        if 'stub_indirect_index' not in p or 'pointer_indirect_index' not in p:
            _fail('missing_indirect_index')
        for key in ('stub_indirect_entry_offset', 'pointer_indirect_entry_offset', 'nlist_offset',
                    'symbol_index', 'stub_indirect_index', 'pointer_indirect_index', 'pointer_address'):
            _int(p, key)
        words = _field(p, 'stub_words', list)
        if len(words) != 3:
            _fail('invalid_stub_words')
        for i, word in enumerate(words):
            if _int(word, 'pc') != admission['callee_stub_pc'] + 4 * i:
                _fail('inconsistent_stub_address')
            if not re.fullmatch('0x[0-9a-f]{8}', _text(word, 'word')):
                _fail('invalid_stub_word')
            offset = _int(word, 'slice_file_offset')
            if _int(word, 'container_file_offset') != offset + int(identity['slice_offset'], 16):
                _fail('inconsistent_stub_offset')
        if admission['call_pc'] in seen_calls:
            _fail('duplicate_call')
        seen_calls.add(admission['call_pc'])
        signature = canonical_bytes([admission['symbol'], p])
        stub = admission['callee_stub_pc']
        if stub in seen_stubs and seen_stubs[stub] != signature:
            _fail('conflicting_stub')
        index, offset = p['symbol_index'], p['nlist_offset']
        if ((index in symbol_indices and symbol_indices[index] != (offset, symbol)) or
                (offset in nlist_offsets and nlist_offsets[offset] != (index, symbol))):
            _fail('conflicting_symbol_entry')
        symbol_indices[index] = (offset, symbol)
        nlist_offsets[offset] = (index, symbol)
        seen_stubs[stub] = signature
        selected.append(admission)
    ordered_stubs = sorted(seen_stubs)
    if any(right - left < 12 for left, right in zip(ordered_stubs, ordered_stubs[1:])):
        _fail('overlapping_stubs')
    return image + '/' + identity['slice_sha256'][:16], selected


def _safe_text(value):
    try:
        size = len(value.encode('utf-8'))
    except UnicodeEncodeError:
        _fail('unsafe_text')
    if size > 4096 or any(ord(c) < 32 or 127 <= ord(c) <= 159 or
            ord(c) in (0x61c, 0x200e, 0x200f) or
            0x202a <= ord(c) <= 0x202e or 0x2066 <= ord(c) <= 0x2069 for c in value):
        _fail('unsafe_text')


def _measure(value, depth=0):
    """Enforce tree caps and return the number of JSON values (keys excluded)."""
    if depth > 32:
        _fail('format_budget_exceeded')
    if type(value) is str:
        _safe_text(value)
    count = 1
    if type(value) in (list, dict):
        if len(value) > 4096 or (type(value) is list and len(value) > 128):
            _fail('format_budget_exceeded')
        if type(value) is dict:
            for key in value:
                _safe_text(key)
                if len(key.encode()) > 64 or not _KEY.fullmatch(key):
                    _fail('invalid_key')
        for child in (value.values() if type(value) is dict else value):
            count += _measure(child, depth + 1)
    return count


def file_counts(document):
    results = document['results']
    return dict(results=len(results), facts=sum(len(r['facts']) for r in results),
        frontier=sum(len(r['frontier']) for r in results),
        provenance=sum(len(f['provenance']) for r in results for f in r['facts']))


def _check_file(document):
    counts = file_counts(document)
    if (counts['results'] > 128 or counts['facts'] + counts['frontier'] > 1024 or
            counts['provenance'] > 4096 or any(
            len(r['facts']) + len(r['frontier']) > 128 for r in document['results'])):
        _fail('format_budget_exceeded')
    if _measure(document) > 65536 or len(canonical_bytes(document)) + 1 > 4194304:
        _fail('format_budget_exceeded')


def _gap(subject, name, detail, missing):
    _safe_text(detail)
    for text in missing:
        _safe_text(text)
    return dict(kind='FrontierItem', schemaVersion=1,
        id=record_id('g', [subject, name, detail]), subject=subject, gap=name,
        detail=detail, blockedBy=[], missingEvidence=missing, primitives=[],
        cost={}, leverage=0, reason=[], toolchain=TOOLCHAIN)


def _fact(subject, predicate, value, evidence):
    # Attribute the first byte-evidence item; no synthetic rule-only occurrence.
    evidence = [dict(p) for p in evidence]
    evidence[0].update(rule='airs.' + MODEL, ruleVersion='1')
    ident = record_id('f', [subject, predicate, value, 'airs.' + MODEL + '@1'])
    return dict(kind='Fact', schemaVersion=1, id=ident, subject=subject,
        predicate=predicate, value=value, status='authoritative', provenance=evidence,
        toolchain=TOOLCHAIN, revert='revert:' + ident)


def _unit(row):
    address = lambda pc: dict(kind='address', ref=hex(pc))
    d = row['declaration']
    missing = ['abi_admission', 'callee_throw_effect']
    if d['status'] == 'syntax_unresolved':
        missing.append('swift_declaration_syntax:' + d['reason'])
    frontier = _gap(address(row['call_pc']), 'unknownCalleeEffects',
        'imported_callee_abi_unqualified; symbol=' + row['symbol'] +
        '; declaration=' + d['status'] + ':' + (d['reason'] or 'none'), missing)
    call = _fact(address(row['call_pc']), 'callsTarget', hex(row['callee_stub_pc']),
                 [dict(kind='decodedInstruction', ref=hex(row['call_pc']))])
    p = row['import_provenance']
    evidence = [dict(kind='decodedInstruction', ref=hex(w['pc'])) for w in p['stub_words']]
    evidence.append(dict(kind='loaderRecord',
        ref=f"indirectSymbol[{p['stub_indirect_index']}]@{hex(row['callee_stub_pc'])}"))
    evidence.append(dict(kind='loaderRecord',
        ref=f"indirectSymbol[{p['pointer_indirect_index']}]@{hex(p['pointer_address'])}"))
    evidence.append(dict(kind='loaderRecord', ref=f"undefinedSymbol[{p['symbol_index']}]@0x0"))
    name = _fact(address(row['callee_stub_pc']), 'hasName', row['symbol'], evidence)
    return call, name, frontier


def _result(subject, disclosure):
    return dict(kind='PrimitiveResult', schemaVersion=1, primitive='airs.imports-facts',
        primitiveVersion='1', subject=subject, budget={}, outcome='narrowed',
        facts=[], frontier=list(disclosure))


def _envelope(identity, tool_version, completed, results):
    document = dict(kind='airs.navigator_results', formatVersion=1,
                    identity=identity, results=results)
    counts = file_counts(document)
    document['run'] = dict(producerName='AIRS', producerVersion=tool_version,
        contractVersion=1, completed=completed, toolchain=TOOLCHAIN,
        resultCount=counts['results'], factCount=counts['facts'],
        frontierCount=counts['frontier'], refusalCount=sum(r['outcome'] == 'refusal' for r in results))
    return document


def _pack(units, subject, identity, version, completed, disclosure, budget):
    """Greedy row placement; a fresh file resets only the stub-name cache."""
    files = []
    total_facts = exported = 0

    def fresh():
        results = [_result(subject, disclosure)]
        document = _envelope(identity, version, completed, results)
        return results, set(), file_counts(document), _measure(document), len(canonical_bytes(document)) + 1

    results, seen, counts, nodes, size = fresh()
    for call, name, frontier in units:
        # Child tree safety is checked even for a row eventually omitted.
        metrics = {id(record): (_measure(record, 4), len(canonical_bytes(record)))
                   for record in (call, name, frontier)}
        while True:
            additions = [call] if name['id'] in seen else [call, name]
            if total_facts + len(additions) > budget:
                if any(r['facts'] for r in results) or (not files and disclosure):
                    files.append(_envelope(identity, version, completed, results))
                return files, exported
            result = results[-1]
            new_result = len(result['facts']) + len(result['frontier']) + len(additions) + 1 > 128
            extra_nodes = extra_size = 0
            if new_result:
                result = _result(subject, [])
                extra_nodes = _measure(result, 2)
                extra_size = len(canonical_bytes(result)) + 1
            next_counts = dict(results=counts['results'] + int(new_result),
                facts=counts['facts'] + len(additions), frontier=counts['frontier'] + 1,
                provenance=counts['provenance'] + sum(len(f['provenance']) for f in additions))
            extra_nodes += sum(metrics[id(r)][0] for r in [*additions, frontier])
            extra_size += sum(metrics[id(r)][1] for r in [*additions, frontier])
            extra_size += len(additions) - 1 + bool(result['facts']) + bool(result['frontier'])
            extra_size += len('facts') - len(result['outcome'])
            extra_size += sum(len(str(next_counts[k])) - len(str(counts[k]))
                              for k in ('results', 'facts', 'frontier'))
            fits = (next_counts['results'] <= 128 and
                next_counts['facts'] + next_counts['frontier'] <= 1024 and
                next_counts['provenance'] <= 4096 and nodes + extra_nodes <= 65536 and
                size + extra_size <= 4194304)
            if not fits:
                if not any(r['facts'] for r in results):
                    _fail('format_budget_exceeded')
                files.append(_envelope(identity, version, completed, results))
                results, seen, counts, nodes, size = fresh()
                continue
            if new_result:
                results.append(result)
            result['facts'].extend(additions)
            result['frontier'].append(frontier)
            result['outcome'] = 'facts'
            counts, nodes, size = next_counts, nodes + extra_nodes, size + extra_size
            total_facts += len(additions)
            exported += 1
            seen.add(name['id'])
            break
    files.append(_envelope(identity, version, completed, results))
    return files, exported


def export_report(report, *, tool_version, max_facts=4000):
    """Return transport documents and row counts without accessing any binary."""
    if type(tool_version) is not str or not tool_version:
        _fail('invalid_tool_version')
    _safe_text(tool_version)
    if len(tool_version.encode()) > 128:
        _fail('invalid_tool_version')
    if type(max_facts) is not int or not 1 <= max_facts <= 4096:
        _fail('invalid_max_facts')
    _json_value(report, report=True)
    if len(json.dumps(report, ensure_ascii=False, separators=(',', ':')).encode()) > MAX_INPUT_BYTES:
        _fail('input_byte_limit')
    image, rows = _validate(report)
    source = report['identity']
    identity = dict(containerSHA256=source['container_sha256'], sliceSHA256=source['slice_sha256'],
        sliceOffset=int(source['slice_offset'], 16), sliceSize=int(source['slice_size'], 16),
        cpuType=16777228, cpuSubtype=source['cpu_subtype'],
        uuid=str(uuid.UUID(source['uuid'])) if source['uuid'] is not None else None,
        preferredBase=source['preferred_base'])
    subject = dict(kind='image', ref=image)
    disclosure = []
    if report['omitted_calls']:
        disclosure.append(_gap(subject, 'budgetExceeded',
            f"omitted_calls={report['omitted_calls']}", ['omitted_call_rows']))
    for flag in COMPLETENESS:
        if not report[flag]:
            disclosure.append(_gap(subject, 'producerIncomplete', flag + '=false; import_stub_reason=' +
                (report['import_stub_reason'] or 'none'), [flag]))
    if not report['import_stubs_complete']:
        result = _result(subject, disclosure)
        result.update(outcome='refusal', refusal=dict(code='preconditionFailed',
            detail='import_stubs_complete=false; import_stub_reason=' + report['import_stub_reason'],
            retryable=False))
        documents = [_envelope(identity, tool_version, False, [result])]
        exported = 0
    else:
        if not rows:
            _fail('nothing_to_export')
        first, rest, seen = [], [], set()
        for row in sorted(rows, key=lambda r: r['call_pc']):
            (rest if row['callee_stub_pc'] in seen else first).append(row)
            seen.add(row['callee_stub_pc'])
        units = [_unit(row) for row in first + rest]
        completed = not disclosure
        documents, exported = _pack(units, subject, identity, tool_version, completed, disclosure, max_facts)
        if exported < len(rows):
            # Disclosure changes packing. A monotone fixed point includes its
            # exact counts before deciding file boundaries and name repetition.
            while True:
                item = _gap(subject, 'budgetExceeded',
                    f'exporter_fact_budget={max_facts}; exported_rows={exported}; omitted_rows={len(rows)-exported}',
                    ['omitted_call_rows'])
                documents, count = _pack(units, subject, identity, tool_version, False,
                                         disclosure + [item], max_facts)
                if count == exported:
                    break
                exported = count
    for document in documents:
        _check_file(document)
    return documents, dict(total_rows=len(rows), exported_rows=exported,
                          omitted_rows=len(rows)-exported,
                          completed=all(d['run']['completed'] for d in documents))


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail('duplicate_json_key')
        result[key] = value
    return result


def export_bytes(raw, *, tool_version, max_facts=4000):
    """Return named part bytes and manifest bytes, all prepared before writing."""
    if type(raw) is not bytes:
        _fail('invalid_input_bytes')
    if len(raw) > MAX_INPUT_BYTES:
        _fail('input_byte_limit')
    try:
        report = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                            parse_constant=lambda _: _fail('invalid_json_value'))
    except (ValueError, UnicodeError, RecursionError) as error:
        if isinstance(error, ExportError):
            raise
        _fail('malformed_json')
    documents, totals = export_report(report, tool_version=tool_version, max_facts=max_facts)
    files, entries = {}, []
    for i, document in enumerate(documents, 1):
        name = f'part-{i:04d}.airsnav'
        data = canonical_bytes(document) + b'\n'
        files[name] = data
        entries.append(dict(name=name, sha256=hashlib.sha256(data).hexdigest(), **file_counts(document)))
    manifest = dict(exporter_version=EXPORTER_VERSION, tool_version=tool_version,
        report_sha256=hashlib.sha256(raw).hexdigest(), files=entries,
        contract_digests=CONTRACT_DIGESTS, **totals)
    # Manifest keys deliberately include contract filenames, unlike record keys.
    metadata = json.dumps(manifest, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode() + b'\n'
    return files, metadata


def _no_symlinks(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        _fail('invalid_output_path')


def _write_directory(out, files, manifest):
    _no_symlinks(out)
    if out.exists():
        _fail('output_exists')
    staging = Path(tempfile.mkdtemp(prefix='.airs-facts-', dir=out.parent))
    try:
        for name, data in [*files.items(), ('manifest.json', manifest)]:
            with (staging / name).open('xb') as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        fd = os.open(staging, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        # Recheck immediately before the single visibility transition.
        _no_symlinks(out)
        if out.exists():
            _fail('output_exists')
        os.rename(staging, out)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--tool-version', required=True)
    parser.add_argument('--max-facts', type=int, default=4000)
    args = parser.parse_args(argv)
    try:
        source, out = args.report.absolute(), args.out.absolute()
        if source.resolve() == out.resolve() or out.resolve() in source.resolve().parents:
            _fail('path_collision')
        _no_symlinks(source)
        _no_symlinks(out)
        if out.exists():
            _fail('output_exists')
        fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                _fail('invalid_input_path')
            raw = handle.read(MAX_INPUT_BYTES + 1)
        files, manifest = export_bytes(raw, tool_version=args.tool_version, max_facts=args.max_facts)
        _write_directory(out, files, manifest)
    except ExportError as error:
        print(error.reason, file=sys.stderr)
        return 3 if error.reason == 'nothing_to_export' else 2
    except OSError:
        print('io_error', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
