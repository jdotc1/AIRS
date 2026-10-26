#!/usr/bin/env python3
"""Bounded publication preflight. Never uploads, signs, executes inputs or rewrites history."""
import argparse
import base64
from collections import deque
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import subprocess
import sys
import tempfile
import zipfile

MAXIMUM_BYTES = 512 * 1024 * 1024
MAXIMUM_ENTRIES = 20000
MAX_ARCHIVE_LINK_STEPS = 8192
PUBLIC_EMAILS = {'138259519+jdotc1@users.noreply.github.com', 'noreply@github.com'}

class GateError(ValueError):
    pass


def inspect_bytes(data, label):
    # Upstream standard-library lookup defaults contain no account identity.
    # Admit only the complete quoted literals, never arbitrary home paths.
    shorthand_data = data
    for literal in (b'~/Library/Frameworks',
                    b'~/Library/Preferences/com.apple.LaunchServices/'):
        for quote in (b"'", b'"'):
            token = re.compile(rb'(?<!\\)' + re.escape(quote + literal + quote))
            shorthand_data = token.sub(lambda match: b' ' * len(match[0]), shorthand_data)
    # Construct patterns without embedding examples of forbidden private text.
    patterns = [
        rb'/(?:Users|home)/(?!example(?:/|\b))[^/\s\x00]+/',
        rb'~/(?:Developer|Documents|Desktop|Library)(?:/|\b)',
        rb'Developer/' + rb'Codex\b',
        rb'/(?:private/)?tmp/' + rb'claude-[^/\s]+',
        rb'-Users-(?!example\b)[A-Za-z0-9._-]+',
        rb'gh[pousr]_[A-Za-z0-9]{30,}',
        rb'homeDirectoryForCurrentUser[\s\S]{0,160}appendingPathComponent\("(?:Work|Developer[^"]*)"',
        rb'sk-(?:proj-)?[A-Za-z0-9_-]{24,}',
        rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    ]
    if any(re.search(pattern, shorthand_data if index == 1 else data, re.I)
           for index, pattern in enumerate(patterns)):
        raise GateError('Private publication marker detected; matching bytes withheld (' + label + ')')


def inspect_identity(email):
    if email not in PUBLIC_EMAILS:
        raise GateError('Unapproved public commit/tag identity; address withheld')


def inspect_message(message):
    inspect_bytes(message.encode(), 'message')
    if re.search(r'^Co-authored-by:', message, re.I | re.M):
        raise GateError('Unapproved co-author trailer')


def safe_name(name):
    value = PurePosixPath(name)
    if not name or '\\' in name or value.is_absolute() or '..' in value.parts:
        raise GateError('Unsafe archive or source member name')
    inspect_bytes(name.encode(), 'member name')


def inspect_asset(path, maximum_bytes=MAXIMUM_BYTES):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise GateError('Asset must be a regular file')
    if path.stat().st_size > maximum_bytes:
        raise GateError('Asset exceeds the bounded inspection size')
    with path.open('rb') as stream:
        data = stream.read(maximum_bytes + 1)
    inspect_payload(data, path.name, maximum_bytes)



def archive_link_graph(archive, members):
    """Canonical ZIP namespace, including implicit directories; no extraction."""
    nodes = {}; links = {}
    for member in members:
        path = PurePosixPath(member.filename)
        if len(path.parts) > 128:
            raise GateError('Archive member component depth exceeds its bound')
        name = str(path)
        if name == '.' or name in nodes:
            raise GateError('Duplicate or empty canonical archive member')
        mode = member.external_attr >> 16
        if stat.S_ISLNK(mode):
            if member.is_dir() or member.file_size > 4096:
                raise GateError('Malformed or excessive archive link')
            try:
                target = archive.read(member).decode('utf-8')
            except UnicodeError as error:
                raise GateError('Malformed archive link encoding') from error
            inspect_bytes(target.encode(), 'link target')
            if not target or target.startswith('/') or '\\' in target or '\x00' in target:
                raise GateError('Absolute or malformed archive link')
            nodes[name] = 'link'; links[name] = target
        else:
            nodes[name] = 'directory' if member.is_dir() or stat.S_ISDIR(mode) else 'file'
    for name in tuple(nodes):
        parent = PurePosixPath(name).parent
        while str(parent) != '.':
            label = str(parent)
            if label in nodes and nodes[label] != 'directory':
                raise GateError('Archive member has a non-directory parent')
            nodes.setdefault(label, 'directory')
            if len(nodes) > MAXIMUM_ENTRIES * 2:
                raise GateError('Archive namespace exceeds its bound')
            parent = parent.parent
    return nodes, links


def resolve_archive_link(member, nodes, links):
    """Follow at most 32 links, resolving each target relative to its parent."""
    top = PurePosixPath(member).parts[0]
    pending = deque((*PurePosixPath(member).parent.parts, *links[member].split('/')))
    resolved = []; hops = 1; steps = 0; seen = {(member, ())}
    while pending:
        steps += 1
        if steps > MAX_ARCHIVE_LINK_STEPS:
            raise GateError('Archive link path expansion exceeds its bound')
        part = pending.popleft()
        if part in ('', '.'):
            continue
        if part == '..':
            if len(resolved) <= 1:
                raise GateError('Archive link escapes its top-level payload')
            resolved.pop(); continue
        resolved.append(part)
        name = '/'.join(resolved)
        if resolved[0] != top:
            raise GateError('Archive link escapes its top-level payload')
        if name not in nodes:
            raise GateError('Archive link is dangling')
        if name in links:
            hops += 1
            state = (name, tuple(pending))
            if hops > 32 or state in seen:
                raise GateError('Archive link cycle or resolution bound exceeded')
            seen.add(state)
            resolved.pop()
            pending.extendleft(reversed(links[name].split('/')))
        elif pending and nodes[name] != 'directory':
            raise GateError('Archive link traverses a non-directory')
    if not resolved or '/'.join(resolved) not in nodes:
        raise GateError('Archive link is dangling')
    return '/'.join(resolved)


def inspect_payload(data, name, maximum_bytes=MAXIMUM_BYTES):
    if len(data) > maximum_bytes: raise GateError('Payload exceeds bounded inspection size')
    budget = [maximum_bytes, MAXIMUM_ENTRIES]
    def visit(payload, name, depth=0):
        safe_name(name)
        if depth > 4:
            raise GateError('Archive nesting exceeds limit')
        if zipfile.is_zipfile(io.BytesIO(payload)):
            # Bound directory metadata before ZipFile materializes its entries.
            offset = payload.rfind(b'PK\x05\x06', max(0, len(payload) - 65557))
            if offset < 0 or len(payload) - offset < 22: raise GateError('Missing ZIP directory')
            record = struct.unpack_from('<4s4H2LH', payload, offset)
            count, directory_size = record[4], record[5]
            if record[1] or record[2] or record[3] != count or count == 65535 or count > budget[1] or directory_size > 16 * 1024 * 1024:
                raise GateError('ZIP directory exceeds bounds or requires unsupported multipart/ZIP64 policy')
            if offset + 22 + record[7] != len(payload): raise GateError('ZIP trailing or malformed metadata')
            directory_offset = record[6]
            if payload[max(0, offset - 20):offset - 16] == b'PK\x06\x07' or directory_offset + directory_size != offset:
                raise GateError('Unsupported ZIP64 or inconsistent directory bounds')
            cursor = directory_offset
            actual = 0
            while cursor < offset:
                if cursor + 46 > offset or payload[cursor:cursor + 4] != b'PK\x01\x02':
                    raise GateError('Malformed ZIP central directory')
                actual += 1
                if actual > budget[1]: raise GateError('ZIP directory entry budget exceeded')
                lengths = struct.unpack_from('<3H', payload, cursor + 28)
                cursor += 46 + sum(lengths)
            if cursor != offset or actual != count: raise GateError('Contradictory ZIP central directory')

            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                if len(archive.infolist()) != count: raise GateError('Contradictory ZIP entry count')
                inspect_bytes(archive.comment, 'archive comment')
                members = archive.infolist()
                for member in members:
                    safe_name(member.filename)
                    budget[1] -= 1; budget[0] -= member.file_size
                    if budget[1] < 0 or budget[0] < 0 or member.flag_bits & 1:
                        raise GateError('Archive exceeds bounds or is encrypted')
                    inspect_bytes(member.comment + member.extra, 'archive metadata')
                nodes, links = archive_link_graph(archive, members)
                for name in links:
                    resolve_archive_link(name, nodes, links)
                for member in members:
                    if str(PurePosixPath(member.filename)) in links:
                        continue
                    visit(archive.read(member), member.filename, depth + 1)
        else:
            if name.lower().endswith(('.zip', '.gz', '.tgz', '.tar', '.xz', '.7z', '.rar', '.dmg', '.pkg')) or payload.startswith((b'\x1f\x8b', b'7z\xbc\xaf\x27\x1c', b'Rar!', b'\xfd7zXZ')) or payload[257:262] == b'ustar':
                raise GateError('Unsupported or malformed archive; separate accepted qualification required')
            inspect_bytes(payload, 'asset content')
    visit(data, name)


def scanner_identity():
    # Exact policy-source equality invalidates stale receipts without rehashing
    # previously accepted assets. Receipt files remain private local evidence.
    return base64.b64encode(Path(__file__).read_bytes()).decode()


def load_receipt(path):
    if path and Path(path).exists():
        receipt = json.loads(Path(path).read_text())
        if receipt.get('scanner') != scanner_identity():
            raise GateError('Receipt policy changed; retain accepted evidence and qualify changed policy scope explicitly')
        return receipt
    return {'schema_version': 1, 'scanner': scanner_identity(), 'files': {}, 'objects': {}, 'commits': {}}


def save_receipt(path, receipt):
    if not path:
        return
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.publication-', dir=target.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(receipt, stream, sort_keys=True); stream.write('\n')
        os.replace(name, target)
    finally:
        if os.path.exists(name): os.unlink(name)


def file_identity(path):
    item = path.stat()
    return [item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns]


def check_files(paths, receipt_path=None):
    receipt = load_receipt(receipt_path)
    counts = {'inspected': 0, 'reused': 0}
    for value in paths:
        path = Path(value)
        safe_name(path.name)
        if path.is_symlink() or not path.is_file():
            raise GateError('Public input must be a regular file')
        key = str(path.resolve()); identity = file_identity(path)
        if receipt['files'].get(key) == identity:
            counts['reused'] += 1; continue
        inspect_asset(path)
        if identity != file_identity(path):
            raise GateError('Public input changed during inspection')
        receipt['files'][key] = identity; counts['inspected'] += 1
    save_receipt(receipt_path, receipt)
    return counts


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def check_git(root, base, head, receipt_path=None):
    receipt = load_receipt(receipt_path)
    base = git(root, 'rev-parse', '--verify', '--end-of-options', base + '^{commit}').decode().strip()
    target = git(root, 'rev-parse', '--verify', '--end-of-options', head).decode().strip()
    commit = git(root, 'rev-parse', '--verify', '--end-of-options', head + '^{commit}').decode().strip()
    if subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', base, commit],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        raise GateError('Accepted baseline is not an ancestor of outgoing source')
    while git(root, 'cat-file', '-t', target).strip() == b'tag':
        tag = git(root, 'cat-file', 'tag', target).decode()
        inspect_message(tag)
        match = re.search(r'^tagger .* <([^<>]+)> ', tag, re.M)
        if not match: raise GateError('Missing tagger identity')
        inspect_identity(match.group(1))
        target = tag.split('\n', 1)[0].removeprefix('object ')
    revisions = git(root, 'rev-list', '--reverse', base + '..' + commit).decode().splitlines()
    inspected = reused = 0
    for revision in revisions:
        if revision in receipt['commits']:
            reused += 1; continue
        identity = git(root, 'show', '-s', '--format=%ae%n%ce%n%B', revision).decode()
        author, committer, message = identity.split('\n', 2)
        inspect_identity(author); inspect_identity(committer); inspect_message(message)
        # Inspect every changed tree entry at every outgoing commit, including
        # intermediate leaks removed at the final tip and merge resolutions.
        parents = git(root, 'show', '-s', '--format=%P', revision).decode().split()
        previous = parents[0] if parents else base
        names = git(root, 'diff', '--name-only', '-z', '--diff-filter=ACMRT', previous, revision).split(b'\0')
        for raw in filter(None, names):
            name = raw.decode(); safe_name(name)
            entry = git(root, 'ls-tree', '-z', revision, '--', name)
            mode_type, _ = entry.split(b'\t', 1)
            mode, kind, oid = mode_type.decode().split()
            if kind != 'blob' or mode == '120000':
                raise GateError('Source links/submodules require explicit separate qualification')
            key = name + ':' + oid
            if key not in receipt['objects']:
                size = int(git(root, 'cat-file', '-s', oid))
                if size > MAXIMUM_BYTES: raise GateError('Source object exceeds inspection bound')
                inspect_payload(git(root, 'cat-file', 'blob', oid), name)
                receipt['objects'][key] = True
        receipt['commits'][revision] = True; inspected += 1
    save_receipt(receipt_path, receipt)
    return {'head': commit, 'inspected_commits': inspected, 'reused_commits': reused}


def validate_plan(plan):
    required = {'action', 'repository', 'base', 'head', 'text', 'assets'}
    if not required <= plan.keys() or plan['repository'] != 'jdotc1/AIRS':
        raise GateError('Publication plan must declare exact AIRS repository and all surfaces')
    if plan['action'] not in {'push', 'pull_request', 'release'}:
        raise GateError('Unknown publication action')
    if not all(isinstance(plan[key], str) and plan[key] for key in ('base', 'head')):
        raise GateError('Missing source range')
    if not all(isinstance(plan[key], list) and all(isinstance(p, str) for p in plan[key]) for key in ('text', 'assets')):
        raise GateError('Text and assets must be explicit file lists')
    if plan['action'] in {'pull_request', 'release'} and not plan['text']:
        raise GateError('Public text must be supplied for inspection')
    if plan['action'] == 'release' and not plan['assets']:
        raise GateError('Release assets must be supplied for inspection')
    metadata = plan.get('public_metadata', {})
    expected = {'push': {'destination_ref'}, 'pull_request': {'base_branch', 'head_branch', 'title'}, 'release': {'tag', 'title'}}[plan['action']]
    if not isinstance(metadata, dict) or set(metadata) != expected or not all(isinstance(v, str) and v and not v.startswith('-') for v in metadata.values()):
        raise GateError('Exact public action metadata is required')
    inspect_message(json.dumps(metadata))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--base'); parser.add_argument('--head', default='HEAD')
    parser.add_argument('--file', type=Path, action='append', default=[])
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--plan', type=Path)
    args = parser.parse_args()
    result = {}
    if args.plan:
        plan = json.loads(args.plan.read_text()); validate_plan(plan)
        args.base, args.head = plan['base'], plan['head']
        args.file += [Path(p) for p in plan['text'] + plan['assets']]
    if not args.base and not args.file:
        parser.error('Declare a source range, public files or a publication plan')
    if args.base:
        result['source'] = check_git(args.root, args.base, args.head, args.receipt)
    if args.file:
        result['files'] = check_files(args.file, args.receipt)
    result['scope'] = 'Declared surfaces only; no upload, signing or runtime qualification'
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    try: main()
    except (GateError, OSError, ValueError, subprocess.CalledProcessError, zipfile.BadZipFile):
        sys.exit('Publication gate failed; inspect private inputs locally. No matching bytes are printed.')
