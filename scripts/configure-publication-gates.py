#!/usr/bin/env python3
"""Install the local source gate without overwriting an existing hook."""
import argparse
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--accepted-base', required=True)
    parser.add_argument('--evidence', required=True, help='Local record identifying the accepted baseline')
    args = parser.parse_args()
    if len(args.accepted_base) != 40 or any(c not in '0123456789abcdef' for c in args.accepted_base):
        parser.error('An exact accepted commit ID is required')
    subprocess.run(['git', 'cat-file', '-e', args.accepted_base + '^{commit}'], check=True)
    configured = subprocess.run(['git', 'config', '--get', 'core.hooksPath'], capture_output=True, text=True)
    if configured.returncode == 0: parser.error('Preserve the configured hook directory; integrate manually')
    common = Path(subprocess.check_output(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir']).decode().strip())
    hook = common / 'hooks/pre-push'
    marker = '# AIRS publication source gate'
    content = '''#!/bin/sh
# AIRS publication source gate
set -eu
root=$(git rev-parse --show-toplevel)
exec python3 "$root/scripts/publication-pre-push.py" "$@"
'''
    if hook.exists() and marker not in hook.read_text(): parser.error('Existing pre-push hook retained; integrate manually')
    hook.parent.mkdir(parents=True, exist_ok=True); hook.write_text(content); hook.chmod(0o755)
    subprocess.run(['git', 'config', 'airs.publicationBaseline', args.accepted_base], check=True)
    subprocess.run(['git', 'config', 'airs.publicationEvidence', args.evidence], check=True)
    print('Local pre-push gate installed; public text and assets still require a publication plan.')

if __name__ == '__main__': main()
