"""New synthetic packaging inputs only; never exports or verifies real source."""
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SPEC = importlib.util.spec_from_file_location('broad_packager', Path(__file__).resolve().parents[1] / 'scripts/package_swift_broad_handback.py')
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)


def tar_source(entries):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w') as archive:
        for name, content, kind in entries:
            member = tarfile.TarInfo(name)
            if kind == 'link':
                member.type = tarfile.SYMTYPE; member.linkname = '/outside'
                archive.addfile(member)
            else:
                member.size = len(content); member.mode = 0o755 if name.endswith('.sh') else 0o644
                archive.addfile(member, io.BytesIO(content))
    data.seek(0)
    return tarfile.open(fileobj=data, mode='r|')


class BroadHandbackTests(unittest.TestCase):
    def export(self, entries, **kwargs):
        data = io.BytesIO()
        with tar_source(entries) as source, zipfile.ZipFile(data, 'w') as destination:
            p.add_source_tar(source, destination, **kwargs)
        data.seek(0)
        return zipfile.ZipFile(data)

    def test_complete_source_all_formats_and_root_native_licenses(self):
        names = ['LICENSE', 'README.md', '.gitignore', 'pyproject.toml',
                 'native/App.swift', 'src/airs/main.py', 'tests/fixtures/sample.macho',
                 'tests/fixtures/sample.bin', 'docs/screenshot.png', 'scripts/run.sh']
        entries = [(name, b'owned fixture\x00' if name.endswith(('.macho', '.bin', '.png')) else b'text', 'file') for name in names]
        with self.export(entries, expected_names=set(names)) as archive:
            self.assertEqual(set(archive.namelist()), {'AIRS/source/' + n for n in names})
            self.assertEqual(archive.read('AIRS/source/tests/fixtures/sample.macho'), b'owned fixture\x00')
            self.assertEqual(archive.getinfo('AIRS/source/scripts/run.sh').external_attr >> 16, 0o755)

    def test_omitted_export_ignore_member_refused(self):
        with self.assertRaises(p.PackageError):
            self.export([('LICENSE', b'license', 'file')], expected_names={'LICENSE', 'hidden.bin'})

    def test_traversal_absolute_windows_and_control_names_refused(self):
        for name in ('../escape', '/absolute', 'a/../escape', 'a//b', 'C:/escape', 'a\\b', 'a\nb'):
            with self.subTest(name=name), self.assertRaises(p.PackageError): p.safe_name(name)

    def test_unsafe_links_refused_without_silent_omission(self):
        with self.assertRaises(p.PackageError): self.export([('link', b'', 'link')])

    def test_caches_history_credentials_refused(self):
        for name in ('.git/config', 'local-evidence/secret.json', '.build/a', 'x/.env', 'x/private.p12'):
            with self.subTest(name=name), self.assertRaises(p.PackageError):
                self.export([(name, b'private', 'file')])

    def test_expanded_source_bound(self):
        with self.assertRaises(p.PackageError): self.export([('fixture.bin', b'12345', 'file')], maximum=4)

    def test_duplicate_member_refused(self):
        with self.assertRaises(p.PackageError):
            self.export([('LICENSE', b'a', 'file'), ('LICENSE', b'b', 'file')])

    def test_relocation_preserves_original_digest_and_instruction_evidence(self):
        record = {'source_sha256': 'source-existing', 'emitted_sha256': 'image-existing',
                  'swiftc': '/Applications/Toolchain/usr/bin/swiftc',
                  'command': ['/Applications/Toolchain/usr/bin/swiftc', '-O', '/capture/owned.swift'],
                  'custody_after': {'dev': 123, 'ino': 456}, 'dev': 789,
                  'pc': 0x1000, 'word': 0xd65f03c0, 'counts': {'eligible': 14}}
        view = p.relocated_view(record, [('/Applications/Toolchain', 'toolchains/primary'), ('/capture', 'captures/primary')])
        result = view['record']
        self.assertEqual(result['source_sha256'], 'source-existing')
        self.assertEqual(result['emitted_sha256'], 'image-existing')
        self.assertEqual(result['command'], ['toolchains/primary/usr/bin/swiftc', '-O', 'captures/primary/owned.swift'])
        self.assertNotIn('custody_after', result); self.assertNotIn('dev', result)
        self.assertEqual(result['pc'], 0x1000); self.assertEqual(result['word'], 0xd65f03c0)
        self.assertEqual(result['counts']['eligible'], 14)
        self.assertIn('not a new cryptographic attestation', view['attestation'])

    def test_unknown_private_path_refused_without_printing_bytes(self):
        for text in ('/Users/example/private', '/Applications/Unknown/bin/swiftc', '/tmp/private', '/Library/Developer/SDK'):
            with self.subTest(text=text), self.assertRaises(p.PackageError) as caught:
                p.relocate_text(text, [])
            self.assertNotIn(text, str(caught.exception))

    def test_source_clearance_exact_identity_and_scope(self):
        value = {'accepted_baseline': p.ACCEPTED_BASELINE, 'package_head': 'head', 'state': 'passed',
                 'scope': 'complete_tracked_source_and_new_export_metadata', 'accepted_baseline_reused': True}
        p.check_clearance(value, 'head')
        for key in value:
            changed = dict(value); changed[key] = 'wrong'
            with self.subTest(key=key), self.assertRaises(p.PackageError): p.check_clearance(changed, 'head')

    def test_engine_changes_refused_doc_only_final_commit_allowed(self):
        for changed, allowed in ((b'docs/swift/PACK.md\n', True), (b'src/airs/core.py\n', False),
                                 (b'native/App.swift\n', False), (b'pyproject.toml\n', False)):
            with self.subTest(changed=changed), patch.object(p, 'git', side_effect=[b'head\n', b'qualified\n', changed]):
                if allowed: self.assertEqual(p.validate_identity('.', 'HEAD', 'qualified'), ('head', 'qualified'))
                else:
                    with self.assertRaises(p.PackageError): p.validate_identity('.', 'HEAD', 'qualified')

    def test_exact_git_blob_stream_preserves_attribute_sensitive_formats(self):
        blob = b'owned\x00$Format:%H$'
        class Process:
            def __init__(self): self.stdout = io.BytesIO(blob)
            def wait(self): return 0
            def kill(self): pass
        rows = [('fixture.bin', '100644', 'a' * 40, len(blob))]
        output = io.BytesIO()
        with patch.object(p.subprocess, 'Popen', return_value=Process()) as call:
            with zipfile.ZipFile(output, 'w') as archive:
                p.add_source_tar(p.GitBlobSource('/synthetic', rows), archive, expected_names={'fixture.bin'})
            self.assertEqual(call.call_args.args[0], ['git', '-C', '/synthetic', 'show', 'a' * 40])
        output.seek(0)
        with zipfile.ZipFile(output) as archive: self.assertEqual(archive.read('AIRS/source/fixture.bin'), blob)

    def test_marker_survives_failure_and_forbids_retry(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'local-evidence') as tmp:
            output = Path(tmp) / 'synthetic.zip'; marker = Path(tmp) / 'started.json'
            p.reserve_operation(output, marker, {'package_head': 'synthetic'})
            self.assertFalse(output.exists())
            self.assertEqual(json.loads(marker.read_text())['state'], 'STARTED_NO_AUTOMATIC_RETRY')
            with self.assertRaises(p.PackageError): p.reserve_operation(output, marker, {})

    def test_dangling_output_symlink_refuses(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'local-evidence') as tmp:
            output = Path(tmp) / 'synthetic.zip'; output.symlink_to('missing')
            with self.assertRaises(p.PackageError): p.reserve_operation(output, Path(tmp) / 'marker', {})

    def test_no_execution_without_final_local_switch(self):
        args = p.parser().parse_args(['--primary-capture', 'a', '--second-capture', 'b', '--qualification', 'q', '--ledger', 'l',
                                     '--source-clearance', 'c', '--output', 'o', '--marker', 'm'])
        with patch.object(p, 'read_json', side_effect=AssertionError('must not read evidence')), self.assertRaises(p.PackageError):
            p.build(args)


class PackagerReviewBoundaryTests(unittest.TestCase):
    """New changed-boundary cases; run this class only, reuse original 15."""
    def test_two_thousand_response_prefixes_are_iterative_and_empty_refuses(self):
        prefix = '@' * 2000
        args = ['toolchains/swiftc', prefix + 'captures/primary/args']
        self.assertEqual(p.portable_command(args), args)
        for operand in (prefix, prefix + '/opt/private/args'):
            with self.subTest(operand_length=len(operand)), self.assertRaises(p.PackageError):
                p.portable_command(['toolchains/swiftc', operand])

    def test_response_files_and_plugin_server_operands_require_relative_paths(self):
        for operand in ('@/opt/private/args', '-external-plugin-path=relative/plugin#/scratch/server'):
            with self.subTest(operand=operand), self.assertRaises(p.PackageError):
                p.portable_command(['toolchains/swiftc', operand])
        args = ['toolchains/swiftc', '@captures/primary/args', '-external-plugin-path=plugins#server/bin']
        self.assertEqual(p.portable_command(args), args)

    def test_unenumerated_attached_paths_refuse_and_known_relative_clang_forms_survive(self):
        for operand in ('-iquote/opt/private/include', '-o/abs/output', '-unknown/opt/private', '-unknownC:\\private\\include'):
            with self.subTest(operand=operand), self.assertRaises(p.PackageError):
                p.portable_command(['toolchains/swiftc', '-Xcc', operand])
        args = ['toolchains/swiftc', '-Xcc', '-iquoterelative/include', '-orelative/output']
        self.assertEqual(p.portable_command(args), args)

    def test_relocated_dictionary_key_collisions_refuse_without_second_relocation(self):
        with self.assertRaises(p.PackageError):
            p.bounded_json_bytes({'/capture/file': 1, 'captures/primary/file': 2}, p.EvidenceBudget(limit=10000),
                                 replacements=[('/capture', 'captures/primary')])
        view = p.bounded_json_bytes({'/capture/file': 'existing-digest'}, p.EvidenceBudget(limit=10000),
                                    replacements=[('/capture', 'captures/capture')])
        self.assertEqual(json.loads(view), {'captures/capture/file': 'existing-digest'})

    def test_git_control_queries_stop_at_fixed_output_bound(self):
        process = unittest.mock.Mock(stdout=io.BytesIO(b'x' * 100))
        process.wait.return_value = 0
        with patch.object(p, 'GIT_CONTROL_LIMIT', 8), patch.object(p.subprocess, 'Popen', return_value=process):
            with self.assertRaises(p.PackageError): p.git('/synthetic', 'status')
        process.kill.assert_called_once()

    def test_relocated_json_escape_budget_is_reserved_before_encoder(self):
        with patch.object(p.json.JSONEncoder, 'iterencode', side_effect=AssertionError('must reserve first')):
            with self.assertRaises(p.PackageError):
                p.bounded_json_bytes('/x', p.EvidenceBudget(limit=150), replacements=[('/x', 'r' * 20)])

    def test_shared_budget_refuses_second_read_before_read_allocation(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'local-evidence') as tmp:
            path = Path(tmp) / 'new.txt'; path.write_bytes(b'12345')
            budget = p.EvidenceBudget(limit=10)
            self.assertEqual(p.read_bytes(path, budget=budget), b'12345')
            with self.assertRaises(p.PackageError): p.read_bytes(path, budget=budget)
            self.assertEqual(budget.used, 6)

    def test_serialization_has_incremental_retained_buffer_budget(self):
        budget = p.EvidenceBudget(limit=80)
        with self.assertRaises(p.PackageError):
            p.bounded_json_bytes({'new': ['a'] * 100}, budget)
        self.assertLessEqual(budget.used, 80)

    def test_decode_parse_and_relocation_reserve_before_allocation(self):
        with self.assertRaises(p.PackageError): p.decoded_text(b'12345', p.EvidenceBudget(limit=19))
        with self.assertRaises(p.PackageError): p.relocate_text('/old/file', [('/old', 'new/' * 10)], p.EvidenceBudget(limit=8))
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'local-evidence') as tmp:
            path = Path(tmp) / 'new.json'; path.write_text('{"a": [1,2,3]}')
            with self.assertRaises(p.PackageError): p.read_json(path, budget=p.EvidenceBudget(limit=30))

    def test_source_and_review_counts_capped_before_evidence_reads(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'local-evidence') as tmp:
            for index in range(p.MAX_SWIFT_SOURCES + 1): (Path(tmp) / f'new{index}.swift').touch()
            with self.assertRaises(p.PackageError): p.capture_sources(Path(tmp))
        args = p.parser().parse_args(['--primary-capture', 'a', '--second-capture', 'b', '--qualification', 'q', '--ledger', 'l',
                                     '--source-clearance', 'c', '--output', 'o', '--marker', 'm', '--execute-final-local'] +
                                    sum((['--review', str(index)] for index in range(p.MAX_REVIEWS + 1)), []))
        with patch.object(p, 'read_json', side_effect=AssertionError('must not read')), self.assertRaises(p.PackageError): p.build(args)

    def test_tree_stream_stops_at_entry_row_byte_and_source_limits(self):
        row = b'100644 blob ' + b'a' * 40 + b' 1\tx.bin\0'
        for kwargs in ({'entry_limit': 1}, {'byte_limit': len(row)}, {'source_limit': 1}):
            stream = io.BytesIO(row * 100)
            with self.subTest(kwargs=kwargs), self.assertRaises(p.PackageError): list(p.stream_tree_rows(stream, **kwargs))
            self.assertLess(stream.tell(), len(row) * 3)
        stream = io.BytesIO(b'x' * (p.TREE_ROW_LIMIT + 2))
        with self.assertRaises(p.PackageError): list(p.stream_tree_rows(stream))
        self.assertEqual(stream.tell(), p.TREE_ROW_LIMIT + 1)

    def test_tree_stream_preserves_raw_identity_name_and_size(self):
        row = b'100755 blob ' + b'b' * 40 + b' 17\tnative/new.bin\0'
        self.assertEqual(list(p.stream_tree_rows(io.BytesIO(row))), [('native/new.bin', '100755', 'b' * 40, 17)])

    def test_command_rejects_every_absolute_path_form(self):
        cases = [['/opt/bin/swiftc', '-O'], ['toolchains/swiftc', '/scratch/a.swift'],
                 ['toolchains/swiftc', '-I/opt/include'], ['toolchains/swiftc', '-F/usr/local/Frameworks'],
                 ['toolchains/swiftc', '-L', '/opt/lib'], ['toolchains/swiftc', '-sdk/opt/SDK'],
                 ['toolchains/swiftc', '-sdk=/opt/SDK'], ['toolchains/swiftc', '-module-cache-path=/scratch/cache'],
                 ['toolchains/swiftc', '-Wl,-rpath,/opt/lib'], ['toolchains/swiftc', '-debug-prefix-map', 'relative=/scratch'],
                 ['toolchains/swiftc', '-plugin-path=/opt/plugin'], ['toolchains/swiftc', '-I../escape']]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(p.PackageError): p.portable_command(args)

    def test_command_preserves_relative_operands_public_urls_and_nonpath_flags(self):
        args = ['toolchains/primary/bin/swiftc', '-swift-version', '6', '-target', 'arm64-apple-macosx14.0',
                '-Irelative/include', '-F', 'relative/Frameworks', '-Lrelative/lib', '-sdk', 'sdks/primary',
                '-module-cache-path=cache', '-O', 'captures/primary/a.swift', '-o', 'captures/primary/a.dylib',
                '-reference-url=https://example.org/public']
        self.assertEqual(p.portable_command(args), args)

    def complete_records(self):
        qualification = {'schema': 'airs.swift-broad-qualification.v1', 'state': 'qualified',
                         'gates': {key: True for key in p.MANDATORY_GATES}}
        reviews = [{'scope': 'whole_broad_branch', 'decision': 'passed', 'unresolved_findings': [],
                    'source_revision': 'qualified', 'correction_history': [], 'reviewer': identity}
                   for identity in ('one', 'two')]
        return qualification, {'state': 'ready', 'scope': p.READINESS_SCOPE, 'remaining_work': [],
                               'task_remaining_work': ['stage artifact', 'authorized private delivery']}, [Path('one.json'), Path('two.json')], reviews

    def test_completeness_rejects_missing_schema_gate_and_nonboolean_gate(self):
        qualification, ledger, paths, reviews = self.complete_records()
        self.assertTrue(p.completeness(qualification, ledger, paths, reviews, 'qualified'))
        import copy
        bad_records = [dict(qualification, schema='wrong'), dict(qualification, gates={'arbitrary': True}),
                       dict(qualification, gates={key: 1 for key in p.MANDATORY_GATES})]
        missing = copy.deepcopy(qualification); missing['gates'].pop(next(iter(p.MANDATORY_GATES))); bad_records.append(missing)
        for record in bad_records:
            with self.subTest(record=record): self.assertFalse(p.completeness(record, ledger, paths, reviews, 'qualified'))

    def test_completeness_rejects_duplicate_or_stale_review_records(self):
        qualification, ledger, paths, reviews = self.complete_records()
        self.assertFalse(p.completeness(qualification, ledger, [paths[0], paths[0]], reviews, 'qualified'))
        import copy
        for key, value in [('reviewer', 'one'), ('source_revision', 'stale'), ('decision', 'pending'),
                           ('scope', 'partial'), ('unresolved_findings', ['open']), ('correction_history', None)]:
            changed = copy.deepcopy(reviews); changed[1][key] = value
            with self.subTest(key=key): self.assertFalse(p.completeness(qualification, ledger, paths, changed, 'qualified'))

    def test_strict_json_rejects_duplicate_keys_and_nonfinite_values(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'local-evidence') as tmp:
            path = Path(tmp) / 'new.json'
            for text in ('{"x":1,"x":2}', '{"nested":{"x":1,"x":2}}', '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}', '{"x":1e999}'):
                path.write_text(text)
                with self.subTest(text=text), self.assertRaises(p.PackageError): p.read_json(path, budget=p.EvidenceBudget(limit=10000))
            path.write_text('{"digest":"existing","pc":4096,"ratio":0.5}')
            self.assertEqual(p.read_json(path, budget=p.EvidenceBudget(limit=10000)), {'digest': 'existing', 'pc': 4096, 'ratio': 0.5})


class RoundOnePackagerRepairTests(unittest.TestCase):
    """New R1-04 synthetic metadata only; no real Git/capture/ZIP/hash work."""
    def records(self):
        qualification = {'schema': 'airs.swift-broad-qualification.v1', 'state': 'qualified',
                         'gates': {name: True for name in p.MANDATORY_GATES}}
        ledger = {'scope': p.READINESS_SCOPE, 'state': 'ready', 'remaining_work': [],
                  'task_remaining_work': ['stage the portable artifact', 'approved private cross-device delivery']}
        reviews = [{'reviewer': name, 'scope': 'whole_broad_branch', 'decision': 'passed',
                    'source_revision': 'q' * 40, 'unresolved_findings': [], 'correction_history': []}
                   for name in ('review-one', 'review-two')]
        return qualification, ledger, reviews

    def receipts(self):
        return {name: {'source_sha256': 'a' * 64, 'modes': {
            'O': {'library': 'BroadOwned-O.dylib', 'emitted_sha256': image * 64}}}
            for name, image in (('primary', 'b'), ('second', 'c'))}

    def test_scoped_readiness_does_not_require_future_artifact_or_delivery_completion(self):
        qualification, ledger, reviews = self.records()
        paths = [Path('new-review-one.json'), Path('new-review-two.json')]
        self.assertTrue(p.completeness(qualification, ledger, paths, reviews, 'q' * 40))
        self.assertEqual(len(ledger['task_remaining_work']), 2)
        for key, value in [('scope', 'whole_task'), ('state', 'complete'), ('remaining_work', ['pending analysis']),
                           ('task_remaining_work', None)]:
            changed = dict(ledger); changed[key] = value
            with self.subTest(key=key):
                self.assertFalse(p.completeness(qualification, changed, paths, reviews, 'q' * 40))

    def test_complete_patch_stream_is_bounded_and_preserves_text_and_binary_patch_bytes(self):
        data = b'diff --git a/new.bin b/new.bin\nGIT binary patch\nliteral 2\nLc${Nk00001\n'
        process = unittest.mock.Mock(stdout=io.BytesIO(data)); process.wait.return_value = 0
        with patch.object(p, 'git', return_value=b'') as control, patch.object(p.subprocess, 'Popen', return_value=process) as spawn:
            self.assertEqual(p.git_patch('/synthetic', 'd' * 40, p.EvidenceBudget()), data)
        control.assert_called_once_with('/synthetic', 'merge-base', '--is-ancestor', p.ACCEPTED_BASELINE, 'd' * 40)
        args = spawn.call_args.args[0]
        self.assertIn('--binary', args); self.assertIn('--full-index', args)
        self.assertIn('--no-ext-diff', args); self.assertIn('--no-textconv', args)
        self.assertEqual(args[-3:], [p.ACCEPTED_BASELINE, 'd' * 40, '--'])
        process = unittest.mock.Mock(stdout=io.BytesIO(b'x' * 9)); process.wait.return_value = 0
        with patch.object(p, 'PATCH_LIMIT', 8), patch.object(p, 'git', return_value=b''), patch.object(p.subprocess, 'Popen', return_value=process):
            with self.assertRaises(p.PackageError): p.git_patch('/synthetic', 'd' * 40, p.EvidenceBudget())
        process.kill.assert_called_once()

    def test_commit_inventory_contains_only_ordered_ids_and_sanitized_subjects(self):
        raw = (('1' * 40 + '\0Repair /origin/local/file reviewer@example.org\0\n' +
                '2' * 40 + '\0Document portable scope\0\n').encode())
        with patch.object(p, 'git', return_value=raw) as control:
            result = p.commit_inventory('/synthetic', 'd' * 40, [('/origin/local', 'origin')], p.EvidenceBudget())
        self.assertEqual([record['sha'] for record in result['commits']], ['1' * 40, '2' * 40])
        self.assertEqual(result['commits'][0]['subject'], 'Repair origin/file [redacted email]')
        self.assertEqual(set(result['commits'][0]), {'sha', 'subject'})
        self.assertIn('--format=%H%x00%s%x00', control.call_args.args)
        self.assertNotIn('/origin/local', json.dumps(result)); self.assertNotIn('reviewer@example.org', json.dumps(result))

    def test_scoped_manifest_reuses_existing_digests_without_member_or_zip_coverage(self):
        with patch('hashlib.sha256', side_effect=AssertionError('no hashing')):
            result = p.reused_sha256_manifest(self.receipts(), 'synthetic-handback.zip')
        self.assertEqual([row['sha256'] for row in result['records']], ['a' * 64, 'b' * 64, 'a' * 64, 'c' * 64])
        self.assertTrue(all(row['status'] == 'REUSED_CAPTURED_IDENTITY' for row in result['records']))
        self.assertTrue(all('NOT relocated archive members' in row['covers'] for row in result['records']))
        self.assertEqual(result['final_archive']['status'], 'UNSEALED_BY_PACKAGER')
        self.assertNotIn('sha256', result['final_archive'])
        self.assertIn('no per-member digest coverage', result['coverage'])
        malformed = self.receipts(); malformed['primary']['modes']['O']['library'] = None
        with self.assertRaises(p.PackageError): p.reused_sha256_manifest(malformed, 'synthetic.zip')

    def test_new_handoff_surfaces_have_root_navigation_scope_and_exact_remaining_work(self):
        qualification, ledger, _ = self.records()
        raw = ('1' * 40 + '\0Synthetic change\0\n').encode()
        with patch.object(p, 'git_patch', return_value=b'complete synthetic patch\n'), patch.object(p, 'git', return_value=raw), \
                patch.object(p.zipfile, 'ZipFile', side_effect=AssertionError('no ZIP staging')), \
                patch('hashlib.sha256', side_effect=AssertionError('no hashing')):
            extra = p.handback_surfaces('/synthetic', 'd' * 40, 'q' * 40, 'qualified_source_package_content_ready',
                ledger, qualification, self.receipts(), [], p.EvidenceBudget(), 'synthetic.zip')
        self.assertEqual(set(extra), {'HANDOFF.md', 'AIRS/changes/BASELINE-TO-HEAD.patch',
            'AIRS/changes/COMMITS.json', 'AIRS/evidence/SHA256-MANIFEST.json'})
        self.assertEqual(extra['AIRS/changes/BASELINE-TO-HEAD.patch'], b'complete synthetic patch\n')
        handoff = extra['HANDOFF.md'].decode()
        for path in ('AIRS/source/', 'AIRS/changes/COMMITS.json', 'AIRS/evidence/SHA256-MANIFEST.json'):
            self.assertIn(path, handoff)
        self.assertIn('d' * 40, handoff); self.assertIn('q' * 40, handoff)
        self.assertIn('approved private cross-device delivery', handoff)
        self.assertIn('Whole-task completion is not established', handoff)
        self.assertIn('computes no digest', handoff)
        self.assertNotIn('/synthetic', handoff)

    def test_additional_patch_inventory_handoff_digest_clearance_is_explicit(self):
        p.check_handoff_clearance({'additional_export_surfaces': sorted(p.HANDOFF_SURFACES)})
        for value in (None, [], ['baseline_to_head_patch'], [{}]):
            with self.subTest(value=value), self.assertRaises(p.PackageError):
                p.check_handoff_clearance({'additional_export_surfaces': value})

    def test_incomplete_handoff_preserves_false_gates_and_pending_work(self):
        qualification, ledger, _ = self.records()
        qualification['gates']['source_420'] = False
        ledger['remaining_work'] = ['finish analysis readiness']
        handoff = p.handoff_text('d' * 40, 'q' * 40, 'INCOMPLETE', ledger, qualification, [], p.EvidenceBudget())
        self.assertIn('INCOMPLETE', handoff); self.assertIn('source_420', handoff)
        self.assertIn('finish analysis readiness', handoff)
        self.assertIn('approved private cross-device delivery', handoff)



class OutputDirectoryCliTests(unittest.TestCase):
    """New conventional output-directory boundary only; no old methods run."""
    def arguments(self, *extra):
        return ['--primary-capture', 'primary', '--second-capture', 'second', '--qualification', 'q',
                '--ledger', 'l', '--source-clearance', 'c', '--marker', 'marker.json', *extra]

    def test_output_modes_are_explicit_and_mutually_exclusive(self):
        parser = p.parser()
        with patch('sys.stderr', io.StringIO()):
            for extra in ([], ['--output', 'one.zip', '--output-dir', 'existing']):
                with self.subTest(extra=extra), self.assertRaises(SystemExit): parser.parse_args(self.arguments(*extra))
        directory = parser.parse_args(self.arguments('--output-dir', 'existing', '--archive-name', 'new.zip'))
        self.assertEqual(directory.output_dir, Path('existing')); self.assertIsNone(directory.output)
        legacy = parser.parse_args(self.arguments('--output', 'one.zip'))
        self.assertEqual(legacy.output, Path('one.zip')); self.assertIsNone(legacy.output_dir)

    def test_existing_directory_derives_exact_child_and_same_root_marker_without_metadata_reads(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'local-evidence') as tmp:
            root = Path(tmp)
            args = p.parser().parse_args(self.arguments('--output-dir', str(root), '--archive-name', 'new.zip',
                                                       '--marker', str(root / 'new-marker.json')))
            with patch.object(p, 'read_json', side_effect=AssertionError('no metadata reads')):
                self.assertEqual(p.resolve_output_paths(args), (root / 'new.zip', root / 'new-marker.json'))
            self.assertEqual(list(root.iterdir()), [])

    def test_unsafe_or_missing_archive_basenames_refuse(self):
        for name in (None, '', ' ', '.', '..', 'a..zip', '/absolute.zip', 'sub/new.zip', 'sub\\new.zip', 'C:new.zip', 'new\n.zip'):
            with self.subTest(name=name), self.assertRaises(p.PackageError): p.archive_basename(name)

    def test_directory_must_exist_be_directory_and_not_be_symlink(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'local-evidence') as tmp:
            root = Path(tmp); ordinary = root / 'file'; ordinary.touch(); linked = root / 'linked'; linked.symlink_to(root, target_is_directory=True)
            for directory in (root / 'missing', ordinary, linked):
                args = p.parser().parse_args(self.arguments('--output-dir', str(directory), '--archive-name', 'new.zip',
                                                           '--marker', str(directory / 'marker.json')))
                with self.subTest(directory=directory.name), self.assertRaises(p.PackageError): p.resolve_output_paths(args)

    def test_legacy_file_mode_preserves_paths_and_refuses_archive_name(self):
        args = p.parser().parse_args(self.arguments('--output', 'legacy/new.zip', '--marker', 'legacy/marker.json'))
        self.assertEqual(p.resolve_output_paths(args), (Path('legacy/new.zip').absolute(), Path('legacy/marker.json').absolute()))
        args.archive_name = 'wrong.zip'
        with self.assertRaises(p.PackageError): p.resolve_output_paths(args)

    def test_directory_mode_rejects_marker_outside_root_and_archive_symlink(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'local-evidence') as tmp:
            root = Path(tmp)
            args = p.parser().parse_args(self.arguments('--output-dir', str(root), '--archive-name', 'new.zip',
                                                       '--marker', str(root.parent / 'outside-marker.json')))
            with self.assertRaises(p.PackageError): p.resolve_output_paths(args)
            args.marker = root / 'marker.json'; (root / 'new.zip').symlink_to('missing-target')
            with self.assertRaises(p.PackageError): p.resolve_output_paths(args)

    def test_new_directory_combination_preserves_exclusive_output_marker_sidecar_refusal(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'local-evidence') as tmp:
            root = Path(tmp)
            args = p.parser().parse_args(self.arguments('--output-dir', str(root), '--archive-name', 'new.zip',
                                                       '--marker', str(root / 'marker.json')))
            output, marker = p.resolve_output_paths(args)
            for path in (output, marker, root / 'new.zip.sha256.json'):
                path.write_bytes(b'preserved-new-fixture')
                with self.subTest(path=path.name), self.assertRaises(p.PackageError): p.reserve_operation(output, marker, {})
                self.assertEqual(path.read_bytes(), b'preserved-new-fixture'); path.unlink()
            marker.symlink_to('missing-target')
            with self.assertRaises(p.PackageError): p.reserve_operation(output, marker, {})
            self.assertTrue(marker.is_symlink())



class LargeEvidenceSupplementTests(unittest.TestCase):
    def receipt(self):
        return {'role':'supplemental_challenge_only','source_file':'SupplementalOwnedChallenges.swift',
                'source_sha256':'a'*64,'swiftc':'/opt/tools/bin/swiftc','sdk':'/opt/sdk',
                'modes':{mode:{'emitted_sha256':digest*64,'library':f'Supplement-{mode}.dylib'}
                         for mode,digest in (('Onone','b'),('O','c'),('Osize','d'))}}

    def declaration(self,receipt):
        return {'supplemental_capture_evidence':{'used':True,'role':'supplemental_challenge_only',
            'source_sha256':receipt['source_sha256'],
            'images':{mode:row['emitted_sha256'] for mode,row in receipt['modes'].items()}}}

    def test_49m_report_ratio_fits_processing_without_raising_serialized_caps(self):
        budget=p.EvidenceBudget();size=49*1024*1024
        budget.reserve_input(size+1);budget.reserve(size*4)
        budget.reserve(size*4+p.JSON_TOKEN_LIMIT*64)
        budget.reserve(size*200)  # deliberately conservative repeated conversion ratio
        budget.retain(56_350_610)
        self.assertGreater(budget.used,p.EVIDENCE_LIMIT)
        self.assertLess(budget.used,p.PROCESSING_ALLOWANCE)
        self.assertEqual(budget.serialized_limit,256*1024*1024)
        self.assertEqual(p.SOURCE_LIMIT,256*1024*1024);self.assertEqual(p.ZIP_LIMIT,512*1024*1024)
        with self.assertRaises(p.PackageError):budget.reserve(p.PROCESSING_ALLOWANCE)

    def test_raw_input_and_retained_payload_caps_remain_independent_and_fail_closed(self):
        budget=p.EvidenceBudget(serialized_limit=12,input_limit=10);payload=p.EvidencePayload(budget)
        payload['one']=b'12345678'
        with self.assertRaises(p.PackageError):payload['two']=b'12345'
        self.assertEqual(budget.serialized_used,8);self.assertNotIn('two',payload)
        with self.assertRaises(p.PackageError):p.bounded_json_bytes('12345',budget)
        with self.assertRaises(p.PackageError):budget.reserve_input(11)
        self.assertEqual(budget.input_used,0)

    def test_json_escaping_uses_small_bounded_chunks_and_preserves_complete_value(self):
        value='unicode \u03bb and quote " '*5000
        original=p.json.JSONEncoder.encode;seen=[]
        def checked(encoder,chunk):
            seen.append(len(chunk));self.assertLessEqual(len(chunk),4096)
            return original(encoder,chunk)
        with patch.object(p.json.JSONEncoder,'encode',checked):
            result=p.bounded_json_bytes({'complete':value},p.EvidenceBudget())
        self.assertEqual(json.loads(result),{'complete':value});self.assertGreater(len(seen),1)

    def test_optional_supplement_requires_exact_declared_original_lineage_and_role(self):
        import copy
        receipt=self.receipt();qualification=self.declaration(receipt)
        self.assertTrue(p.supplemental_lineage(qualification,receipt))
        self.assertFalse(p.supplemental_lineage({},None))
        self.assertFalse(p.supplemental_lineage({'supplemental_capture_evidence':{'used':False}},None))
        for changed,provided in ((qualification,None),({},receipt)):
            with self.assertRaises(p.PackageError):p.supplemental_lineage(changed,provided)
        for key,value in (('source_sha256','e'*64),('images',{'O':'c'*64}),('role','main_qualification')):
            changed=copy.deepcopy(qualification);changed['supplemental_capture_evidence'][key]=value
            with self.subTest(key=key),self.assertRaises(p.PackageError):p.supplemental_lineage(changed,receipt)
        receipt['role']='primary'
        with self.assertRaises(p.PackageError):p.supplemental_lineage(qualification,receipt)

    def test_supplemental_views_and_digest_labels_preserve_full_evidence_without_hashing(self):
        evidence=Path(__file__).resolve().parents[1]/'local-evidence';evidence.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=evidence) as tmp:
            root=Path(tmp);receipt=self.receipt()
            (root/'SupplementalOwnedChallenges.swift').write_text('public func owned() {}\n')
            for name in ('source-manifest.json','compiler-index.json'):
                (root/name).write_text('{"raw_pc":4096,"word":3596551104,"count":6}')
            for mode,row in receipt['modes'].items():
                row['command']=[receipt['swiftc'],'-sdk',receipt['sdk'],'-'+mode,str(root/'SupplementalOwnedChallenges.swift'),'-o',str(root/row['library'])]
                row['custody_after']={'dev':1,'ino':2}
                for kind in ('nm','objdump'):(root/f'{kind}-{mode}.txt').write_text(str(root/row['library'])+' raw observation\n')
                (root/f'compile-{mode}.log').write_text(str(root/'SupplementalOwnedChallenges.swift')+': recorded diagnostic\n')
            replacements=p.relocations({'supplemental':root},{'supplemental':receipt},{})
            budget=p.EvidenceBudget();payload=p.EvidencePayload(budget)
            with patch('hashlib.sha256',side_effect=AssertionError('no hashes')):
                p.capture_payload('supplemental',root,receipt,replacements,payload,budget)
                manifest=p.reused_sha256_manifest({'supplemental':receipt},'new.zip')
            self.assertIn('captures/supplemental/SupplementalOwnedChallenges.swift',payload)
            self.assertIn('captures/supplemental/objdump-Osize.txt',payload)
            view=json.loads(payload['captures/supplemental/compile-receipt.json'])['record']
            self.assertNotIn('custody_after',view['modes']['O'])
            self.assertEqual(view['source_sha256'],'a'*64)
            self.assertEqual(manifest['records'][0]['original_artifact'],'SupplementalOwnedChallenges.swift')
            self.assertNotIn(str(root),payload['captures/supplemental/REPRODUCE.sh'].decode())
            self.assertEqual(json.loads(payload['captures/supplemental/compiler-index.json'])['record']['raw_pc'],4096)



if __name__ == '__main__': unittest.main()
