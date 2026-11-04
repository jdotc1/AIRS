"""Bounded exact-byte body evidence; synthetic instructions are never executed."""
from dataclasses import replace
import struct
import unittest
from airs.types import AuditResult
from test_rbit_x_candidate import fixture,RET

WORDS=(0xd28000e0,0xd2800101,0x9b017c02,RET)


def inputs():
    image,function,_=fixture(WORDS)
    outcome=AuditResult('agreement','compact','frameless','modeled_leaf_body',
                        ('supported_model_agreement',),instruction_count=4)
    return image,function,outcome


class BodyFingerprintTests(unittest.TestCase):
    def producer(self,*args):
        from airs.body_fingerprint import exact_body_fingerprint
        return exact_body_fingerprint(*args)

    def test_opt_in_producer_has_explicit_kind_size_and_digest(self):
        result=self.producer(*inputs())
        self.assertEqual(set(result),{'kind','sha256','instruction_count'})
        self.assertEqual(result['kind'],'arm64-exact-bytes-v1')
        self.assertEqual(result['instruction_count'],4)
        self.assertRegex(result['sha256'],r'^[0-9a-f]{64}$')

    def test_immediate_and_word_order_changes_remain_visible(self):
        image,function,outcome=inputs()
        original=self.producer(image,function,outcome)['sha256']
        for words in ((0xd2800120,*WORDS[1:]),(WORDS[1],WORDS[0],*WORDS[2:])):
            changed=replace(image,data=struct.pack('<4I',*words))
            self.assertNotEqual(self.producer(changed,function,outcome)['sha256'],original)

    def test_body_digest_does_not_include_vm_address_or_symbol(self):
        image,function,outcome=inputs()
        moved=replace(image,preferred_base=0x2000,sections=tuple(replace(s,address=s.address+0x1000) for s in image.sections))
        renamed=replace(function,start=function.start+0x1000,end=function.end+0x1000,name='renamed')
        self.assertEqual(self.producer(image,function,outcome),self.producer(moved,renamed,outcome))

    def test_refuses_short_partial_unknown_boundary_and_unresolved(self):
        image,function,outcome=inputs()
        for candidate in (replace(outcome,verdict='unresolved'),replace(outcome,instruction_count=3)):
            self.assertIsNone(self.producer(image,function,candidate))
        self.assertIsNone(self.producer(image,replace(function,boundary_source='compact_unwind'),outcome))
        self.assertIsNone(self.producer(image,replace(function,end=function.start+8),replace(outcome,instruction_count=2)))
        self.assertIsNone(self.producer(image,replace(function,start=function.start+1),outcome))
        self.assertIsNone(self.producer(image,replace(function,end=function.start+4*16385),replace(outcome,instruction_count=16385)))

    def test_refuses_unmapped_nonexecutable_zero_fill_and_wrong_architecture(self):
        image,function,outcome=inputs()
        for candidate in (replace(image,architecture='arm64e'),replace(image,cpu_subtype=2),
                          replace(image,data=b''),replace(image,sections=()),
                          replace(image,sections=tuple(replace(s,name='__data',flags=0) for s in image.sections)),
                          replace(image,sections=tuple(replace(s,flags=1) for s in image.sections))):
            self.assertIsNone(self.producer(candidate,function,outcome))
