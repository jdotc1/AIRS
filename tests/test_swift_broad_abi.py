"""Broad ABI admission uses exact selected-image records, never names alone."""
import dataclasses
import importlib.util
import struct
import unittest

from airs.swift_declaration_profiles import parse_broad_declaration
from airs.types import MachOImage, Section


def image_for(kind=17, *, flags=None, module='Test', name='Owner', duplicate=False):
    data = bytearray(512)
    struct.pack_into('<i', data, 0, 64)
    if duplicate:
        struct.pack_into('<i', data, 4, 124)
    for pc in ([64, 128] if duplicate else [64]):
        struct.pack_into('<Iii', data, pc, flags if flags is not None else kind | 0x40,
                         192 - (pc + 4), 256 - (pc + 8))
    struct.pack_into('<Iii', data, 192, 0, 0, 288 - 200)
    data[256:256+len(name)+1] = name.encode() + b'\0'
    data[288:288+len(module)+1] = module.encode() + b'\0'
    return MachOImage(bytes(data), 'synthetic', 'container', 'slice', 4096, len(data),
                      'arm64', 0, None, 0, 6,
                      (Section('__TEXT', '__swift5_types', 0, 8 if duplicate else 4, 0),
                       Section('__TEXT', '__const', 64, 448, 64)), ())


class BroadABITests(unittest.TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('airs.swift_abi_profiles'),
                             'broad ABI admission module is missing')
        from airs import swift_abi_profiles
        return swift_abi_profiles

    def declaration(self, code='V'):
        return parse_broad_declaration(f'$s4Test5Owner{code}3fooyS2iKF')

    def test_exact_struct_enum_class_metadata_is_retained_without_lowering_claim(self):
        api = self.api()
        for code, kind in [('V', 17), ('O', 18), ('C', 16)]:
            result = api.admit_swift_abi(image_for(kind), self.declaration(code))
            self.assertEqual(result['status'], 'unresolved')
            self.assertEqual(result['reason'], 'lowering_not_qualified')
            context = result['evidence']['nominal_context']
            self.assertEqual(context['status'], 'admitted_nominal_context')
            self.assertEqual(context['records'][0]['descriptor_pc'], '0x40')
            self.assertEqual(len(context['records'][0]['raw_descriptor']), 56 if kind != 16 else 88)
            self.assertEqual(context['slice']['offset'], 4096)
            self.assertEqual(context['module']['raw_name'], b'Test\0'.hex())
            self.assertNotIn('error_register', result)

    def test_module_kind_and_duplicate_aliases_do_not_match(self):
        api = self.api()
        for image in [image_for(module='Else'), image_for(18), image_for(duplicate=True)]:
            self.assertNotEqual(api.admit_swift_abi(image, self.declaration())['evidence']['nominal_context']['status'],
                                'admitted_nominal_context')

    def test_generic_version_unknown_flags_and_malformed_relative_are_explicit(self):
        api = self.api()
        for flags, reason in [(0xd1, 'generic_context_unqualified'), (0x151, 'descriptor_flags_unqualified'),
                              (0x10051, 'descriptor_flags_unqualified')]:
            result = api.admit_swift_abi(image_for(flags=flags), self.declaration())
            self.assertEqual(result['reason'], reason)
        image = image_for()
        data = bytearray(image.data)
        struct.pack_into('<i', data, 68, -0x80000000)
        result = api.admit_swift_abi(dataclasses.replace(image, data=bytes(data)), self.declaration())
        self.assertEqual(result['reason'], 'malformed_nominal_metadata')

    def test_limits_precede_access_and_profile_is_immutable(self):
        api = self.api()
        class NoRead:
            architecture = 'arm64'
            def section(self, *args):
                return Section('__TEXT', '__swift5_types', 0, 0x100000000, 0)
            def bytes_at(self, *args):
                raise AssertionError('oversized section accessed')
        result = api.admit_swift_abi(NoRead(), self.declaration())
        self.assertEqual(result['reason'], 'metadata_resource_limit')
        result = api.admit_swift_abi(image_for(), self.declaration(), limits=api.ABILimits(max_work=0))
        self.assertEqual(result['reason'], 'metadata_resource_limit')
        with self.assertRaises(dataclasses.FrozenInstanceError):
            api.SYNC_ARM64_SWIFT6.error_register = 'x0'

    def test_unknown_architecture_arbitrary_qualification_and_generic_decline(self):
        api = self.api()
        free = parse_broad_declaration('$s4Test3fooyS2iKF')
        result = api.admit_swift_abi(image_for(), free, qualification={'error_register': 'x21'})
        self.assertEqual(result['reason'], 'untrusted_qualification')
        result = api.admit_swift_abi(dataclasses.replace(image_for(), architecture='arm64e'), free)
        self.assertEqual(result['reason'], 'architecture_unqualified')
        generic = parse_broad_declaration('$s4Test3fooyxxlF')
        self.assertEqual(api.admit_swift_abi(image_for(), generic)['reason'], 'generic_callable_unqualified')
        async_decl = parse_broad_declaration('$s4Test3fooyyYaKF')
        self.assertEqual(api.admit_swift_abi(image_for(), async_decl)['reason'], 'async_context')

    def test_string_and_depth_bounds(self):
        api = self.api()
        self.assertEqual(api.admit_swift_abi(image_for(), self.declaration(),
                         limits=api.ABILimits(max_string_bytes=3))['reason'], 'metadata_resource_limit')
        self.assertEqual(api.admit_swift_abi(image_for(), self.declaration(),
                         limits=api.ABILimits(max_context_depth=0))['reason'], 'metadata_resource_limit')

    def test_symbol_names_cannot_self_qualify_scalar_or_aggregate_lowering(self):
        api = self.api()
        for symbol in ['$s4Test3fooyS2iKF', '$s4Test3fooyySiSgKF', '$s4Test3fooyySaySiGKF']:
            result = api.admit_swift_abi(image_for(), parse_broad_declaration(symbol))
            self.assertEqual(result['reason'], 'lowering_not_qualified')
            self.assertNotIn('result_register', result)

    def test_owned_qualification_requires_retained_instruction_bytes(self):
        api = self.api()
        evidence = api.LOWERING_QUALIFICATIONS['owned-initial-v1-O-transform-int']
        data = bytearray(0x1000)
        for pc, raw, _ in evidence.observations:
            data[pc:pc+len(bytes.fromhex(raw))] = bytes.fromhex(raw)
        image = dataclasses.replace(image_for(), data=bytes(data), slice_sha256=evidence.slice_sha256,
                                    slice_size=len(data), sections=(Section('__TEXT', '__text', 0, len(data), 0),))
        declaration = parse_broad_declaration(evidence.symbol)
        result = api.admit_swift_abi(image, declaration)
        self.assertEqual(result['status'], 'admitted')
        self.assertEqual(result['result_location'], 'x0')
        changed = bytearray(data)
        changed[evidence.observations[0][0]] ^= 1
        result = api.admit_swift_abi(dataclasses.replace(image, data=bytes(changed)), declaration)
        self.assertEqual(result['reason'], 'qualification_bytes_mismatch')
        wrong = dataclasses.replace(image, slice_sha256='different')
        self.assertEqual(api.admit_swift_abi(wrong, declaration)['reason'], 'lowering_not_qualified')

    def test_nested_parent_identity_generic_parent_and_cycle(self):
        api = self.api()
        image = image_for()
        data = bytearray(image.data)
        struct.pack_into('<i', data, 68, 128-68)
        struct.pack_into('<Iii', data, 128, 0x51, 192-132, 320-136)
        data[320:326] = b'Outer\0'
        declaration = parse_broad_declaration('$s4Test5OuterV5OwnerV3fooyS2iKF')
        image = dataclasses.replace(image, data=bytes(data))
        result = api.admit_swift_abi(image, declaration)
        self.assertEqual(result['evidence']['nominal_context']['status'], 'admitted_nominal_context')
        struct.pack_into('<I', data, 128, 0xd1)
        self.assertEqual(api.admit_swift_abi(dataclasses.replace(image, data=bytes(data)), declaration)['reason'],
                         'generic_context_unqualified')
        struct.pack_into('<I', data, 128, 0x51)
        struct.pack_into('<i', data, 132, 64-132)
        self.assertEqual(api.admit_swift_abi(dataclasses.replace(image, data=bytes(data)), declaration)['reason'],
                         'cyclic_context_parent')

    def test_unrelated_generic_record_cannot_mask_exact_candidate(self):
        api = self.api()
        image = image_for(duplicate=True)
        data = bytearray(image.data)
        struct.pack_into('<I', data, 128, 0xd1)
        struct.pack_into('<i', data, 136, 320-136)
        data[320:326] = b'Other\0'
        result = api.admit_swift_abi(dataclasses.replace(image, data=bytes(data)), self.declaration())
        self.assertEqual(result['evidence']['nominal_context']['status'], 'admitted_nominal_context')

    def test_known_class_vtable_flag_admits_identity_without_virtual_dispatch(self):
        api = self.api()
        result = api.admit_swift_abi(image_for(16, flags=0x80000050), self.declaration('C'))
        self.assertEqual(result['reason'], 'lowering_not_qualified')
        self.assertEqual(result['evidence']['nominal_context']['status'], 'admitted_nominal_context')
        self.assertFalse(api.SYNC_ARM64_SWIFT6.virtual_dispatch_supported)

    def test_owned_methods_require_nominal_identity_and_corroborating_bytes(self):
        api = self.api()
        for evidence_id, kind in [('owned-initial-v1-O-struct0080', 17),
                                  ('owned-initial-v1-O-enum0180', 18),
                                  ('owned-initial-v1-O-class0249', 16)]:
            with self.subTest(evidence_id=evidence_id):
                self.assertIn(evidence_id, api.LOWERING_QUALIFICATIONS)
                observation = api.LOWERING_QUALIFICATIONS[evidence_id]
                declaration = parse_broad_declaration(observation.symbol)
                self.assertTrue(declaration.supported, declaration)
                context = declaration.identity.context[-1]
                base = image_for(kind, module='BroadOwned', name=context.name)
                data = bytearray(base.data) + bytearray(0x20000)
                for pc, raw, _ in observation.observations:
                    data[pc:pc+len(bytes.fromhex(raw))] = bytes.fromhex(raw)
                image = dataclasses.replace(base, data=bytes(data), slice_sha256=observation.slice_sha256,
                    slice_size=len(data), sections=(*base.sections, Section('__TEXT', '__text', 512, len(data)-512, 512)))
                result = api.admit_swift_abi(image, declaration, qualification=evidence_id)
                self.assertEqual(result['status'], 'admitted', result)
                self.assertEqual(result['receiver_location'], observation.receiver_location)
                self.assertEqual(result['result_location'], 'x0')
                wrong = dataclasses.replace(declaration.identity, context=())
                self.assertNotEqual(api.admit_swift_abi(image, wrong, qualification=evidence_id)['status'], 'admitted')

    def test_unrelated_kind_specific_tail_does_not_change_nominal_name_prefix(self):
        api = self.api()
        image = image_for(duplicate=True)
        data = bytearray(image.data)
        struct.pack_into('<I', data, 128, 0x12340051)
        struct.pack_into('<i', data, 136, 320-136)
        data[320:326] = b'Other\0'
        result = api.admit_swift_abi(dataclasses.replace(image, data=bytes(data)), self.declaration())
        self.assertEqual(result['evidence']['nominal_context']['status'], 'admitted_nominal_context')

    def test_frozen_identity_cannot_disagree_with_its_qualified_symbol(self):
        api = self.api()
        observation = api.LOWERING_QUALIFICATIONS['owned-initial-v1-O-transform-int']
        data = bytearray(0x1000)
        for pc, raw, _ in observation.observations:
            data[pc:pc+len(bytes.fromhex(raw))] = bytes.fromhex(raw)
        image = dataclasses.replace(image_for(), data=bytes(data), slice_sha256=observation.slice_sha256,
            slice_size=len(data), sections=(Section('__TEXT', '__text', 0, len(data), 0),))
        identity = parse_broad_declaration(observation.symbol).identity
        for field, value in [('module', 'Else'), ('function_name', 'other')]:
            result = api.admit_swift_abi(image, dataclasses.replace(identity, **{field: value}))
            self.assertNotEqual(result['status'], 'admitted', field)

    def test_work_budget_covers_metadata_and_lowering_together(self):
        api = self.api()
        observation = api.LOWERING_QUALIFICATIONS['owned-initial-v1-O-struct0080']
        declaration = parse_broad_declaration(observation.symbol)
        base = image_for(17, module='BroadOwned', name='BroadOwner0080')
        data = bytearray(base.data) + bytearray(0x10000)
        for pc, raw, _ in observation.observations:
            data[pc:pc+len(bytes.fromhex(raw))] = bytes.fromhex(raw)
        image = dataclasses.replace(base, data=bytes(data), slice_sha256=observation.slice_sha256,
            slice_size=len(data), sections=(*base.sections, Section('__TEXT', '__text', 512, len(data)-512, 512)))
        metadata = api.admit_nominal_context(image, declaration.identity)
        limits = api.ABILimits(max_work=metadata['work_bytes'] + 1)
        result = api.admit_swift_abi(image, declaration, limits=limits)
        self.assertEqual(result['reason'], 'metadata_resource_limit')

    def test_selected_slice_and_unique_mapping_bound_observation_reads(self):
        api = self.api()
        observation = api.LOWERING_QUALIFICATIONS['owned-initial-v1-O-transform-int']
        data = bytearray(0x1000)
        for pc, raw, _ in observation.observations:
            data[pc:pc+len(bytes.fromhex(raw))] = bytes.fromhex(raw)
        image = dataclasses.replace(image_for(), data=bytes(data), slice_sha256=observation.slice_sha256,
            slice_size=len(data), sections=(Section('__TEXT', '__text', 0, len(data), 0),))
        declaration = parse_broad_declaration(observation.symbol)
        for changed in (dataclasses.replace(image, slice_size=1024),
                        dataclasses.replace(image, sections=image.sections*2)):
            self.assertNotEqual(api.admit_swift_abi(changed, declaration)['status'], 'admitted')

    def test_binding_retains_excluded_leaf_reads_and_directory_geometry(self):
        api = self.api()
        image = image_for(duplicate=True)
        data = bytearray(image.data)
        struct.pack_into('<i', data, 136, 320-136)
        data[320:326] = b'Other\0'
        image = dataclasses.replace(image, data=bytes(data))
        record = api.admit_nominal_context(image, self.declaration().identity)
        self.assertEqual(record['status'], 'admitted_nominal_context')
        self.assertTrue(hasattr(api, 'swift_abi_binding_matches'))
        self.assertTrue(api.swift_abi_binding_matches(image, record))
        data[320:326] = b'Owner\0'
        self.assertFalse(api.swift_abi_binding_matches(dataclasses.replace(image, data=bytes(data)), record))
        changed_sections = (dataclasses.replace(image.sections[0], size=12), *image.sections[1:])
        self.assertFalse(api.swift_abi_binding_matches(dataclasses.replace(image, sections=changed_sections), record))

    def test_disjoint_duplicate_type_directories_cannot_hide_alias(self):
        api = self.api()
        image = image_for(duplicate=True)
        first = dataclasses.replace(image.sections[0], size=4)
        second = dataclasses.replace(first, address=4, file_offset=4)
        image = dataclasses.replace(image, sections=(first, second, image.sections[1]))
        result = api.admit_swift_abi(image, self.declaration())
        self.assertEqual(result['reason'], 'ambiguous_metadata_directory')

    def test_general_profile_uses_raw_call_callee_transport_and_storage(self):
        api = self.api()
        self.assertTrue(hasattr(api, 'ABICallsiteQualification'))
        from airs.types import FunctionRange
        symbol = '_$s4Test3fooyS2iKF'
        data = bytearray(1024)
        struct.pack_into('<IiiIIIII', data, 0, 0xfeedfacf, 0x100000c, 0, 2, 3, 192, 0, 0)
        strings = b'\0' + symbol.encode() + b'\0'
        struct.pack_into('<IIIIII', data, 32, 2, 24, 512, 1, 768, len(strings))
        struct.pack_into('<II16sQQQQiiII', data, 56, 0x19, 152, b'__TEXT', 0xf00, 0x500, 0, 1024, 7, 5, 1, 0)
        struct.pack_into('<16s16sQQIIIIIIII', data, 128, b'__text', b'__TEXT', 0x1000, 96, 256, 2, 0, 0, 0, 0, 0, 0)
        struct.pack_into('<IIII', data, 208, 0x26, 16, 900, 4)
        data[900:904] = b'\x80\x02\x20\x00'
        struct.pack_into('<IBBHQ', data, 512, 1, 15, 1, 0, 0x1020)
        data[768:768+len(strings)] = strings
        caller_words = [0xd2800015, 0x94000007, 0xb4000055, 0xd503201f,
                        0x8b010000, 0xd65f03c0, 0xd503201f, 0xd503201f]
        callee_words = [0xf100041f, 0x54000061, 0xaa0003f5, 0x14000002,
                        0x91000400, 0xd65f03c0] + [0xd503201f]*10
        struct.pack_into('<24I', data, 256, *(caller_words+callee_words))
        caller = FunctionRange(0x1000, 0x1020, 'caller', 'lc_function_starts')
        callee = FunctionRange(0x1020, 0x1060, symbol, 'lc_function_starts')
        image = MachOImage(bytes(data), 'synthetic', 'container', 'slice', 0, len(data), 'arm64', 0,
                           None, 0xf00, 2, (Section('__TEXT', '__text', 0x1000, 96, 256),), (caller, callee))
        request = api.ABICallsiteQualification(api.STABLE_ARM64_SWIFT6.identifier, 0x1004, 0x1000, 0x1020)
        result = api.admit_swift_abi(image, parse_broad_declaration(symbol), qualification=request)
        self.assertEqual(result['status'], 'admitted', result)
        self.assertFalse(result['compiler_verified'])
        self.assertEqual(result['result_storage']['locations'], ['x0'])
        self.assertTrue(api.swift_abi_binding_matches(image, result))
        for at in (0x1000, 0x1008, 0x1030):
            changed = bytearray(data)
            struct.pack_into('<I', changed, 256+at-0x1000, 0xd503201f)
            declined = api.admit_swift_abi(dataclasses.replace(image, data=bytes(changed)),
                                         parse_broad_declaration(symbol), qualification=request)
            if at == 0x1030:
                self.assertNotEqual(declined['status'], 'admitted', hex(at))
            else:
                self.assertEqual(declined['status'], 'admitted', declined)
                self.assertFalse(declined['error_state_proven'])
                self.assertIn('caller_error_observations', declined)

    def test_scalar_fp_storage_patterns_preserve_direction_and_precision(self):
        api = self.api()
        single = api.STABLE_STORAGE_CAPABILITIES['Swift.Float']
        double = api.STABLE_STORAGE_CAPABILITIES['Swift.Double']
        self.assertTrue(api._result_corroboration((0x1e270100,), single))  # fmov s0,w8
        self.assertTrue(api._result_corroboration((0x9e620100,), double))  # scvtf d0,x8
        self.assertFalse(api._result_corroboration((0x1e260100,), single))  # fmov w0,s8
        self.assertFalse(api._result_corroboration((0x1e270100,), double))

    def test_concrete_specialization_keeps_observed_formal_argument_locations(self):
        api = self.api()
        self.assertTrue(hasattr(api, '_concrete_arguments_corroborated'))
        arguments = [{'locations': ['w0']}, {'locations': ['w1']}, {'locations': ['x2']}]
        # Retained v2 generic340 prefix: Bool x0, UInt8 w1, concrete Int x2.
        prefix = (0xa9be4ff4, 0xa9017bfd, 0x910043fd,
                  0x92400009, 0x8b210129, 0x8b020134, 0xf1055e9f, 0x540001ca)
        self.assertTrue(api._concrete_arguments_corroborated(prefix, arguments))
        # Writing a constant to x2 before its first use cannot attest input x2.
        changed = prefix[:5] + (0xd2800002,) + prefix[5:]
        self.assertFalse(api._concrete_arguments_corroborated(changed, arguments))

    def test_general_profile_consumes_private_callsite_custody_not_record_dict(self):
        api = self.api()
        from test_swift_broad_callsite import image as call_image
        from airs.swift_callsite_admission import create_callsite_session, admit_callsite_capability
        image, caller = call_image()
        data = bytearray(image.data)
        struct.pack_into('<4I', data, 272, 0xaa0003f5, 0x91000400, 0xd65f03c0, 0xd503201f)
        image = dataclasses.replace(image, data=bytes(data))
        session = create_callsite_session(image)
        capability = admit_callsite_capability(image, caller, 0x1000, session=session)
        declaration = parse_broad_declaration('_$s4Test3fooyS2iKF')
        request = api.ABICallsiteQualification(api.STABLE_ARM64_SWIFT6.identifier,
                                               0x1000, caller.start, 0x1010, capability)
        admitted = api.admit_swift_abi(image, declaration, qualification=request)
        self.assertEqual(admitted['status'], 'admitted', admitted)
        self.assertTrue(api.swift_abi_binding_matches(image, admitted, callsite_capability=capability))
        self.assertFalse(api.swift_abi_binding_matches(image, admitted))
        untrusted = dataclasses.replace(request, callsite_capability=capability.record())
        self.assertEqual(api.admit_swift_abi(image, declaration, qualification=untrusted)['reason'],
                         'untrusted_callsite_capability')
        mismatch = dataclasses.replace(request, caller_start=0x1010)
        self.assertEqual(api.admit_swift_abi(image, declaration, qualification=mismatch)['reason'],
                         'callsite_capability_request_mismatch')

    def test_specialization_vector_stores_cannot_attest_integer_arguments(self):
        api = self.api()
        arguments = [{'locations': ['x0']}, {'locations': ['x1']}]
        # STR Q0,[SP] and STR Q1,[SP,#16] read SIMD values, not GPR X0/X1.
        self.assertFalse(api._concrete_arguments_corroborated(
            (0x3d8003e0, 0x3d8007e1, 0xd65f03c0), arguments))

    def test_specialization_prefix_stops_at_signed_load_branch_and_unknown_effects(self):
        api = self.api()
        arguments = [{'locations': ['x0']}]
        examples = [
            (0xb98003e0, 0xd65f03c0),  # LDRSW X0,[SP] defines X0, does not read it
            (0x54000011, 0x91000403),  # conditional branch variant before X0 use
            (0x88a07c41, 0x91000403),  # unknown CAS-like effects include Rs beyond Rd
            (0xf8008c01, 0x91000403),  # unsupported pre-index store through X0
        ]
        for words in examples:
            self.assertFalse(api._concrete_arguments_corroborated(words, arguments), hex(words[0]))

    def test_error_register_self_move_and_zero_move_are_not_transport(self):
        api = self.api()
        self.assertTrue(hasattr(api, '_error_transport_word'))
        self.assertFalse(api._error_transport_word(0xaa1503f5))  # mov x21,x21
        self.assertFalse(api._error_transport_word(0xaa1f03f5))  # mov x21,xzr
        self.assertTrue(api._error_transport_word(0xaa0003f5))   # mov x21,x0

    def test_indirect_result_corroboration_requires_allocated_store_encodings(self):
        api = self.api()
        storage = api.STABLE_STORAGE_CAPABILITIES['BroadOwned.BroadSmall']
        for word in (0xb9800100, 0x39800100, 0x79800100, 0xf9800100, 0x3dc00100, 0xa9400500):
            self.assertFalse(api._result_corroboration((word,), storage), hex(word))
        for word in (0xf9000100, 0x3d800100, 0xa9000500):
            self.assertTrue(api._result_corroboration((word,), storage), hex(word))

    def test_prefix_rejects_reserved_shift_extend_and_immediate_allocations(self):
        api = self.api()
        arguments = [{'locations': ['x0']}]
        reserved = (
            0x0b00fc00,  # W ADD shift amount63
            0x0bc00000,  # ADD shifted register shift=3
            0x0b206000,  # W ADD extended UXTX outside supported width subset
            0x0b201400,  # ADD extended shift amount5
            0x0b600000,  # extended-register fixed shift bits are nonzero
            0x0a008000,  # W logical shift amount32
            0x11800021,  # reserved immediate-arithmetic bit23
            0x12c00001,  # W move-wide halfword position2
            0x32800001,  # reserved move-wide opc01
            0x13008021,  # W bitfield imms32
            0x9240fc21,  # reserved all-ones logical-immediate element
            0xed000000,  # SIMD pair with reserved size3
            0x7d800000,  # SIMD single opc10 only allocated for size0 Q
        )
        for word in reserved:
            self.assertFalse(api._concrete_arguments_corroborated(
                (word, 0x91000403), arguments), hex(word))
        # Allocated neighboring W/X shifted and extended forms retain the input.
        for word in (0x0b007c01, 0x8b00fc01, 0x0b205001, 0x8b207001, 0x0a007c01):
            self.assertTrue(api._concrete_arguments_corroborated((word,), arguments), hex(word))

    def test_reserved_data_processing_does_not_attest_scalar_result_storage(self):
        api = self.api()
        storage = api.STABLE_STORAGE_CAPABILITIES['Swift.Int']
        for word in (0x0b00fc00, 0x0bc00000, 0x0b206000, 0x0a008000, 0x12c00000):
            self.assertFalse(api._result_corroboration((word,), storage), hex(word))

    def test_owned_lineage_keeps_selected_source_distinct_from_primary_reference(self):
        api = self.api()
        self.assertTrue(hasattr(api, 'OWNED_SOURCE_BY_SLICE'))
        from test_swift_broad_callsite import image as call_image
        secondary_slice = '35f5565c675d9d4c328e310bfc1adaa2bd58afc8b3905bd888f009cd03f7cd76'
        secondary_source = 'ca091dde5345cda398ef78f95b6969abd0736acd508961a705654c9bedffb5cf'
        self.assertEqual(api.OWNED_SOURCE_BY_SLICE[secondary_slice], secondary_source)
        self.assertEqual(set(api._V2_SLICES), set(api.OWNED_SOURCE_BY_SLICE) & set(api._V2_SLICES))
        with self.assertRaises(TypeError):
            api.OWNED_SOURCE_BY_SLICE[secondary_slice] = 'caller supplied source'
        image, caller = call_image()
        data = bytearray(image.data)
        struct.pack_into('<4I', data, 272, 0xaa0003f5, 0x91000400, 0xd65f03c0, 0xd503201f)
        image = dataclasses.replace(image, data=bytes(data), slice_sha256=secondary_slice)
        request = api.ABICallsiteQualification(api.STABLE_ARM64_SWIFT6.identifier,
                                               0x1000, caller.start, 0x1010)
        result = api.admit_swift_abi(image, parse_broad_declaration('_$s4Test3fooyS2iKF'), qualification=request)
        self.assertEqual(result['status'], 'admitted', result)
        lowering = result['evidence']['lowering']
        self.assertEqual(lowering['selected_source_sha256'], secondary_source)
        self.assertEqual(lowering['selected_slice_sha256'], secondary_slice)
        self.assertEqual(lowering['source_sha256'], api._V2_SOURCE)
        self.assertNotEqual(lowering['selected_source_sha256'], lowering['source_sha256'])
        self.assertEqual(result['family_evidence']['source_sha256'], secondary_source)
        self.assertIn(lowering['reference_slice_sha256'], api._V2_SLICES)
        self.assertNotIn(secondary_slice, api._V2_SLICES)

    def test_unregistered_slice_cannot_supply_owned_source_lineage(self):
        api = self.api()
        self.assertTrue(hasattr(api, 'OWNED_SOURCE_BY_SLICE'))
        self.assertIsNone(api.OWNED_SOURCE_BY_SLICE.get('caller supplied slice'))
        for primary in api._V2_SLICES:
            self.assertEqual(api.OWNED_SOURCE_BY_SLICE[primary], api._V2_SOURCE)

    def test_exact_straightline_leaf_can_preserve_x21_without_error_copy(self):
        api = self.api()
        self.assertTrue(hasattr(api, '_leaf_preserves_x21'))
        # Retained compiler pattern motivates this newly authored word fixture.
        leaf = (0x7200001f, 0x528008e8, 0x1a880508, 0x0b010100, 0xd65f03c0)
        self.assertTrue(api._leaf_preserves_x21(leaf))
        self.assertTrue(api._leaf_preserves_x21((0x9e670115, 0xd65f03c0)))  # writes D21, not X21
        self.assertTrue(api._leaf_preserves_x21((0xf90003f5, 0xd65f03c0)))  # stores X21, does not change it
        for words in (
            (0xaa0003f5, 0xd65f03c0),  # X21 destination
            (0xaa1503f5, 0xd65f03c0),  # even a self-write is outside this strict proof
            (0xf94003f5, 0xd65f03c0),  # X21 load destination
            (0x9e660015, 0xd65f03c0),  # FMOV X21,D0
            (0x0b00fc00, 0xd65f03c0),  # reserved W shifted ADD
            (0x94000001, 0xd65f03c0),  # opaque call
            (0x14000001, 0xd65f03c0),  # another control transfer
            (0x54000010, 0xd65f03c0),  # conditional branch variant
            (0x88a07c41, 0xd65f03c0),  # unknown atomic effects
            (0xd65f03c0, 0xd503201f, 0xd65f03c0),  # multiple returns
            (0xd503201f,),  # no return
        ):
            self.assertFalse(api._leaf_preserves_x21(words), tuple(hex(w) for w in words))

    def test_leaf_preservation_admission_keeps_incoming_error_state_unproven(self):
        api = self.api()
        from test_swift_broad_callsite import image as call_image
        image, caller = call_image()
        data = bytearray(image.data)
        struct.pack_into('<4I', data, 272, 0x91000400, 0xd503201f, 0xd503201f, 0xd65f03c0)
        image = dataclasses.replace(image, data=bytes(data))
        request = api.ABICallsiteQualification(api.STABLE_ARM64_SWIFT6.identifier,
                                               0x1000, caller.start, 0x1010)
        result = api.admit_swift_abi(image, parse_broad_declaration('_$s4Test3fooyS2iKF'), qualification=request)
        self.assertEqual(result['status'], 'admitted', result)
        observation = result['evidence']['lowering']['callee_error_observation']
        self.assertEqual(observation['mode'], 'preserved_x21_leaf')
        self.assertTrue(observation['preserves_incoming_x21'])
        self.assertFalse(observation['incoming_state_proven'])
        self.assertFalse(observation['error_object_type_proven'])
        self.assertFalse(result['error_state_proven'])
        self.assertFalse(result['call_return_proven'])
