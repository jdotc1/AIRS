"""Admission seals bind immutable parsed bytes without repeated source hashes."""
from dataclasses import replace
import unittest

from airs.macho import parse_macho
from airs.swift_owned_image import _OwnedDigestReceipt
from parser_helpers import build_macho


class ImageAdmissionTests(unittest.TestCase):
    def test_first_parse_mints_seal_and_source_changes_invalidate(self):
        image = parse_macho(build_macho(bytes(28)))
        self.assertTrue(image.has_valid_admission())
        self.assertTrue(replace(image, path='another-display-path').has_valid_admission())
        mutations = {
            'data': bytes(bytearray(image.data)),
            'container_sha256': '0' * 64,
            'slice_sha256': '1' * 64,
            'slice_offset': image.slice_offset + 1,
            'slice_size': image.slice_size + 1,
            'architecture': 'arm64e',
            'cpu_subtype': image.cpu_subtype + 1,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                self.assertFalse(replace(image, **{field: value}).has_valid_admission())
        mutated = bytearray(image.data)
        mutated[-1] ^= 1
        self.assertFalse(replace(image, data=bytes(mutated)).has_valid_admission())

    def test_no_seal_is_unadmitted_and_hidden_from_equality_and_repr(self):
        image = parse_macho(build_macho(bytes(32)))
        unadmitted = replace(image, _admission_seal=None)
        self.assertFalse(unadmitted.has_valid_admission())
        self.assertEqual(image, unadmitted)
        self.assertNotIn('_admission_seal', repr(image))

    def test_owned_digest_reuse_mints_seal_without_new_digest(self):
        data = build_macho(bytes(36))
        digest = 'b' * 64
        image = parse_macho(data, _owned_digest_receipt=_OwnedDigestReceipt(data, digest))
        self.assertEqual(image.slice_sha256, digest)
        self.assertTrue(image.has_valid_admission())
        self.assertFalse(replace(image, slice_size=float(image.slice_size)).has_valid_admission())

    def test_fat_admission_binds_selected_slice_object(self):
        from parser_helpers import build_fat
        data = build_fat((build_macho(bytes(40)),))
        image = parse_macho(data)
        self.assertGreater(image.slice_offset, 0)
        self.assertTrue(image.has_valid_admission())
        self.assertFalse(replace(image, data=data).has_valid_admission())

    def test_parser_metadata_replacements_invalidate_admission(self):
        from airs.types import Issue
        image = parse_macho(build_macho(bytes(44)))
        self.assertTrue(image.has_valid_admission())
        self.assertTrue(replace(image, path='changed display path').has_valid_admission())
        first = image.functions[0]
        section = image.sections[0]
        mutations = {
            'functions': (),
            'function_name': {'functions': (replace(first, name='filtered_name'),) + image.functions[1:]},
            'function_boundary': {'functions': (replace(first, end=first.end - 1),) + image.functions[1:]},
            'sections': (),
            'section_mapping': {'sections': (replace(section, address=section.address + 4),) + image.sections[1:]},
            'preferred_base': image.preferred_base + 4,
            'preferred_base_type': {'preferred_base': float(image.preferred_base)},
            'file_type': image.file_type + 1,
            'file_type_type': {'file_type': float(image.file_type)},
            'uuid': 'other-image-uuid',
            'issues': (Issue('replacement', 'changed parser qualification'),),
        }
        for label, value in mutations.items():
            changed = value if isinstance(value, dict) else {label: value}
            with self.subTest(field=label):
                self.assertFalse(replace(image, **changed).has_valid_admission())

    def test_thin_image_records_single_container_slice(self):
        image = parse_macho(build_macho(bytes(48)))
        self.assertEqual(getattr(image, 'slice_index', None), 0)
        self.assertEqual(getattr(image, 'container_slice_count', None), 1)
        self.assertTrue(image.has_valid_admission())

    def test_fat_image_records_actual_nonzero_directory_index(self):
        from parser_helpers import build_fat
        container = build_fat((build_macho(bytes(52), cpusubtype=2),
                               build_macho(bytes(56))))
        image = parse_macho(container)
        self.assertEqual(getattr(image, 'slice_index', None), 1)
        self.assertEqual(getattr(image, 'container_slice_count', None), 2)
        self.assertTrue(image.has_valid_admission())

    def test_changed_slice_index_and_count_invalidate_custody(self):
        image = parse_macho(build_macho(bytes(60)))
        self.assertTrue(image.has_valid_admission())
        for field, value in (('slice_index', 1), ('slice_index', False),
                             ('slice_index', 0.0), ('slice_index', None),
                             ('container_slice_count', 2), ('container_slice_count', True),
                             ('container_slice_count', 1.0), ('container_slice_count', None)):
            with self.subTest(field=field, value=value):
                self.assertFalse(replace(image, **{field: value}).has_valid_admission())
