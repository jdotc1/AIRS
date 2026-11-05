#!/usr/bin/env python3
"""Bounded first capture of the fixed owned supplemental Swift challenge source.

Planning is the default. Execution needs --execute-first-capture and separate
explicit authority. No engine imports, discovery, version queries or retries.
"""
from __future__ import annotations
import argparse
import bisect
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import time

MATRIX_PATH=Path(__file__).with_name('swift_fixture_matrix.py')
spec=importlib.util.spec_from_file_location('supplemental_fixture_matrix',MATRIX_PATH)
matrix=importlib.util.module_from_spec(spec);spec.loader.exec_module(matrix)
MODES=('Onone','O','Osize')
MAX_BYTES=16*1024*1024
MAX_SECONDS=60
MODULE='SupplementalOwnedChallenges'
FUNCTIONS=('supplementPrimary','supplementRecovery','supplementNested',
    'supplementConvertConstant','supplementConvertRecovery','supplementConvertNegative')


def read_small(path,limit=65536):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size>limit:raise ValueError('Bounded regular input required')
        data=stream.read(limit+1);after=os.fstat(stream.fileno())
        keys=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_mode')
        if len(data)>limit or any(getattr(before,k)!=getattr(after,k) for k in keys):raise ValueError('Input changed during read')
        return data


def destination(args):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}',args.run_name) or '..' in args.run_name:
        raise ValueError('Safe single-component run name required')
    return matrix.resolve_run_output(args.output_dir,args.run_name)


def expected_symbols(module=MODULE):
    return {'$s'+str(len(module))+module+str(len(name))+name+'yS2iKF':name for name in FUNCTIONS}


def swift_spelling(name):
    # One Mach-O C prefix is conventional; additional underscores are a
    # different raw symbol and cannot mint an exact source-signature match.
    return name[1:] if name.startswith('_$s') else name


def bounded_lines(text,maximum):
    if len(text.encode('utf-8'))>MAX_BYTES:raise ValueError('Index text byte limit')
    lines=text.splitlines()
    if len(lines)>maximum or any(len(line)>4096 for line in lines):raise ValueError('Index line/count limit')
    return lines


def independent_index(disassembly,nm_text,*,module=MODULE,deadline=None):
    symbols={};text_symbols={}
    bounded_lines(disassembly,16384)
    for line in bounded_lines(nm_text,8192):
        if deadline is not None:matrix.check_deadline(deadline)
        match=re.fullmatch(r'\s*([0-9a-fA-F]+)\s+([A-Za-z])\s+(\S+)\s*',line)
        if not match:continue
        address,kind,name=match.groups();pc=int(address,16)
        if kind in ('T','t'):
            text_symbols.setdefault(pc,[]).append(name)
            symbols.setdefault(hex(pc),[]).append(name)
    expected=expected_symbols(module);starts=sorted(text_symbols);rows=[];seen=set()
    for row in matrix.parse_disassembly(disassembly,deadline=deadline):
        if row['pc'] in seen:continue
        seen.add(row['pc']);position=bisect.bisect_right(starts,int(row['pc'],16))-1
        aliases=text_symbols[starts[position]] if position>=0 else []
        callers=sorted({expected[swift_spelling(n)] for n in aliases if swift_spelling(n) in expected})
        if not callers:continue
        targets=symbols.get(row['target_pc'],[])
        owned=sorted({expected[swift_spelling(n)] for n in targets if swift_spelling(n) in expected})
        row.update(caller_aliases_nm=sorted(aliases),caller_function_names=callers,
            target_symbols_nm=sorted(targets),owned_target_function_names=owned,
            owned_target_confirmed=bool(owned) and row['call_kind']=='direct',
            source_call_candidate=bool(owned) or row['call_kind']=='indirect',
            evidence_scope='raw_call_word_plus_exact_nm_module_function_signature_only',
            abi_proven=False,cfg_proven=False,runtime_execution_proven=False)
        rows.append(row)
        if len(rows)>4096:raise ValueError('Supplemental call index bound exceeded')
    return dict(calls=rows,confirmed_owned_target_call_count=sum(r['owned_target_confirmed'] for r in rows),
        function_symbol_matches={name:sorted(hex(pc) for pc,names in text_symbols.items()
            if any(expected.get(swift_spelling(n))==name for n in names)) for name in FUNCTIONS})


def check_bounds(root,deadline):
    matrix.check_deadline(deadline);size=0;count=0
    for path in root.rglob('*'):
        count+=1
        if count>4096 or path.is_symlink():raise RuntimeError('Supplemental entry/symlink bound exceeded')
        if path.is_file():size+=path.stat().st_size
    if size>MAX_BYTES:raise RuntimeError('Combined supplemental byte bound exceeded; preserve partial output')
    return size


def write_json(path,value,root,deadline):
    data=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    if check_bounds(root,deadline)+len(data)>MAX_BYTES:raise RuntimeError('Receipt exceeds remaining combined byte budget')
    temporary=path.with_name(path.name+'.partial')
    with temporary.open('xb') as stream:stream.write(data)
    temporary.replace(path);check_bounds(root,deadline)


def validate_inputs(args):
    if args.module!=MODULE or args.target!='arm64-apple-macosx14.0':raise ValueError('Fixed supplemental module/target required')
    for value in (args.swiftc,args.nm,args.objdump,args.sdk,args.version_receipt):
        if not value.is_absolute():raise ValueError('Explicit absolute tool/SDK/version-receipt paths required')
    manifest=json.loads(read_small(args.manifest))
    if (manifest.get('module')!=MODULE or manifest.get('role')!='supplemental_challenge_only'
            or tuple(x.get('name') for x in manifest.get('functions',[]))!=FUNCTIONS):
        raise ValueError('Fixed six-function supplemental manifest required')
    source=read_small(args.source)
    # The source is checked only as the fixed owned input, never as emitted proof.
    names=tuple(re.findall(rb'@inline\(never\) public func ([A-Za-z]+)\(_ n: Int\) throws -> Int',source))
    if tuple(n.decode() for n in names)!=FUNCTIONS:raise ValueError('Fixed source declarations do not match manifest')
    version=read_small(args.version_receipt).decode('utf-8')
    if not re.search(r'Swift version 6\.',version):raise ValueError('Existing Swift 6 version receipt required')
    return source,manifest,version


def compile_plan(args,root,source_name):
    return {mode:[str(args.swiftc),'-swift-version','6','-target',args.target,'-sdk',str(args.sdk),
        '-emit-library','-module-name',args.module,'-enable-library-evolution','-module-cache-path',str(root/'module-cache'),
        '-'+mode,str(root/source_name),'-o',str(root/(args.module+'-'+mode+'.dylib'))] for mode in MODES}


def capture(args):
    root=destination(args)
    if root.exists():raise FileExistsError('Supplemental destination exists; no automatic repeats')
    source,manifest,version=validate_inputs(args)
    # Exclusive creation is the first mutation. A partial destination cannot resume.
    root.mkdir(mode=0o700);root=root.resolve(strict=True)
    deadline=time.monotonic()+MAX_SECONDS
    receipt=dict(schema='airs.owned-swift-broad-compile.v2',state='in_progress',
        role='supplemental_challenge_only',output_directory=str(root),module=args.module,
        swiftc=str(args.swiftc),sdk=str(args.sdk),target=args.target,toolchain=version,
        version_evidence_reuse=str(args.version_receipt),budget_seconds=MAX_SECONDS,budget_bytes=MAX_BYTES,modes={})
    try:
        captured=root/'SupplementalOwnedChallenges.swift'
        with captured.open('xb') as stream:stream.write(source)
        captured.chmod(0o444)
        (root/'source-manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
        (root/'swift-version-reused.log').write_text(version)
        check_bounds(root,deadline)
        source_identity=matrix.capture_library_identity(captured)
        receipt.update(source_sha256=source_identity['emitted_sha256'],source_identity=source_identity,
            source_file=captured.name,source_bytes=len(source))
        write_json(root/'compile-receipt.json',receipt,root,deadline)
        commands=compile_plan(args,root,captured.name)
        index=dict(schema='airs.owned-swift-supplemental-compiler-index.v1',state='incomplete',
            role='supplemental_challenge_only',independence='retained LLVM raw words plus exact nm aliases; no AIRS imports',modes={})
        for mode in MODES:
            matrix.run_bounded(commands[mode],root/f'compile-{mode}.log',deadline,root,limit=MAX_BYTES)
            library=root/(args.module+'-'+mode+'.dylib');check_bounds(root,deadline)
            receipt['modes'][mode]=dict(command=commands[mode],**matrix.capture_library_identity(library))
            write_json(root/'compile-receipt.json',receipt,root,deadline)
            dump=root/f'objdump-{mode}.txt';nm=root/f'nm-{mode}.txt'
            matrix.run_bounded([str(args.objdump),'--disassemble','--print-imm-hex',str(library)],dump,deadline,root,limit=MAX_BYTES)
            matrix.run_bounded([str(args.nm),'-n',str(library)],nm,deadline,root,limit=MAX_BYTES)
            check_bounds(root,deadline)
            index['modes'][mode]=independent_index(read_small(dump,MAX_BYTES).decode(),read_small(nm,MAX_BYTES).decode(),
                module=args.module,deadline=deadline)
            write_json(root/'compiler-index.json',index,root,deadline)
        receipt['state']='indexed';index['state']='indexed_supplemental'
        index['confirmed_owned_target_call_count']=sum(v['confirmed_owned_target_call_count'] for v in index['modes'].values())
        index['compile_receipt']='compile-receipt.json';index['study_observations_executed']=0
        index['future_first_study_limit']=18
        write_json(root/'compile-receipt.json',receipt,root,deadline)
        write_json(root/'compiler-index.json',index,root,deadline)
        return dict(state='indexed_supplemental',output_directory=str(root),role='supplemental_challenge_only',
            confirmed_calls=index['confirmed_owned_target_call_count'],study_observations_executed=0)
    except Exception as error:
        receipt.update(state='failed_partial_no_retry',failure=dict(type=type(error).__name__,reason=str(error)))
        try:write_json(root/'compile-receipt.json',receipt,root,deadline)
        except Exception:pass  # Original in-progress receipt/partial output survive.
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ('source','manifest','output-dir','swiftc','nm','objdump','sdk','version-receipt'):
        parser.add_argument('--'+flag,type=Path,required=True)
    parser.add_argument('--run-name',required=True)
    parser.add_argument('--module',required=True);parser.add_argument('--target',required=True)
    parser.add_argument('--execute-first-capture',action='store_true')
    args=parser.parse_args(argv)
    if not args.execute_first_capture:
        root=destination(args)
        print(json.dumps(dict(state='UNRUN',role='supplemental_challenge_only',destination=str(root),
            commands=compile_plan(args,root,'SupplementalOwnedChallenges.swift'),budget_seconds=MAX_SECONDS,budget_bytes=MAX_BYTES),indent=2))
        return 0
    print(json.dumps(capture(args),indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
