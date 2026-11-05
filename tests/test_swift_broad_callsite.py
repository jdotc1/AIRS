"""Owned synthetic words; expected targets are chosen independently of admission."""
import dataclasses
import struct
import unittest
from airs.types import MachOImage, Section, FunctionRange


def image(word=0x94000004, aliases=(), target=0x1010):
    data=bytearray(1024)
    struct.pack_into('<IiiIIIII',data,0,0xfeedfacf,0x100000c,0,2,3,192,0,0)
    names=['_$s4Test3fooyS2iKF',*aliases]
    strings=b'\0'+b''.join(n.encode()+b'\0' for n in names)
    struct.pack_into('<IIIIII',data,32,2,24,512,len(names),768,len(strings))
    struct.pack_into('<II16sQQQQiiII',data,56,0x19,152,b'__TEXT',0xf00,0x500,0,1024,7,5,1,0)
    struct.pack_into('<16s16sQQIIIIIIII',data,128,b'__text',b'__TEXT',0x1000,32,256,2,0,0,0,0,0,0)
    struct.pack_into('<IIII',data,208,0x26,16,900,4)
    data[900:904]=b'\x80\x02\x10\x00'
    pos=1
    for i,name in enumerate(names):
        struct.pack_into('<IBBHQ',data,512+16*i,pos,15,1,0,target)
        pos+=len(name)+1
    data[768:768+len(strings)]=strings
    struct.pack_into('<I',data,256,word)
    struct.pack_into('<I',data,272,0xd65f03c0)
    caller=FunctionRange(0x1000,0x1010,'caller','lc_function_starts')
    callee=FunctionRange(0x1010,0x1020,names[0],'lc_function_starts')
    return MachOImage(bytes(data),'synthetic','container','slice',4096,len(data),'arm64',0,None,0xf00,2,(Section('__TEXT','__text',0x1000,32,256),),(caller,callee)),caller


class CallsiteTests(unittest.TestCase):
    def admit(self,im,fn,pc=0x1000,**kw):
        from airs.swift_callsite_admission import admit_broad_swift_callsite
        return admit_broad_swift_callsite(im,fn,pc,**kw)

    def test_direct_owned_word(self):
        im,fn=image();r=self.admit(im,fn)
        self.assertEqual(r['status'],'admitted_callsite',r)
        self.assertEqual(r['callee_pc'],0x1010)
        self.assertEqual(r['provenance']['call']['slice_file_offset'],256)
        self.assertEqual(r['provenance']['call']['container_file_offset'],4352)
        self.assertFalse(r['abi_admitted'])
        self.assertFalse(r['call_return_proven'])
        self.assertEqual(r['declaration']['status'],'syntax_admitted')

    def test_indirect_and_authenticated_distinct(self):
        for word,reason in [(0xd63f0200,'indirect_target_unresolved'),(0xd73f0a11,'authenticated_indirect_unsupported')]:
            im,fn=image(word);self.assertEqual(self.admit(im,fn)['reason'],reason)

    def test_aliases_and_middle_target(self):
        im,fn=image(aliases=['_other']);self.assertEqual(self.admit(im,fn)['reason'],'callee_aliases')
        im,fn=image(0x94000005);self.assertEqual(self.admit(im,fn)['reason'],'callee_exact_entry_required')

    def test_membership_alignment_and_tail(self):
        im,fn=image();self.assertEqual(self.admit(im,fn,0x1002)['reason'],'call_pc_alignment')
        fake=dataclasses.replace(fn,name='fake');self.assertEqual(self.admit(im,fake)['reason'],'caller_exact_membership')
        im,fn=image(0x14000004);r=self.admit(im,fn)
        self.assertEqual(r['status'],'tail_call_candidate');self.assertFalse(r['call_return_proven'])

    def test_budget(self):
        from airs.swift_callsite_admission import CallsiteLimits
        im,fn=image();r=self.admit(im,fn,limits=CallsiteLimits(max_work=0))
        self.assertEqual(r['status'],'unresolved');self.assertFalse(r['details_complete'])

    def test_parser_failure_keeps_target(self):
        im,fn=image(aliases=());data=bytearray(im.data);data[769:790]=b'_not_swift'+b'\0'*11
        r=self.admit(dataclasses.replace(im,data=bytes(data)),fn)
        self.assertEqual(r['status'],'admitted_callsite');self.assertEqual(r['declaration']['status'],'syntax_unresolved')

    def test_binding_rejects_changed_bytes_and_slice(self):
        from airs.swift_callsite_admission import callsite_binding_matches
        im,fn=image();r=self.admit(im,fn)
        self.assertTrue(callsite_binding_matches(im,r))
        data=bytearray(im.data);data[256]=0
        self.assertFalse(callsite_binding_matches(dataclasses.replace(im,data=bytes(data)),r))
        self.assertFalse(callsite_binding_matches(dataclasses.replace(im,slice_offset=0),r))

    def test_visibility_alternate_resolver_relocation(self):
        for kind,desc in [(14,0),(31,0),(15,0x200),(15,0x100),(15,0x80)]:
            im,fn=image();data=bytearray(im.data);struct.pack_into('<BBH',data,516,kind,1,desc)
            self.assertEqual(self.admit(dataclasses.replace(im,data=bytes(data)),fn)['reason'],'callee_visibility')

    def test_overflow_and_nonexecutable(self):
        im,fn=image(0x97ffffff)
        self.assertEqual(self.admit(im,fn)['reason'],'callee_exact_entry_required')
        im,fn=image();sec=dataclasses.replace(im.sections[0],name='__data')
        self.assertEqual(self.admit(dataclasses.replace(im,sections=(sec,)),fn)['reason'],'instruction_not_executable')

    def test_true_displacement_overflow(self):
        im,fn=image();base=2**64-16
        caller=dataclasses.replace(fn,start=base,end=2**64)
        section=dataclasses.replace(im.sections[0],address=base)
        im=dataclasses.replace(im,functions=(caller,),sections=(section,))
        self.assertEqual(self.admit(im,caller,base)['reason'],'call_target_overflow')

    def test_unbounded_commands_and_overlapping_mapping(self):
        im,fn=image();data=bytearray(im.data);struct.pack_into('<I',data,36,0)
        self.assertEqual(self.admit(dataclasses.replace(im,data=bytes(data)),fn)['reason'],'load_command_extent')
        self.assertEqual(self.admit(dataclasses.replace(im,sections=im.sections*2),fn)['reason'],'instruction_mapping_ambiguous')

    def test_section_and_dynamic_relocations(self):
        for command,size in [(0x19,152),(0xb,80)]:
            im,fn=image();data=bytearray(im.data)
            struct.pack_into('<II',data,16,2,24+size)
            struct.pack_into('<II',data,56,command,size)
            if command==0x19:
                struct.pack_into('<I',data,120,1)
                struct.pack_into('<II',data,184,900,1)
            else:
                struct.pack_into('<I',data,124,1)
            self.assertEqual(self.admit(dataclasses.replace(im,data=bytes(data)),fn)['reason'],'relocations_unsupported')

    def test_instruction_and_alias_caps(self):
        from airs.swift_callsite_admission import CallsiteLimits
        im,fn=image()
        for limits in (CallsiteLimits(max_window_instructions=0),CallsiteLimits(max_aliases=0),CallsiteLimits(max_records=0)):
            self.assertFalse(self.admit(im,fn,limits=limits)['details_complete'])

    def test_output_metadata_bounded(self):
        from airs.swift_callsite_admission import CallsiteLimits
        im,fn=image();fn=dataclasses.replace(fn,name='x'*5000)
        im=dataclasses.replace(im,functions=(fn,im.functions[1]))
        r=self.admit(im,fn)
        self.assertFalse(r['details_complete'])
        self.assertEqual(r['reason'],'metadata_name_limit')
        self.assertFalse(r['syntactic_call_target_admitted'])


class CallsiteMetadataReviewTests(unittest.TestCase):
    def test_raw_metadata_binding_and_stale_initial_admission(self):
        from airs.swift_callsite_admission import admit_broad_swift_callsite,callsite_binding_matches
        im,fn=image();record=admit_broad_swift_callsite(im,fn,0x1000)
        self.assertEqual(record['status'],'admitted_callsite',record)
        for offset,value in [(8,1),(192,8),(901,1),(176,4),(112,1)]:
            data=bytearray(im.data);data[offset]=value
            stale=dataclasses.replace(im,data=bytes(data))
            self.assertFalse(callsite_binding_matches(stale,record),offset)
            self.assertNotEqual(admit_broad_swift_callsite(stale,fn,0x1000)['status'],'admitted_callsite',offset)

    def test_all_serialized_strings_are_bounded(self):
        from airs.swift_callsite_admission import admit_broad_swift_callsite
        im,fn=image()
        for modified in [dataclasses.replace(im,sections=(dataclasses.replace(im.sections[0],segment='x'*10000),)),
                         dataclasses.replace(im,functions=(fn,dataclasses.replace(im.functions[1],boundary_source='x'*10000))),
                         dataclasses.replace(im,slice_sha256='x'*10000)]:
            record=admit_broad_swift_callsite(modified,fn,0x1000)
            self.assertFalse(record['details_complete'])
            self.assertEqual(record['reason'],'metadata_name_limit')


def constant_image(words):
    """Independent encodings: ADR x16,+16; ADRP x16,0x1000; BLR x16."""
    im,fn=image()
    data=bytearray(im.data)
    for i,word in enumerate(words):
        struct.pack_into('<I',data,256+4*i,word)
    return dataclasses.replace(im,data=bytes(data)),fn


class ConstantIndirectReviewTests(unittest.TestCase):
    def admit(self,im,fn,pc):
        from airs.swift_callsite_admission import admit_broad_swift_callsite
        return admit_broad_swift_callsite(im,fn,pc)

    def test_independent_adr_blr_positive(self):
        im,fn=constant_image([0x10000090,0xd63f0200,0xd503201f,0xd65f03c0])
        record=self.admit(im,fn,0x1004)
        self.assertEqual(record['status'],'admitted_callsite',record)
        self.assertEqual(record['callee_pc'],0x1010)
        self.assertEqual(record['call_kind'],'blr_constant')
        self.assertEqual(record['provenance']['target_constant']['register'],'x16')
        self.assertEqual(record['provenance']['target_constant']['instructions'][0]['word'],'0x10000090')
        self.assertFalse(record['abi_admitted'])
        self.assertFalse(record['exclusive_entry_proven'])

    def test_adrp_add_and_move_wide_positive(self):
        for words in ([0x90000010,0x91004210,0xd63f0200,0xd65f03c0],
                      [0xd2820210,0xf2a00010,0xd63f0200,0xd65f03c0],
                      [0x10000089,0xaa0903f0,0xd63f0200,0xd65f03c0]):
            im,fn=constant_image(words);record=self.admit(im,fn,0x1008)
            self.assertEqual(record['status'],'admitted_callsite',record)
            self.assertEqual(record['callee_pc'],0x1010)

    def test_unknown_narrow_and_nonconstant_prefix(self):
        for words in ([0xf9400010,0xd63f0200,0xd503201f,0xd65f03c0],
                      [0x10000090,0x2a1f03f0,0xd63f0200,0xd65f03c0],
                      [0xf2a00010,0xd63f0200,0xd503201f,0xd65f03c0]):
            im,fn=constant_image(words);record=self.admit(im,fn,0x1004 if words[1]==0xd63f0200 else 0x1008)
            self.assertEqual(record['status'],'unresolved',record)
            self.assertFalse(record['syntactic_call_target_admitted'])

    def test_incoming_edge_and_entry_alias_attack(self):
        im,fn=constant_image([0x10000090,0xd63f0200,0xd503201f,0x17fffffe])
        self.assertEqual(self.admit(im,fn,0x1004)['reason'],'indirect_window_incoming_edge')
        im,fn=constant_image([0x10000090,0xd63f0200,0xd503201f,0xd65f03c0])
        data=bytearray(im.data)
        struct.pack_into('<I',data,44,2)
        struct.pack_into('<IBBHQ',data,528,1,15,1,0,0x1004)
        self.assertEqual(self.admit(dataclasses.replace(im,data=bytes(data)),fn,0x1004)['reason'],'indirect_window_symbol_entry')

    def test_provenance_changed_prefix_and_unknown_other_indirect(self):
        from airs.swift_callsite_admission import callsite_binding_matches
        im,fn=constant_image([0x10000090,0xd63f0200,0xd503201f,0xd65f03c0])
        record=self.admit(im,fn,0x1004)
        data=bytearray(im.data);data[256]=0x91
        self.assertFalse(callsite_binding_matches(dataclasses.replace(im,data=bytes(data)),record))
        struct.pack_into('<I',data,256,0x10000090)
        struct.pack_into('<I',data,276,0xd61f0220)
        self.assertEqual(self.admit(dataclasses.replace(im,data=bytes(data)),fn,0x1004)['reason'],'indirect_entry_screen_unresolved')

    def test_indirect_screen_budget(self):
        from airs.swift_callsite_admission import admit_broad_swift_callsite,CallsiteLimits
        im,fn=constant_image([0x10000090,0xd63f0200,0xd503201f,0xd65f03c0])
        record=admit_broad_swift_callsite(im,fn,0x1004,limits=CallsiteLimits(max_entry_screen_instructions=1))
        self.assertFalse(record['details_complete'])
        self.assertEqual(record['reason'],'indirect_entry_screen_limit')

    def test_constant_target_still_requires_exact_public_entry(self):
        # ADR x16,+20 names the middle of the callee, never its entry.
        im,fn=constant_image([0x100000b0,0xd63f0200,0xd503201f,0xd65f03c0])
        self.assertEqual(self.admit(im,fn,0x1004)['reason'],'callee_exact_entry_required')
        im,fn=constant_image([0x10000090,0xd63f0200,0xd503201f,0xd65f03c0])
        for kind,desc in [(14,0),(15,0x200),(15,0x100)]:
            data=bytearray(im.data);struct.pack_into('<BBH',data,516,kind,1,desc)
            self.assertEqual(self.admit(dataclasses.replace(im,data=bytes(data)),fn,0x1004)['reason'],'callee_visibility')

    def test_literal_and_control_flow_prefix_remain_unresolved(self):
        # LDR literal X16 and unconditional B are outside the constant grammar.
        for first in (0x58000090,0x14000001):
            im,fn=constant_image([first,0xd63f0200,0xd503201f,0xd65f03c0])
            self.assertEqual(self.admit(im,fn,0x1004)['reason'],'indirect_target_unresolved')


class LocalSpecializationReviewTests(unittest.TestCase):
    symbol='_$s10BroadOwned0A9Owner0363V15broad_case_0363ySis5Int32V_s6UInt64VSixtKSzRzlFZSi_Tt3g5'

    def local(self,symbol=None,kind=14,desc=0):
        im,fn=image();data=bytearray(im.data)
        name=(self.symbol if symbol is None else symbol).encode()+b'\0'
        struct.pack_into('<I',data,52,len(name)+1)
        data[769:769+len(name)]=name
        struct.pack_into('<BBH',data,516,kind,1,desc)
        return dataclasses.replace(im,data=bytes(data)),fn

    def test_exact_local_specialization_only(self):
        from airs.swift_callsite_admission import admit_broad_swift_callsite
        im,fn=self.local();r=admit_broad_swift_callsite(im,fn,0x1000)
        self.assertEqual(r['status'],'admitted_callsite',r)
        self.assertTrue(r['symbol_evidence']['local_specialization'])
        self.assertEqual(r['symbol_evidence']['n_type'],14)
        self.assertEqual(r['symbol_evidence']['specialization_kind'],'generic_reabstracted')
        self.assertFalse(r['abi_admitted'])

    def test_ordinary_local_and_malformed_specialization_refused(self):
        from airs.swift_callsite_admission import admit_broad_swift_callsite
        for symbol in ('_$s4Test3fooyS2iKF',self.symbol+'junk'):
            im,fn=self.local(symbol)
            self.assertEqual(admit_broad_swift_callsite(im,fn,0x1000)['reason'],'callee_visibility')
        for kind,desc in ((30,0),(14,0x100),(14,0x200),(14,0x80),(14,1)):
            im,fn=self.local(kind=kind,desc=desc)
            self.assertEqual(admit_broad_swift_callsite(im,fn,0x1000)['reason'],'callee_visibility')

    def test_indirect_absolute_entry_alias_is_screened(self):
        from airs.swift_callsite_admission import admit_broad_swift_callsite
        im,fn=constant_image([0x10000090,0xd63f0200,0xd503201f,0xd65f03c0])
        data=bytearray(im.data);struct.pack_into('<I',data,44,2)
        struct.pack_into('<IBBHQ',data,528,1,3,0,0,0x1004)
        self.assertEqual(admit_broad_swift_callsite(dataclasses.replace(im,data=bytes(data)),fn,0x1004)['reason'],'indirect_window_symbol_entry')

    def test_bc_cond_incoming_entry_is_screened(self):
        from airs.swift_callsite_admission import admit_broad_swift_callsite
        # BC.eq 0x1004 at 0x100c (FEAT_HBC, bit 4 set) skips ADR.
        im,fn=constant_image([0x10000090,0xd63f0200,0xd503201f,0x54ffffd0])
        self.assertEqual(admit_broad_swift_callsite(im,fn,0x1004)['reason'],'indirect_window_incoming_edge')


class PrivateWeakSpecializationReviewTests(unittest.TestCase):
    symbol=LocalSpecializationReviewTests.symbol
    local=LocalSpecializationReviewTests.local

    def test_exact_private_weak_specialization_direct_bl(self):
        from airs.swift_callsite_admission import admit_broad_swift_callsite
        im,fn=self.local(kind=30,desc=0x80)
        r=admit_broad_swift_callsite(im,fn,0x1000)
        self.assertEqual(r['status'],'admitted_callsite',r)
        self.assertEqual(r['symbol_evidence']['visibility'],'private_extern_weak_concrete_specialization')
        self.assertTrue(r['symbol_evidence']['private_extern_weak_specialization'])
        self.assertEqual((r['symbol_evidence']['n_type'],r['symbol_evidence']['n_desc']),(30,0x80))
        self.assertFalse(r['abi_admitted'])

    def test_private_weak_scope_negatives(self):
        from airs.swift_callsite_admission import admit_broad_swift_callsite
        for symbol,kind,desc in [(self.symbol,30,0),(self.symbol,30,0x180),(self.symbol,30,0x280),
                                 (self.symbol,14,0x80),(self.symbol,15,0x80),
                                 ('_$s4Test3fooyS2iKF',30,0x80),(self.symbol+'junk',30,0x80)]:
            im,fn=self.local(symbol,kind=kind,desc=desc)
            self.assertEqual(admit_broad_swift_callsite(im,fn,0x1000)['reason'],'callee_visibility')
        im,fn=self.local(kind=30,desc=0x80);data=bytearray(im.data)
        struct.pack_into('<I',data,256,0x14000004)
        self.assertEqual(admit_broad_swift_callsite(dataclasses.replace(im,data=bytes(data)),fn,0x1000)['reason'],'callee_visibility')


class PrivateStaticBodyRepairTests(unittest.TestCase):
    # Exact independent synthetic class/static spelling, not a dispatch thunk.
    symbol='_$s4Test5OwnerC3fooyS2iKFZ'
    local=LocalSpecializationReviewTests.local

    def test_private_static_body_direct_bl_and_capability(self):
        from airs.swift_callsite_admission import (create_callsite_session,
            admit_callsite_capability, validate_callsite_capability,
            admit_broad_swift_callsite)
        im,fn=self.local(kind=30,desc=0)
        result=admit_broad_swift_callsite(im,fn,0x1000)
        self.assertEqual(result['status'],'admitted_callsite',result)
        self.assertEqual(result['symbol_evidence']['visibility'],'private_extern_throwing_class_static_body')
        self.assertTrue(result['symbol_evidence']['private_extern_static_body'])
        self.assertFalse(result['symbol_evidence']['private_extern_weak_specialization'])
        self.assertFalse(result['abi_admitted'])
        session=create_callsite_session(im)
        cap=admit_callsite_capability(im,fn,0x1000,session=session)
        self.assertIsNotNone(validate_callsite_capability(im,cap))
        self.assertIsNone(validate_callsite_capability(dataclasses.replace(im),cap))

    def test_private_static_body_exact_scope_and_parse(self):
        from airs.swift_callsite_admission import admit_broad_swift_callsite
        for symbol,kind,desc in [
            (self.symbol,30,0x80),(self.symbol,30,0x100),(self.symbol,30,0x200),
            (self.symbol,14,0),(self.symbol,31,0),
            ('_$s4Test5OwnerV3fooyS2iKFZ',30,0),
            ('_$s4Test5OwnerC3fooyS2iKF',30,0),
            ('_$s4Test5OwnerC3fooyS2iFZ',30,0),
            (self.symbol+'Tj',30,0),(self.symbol+'Tf4nd_n',30,0),
            (self.symbol+'junk',30,0),
        ]:
            im,fn=self.local(symbol,kind,desc)
            result=admit_broad_swift_callsite(im,fn,0x1000)
            self.assertFalse(result['syntactic_call_target_admitted'],(symbol,kind,desc,result))
        im,fn=self.local(kind=30,desc=0)
        for word in (0x14000004,0xd63f0200):
            data=bytearray(im.data);struct.pack_into('<I',data,256,word)
            result=admit_broad_swift_callsite(dataclasses.replace(im,data=bytes(data)),fn,0x1000)
            self.assertFalse(result['syntactic_call_target_admitted'],result)

    def test_private_static_body_alias_entry_and_binding(self):
        from airs.swift_callsite_admission import admit_broad_swift_callsite,callsite_binding_matches
        im,fn=self.local(kind=30,desc=0)
        result=admit_broad_swift_callsite(im,fn,0x1000)
        self.assertEqual(result['status'],'admitted_callsite',result)
        data=bytearray(im.data);struct.pack_into('<H',data,518,0x80)
        self.assertFalse(callsite_binding_matches(dataclasses.replace(im,data=bytes(data)),result))
        data=bytearray(im.data);struct.pack_into('<I',data,44,2)
        struct.pack_into('<IBBHQ',data,528,1,30,1,0,0x1010)
        result=admit_broad_swift_callsite(dataclasses.replace(im,data=bytes(data)),fn,0x1000)
        self.assertEqual(result['reason'],'callee_aliases')
        data=bytearray(im.data);struct.pack_into('<I',data,256,0x94000005)
        result=admit_broad_swift_callsite(dataclasses.replace(im,data=bytes(data)),fn,0x1000)
        self.assertEqual(result['reason'],'callee_exact_entry_required')

    def test_private_static_body_known_blr_and_other_contexts(self):
        from airs.swift_callsite_admission import admit_broad_swift_callsite
        im,fn=self.local(kind=30,desc=0)
        data=bytearray(im.data)
        # ADR x16,0x1010 at caller entry; BLR x16 at 0x1004.
        struct.pack_into('<II',data,256,0x10000090,0xd63f0200)
        result=admit_broad_swift_callsite(dataclasses.replace(im,data=bytes(data)),fn,0x1004)
        self.assertEqual(result['reason'],'callee_visibility',result)
        for symbol in ('_$s4Test3fooyS2iKF','_$s4Test5OwnerO3fooyS2iKFZ'):
            im,fn=self.local(symbol,30,0)
            result=admit_broad_swift_callsite(im,fn,0x1000)
            self.assertEqual(result['reason'],'callee_visibility',result)


class CallsiteSessionTests(unittest.TestCase):
    def test_exact_image_session_and_private_capability(self):
        from airs.swift_callsite_admission import (create_callsite_session,admit_callsite_capability,
            validate_callsite_capability,admit_broad_swift_callsite,callsite_binding_matches)
        im,fn=image();session=create_callsite_session(im)
        self.assertGreater(session.initial_work_steps,0)
        cap=admit_callsite_capability(im,fn,0x1000,session=session)
        record=cap.record()
        self.assertEqual(record['status'],'admitted_callsite',record)
        self.assertEqual(record['session_initial_work_steps'],session.initial_work_steps)
        self.assertLess(len(record['binding']['reads']),len(session._raw_reads))
        self.assertIsNotNone(validate_callsite_capability(im,cap))
        self.assertTrue(callsite_binding_matches(im,record,session=session))
        self.assertFalse(callsite_binding_matches(im,record))
        record['callee_pc']=0x1004
        self.assertEqual(cap.record()['callee_pc'],0x1010)
        self.assertIsNone(validate_callsite_capability(im,record))
        with self.assertRaises(TypeError): dataclasses.replace(cap,_record={})
        with self.assertRaises(TypeError): dataclasses.replace(session,_image=im)
        other=dataclasses.replace(im)
        self.assertIsNone(validate_callsite_capability(other,cap))
        self.assertEqual(admit_broad_swift_callsite(other,fn,0x1000,session=session)['reason'],'callsite_session_image_mismatch')

    def test_changed_bytes_forged_object_and_serialized_record_have_no_authority(self):
        import json
        from airs.swift_callsite_admission import create_callsite_session,admit_callsite_capability,validate_callsite_capability
        im,fn=image();session=create_callsite_session(im);cap=admit_callsite_capability(im,fn,0x1000,session=session)
        data=bytearray(im.data);data[256]=0
        self.assertIsNone(validate_callsite_capability(dataclasses.replace(im,data=bytes(data)),cap))
        self.assertIsNone(validate_callsite_capability(im,json.loads(json.dumps(cap.record()))))
        class Forged:
            def record(self): return cap.record()
        self.assertIsNone(validate_callsite_capability(im,Forged()))

    def test_session_budget_and_failed_admission_do_not_mint_authority(self):
        from airs.swift_callsite_admission import (create_callsite_session,CallsiteSessionError,
            CallsiteLimits,admit_callsite_capability,validate_callsite_capability)
        im,fn=image()
        with self.assertRaises(CallsiteSessionError):
            create_callsite_session(im,limits=CallsiteLimits(max_work=0))
        session=create_callsite_session(im)
        cap=admit_callsite_capability(im,fn,0x1004,session=session)
        self.assertNotEqual(cap.record()['status'],'admitted_callsite')
        self.assertIsNone(validate_callsite_capability(im,cap))

    def test_cached_private_specialization_and_indirect_firewall(self):
        from airs.swift_callsite_admission import create_callsite_session,admit_callsite_capability,validate_callsite_capability
        helper=PrivateWeakSpecializationReviewTests()
        im,fn=helper.local(kind=30,desc=0x80);session=create_callsite_session(im)
        cap=admit_callsite_capability(im,fn,0x1000,session=session)
        self.assertTrue(cap.record()['symbol_evidence']['private_extern_weak_specialization'])
        self.assertEqual(validate_callsite_capability(im,cap)['caller_start'],0x1000)
        im,fn=constant_image([0x10000090,0xd63f0200,0xd503201f,0x54ffffd0])
        session=create_callsite_session(im)
        self.assertEqual(admit_callsite_capability(im,fn,0x1004,session=session).record()['reason'],'indirect_window_incoming_edge')

    def test_implicit_factory_work_and_validation_budget(self):
        from airs.swift_callsite_admission import create_callsite_session,admit_callsite_capability,validate_callsite_capability
        im,fn=image();session=create_callsite_session(im)
        implicit=admit_callsite_capability(im,fn,0x1000)
        explicit=admit_callsite_capability(im,fn,0x1000,session=session)
        self.assertEqual(implicit.record()['work_steps']-explicit.record()['work_steps'],session.initial_work_steps)
        self.assertIsNone(validate_callsite_capability(im,explicit,max_work=1))
