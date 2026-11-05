#!/usr/bin/env python3
"""One-shot, local-only complete tracked-source + relocated evidence handback.

No compilation, disassembly, source/capture hashing, publication or delivery.
Execute only after the parent completes the separate source-boundary review.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import zipfile

ACCEPTED_BASELINE = '0b192429cbfb5583557c4c5f04017b1946141e4a'
SOURCE_LIMIT = 256 * 1024 * 1024
ZIP_LIMIT = 512 * 1024 * 1024
ENTRY_LIMIT = 20000
INPUT_LIMIT = 128 * 1024 * 1024
EVIDENCE_LIMIT = ZIP_LIMIT - SOURCE_LIMIT
PROCESSING_ALLOWANCE = 16 * 1024 * 1024 * 1024
JSON_TOKEN_LIMIT = 16_000_000
MAX_REVIEWS = 8
MAX_SWIFT_SOURCES = 8
TREE_ROW_LIMIT = 8192
GIT_CONTROL_LIMIT = 1024 * 1024
PATCH_LIMIT = 64 * 1024 * 1024
COMMIT_LIMIT = 4096
READINESS_SCOPE = 'implementation_qualification_reviews_source_export'
HANDOFF_SURFACES = frozenset(('baseline_to_head_patch', 'sanitized_commit_inventory',
                              'archive_root_handoff', 'scoped_sha256_manifest'))
MANDATORY_GATES = frozenset((
    'aggregate_work_complete', 'aggregate_retained_output_complete',
    'raw_compiler_challenge_scan_complete', 'unsupported_compiler_forms_disposition',
    'required_unsupported_challenges_observed', 'callsite_sessions_complete',
    'independent_image_ledgers_complete', 'source_420', 'source_methods_340',
    'source_category_minima', 'source_diversity_reconciled',
    'emitted_abi_shapes_80', 'physical_calls_1500', 'eligible_primary_witnesses_250',
    'seven_families_15_each', 'positive_emitted_geometries_10',
    'observed_emitted_challenges_12', 'result_lowerings_8',
    'negative_300_zero_false_eligible', 'fresh_raw_coordinate_attacks',
    'negative_attack_kind_coverage', 'seven_family_negative_controls', 'stratified_100_identical',
    'second_compiler_positive', 'two_whole_branch_reviews', 'measured_latency_rss'))

REMOVED_KEYS = {'dev', 'ino', 'device', 'inode', 'devino', 'mtime_ns', 'ctime_ns',
                'started_unix', 'finished_unix', 'duration_seconds'}
FORBIDDEN_PARTS = {'.git', '.build', '__pycache__', 'local-evidence', '.venv',
                   'node_modules', '.pytest_cache', 'DerivedData', 'module-cache',
                   'compiler-tmp', '.DS_Store'}
PRIVATE_PATH = re.compile(r'(?:/Us' r'ers/|/ho' r'me/|/Applications/|/Library/Developer/|/Volumes/|/private/(?:var|tmp)/|/var/(?:folders|tmp)/|/tmp/|[A-Za-z]:\\Users\\)')


class PackageError(ValueError):
    pass


def git(root, *args):
    process = subprocess.Popen(['git', '-C', str(root), *args], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        data = process.stdout.read(GIT_CONTROL_LIMIT + 1)
        if len(data) > GIT_CONTROL_LIMIT: raise PackageError('Git control output bound exceeded')
        if process.wait(): raise PackageError('Git control query failed')
        return data
    except BaseException:
        process.kill(); process.wait(); raise
    finally: process.stdout.close()


def safe_name(name):
    path = PurePosixPath(name)
    if not name or '\\' in name or name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/')):
        raise PackageError('Unsafe archive member')
    if re.match(r'^[A-Za-z]:', name) or any(ord(c) < 32 for c in name):
        raise PackageError('Unsafe archive member')
    return path


def assert_portable(text):
    if PRIVATE_PATH.search(text):
        raise PackageError('Unrelocated private path in new export view; details withheld')


class EvidenceBudget:
    """Separate bounded processing charges from retained serialized bytes.

    Processing charges conservatively count repeated conversion/allocation work;
    they are neither disk bytes nor measured/guaranteed peak RSS. Raw inputs and
    retained serialized evidence each keep their independent 256 MiB caps.
    """
    def __init__(self, limit=PROCESSING_ALLOWANCE, entry_limit=ENTRY_LIMIT,
                 serialized_limit=EVIDENCE_LIMIT, input_limit=EVIDENCE_LIMIT):
        self.limit, self.used, self.entries, self.entry_limit = limit, 0, 0, entry_limit
        self.serialized_limit, self.serialized_used = serialized_limit, 0
        self.input_limit, self.input_used = input_limit, 0

    def reserve(self, amount):
        if amount < 0 or amount > self.limit - self.used:
            raise PackageError('Evidence processing allowance exceeded')
        self.used += amount

    def reserve_input(self, amount):
        if amount < 0 or amount > self.input_limit - self.input_used:
            raise PackageError('Aggregate raw evidence input bound exceeded')
        self.reserve(amount); self.input_used += amount

    def check_buffer(self, size):
        if size < 0 or size > self.serialized_limit - self.serialized_used:
            raise PackageError('Retained serialized evidence bound exceeded')

    def retain(self, size):
        self.check_buffer(size); self.serialized_used += size

    def entry(self):
        if self.entries >= self.entry_limit: raise PackageError('Evidence entry bound exceeded')
        self.entries += 1


class EvidencePayload(dict):
    """Retain each new byte payload once under the shared serialized cap."""
    def __init__(self,budget):
        super().__init__(); self.budget = budget

    def __setitem__(self,key,value):
        if key in self or not isinstance(value,bytes): raise PackageError('Duplicate/nonbyte evidence payload')
        self.budget.retain(len(value))
        super().__setitem__(key,value)


def read_bytes(path, maximum=INPUT_LIMIT, budget=None):
    if Path(path).is_symlink(): raise PackageError('Evidence symlink refused')
    with Path(path).open('rb') as stream:
        import os
        size = os.fstat(stream.fileno()).st_size
        if size > maximum: raise PackageError('Evidence input exceeds bound')
        if budget: budget.reserve_input(size + 1)
        data = stream.read(size + 1)
    if len(data) != size: raise PackageError('Evidence input changed during read')
    return data


def reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise PackageError('Duplicate JSON object key')
        result[key] = value
    return result


def reject_nonfinite(value):
    raise PackageError('Nonfinite JSON value')


def finite_float(value):
    number = float(value)
    if not math.isfinite(number): raise PackageError('Nonfinite JSON number')
    return number


def read_json(path, maximum=INPUT_LIMIT, budget=None):
    data = read_bytes(path, maximum, budget)
    if budget: budget.reserve(len(data) * 4)
    text = data.decode('utf-8')
    depth = 0; quoted = False; escaped = False; tokens = 0; scalar = False
    for ch in text:
        if quoted:
            if escaped: escaped = False
            elif ch == '\\': escaped = True
            elif ch == '"': quoted = False
        elif ch == '"': quoted = True; tokens += 1; scalar = False
        elif ch in '[{':
            depth += 1; tokens += 1; scalar = False
            if depth > 64: raise PackageError('Evidence JSON depth exceeds bound')
        elif ch in ']}': depth -= 1; scalar = False
        elif ch in ',:' or ch.isspace(): scalar = False
        elif not scalar: tokens += 1; scalar = True
        if tokens > JSON_TOKEN_LIMIT: raise PackageError('JSON token bound exceeded')
    # Account for parsed strings/containers before the JSON parser creates them.
    if budget: budget.reserve(len(data) * 4 + tokens * 64)
    result = json.loads(text, object_pairs_hook=reject_duplicate_pairs, parse_constant=reject_nonfinite, parse_float=finite_float)
    if not isinstance(result, dict): raise PackageError('JSON evidence object required')
    return result


def decoded_text(data, budget):
    budget.reserve(len(data) * 4)
    return data.decode('utf-8')


def bounded_text_bytes(text, budget):
    assert_portable(text)
    output = bytearray()
    for offset in range(0,len(text),4096):
        budget.reserve(min(4096,len(text)-offset)*8)
        chunk = text[offset:offset+4096].encode('utf-8')
        budget.check_buffer(len(output)+len(chunk))
        output.extend(chunk)
    budget.reserve(len(output))
    return bytes(output)


def bounded_json_bytes(value, budget, replacements=None):
    """Incremental JSON tokens; no unbounded dumps or full sanitized copy."""
    encoder = json.JSONEncoder(ensure_ascii=True, allow_nan=False, separators=(',', ':'))
    output = bytearray()
    def emit(text):
        budget.check_buffer(len(output)+len(text))
        budget.reserve(len(text))
        output.extend(text.encode('ascii'))
    def string(value, relocate=True):
        # Replacement and escaping reservations precede those allocations.
        if relocate and replacements is not None: value = relocate_text(value, replacements, budget)
        budget.reserve(len(value) * 12 + 2)
        # Escape fixed-size chunks: a large valid JSON string never creates an
        # unchecked whole-string escaped buffer before the serialized cap.
        emit('"')
        for offset in range(0,len(value),4096):
            budget.reserve(min(4096,len(value)-offset)*16+2)
            escaped = encoder.encode(value[offset:offset+4096])
            emit(escaped[1:-1])
        emit('"')
    def visit(value):
        if isinstance(value, dict):
            budget.reserve(216); seen_keys = set()
            emit('{'); first = True
            for key, item in value.items():
                if replacements is not None and (key in REMOVED_KEYS or 'custody' in str(key).lower()): continue
                if not isinstance(key, str): raise PackageError('JSON object key must be text')
                converted = relocate_text(key, replacements, budget) if replacements is not None else key
                budget.reserve(len(converted) * 4 + 72)
                if converted in seen_keys: raise PackageError('Relocated JSON object key collision')
                seen_keys.add(converted)
                if not first: emit(',')
                first = False; string(converted, relocate=False); emit(':'); visit(item)
            emit('}')
        elif isinstance(value, list):
            emit('[')
            for index, item in enumerate(value):
                if index: emit(',')
                visit(item)
            emit(']')
        elif isinstance(value, str): string(value)
        else:
            for chunk in encoder.iterencode(value): emit(chunk)
    visit(value); emit('\n')
    budget.reserve(len(output))
    return bytes(output)


def bounded_view_bytes(value, replacements, budget):
    return bounded_json_bytes({'view': 'SANITIZED/RELOCATED',
        'attestation': 'Derived portable view; not a new cryptographic attestation. Existing digests copied, not recomputed. Custody and filesystem metadata removed.',
        'record': value}, budget, replacements)


def portable_command(command):
    """All captured operands are relative after relocation, including -I/path."""
    if not command or len(command) > 256: raise PackageError('Compiler command bound exceeded')
    path_flags = {'-I', '-F', '-L', '-iquote', '-isystem', '-idirafter', '-iframework',
                  '-include', '-imacros', '-iprefix', '-iwithprefixbefore', '-iwithprefix', '-B', '-sdk', '-isysroot', '-o', '-module-cache-path',
                  '-resource-dir', '-working-directory', '-vfsoverlay', '-filelist',
                  '-import-objc-header', '-emit-module-path', '-emit-module-interface-path',
                  '-emit-private-module-interface-path', '-emit-objc-header-path',
                  '-index-store-path', '-debug-prefix-map', '-file-prefix-map'}
    attached = ('-I', '-F', '-L', '-iquote', '-isystem', '-idirafter', '-iframework',
                '-include', '-imacros', '-iprefix', '-iwithprefixbefore', '-iwithprefix',
                '-B', '-o', '-sdk', '-isysroot', '-module-cache-path=',
                '-resource-dir=', '-working-directory=', '-vfsoverlay=', '-o=')
    def relative(value):
        if value.startswith(('https://', 'http://')): return
        if value.startswith('@'):
            value = value.lstrip('@')
            if not value: raise PackageError('Empty compiler response operand')
        if value.startswith(('/', '~', '\\')) or re.match(r'^[A-Za-z]:', value):
            raise PackageError('Absolute compiler command operand remains after relocation')
        if '..' in PurePosixPath(value).parts or '\\' in value:
            raise PackageError('Unsafe compiler path operand')
        if any(separator in value for separator in '=,#'):
            for part in re.split('[=,#]', value): relative(part)
    pending = False
    for index, argument in enumerate(command):
        if not isinstance(argument, str) or len(argument) > 8192 or any(ord(c) < 32 for c in argument):
            raise PackageError('Compiler argument bound exceeded')
        if pending: relative(argument); pending = False; continue
        if argument in path_flags: pending = True; continue
        found = next((prefix for prefix in attached if argument.startswith(prefix) and argument != prefix), None)
        if found: relative(argument[len(found):]); continue
        if argument.startswith('-') and '=' in argument:
            # Includes prefix maps and plugin/SDK options not enumerated above.
            for operand in argument.split('=')[1:]: relative(operand)
        elif argument.startswith('-') and ',' in argument:
            for operand in argument.split(',')[1:]: relative(operand)
        elif argument.startswith('-') and ('/' in argument or '\\' in argument):
            raise PackageError('Unrecognized joined compiler path option')
        elif not argument.startswith('-') or index == 0: relative(argument)
    if pending: raise PackageError('Missing compiler path operand')
    return command


def relocations(captures, receipts, supplied):
    replacements = dict(supplied)
    for label, directory in captures.items():
        replacements[str(directory.resolve())] = f'captures/{label}'
        receipt = receipts[label]
        compiler, sdk = receipt.get('swiftc'), receipt.get('sdk')
        if not isinstance(compiler, str) or not compiler.startswith('/'):
            raise PackageError('Captured compiler identity required')
        # Replace specific toolchain prefix, preserving tool name and identity in
        # captured compiler version. Each capture has its own relocation root.
        replacements[str(Path(compiler).parent)] = f'toolchains/{label}/bin'
        if isinstance(sdk, str) and sdk.startswith('/'):
            replacements[sdk] = f'sdks/{label}/MacOSX.sdk'
    for old, new in replacements.items():
        if not old.startswith('/') or not new or new.startswith('/'):
            raise PackageError('Relocation requires absolute input and relative output')
        safe_name(new)
    return sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True)


def relocate_text(text, replacements, budget=None):
    for old, new in replacements:
        if old not in text: continue
        if budget: budget.reserve(max(0, len(text) + text.count(old) * (len(new) - len(old))) * 4)
        text = text.replace(old, new)
    assert_portable(text)
    return text


def sanitize(value, replacements):
    if isinstance(value, dict):
        return {relocate_text(str(k), replacements): sanitize(v, replacements)
                for k, v in value.items()
                if k not in REMOVED_KEYS and 'custody' not in k.lower()}
    if isinstance(value, list):
        return [sanitize(v, replacements) for v in value]
    if isinstance(value, str):
        return relocate_text(value, replacements)
    return value


def relocated_view(value, replacements):
    return {'view': 'SANITIZED/RELOCATED',
            'attestation': 'Derived portable view of retained evidence; not a new cryptographic attestation. Existing digests are copied, not recomputed. Local custody and filesystem metadata removed.',
            'record': sanitize(value, replacements)}


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def add_source_tar(source, destination, maximum=SOURCE_LIMIT, expected_names=None):
    """Bounded stream adapter shared by exact Git blobs and synthetic tar tests."""
    total = count = 0
    names = set(); files = set()
    for member in source:
        name = member.name.rstrip('/')
        path = safe_name(name)
        if any(p in FORBIDDEN_PARTS for p in path.parts) or path.name in {'.env', '.netrc', '.npmrc'} or path.suffix in {'.pyc', '.p12', '.p8', '.key'}:
            raise PackageError('Unshippable tracked member; source clearance required')
        count += 1; total += member.size
        if count > ENTRY_LIMIT or total > maximum:
            raise PackageError('Source archive exceeds bound')
        if name in names:
            raise PackageError('Duplicate source member')
        names.add(name)
        if member.isdir(): continue
        if not member.isfile():
            raise PackageError('Source link or special member requires separate qualification')
        files.add(name)
        entry = zipfile.ZipInfo('AIRS/source/' + name)
        entry.compress_type = zipfile.ZIP_DEFLATED
        entry.external_attr = (member.mode & 0o777) << 16
        with source.extractfile(member) as incoming, destination.open(entry, 'w') as outgoing:
            remaining = member.size
            while remaining:
                chunk = incoming.read(min(1024 * 1024, remaining))
                if not chunk: raise PackageError('Truncated source member')
                outgoing.write(chunk); remaining -= len(chunk)
    if expected_names is not None and files != set(expected_names):
        raise PackageError('Source stream differs from complete tracked tree')
    return {'source_entries': count, 'source_bytes': total}


class GitBlobSource:
    """Expose committed blobs through a tar-like bounded adapter, without a tar.

    ls-tree identities and git-show streams avoid export-ignore/export-subst,
    global attributes and loose working files. No source digest is recomputed.
    """
    def __init__(self, root, rows):
        self.root, self.rows, self.process = root, rows, None

    def __iter__(self):
        for name, mode, oid, size in self.rows:
            member = tarfile.TarInfo(name); member.mode = int(mode, 8) & 0o777; member.size = size
            member.pax_headers['blob_oid'] = oid
            yield member

    def extractfile(self, member):
        self.process = subprocess.Popen(['git', '-C', str(self.root), 'show', member.pax_headers['blob_oid']],
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        owner = self
        class BlobReader:
            def __enter__(self): return self
            def read(self, size): return owner.process.stdout.read(size)
            def __exit__(self, kind, value, traceback):
                if kind is not None:
                    owner.process.kill()
                elif owner.process.stdout.read(1):
                    owner.process.kill(); owner.process.wait(); owner.process.stdout.close()
                    raise PackageError('Source blob exceeds declared size')
                code = owner.process.wait(); owner.process.stdout.close()
                if kind is None and code: raise PackageError('Committed source blob stream failed')
        return BlobReader()


def validate_identity(root, head, qualified_revision):
    head = git(root, 'rev-parse', '--verify', head + '^{commit}').decode().strip()
    qualified_revision = git(root, 'rev-parse', '--verify', qualified_revision + '^{commit}').decode().strip()
    # Conservatively bind executable engine, native targets and root build files.
    # Only explicitly non-engine additions may follow the qualified revision.
    paths = git(root, 'diff', '--name-only', qualified_revision, head, '--').decode().splitlines()
    for path in paths:
        if not (path.startswith(('docs/', 'tests/')) or path in {
            'scripts/package_swift_broad_handback.py', 'README.md', 'CHANGELOG.md'}):
            raise PackageError('Package differs from qualified engine; new qualification required')
    return head, qualified_revision


def check_clearance(clearance, head):
    if (clearance.get('accepted_baseline') != ACCEPTED_BASELINE
            or clearance.get('package_head') != head
            or clearance.get('state') != 'passed'
            or clearance.get('scope') != 'complete_tracked_source_and_new_export_metadata'
            or clearance.get('accepted_baseline_reused') is not True):
        raise PackageError('Exact source/export clearance required')


def capture_sources(directory):
    sources = []
    for source in directory.glob('*.swift'):
        if len(sources) >= MAX_SWIFT_SOURCES: raise PackageError('Owned source file count bound exceeded')
        sources.append(source)
    if not sources: raise PackageError('Owned fixture source missing')
    return sources


def capture_payload(label, directory, receipt, replacements, payload, budget, sources=None):
    """Fixed bounded evidence list, with reservations before every conversion."""
    if sources is None: sources = capture_sources(directory)
    modes = receipt.get('modes', {})
    if not isinstance(modes, dict) or not modes or len(modes) > 3:
        raise PackageError('Captured optimization modes required')
    for name in ('source-manifest.json', 'compiler-index.json'):
        budget.entry()
        record = read_json(directory / name, budget=budget)
        payload[f'captures/{label}/{name}'] = bounded_view_bytes(record, replacements, budget)
    budget.entry()
    payload[f'captures/{label}/compile-receipt.json'] = bounded_view_bytes(receipt, replacements, budget)
    for source in sorted(sources):
        budget.entry()
        text = decoded_text(read_bytes(source, budget=budget), budget)
        text = relocate_text(text, replacements, budget)
        payload[f'captures/{label}/{source.name}'] = bounded_text_bytes(text, budget)
    commands = ['# SANITIZED/RELOCATED captured argument vectors',
                '# Run from AIRS/evidence with relocated matching compiler/SDK.',
                '# Reproduction does not recreate historical attestation.', '']
    import shlex
    for mode, row in modes.items():
        if not re.fullmatch(r'[A-Za-z0-9_-]+', mode): raise PackageError('Unsafe mode')
        command = row.get('command')
        if not isinstance(command, list) or len(command) > 256 or not all(isinstance(x, str) for x in command):
            raise PackageError('Captured compiler argument vector required')
        converted = [relocate_text(argument, replacements, budget) for argument in command]
        portable_command(converted)
        budget.reserve(sum(len(arg) * 4 + 3 for arg in converted))
        commands.append(' '.join(shlex.quote(arg) for arg in converted))
        for kind, extension in (('nm', 'txt'), ('objdump', 'txt'), ('compile', 'log')):
            budget.entry(); name = f'{kind}-{mode}.{extension}'
            text = decoded_text(read_bytes(directory / name, budget=budget), budget)
            text = relocate_text(text, replacements, budget)
            budget.reserve(len(text) * 4 + 128)
            payload[f'captures/{label}/{name}'] = bounded_text_bytes('# SANITIZED/RELOCATED captured tool output; digests not recomputed.\n' + text, budget)
    budget.entry(); budget.reserve(sum(len(command) * 4 + 4 for command in commands))
    payload[f'captures/{label}/REPRODUCE.sh'] = bounded_text_bytes('\n'.join(commands) + '\n', budget)


def stream_tree_rows(stream, entry_limit=ENTRY_LIMIT, source_limit=SOURCE_LIMIT, byte_limit=16 * 1024 * 1024):
    """Read bounded NUL rows, never materializing an unchecked tree listing."""
    count = total = consumed = 0
    while True:
        row = bytearray()
        while True:
            chunk = stream.read(1)
            if not chunk:
                if row: raise PackageError('Truncated source tree row')
                return
            consumed += 1
            if consumed > byte_limit: raise PackageError('Source tree listing byte bound exceeded')
            if chunk == b'\0': break
            if len(row) >= TREE_ROW_LIMIT: raise PackageError('Source tree row bound exceeded')
            row.extend(chunk)
        count += 1
        if count > entry_limit: raise PackageError('Tracked source entry bound exceeded')
        metadata, raw_name = bytes(row).split(b'\t', 1)
        mode, kind, oid, raw_size = metadata.split()
        if kind != b'blob' or mode not in (b'100644', b'100755'):
            raise PackageError('Tracked links/submodules require separate qualification')
        name = raw_name.decode('utf-8'); safe_name(name)
        size = int(raw_size); total += size
        if size < 0 or total > source_limit: raise PackageError('Tracked source byte bound exceeded')
        yield name, mode.decode(), oid.decode(), size


def source_tree(root, head, reserved_entries=0):
    process = subprocess.Popen(['git', '-C', str(root), 'ls-tree', '-rlz', '--full-tree', head],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        rows = list(stream_tree_rows(process.stdout, entry_limit=ENTRY_LIMIT - reserved_entries))
        if process.wait(): raise PackageError('Source tree enumeration failed')
        return rows
    except BaseException:
        process.kill(); process.wait(); raise
    finally: process.stdout.close()


def completeness(qualification, ledger, review_paths, reviews, revision):
    gates = qualification.get('gates')
    if (qualification.get('schema') != 'airs.swift-broad-qualification.v1'
            or qualification.get('state') != 'qualified' or not isinstance(gates, dict)
            or not MANDATORY_GATES <= gates.keys() or not all(v is True for v in gates.values())
            or ledger.get('state') != 'ready' or ledger.get('scope') != READINESS_SCOPE
            or ledger.get('remaining_work') != []
            or not isinstance(ledger.get('task_remaining_work'), list)):
        return False
    if len({str(path.resolve()) for path in review_paths}) < 2: return False
    identities = set()
    for review in reviews:
        if (not isinstance(review, dict) or review.get('scope') != 'whole_broad_branch'
                or review.get('decision') != 'passed' or review.get('unresolved_findings') != []
                or review.get('source_revision') != revision
                or not isinstance(review.get('correction_history'), list)
                or not isinstance(review.get('reviewer'), str) or not review['reviewer'].strip()):
            return False
        identities.add(review['reviewer'])
    return len(identities) >= 2


def reserve_operation(output, marker, identity):
    # Inspect lexical paths before resolution so dangling symlinks also refuse.
    sidecar=output.with_name(output.name+'.sha256.json')
    if any(path.exists() or path.is_symlink() for path in (output,marker,sidecar)):
        raise PackageError('Existing output/start marker forbids replacement or retry')
    output.parent.mkdir(parents=True, exist_ok=True)
    marker.parent.mkdir(parents=True, exist_ok=True)
    with marker.open('x') as stream:
        json.dump({'state': 'STARTED_NO_AUTOMATIC_RETRY', **identity}, stream)


def git_patch(root,head,budget):
    """Complete endpoint diff, including binary data; no intermediate snapshots."""
    git(root,'merge-base','--is-ancestor',ACCEPTED_BASELINE,head)
    process=subprocess.Popen(['git','-C',str(root),'diff','--binary','--full-index',
        '--no-ext-diff','--no-textconv','--no-renames','--no-color','--no-relative','--submodule=short','--src-prefix=a/',
        '--dst-prefix=b/',ACCEPTED_BASELINE,head,'--'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    result=bytearray()
    try:
        while True:
            # Reserve both read buffer and bytearray growth before allocation.
            capacity=min(65536,PATCH_LIMIT-len(result)+1);budget.reserve(capacity*2)
            chunk=process.stdout.read(capacity)
            if not chunk:break
            if len(result)+len(chunk)>PATCH_LIMIT:raise PackageError('Complete patch exceeds bound')
            budget.check_buffer(len(result)+len(chunk))
            result.extend(chunk)
        if process.wait():raise PackageError('Complete baseline patch failed')
        budget.reserve(len(result));return bytes(result)
    except BaseException:
        process.kill();process.wait();raise
    finally:process.stdout.close()


def commit_inventory(root,head,replacements,budget):
    # %H and %s only: never author/committer/email, bodies, dates or .git.
    budget.reserve(GIT_CONTROL_LIMIT+1)
    raw=git(root,'log','--reverse','--topo-order','--format=%H%x00%s%x00',ACCEPTED_BASELINE+'..'+head,'--')
    budget.reserve(len(raw)*8+1)
    fields=raw.decode('utf-8').split('\0');records=[]
    if fields[-1].strip():raise PackageError('Truncated commit inventory')
    fields.pop()
    if len(fields)%2:raise PackageError('Malformed commit inventory')
    for index in range(0,len(fields),2):
        if len(records)>=COMMIT_LIMIT:raise PackageError('Commit count bound exceeded')
        sha,subject=fields[index].strip(),fields[index+1]
        if not re.fullmatch('[0-9a-f]{40}',sha) or any(ord(ch)<32 for ch in subject):
            raise PackageError('Malformed commit subject/identity')
        subject=relocate_text(subject,replacements,budget)
        # Subjects are retained as sanitized metadata, never contact records.
        budget.reserve(len(subject)*12+32)
        subject=re.sub(r'[A-Za-z0-9_.+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', '[redacted email]',subject)
        budget.reserve(len(subject)*4+256)
        records.append(dict(sha=sha,subject=subject))
    return dict(accepted_baseline=ACCEPTED_BASELINE,package_head=head,
        order='git reverse topological order for baseline..head',commits=records,
        scope='SHA and sanitized subject only; no authors, emails, bodies, raw intermediate files or Git database')


def reused_sha256_manifest(receipts,archive_name):
    safe_name(archive_name)
    if not 1 <= len(receipts) <= 3: raise PackageError('Capture count bound exceeded')
    records=[]
    for label,receipt in sorted(receipts.items()):
        source_file=receipt.get('source_file','BroadOwned.swift' if label != 'supplemental' else None)
        if not isinstance(source_file,str) or '/' in source_file or '\\' in source_file:
            raise PackageError('Original owned source filename required')
        safe_name(source_file)
        values=[('original owned source',source_file,receipt.get('source_sha256'),None)]
        modes=receipt.get('modes',{})
        if not isinstance(modes,dict) or not 1<=len(modes)<=3:raise PackageError('Digest receipt mode count')
        for mode,row in sorted(modes.items()):
            name=row.get('library')
            if not isinstance(name,str):raise PackageError('Captured library name required')
            safe_name(name)
            values.append(('original emitted image',name,row.get('emitted_sha256'),mode))
        for kind,name,digest,mode in values:
            if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):
                raise PackageError('Existing captured SHA-256 required; never regenerate it')
            records.append(dict(capture=label,original_artifact=name,kind=kind,mode=mode,
                sha256=digest,status='REUSED_CAPTURED_IDENTITY',
                receipt_view='captures/'+label+'/compile-receipt.json',
                covers='original captured bytes only; NOT relocated archive members'))
    return dict(schema='airs.swift-broad-sha256-manifest.v1',algorithm='SHA-256',records=records,
        coverage='saved original source/image identities only; no per-member digest coverage',
        unhashed_members='source snapshot, patch, commit inventory, handoff and all relocated evidence views',
        final_archive=dict(status='UNSEALED_BY_PACKAGER',suggested_sidecar=archive_name+'.sha256.json',
            scope='A separate explicitly authorized first seal may identify the newly created ZIP; no digest exists here.',
            digest_inside_archive=False),
        no_source_or_capture_rehash=True)


def check_handoff_clearance(clearance):
    surfaces = clearance.get('additional_export_surfaces')
    if (not isinstance(surfaces, list) or not all(isinstance(item,str) for item in surfaces)
            or not HANDOFF_SURFACES <= set(surfaces)):
        raise PackageError('Patch, inventory, handoff and digest-scope export clearance required')


def handoff_text(head, qualified, state, ledger, qualification, replacements, budget):
    gates = qualification.get('gates', {})
    if not isinstance(gates,dict): gates = {}
    pending = {'readiness_scope': ledger.get('scope'),
        'readiness_state': ledger.get('state'),
        'in_scope_remaining_work': ledger.get('remaining_work', 'NOT PROVIDED'),
        'whole_task_remaining_work': ledger.get('task_remaining_work', 'NOT PROVIDED'),
        'false_or_missing_qualification_gates': sorted(MANDATORY_GATES - gates.keys()) +
            sorted(key for key,value in gates.items() if value is not True)}
    pending_text = decoded_text(bounded_json_bytes(pending, budget, replacements), budget)
    sections = ["# AIRS broad Swift handoff\n\n",
        f"Package-content readiness: {state}. Delivery: STAGED LOCAL ONLY. Whole-task completion is not established by this archive.\n\n",
        f"Accepted baseline: `{ACCEPTED_BASELINE}`. Package head: `{head}`. Engine-qualified revision: `{qualified}`.\n\n",
        "Relative navigation after opening/extracting this portable archive:\n\n",
        "- Complete source/tests/owned fixtures/schemas: `AIRS/source/`.\n",
        "- Complete baseline-to-head textual/binary patch: `AIRS/changes/BASELINE-TO-HEAD.patch`.\n",
        "- Commit SHA and sanitized subjects only: `AIRS/changes/COMMITS.json`.\n",
        "- Qualification observations/gates: `AIRS/evidence/qualification.json`.\n",
        "- Scoped readiness and whole-task remaining work: `AIRS/evidence/check-ledger.json`.\n",
        "- Independent reviews: `AIRS/evidence/reviews/`.\n",
        "- Captured source/compiler/index/raw PC/word views and reproduction commands: `AIRS/evidence/captures/`.\n",
        "- Scope: `AIRS/source/docs/swift/BROAD_SCOPE.md`.\n",
        "- Qualification: `AIRS/source/docs/swift/BROAD_QUALIFICATION.md`.\n",
        "- Porting: `AIRS/source/docs/swift/BROAD_PORTING.md`.\n",
        "- Inventory and export clearance: `AIRS/evidence/MANIFEST.json`, `AIRS/evidence/source-clearance.json`.\n",
        "- Scoped reused SHA-256 identities: `AIRS/evidence/SHA256-MANIFEST.json`.\n\n",
        "## Readiness and exact remaining work\n\n```json\n", pending_text, "```\n\n",
        "The readiness ledger covers implementation, qualification, reviews and source/export readiness only. Packaging and delivery remain separate whole-task items. This archive cannot mark the overall objective complete. A local path is not cross-device delivery.\n\n",
        "## Evidence reuse and digest coverage\n\n",
        "Accepted baseline and existing source/image SHA-256 receipts are reused without hashing unchanged source/captures. SANITIZED/RELOCATED evidence views are not new cryptographic attestations. SHA256-MANIFEST.json covers original captured identities only; it does not claim per-member or whole-archive hashes. This packager computes no digest. A separate authorized first ZIP seal may create an adjacent sidecar after the new artifact exists; the ZIP cannot contain its own final hash.\n\n",
        "## Boundaries and next steps\n\n",
        "Reconcile every false/missing gate and remaining-work item. Preserve one-shot markers; no automatic repeat is authorized. Confirm the first local artifact operation, then use an explicitly authorized private delivery destination and verify its destination metadata. No upload, release, publication or cross-device delivery is implied here. Captured dylibs are omitted pending portable clearance. Structural conditional evidence does not establish runtime execution, catch semantics, exclusive entry, source reconstruction, clinical acceptance or native/release acceptance. Later documentation/package commits do not requalify the engine.\n"]
    budget.reserve(sum(len(section)*4 for section in sections))
    return ''.join(sections)


def handback_surfaces(root, head, qualified, state, ledger, qualification, receipts,
                      replacements, budget, archive_name):
    """Mandatory new surfaces; patch bytes remain exact and separately reviewed."""
    extra = EvidencePayload(budget)
    budget.entry(); extra['AIRS/changes/BASELINE-TO-HEAD.patch'] = git_patch(root, head, budget)
    budget.entry(); extra['AIRS/changes/COMMITS.json'] = bounded_json_bytes(
        commit_inventory(root, head, replacements, budget), budget)
    budget.entry(); extra['AIRS/evidence/SHA256-MANIFEST.json'] = bounded_json_bytes(
        reused_sha256_manifest(receipts, archive_name), budget)
    budget.entry(); extra['HANDOFF.md'] = bounded_text_bytes(
        handoff_text(head, qualified, state, ledger, qualification, replacements, budget), budget)
    return extra


def supplemental_lineage(qualification, receipt):
    declared = qualification.get('supplemental_capture_evidence')
    if declared is None or (isinstance(declared,dict) and declared.get('used') is False):
        if receipt is not None: raise PackageError('Supplemental input requires explicit qualification lineage')
        return False
    if (not isinstance(declared,dict) or declared.get('used') is not True
            or declared.get('role') != 'supplemental_challenge_only'):
        raise PackageError('Invalid supplemental qualification role')
    if receipt is None: raise PackageError('Qualification uses missing --supplemental-capture')
    if receipt.get('role') != 'supplemental_challenge_only':
        raise PackageError('Supplemental receipt role mismatch')
    modes = receipt.get('modes')
    if not isinstance(modes,dict) or not 1 <= len(modes) <= 3:
        raise PackageError('Supplemental captured mode lineage required')
    images = {mode: row.get('emitted_sha256') for mode,row in modes.items() if isinstance(row,dict)}
    source = receipt.get('source_sha256')
    if (not isinstance(source,str) or not re.fullmatch('[0-9a-f]{64}',source)
            or not all(isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) for value in images.values())
            or set(images) != set(modes) or declared.get('source_sha256') != source
            or declared.get('images') != images):
        raise PackageError('Supplemental original source/image lineage mismatch')
    return True


def archive_basename(name):
    if not isinstance(name,str) or not name.strip() or '..' in name or '/' in name or '\\' in name:
        raise PackageError('Archive name must be a safe single basename')
    safe_name(name)
    return name


def resolve_output_paths(args):
    """Reuse an explicit existing export directory; never register/create one."""
    directory = args.output_dir
    if directory is None:
        if args.archive_name is not None: raise PackageError('--archive-name requires --output-dir')
        if args.output is None: raise PackageError('An output mode is required')
        return args.output.absolute(), args.marker.absolute()
    if args.output is not None: raise PackageError('Output modes are mutually exclusive')
    if directory.is_symlink() or not directory.is_dir():
        raise PackageError('--output-dir must be an existing nonsymlink directory')
    directory = directory.absolute()
    output = directory / archive_basename(args.archive_name)
    marker = args.marker.absolute()
    if marker.parent != directory: raise PackageError('Directory-mode marker must be directly inside --output-dir')
    archive_basename(marker.name)
    if output.is_symlink(): raise PackageError('Archive basename cannot name a symlink')
    return output, marker


def build(args):
    if not args.execute_final_local:
        raise PackageError('Final local staging requires explicit --execute-final-local')
    output, marker = resolve_output_paths(args)
    if not 2 <= len(args.review) <= MAX_REVIEWS: raise PackageError('Review count bound requires two to eight records')
    if len(args.relocate_prefix) > 32: raise PackageError('Relocation count bound exceeded')
    captures = {'primary': args.primary_capture.resolve(), 'second': args.second_capture.resolve()}
    if args.supplemental_capture is not None:
        captures['supplemental'] = args.supplemental_capture.resolve()
    sources = {label: capture_sources(directory) for label, directory in captures.items()}
    budget = EvidenceBudget()
    root = args.root.resolve()
    qualification = read_json(args.qualification, budget=budget)
    head, qualified = validate_identity(root, args.head, qualification['source_revision'])
    if git(root, 'status', '--porcelain', '--untracked-files=no').strip():
        raise PackageError('Commit final tracked changes before staging')
    clearance = read_json(args.source_clearance, 1024 * 1024, budget)
    check_clearance(clearance, head)
    check_handoff_clearance(clearance)
    ledger = read_json(args.ledger, budget=budget)
    reviews = [read_json(path, 2 * 1024 * 1024, budget) for path in args.review]
    incomplete = not completeness(qualification, ledger, args.review, reviews, qualified)
    if incomplete and not args.allow_incomplete:
        raise PackageError('Incomplete gate/review records require explicit preservation-only --allow-incomplete')
    receipts = {label: read_json(path / 'compile-receipt.json', budget=budget) for label, path in captures.items()}
    supplemental_used = supplemental_lineage(qualification,receipts.get('supplemental'))
    supplied = {}
    for item in args.relocate_prefix:
        if '=' not in item: raise PackageError('Relocation must be ABSOLUTE=relative')
        if len(item) > 16384: raise PackageError('Relocation size bound exceeded')
        old, new = item.split('=', 1); supplied[old] = new
    replacements = relocations(captures, receipts, supplied)
    payload = EvidencePayload(budget)
    for label, directory in captures.items():
        capture_payload(label, directory, receipts[label], replacements, payload, budget, sources[label])
    for name, record in [('qualification.json', qualification), ('check-ledger.json', ledger),
                         ('source-clearance.json', clearance)]:
        budget.entry(); payload[name] = bounded_view_bytes(record, replacements, budget)
    for index, record in enumerate(reviews, 1):
        budget.entry()
        payload[f'reviews/review-{index:02}.json'] = bounded_view_bytes(record, replacements, budget)
    manifest = {'schema': 'airs.swift-broad-local-handback.v1',
                'state': 'INCOMPLETE' if incomplete else 'qualified_source_package_content_ready',
                'delivery': 'STAGED_LOCAL_ONLY; no cross-device delivery, upload, release or publication',
                'accepted_baseline': ACCEPTED_BASELINE, 'package_head': head,
                'engine_qualified_revision': qualified,
                'qualification_gates': qualification.get('gates'), 'check_ledger_state': ledger.get('state'),
                'check_ledger_scope': ledger.get('scope'), 'whole_task_completion': 'NOT_ESTABLISHED_BY_PACKAGER',
                'task_remaining_work': ledger.get('task_remaining_work'),
                'additional_export_surfaces': sorted(HANDOFF_SURFACES),
                'capture_roles': dict(primary='main_qualification',second='independent_compiler',
                    **({'supplemental':'supplemental_challenge_only'} if supplemental_used else {})),
                'supplemental_capture_evidence': qualification.get('supplemental_capture_evidence'),
                'source': 'Complete committed tracked tree from ls-tree/git-show blobs, all fixture formats; no Git database/raw private history; sanitized commit inventory separate.',
                'evidence': 'SANITIZED/RELOCATED views; original existing digests preserved without rehashing.',
                'executable_capture_artifacts': 'OMITTED: no portable binary clearance; owned sources, raw PC/word evidence, compiler/nm/objdump views and existing image digests retained.',
                'limits': {'source_bytes': SOURCE_LIMIT, 'zip_and_expanded_bytes': ZIP_LIMIT, 'entries': ENTRY_LIMIT,
                    'serialized_evidence_bytes': EVIDENCE_LIMIT, 'raw_evidence_input_bytes': EVIDENCE_LIMIT,
                    'processing_charge_allowance': PROCESSING_ALLOWANCE,
                    'processing_charge_scope':'cumulative conservative conversion/allocation work units, not peak RSS or disk bytes'},
                'limitations': ['Archive existence does not establish test, native acceptance or B1-B12 success.',
                                'No fresh compilation, disassembly, hashing, signature or dependency verification.',
                                'Source/export boundary clearance is a separate supplied parent record.',
                                'Portable views are not cryptographic attestations.']}
    budget.entry(); payload['MANIFEST.json'] = bounded_json_bytes(manifest, budget, replacements)
    budget.entry(); payload['README.txt'] = bounded_text_bytes(("AIRS broad Swift local handback\n"
        "STAGED LOCAL ONLY. Consult MANIFEST.json, qualification.json and check-ledger.json for actual gate states.\n"
        "Source: ../source (complete tracked committed snapshot, no history).\n"
        "Evidence views are SANITIZED/RELOCATED; original digests copied without recomputation.\n"
        "Executable capture dylibs are omitted pending separate portable clearance.\n"
        "Each capture retains owned Swift sources, source manifest, compiler-index raw instruction PCs/words, captured compiler version/target/flags, nm and objdump text.\n"
        "REPRODUCE.sh preserves captured command operands with relocated prefixes. Supply the matching compiler and SDK and create module-cache locally before running.\n"
        "Qualification commands and tests live in the complete source tree; evidence records retain the original executed work ledger.\n"
        "No upload, release, or phone delivery has occurred.\n"), budget)
    extras = handback_surfaces(root, head, qualified, manifest['state'], ledger, qualification,
                              receipts, replacements, budget, output.name)
    expanded = sum(map(len, payload.values())) + sum(map(len, extras.values()))
    total_entries = len(payload) + len(extras)
    if expanded > ZIP_LIMIT - SOURCE_LIMIT or total_entries > ENTRY_LIMIT:
        raise PackageError('Relocated evidence exceeds aggregate bound')
    for name, content in payload.items():
        safe_name(name)
        if re.search(PRIVATE_PATH.pattern.encode('ascii'), content):
            raise PackageError('Unrelocated private path in final new export view')
    # Bounded immutable identity/size enumeration, no source hashing.
    # The exact textual/binary patch is separately covered by parent clearance.
    # Do not redact its bytes: source tests can legitimately contain path-pattern literals.
    for name, content in extras.items():
        safe_name(name)
        if not name.endswith('.patch') and re.search(PRIVATE_PATH.pattern.encode('ascii'), content):
            raise PackageError('Private path in additional export metadata')
    source_rows = source_tree(root, head, total_entries)
    expected_names = {row[0] for row in source_rows}
    if len(expected_names) != len(source_rows): raise PackageError('Duplicate tracked source path')
    reserve_operation(output, marker, {'package_head': head,
                      'engine_qualified_revision': qualified, 'local_only': True})
    try:
        with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED, allowZip64=False) as archive:
            stats = add_source_tar(GitBlobSource(root, source_rows), archive, expected_names=expected_names)
            if stats['source_entries'] + total_entries > ENTRY_LIMIT or stats['source_bytes'] + expanded > ZIP_LIMIT:
                raise PackageError('Aggregate expanded archive bound exceeded')
            for name, content in sorted(extras.items()):
                archive.writestr(name, content)
                if output.stat().st_size > ZIP_LIMIT: raise PackageError('ZIP bound exceeded')
            for name, content in sorted(payload.items()):
                archive.writestr('AIRS/evidence/' + name, content)
                if output.stat().st_size > ZIP_LIMIT: raise PackageError('ZIP bound exceeded')
        if output.stat().st_size > ZIP_LIMIT: raise PackageError('ZIP bound exceeded')
    except BaseException:
        # Preserve a stopped partial as evidence; never auto-delete/retry/export.
        raise
    with marker.open('w') as stream:
        json.dump({'state': 'STAGED_LOCAL_ONLY', 'package_head': head,
                   'engine_qualified_revision': qualified, 'gates_state': manifest['state'], **stats}, stream)
    return manifest


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--head', default='HEAD')
    output_mode = p.add_mutually_exclusive_group(required=True)
    output_mode.add_argument('--output', type=Path, help='Legacy explicit output file')
    output_mode.add_argument('--output-dir', type=Path, help='Actual existing export root, also recognized by storage-guard')
    p.add_argument('--archive-name', help='Safe single filename; required with --output-dir only')
    for name in ('primary-capture', 'second-capture', 'qualification', 'ledger', 'source-clearance', 'marker'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--supplemental-capture',type=Path,help='Optional third challenge-only owned capture; requires matching declared lineage')
    p.add_argument('--review', action='append', type=Path, default=[])
    p.add_argument('--relocate-prefix', action='append', default=[], metavar='ABSOLUTE=relative')
    p.add_argument('--execute-final-local', action='store_true')
    p.add_argument('--allow-incomplete', action='store_true', help='Explicit preservation only; never completes B1-B12')
    return p


if __name__ == '__main__':
    try:
        result = build(parser().parse_args())
        print(json.dumps({'state': result['state'], 'delivery': result['delivery']}))
    except (PackageError, OSError, ValueError, subprocess.CalledProcessError, tarfile.TarError, zipfile.BadZipFile):
        raise SystemExit('Local staging refused; private details withheld. Preserve any start marker/partial; no automatic retry.')
