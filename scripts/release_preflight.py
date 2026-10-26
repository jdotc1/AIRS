#!/usr/bin/env python3
"""Read-only, exact-candidate release preflight. Never sign, install or publish.

A matching embedded source record is a signed claim, not a reproducible build.
Run once for a newly qualified candidate and retain the receipt for reuse.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import selectors
import signal
import stat
import subprocess
import sys
import time
from build_provenance import plain_path, validate_identity, write_exclusive

MAX_CAPTURE_BYTES = 16 * 1024
CHECK_TIMEOUT = 45
MAX_EXECUTABLE_BYTES = 512 * 1024 * 1024


def read_file(path: Path, maximum: int, *, digest: bool = False):
    path = plain_path(path)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise ValueError('Candidate file is not regular or exceeds its bound')
        with os.fdopen(descriptor, 'rb', closefd=False) as source:
            if digest:
                value = hashlib.sha256(); total = 0
                for part in iter(lambda: source.read(1024 * 1024), b''):
                    total += len(part)
                    if total > maximum:
                        raise ValueError('Candidate file grew past its bound')
                    value.update(part)
                return value.hexdigest()
            value = source.read(maximum + 1)
            if len(value) > maximum:
                raise ValueError('Candidate file grew past its bound')
            return value
    finally:
        os.close(descriptor)


def candidate_metadata(app: Path) -> dict:
    app = plain_path(app)
    if not app.is_dir() or app.suffix != '.app':
        raise ValueError('An ordinary app directory is required')
    info = plistlib.loads(read_file(app / 'Contents/Info.plist', 1024 * 1024))
    if not isinstance(info, dict):
        raise ValueError('Info.plist must be a dictionary')
    label = info.get('CFBundleExecutable')
    if not isinstance(label, str) or not label or label in ('.', '..') or '/' in label or '\x00' in label:
        raise ValueError('Invalid principal executable label')
    return {'bundle_id': info.get('CFBundleIdentifier'), 'version': info.get('CFBundleShortVersionString'),
            'build': info.get('CFBundleVersion'),
            'principal_sha256': read_file(app / 'Contents/MacOS' / label, MAX_EXECUTABLE_BYTES, digest=True)}


def embedded_provenance(app: Path, commit: str, bundle_id: str, build: str) -> dict:
    path = app / 'Contents/Resources/AIRSBuildProvenance.json'
    if not path.exists():
        return {'state': 'unavailable', 'matches_request': False}
    try:
        encoded = read_file(path, 16 * 1024)
        fields = json.loads(encoded)
    except (UnicodeError, ValueError, OSError):
        return {'state': 'malformed', 'matches_request': False}
    matches = (isinstance(fields, dict) and fields.get('schema') == 'airs-source-build-record-v1'
               and fields.get('source_repository') == 'jdotc1/AIRS'
               and fields.get('source_commit') == commit and fields.get('bundle_id') == bundle_id
               and fields.get('build') == build
               and fields.get('provenance_strength') == 'builder_recorded_not_reproducibly_attested')
    return {'state': 'recorded_unverified', 'matches_request': matches,
            'embedded_commit': fields.get('source_commit') if isinstance(fields, dict) else None,
            'record_sha256': hashlib.sha256(encoded).hexdigest()}


def execute_check(command: list[str]) -> dict:
    """Bound time/output and kill only the process group started for this check."""
    process = None
    streams = {}
    total = 0
    failure = None
    started = time.monotonic()
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        with selectors.DefaultSelector() as selector:
            for name, pipe in (('stdout', process.stdout), ('stderr', process.stderr)):
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ, name)
                streams[name] = bytearray()
            while selector.get_map():
                if time.monotonic() - started >= CHECK_TIMEOUT:
                    failure = 'timeout'; break
                for key, _ in selector.select(timeout=0.1):
                    data = os.read(key.fileobj.fileno(), 4096)
                    if not data:
                        selector.unregister(key.fileobj); continue
                    total += len(data)
                    if total > MAX_CAPTURE_BYTES:
                        failure = 'output_limit'; break
                    streams[key.data].extend(data)
                if failure:
                    break
        if failure:
            os.killpg(process.pid, signal.SIGKILL)
        code = process.wait(timeout=2)
        return {'available': True, 'passed': failure is None and code == 0, 'exit_code': code,
                'failure': failure, **{key: bytes(value[-4096:]).decode('utf-8', errors='backslashreplace')
                                     for key, value in streams.items()}}
    except (OSError, subprocess.SubprocessError):
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL); process.wait(timeout=2)
            except (OSError, subprocess.SubprocessError):
                pass
        return {'available': False, 'passed': False, 'failure': 'execution_unavailable'}
    finally:
        if process is not None:
            for pipe in (process.stdout, process.stderr):
                if pipe is not None:
                    pipe.close()


def evaluate(app: Path, commit: str, expected_id: str, expected_build: str) -> dict:
    validate_identity(commit, expected_id, expected_build)
    app = plain_path(app)
    metadata = candidate_metadata(app)
    source = embedded_provenance(app, commit, expected_id, expected_build)
    identity = metadata['bundle_id'] == expected_id and metadata['build'] == expected_build
    checks = {}
    if identity and source['matches_request'] and sys.platform == 'darwin':
        for name, command in (
            ('codesign', ['/usr/bin/codesign', '--verify', '--deep', '--strict', '--verbose=2', str(app)]),
            ('gatekeeper', ['/usr/sbin/spctl', '--assess', '--verbose=4', str(app)]),
            ('staple', ['/usr/bin/xcrun', 'stapler', 'validate', str(app)])):
            checks[name] = execute_check(command)
            if not checks[name]['passed']:
                break
    return {'schema': 'airs-release-preflight-v1', 'app_name': app.name, 'metadata': metadata,
            'source_provenance': source, 'platform': sys.platform, 'checks': checks,
            'identity_matches_request': identity,
            'release_gate_passed': bool(identity and source['matches_request'] and len(checks) == 3
                                        and all(item['passed'] for item in checks.values())),
            'limitations': ['Embedded source metadata is a builder claim, not reproducible-build proof.',
                           'Clean-host, supported-OS, functional and translocation acceptance are separate.',
                           'A passing preflight does not authorize release publication.']}


def receipt_destination(path: Path, app: Path) -> Path:
    path, app = plain_path(path, exists=False), plain_path(app)
    plain_path(path.parent)
    if path == app or app in path.parents or path.exists():
        raise ValueError('Receipt must be new and outside the protected app')
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--expected-source-commit', required=True)
    parser.add_argument('--expected-bundle-id', required=True)
    parser.add_argument('--expected-build', required=True)
    parser.add_argument('--json-out', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.json_out:
            receipt_destination(args.json_out, args.app)
        value = evaluate(args.app, args.expected_source_commit, args.expected_bundle_id, args.expected_build)
        encoded = json.dumps(value, indent=2, sort_keys=True) + '\n'
        if args.json_out:
            write_exclusive(args.json_out, encoded)
        print(encoded, end='')
        return 0 if value['release_gate_passed'] else 2
    except (OSError, ValueError, TypeError, plistlib.InvalidFileException):
        print(json.dumps({'release_gate_passed': False, 'error': 'Candidate or receipt boundary refused'}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
