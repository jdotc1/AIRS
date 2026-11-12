"""Unit tests for scripts/arm64-oracle-diff.py on a self-contained synthetic vectors tree.

The embedded SAMPLES are (word, address, oracle text) triples chosen by the test
author. Each word was decoded with both AIRS decoders and assembled and
disassembled once with the platform LLVM tools when the table was written; the
text is that tool's output for these words. Nothing here reads any other checkout
and no disassembler runs during the test.
"""
import contextlib
import gzip
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location('arm64_oracle_diff', ROOT / 'scripts/arm64-oracle-diff.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


H = load()
FILES = tuple(H.SPECS)

SAMPLES = (
    ('d503201f', 0x0, 'nop'),
    ('d65f03c0', 0x4, 'ret'),
    ('d65f0020', 0x8, 'ret x1'),
    ('d4000001', 0x20, 'svc #0'),
    ('d503233f', 0x38, 'paciasp'),
    ('09000020', 0x5c, '<unknown>'),
    ('f94003e0', 0x78, 'ldr x0, [sp]'),
    ('8affff00', 0x88, 'bic x0, x24, xzr, ror #63'),
    ('94000040', 0x90, 'bl 0x190'),
    ('14000040', 0x94, 'b 0x194'),
    ('54000200', 0xb8, 'b.eq 0xf8'),
    ('54000221', 0xc0, 'b.ne 0x104'),
    ('54000242', 0xc8, 'b.hs 0x110'),
    ('54000263', 0xd0, 'b.lo 0x11c'),
    ('54000284', 0xd8, 'b.mi 0x128'),
    ('540002a5', 0xe0, 'b.pl 0x134'),
    ('540002c6', 0xe8, 'b.vs 0x140'),
    ('540002e7', 0xf0, 'b.vc 0x14c'),
    ('54000308', 0xf8, 'b.hi 0x158'),
    ('54000329', 0x100, 'b.ls 0x164'),
    ('5400034a', 0x108, 'b.ge 0x170'),
    ('5400036b', 0x110, 'b.lt 0x17c'),
    ('5400038c', 0x118, 'b.gt 0x188'),
    ('540003ad', 0x120, 'b.le 0x194'),
    ('540003ce', 0x128, 'b.al 0x1a0'),
    ('34000200', 0x13c, 'cbz w0, 0x17c'),
    ('35000200', 0x164, 'cbnz w0, 0x1a4'),
    ('b4000200', 0x18c, 'cbz x0, 0x1cc'),
    ('b5000200', 0x1b4, 'cbnz x0, 0x1f4'),
    ('36000200', 0x1dc, 'tbz w0, #0x0, 0x21c'),
    ('37000200', 0x1f4, 'tbnz w0, #0x0, 0x234'),
    ('b6000200', 0x26c, 'tbz x0, #0x20, 0x2ac'),
    ('b7000200', 0x284, 'tbnz x0, #0x20, 0x2c4'),
    ('a9007bfd', 0x2fc, 'stp x29, x30, [sp]'),
    ('a9807bbd', 0x3b0, 'stp x29, x30, [x29, #0x0]!'),
    ('a9407bfd', 0x464, 'ldp x29, x30, [sp]'),
    ('a9407fff', 0x46c, 'ldp xzr, xzr, [sp]'),
    ('a9400440', 0x5cc, 'ldp x0, x1, [x2]'),
    ('91000000', 0x5f8, 'add x0, x0, #0x0'),
    ('910003e0', 0x628, 'mov x0, sp'),
    ('d1000000', 0x6d0, 'sub x0, x0, #0x0'),
    ('11401400', 0x7a8, 'add w0, w0, #0x5, lsl #12   ; =0x5000'),
    ('117fffe0', 0x7b4, 'add w0, wsp, #0xfff, lsl #12 ; =0xfff000'),
    ('31000000', 0x800, 'adds w0, w0, #0x0'),
    ('317ffc1f', 0x848, 'cmn w0, #0xfff, lsl #12     ; =0xfff000'),
    ('71001400', 0x8bc, 'subs w0, w0, #0x5'),
    ('7140001f', 0x904, 'cmp w0, #0x0, lsl #12       ; =0x0'),
    ('b1400000', 0x918, 'adds x0, x0, #0x0, lsl #12   ; =0x0'),
    ('b100141f', 0x94c, 'cmn x0, #0x5'),
    ('f17ffc00', 0x958, 'subs x0, x0, #0xfff, lsl #12 ; =0xfff000'),
    ('f100001f', 0x980, 'cmp x0, #0x0'),
    ('aa0003e0', 0xa48, 'mov x0, x0'),
    ('aa0107e2', 0xa78, 'orr x2, xzr, x1, lsl #1'),
    ('aa2103e2', 0xa84, 'mvn x2, x1'),
    ('92800000', 0xaf4, 'mov x0, #-0x1               ; =-1'),
    ('92a00000', 0xb24, 'movn x0, #0x0, lsl #16'),
    ('d2800000', 0xbb4, 'mov x0, #0x0                ; =0'),
    ('d2a00000', 0xbe4, 'movz x0, #0x0, lsl #16'),
    ('72800000', 0xc74, 'movk w0, #0x0'),
    ('72c00000', 0xcbc, '<unknown>'),
    ('f2800000', 0xd04, 'movk x0, #0x0'),
    ('1ac20be0', 0xd9c, 'udiv w0, wzr, w2'),
    ('1ac20c20', 0xdac, 'sdiv w0, w1, w2'),
    ('1adf2020', 0xdc0, 'lsl w0, w1, wzr'),
    ('1ac227e0', 0xddc, 'lsr w0, wzr, w2'),
    ('1ac22820', 0xdf8, 'asr w0, w1, w2'),
    ('1ac22c20', 0xe1c, 'ror w0, w1, w2'),
    ('9ac20820', 0xe34, 'udiv x0, x1, x2'),
    ('9ac20c3d', 0xe50, 'sdiv x29, x1, x2'),
    ('9adf2020', 0xe68, 'lsl x0, x1, xzr'),
    ('9adf2420', 0xe80, 'lsr x0, x1, xzr'),
    ('9ac22820', 0xe98, 'asr x0, x1, x2'),
    ('9ac22c20', 0xeb4, 'ror x0, x1, x2'),
    ('5ac00020', 0xed0, 'rbit w0, w1'),
    ('5ac00420', 0xee8, 'rev16 w0, w1'),
    ('5ac00820', 0xf00, 'rev w0, w1'),
    ('5ac01020', 0xf30, 'clz w0, w1'),
    ('5ac01420', 0xf48, 'cls w0, w1'),
    ('dac00020', 0xf90, 'rbit x0, x1'),
    ('dac00420', 0xfa8, 'rev16 x0, x1'),
    ('dac00820', 0xfc0, 'rev32 x0, x1'),
    ('dac00c20', 0xfd8, 'rev x0, x1'),
    ('dac01020', 0xff0, 'clz x0, x1'),
    ('dac01420', 0x1008, 'cls x0, x1'),
    ('3a420025', 0x1068, 'ccmn w1, w2, #0x5, eq'),
    ('3a42e025', 0x10a0, 'ccmn w1, w2, #0x5, al'),
    ('3a430825', 0x10a8, 'ccmn w1, #0x3, #0x5, eq'),
    ('7a420025', 0x10e8, 'ccmp w1, w2, #0x5, eq'),
    ('7a430825', 0x1128, 'ccmp w1, #0x3, #0x5, eq'),
    ('ba420025', 0x1168, 'ccmn x1, x2, #0x5, eq'),
    ('ba430825', 0x11a8, 'ccmn x1, #0x3, #0x5, eq'),
    ('fa420025', 0x11e8, 'ccmp x1, x2, #0x5, eq'),
    ('fa430825', 0x1228, 'ccmp x1, #0x3, #0x5, eq'),
    ('1a1f0020', 0x138c, 'adc w0, w1, wzr'),
    ('3a020020', 0x13a4, 'adcs w0, w1, w2'),
    ('5a020020', 0x13c4, 'sbc w0, w1, w2'),
    ('5a0203e0', 0x13c8, 'ngc w0, w2'),
    ('7a1f0020', 0x13e4, 'sbcs w0, w1, wzr'),
    ('7a0203fd', 0x13f0, 'ngcs w29, w2'),
    ('9a020020', 0x1400, 'adc x0, x1, x2'),
    ('ba0203e0', 0x1424, 'adcs x0, xzr, x2'),
    ('da1f0020', 0x1440, 'sbc x0, x1, xzr'),
    ('da0203e0', 0x1444, 'ngc x0, x2'),
    ('fa020020', 0x145c, 'sbcs x0, x1, x2'),
    ('fa0203fd', 0x1464, 'ngcs x29, x2'),
    ('2b027c20', 0x14cc, 'adds w0, w1, w2, lsl #31'),
    ('2b1f83fd', 0x14dc, '<unknown>'),
    ('2b1f1c3f', 0x14e0, 'cmn w1, wzr, lsl #7'),
    ('6b021c20', 0x1590, 'subs w0, w1, w2, lsl #7'),
    ('6b1f7fe0', 0x1598, 'negs w0, wzr, lsl #31'),
    ('6b021c3f', 0x15ac, 'cmp w1, w2, lsl #7'),
    ('ab02ffe0', 0x1674, 'adds x0, xzr, x2, lsl #63'),
    ('ab1ffc3f', 0x1684, 'cmn x1, xzr, lsl #63'),
    ('eb021c20', 0x1744, 'subs x0, x1, x2, lsl #7'),
    ('eb02fffd', 0x1750, 'negs x29, x2, lsl #63'),
    ('eb02003f', 0x1758, 'cmp x1, x2'),
    ('2b22003d', 0x1998, 'adds w29, w1, w2, uxtb'),
    ('2b220bff', 0x199c, 'cmn wsp, w2, uxtb #2'),
    ('2b22103f', 0x19a0, 'cmn w1, w2, uxtb #4'),
    ('2b221420', 0x19a4, '<unknown>'),
    ('2b2217e0', 0x19a8, '<unknown>'),
    ('2b22683f', 0x19dc, 'cmn w1, w2, uxtx #2'),
    ('6b220020', 0x1ad0, 'subs w0, w1, w2, uxtb'),
    ('6b22283f', 0x1aec, 'cmp w1, w2, uxth #2'),
    ('ab22003f', 0x1c14, 'cmn x1, w2, uxtb'),
    ('ab220820', 0x1c1c, 'adds x0, x1, w2, uxtb #2'),
    ('eb22083f', 0x1d4c, 'cmp x1, w2, uxtb #2'),
    ('eb22303d', 0x1d70, 'subs x29, x1, w2, uxth #4'),
    ('0a1f143d', 0x2088, 'and w29, w1, wzr, lsl #5'),
    ('0a8283ff', 0x20a8, '<unknown>'),
    ('0a22143d', 0x20b0, 'bic w29, w1, w2, lsl #5'),
    ('2a0217fd', 0x20e8, 'orr w29, wzr, w2, lsl #5'),
    ('2a221420', 0x2114, 'orn w0, w1, w2, lsl #5'),
    ('2a2203e0', 0x2118, 'mvn w0, w2'),
    ('4a1f7fe0', 0x2148, 'eor w0, wzr, wzr, lsl #31'),
    ('4a2217fd', 0x2184, 'eon w29, wzr, w2, lsl #5'),
    ('6a02003d', 0x21ac, 'ands w29, w1, w2'),
    ('6a02003f', 0x21b4, 'tst w1, w2'),
    ('6a220020', 0x21e8, 'bics w0, w1, w2'),
    ('8a021420', 0x2220, 'and x0, x1, x2, lsl #5'),
    ('aa3f143d', 0x22cc, 'orn x29, x1, xzr, lsl #5'),
    ('ca1f143d', 0x22ec, 'eor x29, x1, xzr, lsl #5'),
    ('ca221420', 0x2314, 'eon x0, x1, x2, lsl #5'),
    ('ea02143d', 0x235c, 'ands x29, x1, x2, lsl #5'),
    ('ea1ffc3f', 0x2364, 'tst x1, xzr, lsl #63'),
    ('ea3f03e0', 0x23b0, 'bics x0, xzr, xzr'),
    ('2a0203e0', 0x23f0, 'mov w0, w2'),
    ('b2401c20', 0x274c, 'orr x0, x1, #0xff'),
    ('f2401c3d', 0x2750, 'ands x29, x1, #0xff'),
    ('b2781c3f', 0x2758, 'orr sp, x1, #0xff00'),
    ('12003c20', 0x2768, 'and w0, w1, #0xffff'),
    ('92003fe0', 0x276c, 'and x0, xzr, #0xffff0000ffff'),
    ('b2003fe0', 0x2778, 'mov x0, #0xffff0000ffff     ; =281470681808895'),
    ('d2003ffd', 0x2784, 'eor x29, xzr, #0xffff0000ffff'),
    ('520713e0', 0x2794, 'eor w0, wzr, #0x3e000000'),
    ('720713fd', 0x2798, 'ands w29, wzr, #0x3e000000'),
    ('720713ff', 0x279c, 'tst wzr, #0x3e000000'),
    ('f202883f', 0x27c4, 'tst x1, #0xc001c001c001c001'),
    ('3200c020', 0x27c8, 'orr w0, w1, #0x1010101'),
    ('3201e7fd', 0x2808, 'mov w29, #-0x66666667       ; =-1717986919'),
    ('9240fc20', 0x29dc, '<unknown>'),
    ('9b427c20', 0x29f0, 'smulh x0, x1, x2'),
    ('9bc27c20', 0x29f4, 'umulh x0, x1, x2'),
    ('9b220c20', 0x2a50, 'smaddl x0, w1, w2, x3'),
    ('9b227c20', 0x2a68, 'smull x0, w1, w2'),
    ('9b228c20', 0x2a98, 'smsubl x0, w1, w2, x3'),
    ('9b22fc20', 0x2ab0, 'smnegl x0, w1, w2'),
    ('9ba20c20', 0x2ae0, 'umaddl x0, w1, w2, x3'),
    ('9ba27c20', 0x2af8, 'umull x0, w1, w2'),
    ('9ba28c20', 0x2b28, 'umsubl x0, w1, w2, x3'),
    ('9ba2fc20', 0x2b40, 'umnegl x0, w1, w2'),
    ('1b1f0c3d', 0x2b70, 'madd w29, w1, wzr, w3'),
    ('1b1f7c20', 0x2b7c, 'mul w0, w1, wzr'),
    ('1b1f8fe0', 0x2b94, 'msub w0, wzr, wzr, w3'),
    ('1b02fc20', 0x2ba0, 'mneg w0, w1, w2'),
    ('9b020c20', 0x2ba8, 'madd x0, x1, x2, x3'),
    ('9b027c20', 0x2bc0, 'mul x0, x1, x2'),
    ('9b028c20', 0x2bd4, 'msub x0, x1, x2, x3'),
    ('9b1fffe0', 0x2bec, 'mneg x0, xzr, xzr'),
    ('13820020', 0x2c10, 'extr w0, w1, w2, #0x0'),
    ('1382803f', 0x2c28, '<unknown>'),
    ('13810020', 0x2c30, 'ror w0, w1, #0x0'),
    ('93c20020', 0x2cb8, 'extr x0, x1, x2, #0x0'),
    ('93c11420', 0x2cd8, 'ror x0, x1, #0x5'),
    ('13071c20', 0x2d84, 'sbfx w0, w1, #7, #1'),
    ('13010020', 0x2d88, 'sbfiz w0, w1, #31, #1'),
    ('13017c20', 0x2d90, 'asr w0, w1, #1'),
    ('13003c20', 0x2d94, 'sxth w0, w1'),
    ('13001fff', 0x2de8, 'sxtb wzr, wzr'),
    ('33007c20', 0x2df8, 'bfxil w0, w1, #0, #32'),
    ('331f7820', 0x2e08, 'bfi w0, w1, #1, #31'),
    ('531f7820', 0x2e70, 'lsl w0, w1, #1'),
    ('531f0020', 0x2e74, 'ubfiz w0, w1, #1, #1'),
    ('53017c20', 0x2e78, 'lsr w0, w1, #1'),
    ('53003c20', 0x2e7c, 'uxth w0, w1'),
    ('53071fe0', 0x2e88, 'ubfx w0, wzr, #7, #1'),
    ('53001ffd', 0x2ebc, 'uxtb w29, wzr'),
    ('937f0020', 0x2ee4, 'sbfiz x0, x1, #1, #1'),
    ('93431820', 0x2eec, 'sbfx x0, x1, #3, #4'),
    ('93403c20', 0x2ef4, 'sxth x0, w1'),
    ('9345ffe0', 0x2ef8, 'asr x0, xzr, #5'),
    ('93407fe0', 0x2f00, 'sxtw x0, wzr'),
    ('93401c3d', 0x2f14, 'sxtb x29, w1'),
    ('b37f0020', 0x2f5c, 'bfi x0, x1, #1, #1'),
    ('b341fc20', 0x2f60, 'bfxil x0, x1, #1, #63'),
    ('d3401c20', 0x2fd4, 'ubfx x0, x1, #0, #8'),
    ('d345fc20', 0x2fe0, 'lsr x0, x1, #5'),
    ('d35d73e0', 0x2fec, 'lsl x0, xzr, #35'),
    ('d37f003d', 0x3008, 'ubfiz x29, x1, #1, #1'),
    ('73001c20', 0x31fc, '<unknown>'),
    ('f90003e0', 0x3214, 'str x0, [sp]'),
    ('f9000020', 0x325c, 'str x0, [x1]'),
    ('b90003e0', 0x32e8, 'str w0, [sp]'),
    ('b94003e0', 0x3354, 'ldr w0, [sp]'),
    ('1a820020', 0x33e0, 'csel w0, w1, w2, eq'),
    ('1a820420', 0x3420, 'csinc w0, w1, w2, eq'),
    ('5a820020', 0x3460, 'csinv w0, w1, w2, eq'),
    ('5a820420', 0x34a0, 'csneg w0, w1, w2, eq'),
    ('9a820020', 0x34e0, 'csel x0, x1, x2, eq'),
    ('9a820420', 0x3520, 'csinc x0, x1, x2, eq'),
    ('da820020', 0x3560, 'csinv x0, x1, x2, eq'),
    ('da820420', 0x35a0, 'csneg x0, x1, x2, eq'),
    ('1a9f17ff', 0x3614, 'cset wzr, eq'),
    ('5a811020', 0x3618, 'cinv w0, w1, eq'),
    ('5a9f53fd', 0x3628, 'csetm w29, mi'),
    ('5a815420', 0x3634, 'cneg w0, w1, mi'),
    ('9a9fd7ff', 0x3690, 'cset xzr, gt'),
    ('da9fc3e0', 0x369c, 'csetm x0, le'),
    ('da81003f', 0x36a4, 'cinv xzr, x1, ne'),
    ('da815420', 0x36ac, 'cneg x0, x1, mi'),
)

NOP = 'd503201f'
ADD5 = '91001420'
ADD_FP = '910043fd'
MOV_FP = '910003fd'
MOVK32 = '72c00000'
RET_X1 = 'd65f0020'
SIMD = '09000020'
COVERAGE = 'arm64-coverage-vectors/vectors.tsv'
FEATURE = 'arm64-feature-vectors/vectors.tsv'


def split_text(text):
    parts = text.split(None, 1)
    return parts[0], (parts[1] if len(parts) > 1 else '')


def line_for(relpath, group, address, word, text):
    mnemonic, operands = split_text(text)
    values = {'group': group, 'address': '%#x' % address, 'word': word, 'objdump': text,
              'mnemonic': mnemonic, 'operands': operands, 'source': 'synthetic'}
    return '\t'.join(values[c] for c in H.SPECS[relpath][1]) + '\n'


def write_tree(root, rows_by_file, newline=b'\n'):
    for relpath, rows in rows_by_file.items():
        path = Path(root) / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        body = b'# synthetic header\n# second comment line\n\n'
        for row in rows:
            body += row if isinstance(row, bytes) else row.encode('utf-8')
        path.write_bytes(body.replace(b'\n', newline))


def sample_rows():
    rows = {relpath: [] for relpath in FILES}
    for index, (word, address, text) in enumerate(SAMPLES):
        relpath = FILES[index % len(FILES)]
        rows[relpath].append(line_for(relpath, 'g%d' % index, address, word, text))
    return rows


def coverage_rows(cases):
    return {COVERAGE: [line_for(COVERAGE, 'case', address, word, text) for word, address, text in cases]}


def run_harness(root, **options):
    options.setdefault('allow_unpinned', True)
    return H.run_harness(root, **options)


def quiet_main(argv):
    argv = list(argv)
    if '--no-allow' in argv:
        argv.remove('--no-allow')
    elif '--allow-unpinned' not in argv:
        argv.append('--allow-unpinned')
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return H.main(argv)


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def tree(self, rows_by_file, name='vectors', newline=b'\n'):
        root = self.base / name
        write_tree(root, rows_by_file, newline)
        return root

    def classify_all(self, rows_by_file, **options):
        seen = []
        summary, blocking = run_harness(self.tree(rows_by_file), rowsink=seen.append, **options)
        return summary, blocking, {(row[3], row[6]): row[7:9] for row in seen}

    def test_samples_agree_and_cover_every_kind(self):
        summary, blocking, _ = self.classify_all(sample_rows())
        self.assertEqual(blocking, [])
        inventory = H.derive_inventory((ROOT / 'src/airs/arm64.py').read_text(), (ROOT / 'src/airs/cfg.py').read_text())
        for decoder, (kinds, _codes) in inventory.items():
            self.assertEqual(set(summary['agree_by_kind'][decoder]), kinds, decoder)
        totals = summary['totals']['cfg']
        for category in ('AGREE', 'AGREE-REJECT', 'BOTH-REJECT', 'SCOPE-DECLINE'):
            self.assertGreater(totals.get(category, 0), 0, category)
        self.assertGreater(summary['totals']['linear']['SCOPE-DECLINE'], 0)
        self.assertEqual(sum(1 for f in FILES if summary['inputs'][f]['present']), len(FILES))
        self.assertEqual(summary['inputs'][COVERAGE]['pin'], 'mismatch')

    def test_every_classification_outcome(self):
        cases = [
            (NOP, 0x0, 'nop'),
            (NOP, 0x4, '<unknown>'),
            (NOP, 0x8, 'ret'),
            (ADD5, 0xc, 'add x0, x1, #0x6'),
            (ADD5, 0x10, 'add x0, x1, #0x5'),
            (NOP, 0x14, 'nop foo'),
            (MOVK32, 0x18, 'movk w0, #0x0'),
            (MOVK32, 0x1c, '<unknown>'),
            (RET_X1, 0x20, 'ret x1'),
            (SIMD, 0x24, '<unknown>'),
            (NOP, 0x28, 'nop'),
            (NOP, 0x28, 'ret'),
        ]
        rows = coverage_rows(cases)
        rows[COVERAGE] += [b'bad\t0x30\tzz\tnop\n', b'bad\t0x34\tdeadbeef\n', b'bad\txx\tdeadbeef\tnop\n',
                           b'bad\t0x38\tdeadbeef\t123 foo\n', b'bad\t0x3c\tdeadbeef\t\xff\xfe\n']
        rows[FEATURE] = [line_for(FEATURE, 'g', 0x100, NOP, '<unknown>')]
        summary, blocking, outcome = self.classify_all(rows)
        expected = {
            0x0: {'linear': ('AGREE', ''), 'cfg': ('AGREE', '')},
            0x4: {'linear': ('OVER-ADMIT', ''), 'cfg': ('OVER-ADMIT', '')},
            0x8: {'linear': ('WRONG-ADMIT', 'F'), 'cfg': ('WRONG-ADMIT', 'F')},
            0xc: {'linear': ('WRONG-ADMIT', 'O'), 'cfg': ('WRONG-ADMIT', 'O')},
            0x10: {'linear': ('AGREE', ''), 'cfg': ('AGREE', '')},
            0x14: {'linear': ('WRONG-ADMIT', 'O'), 'cfg': ('WRONG-ADMIT', 'O')},
            0x18: {'linear': ('SCOPE-DECLINE', ''), 'cfg': ('FALSE-INVALID', '')},
            0x1c: {'linear': ('BOTH-REJECT', ''), 'cfg': ('AGREE-REJECT', '')},
            0x20: {'linear': ('SCOPE-DECLINE', ''), 'cfg': ('SCOPE-DECLINE', '')},
            0x24: {'linear': ('BOTH-REJECT', ''), 'cfg': ('BOTH-REJECT', '')},
            0x28: {'linear': ('AGREE', ''), 'cfg': ('AGREE', '')},
        }
        for address, by_decoder in expected.items():
            for decoder, result in by_decoder.items():
                self.assertEqual(tuple(outcome[(address, decoder)]), result, (hex(address), decoder))
        reasons = {(r['address'], r['decoder']): r['reason'] for r in blocking}
        self.assertEqual(reasons[('0x14', 'cfg')], 'unparsed-operand')
        self.assertEqual(reasons[('0x4', 'cfg')], 'over-admit')
        self.assertEqual(reasons[('0x18', 'cfg')], 'false-invalid')
        self.assertEqual(sum(1 for r in blocking if r['category'] == 'ORACLE-CONFLICT'), 1)
        self.assertEqual(sorted(r['reason'] for r in blocking if r['category'] == 'UNPARSEABLE'),
                         ['bad-address', 'bad-oracle-text', 'bad-utf8', 'bad-word', 'column-count-3-expected-4'])
        hint = [r for r in blocking if r['file'] == FEATURE]
        self.assertEqual(hint[0]['category'], 'OVER-ADMIT')
        self.assertEqual(hint[0]['oracle_elsewhere'], 'coverage:mixed')
        self.assertEqual(summary['inputs'][COVERAGE]['malformed_rows'], 5)
        self.assertEqual(summary['blocking_total'], len(blocking))
        self.assertGreater(summary['cross_file_validity']['words_differing'], 0)

    def test_effects_level_and_decoder_failures(self):
        rows = coverage_rows([(ADD_FP, 0x0, 'add x29, sp, #0x10'), (MOV_FP, 0x4, 'mov x29, sp')])
        _, clean, _ = self.classify_all(rows)
        self.assertEqual(clean, [])
        with mock.patch.object(H.arm64, '_FP_DESTINATION_KINDS', frozenset()):
            _, blocking, outcome = self.classify_all(rows)
        self.assertEqual(outcome[(0x0, 'linear')], ('WRONG-ADMIT', 'P'))
        self.assertEqual(outcome[(0x4, 'cfg')], ('WRONG-ADMIT', 'P'))

        def boom(word, address=0):
            raise RuntimeError('boom')

        def mystery(word, address=0):
            raise H.ModelError('mystery_code', 'x', address)

        def odd_kind(word, address=0):
            return H.arm64.Instruction(address, word, 'zzz')

        decoders = (('boom', boom), ('mystery', mystery), ('odd', odd_kind))
        _, blocking, outcome = self.classify_all(coverage_rows([(NOP, 0x0, 'nop')]), decoders=decoders)
        self.assertEqual([r['category'] for r in blocking], ['DECODER-EXCEPTION'] * 3)
        self.assertEqual(sorted(r['reason'] for r in blocking), ['exception', 'unknown-code', 'unknown-kind'])

    def test_parsing_rules(self):
        parse = H.parse_oracle
        self.assertEqual(parse('add', 'x0, x1, #0x10 // =0x10', True).tokens, ('x0', 'x1', '#16'))
        self.assertEqual(parse('add', 'x0, x1, #0x10 ; =0x10', True).tokens, ('x0', 'x1', '#16'))
        self.assertEqual(parse('bl', '0x190 <sym+0x190>', True).tokens, ('@400',))
        self.assertEqual(parse('b', '0x40', False).tokens, ('@?',))
        self.assertEqual(parse('mov', 'x8, #-0xd943', True).tokens, ('x8', '#%d' % ((1 << 64) - 0xd943)))
        self.assertEqual(parse('mov', 'w8, #-1', True).tokens, ('w8', '#4294967295'))
        self.assertEqual(parse('b.cs', '0x10', True).mnemonic, 'b.hs')
        self.assertEqual(parse('csel', 'x0, x1, x2, cc', True).tokens, ('x0', 'x1', 'x2', 'lo'))
        self.assertEqual(parse('ldp', 'x5, x26, [sp, #-0x110]', True).tokens, ('x5', 'x26', '[sp,#-272]'))
        self.assertEqual(parse('stp', 'x15, x7, [x10, #0x98]!', True).tokens, ('x15', 'x7', '[x10,#152]!'))
        self.assertEqual(parse('ldr', 'x0, [sp, #0x0]', True).tokens, ('x0', '[sp]'))
        self.assertEqual(parse('ldp', 'x29, x30, [sp], #0x10', True).tokens, ('x29', 'x30', '[sp]', '#16'))
        self.assertEqual(parse('add', 'x0, x1, x2, lsl #0x0', True).tokens, ('x0', 'x1', 'x2'))
        self.assertEqual(parse('neg', 'w0, w15, asr #0', True).tokens, ('w0', 'w15', 'asr #0'))
        self.assertEqual(parse('cmn', 'w1, w2, uxtw #0', True).tokens, ('w1', 'w2', 'uxtw'))
        self.assertEqual(parse('mov', 'fp, lr', True).tokens, ('x29', 'x30'))
        self.assertEqual(parse('<unknown>', '', True).state, 'unknown')
        self.assertEqual(parse('123', '', True).state, 'bad')
        self.assertTrue(parse('add', 'v0.4s, x1', True).tokens[0].startswith('?raw'))
        self.assertEqual(H.oracle_effects('stp', ('x29', 'x30', '[sp,#-16]!')), (True, False))
        self.assertEqual(H.oracle_effects('ldp', ('x29', 'x30', '[sp]', '#16')), (True, True))
        self.assertEqual(H.oracle_effects('add', ('sp', 'sp', '#16')), (True, False))
        self.assertEqual(H.oracle_effects('cmp', ('x29', '#0')), (False, False))
        self.assertEqual(H.oracle_effects('ldr', ('w29', '[sp,#8]')), (False, True))

    def test_line_endings_limit_and_absent_files(self):
        rows = sample_rows()
        lf, _ = run_harness(self.tree(rows, 'lf'))
        crlf, _ = run_harness(self.tree(rows, 'crlf', newline=b'\r\n'))
        for summary in (lf, crlf):
            for entry in summary['inputs'].values():
                entry.pop('sha256'), entry.pop('git_blob_id'), entry.pop('bytes')
        self.assertEqual(lf, crlf)
        limited, _ = run_harness(self.tree(coverage_rows([(NOP, 0, 'nop'), (ADD5, 4, 'add x0, x1, #5'), (SIMD, 8, '<unknown>')]), 'limit'), limit=2)
        info = limited['inputs'][COVERAGE]
        self.assertEqual((info['rows'], info['decoded_rows'], info['unknown_rows']), (3, 2, 1))
        self.assertEqual(info['comment_lines'], 2)
        self.assertEqual(info['blank_lines'], 1)
        self.assertFalse(limited['inputs'][FEATURE]['present'])
        with self.assertRaises(H.HarnessRefusal):
            run_harness(self.base / 'missing')

    def test_pins_enforced_by_default(self):
        with self.assertRaises(H.PinRefusal):
            H.run_harness(self.tree(coverage_rows([(NOP, 0, 'nop')]), 'pinned'))

    def test_base_register_and_ret_are_compared_exactly(self):
        def agree(ins, mnemonic, text):
            return H.classify(('ok', ins), H.parse_oracle(mnemonic, text, True), True)[0]

        I = H.arm64.Instruction
        self.assertEqual(agree(I(0, 0xa9007bbd, 'stp', rd=29, rn=31, rt2=30, addressing='offset'), 'stp', 'x29, x30, [sp]'), 'AGREE')
        self.assertNotEqual(agree(I(0, 0xa9007bbd, 'stp', rd=29, rn=5, rt2=30, addressing='offset'), 'stp', 'x29, x30, [x29]'), 'AGREE')
        self.assertEqual(agree(I(0, 0xa9007bbd, 'stp', rd=29, rn=5, rt2=30, addressing='offset'), 'stp', 'x29, x30, [x5]'), 'AGREE')
        self.assertNotEqual(agree(I(0, 0xf9400000, 'xldr', rd=0, rn=7, immediate=8), 'ldr', 'x0, [x29, #0x8]'), 'AGREE')
        self.assertEqual(agree(I(0, 0xf9400000, 'xldr', rd=0, rn=7, immediate=8), 'ldr', 'x0, [x7, #0x8]'), 'AGREE')
        self.assertEqual(agree(I(0, 0xd65f03c0, 'ret', rn=30), 'ret', ''), 'AGREE')
        self.assertNotEqual(agree(I(0, 0xd65f0020, 'ret', rn=1), 'ret', ''), 'AGREE')
        self.assertEqual(agree(I(0, 0xd65f0020, 'ret', rn=1), 'ret', 'x1'), 'AGREE')

    def test_sp_effect_disagreement_is_blocking(self):
        ins = H.arm64.Instruction(0, 0x910043ff, 'add', rd=31, rn=31, immediate=16)
        oracle = H.parse_oracle('add', 'sp, sp, #0x10', True)
        self.assertEqual(H.classify(('ok', ins), oracle, True)[0], 'AGREE')
        with mock.patch.object(H.arm64.Instruction, 'changes_sp', property(lambda self: False)):
            result = H.classify(('ok', ins), oracle, True)
        self.assertEqual(result[:2], ('WRONG-ADMIT', 'P'))

    def test_kind_table_completeness_check(self):
        sources = ((ROOT / 'src/airs/arm64.py').read_text(), (ROOT / 'src/airs/cfg.py').read_text())
        inventory = H.derive_inventory(*sources)
        errors, stale = H.check_inventory(inventory, H.KIND_TABLE, H.arm64._FP_DESTINATION_KINDS, H.VALIDITY_CODES, H.SCOPE_CODES)
        self.assertEqual((errors, stale), ([], []))
        table = dict(H.KIND_TABLE)
        del table['xmovk']
        errors, _ = H.check_inventory(inventory, table, H.arm64._FP_DESTINATION_KINDS, H.VALIDITY_CODES, H.SCOPE_CODES)
        self.assertTrue(any("'xmovk'" in e for e in errors))
        errors, _ = H.check_inventory(inventory, H.KIND_TABLE, H.arm64._FP_DESTINATION_KINDS, H.VALIDITY_CODES, frozenset())
        self.assertTrue(any('not classified' in e for e in errors))
        errors, stale = H.check_inventory(inventory, {**H.KIND_TABLE, 'extra': ('nop', 'nop', 0)}, frozenset(('nowhere',)), H.VALIDITY_CODES, H.SCOPE_CODES)
        self.assertEqual(stale, ['extra'])
        self.assertTrue(any("'nowhere'" in e for e in errors))

    def test_kind_derivation_on_synthetic_source(self):
        source = (
            "def decode_instruction(word, address=0):\n"
            "    if word == 1:\n"
            "        return Instruction(address, word, 'nop')\n"
            "    table = {1: ('stp', 'pre'), 2: ('ldp', 'post')}\n"
            "    form = table.get(word & 3)\n"
            "    if form:\n"
            "        kind, mode = form\n"
            "        return Instruction(address, word, kind, addressing=mode)\n"
            "    kind = ('x' if word & 2 else 'w') + ('foo', 'bar')[word & 1]\n"
            "    if word == 2:\n"
            "        raise ModelError('unsupported_instruction', 'x')\n"
            "    return Instruction(address, word, kind)\n")
        derived = H.derive_decoder(source)
        self.assertEqual(derived.kinds, {'nop', 'stp', 'ldp', 'xfoo', 'xbar', 'wfoo', 'wbar'})
        self.assertEqual(derived.codes, {'unsupported_instruction'})
        self.assertFalse(derived.includes_linear)
        chained = H.derive_decoder("def decode_instruction(word, address=0):\n    return decode_linear(word, address)\n")
        self.assertTrue(chained.includes_linear)
        for bad in ("def decode_instruction(word):\n    for x in word:\n        pass\n",
                    "def decode_instruction(word):\n    return word\n",
                    "def decode_instruction(word):\n    return Instruction(0, word, undefined_name)\n",
                    "def decode_instruction(word):\n    raise ModelError(some_code)\n",
                    "def other(word):\n    return 1\n"):
            with self.assertRaises(H.DerivationError):
                H.derive_decoder(bad)

    def test_out_dir_rules(self):
        root = self.base / 'repo'
        (root / 'docs').mkdir(parents=True)
        lines = ['# comment', 'local-evidence/', '*.log', '/build/', 'cache']
        allowed = H.out_dir_allowed
        self.assertFalse(allowed(root / 'docs' / 'x', root, lines))
        self.assertFalse(allowed(root, root, lines))
        self.assertFalse(allowed(root / '.git' / 'x', root, lines))
        self.assertTrue(allowed(root / 'local-evidence' / 'run1', root, lines))
        self.assertTrue(allowed(root / 'build' / 'x', root, lines))
        self.assertFalse(allowed(root / 'sub' / 'build' / 'x', root, lines))
        self.assertFalse(allowed(root / 'out.log', root, lines))
        self.assertFalse(allowed(root / 'cache' / 'x', root, lines))
        self.assertTrue(allowed(self.base / 'elsewhere', root, lines))
        real = (ROOT / '.gitignore').read_text().splitlines()
        self.assertTrue(allowed(ROOT / 'local-evidence' / 'unwind-oracle' / 'run', ROOT, real))
        self.assertFalse(allowed(ROOT / 'scripts' / 'run', ROOT, real))

    def test_main_refusals_and_exit_codes(self):
        vectors = self.tree(sample_rows())
        inside = ROOT / 'tests' / '_oracle_diff_unit_test_out'
        self.assertEqual(quiet_main(['--vectors-root', str(vectors), '--out', str(inside)]), 2)
        self.assertFalse(inside.exists())
        self.assertEqual(quiet_main(['--vectors-root', str(vectors), '--out', str(vectors / 'out')]), 2)
        self.assertEqual(quiet_main(['--vectors-root', str(self.base / 'nope'), '--out', str(self.base / 'o1')]), 2)
        self.assertEqual(quiet_main(['--vectors-root', str(vectors), '--out', str(self.base / 'o2'), '--limit', '0']), 2)
        self.assertEqual(quiet_main(['--vectors-root', str(vectors), '--out', str(self.base / 'o3'), '--no-allow']), 3)
        partial = self.tree(coverage_rows([(NOP, 0, 'nop')]), 'partial')
        self.assertEqual(quiet_main(['--vectors-root', str(partial), '--out', str(self.base / 'o3b'), '--no-allow']), 3)
        self.assertEqual(quiet_main(['--vectors-root', str(partial), '--out', str(self.base / 'o3c')]), 0)
        afile = self.base / 'afile'
        afile.write_text('x')
        self.assertEqual(quiet_main(['--vectors-root', str(vectors), '--out', str(afile)]), 2)
        with mock.patch.object(H, 'derive_inventory', side_effect=RuntimeError('boom')):
            self.assertEqual(quiet_main(['--vectors-root', str(vectors), '--out', str(self.base / 'o3d')]), 2)
        with mock.patch.object(H, 'check_inventory', return_value=(['broken'], [])):
            self.assertEqual(quiet_main(['--vectors-root', str(vectors), '--out', str(self.base / 'o3e')]), 2)
        self.assertEqual(quiet_main(['--vectors-root', str(vectors), '--out', str(self.base / 'o4')]), 0)
        self.assertEqual(quiet_main(['--vectors-root', str(vectors), '--out', str(self.base / 'o4')]), 2)
        self.assertEqual(quiet_main(['--vectors-root', str(vectors), '--out', str(self.base / 'o4'), '--overwrite']), 0)
        failing = self.tree(coverage_rows([(NOP, 0, '<unknown>')]), 'failing')
        self.assertEqual(quiet_main(['--vectors-root', str(failing), '--out', str(self.base / 'o5')]), 1)
        text = (self.base / 'o5' / 'disagreements.tsv').read_text().splitlines()
        self.assertEqual(text[0].split('\t'), list(H.DISAGREEMENT_COLUMNS))
        self.assertEqual(len(text), 3)

    def test_outputs_are_deterministic_and_split(self):
        vectors = self.tree(sample_rows())
        outputs = []
        for name in ('a', 'b'):
            out = self.base / name
            self.assertEqual(quiet_main(['--vectors-root', str(vectors), '--out', str(out), '--full']), 0)
            outputs.append(out)
        for name in ('summary.json', 'disagreements.tsv', 'rows.tsv.gz'):
            self.assertEqual((outputs[0] / name).read_bytes(), (outputs[1] / name).read_bytes(), name)
        with gzip.open(outputs[0] / 'rows.tsv.gz', 'rt') as handle:
            self.assertEqual(len(handle.read().splitlines()), 2 * len(SAMPLES))
        summary = (outputs[0] / 'summary.json').read_text()
        self.assertTrue(summary.endswith('}\n'))
        self.assertNotIn(str(self.base), summary)
        self.assertTrue((outputs[0] / 'run-info.json').is_file())
        many = coverage_rows([(NOP, 4 * n, '<unknown>') for n in range(5)])
        out = self.base / 'split'
        with mock.patch.object(H, 'PART_ROWS', 4):
            self.assertEqual(quiet_main(['--vectors-root', str(self.tree(many, 'many')), '--out', str(out)]), 1)
        parts = sorted(p.name for p in out.glob('disagreements-*.tsv'))
        self.assertEqual(parts, ['disagreements-0001.tsv', 'disagreements-0002.tsv', 'disagreements-0003.tsv'])
        self.assertEqual([len((out / p).read_text().splitlines()) - 1 for p in parts], [4, 4, 2])
        self.assertFalse((out / 'disagreements.tsv').exists())

if __name__ == '__main__':
    unittest.main()
