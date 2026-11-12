"""Profile broad-imports-got-v1: synthetic flow tests and the owned real-toolchain fixture.

Synthetic expectations derive from the GOT attribution contract
and the byte layout in got_image_helpers. Fixture expectations
come from fixtures/swift-error-flow/broad-imports/expected-got.json, which was
derived from Apple tools only (its 'derivation' field lists the commands).
Relations to broad-imports-v1 are checked in process on the same image. No
image is executed.
"""
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from got_image_helpers import (  # noqa: E402
    GotImport, NOP, PtrSection, RET, THROWING, X16, X17, blr, blraaz, br, build_got_image, got_call, mov_x,
    movz_x,
)
from airs.macho import parse_macho  # noqa: E402
from airs.report import dumps  # noqa: E402
from airs.swift_import_declarations import parse_import_declaration  # noqa: E402
from airs.swift_broad_flow import EXTENDED_BROAD_LIMITS, PROFILE_LIMITS, recover_swift_broad_flow  # noqa: E402
from airs.macho_got import CHAINED_FIXUPS_MODEL, GOT_MODEL, WINDOW_MODEL, attribute_got_bindings  # noqa: E402

PROFILE = 'broad-imports-got-v1'
MODEL = 'swift-broad-error-flow-imports-got-v1'
BASE_PROFILE = 'broad-imports-v1'
BASE_MODEL = 'swift-broad-error-flow-imports-v1'
OLDER_PROFILES = ('broad-v1', 'broad-large-v1', 'broad-extended-v1')
NON_THROWING = '_$s4Test3fooyS2iF'
UNRESOLVED = '_$sZZZ'
THROWING2 = '_$s4Test3baryS2iKF'
CALLER = 0x100001000
GOT = 0x100004000
SWIFT_CORE = '/usr/lib/swift/libswiftCore.dylib'
GOT_KEYS = {'got_binding_model', 'chained_fixups_model', 'got_window_model', 'got_bindings_complete',
            'got_binding_reason', 'chained_fixups_status', 'got_counts', 'got_decline_counts',
            'got_slot_decline_counts'}
COUNT_KEYS = ('got_slots', 'agreeing_got_slots', 'declined_got_slots', 'blr_instructions', 'got_candidates',
              'attributed_got_calls', 'declined_got_calls', 'selected_got_calls', 'non_throwing_swift_got_calls',
              'non_swift_got_calls')
SELECTION_KEYS = ('calls', 'selected_call_candidates', 'status_counts', 'reason_counts')
FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures' / 'swift-error-flow' / 'broad-imports'


def image_of(data):
    return parse_macho(data, limits=EXTENDED_BROAD_LIMITS)


def flow(image, limits=None, profile=PROFILE):
    return recover_swift_broad_flow(image, limits, profile=profile)


def listify(value):
    if isinstance(value, dict):
        return {k: listify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [listify(v) for v in value]
    return value


def got_counts(**overrides):
    counts = dict.fromkeys(COUNT_KEYS, 0)
    counts.update(overrides)
    return counts


def common(report):
    """The report without the keys the new profile may change.

    'analysis_work' is a whole-report work counter: the GOT table and window cost work and a
    skipped row saves work, so it is not compared. Rows, including
    their own work_steps, are compared byte for byte.
    """
    return {k: v for k, v in report.items()
            if k not in GOT_KEYS | {'model_version', 'profile', 'limitations', 'analysis_work'}}


class GotProfileTestCase(unittest.TestCase):
    def pair(self, data, limits=None):
        image = image_of(data)
        return flow(image, limits), flow(image, limits, BASE_PROFILE)

    def assertProfileShape(self, report, base):
        self.assertEqual((report['model_version'], report['profile']), (MODEL, PROFILE))
        self.assertEqual((base['model_version'], base['profile']), (BASE_MODEL, BASE_PROFILE))
        self.assertEqual(set(report) - set(base), GOT_KEYS)
        self.assertEqual(set(base) - set(report), set())
        self.assertFalse(GOT_KEYS & set(base))
        self.assertEqual(report['limitations'],
                         base['limitations'] + ['got_callees_attribution_only', 'got_window_entry_screen_syntactic'])
        self.assertEqual((report['got_binding_model'], report['chained_fixups_model'], report['got_window_model']),
                         (GOT_MODEL, CHAINED_FIXUPS_MODEL, WINDOW_MODEL))
        self.assertEqual(set(report['got_counts']), set(COUNT_KEYS))
        self.assertTrue(all(type(v) is int for v in report['got_counts'].values()))
        for key in ('got_decline_counts', 'got_slot_decline_counts'):
            self.assertEqual(list(report[key]), sorted(report[key]), key)
        json.loads(dumps(report))

    def assertSameAsBase(self, report, base):
        """No attributed call: every shared key (rows included) is identical to broad-imports-v1."""
        self.assertProfileShape(report, base)
        self.assertEqual(common(report), common(base))

    def assertReplaced(self, report, base, replaced):
        """Attributed calls: `replaced` maps call_pc (hex) to the new GOT row, or None for a skipped call.

        Every row at any other pc is byte-identical to broad-imports-v1 (I6), the rows keep their order,
        and the selection counters move by exactly the removed and added rows.
        """
        self.assertProfileShape(report, base)
        a, b = common(report), common(base)
        for key in SELECTION_KEYS:
            a.pop(key), b.pop(key)
        self.assertEqual(a, b)
        expected, removed, added = [], [], []
        for row in base['calls']:
            if row['call_pc'] in replaced:
                removed.append(row)
                if replaced[row['call_pc']] is not None:
                    expected.append(replaced[row['call_pc']])
                    added.append(replaced[row['call_pc']])
            else:
                expected.append(row)
        for pc, row in replaced.items():
            if row is not None and row not in added:
                expected.append(row)
                added.append(row)
        self.assertEqual(sorted(json.dumps(r, sort_keys=True) for r in report['calls']),
                         sorted(json.dumps(r, sort_keys=True) for r in expected))
        self.assertEqual([r for r in report['calls'] if r['call_pc'] not in replaced],
                         [r for r in base['calls'] if r['call_pc'] not in replaced])
        self.assertEqual(report['selected_call_candidates'],
                         base['selected_call_candidates'] - len(removed) + len(added))

        def tally(rows, field):
            return Counter(r['admission'][field] for r in rows)

        self.assertEqual(Counter(report['status_counts']) + tally(removed, 'status'),
                         Counter(base['status_counts']) + tally(added, 'status'))
        self.assertEqual(Counter(report['reason_counts']) + tally(removed, 'reason'),
                         Counter(base['reason_counts']) + tally(added, 'reason'))

    def expected_row(self, data, *, call_pc, caller=CALLER, symbol=THROWING, declaration=None):
        image = image_of(data)
        table = attribute_got_bindings(image)
        function = next(f for f in image.functions if f.start == caller)
        kind, call = table.classify(function, call_pc)
        self.assertEqual(kind, 'attributed')
        binding = call.binding
        if declaration is None:
            declaration = {'status': 'syntax_admitted',
                           'identity': listify(asdict(parse_import_declaration(symbol).identity)), 'reason': None}
        return {'caller_pc': hex(caller), 'call_pc': hex(call_pc), 'candidate': None, 'validation': None,
                'admission': {
                    'model_version': 'swift-broad-got-callsite-v1', 'status': 'unresolved',
                    'reason': 'imported_callee_abi_unqualified', 'call_kind': 'blr_got', 'call_pc': call_pc,
                    'caller_start': caller, 'register': 'x%d' % call.register, 'adrp_pc': call.adrp_pc,
                    'ldr_pc': call.ldr_pc, 'slot_address': binding.slot_address,
                    'slot_section': binding.slot_section, 'symbol': symbol,
                    'library_ordinal': binding.library_ordinal, 'library_path': binding.library_path,
                    'weak_import': binding.weak_import, 'import_ordinal': binding.import_ordinal,
                    'declaration': declaration,
                    'got_provenance': listify({**call.record()['provenance'],
                                               'binding': binding.record()['provenance'], 'got_model': GOT_MODEL}),
                    'details_complete': True, 'call_return_proven': False,
                    'syntactic_call_target_admitted': False, 'import_attribution_admitted': True}}

    def assertRow(self, row, expected):
        row = json.loads(json.dumps(row))
        admission = dict(row['admission'])
        work = admission.pop('work_steps')
        self.assertIs(type(work), int)
        self.assertGreaterEqual(work, 0)
        self.assertEqual({**row, 'admission': admission}, expected)


class ProfileTests(GotProfileTestCase):
    def test_profile_constants(self):
        from airs.swift_broad_profiles import BROAD_IMPORTS_GOT_MODEL, BROAD_IMPORTS_GOT_PROFILE
        self.assertEqual((BROAD_IMPORTS_GOT_PROFILE, BROAD_IMPORTS_GOT_MODEL), (PROFILE, MODEL))
        self.assertIn(PROFILE, PROFILE_LIMITS)
        self.assertEqual(PROFILE_LIMITS[PROFILE], PROFILE_LIMITS[BASE_PROFILE])

    def test_throwing_swift_got_call_is_selected(self):
        data, _ = build_got_image()
        report, base = self.pair(data)
        self.assertTrue(report['got_bindings_complete'])
        self.assertIsNone(report['got_binding_reason'])
        self.assertEqual(report['chained_fixups_status'], 'decoded')
        self.assertEqual(report['got_counts'], got_counts(got_slots=1, agreeing_got_slots=1, blr_instructions=1,
                                                          got_candidates=1, attributed_got_calls=1,
                                                          selected_got_calls=1))
        self.assertEqual((report['got_decline_counts'], report['got_slot_decline_counts']), ({}, {}))
        self.assertEqual(report['observed_call_instructions'], base['observed_call_instructions'])
        self.assertTrue(report['call_details_complete'])
        expected = self.expected_row(data, call_pc=CALLER + 8)
        self.assertEqual(expected['admission']['slot_section'], '__DATA_CONST,__got')
        self.assertEqual((expected['admission']['register'], expected['admission']['library_path']),
                         ('x16', SWIFT_CORE))
        row = next(r for r in report['calls'] if r['call_pc'] == hex(CALLER + 8))
        self.assertRow(row, expected)
        self.assertReplaced(report, base, {hex(CALLER + 8): row})

    def test_non_swift_got_call_is_skipped(self):
        for symbol in ('_objc_msgSend', '___chkstk_darwin', '_s4Test3fooyS2iKF'):
            with self.subTest(symbol):
                data, _ = build_got_image(imports=(GotImport(symbol, 1),))
                report, base = self.pair(data)
                self.assertEqual(report['got_counts'],
                                 got_counts(got_slots=1, agreeing_got_slots=1, blr_instructions=1, got_candidates=1,
                                            attributed_got_calls=1, non_swift_got_calls=1))
                self.assertReplaced(report, base, {hex(CALLER + 8): None})  # decision D3: skipped

    def test_non_throwing_swift_got_call_is_skipped(self):
        parsed = parse_import_declaration(NON_THROWING)
        self.assertTrue(parsed.supported)
        self.assertFalse(parsed.identity.throws)
        data, _ = build_got_image(imports=(GotImport(NON_THROWING),))
        report, base = self.pair(data)
        self.assertEqual(report['got_counts'],
                         got_counts(got_slots=1, agreeing_got_slots=1, blr_instructions=1, got_candidates=1,
                                    attributed_got_calls=1, non_throwing_swift_got_calls=1))
        self.assertReplaced(report, base, {hex(CALLER + 8): None})

    def test_unresolved_swift_got_call_is_selected(self):
        self.assertFalse(parse_import_declaration(UNRESOLVED).supported)
        data, _ = build_got_image(imports=(GotImport(UNRESOLVED),))
        report, base = self.pair(data)
        self.assertEqual(report['got_counts']['selected_got_calls'], 1)
        row = next(r for r in report['calls'] if r['call_pc'] == hex(CALLER + 8))
        declaration = row['admission']['declaration']
        self.assertEqual((declaration['status'], declaration['identity']), ('syntax_unresolved', None))
        self.assertIs(type(declaration['reason']), str)
        self.assertTrue(declaration['reason'])
        self.assertRow(row, self.expected_row(data, call_pc=CALLER + 8, symbol=UNRESOLVED,
                                              declaration=declaration))
        self.assertReplaced(report, base, {hex(CALLER + 8): row})

    def test_declined_call_keeps_the_base_row(self):
        fn = (movz_x(X16, 4), ('ldr', X16, X16, ('slot', '__got', 0)), blr(X16), RET)
        data, _ = build_got_image((fn,))
        report, base = self.pair(data)
        self.assertEqual(report['got_counts'],
                         got_counts(got_slots=1, agreeing_got_slots=1, blr_instructions=1, got_candidates=1,
                                    declined_got_calls=1))
        self.assertEqual(report['got_decline_counts'], {'got_base_not_adrp': 1})
        self.assertSameAsBase(report, base)

    def test_slot_decline_is_counted_and_keeps_the_base_row(self):
        data, layout = build_got_image()
        data = bytearray(data)
        data[layout.import_entry_off(0):layout.import_entry_off(0) + 4] = (1 | (1 << 9)).to_bytes(4, 'little')
        report, base = self.pair(bytes(data))
        self.assertEqual(report['got_counts'],
                         got_counts(got_slots=1, declined_got_slots=1, blr_instructions=1, got_candidates=1,
                                    declined_got_calls=1))
        self.assertEqual(report['got_slot_decline_counts'], {'binding_library_mismatch': 1})
        self.assertEqual(report['got_decline_counts'], {'binding_library_mismatch': 1})
        self.assertSameAsBase(report, base)

    def test_shape_absent_and_non_plain_blr(self):
        data, _ = build_got_image(((mov_x(X16, 0), blr(X16), br(X17), blraaz(X16), RET),))
        report, base = self.pair(data)
        self.assertEqual(report['got_counts'], got_counts(got_slots=1, agreeing_got_slots=1, blr_instructions=1))
        self.assertSameAsBase(report, base)

    def test_image_level_status_declines_every_slot_and_call(self):
        data, _ = build_got_image(include_chained=False)
        report, base = self.pair(data)
        self.assertTrue(report['got_bindings_complete'])
        self.assertIsNone(report['got_binding_reason'])
        self.assertEqual(report['chained_fixups_status'], 'chained_fixups_absent')
        self.assertEqual(report['got_counts'], got_counts(got_slots=1, declined_got_slots=1, blr_instructions=1,
                                                          got_candidates=1, declined_got_calls=1))
        self.assertEqual(report['got_slot_decline_counts'], {'chained_fixups_absent': 1})
        self.assertEqual(report['got_decline_counts'], {'chained_fixups_absent': 1})
        self.assertSameAsBase(report, base)

    def test_incomplete_table_forces_call_details_incomplete(self):
        data, _ = build_got_image(include_dysymtab=False)
        report, base = self.pair(data)
        self.assertFalse(report['got_bindings_complete'])
        self.assertEqual(report['got_binding_reason'], 'indirect_symbol_table_missing')
        self.assertFalse(report['call_details_complete'])
        self.assertEqual(report['got_counts']['blr_instructions'], 1)
        for key in ('got_candidates', 'attributed_got_calls', 'declined_got_calls', 'selected_got_calls'):
            self.assertEqual(report['got_counts'][key], 0, key)
        self.assertEqual(report['got_decline_counts'], {})
        self.assertProfileShape(report, base)
        a, b = common(report), common(base)
        a.pop('call_details_complete'), b.pop('call_details_complete')
        self.assertEqual(a, b)

    def test_mixed_sites_rows_identical_except_attributed(self):
        # caller0: attributed throwing call; declined call (base not ADRP); shape-absent BLR; caller1: a
        # non-Swift attributed call; caller2: another attributed throwing call to slot 1.
        imports = (GotImport(THROWING), GotImport(THROWING2), GotImport('_free', 1))
        slot = lambda k: ('slot', '__got', k)  # noqa: E731
        callers = (got_call(slot=0) + (movz_x(X17, 1), ('ldr', X16, X17, slot(1)), blr(X16), mov_x(X16, 1),
                                       blr(X16), RET),
                   got_call(slot=2) + (RET,),
                   got_call(slot=1, rd=X17) + (RET,))
        data, layout = build_got_image(callers, imports)
        report, base = self.pair(data)
        first, second, third = layout.caller_addrs
        self.assertEqual(report['got_counts'], got_counts(
            got_slots=3, agreeing_got_slots=3, blr_instructions=5, got_candidates=4, attributed_got_calls=3,
            declined_got_calls=1, selected_got_calls=2, non_swift_got_calls=1))
        self.assertEqual(report['got_decline_counts'], {'got_base_not_adrp': 1})
        rows = [r for r in report['calls'] if r['call_pc'] in (hex(first + 8), hex(third + 8))]
        self.assertEqual(len(rows), 2)
        self.assertRow(rows[0] if rows[0]['call_pc'] == hex(first + 8) else rows[1],
                       self.expected_row(data, call_pc=first + 8, caller=first))
        self.assertRow(rows[1] if rows[1]['call_pc'] == hex(third + 8) else rows[0],
                       self.expected_row(data, call_pc=third + 8, caller=third, symbol=THROWING2))
        by_pc = {r['call_pc']: r for r in rows}
        self.assertReplaced(report, base, {**by_pc, hex(second + 8): None})

    def test_two_calls_to_one_slot_share_the_declaration(self):
        data, _ = build_got_image((got_call() + got_call() + (RET,),))
        report, base = self.pair(data)
        self.assertEqual(report['got_counts']['selected_got_calls'], 2)
        rows = [r for r in report['calls'] if r['admission'].get('call_kind') == 'blr_got']
        self.assertEqual([r['call_pc'] for r in rows], [hex(CALLER + 8), hex(CALLER + 20)])
        self.assertEqual(rows[0]['admission']['declaration'], rows[1]['admission']['declaration'])
        self.assertReplaced(report, base, {r['call_pc']: r for r in rows})

    def test_per_function_retention_cap(self):
        imports = (GotImport(THROWING), GotImport(THROWING2))
        data, _ = build_got_image((got_call(slot=0) + got_call(slot=1) + (RET,),), imports)
        image = image_of(data)
        full = flow(image)
        self.assertEqual(full['got_counts']['selected_got_calls'], 2)
        limits = replace(PROFILE_LIMITS[PROFILE], max_observations_per_function=1)
        report = flow(image, limits)
        base = flow(image, limits, BASE_PROFILE)
        rows = [r for r in report['calls'] if r['admission'].get('call_kind') == 'blr_got']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['admission']['symbol'], THROWING)
        self.assertEqual(report['omitted_calls'], 1)
        self.assertFalse(report['call_details_complete'])
        self.assertFalse(report['outcome_witnesses_complete'])
        self.assertEqual(report['got_counts']['selected_got_calls'], 2)
        self.assertEqual(report['status_counts'], {'unresolved': 1})
        self.assertEqual(report['reason_counts'], {'imported_callee_abi_unqualified': 1})

    def test_other_profiles_are_unchanged(self):
        images = [build_got_image()[0], build_got_image(include_chained=False)[0],
                  build_got_image(imports=(GotImport('_free', 1),))[0]]
        for data in images:
            image = image_of(data)
            for profile in OLDER_PROFILES + (BASE_PROFILE,):
                with self.subTest(profile=profile):
                    report = flow(image, profile=profile)
                    self.assertFalse(GOT_KEYS & set(report))
                    self.assertNotIn('got_callees_attribution_only', report['limitations'])
                    self.assertFalse([r for r in report['calls']
                                      if r['admission'].get('model_version') == 'swift-broad-got-callsite-v1'])

    def test_cli_json_and_text(self):
        from airs.cli import main
        data, _ = build_got_image()
        flags = ['--swift-profile', PROFILE, '--include-outcome-witnesses', '--include-error-regions',
                 '--validate-region-entries', '--include-structured-presentation']
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'got.macho'
            path.write_bytes(data)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(['swift-error-flow', str(path), *flags])
            self.assertEqual(code, 0)
            report = json.loads(out.getvalue())
            self.assertEqual((report['profile'], report['model_version']), (PROFILE, MODEL))
            self.assertEqual(report['got_counts']['selected_got_calls'], 1)
            rows = [r for r in report['calls'] if r['admission'].get('call_kind') == 'blr_got']
            self.assertEqual([(r['admission']['symbol'], r['admission']['slot_address']) for r in rows],
                             [(THROWING, GOT)])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(['swift-error-flow', str(path), *flags, '--format', 'text'])
            self.assertEqual(code, 0)
            text = out.getvalue()
            self.assertIn(PROFILE, text)
            self.assertIn('imported_callee_abi_unqualified', text)


class OwnedImportsGotFixtureTests(GotProfileTestCase):
    """Section 9 and 10 against expected-got.json (Apple tools only)."""

    @classmethod
    def setUpClass(cls):
        cls.expected = json.loads((FIXTURE / 'expected-got.json').read_text())
        cls.data = (FIXTURE / cls.expected['binary']).read_bytes()
        cls.image = parse_macho(cls.data, cls.expected['binary'], PROFILE_LIMITS[PROFILE])

    def test_expected_record_is_apple_tool_derived(self):
        self.assertEqual(hashlib.sha256(self.data).hexdigest(), self.expected['binary_sha256'])
        base = json.loads((FIXTURE / 'expected.json').read_text())
        self.assertEqual((self.expected['binary'], self.expected['binary_sha256']),
                         (base['binary'], base['binary_sha256']))
        commands = self.expected['derivation']['commands']
        for tool in ('otool -l', 'otool -Iv', 'otool -chained_fixups', 'dyld_info -fixup_chain_details',
                     'dyld_info -imports', 'objdump -d'):
            self.assertTrue(any(tool in c for c in commands), tool)
        self.assertEqual((self.expected['model'], self.expected['profile']), (GOT_MODEL, PROFILE))

    def test_table_matches_every_toolchain_slot(self):
        table = attribute_got_bindings(self.image)
        self.assertTrue(table.complete, table.reason)
        self.assertIsNone(table.reason)
        self.assertEqual(table.chained_fixups_status, 'decoded')
        self.assertEqual(dict(table.declined_slots), {})
        got = self.expected['got_section']
        label = got['segment'] + ',' + got['section']
        tables = self.expected['symbol_tables']
        cf = self.expected['chained_fixups']
        record_offset = cf['dataoff'] + cf['header']['starts_offset'] + cf['seg_info_offset'][
            cf['segment_record']['segment_index']]
        slots = self.expected['got_slots']
        self.assertEqual(sorted(table.bindings), [s['address'] for s in slots])
        self.assertEqual(table.counts(), {'got_slots': 35, 'agreeing_got_slots': 35, 'declined_got_slots': 0})
        for slot in slots:
            with self.subTest(slot=hex(slot['address'])):
                binding = table.bindings[slot['address']]
                self.assertEqual(
                    (binding.slot_section, binding.slot_index, binding.symbol, binding.symbol_index,
                     binding.library_ordinal, binding.library_path, binding.weak_import, binding.import_ordinal),
                    (label, slot['slot_index'], slot['symbol'], slot['symbol_index'], slot['lib_ordinal'],
                     slot['library_path'], slot['weak_import'], slot['import_ordinal']))
                provenance = binding.record()['provenance']
                self.assertEqual(provenance['indirect_entry_offset'],
                                 tables['indirectsymoff'] + 4 * slot['indirect_entry_index'])
                self.assertEqual(provenance['nlist_offset'], tables['symoff'] + 16 * slot['symbol_index'])
                chained = dict(provenance['chained'])
                self.assertEqual(chained.pop('chain_step'), slot['chain_member_index'])
                self.assertEqual(chained.pop('name_offset'),
                                 cf['dataoff'] + cf['header']['symbols_offset'] + slot['name_offset'])
                self.assertEqual(chained, {
                    'model': CHAINED_FIXUPS_MODEL, 'blob_offset': cf['dataoff'],
                    'segment_index': cf['segment_record']['segment_index'], 'segment_record_offset': record_offset,
                    'pointer_format': cf['segment_record']['pointer_format'], 'page_index': 0,
                    'page_start': cf['segment_record']['page_start'][0],
                    'member_slice_file_offset': slot['member_slice_file_offset'],
                    'member_container_file_offset': slot['member_slice_file_offset'], 'raw': slot['raw'],
                    'import_entry_offset': slot['import_entry_offset']})

    def test_every_census_site_classifies_as_recorded(self):
        table = attribute_got_bindings(self.image)
        functions = [f for f in self.image.functions if f.boundary_source == 'lc_function_starts']
        for site in self.expected['branch_sites']:
            pc = site.get('call_pc', site.get('pc'))
            with self.subTest(pc=hex(pc)):
                function = next(f for f in functions if f.start <= pc < f.end)
                found = table.classify(function, pc)
                if site['outcome'] == 'not_blr':
                    self.assertIsNone(found)
                elif site['outcome'] == 'declined':
                    self.assertEqual(found, ('declined', site['reason']))
                else:
                    self.assertEqual(found[0], 'attributed')
                    call = found[1]
                    self.assertEqual(
                        (call.call_pc, call.register, call.adrp_pc, call.ldr_pc, call.gap_adrp_to_ldr,
                         call.gap_ldr_to_blr, call.binding.slot_address, call.binding.symbol,
                         call.binding.library_path, call.binding.library_ordinal, call.binding.weak_import,
                         call.binding.import_ordinal),
                        (pc, site['register'], site['adrp_pc'], site['ldr_pc'], site['gap_adrp_to_ldr'],
                         site['gap_ldr_to_blr'], site['slot_address'], site['symbol'], site['library_path'],
                         site['library_ordinal'], site['weak_import'], site['import_ordinal']))
                    roles = [w['role'] for w in call.record()['provenance']['window_words']]
                    self.assertEqual(roles, ['adrp'] + ['gap'] * site['gap_adrp_to_ldr'] + ['ldr']
                                     + ['gap'] * site['gap_ldr_to_blr'] + ['blr'])

    def test_acceptance_counts_and_calls_relation(self):
        report = flow(self.image)
        base = flow(self.image, profile=BASE_PROFILE)
        self.assertProfileShape(report, base)
        self.assertTrue(report['got_bindings_complete'])
        self.assertIsNone(report['got_binding_reason'])
        self.assertEqual(report['chained_fixups_status'], 'decoded')
        self.assertEqual(report['got_counts'], self.expected['expected_counts'])
        self.assertEqual(report['got_decline_counts'], self.expected['expected_decline_counts'])
        self.assertEqual(report['got_slot_decline_counts'], {})
        attributed = {hex(s['call_pc']) for s in self.expected['branch_sites'] if s['outcome'] == 'attributed'}
        self.assertEqual(attributed, {'0x100000f40', '0x10000122c', '0x1000013c0'})
        removed = [r for r in base['calls'] if r['call_pc'] in attributed]
        self.assertEqual(len(removed), 3)
        self.assertEqual(report['calls'], [r for r in base['calls'] if r['call_pc'] not in attributed])
        self.assertEqual(report['observed_call_instructions'], base['observed_call_instructions'])
        self.assertEqual(report['selected_call_candidates'], base['selected_call_candidates'] - 3)
        removed_status = Counter(r['admission']['status'] for r in removed)
        removed_reason = Counter(r['admission']['reason'] for r in removed)
        self.assertEqual(Counter(report['status_counts']) + removed_status, Counter(base['status_counts']))
        self.assertEqual(Counter(report['reason_counts']) + removed_reason, Counter(base['reason_counts']))
        a, b = common(report), common(base)
        for key in SELECTION_KEYS:
            a.pop(key), b.pop(key)
        self.assertEqual(a, b)


if __name__ == '__main__':
    unittest.main()
