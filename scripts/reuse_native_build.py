#!/usr/bin/env python3
"""Reuse a trusted local native-build receipt without hashes or compilation.

Receipt custody is local trust, not adversarial authentication. Source object
identities and artifact metadata must still match the accepted build exactly.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from build_provenance import plain_path

INPUTS = ('native/Sources', 'native/Package.swift', 'native/Vendor')
PRODUCTS = frozenset(('AIRSApp', 'airs-entitlements'))
MAX_RECEIPT_BYTES = 1024 * 1024
MAX_ARTIFACTS = 20000


def git(root: Path, *args: str) -> str:
    process = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                             text=True, timeout=15, check=True)
    if len(process.stdout) > MAX_RECEIPT_BYTES:
        raise ValueError('Native source inventory exceeds its bound')
    return process.stdout.strip()


def metadata(path: Path) -> list[int]:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('Native artifact is not an ordinary file')
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_mode]


def artifact_files(build: Path) -> dict[str, Path]:
    files = {name: build / name for name in PRODUCTS}
    bundles = sorted(build.glob('*_*.bundle'))
    if not bundles:
        raise ValueError('Native resource bundle is missing')
    for bundle in bundles:
        if bundle.is_symlink() or not bundle.is_dir():
            raise ValueError('Native resource bundle must be an ordinary directory')
        before = len(files)
        for path in bundle.rglob('*'):
            if path.is_symlink():
                raise ValueError('Native resource links require separate qualification')
            if path.is_dir():
                continue
            files[path.relative_to(build).as_posix()] = path
            if len(files) > MAX_ARTIFACTS:
                raise ValueError('Native artifact inventory exceeds its bound')
        if len(files) == before:
            raise ValueError('An empty resource bundle lacks recorded file identity')
    if len(files) == len(PRODUCTS):
        raise ValueError('Native resources contain no recorded files')
    return files


def reuse(source: Path, receipt_path: Path) -> Path:
    source, receipt_path = plain_path(source), plain_path(receipt_path)
    descriptor = os.open(receipt_path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_RECEIPT_BYTES:
            raise ValueError('Native receipt must be a bounded ordinary file')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            encoded = stream.read(MAX_RECEIPT_BYTES + 1)
        if len(encoded) > MAX_RECEIPT_BYTES:
            raise ValueError('Native receipt exceeds its bound')
        receipt = json.loads(encoded)
    finally:
        os.close(descriptor)
    if not isinstance(receipt, dict) or receipt.get('schema') != 'airs-native-build-reuse-v1':
        raise ValueError('Unsupported native build receipt')
    accepted = receipt.get('source_commit')
    if not isinstance(accepted, str) or re.fullmatch(r'[0-9a-f]{40}', accepted) is None:
        raise ValueError('Receipt must name an exact accepted source commit')
    build_value = receipt.get('build_path')
    if not isinstance(build_value, str) or not Path(build_value).is_absolute():
        raise ValueError('Native build path must be absolute')
    build = plain_path(Path(build_value))
    native_root = plain_path(source / 'native/.build')
    if native_root not in build.parents or not build.is_dir():
        raise ValueError('Native build must be inside the source build root')
    inputs = receipt.get('native_input_oids')
    if not isinstance(inputs, dict) or set(inputs) != set(INPUTS):
        raise ValueError('Native receipt has incomplete source inputs')
    for path, oid in inputs.items():
        if not isinstance(oid, str) or re.fullmatch(r'[0-9a-f]{40}', oid) is None:
            raise ValueError('Invalid accepted native source object identity')
        if git(source, 'rev-parse', accepted + ':' + path) != oid or git(source, 'rev-parse', 'HEAD:' + path) != oid:
            raise ValueError('Native source differs from the accepted build')
    if git(source, 'status', '--porcelain', '--untracked-files=all', '--', *INPUTS):
        raise ValueError('Native compiler inputs are modified')
    ignored = ('native/Sources', 'native/Package.swift',
               ':(glob)native/Vendor/**/Sources/**', ':(glob)native/Vendor/**/Package.swift')
    if git(source, 'ls-files', '--others', '--ignored', '--exclude-standard', '--', *ignored):
        raise ValueError('Ignored native compiler inputs are not covered by the receipt')
    recorded = receipt.get('artifacts')
    if not isinstance(recorded, dict) or not PRODUCTS <= recorded.keys() or not len(recorded) <= MAX_ARTIFACTS:
        raise ValueError('Incomplete or excessive native artifact receipt')
    for name, record in recorded.items():
        if (not isinstance(name, str) or '\\' in name or PurePosixPath(name).is_absolute()
                or '..' in PurePosixPath(name).parts or str(PurePosixPath(name)) != name
                or not isinstance(record, list) or len(record) != 6
                or any(type(value) is not int or value < 0 for value in record)):
            raise ValueError('Malformed native artifact identity')
    actual = artifact_files(build)
    if set(actual) != set(recorded):
        raise ValueError('Native product/resource membership changed')
    for name, path in actual.items():
        value = metadata(path)
        if value != recorded[name] or (name in PRODUCTS and value[-1] & 0o111 == 0):
            raise ValueError('Native product/resource metadata changed')
    return build


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(reuse(args.source, args.receipt))
        return 0
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        print('Native build reuse refused; preserve accepted evidence and qualify changed inputs.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
