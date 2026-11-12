#!/usr/bin/env python3
"""Assemble generated .inst words and record LLVM disassembly, never execute it."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


class Refusal(ValueError):
    """Malformed input, incomplete disassembly, or a failed tool."""


def read_words(text):
    words = []
    for number, line in enumerate(text.splitlines(), 1):
        match = re.fullmatch(r'\.inst 0x([0-9a-f]{8})', line)
        if not match:
            raise Refusal('invalid input line %d' % number)
        words.append(int(match[1], 16))
    if not words or len(set(words)) != len(words):
        raise Refusal('input must contain distinct words and must not be empty')
    return words


def parse_disassembly(text, words):
    """Accept LLVM's word or little-endian byte display; account for every line."""
    rows = []
    section_seen = False
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        if not section_seen and re.fullmatch(r'.+:\s+file format mach-o arm64', stripped):
            continue
        if stripped == 'Disassembly of section __TEXT,__text:' and not section_seen:
            section_seen = True
            continue
        if section_seen and re.fullmatch(r'[0-9a-fA-F]+ <[^<>]+>:', stripped):
            continue
        match = re.fullmatch(
            r'\s*([0-9a-fA-F]+):\s+([0-9a-fA-F]{8}|[0-9a-fA-F]{2}(?:\s+[0-9a-fA-F]{2}){3})\s+(<unknown>|[a-zA-Z][a-zA-Z0-9_.]*)(?:\s+(.*?))?\s*', line)
        if not section_seen or not match:
            raise Refusal('unparsed disassembly line %d' % number)
        address = int(match[1], 16)
        raw = match[2].split()
        word = int(raw[0], 16) if len(raw) == 1 else int.from_bytes(bytes(int(b, 16) for b in raw), 'little')
        index = len(rows)
        if index >= len(words) or address != index * 4 or word != words[index]:
            raise Refusal('disassembly address/word mismatch at row %d' % (index + 1))
        operands = (match[4] or '').replace('\t', ' ')
        rows.append((address, word, match[3], operands))
    if len(rows) != len(words):
        raise Refusal('disassembly count mismatch: expected %d, got %d' % (len(words), len(rows)))
    return rows


def run_tool(argv):
    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    if result.returncode:
        raise Refusal('%s failed (exit %d): %s' % (Path(argv[0]).name, result.returncode,
                                                ' '.join(result.stderr.splitlines())))
    return result.stdout


def locate(name, override):
    if override:
        return override
    if sys.platform == 'darwin':
        path = run_tool(['xcrun', '--find', name]).strip()
    else:
        path = shutil.which(name)
    if not path:
        raise Refusal('tool not found: ' + name)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path, help='directory for generated.tsv and tools.txt')
    parser.add_argument('--clang')
    parser.add_argument('--objdump')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args(argv)
    try:
        words = read_words(args.input.read_text(encoding='ascii'))
        outputs = [args.out / name for name in ('generated.tsv', 'tools.txt')]
        if not args.overwrite and any(path.exists() for path in outputs):
            raise Refusal('refusing existing output; use --overwrite')
        clang, objdump = locate('clang', args.clang), locate('llvm-objdump', args.objdump)
        versions = 'clang\n' + run_tool([clang, '--version']) + '\nllvm-objdump\n' + run_tool([objdump, '--version'])
        args.out.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='assembly-', dir=args.out) as directory:
            source, obj = Path(directory) / 'words.s', Path(directory) / 'words.o'
            source.write_text('.text\n' + ''.join('.inst 0x%08x\n' % word for word in words), encoding='ascii')
            run_tool([clang, '-target', 'arm64-apple-macos', '-c', str(source), '-o', str(obj)])
            text = run_tool([objdump, '--disassemble', '--disassemble-zeroes', str(obj)])
            rows = parse_disassembly(text, words)
        outputs[0].write_text('# address\tword\tmnemonic\toperands\n' + ''.join(
            '0x%08x\t%08x\t%s\t%s\n' % row for row in rows), encoding='utf-8')
        outputs[1].write_text(versions, encoding='utf-8')
    except Exception as error:
        print('arm64-oracle-generate: ' + ' '.join(str(error).splitlines()), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
