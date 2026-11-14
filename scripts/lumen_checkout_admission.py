#!/usr/bin/env python3
"""Admit the resolved public Lumen checkout without granting it live authority."""
import json
import pathlib
import subprocess
import sys

REVISION = '3ffac7a51e8cf7a0d61a3cfc6289c927a535ce61'


def check_checkout(checkout, revision):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(checkout), *args], text=True).strip()
    if git('rev-parse', 'HEAD') != revision or git('status', '--porcelain', '--untracked-files=all'):
        raise ValueError('Lumen checkout differs from the resolved public revision')
    if git('ls-files', '--others', '--ignored', '--exclude-standard', '--',
           'Sources/LumenUI', 'Sources/LumenTokens', 'Package.swift'):
        raise ValueError('Ignored Lumen compiler or resource inputs are not covered by the pinned revision')


def main(lock_path, checkout):
    lock = json.loads(pathlib.Path(lock_path).read_text())
    pins = [p for p in lock['pins'] if p.get('identity') == 'lumen']
    if (len(pins) != 1 or pins[0].get('location') != 'https://github.com/jdotc1/Lumen.git'
            or pins[0].get('state') != {'version': '1.3.0', 'revision': REVISION}):
        raise ValueError('Lumen pin is not the admitted public 1.3.0 revision')
    check_checkout(checkout, REVISION)


if __name__ == '__main__':
    try:
        main(sys.argv[1], sys.argv[2])
    except (IndexError, KeyError, OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
