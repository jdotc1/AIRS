#!/usr/bin/env python3
"""Run the documented bounded triage example against saved sample JSON only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='New directory for example outputs; existing directories are refused')
    args = parser.parse_args()
    destination = args.output_dir.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    source = ROOT / 'examples/mixed.audit.json'
    saved = json.loads(source.read_text(encoding='utf-8'))
    commands = [
        ['coverage', '--report', str(source), '--minimum-count', '1',
         '--sort', 'reason', '--limit', '4', '--output', str(destination / 'coverage.json')],
        ['summary', '--report', str(source), '--verdict', 'unresolved',
         '--reason', 'unsupported_control_flow', '--name-contains', 'conditional',
         '--sort', 'verdict', '--limit', '1', '--output', str(destination / 'selected-summary.json')],
    ]
    for index, arguments in enumerate(commands, 1):
        completed = subprocess.run([sys.executable, '-I', str(ROOT / 'airs_cli.py'), *arguments],
                                   cwd=ROOT, capture_output=True, text=True, timeout=30)
        (destination / f'command-{index}.stdout.txt').write_text(completed.stdout, encoding='utf-8')
        (destination / f'command-{index}.stderr.txt').write_text(completed.stderr, encoding='utf-8')
        require(completed.returncode == 0, f'Example command {index} failed; inspect retained logs')
    inventory = json.loads((destination / 'coverage.json').read_text(encoding='utf-8'))
    summary = json.loads((destination / 'selected-summary.json').read_text(encoding='utf-8'))
    expected = [finding for finding in saved['findings']
                if finding['verdict'] == 'unresolved'
                and 'unsupported_control_flow' in finding['reason_codes']
                and 'conditional' in (finding['function'].get('name') or '')]
    require(len(expected) == 1, 'Sample no longer contains the documented single finding')
    require(inventory['summary']['function_count'] == summary['summary']['function_count'] == 9,
            'Full function denominators changed')
    require(inventory['summary']['unresolved_count'] == summary['summary']['unresolved_count'] == 4,
            'Full unresolved denominators changed')
    require(len(inventory['reasons']) == 4 and
            inventory['reason_frequency_selection']['omitted_count'] == 0,
            'Expected four unresolved reason rows without frequency omissions')
    require(any(row['reason'] == 'unsupported_control_flow' and row['count'] == 1
                for row in inventory['reasons']), 'Chosen reason missing from inventory')
    require([finding['id'] for finding in summary['findings']] == [expected[0]['id']],
            'Selected detail no longer points to the original saved finding')
    require(summary['finding_name_selection']['selected_count'] == 1 and
            summary['finding_limit']['returned_count'] == 1,
            'Selected detail stage counts changed')
    receipt = {'status': 'passed', 'scope': 'saved sample triage composition only',
               'commands_completed': 2, 'full_function_count': 9, 'full_unresolved_count': 4,
               'inventory_reason_rows': 4, 'selected_finding_ids': [expected[0]['id']],
               'image_reaudited': False, 'saved_identity_reverified': False}
    (destination / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
