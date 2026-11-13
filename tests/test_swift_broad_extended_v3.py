"""Wiring tests for profile broad-extended-v3 (indirect target shape and value-witness admission).

Images are synthetic (tests/indirect_v3_image_helpers.py) plus the owned broad-imports fixture, which is
data and is never executed. The isolation hashes below were captured from the code before this profile
existed, on the same inputs; they show that every earlier profile still produces the same bytes.
"""
import contextlib
import functools
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import indirect_v3_image_helpers as helpers  # noqa: E402
from airs import analysis_models  # noqa: E402
from airs.cli import main  # noqa: E402
from airs.macho import parse_macho  # noqa: E402
from airs.report import dumps  # noqa: E402
from airs.swift_broad_flow import PROFILE_LIMITS, PROFILE_MODELS, recover_swift_broad_flow  # noqa: E402
from airs.swift_broad_text import render_swift_broad_text  # noqa: E402
from airs.swift_indirect_target_shape import CLASSES  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures' / 'swift-error-flow' / 'broad-imports' / 'OwnedImports.macho'
PROFILE = 'broad-extended-v3'
MODEL = 'swift-broad-error-flow-extended-v3'
EARLIER = ('broad-v1', 'broad-large-v1', 'broad-extended-v1', 'broad-imports-v1', 'broad-imports-got-v1',
           'broad-extended-v2')
ADMITTED_REASON = 'value_witness_abi_nonthrowing'
BASELINE = {
    'broad-v1/fixture': 'c0b60b0c21b0d5a206e2e4e3f22b126e55e848cfaf3f898e80c1579adeb46eab',
    'broad-v1/imported': '4bd27c94305310e6bac65cddd12d3afd10f901968186dfb24ce8f5cb0de99ba6',
    'broad-v1/runtime': '4f0d2e51d539bdbaf15be603d06b75827ce704f091d8c0da481f088631761046',
    'broad-v1/not_accessor': 'ea084ff8866a666ff70e79a732227a107b45a2ca2b3772b6109a70f7dba72463',
    'broad-v1/local': '773c30a37c58b3f74fc84bd8e88da295952372affab578ba2ea209601876271a',
    'broad-v1/unnamed': '944132989399fdf92cb5548633f45877a57e8be06d9f6e7f407e1ba52ceb9978',
    'broad-v1/closure': '1ab5fd9e45b9490b2f1b7bc5bebb1696fa15c101c7b2ac7cfffa13cbab1ceef8',
    'broad-v1/isa': 'c928e8806c1850681572f1d84611c03a75e4a71511add9dc1427c12ef0c4b7c8',
    'broad-v1/mixed': '141b94c4db39a9178168f8f2dface8491acdbd99ac75b9a8c88e989aed0c7578',
    'broad-large-v1/fixture': '25c4ca8a51e4035c189eb003803069276de48c0e3a0715bb14d77cc0b6a64430',
    'broad-large-v1/imported': '816c9d3e8341ac10f17ee3fa7cfa3cbf8b1e5e3d92aa13fdeb2d6e5ad989f379',
    'broad-large-v1/runtime': 'e9a94a517c24af2474ffef718254d190ea81c86d5fd3145e385f2a9f04adccdd',
    'broad-large-v1/not_accessor': 'e95fa5ed7a7f7c4f3f3a84501f23279f822fa1cc067959c83fb97de4d00d96d8',
    'broad-large-v1/local': '23dec1d3fc16814bb2070999bef406b8133099f1b3f455c7dbde2af285e5c2df',
    'broad-large-v1/unnamed': '60a029af2506929345d337a5ebe4253b318c9759a8a9e664756818cfa5674848',
    'broad-large-v1/closure': '6fc4e82a6a11aad23d32a065e07559bf0991015ad38c4758a0bdd61a30a86863',
    'broad-large-v1/isa': '3405c161d36ef80446e3f73ecb372e65ef601272eaa7b870e871d60a442eba1c',
    'broad-large-v1/mixed': 'e05ad2e3d16caf0ba68679d89cc969764fccbd494a99a6e8f8bb99486ec6ae9f',
    'broad-extended-v1/fixture': '97d7ebb6aa4cec97ab1b06b363c66f4760cebcef0c20bc2767fd55d046a26c8d',
    'broad-extended-v1/imported': 'dae0bc60a80bc8db17e2601d88f16adde85f761270ca60ddb3519b46311dd8f1',
    'broad-extended-v1/runtime': '4bf2bbcfac376c2a2d1aea93eb9b424fa49292e4900d1b3134a71373f6c228c1',
    'broad-extended-v1/not_accessor': 'c1b66af6d5e9b0af94b72da6651b7ae73d3baa94575cffe3ddc23ff75e0df277',
    'broad-extended-v1/local': 'c3247bd0c23937fc1ee568bc048df80decbf7d79f7922d45b1f53d8ac0c35986',
    'broad-extended-v1/unnamed': 'ce5a85bf7e411a99323170f46b7e189a69409fa755d6f33c6dec31816a723c3a',
    'broad-extended-v1/closure': '28bd94938993f5696626f897026652f2d7a588bc953c5e3e0331c60348681036',
    'broad-extended-v1/isa': '170f02370ba4fbbe7d59ae7e76de45a2d67e552a62fc97240d89fd4e5545d334',
    'broad-extended-v1/mixed': 'dd7bc9f371f58a71eba2cb1f646496dbbc6aab99b24eb74a6b63ea011be348e1',
    'broad-imports-v1/fixture': '29d745c4f880e51b6a24f02019be12f212523ebd31f19662b793860985e9a5e0',
    'broad-imports-v1/imported': '48600a3587eb49ac3ff3eac146ee93f47126ccddc3a841d1f8799750fbfe56a6',
    'broad-imports-v1/runtime': '525152918323b515c590410db5ebaab825f2fa51d2c77205710952c0ea868a9e',
    'broad-imports-v1/not_accessor': '5c0f7eb02082b0d21d2574478c44cfa41d9fdf18d813219f5a3ed8dac7bca4d3',
    'broad-imports-v1/local': '53f6bf35a9e0092a25f0985a26f38cdf8d7a45feb7b6edc87b102cdef1b7cad0',
    'broad-imports-v1/unnamed': 'f3bcb835a34b75be82cfc8f34f01779275f814f53315e8f201c7e13041d683f7',
    'broad-imports-v1/closure': '5be58141856df4350ddc6c0cfff62b1837e18e7e3e73ca3906581fb0a0653c6d',
    'broad-imports-v1/isa': 'aab0a5728916c7eb2ae3d8ecd95933312e41b24fb72a9055c8984aa4bbc800f4',
    'broad-imports-v1/mixed': '7dd3d8e2abd81d3183d82ea6af381f587c11b3171ae1e6fbae9535d0483355b6',
    'broad-imports-got-v1/fixture': 'db5765e3cc1cf729e1a96e23585b7efd8331661bd1a4736f8949fab6346c4b79',
    'broad-imports-got-v1/imported': '64df641c670a72903f86c308f3ccadbdd0f6ef30f5c680443d557e8514d34d29',
    'broad-imports-got-v1/runtime': '6fd2fe3ce441354dfbef8a3768129ffc02597c881c817396ba16592036526805',
    'broad-imports-got-v1/not_accessor': '00afe2f8dfa1d0aa67961cdae28a13a1b3d8296f1c173733d0c16160110cb99c',
    'broad-imports-got-v1/local': 'b9403626a1c40d2c3b86c0ba6db1eb552e5590c01857ddf588262bf5a3b159e8',
    'broad-imports-got-v1/unnamed': 'b500cd1be199fb659609c3c71ee486f062ce42f08489670371097c3acf4dcd4c',
    'broad-imports-got-v1/closure': '7b6f06d672b221410366e70e6a738c523403b8b630b70669e600aa51a57b4dc8',
    'broad-imports-got-v1/isa': '11cdbb44aeecff1293043396ef00282b144df1a5fd4d5ac168ed9ef2c88ecd58',
    'broad-imports-got-v1/mixed': '56e77e5fc5baf41653555b3b8a3b10cf7ca895bf42b6c7aaae0460e97c88f397',
    'broad-extended-v2/fixture': '1739b3b8f0c604bd392812797a0be45f1e5eda2290efe4323298f9abf0b24dc9',
    'broad-extended-v2/imported': '0d97ae411e0d75f078d18ee3aaf7efff1af70ab3615d5e7e06c5ac41b6b98903',
    'broad-extended-v2/runtime': '3db68b24b52ee8ceffde201f8231cda3e44a97cc647e82fa4e26531ee7d3951b',
    'broad-extended-v2/not_accessor': 'a5542746123f43904c944beb7f9bd4c26a4e4a600783f43ab2c58303e22b59bd',
    'broad-extended-v2/local': '3dd51058a757828499a731dbfe60990bef230abb7773feeb5811d831a528a17f',
    'broad-extended-v2/unnamed': 'c2880dbca912e05ae8d762889108f8bffd411e64a37a7660a9630185d27ae943',
    'broad-extended-v2/closure': '825624c446c0443b96660bd2c66c75f08e450a0910dfed23ad7f061263b047e6',
    'broad-extended-v2/isa': '9262062fd6ca61d78651419da544371a1f986295adf5d39ec5bf0a1ece6a4608',
    'broad-extended-v2/mixed': '7c841a48b4442962ec64da65d3c9ce1cc85146861759d3b5df542239dfbdabc0',
}


def image(key):
    return FIXTURE.read_bytes() if key == 'fixture' else helpers.IMAGES[key]()


@functools.lru_cache(maxsize=None)
def report(profile, key):
    return recover_swift_broad_flow(parse_macho(image(key), limits=PROFILE_LIMITS[profile]), profile=profile)


def digest(profile, key):
    return hashlib.sha256(dumps(report(profile, key)).encode()).hexdigest()


def rows_by_pc(rep):
    return {row['call_pc']: row for row in rep['calls']}


def witness_rows(rep):
    return [row for row in rep['calls'] if 'indirect_target_shape' in row]


class ProfileWiringTests(unittest.TestCase):
    def test_pair_is_registered(self):
        self.assertEqual(PROFILE_MODELS[PROFILE], MODEL)
        self.assertIn((MODEL, PROFILE), analysis_models.SWIFT_BROAD_PAIRS)
        self.assertEqual(analysis_models.SWIFT_INDIRECT_TARGET_SHAPE_MODEL, 'swift-indirect-target-shape-v1')
        self.assertEqual(analysis_models.SWIFT_VALUE_WITNESS_ADMISSION_MODEL, 'swift-value-witness-admission-v1')
        self.assertEqual(PROFILE_LIMITS[PROFILE], PROFILE_LIMITS['broad-extended-v2'])

    def test_report_envelope(self):
        rep = report(PROFILE, 'imported')
        self.assertEqual((rep['model_version'], rep['profile']), (MODEL, PROFILE))
        self.assertEqual(rep['indirect_target_shape_model'], 'swift-indirect-target-shape-v1')
        self.assertEqual(rep['value_witness_admission_model'], 'swift-value-witness-admission-v1')
        for key in ('caller_error_test_counts', 'got_counts', 'import_stub_counts'):
            self.assertIn(key, rep)
        self.assertIn('indirect_target_shape_does_not_claim_callee_behaviour', rep['limitations'])

    def test_cli_json_and_text(self):
        flags = ['--include-outcome-witnesses', '--include-error-regions', '--validate-region-entries',
                 '--include-structured-presentation']
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'owned.macho'
            path.write_bytes(image('mixed'))
            for fmt, expected in (('json', MODEL), ('text', 'Value-witness admission')):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = main(['swift-error-flow', str(path), '--swift-profile', PROFILE, *flags, '--format', fmt])
                self.assertEqual(code, 0)
                self.assertIn(expected, out.getvalue())
            self.assertIn('value witness admitted "True"', out.getvalue())
            self.assertIn('indirect target "unknown"', out.getvalue())


class RecordTests(unittest.TestCase):
    def check_shape(self, shape):
        self.assertEqual(shape['model'], 'swift-indirect-target-shape-v1')
        self.assertIn(shape['class'], CLASSES)
        self.assertIs(shape['claims_callee_behaviour'], False)
        self.assertRegex(shape['site_pc'], r'^0x[0-9a-f]+$')
        for entry in shape['deciding_instructions']:
            self.assertRegex(entry['pc'], r'^0x[0-9a-f]+$')
            self.assertRegex(entry['word'], r'^0x[0-9a-f]{8}$')
        json.dumps(shape)

    def test_imported_accessor_is_admitted_and_leaves_the_unresolved_set(self):
        for key, kind, symbol in (('imported', 'imported_metadata_accessor_call', helpers.IMPORTED_ACCESSOR),
                                  ('runtime', 'runtime_metadata_call', helpers.RUNTIME_METADATA),
                                  ('local', 'metadata_accessor_call', '_$sSiMa')):
            with self.subTest(key=key):
                rep = report(PROFILE, key)
                (row,) = witness_rows(rep)
                self.check_shape(row['indirect_target_shape'])
                self.assertEqual((row['indirect_target_shape']['class'], row['indirect_target_shape']['slot_offset']),
                                 ('value_witness', 8))
                witness = row['value_witness_admission']
                self.assertEqual((witness['admitted'], witness['provenance_kind'], witness['symbol']),
                                 (True, kind, symbol))
                self.assertIsNone(witness['first_failing_condition'])
                self.assertIs(witness['claims_callee_behaviour'], False)
                self.assertEqual(row['admission']['status'], 'declined')
                self.assertEqual(row['admission']['reason'], ADMITTED_REASON)
                self.assertEqual(rep['reason_counts'][ADMITTED_REASON], 1)
                self.assertEqual(rep['value_witness_admission_counts'], {'admitted': 1, 'refused': 0})
                self.assertEqual(rep['value_witness_refusal_condition_counts'], {})
                self.assertNotIn('indirect_target_unresolved', rep['reason_counts'])
                self.assertEqual(rep['status_counts'].get('unresolved', 0), 1 if key == 'local' else 0)

    def test_metadata_callee_is_recomputed_from_the_recorded_bl(self):
        row = witness_rows(report(PROFILE, 'imported'))[0]
        word = next(e for e in row['indirect_target_shape']['deciding_instructions']
                    if e['role'] == 'metadata_call_result')
        self.assertTrue(int(word['word'], 16) & 0xfc000000 == 0x94000000)
        self.assertEqual(row['value_witness_admission']['metadata_callee_pc'], '0x100001014')

    def test_refusals_keep_the_row_as_in_v2_and_add_both_records(self):
        expected = {'not_accessor': (2, 'runtime_symbol_not_allowlisted'), 'unnamed': (2, 'grammar_invalid_input'),
                    'isa': (2, 'isa_is_not_proven_swift_metadata'), 'closure': (1, 'base_entry_register_x20')}
        for key, (condition, reason) in expected.items():
            with self.subTest(key=key):
                rep = report(PROFILE, key)
                (row,) = witness_rows(rep)
                self.check_shape(row['indirect_target_shape'])
                witness = row['value_witness_admission']
                self.assertEqual((witness['admitted'], witness['first_failing_condition'], witness['reason']),
                                 (False, condition, reason))
                self.assertEqual((row['admission']['status'], row['admission']['reason']),
                                 ('unresolved', 'indirect_target_unresolved'))
                self.assertEqual(rep['value_witness_admission_counts'], {'admitted': 0, 'refused': 1})
                self.assertEqual(rep['value_witness_refusal_condition_counts'], {str(condition): 1})
                self.assertNotIn(ADMITTED_REASON, rep['reason_counts'])

    def test_class_counts_cover_every_row_with_a_record(self):
        rep = report(PROFILE, 'mixed')
        self.assertEqual(rep['indirect_target_shape_counts'], {'unknown': 1, 'value_witness': 1})
        self.assertEqual(rep['value_witness_admission_counts'], {'admitted': 1, 'refused': 1})
        self.assertEqual(rep['value_witness_refusal_condition_counts'], {'1': 1})
        self.assertEqual(sum(rep['indirect_target_shape_counts'].values()), len(witness_rows(rep)))
        self.assertEqual(rep['status_counts'], {'declined': 1, 'unresolved': 1})

    def test_tier_one_changes_no_status_reason_or_count(self):
        # Strip every v3 addition from a v3 report with no admitted site; v2 on the same bytes must equal it.
        for key in ('not_accessor', 'unnamed', 'isa', 'closure'):
            with self.subTest(key=key):
                v3 = json.loads(dumps(report(PROFILE, key)))
                v2 = json.loads(dumps(report('broad-extended-v2', key)))
                for row in v3['calls']:
                    row.pop('indirect_target_shape'), row.pop('value_witness_admission')
                for name in ('indirect_target_shape_model', 'value_witness_admission_model',
                             'indirect_target_shape_counts', 'value_witness_admission_counts',
                             'value_witness_refusal_condition_counts', 'analysis_work'):
                    v3.pop(name)
                v2.pop('analysis_work')
                v3['limitations'] = [x for x in v3['limitations'] if x not in (
                    'indirect_target_shape_does_not_claim_callee_behaviour',
                    'value_witness_admission_by_abi_with_recorded_provenance')]
                v3['model_version'], v3['profile'] = v2['model_version'], v2['profile']
                self.assertEqual(v3, v2)

    def test_admission_changes_only_the_admitted_row(self):
        v3 = json.loads(dumps(report(PROFILE, 'mixed')))
        v2 = json.loads(dumps(report('broad-extended-v2', 'mixed')))
        self.assertEqual([r['call_pc'] for r in v3['calls']], [r['call_pc'] for r in v2['calls']])
        changed = [a['call_pc'] for a, b in zip(v3['calls'], v2['calls'])
                   if (a['admission']['status'], a['admission']['reason']) != (b['admission']['status'], b['admission']['reason'])]
        self.assertEqual(changed, ['0x10000100c'])
        self.assertEqual(v2['calls'][0]['admission']['reason'], 'indirect_target_unresolved')

    def test_text_rendering_lists_both_records(self):
        text = render_swift_broad_text(report(PROFILE, 'mixed'))
        for line in ('indirect_target_shape_counts.', 'value_witness_admission_counts.', 'value witness admitted "True"',
                     'value witness admitted "False"', ADMITTED_REASON):
            self.assertIn(line, text)
        self.assertNotIn('Traceback', text)


class FixtureTests(unittest.TestCase):
    """The owned broad-imports example: four value-witness sites that the GOT screen declines."""
    SITES = ('0x100000cdc', '0x100000f9c', '0x1000012a4', '0x100001438')

    def test_four_got_base_not_adrp_declines_carry_records(self):
        rep = report(PROFILE, 'fixture')
        self.assertEqual(rep['got_decline_counts'].get('got_base_not_adrp'), 4)
        rows = rows_by_pc(rep)
        for site in self.SITES:
            with self.subTest(site=site):
                self.assertEqual(rows[site]['indirect_target_shape']['class'], 'value_witness')
                self.assertIs(rows[site]['indirect_target_shape']['claims_callee_behaviour'], False)
        admitted = [s for s in self.SITES if rows[s]['value_witness_admission']['admitted']]
        self.assertEqual(admitted, ['0x100000f9c'])
        self.assertEqual(rows['0x100000f9c']['admission']['reason'], ADMITTED_REASON)
        self.assertEqual(rows['0x100000f9c']['value_witness_admission']['symbol'], '_$sSS10FoundationE8EncodingVMa')
        refused = {s: rows[s]['value_witness_admission']['reason'] for s in self.SITES if s != '0x100000f9c'}
        self.assertEqual(refused, {'0x100000cdc': 'metadata_stack_transport_not_admitted',
                                   '0x1000012a4': 'direct_target_symbol_missing',
                                   '0x100001438': 'direct_target_symbol_missing'})

    def test_every_unresolved_indirect_row_has_both_records_and_counts_agree(self):
        rep = report(PROFILE, 'fixture')
        for row in rep['calls']:
            if row['admission']['reason'] in ('indirect_target_unresolved', ADMITTED_REASON):
                self.assertIn('indirect_target_shape', row)
                self.assertIn('value_witness_admission', row)
        records = witness_rows(rep)
        self.assertEqual(sum(rep['indirect_target_shape_counts'].values()), len(records))
        self.assertEqual(sum(rep['value_witness_admission_counts'].values()), len(records))
        self.assertEqual(rep['value_witness_admission_counts']['admitted'], rep['reason_counts'][ADMITTED_REASON])
        self.assertEqual(sum(rep['value_witness_refusal_condition_counts'].values()),
                         rep['value_witness_admission_counts']['refused'])

    def test_only_the_admitted_site_changes_against_v2(self):
        v3, v2 = report(PROFILE, 'fixture'), report('broad-extended-v2', 'fixture')
        self.assertEqual([r['call_pc'] for r in v3['calls']], [r['call_pc'] for r in v2['calls']])
        changed = [a['call_pc'] for a, b in zip(v3['calls'], v2['calls'])
                   if (a['admission']['status'], a['admission']['reason']) != (b['admission']['status'], b['admission']['reason'])]
        self.assertEqual(changed, ['0x100000f9c'])
        self.assertEqual(v3['observed_call_instructions'], v2['observed_call_instructions'])
        self.assertEqual(v3['selected_call_candidates'], v2['selected_call_candidates'])
        self.assertEqual(v3['got_decline_counts'], v2['got_decline_counts'])
        self.assertEqual(v3['caller_error_test_counts'], v2['caller_error_test_counts'])


class IsolationTests(unittest.TestCase):
    def test_earlier_profiles_are_byte_identical_to_the_captured_baseline(self):
        for profile in EARLIER:
            for key in ('fixture', *helpers.IMAGES):
                with self.subTest(profile=profile, image=key):
                    self.assertEqual(digest(profile, key), BASELINE[profile + '/' + key])

    def test_earlier_profiles_gain_no_indirect_fields(self):
        for profile in EARLIER:
            for key in ('fixture', 'mixed'):
                with self.subTest(profile=profile, image=key):
                    rep = report(profile, key)
                    for name in ('indirect_target_shape_model', 'value_witness_admission_model',
                                 'indirect_target_shape_counts', 'value_witness_admission_counts'):
                        self.assertNotIn(name, rep)
                    for row in rep['calls']:
                        self.assertNotIn('indirect_target_shape', row)
                        self.assertNotIn('value_witness_admission', row)
                    self.assertNotIn(ADMITTED_REASON, rep['reason_counts'])

    def test_earlier_profiles_cannot_be_asked_for_the_new_model(self):
        self.assertEqual(sorted(p for p, m in PROFILE_MODELS.items() if m == MODEL), [PROFILE])


if __name__ == '__main__':
    unittest.main()
