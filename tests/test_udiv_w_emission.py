"""Owned complete Mach-O W UDIV witnesses; parser and engine run without mocks."""
import os
from pathlib import Path
import struct
import tempfile
import unittest

from airs import ANALYSIS_MODEL_VERSION
from airs.engine import audit_path
from airs.report import dumps, load_report
from parser_helpers import regular_unwind
from test_rbit_x_candidate import NOP, RET, PAIR_PRO, PAIR_EPI
from test_udiv_w import word


OUTPUT = Path(__file__).resolve().parents[1] / 'local-evidence/w-udiv-v43'


def owned_macho(encoding):
    """Independent final-image builder, two entries and a declared owned sink."""
    base = 0x100000000
    # Call at text+28 targets the separate entry at text+256.
    call = 0x94000000 | ((0x100 - 28) // 4)
    words = (*PAIR_PRO, 0x92800000, 0xd2800041, word(19, 0, 1), call, *PAIR_EPI)
    text = struct.pack('<'+'I'*len(words), *words)
    text += struct.pack('<I', NOP) * ((0x100 - len(text)) // 4)
    text += struct.pack('<II', NOP, RET)
    compact = regular_unwind(((0x1000, encoding), (0x1100, 0x02000000)), 0x1108)
    sections = ((b'__text', 0x1000, text, 0x80000400),
                (b'__unwind_info', 0x2000, compact, 0))
    payload = bytearray(0x3000)
    starts = b'\x80\x20\x80\x02\x00'  # deltas0x1000,0x100 then terminator
    payload.extend(starts)
    segment = bytearray(struct.pack('<II16sQQQQiiII', 0x19, 72+80*2, b'__TEXT',
                                    base, 0x4000, 0, len(payload), 7, 5, 2, 0))
    for name, offset, content, flags in sections:
        payload[offset:offset+len(content)] = content
        segment.extend(struct.pack('<16s16sQQIIIIIIII', name, b'__TEXT', base+offset,
                                   len(content), offset, 2, 0, 0, flags, 0, 0, 0))
    commands = bytes(segment)+struct.pack('<IIII', 0x26, 16, 0x3000, len(starts))
    commands += struct.pack('<II', 0x1b, 24)+bytes(range(16))
    header = struct.pack('<8I', 0xfeedfacf, 0x0100000c, 0, 2, 3, len(commands), 0, 0)
    payload[:len(header+commands)] = header+commands
    return bytes(payload)


class WUDIVEmissionTests(unittest.TestCase):
    def test_complete_owned_images_produce_correct_and_wrong_recovery_reports(self):
        OUTPUT.mkdir(parents=True, exist_ok=True)
        for encoding, verdict in ((0x04000001, 'agreement'), (0x04000000, 'inconsistency')):
            with tempfile.TemporaryDirectory(dir=OUTPUT) as directory:
                source = Path(directory) / 'owned-w-udiv.macho'
                source.write_bytes(owned_macho(encoding))
                report = audit_path(source)
                self.assertEqual(report['generator']['analysis_model_version'], ANALYSIS_MODEL_VERSION)
                self.assertEqual(report['summary']['function_count'], 2)
                first = report['findings'][0]
                self.assertEqual((first['verdict'], first['scope'], first['checked_pcs']),
                                 (verdict, 'synchronous_call_sites', ['0x10000101c']))
                self.assertEqual(first['function']['boundary_source'], 'lc_function_starts')
                self.assertEqual(report['findings'][1]['verdict'], 'agreement')
                if verdict == 'inconsistency':
                    self.assertTrue(any(e.get('observed') == 'constant 0x7fffffff' for e in first['evidence']))
                target = OUTPUT / f'{ANALYSIS_MODEL_VERSION}-{verdict}.json'
                self.assertFalse(target.exists(), 'Reuse the accepted emission instead of overwriting it')
                target.write_text(dumps(report), encoding='utf-8')
                self.assertEqual(load_report(target), report)
