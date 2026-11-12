#!/usr/bin/env python3
"""Emit deterministic ARM64 instruction words; no external dependencies."""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys


def harness():
    spec = importlib.util.spec_from_file_location('arm64_oracle_diff', Path(__file__).with_name('arm64-oracle-diff.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Explicit owned examples, keyed by the kind emitted by the CFG decoder.
SEEDS = {
    'add': 0x91000000,
    'b': 0x14000040,
    'bcond': 0x54000200,
    'bl': 0x94000040,
    'ldp': 0xa9407bfd,
    'mov': 0xaa0003e0,
    'movn': 0x92800000,
    'movz': 0xd2800000,
    'nop': 0xd503201f,
    'ret': 0xd65f03c0,
    'smaddl': 0x9b220c20,
    'smsubl': 0x9b228c20,
    'smulh': 0x9b427c20,
    'stp': 0xa9007bfd,
    'sub': 0xd1000000,
    'umaddl': 0x9ba20c20,
    'umsubl': 0x9ba28c20,
    'umulh': 0x9bc27c20,
    'wadc': 0x1a1f0020,
    'wadcs': 0x3a020020,
    'wadd': 0x11401400,
    'wadds': 0x31000000,
    'wadds_ext': 0x2b22003d,
    'wadds_reg': 0x2b027c20,
    'wand_imm': 0x12003c20,
    'wand_reg': 0x0a1f143d,
    'wands': 0x6a02003d,
    'wands_imm': 0x720713fd,
    'wasrv': 0x1ac22820,
    'wbfm': 0x33007c20,
    'wbic_reg': 0x0a22143d,
    'wbics': 0x6a220020,
    'wcbnz': 0x35000200,
    'wcbz': 0x34000200,
    'wccmn_imm': 0x3a430825,
    'wccmn_reg': 0x3a420025,
    'wccmp_imm': 0x7a430825,
    'wccmp_reg': 0x7a420025,
    'wcls': 0x5ac01420,
    'wclz': 0x5ac01020,
    'wcsel': 0x1a820020,
    'wcsinc': 0x1a820420,
    'wcsinv': 0x5a820020,
    'wcsneg': 0x5a820420,
    'weon_reg': 0x4a2217fd,
    'weor_imm': 0x520713e0,
    'weor_reg': 0x4a1f7fe0,
    'wextr': 0x13820020,
    'wldr': 0xb94003e0,
    'wlsl': 0x531f7820,
    'wlslv': 0x1adf2020,
    'wlsrv': 0x1ac227e0,
    'wmadd': 0x1b1f0c3d,
    'wmovk': 0x72800000,
    'wmsub': 0x1b1f8fe0,
    'worn_reg': 0x2a221420,
    'worr_imm': 0x3200c020,
    'worr_reg': 0x2a0217fd,
    'wrbit': 0x5ac00020,
    'wrev': 0x5ac00820,
    'wrev16': 0x5ac00420,
    'wrorv': 0x1ac22c20,
    'wsbc': 0x5a020020,
    'wsbcs': 0x7a1f0020,
    'wsbfm': 0x13071c20,
    'wsdiv': 0x1ac20c20,
    'wstr': 0xb90003e0,
    'wsubs': 0x71001400,
    'wsubs_ext': 0x6b220020,
    'wsubs_reg': 0x6b021c20,
    'wtbnz': 0x37000200,
    'wtbz': 0x36000200,
    'wubfm': 0x531f0020,
    'wudiv': 0x1ac20be0,
    'xadc': 0x9a020020,
    'xadcs': 0xba0203e0,
    'xadds': 0xb1400000,
    'xadds_ext': 0xab22003f,
    'xadds_reg': 0xab02ffe0,
    'xand_imm': 0x92003fe0,
    'xand_reg': 0x8a021420,
    'xands': 0xea02143d,
    'xands_imm': 0xf2401c3d,
    'xasrv': 0x9ac22820,
    'xbfm': 0xb37f0020,
    'xbic_reg': 0x8affff00,
    'xbics': 0xea3f03e0,
    'xcbnz': 0xb5000200,
    'xcbz': 0xb4000200,
    'xccmn_imm': 0xba430825,
    'xccmn_reg': 0xba420025,
    'xccmp_imm': 0xfa430825,
    'xccmp_reg': 0xfa420025,
    'xcls': 0xdac01420,
    'xclz': 0xdac01020,
    'xcsel': 0x9a820020,
    'xcsinc': 0x9a820420,
    'xcsinv': 0xda820020,
    'xcsneg': 0xda820420,
    'xeon_reg': 0xca221420,
    'xeor_imm': 0xd2003ffd,
    'xeor_reg': 0xca1f143d,
    'xextr': 0x93c20020,
    'xldr': 0xf94003e0,
    'xlslv': 0x9adf2020,
    'xlsrv': 0x9adf2420,
    'xmadd': 0x9b020c20,
    'xmovk': 0xf2800000,
    'xmsub': 0x9b028c20,
    'xorn_reg': 0xaa2103e2,
    'xorr_imm': 0xb2401c20,
    'xorr_reg': 0xaa0107e2,
    'xrbit': 0xdac00020,
    'xrev': 0xdac00c20,
    'xrev16': 0xdac00420,
    'xrev32': 0xdac00820,
    'xrorv': 0x9ac22c20,
    'xsbc': 0xda1f0020,
    'xsbcs': 0xfa020020,
    'xsbfm': 0x937f0020,
    'xsdiv': 0x9ac20c3d,
    'xstr': 0xf90003e0,
    'xsubs': 0xf17ffc00,
    'xsubs_ext': 0xeb22083f,
    'xsubs_reg': 0xeb021c20,
    'xtbnz': 0xb7000200,
    'xtbz': 0xb6000200,
    'xubfm': 0xd3401c20,
    'xudiv': 0x9ac20820,
}

REQUIRED_WORDS = (
    0xd65f03c0, 0x9b228c20, 0x9b22fc20, 0xb94003e0, 0xb94007e1,
    0x531f7820, 0x53010020, 0x1ac20c20, 0x1adf0fff, 0xb90003e0, 0xb90007e1,
)
# Numerical Recipes 32-bit LCG, explicitly specified for cross-version stability.
GENERATOR_SEED = 0x41524d36
GENERATED_COUNT = 16384


def inventory():
    h = harness()
    return h.derive_inventory(Path(h.arm64.__file__).read_text(encoding='utf-8'),
                              Path(h.cfg.__file__).read_text(encoding='utf-8'))


def validate_seeds(seeds):
    kinds = set().union(*(k for k, _ in inventory().values()))
    missing, unknown = kinds - seeds.keys(), seeds.keys() - kinds
    if missing or unknown:
        raise ValueError('seed inventory mismatch: missing=' + ','.join(sorted(missing))
                         + '; unknown=' + ','.join(sorted(unknown)))
    if any(type(word) is not int or not 0 <= word <= 0xffffffff for word in seeds.values()):
        raise ValueError('seeds must be 32-bit unsigned words')


def generate_words(seeds=None):
    seeds = SEEDS if seeds is None else seeds
    validate_seeds(seeds)
    words = set(REQUIRED_WORDS)
    for word in seeds.values():
        words.add(word)
        words.update(word ^ (1 << bit) for bit in range(32))
        for shift in (0, 5, 10, 16):
            words.update((word & ~(31 << shift)) | (reg << shift) for reg in (0, 1, 29, 30, 31))
    state = GENERATOR_SEED
    for _ in range(GENERATED_COUNT):
        state = (1664525 * state + 1013904223) & 0xffffffff
        words.add(state)
    return sorted(words)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args(argv)
    try:
        words = generate_words()
        with args.out.open('w' if args.overwrite else 'x', encoding='ascii', newline='\n') as handle:
            handle.writelines('.inst 0x%08x\n' % word for word in words)
    except Exception as error:
        print('arm64-oracle-words: ' + ' '.join(str(error).splitlines()), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
