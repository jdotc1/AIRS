"""Exact method syntax and independently constructed nominal context bytes."""
from dataclasses import replace
import struct
import unittest
from airs.swift_throwing_declarations import parse_throwing_declaration
from airs.swift_nominal_context import admit_struct_context
from airs.swift_error_flow import throwing_declaration, recover_swift_error_flow
from airs.types import Section
from test_swift_error_flow import image

SYMBOL = '_$s4Demo7CounterV5parseyS2iKF'

def method_image(flags=0x51, parent_flags=0, duplicate=False):
    value = image(symbol=SYMBOL)
    raw = bytearray(256)
    struct.pack_into('<i', raw, 0, 0x1000)
    if duplicate:
        struct.pack_into('<i', raw, 4, 0xffc)
    struct.pack_into('<Iii', raw, 16, flags, 60, 88)
    struct.pack_into('<Iii', raw, 80, parent_flags, 0, 40)
    raw[112:120] = b'Counter\0'
    raw[128:133] = b'Demo\0'
    offset = len(value.data)
    return replace(value, data=value.data+raw, sections=value.sections+(
        Section('__TEXT','__swift5_types',0x200000000,8 if duplicate else 4,offset),
        Section('__TEXT','__const',0x200001000,240,offset+16)))

class SwiftMethodTests(unittest.TestCase):
    def test_three_qualified_syntax_forms_are_opt_in(self):
        for suffix in ('yS2iKF','yySiKF','SiyKF'):
            symbol = '_$s4Demo7CounterV5parse'+suffix
            self.assertIsNone(parse_throwing_declaration(symbol))
            declaration = parse_throwing_declaration(symbol, allow_methods=True)
            self.assertEqual(declaration.callable_kind,'struct_instance_method')
            self.assertEqual(declaration.type_name,'Counter')

    def test_legacy_adapter_preserves_keys(self):
        record=throwing_declaration('_$s4Demo5parseyS2iKF')
        self.assertEqual(set(record),{'module','name','parameters','result','convention','error_register','source'})
        self.assertIsNone(throwing_declaration(SYMBOL))

    def test_near_matches_refuse(self):
        for symbol in (SYMBOL+'Z', SYMBOL+'TA', SYMBOL+'junk', SYMBOL.replace('CounterV','CounterC'),
                       SYMBOL.replace('yS2iKF','yS2iYaKF'), SYMBOL.replace('yS2iKF','yxxKlF'),
                       SYMBOL.replace('7Counter','07Counter'), SYMBOL.replace('7Counter','128Counter'),
                       SYMBOL.replace('7Counter','S_'), SYMBOL.replace('Counter','Countér'),
                       '_$s4Demo7CounterV6NestedV5parseyS2iKF'):
            self.assertIsNone(parse_throwing_declaration(symbol,allow_methods=True),symbol)

    def test_context_and_method_call_admit(self):
        value=method_image()
        declaration=parse_throwing_declaration(SYMBOL,allow_methods=True)
        self.assertEqual(admit_struct_context(value,declaration)['status'],'admitted_struct_context')
        report=recover_swift_error_flow(value,include_swift_methods=True)
        self.assertEqual(report['model_version'],'swift-sync-error-edges-v38')
        self.assertEqual(report['calls'][0]['status'],'recovered_candidate')
        self.assertEqual(recover_swift_error_flow(value)['calls'][0]['status'],'declined')

    def test_generic_version_and_parent_context_refuse(self):
        declaration=parse_throwing_declaration(SYMBOL,allow_methods=True)
        for flags,parent in ((0xd1,0),(0x151,0),(0x51,17),(0x51,0x80)):
            self.assertEqual(admit_struct_context(method_image(flags,parent),declaration)['status'],'declined')

    def test_duplicate_and_missing_context_refuse(self):
        declaration=parse_throwing_declaration(SYMBOL,allow_methods=True)
        self.assertEqual(admit_struct_context(method_image(duplicate=True),declaration)['status'],'declined')
        self.assertEqual(admit_struct_context(image(symbol=SYMBOL),declaration)['status'],'declined')

    def test_metadata_budget_and_malformed_pointer_refuse(self):
        value=method_image(); declaration=parse_throwing_declaration(SYMBOL,allow_methods=True)
        self.assertEqual(admit_struct_context(value,declaration,max_entries=0)['status'],'declined')
        raw=bytearray(value.data);struct.pack_into('<i',raw,len(image(symbol=SYMBOL).data),0x7fffffff)
        self.assertEqual(admit_struct_context(replace(value,data=bytes(raw)),declaration)['status'],'declined')
