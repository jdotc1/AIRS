"""Deterministic generated-word inventory tests; no external tools."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('words', ROOT / 'scripts/arm64-oracle-words.py')
W = importlib.util.module_from_spec(spec)
spec.loader.exec_module(W)


class WordsTests(unittest.TestCase):
    def test_deterministic_bytes_and_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'words.s'
            self.assertEqual(W.main(['--out', str(out)]), 0)
            first = out.read_bytes()
            self.assertEqual(W.main(['--out', str(out), '--overwrite']), 0)
            self.assertEqual(first, out.read_bytes())
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(W.main(['--out', str(out)]), 2)
            values = [int(line[8:], 16) for line in first.splitlines()]
            self.assertEqual(values, sorted(set(values)))
            state = W.GENERATOR_SEED
            expected = []
            for _ in range(16384):
                state = (state * 1664525 + 1013904223) % (2 ** 32)
                expected.append(state)
            self.assertTrue(set(expected) <= set(values))

    def test_every_derived_kind_seeded(self):
        inventory = W.inventory()
        self.assertEqual({d: len(k) for d, (k, _) in inventory.items()}, {'cfg': 129, 'linear': 10})
        self.assertEqual(set(W.SEEDS), set().union(*(k for k, _ in inventory.values())))
        h = W.harness()
        for kind, word in W.SEEDS.items():
            self.assertEqual(h.cfg.decode_instruction(word).kind, kind)
        linear = set()
        for word in W.SEEDS.values():
            try:
                linear.add(h.arm64.decode_instruction(word).kind)
            except h.arm64.ModelError:
                pass
        self.assertEqual(linear, inventory['linear'][0])

    def test_required_words_and_all_mutations(self):
        words = set(W.generate_words())
        self.assertTrue(set(W.REQUIRED_WORDS) <= words)
        for word in W.SEEDS.values():
            self.assertIn(word, words)
            for bit in range(32):
                self.assertIn(word ^ (1 << bit), words)
            for shift in (0, 5, 10, 16):
                for reg in (0, 1, 29, 30, 31):
                    self.assertIn((word & ~(31 << shift)) | (reg << shift), words)

    def test_missing_and_unknown_seeds_refused(self):
        seeds = dict(W.SEEDS)
        del seeds['ret']
        with self.assertRaisesRegex(ValueError, 'missing=ret'):
            W.generate_words(seeds)
        with self.assertRaisesRegex(ValueError, 'unknown=bogus'):
            W.generate_words({**W.SEEDS, 'bogus': 0})
        with mock.patch.object(W, 'SEEDS', seeds), contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(W.main(['--out', 'unused']), 2)
        self.assertIn('ret', error.getvalue())
