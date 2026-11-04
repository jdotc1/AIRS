#!/usr/bin/env python3
"""Sanitize only a fresh package's private Python copy before signing.

Prepared runtimes and signed/installed apps are never valid destinations. Native
metadata changes use strip and qualified fixed-width read-only source-path literals.
"""
from __future__ import annotations
import argparse
import ast
import json
import math
import os
from pathlib import Path
import pprint
import re
import shutil
import stat
import struct
import tempfile
from build_provenance import plain_path
from release_preflight import execute_check, read_file
from runtime_source_paths import normalize_source_paths

MAX_CONFIG_BYTES = 1024 * 1024
MAX_ENTRIES = 5000
MAX_CONFIG_FILES = 32
HOME_PREFIX = re.compile(r'/(?:Users|home)/[^/\x00\r\n]+/')
NEUTRAL_PREFIX = '/AIRS/runtime-build/'


def sanitize_values(value):
    count = 0
    def walk(item):
        nonlocal count
        if isinstance(item, str):
            result, changed = HOME_PREFIX.subn(NEUTRAL_PREFIX, item); count += changed; return result
        if isinstance(item, bytes):
            pattern = re.compile(HOME_PREFIX.pattern.encode())
            result, changed = pattern.subn(NEUTRAL_PREFIX.encode(), item); count += changed; return result
        if isinstance(item, dict):
            for key in item:
                if not isinstance(key, str) or HOME_PREFIX.search(key):
                    raise ValueError('Unexpected generated configuration key')
            return {key: walk(member) for key, member in item.items()}
        if isinstance(item, (list, tuple, set)):
            return type(item)(walk(member) for member in item)
        if isinstance(item, (float, complex)) and not (math.isfinite(item.real) and math.isfinite(item.imag)):
            raise ValueError('Nonfinite generated configuration literal')
        if item is None or isinstance(item, (bool, int, float, complex)):
            return item
        raise ValueError('Unsupported generated configuration value')
    return walk(value), lambda: count


def sanitize_json(source: str):
    def pairs(items):
        value = {}
        for key, member in items:
            if key in value: raise ValueError('Duplicate generated configuration key')
            value[key] = member
        return value
    def constant(value): raise ValueError('Nonstandard JSON constant')
    value = json.loads(source, object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value, dict): raise ValueError('Generated JSON must contain a dictionary')
    clean, count = sanitize_values(value)
    return json.dumps(clean, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + '\n', count()


def sanitize_python(source: str):
    module = ast.parse(source)
    body = list(module.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body.pop(0)
    if (len(body) != 1 or not isinstance(body[0], ast.Assign) or len(body[0].targets) != 1
            or not isinstance(body[0].targets[0], ast.Name) or body[0].targets[0].id != 'build_time_vars'
            or not isinstance(body[0].value, ast.Dict)):
        raise ValueError('Expected only a literal build_time_vars assignment')
    assignment = body[0]
    if any(isinstance(node, (ast.Call, ast.Attribute, ast.Name, ast.Lambda, ast.comprehension))
           for node in ast.walk(assignment.value)):
        raise ValueError('Executable generated configuration is not admitted')
    value = ast.literal_eval(assignment.value)
    clean, count = sanitize_values(value)
    lines = source.splitlines(keepends=True)
    prefix = ''.join(lines[:assignment.lineno - 1]) + lines[assignment.lineno - 1].encode()[:assignment.col_offset].decode()
    suffix = lines[assignment.end_lineno - 1].encode()[assignment.end_col_offset:].decode() + ''.join(lines[assignment.end_lineno:])
    prefix, before = HOME_PREFIX.subn(NEUTRAL_PREFIX, prefix)
    suffix, after = HOME_PREFIX.subn(NEUTRAL_PREFIX, suffix)
    return prefix + 'build_time_vars = ' + pprint.pformat(clean, width=100, sort_dicts=True) + suffix, count() + before + after


def framework_root(path: Path) -> Path:
    path = plain_path(path)
    if (path.parts[-4:] != ('AIRS.app', 'Contents', 'Frameworks', 'Python.framework')
            or not path.parents[3].name.startswith('.airs-package.')
            or path.parents[3].name == '.airs-package.' or not path.is_dir()):
        raise ValueError('Only a fresh package staging framework may be sanitized')
    version = plain_path(path / 'Versions/3.15')
    library = plain_path(version / 'lib/python3.15')
    if not version.is_dir() or not library.is_dir():
        raise ValueError('Expected the staged runtime directory layout')
    return path


def inventory(root: Path):
    files = []; count = 0
    for parent, directories, names in os.walk(root, followlinks=False):
        count += len(directories) + len(names)
        if count > MAX_ENTRIES: raise ValueError('Runtime staging inventory exceeds its bound')
        directory = Path(parent)
        directories[:] = [name for name in directories if not (directory / name).is_symlink()]
        for name in names:
            path = directory / name
            if path.is_symlink(): continue
            if not stat.S_ISREG(path.lstat().st_mode):
                raise ValueError('Runtime staging contains a special file')
            files.append(path)
    return files


def code_type(path: Path):
    with path.open('rb') as source:
        header = source.read(32)
        if len(header) < 16: return None
        endian = '<' if header[:4] in (b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe') else '>'
        if header[:4] in (b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xfe\xed\xfa\xce'):
            return struct.unpack_from(endian + 'I', header, 12)[0]
        if header[:4] in (b'\xca\xfe\xba\xbe', b'\xca\xfe\xba\xbf') and len(header) == 32:
            offset = struct.unpack_from('>Q' if header[:4] == b'\xca\xfe\xba\xbf' else '>I', header, 16)[0]
            if offset + 16 > path.stat().st_size: raise ValueError('Malformed staged universal code')
            source.seek(offset); nested = source.read(16)
            if nested[:4] not in (b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xfe\xed\xfa\xce'):
                raise ValueError('Malformed staged universal slice')
            endian = '<' if nested[:4] in (b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe') else '>'
            return struct.unpack_from(endian + 'I', nested, 12)[0]
    return None


def write_config(path: Path, encoded: str):
    mode = stat.S_IMODE(path.lstat().st_mode)
    descriptor, temporary = tempfile.mkstemp(prefix='.runtime-config-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output: output.write(encoded)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def sanitize(framework: Path):
    root = framework_root(framework)
    version = root / 'Versions/3.15'
    files = inventory(root)
    library = version / 'lib/python3.15'
    remove = [path for path in (version / 'share/doc', *library.glob('config-*')) if path.exists() or path.is_symlink()]
    for path in remove:
        plain_path(path)
        if not path.is_dir(): raise ValueError('Unexpected developer directory type')
    configs = []
    for path in files:
        if path.parent != library: continue
        handler = (sanitize_json if path.match('_sysconfig_vars*.json') else
                   sanitize_python if path.match('_sysconfigdata*.py') else None)
        if handler is None: continue
        if len(configs) >= MAX_CONFIG_FILES or path.stat().st_size > MAX_CONFIG_BYTES:
            raise ValueError('Generated configuration exceeds its bound')
        with path.open('rb') as source: data = source.read(MAX_CONFIG_BYTES + 1)
        if len(data) > MAX_CONFIG_BYTES: raise ValueError('Generated configuration grew past its bound')
        encoded, changes = handler(data.decode('utf-8'))
        configs.append((path, encoded, changes))
    marker = root.parents[3] / '.runtime-sanitizer-started'
    with marker.open('x') as output: output.write('Fresh staging runtime sanitation started\n')
    for path in remove: shutil.rmtree(path)
    changed = []; occurrences = 0
    for path, encoded, changes in configs:
        if changes:
            write_config(path, encoded); changed.append(path.relative_to(root).as_posix()); occurrences += changes
    stripped = []; normalized_members = []; normalized_count = 0
    for path in files:
        if not path.exists() or any(parent in remove for parent in path.parents): continue
        if code_type(path) not in (2, 6, 8): continue
        mode = stat.S_IMODE(path.lstat().st_mode)
        try:
            path.chmod(mode | stat.S_IWUSR)
            result = execute_check(['/usr/bin/strip', '-S', '-x', str(path)])
            if not result['passed']: raise ValueError('Staged native stripping failed')
            original = read_file(path, 128 * 1024 * 1024)
            normalized, count = normalize_source_paths(original)
            if count:
                descriptor, temporary = tempfile.mkstemp(prefix='.runtime-code-', dir=path.parent)
                try:
                    with os.fdopen(descriptor, 'wb') as output: output.write(normalized)
                    os.chmod(temporary, mode | stat.S_IWUSR)
                    os.replace(temporary, path)
                finally:
                    Path(temporary).unlink(missing_ok=True)
                normalized_members.append(path.relative_to(root).as_posix()); normalized_count += count
        finally:
            path.chmod(mode)
        stripped.append(path.relative_to(root).as_posix())
    return {'schema': 'airs-runtime-staging-sanitization-v1', 'removed_directories': [p.relative_to(root).as_posix() for p in remove],
            'sanitized_configs': changed, 'neutralized_home_prefixes': occurrences,
            'stripped_code_members': stripped, 'stripped_code_count': len(stripped),
            'normalized_native_members': normalized_members, 'normalized_native_source_prefixes': normalized_count,
            'scope': 'Fresh staging copy only; signing and runtime acceptance remain separate'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--framework', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(sanitize(args.framework), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, SyntaxError):
        print(json.dumps({'sanitized': False, 'error': 'Fresh runtime staging sanitation refused'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
