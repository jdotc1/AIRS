"""Opt-in bounded exact-body evidence, never unwind or identity authority.

Adapt MacScope's stable digest and substantial-body floor. Keep encoded operands
and immediates intact instead of importing decompiler text normalization.
"""
from __future__ import annotations

import hashlib
from .types import InputError

KIND = 'arm64-exact-bytes-v1'
MAX_INSTRUCTIONS = 16_384
DOMAIN = b'AIRS arm64 exact-body v1\x00'


def exact_body_fingerprint(image, function, outcome) -> dict | None:
    count = function.size // 4
    if (image.architecture != 'arm64' or image.cpu_subtype not in (0, 1)
            or function.boundary_source != 'lc_function_starts'
            or function.start % 4 or function.size % 4
            or not 3 <= count <= MAX_INSTRUCTIONS
            or outcome.verdict not in ('agreement', 'inconsistency')
            or outcome.instruction_count != count):
        return None
    if not any(section.executable and section.address <= function.start
               and function.end <= section.end for section in image.sections):
        return None
    try:
        body = image.bytes_at(function.start, function.size)
    except InputError:
        return None
    return {'kind': KIND, 'instruction_count': count,
            'sha256': hashlib.sha256(DOMAIN + body).hexdigest()}
