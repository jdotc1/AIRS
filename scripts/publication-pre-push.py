#!/usr/bin/env python3
"""Git pre-push adapter: inspect outgoing content against a recorded accepted baseline."""
import json
from pathlib import Path
import subprocess
import sys
from publication_gate import GateError, check_git, inspect_bytes


def main():
    root = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel']).decode().strip())
    baseline = subprocess.check_output(['git', 'config', '--get', 'airs.publicationBaseline']).decode().strip()
    if len(baseline) != 40: raise GateError('Configure an exact accepted baseline first')
    origin = subprocess.check_output(['git', 'remote', 'get-url', sys.argv[1]]).decode().strip()
    allowed = {'https://github.com/jdotc1/AIRS.git', 'https://github.com/jdotc1/AIRS', 'git@github.com:jdotc1/AIRS.git'}
    if origin not in allowed or len(sys.argv) < 3 or sys.argv[2] not in allowed:
        raise GateError('Unexpected public destination')
    common = Path(subprocess.check_output(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir']).decode().strip())
    receipt = common / 'airs-publication-receipt.json'
    for line in sys.stdin:
        local_ref, local_oid, remote_ref, remote_oid = line.split()
        inspect_bytes((local_ref + remote_ref).encode(), 'outgoing ref')
        if local_oid == '0' * 40: continue
        check_git(root, baseline, local_oid, receipt)
    print('Outgoing source gate passed; public text/assets require the publication-plan gate.')

if __name__ == '__main__':
    try: main()
    except (GateError, OSError, ValueError, subprocess.CalledProcessError):
        sys.exit('Public push blocked by sanitization gate; review private inputs locally.')
