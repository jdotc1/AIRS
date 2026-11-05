"""New authored repair-two primitives; no saved compiler unit is evaluated."""
import unittest
from airs.arm64 import ModelError
from airs.swift_broad_instructions import decode_instruction, destination_register_bank
from airs.swift_error_flow import decode_instruction as historical
from airs import swift_outcome_values as v
from dataclasses import replace


class RepairTwoDescriptorTests(unittest.TestCase):
    def test_new_memory_width_bank_and_address_modes(self):
        cases=(
            (0xb9000000|(5<<10)|(9<<5)|7,'wstr_raw',7,9,20,'offset',None),
            (0xb9400000|(3<<10)|(29<<5)|4,'wldr_raw',4,29,12,'offset','gpr'),
            (0xb8000000|(0x1f7<<12)|(29<<5)|5,'wstur',5,29,-9,'offset',None),
            (0xb8400000|(0x100<<12)|(29<<5)|6,'wldur',6,29,-256,'offset','gpr'),
            (0xbd000000|(2<<10)|(31<<5)|21,'sstr',21,31,8,'offset',None),
            (0xbd400000|(3<<10)|(31<<5)|21,'sldr',21,31,12,'offset','fp'),
            (0xfc000000|(0x1f0<<12)|(29<<5)|21,'dstr',21,29,-16,'offset',None),
            (0xfc400000|(0xff<<12)|(29<<5)|29,'dldr',29,29,255,'offset','fp'),
            (0xf8000c00|(0x1e0<<12)|(31<<5)|19,'xstr',19,31,-32,'pre',None),
            (0xf8400400|(32<<12)|(31<<5)|19,'xldr_post',19,31,32,'post',None))
        for word,kind,rd,rn,offset,mode,bank in cases:
            with self.subTest(kind=kind,word=hex(word)):
                decoded=decode_instruction(word)
                self.assertEqual((decoded.kind,decoded.rd,decoded.rn,decoded.immediate,decoded.addressing),(kind,rd,rn,offset,mode))
                self.assertEqual(destination_register_bank(decoded),bank)
                self.assertEqual(decoded.changes_sp,mode in ('pre','post'))
                self.assertFalse(decoded.changes_fp)
        self.assertTrue(decode_instruction(0xf8400400|(8<<12)|(31<<5)|29).changes_fp)
        self.assertTrue(decode_instruction(0xf8000c00|(8<<12)|(29<<5)|3).changes_fp)
        self.assertEqual(decode_instruction(0xb90003e7).kind,'wstr')

    def test_extended_and_w_register_arithmetic_fields_reserved_controls(self):
        for option,name in enumerate(('uxtb','uxth','uxtw','uxtx','sxtb','sxth','sxtw','sxtx')):
            word=0x8b200000|(7<<16)|(option<<13)|(4<<10)|(31<<5)|29
            decoded=decode_instruction(word)
            self.assertEqual((decoded.kind,decoded.rd,decoded.rn,decoded.rt2,decoded.immediate,decoded.addressing),
                ('xadd_ext',29,31,7,4,name))
            self.assertTrue(decoded.changes_fp);self.assertFalse(decoded.changes_sp)
        self.assertTrue(decode_instruction(0xcb200000|(3<<13)|(1<<5)|31).changes_sp)
        for word,kind in ((0x0b010100,'wadd_reg'),(0x4b020128,'wsub_reg')):
            decoded=decode_instruction(word)
            self.assertEqual(decoded.kind,kind);self.assertEqual(decoded.addressing,'lsl');self.assertEqual(decoded.immediate,0)
            with self.assertRaises(ModelError):historical(word)
        for word in (0x8b201400,0x0b202000,0xb9800000,0xf8000800,0xbc000c00,
                     0xf8400400|(9<<5)|9,0xf8000c00|(9<<5)|9,0x0b008000):
            with self.subTest(word=hex(word)),self.assertRaises(ModelError):decode_instruction(word)


class RepairTwoValueTests(unittest.TestCase):
    def step(self,state,word):
        result=v.transfer_swift_value(state,decode_instruction(word))
        self.assertEqual(result.status,'resolved',result.reason)
        return result.state

    def test_word_memory_truncates_and_unknown_load_kills_origin(self):
        state=v.initial_state({7:v.Literal(0x123456789,64),21:v.RegisterCopy('error',64)})
        state=self.step(state,0xd10083ff)  # SUB sp,sp,#32
        state=self.step(state,0x910003e9)  # ADD x9,sp,#0
        state=self.step(state,0xb9000127)  # STR w7,[x9]
        state=self.step(state,0xb9400135)  # LDR w21,[x9]
        self.assertEqual(state.read_register(21),v.Literal(0x23456789,64))
        self.assertEqual([(c.slot,c.width) for c in state.stack],[(-32,32)])
        state=self.step(state,0xb8400155)  # LDUR w21,[x10] unknown base
        self.assertEqual(state.read_register(21),v.Unknown())
        state=self.step(state,0xb800015f)  # STUR wzr,[x10] invalidates frame cells
        self.assertFalse(state.stack)

    def test_scalar_fp_store_invalidates_without_same_numbered_gpr_value(self):
        original=v.RegisterCopy('original error',64)
        state=v.initial_state({21:original,29:v.Literal(123,64)})
        state=self.step(state,0xd10083ff)
        state=self.step(state,0xf90003f5)  # STR x21,[sp]
        for fp_store in (0xbd0003f5,0xfd0003f5,0xfc0003f5):
            after=self.step(state,fp_store)
            self.assertFalse(after.stack)
            self.assertEqual(after.read_register(21),original)
            loaded=self.step(after,0xf94003f3)
            self.assertEqual(loaded.read_register(19),v.Unknown())
        for fp_load in (0xbd4003f5,0xfd4003fd,0xfc4003fd):
            after=self.step(state,fp_load)
            self.assertEqual(after.read_register(21),original)
            self.assertEqual(after.read_register(29),v.Literal(123,64))
            self.assertEqual(after.stack,state.stack)

    def test_shifted_arithmetic_width_flags_zero_and_symbolic_inputs(self):
        state=replace(v.initial_state({8:v.Literal(5,64),9:v.Literal(0xfffffffe,64),
                                      21:v.RegisterCopy('error',64)}),sp_offset=-24)
        # SUBS W10,W8,W9,ASR#1 => 5-(-1), with W write zero-extension.
        after=self.step(state,0x6b800000|(9<<16)|(1<<10)|(8<<5)|10)
        self.assertEqual(after.read_register(10),v.Literal(6,64))
        # CMP X8,X9,LSR#1 discards result; SP and independent origin preserved.
        after=self.step(after,0xeb400000|(9<<16)|(1<<10)|(8<<5)|31)
        self.assertEqual(after.sp_offset,-24)
        self.assertEqual(after.read_register(21),state.read_register(21))
        after=self.step(after,0x0b000000|(9<<16)|(8<<5)|0)
        self.assertEqual(after.read_register(0),v.Literal(3,64))
        after=self.step(after,0x0a000000|(9<<16)|(8<<5)|1)
        self.assertEqual(after.read_register(1),v.Literal(4,64))
        after=self.step(after,0xab000000|(8<<16)|(21<<5)|21)
        self.assertIsInstance(after.read_register(21),v.Derived)
        self.assertNotEqual(after.read_register(21),state.read_register(21))
        invalid=replace(decode_instruction(0x6b800000|(9<<16)|(8<<5)|10),immediate=32)
        refused=v.transfer_swift_value(state,invalid)
        self.assertEqual(refused.status,'unresolved');self.assertEqual(refused.state,state)

    def test_extended_add_signed_inputs_and_sp_are_distinct(self):
        state=replace(v.initial_state({8:v.Literal(0xffffffff,64),9:v.Literal(10,64)}),sp_offset=-64)
        # ADD x10,x9,w8,SXTW#2 => 10-4
        after=self.step(state,0x8b200000|(8<<16)|(6<<13)|(2<<10)|(9<<5)|10)
        self.assertEqual(after.read_register(10),v.Literal(6,64))
        # ADD x11,sp,w8,SXTW#0 tracks entry-sp -65, not integer zero+input.
        after=self.step(after,0x8b200000|(8<<16)|(6<<13)|(31<<5)|11)
        self.assertEqual(after.read_register(11),v.Derived('entry_sp_offset',(v.Literal((1<<64)-65,64),),64))
        # ADD sp,sp,xzr,UXTX keeps SP known; unknown x12 then loses frame identity.
        after=self.step(after,0x8b200000|(31<<16)|(3<<13)|(31<<5)|31)
        self.assertEqual(after.sp_offset,-64)
        after=self.step(after,0x8b200000|(12<<16)|(3<<13)|(31<<5)|31)
        self.assertIsNone(after.sp_offset);self.assertFalse(after.stack)

    def test_single_memory_writeback_keeps_frame_coordinates_and_updates_alias(self):
        source=v.RegisterCopy('owned source',64)
        state=self.step(v.initial_state({19:source}),0xf8000c00|(0x1e0<<12)|(31<<5)|19)
        self.assertEqual(state.sp_offset,-32)
        state=self.step(state,0xf8400400|(32<<12)|(31<<5)|20)
        self.assertEqual(state.read_register(20),source)
        self.assertEqual(state.sp_offset,0);self.assertFalse(state.stack)
        state=self.step(state,0xd10103ff)  # allocate64
        state=self.step(state,0x910043fd)  # x29=sp+16
        state=self.step(state,0xf8000c00|(8<<12)|(29<<5)|19)
        self.assertEqual(state.sp_offset,-64)
        self.assertEqual(state.read_register(29),v.Derived('entry_sp_offset',(v.Literal((1<<64)-40,64),),64))
        state=self.step(state,0xf8400400|(8<<12)|(29<<5)|22)
        self.assertEqual(state.read_register(22),source)
        self.assertEqual(state.read_register(29),v.Derived('entry_sp_offset',(v.Literal((1<<64)-32,64),),64))


class RepairTwoProducerTests(unittest.TestCase):
    def result(self,words,call_index=0):
        from test_swift_broad_witness import region_candidate
        from airs.swift_outcome_witness_v2 import build_broad_swift_witness
        image,fn,call=region_candidate(words,call_index)
        return build_broad_swift_witness(image,fn,call)

    def test_new_forms_build_complete_candidate_without_fp_error_alias(self):
        result=self.result([0xf8000c00|(0x1e0<<12)|(31<<5)|19,0,
            0xb9000127,0xbd0003f5,0xfd4003f5,0xb8000000|(0x1f0<<12)|(29<<5)|7,
            0x8b200000|(8<<16)|(6<<13)|(9<<5)|10,
            0xb4000055,0xd65f03c0,0xd65f03c0],call_index=1)
        self.assertTrue(result['completeness']['complete'],result['completeness'])
        self.assertEqual(result['reason'],'validation_required')
        self.assertFalse(result['eligible'])
        self.assertEqual(result['post_call']['test_register'],'x21')
        self.assertTrue(result['cfg']['completeness']['all_words_classified'])

    def test_fp_overwrite_and_unknown_writeback_cannot_preserve_stack_or_error_origin(self):
        # An FP store destroys the integer spill, and an FP load cannot restore it.
        result=self.result([0xd10083ff,0,0xf90003f5,0xfd0003f5,0xf94003f3,
                            0xb4000053,0xd65f03c0,0xd65f03c0],call_index=1)
        self.assertFalse(result['completeness']['complete'])
        self.assertIsNone(result['post_call']['test_register'])
        # x21 as unknown memory base is changed by preindex; original alias dies.
        result=self.result([0,0xf8000c00|(8<<12)|(21<<5)|0,
                            0xb4000055,0xd65f03c0,0xd65f03c0])
        self.assertFalse(result['completeness']['complete'])
        self.assertIsNone(result['post_call']['test_register'])

    def test_reserved_neighbor_after_return_keeps_complete_cfg_refused(self):
        result=self.result([0,0xb4000055,0xd65f03c0,0xd65f03c0,0xbc000c00])
        self.assertFalse(result['cfg']['completeness']['all_words_classified'])
        self.assertFalse(result['completeness']['complete'])
