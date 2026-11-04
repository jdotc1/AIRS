"""Adjacent canonical X CMP zero + EQ/NE edges; handler gates stay closed."""
import unittest
from test_swift_error_flow import image,BASE
from airs.swift_error_flow import recover_swift_error_flow


def compare(register=21):return 0xf100001f | (register<<5)
def branch(words=3,condition=0):return 0x54000000 | ((words&0x7ffff)<<5) | condition

class CompareZeroFirstTests(unittest.TestCase):
    def test_x_compare_zero_equal_branch_recovers_selected_edges(self):
        value=recover_swift_error_flow(image((compare(),branch())))
        call=value['calls'][0]
        self.assertEqual(call['status'],'recovered_candidate')
        self.assertEqual(call['comparison_pc'],hex(BASE+4))
        self.assertEqual(call['test_pc'],hex(BASE+8))
        self.assertEqual((call['success_pc'],call['error_pc']),(hex(BASE+20),hex(BASE+12)))
        self.assertEqual(call['test_kind'],'cmp_zero_bcond')
        self.assertEqual(call['test_condition'],'eq')

class CompareZeroBoundaryTests(unittest.TestCase):
    def call(self, words, **options):
        return recover_swift_error_flow(image(words), **options)['calls'][0]

    def test_ne_reverses_edges(self):
        call = self.call((compare(), branch(condition=1)))
        self.assertEqual((call['success_pc'], call['error_pc']), (hex(BASE+12), hex(BASE+20)))
        self.assertEqual(call['test_condition'], 'ne')

    def test_live_full_width_copy(self):
        call = self.call((0xaa1503f3, compare(19), branch()))
        self.assertEqual(call['status'], 'recovered_candidate')
        self.assertEqual(call['tested_register'], 'x19')

    def test_noncanonical_comparisons_decline(self):
        for word in (compare(20), compare(31), compare() ^ 0x80000000,
                     compare() | 0x1000, compare() | 0x400000, compare() & ~1):
            with self.subTest(word=hex(word)):
                self.assertNotEqual(self.call((word, branch()))['status'], 'recovered_candidate')

    def test_only_adjacent_eq_ne(self):
        for words in ((compare(), 0xd503201f, branch()),
                      (compare(), 0xaa1503f3, branch()),
                      (compare(), compare(), branch()),
                      *((compare(), branch(condition=n)) for n in range(2,16)),
                      (compare(), branch() | 0x10)):
            with self.subTest(words=words):
                self.assertNotEqual(self.call(words)['status'], 'recovered_candidate')

    def test_invalid_successor_declines(self):
        for delta in (-2, 0, 1, 100):
            with self.subTest(delta=delta):
                self.assertNotEqual(self.call((compare(), branch(delta)))['status'], 'recovered_candidate')

    def test_postcall_budget(self):
        call = self.call((*(0xd503201f,)*6, compare(), branch(), *(0xd503201f,)*4))
        self.assertEqual(call['status'], 'recovered_candidate')
        call = self.call((*(0xd503201f,)*7, compare(), branch(), *(0xd503201f,)*4))
        self.assertNotEqual(call['status'], 'recovered_candidate')

    def test_downstream_gates_remain_closed(self):
        call = self.call((compare(), branch()), include_error_regions=True,
                         validate_region_entries=True, include_structured_presentation=True)
        self.assertEqual(call['error_region']['reason'], 'error_region_instruction_unmodeled')
        self.assertNotEqual(call['error_region']['status'], 'structural_region_candidate')
        self.assertNotEqual(call['return_choice']['status'], 'structural_choice_candidate')

class CompareZeroPresentationTests(unittest.TestCase):
    def test_text_exposes_words_and_withheld_plan(self):
        from airs.swift_error_text import render_swift_error_text
        value = recover_swift_error_flow(image((compare(), branch())),
            include_error_regions=True, validate_region_entries=True,
            include_structured_presentation=True)
        text = render_swift_error_text(value)
        for expected in ('comparison_pc', 'cmp_zero_bcond', 'test_condition',
                         '0xf10002bf', '0x54000060',
                         'error_region_instruction_unmodeled',
                         'Structured plan: withheld', 'Source reconstruction: disabled'):
            self.assertIn(expected, text)

    def test_cli_retains_selected_edge_evidence(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from airs.cli import main
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-compare-zero-edges'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'
            source.write_bytes(image((compare(), branch(condition=1))).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source)])
            self.assertEqual(status, 0)
            value = json.loads(output.getvalue())
            self.assertEqual(value['calls'][0]['test_condition'], 'ne')
            self.assertTrue(any('flag-entry' in item for item in value['limitations']))
