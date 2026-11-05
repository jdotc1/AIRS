import struct
import unittest
from airs.macho import parse_macho
from airs.types import InputError
from parser_helpers import build_macho

class PIEHeaderSymbolTests(unittest.TestCase):
    def image(self, name='__mh_execute_header', relative=-0x1000, filetype=2, pie=True, function_offsets=(0,)):
        data=bytearray(build_macho(bytes.fromhex('c0035fd6'), symbols=((name,relative),('owned_code',0)), filetype=filetype, function_offsets=function_offsets))
        struct.pack_into('<I',data,24,0x200000 if pie else 0)
        return bytes(data)
    def test_pie_header_marker_is_metadata_not_executable_function(self):
        image=parse_macho(self.image())
        self.assertTrue(image.has_valid_admission())
        self.assertEqual(len(image.functions),1)
        self.assertEqual(image.functions[0].name,'owned_code')
        self.assertEqual(image.functions[0].start,0x100001000)
    def test_header_marker_never_becomes_symbol_fallback_boundary(self):
        image=parse_macho(self.image(function_offsets=None))
        self.assertEqual([(f.start,f.name) for f in image.functions],[(0x100001000,'owned_code')])
        self.assertEqual(image.functions[0].boundary_source,'symbol_table')
    def test_noncanonical_outside_section_records_remain_refused(self):
        for kwargs in [dict(name='ordinary_symbol'),dict(name='__mh_execute_header_suffix'),dict(relative=-0xffc),dict(pie=False),dict(filetype=6),dict(filetype=8)]:
            with self.subTest(kwargs=kwargs),self.assertRaises(InputError) as caught:parse_macho(self.image(**kwargs))
            self.assertEqual(caught.exception.code,'symbol_address_extent')
