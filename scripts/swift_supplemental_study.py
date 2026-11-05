#!/usr/bin/env python3
"""One first byte-backed study of the separately authorized owned supplement.

Existing compiler identities are reused without hashes, compilation or indexing.
An exclusive output directory prevents unattended repetition of the study.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
CALLERS = {'supplementNested': 'nested_handlers',
    'supplementConvertConstant': 'local_error_conversion',
    'supplementConvertRecovery': 'local_error_conversion',
    'supplementConvertNegative': 'local_error_conversion'}


def select_plan(index):
    if index.get('role') != 'supplemental_challenge_only':
        raise ValueError('Supplemental index role required')
    plan = []; seen = set()
    for mode, record in sorted(index['modes'].items()):
        if mode not in ('O', 'Onone', 'Osize'):
            raise ValueError('Unknown compiler mode')
        for row in record['calls']:
            if row.get('owned_target_confirmed') is not True or not set(row.get('caller_function_names', [])) & CALLERS.keys():
                continue
            key = (mode, int(row['pc'], 16))
            if key in seen:
                raise ValueError('Duplicate physical study unit')
            seen.add(key); plan.append((mode, row))
            if len(plan) > 18:
                raise ValueError('Authorized first study is limited to eighteen new calls')
    return plan


def run(args):
    spec = importlib.util.spec_from_file_location('supplemental_qualification', ROOT / 'scripts/swift_broad_qualification.py')
    q = importlib.util.module_from_spec(spec); spec.loader.exec_module(q)
    from airs.swift_owned_image import load_owned_swift_image
    from airs.swift_callsite_admission import create_callsite_session, CallsiteLimits
    from airs.swift_outcome_validator_v2 import create_independent_swift_image_ledger
    from swift_fixture_matrix import resolve_run_output

    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=ROOT, text=True)
    if dirty.strip():
        raise ValueError('Commit study and analysis source before first observation')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    capture = args.capture.resolve(strict=True)
    receipt = q.read_bounded_json(capture / 'compile-receipt.json', max_bytes=1024*1024)
    index = q.read_bounded_json(capture / 'compiler-index.json', max_bytes=1024*1024)
    if receipt.get('role') != 'supplemental_challenge_only' or index.get('state') != 'indexed_supplemental':
        raise ValueError('Complete separately authorized supplemental capture required')
    plan = select_plan(index)
    if not plan:
        raise ValueError('No independently indexed owned calls')
    output = resolve_run_output(args.output_dir, args.run_name)
    if output.exists():
        raise FileExistsError('First study exists; preserve and reuse it, never retry automatically')
    output.mkdir(mode=0o700)
    (output / 'FIRST-STUDY-STARTED.json').write_text(json.dumps({
        'source_revision': revision, 'authorized_maximum': 18, 'selected_units': len(plan),
        'scope': 'first new supplemental calls only; no original corpus repeated'}, indent=2))
    rows = []; contexts = {}; work = q.WorkBudget(); retained = q.RetentionBudget()
    try:
        for mode, indexed in plan:
            if mode not in contexts:
                image = load_owned_swift_image(capture / receipt['modes'][mode]['library'], capture / 'compile-receipt.json', mode)
                session = create_callsite_session(image, limits=CallsiteLimits(max_work=2_000_000))
                ledger = create_independent_swift_image_ledger(image)
                if ledger.status != 'ready':
                    raise ValueError('Independent image ledger refused: ' + str(ledger.reason))
                contexts[mode] = (image, session, ledger)
            image, session, ledger = contexts[mode]
            pc = int(indexed['pc'], 16)
            functions = [f for f in image.functions if f.start <= pc < f.end]
            if len(functions) != 1:
                raise ValueError('Unique indexed caller required')
            function = functions[0]
            admission, declaration, candidate, validation = q.analyze_call(image, function, pc, session=session, image_ledger=ledger)
            identity = dict(slice_sha256=image.slice_sha256, container_sha256=image.container_sha256,
                slice_offset=hex(image.slice_offset), slice_size=hex(image.slice_size),
                architecture=image.architecture, cpu_subtype=image.cpu_subtype, uuid=image.uuid,
                preferred_base=hex(image.preferred_base), slice_index=image.slice_index,
                container_slice_count=image.container_slice_count)
            result = validation or admission
            row = dict(capture='supplemental', mode=mode, call_pc=pc, caller_pc=hex(function.start),
                image_identity=identity, target_pc=indexed['target_pc'], eligible=bool(validation and validation.get('eligible')),
                status=result.get('status'), reason=result.get('reason'), admission=q.public(admission),
                candidate=q.public(candidate), validation=q.public(validation),
                source_callers=[dict(caller=name, case_id=name, source_geometry=CALLERS[name])
                    for name in indexed['caller_function_names'] if name in CALLERS])
            row['required_challenge_dispositions'] = q.required_challenge_dispositions(row)
            rows.append(row)
            print(json.dumps(dict(mode=mode, pc=hex(pc), callers=indexed['caller_function_names'],
                eligible=row['eligible'], reason=row['reason'], diagnostic=(validation or {}).get('unresolved_instruction'))), flush=True)
        q.reconcile_nested_challenges(rows, work, retained)
        inventory = q.challenge_inventory(rows, [], [], capture_role='supplemental', challenges=q.SUPPLEMENTAL_CHALLENGES)
        study = dict(schema='airs.swift-broad-supplemental-study.v1', source_revision=revision,
            role='supplemental_challenge_only', state='observed' if inventory['complete'] else 'INCOMPLETE',
            not_primary_positive_credit=True, not_second_compiler_credit=True,
            supplemental_capture_evidence=dict(used=True, role='supplemental_challenge_only',
                source_sha256=receipt['source_sha256'],
                images={mode: receipt['modes'][mode]['emitted_sha256'] for mode in ('Onone', 'O', 'Osize')}),
            observation_count=len(rows), observations=rows, required_challenge_inventory=inventory,
            nested_reconciliation_work=work.report(),
            reuse='Original first source/image seals and compiler index; no repeat hashes, compiler, disassembler or original-corpus observations')
        q.write_bounded_json(output / 'study.json', study, 4*1024*1024)
        print(json.dumps(dict(state=study['state'], observations=len(rows),
            challenges={k: v['observed'] for k, v in inventory['entries'].items()}, output=str(output / 'study.json'))), flush=True)
        return 0 if inventory['complete'] else 2
    except Exception as error:
        q.write_bounded_json(output / 'FAILURE.json', dict(state='INCOMPLETE', reason=str(error),
            completed_observations=rows, next_action='Preserve first observations; no automatic retry'), 4*1024*1024)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--run-name', required=True)
    parser.add_argument('--execute-first-study', action='store_true')
    args = parser.parse_args(argv)
    if not args.execute_first_study:
        print(json.dumps(dict(state='UNRUN', maximum_new_observations=18))); return 0
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
