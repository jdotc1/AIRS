#!/usr/bin/env python3
"""Preflight exact public text/assets; execute only with separate explicit authority."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from publication_gate import GateError, check_files, check_git, git, validate_plan, file_identity


def require_remote_head(root, branch, expected):
    ref = 'refs/heads/' + branch
    process = subprocess.run(['git', '-C', str(root), 'ls-remote', '--exit-code', 'origin', ref], capture_output=True, text=True)
    if process.returncode != 0 or process.stdout.strip() != expected + '\t' + ref:
        raise GateError('Remote PR head differs from inspected source or lookup failed')


def require_new_remote_tag(root, tag):
    ref = 'refs/tags/' + tag
    local = subprocess.run(['git', '-C', str(root), 'show-ref', '--verify', '--quiet', ref])
    if local.returncode != 1: raise GateError('Release tag must be new')
    remote = subprocess.run(['git', '-C', str(root), 'ls-remote', '--exit-code', 'origin', ref], capture_output=True)
    if remote.returncode != 2: raise GateError('Release tag exists or absence could not be established')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--execute', action='store_true', help='Requires authorization for this specific publication')
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text()); validate_plan(plan)
    root = Path(__file__).resolve().parent.parent
    if git(root, 'status', '--porcelain').strip(): raise GateError('Commit intended work before publication')
    destination = git(root, 'remote', 'get-url', 'origin').decode().strip()
    if destination not in {'https://github.com/jdotc1/AIRS.git', 'https://github.com/jdotc1/AIRS', 'git@github.com:jdotc1/AIRS.git'}:
        raise GateError('Unexpected repository destination')
    common = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir').decode().strip())
    if plan['action'] == 'push' and args.receipt.resolve() != (common / 'airs-publication-receipt.json').resolve():
        raise GateError('Push preflight must share the installed hook receipt to avoid duplicate inspection')
    result = check_git(root, plan['base'], plan['head'], args.receipt)
    identities = {p: file_identity(Path(p)) for p in plan['text'] + plan['assets']}
    check_files(plan['text'] + plan['assets'], args.receipt)
    metadata = plan.get('public_metadata', {})
    if not args.execute:
        print('Declared source, public text and assets passed preflight. No publication performed.'); return
    login = subprocess.check_output(['gh', 'api', 'user', '--jq', '.login']).decode().strip()
    if login != 'jdotc1': raise GateError('Unexpected authenticated account')
    if plan['action'] == 'release':
        if set(metadata) != {'tag', 'title'} or len(plan['text']) != 1: raise GateError('Release requires tag/title and one exact notes file')
        if not all(isinstance(v, str) and v and not v.startswith('-') for v in metadata.values()): raise GateError('Invalid release metadata')
        require_new_remote_tag(root, metadata['tag'])
        command = ['gh', 'release', 'create', metadata['tag'], '--repo', plan['repository'], '--target', result['head'],
                   '--title', metadata['title'], '--notes-file', plan['text'][0], '--', *plan['assets']]
    elif plan['action'] == 'pull_request':
        if set(metadata) != {'base_branch', 'head_branch', 'title'} or len(plan['text']) != 1 or plan['assets']:
            raise GateError('PR requires exact branch/title metadata and one body file; no loose attachments')
        if git(root, 'rev-parse', '--verify', metadata['head_branch']).decode().strip() != result['head']:
            raise GateError('PR head differs from inspected source')
        require_remote_head(root, metadata['head_branch'], result['head'])
        command = ['gh', 'pr', 'create', '--repo', plan['repository'], '--base', metadata['base_branch'],
                   '--head', metadata['head_branch'], '--title', metadata['title'], '--body-file', plan['text'][0]]
    else:
        if set(metadata) != {'destination_ref'} or not metadata['destination_ref'].startswith('refs/heads/'):
            raise GateError('Push requires an explicit destination branch ref')
        command = ['git', '-C', str(root), 'push', 'origin', result['head'] + ':' + metadata['destination_ref']]
    if any(Path(p).is_symlink() or file_identity(Path(p)) != identity for p, identity in identities.items()):
        raise GateError('Public input changed after preflight')
    response = subprocess.check_output(command, text=True).strip()
    if plan['action'] == 'push':
        require_remote_head(root, metadata['destination_ref'].removeprefix('refs/heads/'), result['head'])
    elif plan['action'] == 'pull_request':
        record = json.loads(subprocess.check_output(['gh', 'pr', 'view', response, '--repo', plan['repository'], '--json', 'headRefOid,baseRefName,title,body,url'], text=True))
        if record['headRefOid'] != result['head'] or record['baseRefName'] != metadata['base_branch'] or record['title'] != metadata['title'] or record['body'].rstrip() != Path(plan['text'][0]).read_text().rstrip():
            raise GateError('Published PR differs from the inspected plan; preserve evidence and investigate')
    else:
        record = json.loads(subprocess.check_output(['gh', 'release', 'view', metadata['tag'], '--repo', plan['repository'], '--json', 'tagName,name,body,assets'], text=True))
        ref = 'refs/tags/' + metadata['tag']
        remote = subprocess.check_output(['git', '-C', str(root), 'ls-remote', 'origin', ref, ref + '^{}'], text=True).splitlines()
        values = dict(line.split('\t') for line in remote)
        peeled = next((oid for oid, name in values.items() if name == ref + '^{}'), next((oid for oid, name in values.items() if name == ref), None))
        expected_assets = sorted((Path(p).name, Path(p).stat().st_size) for p in plan['assets'])
        actual_assets = sorted((a['name'], a['size']) for a in record['assets'])
        if peeled != result['head'] or record['name'] != metadata['title'] or record['body'].rstrip() != Path(plan['text'][0]).read_text().rstrip() or actual_assets != expected_assets:
            raise GateError('Published release differs from the inspected plan; preserve evidence and investigate')
    if any(Path(p).is_symlink() or file_identity(Path(p)) != identity for p, identity in identities.items()):
        raise GateError('Public input changed during delivery; investigate the actual published payload')
    print('Published destination metadata matches the inspected plan; no runtime or signing qualification is implied.')

if __name__ == '__main__':
    try: main()
    except (GateError, OSError, ValueError, subprocess.CalledProcessError):
        sys.exit('Publication refused; inspect private inputs locally. No matching bytes printed.')
