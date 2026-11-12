"""Strict generated-vector parsing, without running assembler tools."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('generate', ROOT / 'scripts/arm64-oracle-generate.py')
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)
HEADER = 'words.o: file format mach-o arm64\n\nDisassembly of section __TEXT,__text:\n0000000000000000 <ltmp0>:\n'


class GenerateTests(unittest.TestCase):
    def test_word_and_byte_layouts_and_unknown(self):
        for raw in ('d503201f', '1f 20 03 d5'):
            rows = G.parse_disassembly(HEADER + '0: ' + raw + ' nop\n4: 00000000 <unknown>\n', [0xd503201f, 0])
            self.assertEqual(rows, [(0, 0xd503201f, 'nop', ''), (4, 0, '<unknown>', '')])
        rows = G.parse_disassembly(HEADER + '0: b94003e0 ldr\tw0, [sp]\n', [0xb94003e0])
        self.assertEqual(rows[0][3], 'w0, [sp]')

    def test_mismatch_refusals(self):
        for body in ('', '0: d503201e nop\n', '4: d503201f nop\n',
                     '0: d503201f nop\n0: d503201f nop\n',
                     '0: d503201f nop\nunexpected\n', '0: nop\n'):
            with self.subTest(body=body), self.assertRaises(G.Refusal):
                G.parse_disassembly(HEADER + body, [0xd503201f])
        with self.assertRaises(G.Refusal):
            G.parse_disassembly('0: d503201f nop\n', [0xd503201f])

    def test_input_is_only_distinct_inst_words(self):
        self.assertEqual(G.read_words('.inst 0xd503201f\n.inst 0x00000000\n'), [0xd503201f, 0])
        for text in ('', '.inst 0x00000000\n.inst 0x00000000\n', '.include "other"\n', '.inst 0x100000000\n'):
            with self.assertRaises(G.Refusal):
                G.read_words(text)

    def test_tool_failure_is_one_line_exit_two(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'words.s'
            source.write_text('.inst 0xd503201f\n')
            with mock.patch.object(G, 'run_tool', side_effect=G.Refusal('tool failed\nmore')), contextlib.redirect_stderr(io.StringIO()) as error:
                result = G.main(['--input', str(source), '--out', directory, '--clang', 'clang', '--objdump', 'llvm-objdump'])
            self.assertEqual(result, 2)
            self.assertEqual(len(error.getvalue().splitlines()), 1)
            self.assertFalse((Path(directory) / 'generated.tsv').exists())

    def test_discovery_and_command_failure(self):
        with mock.patch.object(G.sys, 'platform', 'darwin'), mock.patch.object(G, 'run_tool', return_value='tool\n') as run:
            self.assertEqual(G.locate('clang', None), 'tool')
            run.assert_called_once_with(['xcrun', '--find', 'clang'])
        with mock.patch.object(G.sys, 'platform', 'linux'), mock.patch.object(G.shutil, 'which', return_value=None):
            with self.assertRaises(G.Refusal):
                G.locate('clang', None)
        self.assertEqual(G.locate('clang', 'override'), 'override')
        with mock.patch.object(G.subprocess, 'run', return_value=mock.Mock(returncode=1, stderr='failed\n', stdout='')):
            with self.assertRaisesRegex(G.Refusal, 'exit 1'):
                G.run_tool(['clang', '--version'])

    def test_cli_writes_boundary_layout_and_never_executes_object(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'words.s'
            source.write_text('.inst 0xd503201f\n')
            commands = []
            def tool(argv):
                commands.append(argv)
                if '--version' in argv:
                    return 'version\n'
                if '--disassemble' in argv:
                    return HEADER + '0: d503201f nop\n'
                return ''
            args = ['--input', str(source), '--out', directory, '--clang', 'clang', '--objdump', 'llvm-objdump']
            with mock.patch.object(G, 'run_tool', side_effect=tool):
                self.assertEqual(G.main(args), 0)
            self.assertEqual((Path(directory) / 'generated.tsv').read_text(),
                             '# address\tword\tmnemonic\toperands\n0x00000000\td503201f\tnop\t\n')
            self.assertEqual([command[0] for command in commands], ['clang', 'llvm-objdump', 'clang', 'llvm-objdump'])
            self.assertIn('arm64-apple-macos', commands[2])
            self.assertIn('-c', commands[2])
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(G.main(args), 2)
