"""Independent mapping and distrust checks for the saved-report exporter."""
import ast
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import random
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

from airs import facts_export as ex
from airsnav_format_check import check


def tiny():
    return dict(profile='broad-imports-v1', model_version='swift-broad-error-flow-imports-v1',
        import_stub_model='arm64-import-stub-double-binding-v1',
        identity=dict(container_sha256='a'*64, slice_sha256='b'*64, architecture='arm64',
            cpu_subtype=0, uuid=None, preferred_base='0x1000', slice_index=0,
            container_slice_count=1, slice_offset='0x0', slice_size='0x1000'),
        import_stubs_complete=True, import_stub_reason=None, word_scan_complete=True,
        call_details_complete=True, outcome_witnesses_complete=True,
        call_return_proven=False, runtime_reachability_proven=False,
        omitted_calls=0, observed_call_instructions=1, limitations=['structural_only'],
        import_stub_counts={'attributed_stubs': 1}, calls=[dict(caller_pc='0x1000',
        call_pc='0x1004', candidate=None, validation=None, admission=dict(
            model_version='swift-broad-import-callsite-v1', status='unresolved',
            reason='imported_callee_abi_unqualified', call_kind='bl', call_pc=4100,
            caller_start=4096, callee_stub_pc=4352, symbol='_$sDemo',
            details_complete=True, call_return_proven=False,
            syntactic_call_target_admitted=False, import_attribution_admitted=True,
            declaration=dict(status='syntax_unresolved', identity=None, reason='unsupported_production'),
            import_provenance=dict(stub_model='arm64-import-stub-double-binding-v1',
                symbol_index=7, stub_indirect_entry_offset=512,
                pointer_indirect_entry_offset=516, nlist_offset=768,
                stub_words=[dict(pc=4352+4*i, word='0x00000000',
                    slice_file_offset=256+4*i, container_file_offset=256+4*i) for i in range(3)])))])


def emit(report):
    documents, _ = ex.export_report(report, tool_version='test-version')
    for document in documents:
        verdict = check(canonical(document))
        expected = 'producerRefusal' if document['run']['refusalCount'] else None
        assert verdict[1] == expected, verdict
    assert len(documents) == 1 and len(documents[0]['results']) == 1
    return documents[0]['results'][0]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def independent_rules(test, result):
    """README sections 2–4, independently implemented, without exporter helpers."""
    identifiers = []
    for fact in result['facts']:
        test.assertEqual('tier' in fact, fact['status'] in ('derived', 'candidate'))
        if fact['status'] == 'authoritative':
            test.assertNotIn('derivedFrom', fact)
        if fact['status'] == 'unknown':
            test.assertIsNone(fact['value'])
        rules = [p for p in fact['provenance'] if 'rule' in p]
        test.assertTrue(rules)
        test.assertEqual(fact['provenance'][0], rules[0])
        key = rules[0]['rule'] + '@' + rules[0]['ruleVersion']
        expected = 'f-' + hashlib.sha256(canonical([fact['subject'], fact['predicate'], fact['value'], key])).hexdigest()[:32]
        test.assertEqual(fact['id'], expected)
        test.assertEqual(fact['revert'], 'revert:' + expected)
        identifiers.append(expected)
    for gap in result['frontier']:
        expected = 'g-' + hashlib.sha256(canonical([gap['subject'], gap['gap'], gap['detail']])).hexdigest()[:32]
        test.assertEqual(gap['id'], expected)
        test.assertTrue(set(gap['blockedBy']) <= {f['id'] for f in result['facts']})
        identifiers.append(expected)
    test.assertEqual(len(identifiers), len(set(identifiers)))

    def walk(value):
        test.assertNotIsInstance(value, float)
        if type(value) is int:
            test.assertTrue(-(2**63) <= value < 2**63)
        if type(value) is dict:
            for key, item in value.items():
                test.assertRegex(key, r'\A[A-Za-z_][A-Za-z0-9_]*\Z')
                walk(item)
        if type(value) is list:
            for item in value:
                walk(item)
    walk(result)


class MappingTests(unittest.TestCase):
    def test_tiny_mapping_and_provenance(self):
        result = emit(tiny())
        facts = {f['predicate']: f for f in result['facts']}
        self.assertEqual(set(facts), {'callsTarget', 'hasName'})
        self.assertEqual(facts['callsTarget']['subject'], dict(kind='address', ref='0x1004'))
        self.assertEqual(facts['callsTarget']['value'], '0x1100')
        self.assertEqual(facts['hasName']['value'], '_$sDemo')
        self.assertEqual([p['ref'] for p in facts['hasName']['provenance']], [
            '0x1100', '0x1104', '0x1108',
            'stubIndirectEntry[0]@0x200', 'pointerIndirectEntry[0]@0x204', 'symtab[7]@0x300'])
        gap = result['frontier'][0]
        self.assertEqual(gap['gap'], 'unknownCalleeEffects')
        self.assertEqual(gap['detail'], 'imported_callee_abi_unqualified; symbol=_$sDemo; declaration=syntax_unresolved:unsupported_production')
        self.assertEqual(gap['missingEvidence'], ['abi_admission', 'callee_throw_effect', 'swift_declaration_syntax:unsupported_production'])
        self.assertEqual(result['primitiveVersion'], '1')
        self.assertEqual(result['budget'], {})
        independent_rules(self, result)

    def test_admitted_declaration(self):
        report = tiny()
        emit(report)
        report['calls'][0]['admission']['declaration'] = dict(status='syntax_admitted', reason=None, identity={'throws': True})
        result = emit(report)
        self.assertEqual(result['frontier'][0]['missingEvidence'], ['abi_admission', 'callee_throw_effect'])
        self.assertTrue(result['frontier'][0]['detail'].endswith('syntax_admitted:none'))
        self.assertNotIn('throws', canonical(result).decode())

    def test_nine_incomplete_table_reasons(self):
        for reason in ('macho_header', 'load_command_limit', 'section_limit',
                       'raw_section_metadata_mismatch', 'indirect_symbol_table_missing',
                       'indirect_symbol_limit', 'indirect_symbol_table_extent',
                       'stub_limit', 'stub_work_limit'):
            with self.subTest(reason=reason):
                report = tiny()
                self.assertEqual(emit(report)['outcome'], 'facts')
                report.update(import_stub_reason=reason, import_stubs_complete=False, calls=[])
                result = emit(report)
                self.assertEqual(result['facts'], [])
                self.assertEqual(result['outcome'], 'refusal')
                self.assertEqual(result['refusal'], dict(code='preconditionFailed',
                    detail='import_stubs_complete=false; import_stub_reason='+reason, retryable=False))
                self.assertIn('producerIncomplete', [g['gap'] for g in result['frontier']])
                self.assertTrue(all(g['subject']['kind'] == 'image' for g in result['frontier']))
                self.assertNotIn('symbol=', canonical(result).decode())
                independent_rules(self, result)

    def test_each_completeness_flag_and_omissions(self):
        for flag in ('word_scan_complete', 'call_details_complete', 'outcome_witnesses_complete'):
            report = tiny()
            report[flag] = False
            gaps = emit(report)['frontier']
            self.assertEqual(len(gaps), 2)
            gap = next(g for g in gaps if g['gap'] == 'producerIncomplete')
            self.assertEqual(gap['detail'], flag+'=false; import_stub_reason=none')
        report = tiny()
        report['omitted_calls'] = 2
        gap = next(g for g in emit(report)['frontier'] if g['gap'] == 'budgetExceeded')
        self.assertEqual(gap['detail'], 'omitted_calls=2')

    def test_empty_even_with_frontier_is_named_error(self):
        for omitted in (0, 1):
            report = tiny()
            report['omitted_calls'] = omitted
            self.assertTrue(emit(report)['facts'])
            report['calls'] = []
            with self.assertRaisesRegex(ex.ExportError, 'nothing_to_export'):
                emit(report)

    def test_uuid_and_fat_identity_sidecar(self):
        report = tiny()
        report['identity'].update(uuid='{ABCDEF01-2345-6789-ABCD-EF0123456789}', slice_offset='0x4000',
                                  slice_index=1, container_slice_count=2)
        for w in report['calls'][0]['admission']['import_provenance']['stub_words']:
            w['container_file_offset'] += 0x4000
        raw = json.dumps(report).encode()
        files, metadata = ex.export_bytes(raw, tool_version='1+2')
        document, meta = json.loads(files['part-0001.airsnav']), json.loads(metadata)
        self.assertEqual(document['results'][0]['subject']['ref'], 'abcdef01-2345-6789-abcd-ef0123456789/'+'b'*16)
        self.assertEqual(document['identity'], dict(containerSHA256='a'*64, sliceSHA256='b'*64,
            sliceOffset=16384, sliceSize=4096, cpuType=16777228, cpuSubtype=0,
            uuid='abcdef01-2345-6789-abcd-ef0123456789', preferredBase='0x1000'))
        self.assertEqual(meta['report_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(meta['files'][0]['sha256'], hashlib.sha256(files['part-0001.airsnav']).hexdigest())
        self.assertEqual(meta['files'][0]['provenance'], 7)
        self.assertEqual(meta['exporter_version'], 1)
        self.assertEqual(meta['tool_version'], '1+2')
        self.assertEqual(check(files['part-0001.airsnav']), (True, None, None))

    def test_repeated_stub_deduplicated_and_order_deterministic(self):
        report = tiny()
        row = copy.deepcopy(report['calls'][0])
        row['call_pc'] = '0x1008'
        row['admission']['call_pc'] = 4104
        report['calls'].append(row)
        first = ex.canonical_bytes(emit(report))
        self.assertEqual(first, ex.canonical_bytes(emit(report)))
        report['calls'].reverse()
        self.assertEqual(first, ex.canonical_bytes(emit(report)))
        self.assertEqual(len(emit(report)['facts']), 3)
        self.assertEqual(len(emit(report)['frontier']), 2)

    def test_other_rows_have_no_projection(self):
        report = tiny()
        report['calls'].append({'admission': {'status': 'unresolved'}})
        self.assertEqual(emit(report), emit(tiny()))

    def test_not_claimable(self):
        result = emit(tiny())
        for fact in result['facts']:
            self.assertEqual(fact['status'], 'authoritative')
            self.assertNotIn('derivedFrom', fact)
            self.assertNotIn('tier', fact)
            self.assertNotEqual(fact['predicate'], 'isFunctionStart')
            self.assertNotIn('proofCertificate', [p['kind'] for p in fact['provenance']])
            self.assertIsInstance(fact['value'], str)
        self.assertEqual({g['gap'] for g in result['frontier']}, {'unknownCalleeEffects'})
        text = canonical(result).decode()
        for forbidden in ('throws', 'returns', 'dyld', 'unresolvedIndirectCall'):
            self.assertNotIn(forbidden, text)


class DistrustTests(unittest.TestCase):
    def refuse_change(self, path, value, delete=False, *, reason=None, report=None):
        report = copy.deepcopy(report) if report is not None else tiny()
        self.assertIn(emit(report)['outcome'], ('facts', 'refusal'))
        parent = report
        for part in path[:-1]:
            parent = parent[part]
        if delete:
            del parent[path[-1]]
        else:
            parent[path[-1]] = value
        with self.assertRaises(ex.ExportError) as caught:
            emit(report)
        if reason is not None:
            self.assertEqual(caught.exception.reason, reason)
        else:
            self.assertRegex(caught.exception.reason, r'^[a-z_][a-z_0-9]*$')
        # The same one-field mutation must fail without creating either output.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            source, out, meta = [root / x for x in ('report.json', 'out.json', 'meta.json')]
            source.write_text(json.dumps(report))
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                self.assertNotEqual(ex.main([str(source), str(out), '--tool-version', 'test']), 0)
            if reason is not None:
                self.assertEqual(stderr.getvalue().strip(), reason)
            self.assertFalse(out.exists())
            self.assertFalse(meta.exists())

    def test_missing_and_mistyped_read_fields(self):
        root_fields = ['profile', 'model_version', 'identity', 'import_stub_model', 'import_stubs_complete',
            'import_stub_reason', 'word_scan_complete', 'call_details_complete', 'outcome_witnesses_complete',
            'call_return_proven', 'runtime_reachability_proven', 'omitted_calls', 'observed_call_instructions',
            'import_stub_counts', 'limitations', 'calls']
        identity_fields = list(tiny()['identity'])
        admission_fields = ['model_version', 'status', 'reason', 'call_kind', 'call_pc', 'caller_start',
            'callee_stub_pc', 'symbol', 'details_complete', 'call_return_proven',
            'syntactic_call_target_admitted', 'import_attribution_admitted', 'declaration', 'import_provenance']
        paths = [[k] for k in root_fields] + [['identity', k] for k in identity_fields]
        paths += [['calls', 0, k] for k in ('admission', 'caller_pc', 'call_pc', 'candidate', 'validation')]
        base = ['calls', 0, 'admission']
        paths += [base+[k] for k in admission_fields]
        paths += [base+['declaration', k] for k in ('status', 'identity', 'reason')]
        paths += [base+['import_provenance', k] for k in tiny()['calls'][0]['admission']['import_provenance']]
        paths += [base+['import_provenance', 'stub_words', 0, k] for k in ('pc', 'word', 'slice_file_offset', 'container_file_offset')]
        paths += [['schema_version'], ['import_stub_counts', 'attributed_stubs']]
        for path in paths:
            report = tiny()
            report['schema_version'] = 1
            # Exercise the object branch of declaration.identity as well.
            if path == base + ['declaration', 'identity']:
                report['calls'][0]['admission']['declaration'] = dict(
                    status='syntax_admitted', reason=None, identity={})
            parent = report
            for part in path[:-1]:
                parent = parent[part]
            original = parent[path[-1]]
            wrong = True if type(original) is int else ('x' if type(original) in (dict, list) else 7)
            expected = 'invalid_field_' + str(path[-1])
            if str(path[-1]).endswith('_proven'):
                expected = 'unsupported_proof_claim'
            elif path[-1] in ('candidate', 'validation'):
                expected = 'unsupported_import_evidence'
            elif path == base + ['model_version']:
                expected = 'invalid_field_model_version'
            with self.subTest(path=path, mutation='type'):
                self.refuse_change(path, wrong, reason=expected, report=report)
            if path in (['schema_version'], ['import_stub_counts', 'attributed_stubs']):
                continue  # Optional field and dynamically enumerated counter key.
            with self.subTest(path=path, mutation='missing'):
                missing_reason = ('invalid_field_' + str(path[-1])
                                  if str(path[-1]).endswith('_proven') else expected)
                if path == base + ['model_version']:
                    missing_reason = 'unsupported_row_model'
                self.refuse_change(path, None, True, reason=missing_reason, report=report)
        self.refuse_change(['omitted_calls'], 1.25, reason='invalid_json_value')

    def test_rows_with_incomplete_stub_table(self):
        report = tiny()
        report['import_stub_reason'] = 'stub_limit'
        report['import_stubs_complete'] = False
        report['calls'] = []
        self.assertEqual(emit(report)['outcome'], 'refusal')
        self.refuse_change(['calls'], tiny()['calls'], reason='rows_with_incomplete_stub_table', report=report)

    def test_stub_reason_with_complete_table(self):
        self.refuse_change(['import_stub_reason'], 'stub_limit', reason='stub_reason_with_complete_table')

    def test_unaligned_address(self):
        for key in ('call_pc', 'callee_stub_pc', 'caller_start'):
            self.refuse_change(['calls', 0, 'admission', key], 4097, reason='unaligned_address')

    def test_call_before_caller_start(self):
        self.refuse_change(['calls', 0, 'admission', 'caller_start'], 4104, reason='call_before_caller_start')

    def two_stubs(self, second=4400):
        report = tiny()
        row = copy.deepcopy(report['calls'][0])
        row['call_pc'] = '0x1008'
        row['admission'].update(call_pc=4104, callee_stub_pc=second)
        for i, word in enumerate(row['admission']['import_provenance']['stub_words']):
            word['pc'] = second + 4*i
        report['calls'].append(row)
        self.assertEqual(len(emit(report)['facts']), 4)
        return report

    def test_overlapping_stubs(self):
        report = self.two_stubs()
        row = copy.deepcopy(report['calls'][1])
        row['admission']['callee_stub_pc'] = 4356
        for i, word in enumerate(row['admission']['import_provenance']['stub_words']):
            word['pc'] = 4356 + 4*i
        self.refuse_change(['calls', 1], row, reason='overlapping_stubs', report=report)

    def test_conflicting_symbol_entry(self):
        base = ['calls', 1, 'admission']
        for path, value in ((base+['symbol'], '_$sOther'),
                            (base+['import_provenance', 'symbol_index'], 8),
                            (base+['import_provenance', 'nlist_offset'], 784)):
            self.refuse_change(path, value, reason='conflicting_symbol_entry', report=self.two_stubs())

    def test_unsupported_symbol(self):
        for symbol in ('_plain', '_$s4Demo3fooyyF'):
            self.refuse_change(['calls', 0, 'admission', 'symbol'], symbol, reason='unsupported_symbol')
        for symbol in ('$sDemo', '__$sDemo', '_$s4Demo3fooyyKF'):
            report = tiny()
            report['calls'][0]['admission']['symbol'] = symbol
            self.assertEqual(emit(report)['outcome'], 'facts')

    def test_invalid_field_symbol(self):
        for symbol in ('_$sDemo;other', '_$sDemo x'):
            self.refuse_change(['calls', 0, 'admission', 'symbol'], symbol, reason='invalid_field_symbol')

    def test_wrong_values_and_strict_integer(self):
        base = ['calls', 0, 'admission']
        cases = [(['profile'], 'broad-v1'), (['model_version'], 'wrong'),
                 (base+['import_attribution_admitted'], False), (base+['call_pc'], True),
                 (['omitted_calls'], True), (['identity', 'cpu_subtype'], True),
                 (['identity', 'uuid'], 'invalid'), (['identity', 'slice_sha256'], 'bad'),
                 (base+['model_version'], 'wrong'), (base+['call_kind'], 'blr'),
                 (base+['details_complete'], False), (base+['symbol'], ''),
                 (base+['syntactic_call_target_admitted'], True),
                 (base+['declaration', 'status'], 'wrong'),
                 (base+['import_provenance', 'stub_words'], []),
                 (base+['import_provenance', 'stub_words', 0, 'container_file_offset'], 99)]
        for path, value in cases:
            with self.subTest(path=path, value=value):
                self.refuse_change(path, value)

    def test_proven_keys_at_every_depth(self):
        for path in (['call_return_proven'], ['runtime_reachability_proven'],
                     ['calls', 0, 'admission', 'call_return_proven'],
                     ['calls', 0, 'admission', 'new_proven']):
            for value in (True, 0, None, 'false'):
                with self.subTest(path=path, value=value):
                    self.refuse_change(path, value)

    def test_duplicate_calls_and_conflicting_stub(self):
        report = tiny()
        emit(report)
        report['calls'].append(copy.deepcopy(report['calls'][0]))
        with self.assertRaisesRegex(ex.ExportError, 'duplicate_call'):
            emit(report)
        report['calls'][1]['call_pc'] = '0x1008'
        report['calls'][1]['admission']['call_pc'] = 4104
        emit(report)
        report['calls'][1]['admission']['symbol'] = '_$sOther'
        with self.assertRaisesRegex(ex.ExportError, 'conflicting_stub'):
            emit(report)

    def test_malformed_json_and_strict_values(self):
        good = json.dumps(tiny()).encode()
        for bad in (good[:-1], b'{', b'\xff', b'{"profile":1,"profile":2}', b'NaN'):
            ex.export_bytes(good, tool_version='test')
            with self.assertRaises(ex.ExportError):
                ex.export_bytes(bad, tool_version='test')
        for value in (2**63, -(2**63)-1, '\ud800', float('inf')):
            self.refuse_change(['extra'], value)

    def test_caps(self):
        from airs.swift_broad_flow import REPORT_BYTES, IMPORTS_BROAD_LIMITS
        self.assertEqual(ex.MAX_INPUT_BYTES, REPORT_BYTES)
        self.assertEqual(ex.MAX_ROWS, IMPORTS_BROAD_LIMITS.max_total_evidence)
        report = tiny()
        report['calls'] += [{'admission': {}}] * (ex.MAX_ROWS - 1)
        emit(report)
        report['calls'].append({'admission': {}})
        with self.assertRaisesRegex(ex.ExportError, 'row_limit'):
            emit(report)
        good = json.dumps(tiny()).encode()
        boundary = good + b' ' * (ex.MAX_INPUT_BYTES - len(good))
        ex.export_bytes(boundary, tool_version='test')
        with self.assertRaisesRegex(ex.ExportError, 'input_byte_limit'):
            ex.export_bytes(boundary + b' ', tool_version='test')
        report = tiny()
        emit(report)
        report['extra'] = 'x' * ex.MAX_INPUT_BYTES
        with self.assertRaisesRegex(ex.ExportError, 'input_byte_limit'):
            emit(report)


class EncodingAndIOTests(unittest.TestCase):
    def test_literal_id_vectors(self):
        vectors = [
            ([{'kind':'address','ref':'0x0'}, 'callsTarget', '0x10', 'r@1'],
             b'[{"kind":"address","ref":"0x0"},"callsTarget","0x10","r@1"]'),
            ([{'kind':'address','ref':'0x1','image':'i'}, 'hasName', 'caf\u00e9', 'r@1'],
             b'[{"image":"i","kind":"address","ref":"0x1"},"hasName","caf\xc3\xa9","r@1"]'),
            ([{'kind':'address','ref':'0x2'}, 'hasName', 'a\x01\n', ''],
             b'[{"kind":"address","ref":"0x2"},"hasName","a\\u0001\\n",""]')]
        for fields, literal in vectors:
            self.assertEqual(ex.canonical_bytes(fields), literal)
            self.assertEqual(ex.record_id('f', fields), 'f-'+hashlib.sha256(literal).hexdigest()[:32])
        fields = [{'image':'i','kind':'address','ref':'0x1'}, 'unknownCalleeEffects', 'x\x0b']
        literal = b'[{"image":"i","kind":"address","ref":"0x1"},"unknownCalleeEffects","x\\u000b"]'
        self.assertEqual(ex.record_id('g', fields), 'g-'+hashlib.sha256(literal).hexdigest()[:32])

    def test_canonical_invalid_values(self):
        for value in (1.0, 2**63, {'bad-key': 1}, '\ud800'):
            with self.assertRaises(ex.ExportError):
                ex.canonical_bytes(value)

    def test_standard_library_only_imports(self):
        tree = ast.parse(Path(ex.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name.split('.')[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0)
                if node.module == 'airs.swift_import_declarations':
                    continue
                names = [node.module.split('.')[0]]
            else:
                continue
            self.assertTrue(set(names) <= sys.stdlib_module_names, names)

    def test_main_existing_and_collisions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            source, out = root/'report.json', root/'out'
            source.write_text(json.dumps(tiny()))
            argv = [str(source), str(out), '--tool-version', 'test']
            self.assertEqual(ex.main(argv), 0)
            original = {p.name: p.read_bytes() for p in out.iterdir()}
            self.assertEqual(set(original), {'part-0001.airsnav', 'manifest.json'})
            self.assertEqual(check(original['part-0001.airsnav']), (True, None, None))
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(ex.main(argv), 2)
            self.assertEqual(stderr.getvalue().strip(), 'output_exists')
            self.assertEqual({p.name: p.read_bytes() for p in out.iterdir()}, original)
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(ex.main([str(source), str(source), '--tool-version', 'test']), 2)
            self.assertEqual(stderr.getvalue().strip(), 'path_collision')

    def test_atomic_failures(self):
        for operation in ('fsync', 'rename'):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve()
                source, out = root/'report.json', root/'out'
                source.write_text(json.dumps(tiny()))
                with patch.object(ex.os, operation, side_effect=OSError('injected')):
                    with contextlib.redirect_stderr(io.StringIO()) as stderr:
                        self.assertEqual(ex.main([str(source), str(out), '--tool-version', 'test']), 2)
                self.assertEqual(stderr.getvalue().strip(), 'io_error')
                self.assertFalse(out.exists())
                self.assertEqual({p.name for p in root.iterdir()}, {'report.json'})

    def test_symlinks_and_invalid_budget(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            source = root/'report.json'
            source.write_text(json.dumps(tiny()))
            link = root/'link'
            link.symlink_to(source)
            for src, out, extra, reason in (
                    (link, root/'out', [], 'invalid_output_path'),
                    (source, link, [], 'path_collision'),
                    (source, root/'out', ['--max-facts', '4097'], 'invalid_max_facts')):
                with contextlib.redirect_stderr(io.StringIO()) as stderr:
                    self.assertEqual(ex.main([str(src), str(out), '--tool-version', 'test', *extra]), 2)
                self.assertEqual(stderr.getvalue().strip(), reason)
            self.assertFalse((root/'out').exists())

    def test_nothing_exit_code(self):
        report = tiny()
        report['calls'] = []
        with tempfile.TemporaryDirectory() as temp:
            source, out = Path(temp).resolve()/'report.json', Path(temp).resolve()/'out'
            source.write_text(json.dumps(report))
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                self.assertEqual(ex.main([str(source), str(out), '--tool-version', 'test']), 3)
            self.assertEqual(stderr.getvalue().strip(), 'nothing_to_export')
            self.assertFalse(out.exists())


class OwnedFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from airs.macho import parse_macho
        from airs.swift_broad_flow import IMPORTS_BROAD_LIMITS, recover_swift_broad_flow
        fixture = Path(__file__).resolve().parents[1]/'fixtures'/'swift-error-flow'/'broad-imports'
        cls.expected = json.loads((fixture/'expected.json').read_text())
        image = parse_macho((fixture/cls.expected['binary']).read_bytes(), 'OwnedImports.macho', IMPORTS_BROAD_LIMITS)
        # The exporter consumes saved JSON, not producer-side Enum/tuple objects.
        cls.report = json.loads(json.dumps(recover_swift_broad_flow(image, profile='broad-imports-v1')))

    def test_mapping_counts_determinism_and_nonclaims(self):
        expected = self.expected
        retained = [c for c in expected['stub_calls'] if c['symbol'].lstrip('_').startswith('$s')
                    and expected['import_declaration_expectations'][c['symbol']]['outcome'] != 'skip_non_throwing']
        result = emit(self.report)
        self.assertEqual(len(retained), 12)
        self.assertEqual({(f['subject']['ref'], f['value']) for f in result['facts'] if f['predicate']=='callsTarget'},
                         {(hex(c['call_pc']), hex(c['stub_address'])) for c in retained})
        self.assertEqual({(f['subject']['ref'], f['value']) for f in result['facts'] if f['predicate']=='hasName'},
                         {(hex(c['stub_address']), c['symbol']) for c in retained})
        self.assertEqual(len(result['facts']), len(retained)+len({c['stub_address'] for c in retained}))
        self.assertEqual(len(result['frontier']), len(retained))
        first = ex.canonical_bytes(result)
        self.assertEqual(first, ex.canonical_bytes(emit(self.report)))
        shuffled = copy.deepcopy(self.report)
        random.Random(5).shuffle(shuffled['calls'])
        self.assertEqual(first, ex.canonical_bytes(emit(shuffled)))
        independent_rules(self, result)
        self.assertEqual({f['predicate'] for f in result['facts']}, {'callsTarget', 'hasName'})
        self.assertEqual({g['gap'] for g in result['frontier']}, {'unknownCalleeEffects'})
        for f in result['facts']:
            self.assertEqual(f['status'], 'authoritative')
            self.assertNotIn('tier', f)
            self.assertNotIn('derivedFrom', f)
            for p in f['provenance']:
                self.assertNotEqual(p['kind'], 'proofCertificate')
            self.assertRegex(f['subject']['ref'], r'\A0x(0|[1-9a-f][0-9a-f]*)\Z')




def many_rows(count, distinct=False):
    report = tiny()
    template = report['calls'][0]
    rows = []
    for i in range(count):
        row = copy.deepcopy(template)
        row['call_pc'] = hex(4100 + 4*i)
        row['admission']['call_pc'] = 4100 + 4*i
        if distinct:
            stub = 65536 + 12*i
            row['admission']['callee_stub_pc'] = stub
            for j, word in enumerate(row['admission']['import_provenance']['stub_words']):
                word['pc'] = stub + 4*j
        rows.append(row)
    report['calls'] = rows
    return report


def control_document():
    """Hand-authored transport, independent of all exporter constructors."""
    subject = {'kind': 'address', 'ref': '0x1000'}
    ident = 'f-' + hashlib.sha256(canonical([subject, 'hasName', 'entry', 'airs.test@1'])).hexdigest()[:32]
    fact = dict(kind='Fact', schemaVersion=1, id=ident, subject=subject,
        predicate='hasName', value='entry', status='authoritative',
        provenance=[dict(kind='loaderRecord', ref='lc[0]', rule='airs.test', ruleVersion='1')],
        toolchain='airs-undetected/1', revert='revert:'+ident)
    result = dict(kind='PrimitiveResult', schemaVersion=1, primitive='airs.test', primitiveVersion='1',
        subject=subject, budget={}, outcome='facts', facts=[fact], frontier=[])
    return dict(kind='airs.navigator_results', formatVersion=1,
        identity=dict(containerSHA256='a'*64, sliceSHA256='b'*64, sliceOffset=0, sliceSize=4096,
                      cpuType=16777228, cpuSubtype=0, uuid=None, preferredBase='0x1000'),
        run=dict(producerName='AIRS', producerVersion='test', contractVersion=1, completed=True,
                 toolchain='airs-undetected/1', resultCount=1, factCount=1, frontierCount=0, refusalCount=0),
        results=[result])


def recount(document):
    document['run'].update(resultCount=len(document['results']),
        factCount=sum(len(r['facts']) for r in document['results']),
        frontierCount=sum(len(r['frontier']) for r in document['results']),
        refusalCount=sum(r['outcome'] == 'refusal' for r in document['results']))


class TransportTests(unittest.TestCase):
    def export(self, report, **kwargs):
        files, manifest = ex.export_bytes(canonical(report), tool_version='test', **kwargs)
        for raw in files.values():
            document = json.loads(raw)
            if document['run']['refusalCount']:
                self.assertEqual(check(raw), (False, 'producerRefusal', 'results[0].refusal'))
            else:
                self.assertEqual(check(raw), (True, None, None))
            for result in document['results']:
                independent_rules(self, result)
        return [json.loads(raw) for raw in files.values()], json.loads(manifest)

    def test_result_packing_boundary(self):
        # One name plus two additions per row: 63 rows -> 127; row 64 needs 129.
        docs, _ = self.export(many_rows(64))
        self.assertEqual([(len(r['facts']), len(r['frontier'])) for r in docs[0]['results']], [(64, 63), (1, 1)])
        report = many_rows(64)
        report['word_scan_complete'] = False
        docs, _ = self.export(report)
        self.assertEqual([(len(r['facts']), len(r['frontier'])) for r in docs[0]['results']], [(64, 64), (1, 1)])

    def test_file_boundary_and_repeated_name(self):
        docs, meta = self.export(many_rows(512))
        self.assertEqual(len(docs), 2)
        self.assertEqual([(d['run']['factCount'], d['run']['frontierCount']) for d in docs], [(512, 511), (2, 1)])
        for d in docs:
            names = [f for r in d['results'] for f in r['facts'] if f['predicate'] == 'hasName']
            self.assertEqual(len(names), 1)
        self.assertEqual(meta['exported_rows'], 512)
        self.assertEqual(meta['omitted_rows'], 0)
        self.assertTrue(meta['completed'])
        self.assertEqual(sum(f['facts'] for f in meta['files']), 514)

    def test_selection_order_and_stop(self):
        report = many_rows(4)
        report['calls'][2]['admission']['callee_stub_pc'] = 4400
        for j, word in enumerate(report['calls'][2]['admission']['import_provenance']['stub_words']):
            word['pc'] = 4400 + 4*j
        report['calls'].reverse()
        docs, meta = self.export(report, max_facts=5)
        calls = [f['subject']['ref'] for d in docs for r in d['results'] for f in r['facts'] if f['predicate'] == 'callsTarget']
        self.assertEqual(calls, ['0x1004', '0x100c', '0x1008'])
        self.assertEqual((meta['total_rows'], meta['exported_rows'], meta['omitted_rows']), (4, 3, 1))
        gap = docs[0]['results'][0]['frontier'][0]
        self.assertEqual(gap['detail'], 'exporter_fact_budget=5; exported_rows=3; omitted_rows=1')
        self.assertEqual(gap['missingEvidence'], ['omitted_call_rows'])
        self.assertFalse(docs[0]['run']['completed'])

    def test_every_file_has_disclosures(self):
        report = many_rows(900, distinct=True)
        report.update(omitted_calls=3, word_scan_complete=False)
        docs, meta = self.export(report, max_facts=1500)
        self.assertGreater(len(docs), 1)
        self.assertEqual(meta['exported_rows'], 750)
        for d in docs:
            self.assertFalse(d['run']['completed'])
            self.assertEqual([g['gap'] for g in d['results'][0]['frontier'][:3]],
                             ['budgetExceeded', 'producerIncomplete', 'budgetExceeded'])
            self.assertEqual(d['results'][0]['frontier'][2]['detail'],
                             'exporter_fact_budget=1500; exported_rows=750; omitted_rows=150')

    def test_budget_one_is_disclosure_only(self):
        docs, meta = self.export(tiny(), max_facts=1)
        self.assertEqual(meta['exported_rows'], 0)
        self.assertEqual(meta['omitted_rows'], 1)
        self.assertEqual(docs[0]['results'][0]['outcome'], 'narrowed')
        self.assertEqual(docs[0]['run']['factCount'], 0)
        for n in (0, 4097, True):
            with self.assertRaisesRegex(ex.ExportError, 'invalid_max_facts'):
                ex.export_report(tiny(), tool_version='test', max_facts=n)
        self.export(tiny(), max_facts=4096)

    def test_refusal_and_completed_flags(self):
        docs, meta = self.export(tiny())
        self.assertTrue(meta['completed'])
        for flag in ex.COMPLETENESS:
            report = tiny()
            report[flag] = False
            if flag == 'import_stubs_complete':
                report.update(calls=[], import_stub_reason='stub_limit')
            docs, meta = self.export(report)
            self.assertFalse(meta['completed'])
            self.assertEqual(docs[0]['run']['refusalCount'], int(flag == 'import_stubs_complete'))
        report = tiny()
        report['omitted_calls'] = 1
        self.assertFalse(self.export(report)[1]['completed'])

    def test_identity_refusals(self):
        helper = DistrustTests()
        for field, value, reason in (
            ('architecture', 'x86_64', 'unsupported_architecture'),
            ('cpu_subtype', 2**31, 'cpu_subtype_range'),
            ('cpu_subtype', -(2**31)-1, 'cpu_subtype_range'),
            ('slice_offset', '0x8000000000000000', 'slice_range'),
            ('slice_size', '0x8000000000000000', 'slice_range'),
            ('slice_size', '0x0', 'empty_slice'),
            ('slice_offset', '0x7fffffffffffffff', 'slice_extent_overflow'),
            ('preferred_base', '0x10000000000000000', 'invalid_field_preferred_base')):
            with self.subTest(field=field, value=value):
                helper.refuse_change(['identity', field], value, reason=reason)
        for subtype in (-(2**31), 2**31-1, 2):
            report = tiny()
            report['identity']['cpu_subtype'] = subtype
            self.assertEqual(self.export(report)[0][0]['identity']['cpuSubtype'], subtype)

    def test_unsafe_text(self):
        helper = DistrustTests()
        chars = [chr(i) for i in range(32)] + [chr(i) for i in range(127, 160)]
        chars += [chr(i) for i in (0x61c, 0x200e, 0x200f, *range(0x202a, 0x202f), *range(0x2066, 0x206a))]
        for char in chars + ['x'*4097]:
            with self.subTest(code=ord(char) if len(char) == 1 else 'long'):
                helper.refuse_change(['calls', 0, 'admission', 'symbol'], '_$sDemo'+char, reason='unsafe_text')
        for version, reason in (('', 'invalid_tool_version'), ('é'*65, 'invalid_tool_version'), ('v\u202e', 'unsafe_text')):
            with self.assertRaisesRegex(ex.ExportError, reason):
                ex.export_report(tiny(), tool_version=version)
        report = tiny()
        report['calls'][0]['admission']['declaration']['reason'] = 'x'*4096
        with self.assertRaisesRegex(ex.ExportError, 'unsafe_text'):
            self.export(report)

    def test_deterministic_bytes_and_manifest(self):
        report = many_rows(520)
        raw = canonical(report)
        first = ex.export_bytes(raw, tool_version='test')
        second = ex.export_bytes(raw, tool_version='test')
        self.assertEqual(first, second)
        report['calls'].reverse()
        shuffled = ex.export_bytes(canonical(report), tool_version='test')
        self.assertEqual(first[0], shuffled[0])
        # The manifest intentionally binds original report bytes, including order.
        self.assertNotEqual(first[1], shuffled[1])
        for data in first[0].values():
            self.assertEqual(check(data), (True, None, None))

    def test_checker_addition_caps(self):
        for count in (128, 129):
            d = control_document()
            d['results'][0]['facts'] *= count
            recount(d)
            self.assertEqual(check(canonical(d))[1], None if count == 128 else 'budgetExceeded')
        for count in (1024, 1025):
            d = control_document()
            r = d['results'][0]
            d['results'] = [dict(r, facts=r['facts']*128) for _ in range(8)]
            if count == 1025:
                d['results'].append(r)
                # Keep declared counts bounded so the raw-addition cap is isolated.
                recount(d)
                d['run']['factCount'] = 1024
            else:
                recount(d)
            self.assertEqual(check(canonical(d))[1], None if count == 1024 else 'budgetExceeded')

    def test_checker_provenance_caps(self):
        for count in (4096, 4097):
            d = control_document()
            f = d['results'][0]['facts'][0]
            d['results'][0]['facts'] = [dict(f, provenance=f['provenance']*128) for _ in range(32)]
            if count == 4097:
                d['results'][0]['facts'].append(f)
            recount(d)
            self.assertEqual(check(canonical(d))[1], None if count == 4096 else 'budgetExceeded')

    def test_checker_envelope_and_record_controls(self):
        d = control_document()
        self.assertEqual(check(canonical(d)), (True, None, None))
        cases = [(['kind'], 'wrong', 'unsupportedFormat'),
            (['formatVersion'], 2, 'unsupportedVersion'),
            (['run', 'factCount'], 0, 'countMismatch'),
            (['run', 'resultCount'], True, 'invalidEnvelope'),
            (['run', 'completed'], False, 'invalidEnvelope'),
            (['identity', 'sliceSize'], 0, 'invalidEnvelope'),
            (['results', 0, 'primitive'], 'foreign.test', 'reservedRule'),
            (['results', 0, 'facts', 0, 'generation'], {}, 'invalidRecord'),
            (['results', 0, 'facts', 0, 'dependsOn'], [], 'invalidRecord'),
            (['results', 0, 'facts', 0, 'status'], 'proven', 'invalidRecord'),
            (['results', 0, 'facts', 0, 'toolchain'], 'other', 'unsupportedToolchain'),
            (['results', 0, 'facts', 0, 'id'], 'f-'+'0'*32, 'invalidRecord')]
        for path, value, code in cases:
            bad = copy.deepcopy(d)
            parent = bad
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = value
            self.assertEqual(check(canonical(bad))[1], code, path)

    def test_checker_remaining_format_caps(self):
        good = canonical(control_document())
        self.assertEqual(check(good + b' '*(4194304-len(good))), (True, None, None))
        self.assertEqual(check(good + b' '*(4194305-len(good)))[1:], ('budgetExceeded', '$'))
        for key, code in (('a'*65, 'budgetExceeded'), ('é', 'invalidKey')):
            self.assertEqual(check(canonical({key: 0}))[1:], (code, '$'))
        for count in (4096, 4097):
            raw = canonical({'a'+str(i): 0 for i in range(count)})
            self.assertEqual(check(raw)[1], 'invalidEnvelope' if count == 4096 else 'budgetExceeded')
        for depth in (32, 33, 1200):
            raw = b'['*depth + b'0' + b']'*depth
            self.assertEqual(check(raw)[1], 'invalidEnvelope' if depth == 32 else 'budgetExceeded')
        for count in (128, 129):
            d = control_document()
            d['results'][0]['facts'][0]['provenance'] *= count
            self.assertEqual(check(canonical(d))[1], None if count == 128 else 'budgetExceeded')
        d = control_document()
        d['results'] *= 129
        self.assertEqual(check(canonical(d))[1:], ('budgetExceeded', 'results'))
        # A dictionary with 512 groups of 128 values crosses the node bound.
        self.assertEqual(check(canonical({'x'+str(i): [0]*128 for i in range(512)}))[1:], ('budgetExceeded', '$'))
        for raw, code in ((b'{"a":0,"\\u0061":1}', 'duplicateKey'),
                          (b'1.0', 'invalidNumber'), (b'1e0', 'invalidNumber'),
                          (b'9223372036854775808', 'invalidNumber'),
                          (b'"\\ud800"', 'malformedJSON'), (b'"\\u202e"', 'unsafeText')):
            self.assertEqual(check(raw)[1:], (code, '$'))

    def test_final_preflight_failure_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            source, out = root/'report.json', root/'out'
            source.write_text(json.dumps(tiny()))
            with patch.object(ex, '_check_file', side_effect=ex.ExportError('format_budget_exceeded')):
                with contextlib.redirect_stderr(io.StringIO()) as stderr:
                    self.assertEqual(ex.main([str(source), str(out), '--tool-version', 'test']), 2)
            self.assertEqual(stderr.getvalue().strip(), 'format_budget_exceeded')
            self.assertFalse(out.exists())
            self.assertEqual({p.name for p in root.iterdir()}, {'report.json'})


if __name__ == '__main__':
    unittest.main()
