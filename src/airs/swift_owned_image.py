"""Bounded reuse of trusted local owned-corpus compile identity receipts.

This is custody bookkeeping, not cryptographic attestation of a receipt. Only
explicitly supplied private compiler receipts are authority; analysis reports
and arbitrary digest dictionaries are not. A user who can rewrite a receipt and
its file metadata is outside this local trust boundary. No changed/v1/FAT input
falls back to a fresh hash: admission fails and requires a new authorized seal.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat

from .types import Limits, MachOImage

_MAX_BYTES = 64 * 1024 * 1024
_MAX_RECEIPT_BYTES = 1024 * 1024
_CUSTODY_KEYS = ('dev', 'ino', 'size', 'mtime_ns', 'ctime_ns')


@dataclass(frozen=True)
class _OwnedDigestReceipt:
    """Internal capability bound to one immutable bytes object (not forgeproof)."""
    data: bytes
    sha256: str

    def _digest_for(self, data: bytes) -> str:
        if data is not self.data or len(data) != len(self.data):
            raise ValueError('Owned digest receipt bytes identity mismatch')
        if not re.fullmatch(r'[0-9a-f]{64}', self.sha256):
            raise ValueError('Invalid owned digest receipt digest')
        return self.sha256


def _unique_receipt_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Compile receipt contains a duplicate JSON key')
        result[key] = value
    return result


def _valid_custody(value: object) -> bool:
    return (isinstance(value, dict) and set(value) == set(_CUSTODY_KEYS)
            and all(type(item) is int and item >= 0 for item in value.values()))


def _custody(value: os.stat_result) -> dict[str, int]:
    return {key: getattr(value, 'st_' + key) for key in _CUSTODY_KEYS}


def _read_regular(parent_fd: int, name: str, limit: int,
                  expected: dict[str, int] | None = None) -> bytes:
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError('Owned receipt/file must be a bounded regular file')
        if expected is not None and _custody(before) != expected:
            raise ValueError('Owned image custody changed before read')
        chunks = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(fd, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b''.join(chunks)
        after = os.fstat(fd)
        if len(data) > limit or len(data) != before.st_size or _custody(before) != _custody(after):
            raise ValueError('Owned file custody changed during read')
        # Catch replacement of the directory entry while retaining an old fd.
        if _custody(os.stat(name, dir_fd=parent_fd, follow_symlinks=False)) != _custody(after):
            raise ValueError('Owned file custody changed after read')
        return data
    finally:
        os.close(fd)


def _open_directory(path: Path) -> int:
    """Walk canonical absolute components without following ancestor symlinks."""
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def load_owned_swift_image(library_path: str | Path, compile_receipt_path: str | Path,
                           mode: str, limits: Limits = Limits()) -> MachOImage:
    """Parse one thin ARM64 owned image using its trusted v2 compiler receipt.

    Both paths must be exact absolute, canonical paths in the receipt output
    directory. Opens use descriptor-relative O_NOFOLLOW; receipt and image are
    bounded regular files. All ordinary Mach-O structural checks still run.
    """
    from .macho import parse_macho

    library = Path(library_path)
    receipt_path = Path(compile_receipt_path)
    if (not library.is_absolute() or not receipt_path.is_absolute()
            or library != library.resolve() or receipt_path != receipt_path.resolve()
            or receipt_path.name != 'compile-receipt.json' or library.parent != receipt_path.parent):
        raise ValueError('Owned paths must be exact canonical files in the receipt output directory')
    parent = library.parent
    parent_fd = _open_directory(parent)
    try:
        receipt = json.loads(_read_regular(parent_fd, receipt_path.name, _MAX_RECEIPT_BYTES),
                             object_pairs_hook=_unique_receipt_object)
        if (not isinstance(receipt, dict) or receipt.get('schema') != 'airs.owned-swift-broad-compile.v2'
                or receipt.get('state') not in ('compiled_unindexed', 'indexed')
                or receipt.get('output_directory') != str(parent)):
            raise ValueError('A trusted complete v2 compile receipt is required')
        modes = receipt.get('modes')
        if not isinstance(modes, dict):
            raise ValueError('Compile receipt has no mode records')
        entry = modes.get(mode)
        if not isinstance(entry, dict) or entry.get('library') != library.name or entry.get('library_path') != str(library):
            raise ValueError('Compile receipt does not bind the exact library path and mode')
        before, after = entry.get('custody_before'), entry.get('custody_after')
        if (not _valid_custody(before) or not _valid_custody(after) or before != after
                or type(entry.get('bytes')) is not int or entry['bytes'] < 0
                or entry['bytes'] != before['size']):
            raise ValueError('Compile receipt has no stable first-hash custody')
        digest = entry.get('emitted_sha256')
        if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('Compile receipt has no valid emitted digest')
        data = _read_regular(parent_fd, library.name, min(_MAX_BYTES, limits.max_file_bytes), before)
    except OSError as error:
        raise ValueError('Owned image/receipt custody open failed') from error
    finally:
        os.close(parent_fd)
    if data[:4] != b'\xcf\xfa\xed\xfe':
        raise ValueError('Owned digest reuse supports thin ARM64 Mach-O only')
    return parse_macho(data, str(library), limits, requested_arch='arm64',
                       _owned_digest_receipt=_OwnedDigestReceipt(data, digest))
