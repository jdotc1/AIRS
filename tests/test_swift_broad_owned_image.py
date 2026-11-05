"""New synthetic files only: exercise receipt reuse without hashing owned outputs."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from parser_helpers import build_macho, build_fat
from airs.types import InputError


class OwnedImageTests(unittest.TestCase):
    def fixture(self, root, data=None):
        root = root.resolve()
        data = build_macho() if data is None else data
        library = root / 'BroadOwned-Onone.dylib'
        library.write_bytes(data)
        with library.open('rb') as handle:
            before = os.fstat(handle.fileno())
            digest = hashlib.sha256(handle.read()).hexdigest()  # first seal of new fixture
            after = os.fstat(handle.fileno())
        def custody(value):
            return {key: getattr(value, 'st_' + key) for key in ('dev', 'ino', 'size', 'mtime_ns', 'ctime_ns')}
        receipt = {'schema': 'airs.owned-swift-broad-compile.v2', 'state': 'compiled_unindexed',
                   'output_directory': str(root), 'modes': {'Onone': {
                       'library': library.name, 'library_path': str(library), 'bytes': len(data),
                       'emitted_sha256': digest, 'custody_before': custody(before), 'custody_after': custody(after)}}}
        path = root / 'compile-receipt.json'
        path.write_text(json.dumps(receipt))
        return library, path, receipt, digest

    def test_loader_exists(self):
        from airs import swift_owned_image
        self.assertTrue(callable(getattr(swift_owned_image, 'load_owned_swift_image', None)))

    def test_reuses_sealed_digest_without_hashing(self):
        from airs.swift_owned_image import load_owned_swift_image
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            library, receipt, _, digest = self.fixture(Path(temporary))
            image = load_owned_swift_image(library, receipt, 'Onone')
            self.assertEqual(image.container_sha256, digest)
            self.assertEqual(image.slice_sha256, digest)
            self.assertTrue(image.functions)

    def test_changed_file_and_untrusted_report_are_refused(self):
        from airs.swift_owned_image import load_owned_swift_image
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            library, receipt, metadata, _ = self.fixture(Path(temporary))
            library.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'custody'):
                load_owned_swift_image(library, receipt, 'Onone')
            metadata['schema'] = 'saved-analysis-report'
            receipt.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, 'receipt'):
                load_owned_swift_image(library, receipt, 'Onone')

    def test_symlink_and_fat_are_refused(self):
        from airs.swift_owned_image import load_owned_swift_image
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            root = Path(temporary)
            library, receipt, _, _ = self.fixture(root, build_fat((build_macho(),)))
            with self.assertRaisesRegex(ValueError, 'thin'):
                load_owned_swift_image(library, receipt, 'Onone')
            alias = root / 'alias.dylib'
            alias.symlink_to(library)
            with self.assertRaises(ValueError):
                load_owned_swift_image(alias, receipt, 'Onone')

    def test_structural_parse_checks_still_apply(self):
        from airs.swift_owned_image import load_owned_swift_image
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            library, receipt, _, _ = self.fixture(Path(temporary), b'\xcf\xfa\xed\xfe' + bytes(4))
            with self.assertRaises(InputError):
                load_owned_swift_image(library, receipt, 'Onone')

    def test_private_token_rejects_equal_distinct_bytes(self):
        from airs.swift_owned_image import _OwnedDigestReceipt
        from airs.macho import parse_macho
        data = build_macho()
        token = _OwnedDigestReceipt(data, 'a' * 64)
        with self.assertRaisesRegex(ValueError, 'identity'):
            parse_macho(bytes(bytearray(data)), _owned_digest_receipt=token)

    def test_default_parser_still_computes_identity(self):
        from airs.macho import parse_macho
        data = build_macho(bytes(20))
        digest = hashlib.sha256(data).hexdigest()
        image = parse_macho(data)
        self.assertEqual(image.container_sha256, digest)

    def test_internal_hook_reuses_bound_digest_and_rejects_dictionary(self):
        from airs.swift_owned_image import _OwnedDigestReceipt
        from airs.macho import parse_macho
        data = build_macho(bytes(24))
        # Deliberately distinct synthetic token proves the parser consumes the
        # internal receipt instead of recomputing; no real artifact is sealed.
        digest = 'a' * 64
        image = parse_macho(data, _owned_digest_receipt=_OwnedDigestReceipt(data, digest))
        self.assertEqual(image.container_sha256, digest)
        self.assertEqual(image.slice_sha256, digest)
        with self.assertRaisesRegex(ValueError, 'internal'):
            parse_macho(data, _owned_digest_receipt={'sha256': digest})

    def test_receipt_missing_custody_and_wrong_path_are_refused(self):
        from airs.swift_owned_image import load_owned_swift_image
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            library, receipt, metadata, _ = self.fixture(Path(temporary))
            metadata['modes']['Onone']['custody_after']['size'] += 1
            receipt.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, 'custody'):
                load_owned_swift_image(library, receipt, 'Onone')
            metadata['modes']['Onone']['library_path'] = str(library.parent / 'other.dylib')
            receipt.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, 'exact library'):
                load_owned_swift_image(library, receipt, 'Onone')

    def test_receipt_duplicate_keys_are_refused(self):
        from airs.swift_owned_image import load_owned_swift_image
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
            library, receipt, metadata, _ = self.fixture(Path(temporary))
            # Conflicting duplicate at a nested custody object must not be
            # silently overwritten by the JSON decoder's final value.
            raw = json.dumps(metadata)
            old = '"custody_after": {'
            raw = raw.replace(old, old + '"size": -1, ', 1)
            receipt.write_text(raw)
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                load_owned_swift_image(library, receipt, 'Onone')

    def test_both_custody_records_and_bytes_require_exact_integers(self):
        from airs.swift_owned_image import load_owned_swift_image
        mutations = [
            ('custody_before', 'size', float),
            ('custody_after', 'size', float),
            ('custody_after', 'dev', lambda _: True),
            ('custody_after', 'size', lambda _: -1),
            ('bytes', None, float),
        ]
        for field, key, convert in mutations:
            with self.subTest(field=field, key=key, convert=convert):
                with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary:
                    library, receipt, metadata, _ = self.fixture(Path(temporary))
                    entry = metadata['modes']['Onone']
                    if key is None:
                        entry[field] = convert(entry[field])
                    else:
                        entry[field][key] = convert(entry[field][key])
                    receipt.write_text(json.dumps(metadata))
                    with self.assertRaisesRegex(ValueError, 'custody'):
                        load_owned_swift_image(library, receipt, 'Onone')
