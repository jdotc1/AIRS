#!/usr/bin/env python3
"""Create an exclusive builder-recorded source claim before app signing.

A record is a claim, not reproducible-build proof or release authorization.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess

COMMIT = re.compile(r'[0-9a-f]{40}')
BUNDLE = re.compile(r'[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)+')


def plain_path(path: Path, *, exists: bool = True) -> Path:
    path = Path(os.path.abspath(path)) if '..' not in Path(path).parts else None
    if path is None:
        raise ValueError('Parent traversal is not allowed')
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise ValueError('Symlinked path components are not allowed')
    if exists and not path.exists():
        raise ValueError('Required path does not exist')
    return path


def validate_identity(commit: str, bundle_id: str, build: str) -> None:
    if not isinstance(commit, str) or COMMIT.fullmatch(commit) is None:
        raise ValueError('Source commit must be an exact lowercase object ID')
    if not isinstance(bundle_id, str) or len(bundle_id) > 255 or BUNDLE.fullmatch(bundle_id) is None:
        raise ValueError('A bounded bundle identifier is required')
    if not isinstance(build, str) or re.fullmatch(r'[1-9][0-9]{0,9}', build) is None:
        raise ValueError('Build must be a positive decimal integer')


def git_output(root: Path, *args: str) -> str:
    result = subprocess.run(['git', '-C', str(root), *args], check=True,
                            capture_output=True, text=True, timeout=15)
    return result.stdout.strip()


def build_claim(root: Path, expected_commit: str, bundle_id: str, build: str) -> dict:
    validate_identity(expected_commit, bundle_id, build)
    root = plain_path(root)
    actual = git_output(root, 'rev-parse', 'HEAD')
    if actual != expected_commit:
        raise ValueError('Source HEAD does not match the requested candidate')
    if git_output(root, 'status', '--porcelain', '--untracked-files=normal'):
        raise ValueError('Freeze clean source before creating a build claim')
    return {'schema': 'airs-source-build-record-v1', 'source_repository': 'jdotc1/AIRS',
            'source_commit': actual, 'bundle_id': bundle_id, 'build': build,
            'provenance_strength': 'builder_recorded_not_reproducibly_attested',
            'generated_utc': dt.datetime.now(dt.timezone.utc).isoformat()}


def write_exclusive(path: Path, encoded: str) -> None:
    path = plain_path(path, exists=False)
    plain_path(path.parent)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            output.write(encoded)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--expected-commit', required=True)
    parser.add_argument('--bundle-id', required=True)
    parser.add_argument('--build', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if plain_path(args.output, exists=False).exists():
            raise ValueError('Build claim destination already exists')
        claim = build_claim(args.source, args.expected_commit, args.bundle_id, args.build)
        write_exclusive(args.output, json.dumps(claim, indent=2, sort_keys=True) + '\n')
        print(json.dumps({'created': True, 'source_commit': claim['source_commit']}))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError):
        print(json.dumps({'created': False, 'error': 'Build claim refused; inspect source identity, clean state and destination'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
