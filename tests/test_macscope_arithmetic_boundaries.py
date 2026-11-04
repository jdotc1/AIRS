"""Literal boundary cases adapted from owned MacScope arithmetic checks.

These qualify existing AIRS arithmetic; no decompiler expression evaluator is
imported and no target instructions are executed.
"""
import unittest
from airs.arm64 import Value
from airs.cfg import PathState, decode_instruction


class MacScopeArithmeticBoundaryTests(unittest.TestCase):
    def test_multiply_accumulate_min_product_and_outer_sum_wrap(self):
        for width,base in ((32,0x1b000000),(64,0x9b000000)):
            minimum=1<<(width-1); maximum=minimum-1; mask=(1<<width)-1
            for a,b,c,expected in ((minimum,mask,0,minimum),(maximum,1,1,minimum)):
                s=PathState();s.registers[1:4]=[Value('constant',a),Value('constant',b),Value('constant',c)]
                s.apply(decode_instruction(base|(2<<16)|(3<<10)|(1<<5)))
                self.assertEqual(s.registers[0],Value('constant',expected))

    def test_multiply_negation_minimum_and_overflowed_product(self):
        for width,base in ((32,0x1b008000),(64,0x9b008000)):
            minimum=1<<(width-1)
            for a,b,expected in ((minimum,1,minimum),(minimum-1,2,2)):
                s=PathState();s.registers[1:3]=[Value('constant',a),Value('constant',b)]
                # MSUB Rd,Rn,Rm,ZR is MNEG; ZR supplies the old addend zero.
                s.apply(decode_instruction(base|(2<<16)|(31<<10)|(1<<5)))
                self.assertEqual(s.registers[0],Value('constant',expected))

    def test_cmn_shifted_sign_overflow_literal_nzcv_and_lt(self):
        for width,word in ((32,0x2b01041f),(64,0xab01041f)):
            minimum=1<<(width-1); mask=(1<<width)-1
            for a,b,nzcv in ((0,minimum//2,0b1000),(minimum,minimum//2,0b0111),
                             (minimum-1,1,0b1001),(minimum,minimum-1,0b0011),
                             (mask-1,1,0b0110),(mask-2,1,0b1000)):
                s=PathState();s.registers[0:2]=[Value('constant',a),Value('constant',b)]
                s.apply(decode_instruction(word))
                expected=tuple(bool(nzcv&bit) for bit in (8,4,2,1))
                self.assertEqual(s.flags,expected)
                self.assertEqual(s.condition(11),expected[0]!=expected[3])
