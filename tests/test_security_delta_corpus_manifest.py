from security_delta_fixture_support import owned_temporary_directory
"""Owned protocol negatives; no downloaded application is needed."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from security_delta_corpus import CorpusRefusal, decode_manifest, validate_corpus, load_manifests


def owned_manifest():
    def source(version, digest, date):
        return dict(version=version, release_url="https://example.org/releases/" + version + ".zip",
                    sha256=digest * 64, license_note="Owned protocol fixture; no third-party payload",
                    license_url="https://example.org/LICENSE", app_relative_path="Owned.app",
                    published_at=date, archive_kind="zip")
    return dict(schema_version=1, case_id="owned.app.1-to-2", publisher="owned",
                application="app", selection=dict(architecture="arm64", purpose="authentic_release_pair"),
                previous=source("1", "a", "2025-01-01T00:00:00Z"),
                current=source("2", "b", "2025-02-01T00:00:00Z"),
                expected=dict(adjudication="pending", source_digests=dict(previous="a" * 64, current="b" * 64),
                              declaration_facts=[], expected_refusals=[]), coverage_tags=[])


class SecurityDeltaCorpusManifestTests(unittest.TestCase):
    def decode(self, value):
        return decode_manifest(json.dumps(value).encode())

    def refused(self, value, code):
        with self.assertRaises(CorpusRefusal) as result:
            self.decode(value)
        self.assertEqual(result.exception.code, code)

    def test_noncanonical_integer_fact_declines(self):
        for decimal in ("-0", "+1", "01"):
            value=owned_manifest()
            value["expected"]["declaration_facts"]=[dict(side="previous",source_path="Contents/Info.plist",source_sha256="c"*64,archive_sha256="a"*64,
                locator=dict(kind="plist_key",key="owned"),state="observed",expected_value=dict(type="integer",decimal=decimal,representation="unspecified"),adjudicator="owned independent parser")]
            with self.subTest(decimal=decimal):
                with self.assertRaises(CorpusRefusal):self.decode(value)

    def test_malformed_fact_tags_bits_and_data_are_classified(self):
        for typed in [{"type":[]},{"type":"real","bits":"7ff0000000000000"},{"type":"date","bits":"7ff8000000000000"},{"type":"data","base64":"not base64"}]:
            value=owned_manifest()
            fact=dict(side="previous",source_path="Contents/Info.plist",source_sha256="c"*64,archive_sha256="a"*64,
                locator=dict(kind="plist_key",key="owned"),state="observed",expected_value=typed,adjudicator="owned independent parser")
            value["expected"]["declaration_facts"]=[fact]
            with self.subTest(typed=typed):
                with self.assertRaises(CorpusRefusal): self.decode(value)

    def test_structured_adjudicated_fact_and_empty_typed_string(self):
        value=owned_manifest()
        fact=dict(side="previous",source_path="Contents/Info.plist",source_sha256="c"*64,archive_sha256="a"*64,
            locator=dict(kind="plist_key",key="CFBundleVersion"),state="observed",expected_value=dict(type="string",value=""),adjudicator="owned independent parser")
        value["expected"].update(adjudication="independently_adjudicated",adjudicator="owned reviewer",declaration_facts=[fact])
        self.decode(value)
        fact["archive_sha256"]="b"*64
        self.refused(value,"fact_source_binding_mismatch")

    def test_owned_protocol_roundtrip_is_immutable(self):
        manifest = self.decode(owned_manifest())
        self.assertEqual(manifest.case_id, "owned.app.1-to-2")
        with self.assertRaises((AttributeError, TypeError)):
            manifest.case_id = "changed"

    def test_missing_digest_and_license_refuse(self):
        for key in ("sha256", "license_note", "license_url"):
            value = owned_manifest(); del value["previous"][key]
            self.refused(value, "manifest_fields")

    def test_duplicate_case_id_refuses_before_lookup(self):
        item = self.decode(owned_manifest())
        with self.assertRaises(CorpusRefusal) as result:
            validate_corpus([item, item])
        self.assertEqual(result.exception.code, "duplicate_case_id")

    def test_swapped_sides_and_digests_refuse(self):
        value = owned_manifest(); value["previous"], value["current"] = value["current"], value["previous"]
        self.refused(value, "comparison_direction")
        value = owned_manifest(); value["previous"]["sha256"] = "c" * 64
        self.refused(value, "source_binding_mismatch")

    def test_path_escapes_and_invalid_utf8_refuse(self):
        for path in ("../Outside.app", "/Owned.app", "Owned.app/../Other", "Owned\\Other.app", "Owned\x00.app"):
            value = owned_manifest(); value["current"]["app_relative_path"] = path
            self.refused(value, "unsafe_relative_path")
        value = owned_manifest(); value["current"]["app_relative_path"] = "\ud800.app"
        self.refused(value, "invalid_utf8")

    def test_untrusted_url_shapes_refuse(self):
        for url in ("file:///input", "http://example.org/a.zip", "https://user:secret@example.org/a.zip",
                    "https://example.org/a.zip?token=secret", "https://example.org/a.zip#fragment"):
            value = owned_manifest(); value["current"]["release_url"] = url
            self.refused(value, "unsupported_source_url")

    def test_unknown_version_unknown_fields_and_duplicate_json_keys_refuse(self):
        value = owned_manifest(); value["schema_version"] = 2
        self.refused(value, "unsupported_schema_version")
        value = owned_manifest(); value["authority"] = "live"
        self.refused(value, "manifest_fields")
        raw = json.dumps(owned_manifest()).replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1')
        with self.assertRaises(CorpusRefusal) as result:
            decode_manifest(raw.encode())
        self.assertEqual(result.exception.code, "duplicate_json_key")

    def test_same_bytes_rezip_and_reversed_date_do_not_count_as_pair(self):
        value = owned_manifest(); value["current"]["sha256"] = "a" * 64
        self.refused(value, "duplicate_release_bytes")
        value = owned_manifest(); value["previous"]["published_at"] = value["current"]["published_at"]
        self.refused(value, "comparison_direction")

    def test_manifest_resource_bounds(self):
        with self.assertRaises(CorpusRefusal) as result:
            decode_manifest(b" " * (262144 + 1))
        self.assertEqual(result.exception.code, "manifest_byte_limit")
        value = owned_manifest(); value["coverage_tags"] = ["simple"] * 40
        self.refused(value, "manifest_collection_limit")

    def test_invalid_raw_utf8_has_precise_code(self):
        with self.assertRaises(CorpusRefusal) as result:
            decode_manifest(b'\xff')
        self.assertEqual(result.exception.code, "invalid_utf8")

    def test_manifest_symlink_and_ancestor_escape_refuse(self):
        # Temporary owned metadata only; no authentic release is touched.
        with owned_temporary_directory() as folder:
            root = Path(folder)
            actual = root / "actual"; actual.mkdir()
            (actual / "case.json").write_text(json.dumps(owned_manifest()))
            link = root / "alias"; link.symlink_to(actual, target_is_directory=True)
            (actual / "nested").mkdir()
            (actual / "nested/case.json").write_text(json.dumps(owned_manifest()))
            with self.assertRaises((CorpusRefusal, OSError)):
                load_manifests(link / "nested")
            (actual / "malicious.json").symlink_to(actual / "case.json")
            with self.assertRaises(CorpusRefusal) as result:
                load_manifests(actual)
            self.assertEqual(result.exception.code, "manifest_source_unavailable")


if __name__ == "__main__":
    unittest.main()
