"""Owned EXTR class fields and conservative outside-class refusal reasons."""
import random
import unittest

import airs
from airs.analysis_models import CFG_MODELS
from airs.arm64 import ModelError
from airs.cfg import decode_instruction


class ExtractClassTests(unittest.TestCase):
    def test_valid_extract_fields(self):
        rows = (
            (0x13800000, 'wextr', (0, 31)),
            (0x93c00000, 'xextr', (0, 31, 32, 63)),
        )
        for form, kind, immediates in rows:
            for immediate in immediates:
                for rd in (0, 31):
                    for rn in (0, 31):
                        for rm in (0, 31):
                            word = form | (rm << 16) | (immediate << 10)
                            word |= (rn << 5) | rd
                            with self.subTest(word=hex(word)):
                                instruction = decode_instruction(word)
                                self.assertEqual(instruction.kind, kind)
                                self.assertEqual(instruction.rd, rd)
                                self.assertEqual(instruction.rn, rn)
                                self.assertEqual(instruction.rt2, rm)
                                self.assertEqual(instruction.immediate, immediate)

    def test_other_extract_forms_remain_invalid(self):
        forms = (
            0x13a00000, 0x13c00000, 0x13e00000,
            0x93800000, 0x93a00000, 0x93e00000,
        )
        for form in forms:
            for operands in (0, 0x001fffff):
                word = form | operands
                with self.subTest(word=hex(word)):
                    with self.assertRaises(ModelError) as caught:
                        decode_instruction(word)
                    self.assertEqual(caught.exception.code, 'invalid_extract_encoding')

    def test_w_extract_high_immediates_remain_invalid(self):
        for immediate in (32, 63):
            for rd in (0, 31):
                for rn in (0, 31):
                    for rm in (0, 31):
                        word = 0x13800000 | (rm << 16) | (immediate << 10)
                        word |= (rn << 5) | rd
                        with self.subTest(word=hex(word)):
                            with self.assertRaises(ModelError) as caught:
                                decode_instruction(word)
                            self.assertEqual(caught.exception.code, 'invalid_extract_encoding')

    def test_outside_extract_class_listed_words_are_unsupported(self):
        words = (
            0xf380001f, 0xf380003f, 0xf380803f, 0xf39fffff,
            0xf3a0001f, 0xf3a0003f, 0xf3a0803f, 0xf3bfffff,
            0x33800000, 0x33ffffff, 0x53800000, 0x53ffffff,
            0x73800000, 0x73ffffff, 0xb3800000, 0xb3ffffff,
            0xd3800000, 0xd3ffffff, 0xf3800000, 0xf3ffffff,
        )
        for word in words:
            with self.subTest(word=hex(word)):
                with self.assertRaises(ModelError) as caught:
                    decode_instruction(word)
                self.assertEqual(caught.exception.code, 'unsupported_instruction')

    def test_outside_extract_class_seeded_words_are_unsupported(self):
        generator = random.Random(51)
        for index in range(2000):
            sf = generator.randrange(2)
            opcode = generator.randrange(1, 4)
            free_bits = generator.getrandbits(23)
            word = 0x13800000 | (sf << 31) | (opcode << 29)
            word |= free_bits
            with self.subTest(index=index, word=hex(word)):
                with self.assertRaises(ModelError) as caught:
                    decode_instruction(word)
                self.assertEqual(caught.exception.code, 'unsupported_instruction')

    def test_current_analysis_model_identity(self):
        self.assertEqual(airs.ANALYSIS_MODEL_VERSION, 'arm64-bounded-extract-class-v51')

    def test_current_and_historical_cfg_identities(self):
        identities = (
            'arm64-bounded-extract-class-v51',
            'arm64-bounded-test-bit-branch-v50',
        )
        for identity in identities:
            with self.subTest(identity=identity):
                self.assertIn(identity, CFG_MODELS)
