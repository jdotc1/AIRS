"""New mock-only first-capture tests; no compiler or existing capture is run."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('supplemental_capture',Path(__file__).resolve().parents[1]/'scripts/swift_supplemental_capture.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
FIXTURE=Path(__file__).resolve().parents[1]/'fixtures/swift-error-flow/broad-supplemental'


class SupplementalCaptureTests(unittest.TestCase):
    def args(self,root):
        version=root/'existing-version.txt';version.write_text('Apple Swift version 6.4.2 (existing synthetic receipt)\n')
        return SimpleNamespace(source=FIXTURE/'SupplementalOwnedChallenges.swift',manifest=FIXTURE/'manifest.json',
            output_dir=root,run_name='authored-first',module=s.MODULE,target='arm64-apple-macosx14.0',
            swiftc=Path('/tools/swiftc'),nm=Path('/tools/nm'),objdump=Path('/tools/llvm-objdump'),
            sdk=Path('/sdk'),version_receipt=version)

    def tools(self,args):
        symbols=s.expected_symbols();primary=next(k for k,v in symbols.items() if v=='supplementPrimary')
        nested=next(k for k,v in symbols.items() if v=='supplementNested')
        def run(command,output,deadline,root,limit):
            self.assertEqual(limit,16*1024*1024)
            if command[0]==str(args.swiftc):
                Path(command[command.index('-o')+1]).write_bytes(b'new authored library');output.write_text('mock compile only\n')
            elif command[0]==str(args.objdump):
                output.write_text(f'0000000000001000 <_{nested}>:\n 1000: 94000040 bl 0x1100 <_{primary}>\n')
            else:output.write_text(f'0000000000001000 T _{nested}\n0000000000001100 T _{primary}\n')
        return run

    def test_new_mock_capture_shares_bounds_and_seals_source_and_each_image_once(self):
        with tempfile.TemporaryDirectory() as directory:
            args=self.args(Path(directory));sealed=[];deadlines=[]
            run=self.tools(args)
            def bounded(command,output,deadline,root,limit):deadlines.append(deadline);return run(command,output,deadline,root,limit)
            def seal(path):
                sealed.append(path.name);st=path.stat();custody=dict(dev=st.st_dev,ino=st.st_ino,size=st.st_size,mtime_ns=st.st_mtime_ns,ctime_ns=st.st_ctime_ns)
                return dict(library=path.name,library_path=str(path.resolve()),bytes=st.st_size,
                    emitted_sha256='a'*64,custody_before=custody,custody_after=custody)
            with patch.object(s.matrix,'run_bounded',side_effect=bounded),patch.object(s.matrix,'capture_library_identity',side_effect=seal):
                result=s.capture(args)
            root=Path(result['output_directory']);receipt=json.loads((root/'compile-receipt.json').read_text())
            self.assertEqual(len(deadlines),9);self.assertEqual(len(set(deadlines)),1)
            self.assertEqual(sealed,['SupplementalOwnedChallenges.swift']+[s.MODULE+'-'+m+'.dylib' for m in s.MODES])
            self.assertEqual(receipt['schema'],'airs.owned-swift-broad-compile.v2');self.assertEqual(receipt['state'],'indexed')
            self.assertEqual(receipt['source_sha256'],'a'*64);self.assertEqual(receipt['role'],'supplemental_challenge_only')
            self.assertEqual(result['study_observations_executed'],0);self.assertEqual(result['confirmed_calls'],3)
            self.assertFalse((root/'SupplementalOwnedChallenges.swift').stat().st_mode&0o222)

    def test_existing_child_and_unsafe_run_name_refuse_before_any_seal_or_process(self):
        with tempfile.TemporaryDirectory() as directory:
            args=self.args(Path(directory));(args.output_dir/args.run_name).mkdir()
            with patch.object(s.matrix,'run_bounded') as run,patch.object(s.matrix,'capture_library_identity') as seal:
                with self.assertRaises(FileExistsError):s.capture(args)
                run.assert_not_called();seal.assert_not_called()
            for name in ('../escape','two/parts','.','unsafe\nname'):
                args.run_name=name
                with self.assertRaises(ValueError):s.destination(args)

    def test_mock_bound_failure_preserves_partial_destination_and_never_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            args=self.args(Path(directory))
            with patch.object(s.matrix,'capture_library_identity',return_value={'emitted_sha256':'b'*64}), \
                 patch.object(s.matrix,'run_bounded',side_effect=RuntimeError('authored bound refusal')) as run:
                with self.assertRaisesRegex(RuntimeError,'bound refusal'):s.capture(args)
                self.assertEqual(run.call_count,1)
            root=args.output_dir/args.run_name
            receipt=json.loads((root/'compile-receipt.json').read_text())
            self.assertEqual(receipt['state'],'failed_partial_no_retry');self.assertTrue((root/'SupplementalOwnedChallenges.swift').exists())

    def test_independent_raw_index_deduplicates_pc_and_requires_exact_signature_alias(self):
        symbols=s.expected_symbols();primary=next(k for k,v in symbols.items() if v=='supplementPrimary')
        nested=next(k for k,v in symbols.items() if v=='supplementNested')
        text=f'1000 <_{nested}>:\n1000: 94000040 bl 0x9999 <wrong_annotation>\n1000: 94000040 bl 0x1100\n'
        nm=f'1000 T _{nested}\n1100 T _{primary}\n1100 T _unrelated_alias\n'
        index=s.independent_index(text,nm)
        self.assertEqual(len(index['calls']),1);row=index['calls'][0]
        self.assertEqual(row['target_pc'],'0x1100');self.assertTrue(row['owned_target_confirmed'])
        self.assertEqual(row['owned_target_function_names'],['supplementPrimary']);self.assertFalse(row['abi_proven'])
        # A source-like substring/suffix cannot fabricate the fixed function ABI spelling.
        bad=s.independent_index(text,nm.replace(primary,primary+'FAKE'))
        self.assertEqual(bad['confirmed_owned_target_call_count'],0)

    def test_plan_is_unrun_and_has_three_modes_without_reading_inputs_or_querying_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            argv=['--source','missing.swift','--manifest','missing.json','--output-dir',directory,'--run-name','new-plan',
                '--swiftc','/tools/swiftc','--nm','/tools/nm','--objdump','/tools/objdump','--sdk','/sdk',
                '--version-receipt','/receipts/existing.txt','--module',s.MODULE,'--target','arm64-apple-macosx14.0']
            with patch.object(s,'validate_inputs') as read,patch.object(s.matrix,'run_bounded') as run,contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(s.main(argv),0)
            result=json.loads(output.getvalue());self.assertEqual(result['state'],'UNRUN');self.assertEqual(set(result['commands']),set(s.MODES))
            self.assertFalse((Path(directory)/'new-plan').exists());read.assert_not_called();run.assert_not_called()

    def test_owned_fixture_has_six_declared_functions_and_nested_success_cannot_share_normal_ret(self):
        with tempfile.TemporaryDirectory() as directory:
            args=self.args(Path(directory));source,manifest,version=s.validate_inputs(args)
        self.assertEqual(len(manifest['functions']),6);self.assertEqual(manifest['source_path'],'SupplementalOwnedChallenges.swift')
        self.assertIn(b'_ = try supplementPrimary(n)\n        fatalError("owned supplemental primary success")',source)
        self.assertNotIn(b'/Users/',source);self.assertIsNone(manifest['source_sha256'])

    def test_extra_raw_symbol_prefix_cannot_confirm_fixed_source_signature(self):
        expected=s.expected_symbols();primary=next(k for k,v in expected.items() if v=='supplementPrimary')
        nested=next(k for k,v in expected.items() if v=='supplementNested')
        text=f'1000 <_{nested}>:\n1000: 94000040 bl 0x1100\n'
        nm=f'1000 T _{nested}\n1100 T __{primary}\n'
        result=s.independent_index(text,nm)
        self.assertEqual(result['confirmed_owned_target_call_count'],0)
        self.assertEqual(result['calls'][0]['target_symbols_nm'],['__'+primary])

    def test_index_limits_refuse_before_raw_call_parser_allocates_rows(self):
        with patch.object(s.matrix,'parse_disassembly') as parse:
            with self.assertRaisesRegex(ValueError,'line/count'):
                s.independent_index('x\n'*16385,'')
            parse.assert_not_called()
