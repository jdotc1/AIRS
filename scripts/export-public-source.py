#!/usr/bin/env python3
"""Export a committed public source snapshot after changed-boundary preflight."""
import argparse
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile
from publication_gate import GateError, check_git, safe_name, MAXIMUM_BYTES, MAXIMUM_ENTRIES


def export(root, base, head, output, receipt=None):
    root, output = Path(root), Path(output)
    if output.exists() or output.is_symlink():
        raise GateError('Export destination must be new')
    result = check_git(root, base, head, receipt)
    # git archive reads committed objects only, never local stores or loose files.
    output.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(['git', '-C', str(root), 'archive', '--format=tar', result['head']], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        with tarfile.open(fileobj=process.stdout, mode='r|') as source, zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as destination:
            count = total = 0
            for member in source:
                count += 1; total += member.size
                if count > MAXIMUM_ENTRIES or total > MAXIMUM_BYTES: raise GateError('Source export exceeds bounds')
                safe_name(member.name)
                parts = Path(member.name).parts
                if any(p in {'.git', '.env', 'local-evidence', '.build', '__pycache__'} for p in parts) or member.name.endswith(('.pyc', '.p12', '.p8')):
                    raise GateError('Unshippable source export member')
                if member.isdir(): continue
                if not member.isfile(): raise GateError('Source export links/special files require separate qualification')
                data = source.extractfile(member).read()
                entry = zipfile.ZipInfo('AIRS-source/' + member.name)
                entry.external_attr = (member.mode & 0o777) << 16
                destination.writestr(entry, data)
        if process.wait() != 0: raise GateError('Source archive command failed')
    except BaseException:
        process.kill(); process.wait()
        if output.exists(): output.unlink()
        raise
    finally:
        process.stdout.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--accepted-base', required=True, help='Exact accepted source commit; not an unchecked baseline')
    parser.add_argument('--head', default='HEAD'); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    export(args.root, args.accepted_base, args.head, args.output, args.receipt)
    print('Committed source snapshot exported; app qualification and publication remain separate.')

if __name__ == '__main__':
    try: main()
    except (GateError, OSError, subprocess.CalledProcessError):
        sys.exit('Source export refused; private details withheld.')
