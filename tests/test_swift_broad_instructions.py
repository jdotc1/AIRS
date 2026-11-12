import unittest
from airs.swift_broad_instructions import decode_instruction
from airs.arm64 import ModelError
from airs.swift_error_flow import decode_instruction as historical


class BroadInstructionTests(unittest.TestCase):
    def test_pc_relative_address_primitives_preserve_legacy_refusal(self):
        for word,kind,rd,immediate in ((0x90000000,'adrp',0,0),
                (0xb0000003,'adrp',3,4096),(0x100000a2,'adr',2,20),
                (0x10ffffe7,'adr',7,-4)):
            with self.subTest(word=hex(word)):
                i=decode_instruction(word,0x1234)
                self.assertEqual((i.kind,i.rd,i.immediate),(kind,rd,immediate))
                self.assertFalse(i.changes_sp)
                with self.assertRaises(ModelError):historical(word,0x1234)


class ScalarAndNarrowInstructionTests(unittest.TestCase):
    def test_retained_scalar_lowering_words(self):
        from airs.swift_broad_instructions import destination_register_bank
        cases = (
            (0x9e220100, 'scvtf_s_x', 0, 8, 0, 0, 'fp'),
            (0x9e620100, 'scvtf_d_x', 0, 8, 0, 0, 'fp'),
            (0x1e211001, 'fmov_s_imm', 1, 0, 0, 8, 'fp'),
            (0x1e611001, 'fmov_d_imm', 1, 0, 0, 8, 'fp'),
            (0x1e211800, 'fdiv_s', 0, 0, 1, 0, 'fp'),
            (0x1e611800, 'fdiv_d', 0, 0, 1, 0, 'fp'),
            (0x1e260008, 'fmov_w_s', 8, 0, 0, 0, 'gpr'),
            (0x1e270101, 'fmov_s_w', 1, 8, 0, 0, 'fp'),
            (0x9e670100, 'fmov_d_x', 0, 8, 0, 0, 'fp'),
            (0x1e212000, 'fcmp_s_reg', 0, 0, 1, 0, None),
            (0x9e380015, 'fcvtzs_x_s', 21, 0, 0, 0, 'gpr'))
        for word, kind, rd, rn, rt2, imm, bank in cases:
            with self.subTest(word=hex(word)):
                i = decode_instruction(word, 0x100)
                self.assertEqual((i.kind, i.rd, i.rn, i.rt2, i.immediate),
                                 (kind, rd, rn, rt2, imm))
                self.assertEqual(destination_register_bank(i), bank)
                self.assertFalse(i.changes_sp)
                with self.assertRaises(ModelError): historical(word, 0x100)

    def test_scalar_register_fields_and_frame_pointer_bank(self):
        from airs.swift_broad_instructions import GPR_DESTINATION_KINDS
        for base, kind in ((0x1e220000, 'scvtf_s_w'), (0x9e620000, 'scvtf_d_x'),
                           (0x1e380000, 'fcvtzs_w_s'), (0x9e780000, 'fcvtzs_x_d'),
                           (0x1e204000, 'fmov_s_reg'), (0x1e604000, 'fmov_d_reg'),
                           (0x9e660000, 'fmov_x_d'), (0x1e260000, 'fmov_w_s')):
            i = decode_instruction(base | 31 << 5 | 29)
            self.assertEqual((i.kind, i.rd, i.rn), (kind, 29, 31))
            self.assertEqual(i.changes_fp, kind in GPR_DESTINATION_KINDS)
        for word, kind in ((0x1e2023e8, 'fcmp_s_zero'), (0x1e6023e8, 'fcmp_d_zero')):
            i = decode_instruction(word)
            self.assertEqual((i.kind, i.rn, i.rt2), (kind, 31, 0))
        self.assertTrue(decode_instruction(0x1000001d).changes_fp)

    def test_narrow_memory_offsets_and_effects(self):
        cases = ((0x3900e3ff, 'wstrb', 31, 31, 56),
                 (0x39400008, 'wldrb', 8, 0, 0),
                 (0x79402fe0, 'wldrh', 0, 31, 22),
                 (0x781c83bf, 'wstrh', 31, 29, -56),
                 (0x781be3a8, 'wstrh', 8, 29, -66),
                 (0x790007fd, 'wstrh', 29, 31, 2),
                 (0x384ff3fd, 'wldrb', 29, 31, 255),
                 (0x785003fd, 'wldrh', 29, 31, -256))
        for word, kind, rd, rn, immediate in cases:
            with self.subTest(word=hex(word)):
                i = decode_instruction(word)
                self.assertEqual((i.kind, i.rd, i.rn, i.immediate, i.addressing),
                                 (kind, rd, rn, immediate, 'offset'))
                self.assertFalse(i.changes_sp)
                self.assertEqual(i.changes_fp, kind.startswith('wldr') and rd == 29)

    def test_neighboring_unsupported_forms_do_not_become_noops(self):
        # UCVTF, half FP, fixed point, lane FMOV, FCMPE, narrow writeback,
        # signed narrow loads and register-offset accesses remain refused.
        for word in (0x9e230100, 0x1ee22000, 0x9e020100, 0x9eaf0000,
                     0x1e212010, 0x38000400, 0x78000c00, 0x39800000,
                     0x38a06800, 0x1e211021, 0x1e201c00):
            with self.subTest(word=hex(word)):
                with self.assertRaises(ModelError): decode_instruction(word)


class AdditionalCompilerPrimitiveTests(unittest.TestCase):
    def test_selected_actual_arithmetic_memory_and_vector_words(self):
        from airs.swift_broad_instructions import destination_register_bank, MEMORY_WIDTHS
        cases = (
            (0x8b130113, 'xadd_reg', 19, 8, 19, 0, 'gpr'),
            (0x8b160014, 'xadd_reg', 20, 0, 22, 0, 'gpr'),
            (0x8b080260, 'xadd_reg', 0, 19, 8, 0, 'gpr'),
            (0x8b080273, 'xadd_reg', 19, 19, 8, 0, 'gpr'),
            (0xf9000816, 'xstr_raw', 22, 0, 0, 16, None),
            (0x3dc00000, 'qldr', 0, 0, 0, 0, 'fp'),
            (0x3d8007e0, 'qstr', 0, 31, 0, 16, None),
            (0xf81d83bf, 'xstur', 31, 29, 0, -40, None),
            (0xf81d03bf, 'xstur', 31, 29, 0, -48, None),
            (0xf81c83bf, 'xstur', 31, 29, 0, -56, None),
            (0xf81d83a0, 'xstur', 0, 29, 0, -40, None),
            (0xf81d03a1, 'xstur', 1, 29, 0, -48, None),
            (0xf81b83a8, 'xstur', 8, 29, 0, -72, None),
            (0xf85b83a8, 'xldur', 8, 29, 0, -72, 'gpr'),
            (0xf81c83a0, 'xstur', 0, 29, 0, -56, None),
            (0x0f0267e1, 'movi_2s_lsl24', 1, 0, 0, 0x5f, 'fp'))
        for word, kind, rd, rn, rt2, imm, bank in cases:
            with self.subTest(word=hex(word)):
                i = decode_instruction(word)
                self.assertEqual((i.kind, i.rd, i.rn, i.rt2, i.immediate),
                                 (kind, rd, rn, rt2, imm))
                self.assertEqual(destination_register_bank(i), bank)
                self.assertFalse(i.changes_sp)
        self.assertEqual({k: MEMORY_WIDTHS[k] for k in ('qstr', 'qldr', 'xstur', 'xldur')},
                         {'qstr': 16, 'qldr': 16, 'xstur': 8, 'xldur': 8})

    def test_new_fields_and_historical_base_descriptor_preservation(self):
        for word, kind, changes_fp in ((0xcb1f03fd, 'xsub_reg', True),
                                       (0x8b1f03ff, 'xadd_reg', False),
                                       (0xf940001d, 'xldr_raw', True),
                                       (0xf85003fd, 'xldur', True),
                                       (0x3dc003fd, 'qldr', False),
                                       (0x0f0767fd, 'movi_2s_lsl24', False)):
            i = decode_instruction(word)
            self.assertEqual(i.kind, kind)
            self.assertEqual(i.changes_fp, changes_fp)
            self.assertFalse(i.changes_sp)
        self.assertEqual(decode_instruction(0xf85003fd).immediate, -256)
        self.assertEqual(decode_instruction(0x0f0767fd).immediate, 255)
        for word in (0xf9000ff5, 0xf9400ff5, 0xf94003bd):
            self.assertEqual(decode_instruction(word), historical(word))
        for immediate in (0, 1, 65535):
            i = decode_instruction(0xd4200000 | immediate << 5)
            self.assertEqual((i.kind, i.immediate), ('brk', immediate))
            self.assertFalse(i.changes_fp or i.changes_sp)

    def test_new_primitive_exact_bounds(self):
        # Shifted arithmetic other than LSL#0, extended arithmetic with a reserved
        # shift above 4, unscaled Q, X writeback, MOVI .4s/other shifts/opcodes,
        # and HLT are out of scope. Extended ADD/SUB with shift 0-4 is modeled.
        for word in (0x8b080660, 0x8b480260, 0x8b281660,
                     0x3cc00000, 0xf8400400, 0xf8000c00,
                     0x4f0267e1, 0x0f0247e1, 0x2f0267e1, 0xd4400020):
            with self.subTest(word=hex(word)):
                with self.assertRaises(ModelError): decode_instruction(word)
