#!/usr/bin/env python3
"""Stage tracked AIRS source and selected advanced-Swift evidence locally."""
import argparse
from pathlib import Path
import subprocess
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', type=Path, required=True)
parser.add_argument('--name', default='AIRS-Advanced-Swift-Handback.zip')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
if Path(args.name).name != args.name:
    parser.error('Name must be a filename')
output = (args.output_dir / args.name).resolve()
if output.exists():
    parser.error('Refusing to replace an existing handback')
paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).split(b'\0')
selected = [root / value.decode() for value in paths if value]
evidence = root / 'local-evidence/advanced-swift-error-flow'
for name in ('disassembly-O.txt', 'disassembly-O0.txt', 'qualification.json',
             'CHECKS.md', 'REVIEW_ROUND_1.md', 'REVIEW_ROUND_2.md', 'MANIFEST.json'):
    path = evidence / name
    if path.is_file():
        selected.append(path)
for pattern in ('*tests*.log', 'integration*.log', 'cli-regression.log'):
    selected.extend(evidence.glob(pattern))
if len(selected) > 20000 or sum(p.stat().st_size for p in selected) > 256 * 1024 * 1024:
    parser.error('Handback exceeds bounded source budget')
output.parent.mkdir(parents=True, exist_ok=True)
try:
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(selected)):
            if path.is_symlink():
                continue
            archive.write(path, 'AIRS/' + str(path.relative_to(root)))
except BaseException:
    output.unlink(missing_ok=True)
    raise
print(output)
