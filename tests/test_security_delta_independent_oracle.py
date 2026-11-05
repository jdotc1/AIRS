"""Independent owned bytes; no AIRS decoder/analyzer imports."""
import plistlib
import struct
import sys
import tempfile
import os
from unittest.mock import patch
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from security_delta_independent_oracle import OracleRefusal, observe_macho, observe_plist, observe_bundle, compare_uuid_tool, compare_loader_tool


def image(commands=(), subtype=0):
    raw = b"".join(commands)
    return struct.pack("<8I", 0xfeedfacf, 0x0100000c, subtype, 2, len(commands), len(raw), 0, 0) + raw


def dylib(path, command=0xc):
    name = path.encode() + b"\0"
    size = (24 + len(name) + 7) & ~7
    return struct.pack("<6I", command, size, 24, 0, 0x10000, 0x10000) + name + bytes(size - 24 - len(name))


class SecurityDeltaIndependentOracleTests(unittest.TestCase):
    def test_boolean_integer_and_nested_order_are_distinct(self):
        a = observe_plist(plistlib.dumps({"value": True, "items": [1, "x"]}, fmt=plistlib.FMT_BINARY))
        b = observe_plist(plistlib.dumps({"value": 1, "items": ["x", 1]}, fmt=plistlib.FMT_BINARY))
        self.assertNotEqual(a["value"], b["value"])
        self.assertNotEqual(a["items"], b["items"])

    def test_raw_plist_does_not_invent_api_numeric_signedness(self):
        facts = observe_plist(plistlib.dumps({"signed": -1, "positive": 1, "large": (1 << 64) - 1}, fmt=plistlib.FMT_BINARY))
        self.assertEqual(facts["large"]["decimal"], "18446744073709551615")
        self.assertEqual(facts["signed"]["decimal"], "-1")
        self.assertEqual(facts["positive"]["representation"], "unspecified")

    def test_empty_privacy_is_present_and_malformed_is_unavailable(self):
        self.assertEqual(observe_plist(plistlib.dumps({})), {})
        with self.assertRaises(OracleRefusal) as result:
            observe_plist(b"malformed")
        self.assertEqual(result.exception.code, "plist_unavailable")

    def test_duplicate_loader_commands_and_order_are_retained(self):
        raw = image([dylib("@rpath/A.dylib"), dylib("@rpath/A.dylib"), dylib("/B.dylib", 0x80000018)])
        observation = observe_macho(raw)
        commands = observation["slices"][0]["loader"]
        self.assertEqual(len(commands), 3)
        self.assertEqual([c["path"] for c in commands], ["@rpath/A.dylib", "@rpath/A.dylib", "/B.dylib"])
        self.assertEqual(commands[2]["kind"], "weak")
        self.assertEqual(commands[0]["offset"], 32)

    def test_equal_architecture_label_does_not_erase_subtype_bits(self):
        a = observe_macho(image(subtype=0))["slices"][0]
        b = observe_macho(image(subtype=0x80000000))["slices"][0]
        self.assertEqual(a["architecture"], b["architecture"])
        self.assertNotEqual(a["identity"]["cpu_subtype"], b["identity"]["cpu_subtype"])

    def test_fat_slice_offsets_sizes_and_uuid_are_independent(self):
        uuid_command = struct.pack("<II", 0x1b, 24) + bytes(range(16))
        thin = image([uuid_command]); offset = 4096
        raw = struct.pack(">II5I", 0xcafebabe, 1, 0x0100000c, 0, offset, len(thin), 12)
        raw += bytes(offset - len(raw)) + thin
        fact = observe_macho(raw)["slices"][0]
        self.assertEqual(fact["identity"]["offset"], offset)
        self.assertEqual(fact["identity"]["size"], len(thin))
        self.assertEqual(fact["uuid"], "00010203-0405-0607-0809-0a0b0c0d0e0f")

    def test_missing_signature_and_malformed_slot_are_distinct(self):
        missing = observe_macho(image())["slices"][0]["signature"]
        blob = struct.pack(">III2I", 0xfade0cc0, 20, 1, 5, 9999)
        command = struct.pack("<IIII", 0x1d, 16, 48, len(blob))
        malformed = observe_macho(image([command]) + blob)["slices"][0]["signature"]
        self.assertEqual(missing["state"], "absent")
        self.assertEqual(malformed["state"], "unavailable")
        self.assertEqual(malformed["reason"], "signature_slot_invalid")

    def test_truncated_header_and_command_refuse(self):
        for raw in (b"\xcf\xfa\xed\xfe", image([struct.pack("<II", 0xc, 0)])):
            with self.assertRaises(OracleRefusal):
                observe_macho(raw)

    def test_bundle_scope_privacy_presence_and_exclusions(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "local-evidence/security-delta-track-a") as folder:
            root = Path(folder) / "Owned.app"
            (root / "Contents/MacOS").mkdir(parents=True)
            (root / "Contents/Resources").mkdir()
            (root / "Contents/MacOS/Main").write_bytes(image())
            (root / "Contents/Info.plist").write_bytes(plistlib.dumps({"CFBundleExecutable": "Main"}))
            (root / "Contents/MacOS/Excluded").symlink_to(Path(folder) / "outside")
            facts = observe_bundle(root)
            self.assertIn("Contents/MacOS/Main", facts["images"])
            self.assertEqual(facts["privacy"]["Contents/Resources/PrivacyInfo.xcprivacy"]["state"], "absent")
            self.assertTrue(any(x["path"] == "Contents/MacOS/Excluded" for x in facts["exclusions"]))
            (root / "Contents/Resources/PrivacyInfo.xcprivacy").write_bytes(plistlib.dumps({}))
            present = observe_bundle(root)
            self.assertEqual(present["privacy"]["Contents/Resources/PrivacyInfo.xcprivacy"]["state"], "observed")
            self.assertEqual(present["plists"]["Contents/Resources/PrivacyInfo.xcprivacy"]["values"], {})

    def test_bundle_missing_cancelled_and_truncated_are_explicit(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "local-evidence/security-delta-track-a") as folder:
            root = Path(folder)
            with self.assertRaises(OracleRefusal) as missing:
                observe_bundle(root / "missing.app")
            self.assertEqual(missing.exception.code, "bundle_source_unavailable")
            with self.assertRaises(OracleRefusal) as cancelled:
                observe_bundle(root, cancelled=lambda: True)
            self.assertEqual(cancelled.exception.code, "cancelled")
            for i in range(4):
                (root / str(i)).write_bytes(b"x")
            partial = observe_bundle(root, maximum_files=2)
            self.assertEqual(partial["scope"]["state"], "truncated")
            self.assertFalse(partial["scope"]["omitted_count_exact"])

    def test_invalid_utf8_filesystem_name_refuses_without_fatal_error(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "local-evidence/security-delta-track-a") as folder:
            try:
                descriptor = os.open(os.fsencode(folder) + b"/\xff", os.O_WRONLY | os.O_CREAT, 0o600)
            except OSError as error:
                if error.errno == 92:
                    self.skipTest("APFS refuses constructing the owned invalid-UTF8 filename (EILSEQ)")
                raise
            os.close(descriptor)
            with self.assertRaises(OracleRefusal) as result:
                observe_bundle(Path(folder))
            self.assertEqual(result.exception.code, "invalid_utf8_path")

    def test_unrepresentable_directory_name_is_classified(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "local-evidence/security-delta-track-a") as folder:
            with patch("security_delta_independent_oracle.bounded_directory_names", return_value=["\udcff"]):
                with self.assertRaises(OracleRefusal) as result:
                    observe_bundle(Path(folder))
                self.assertEqual(result.exception.code, "invalid_utf8_path")

    def test_oracle_output_ceiling_is_observable(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "local-evidence/security-delta-track-a") as folder:
            root = Path(folder)
            (root / "Info.plist").write_bytes(plistlib.dumps({"key": "value"}))
            result = observe_bundle(root, maximum_fact_bytes=16)
            self.assertEqual(result["scope"]["state"], "truncated")
            self.assertEqual(result["scope"]["reason"], "oracle_output_limit")
            self.assertEqual(result["scope"]["omitted_count"], 1)

    def test_probe_bytes_are_in_work_accounting(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "local-evidence/security-delta-track-a") as folder:
            root = Path(folder)
            for i in range(4):
                (root / str(i)).write_bytes(b"opaque")
            result = observe_bundle(root)
            self.assertEqual(result["scope"]["read_source_bytes"], 16)

    def test_duplicate_signature_command_cannot_hide_invalid_region(self):
        valid_blob = struct.pack(">III", 0xfade0cc0, 12, 0)
        good = struct.pack("<4I", 0x1d, 16, 64, len(valid_blob))
        bad = struct.pack("<4I", 0x1d, 16, 9999, 12)
        result = observe_macho(image([bad, good]) + valid_blob)
        self.assertEqual(result["slices"][0]["signature"]["state"], "unavailable")
        self.assertEqual(result["slices"][0]["signature"]["reason"], "signature_command_ambiguous")

    def test_signature_slot_identity_magic_and_overlap_are_not_guessed(self):
        from security_delta_independent_oracle import signature_facts
        payload = plistlib.dumps({"owned": True})
        def region(records, blobs):
            length = 12 + 8 * len(records) + len(blobs)
            return struct.pack(">III", 0xfade0cc0, length, len(records)) + b"".join(struct.pack(">II", *r) for r in records) + blobs
        wrong = struct.pack(">II", 0x12345678, len(payload) + 8) + payload
        result = signature_facts(region([(5, 20)], wrong), 0, 20 + len(wrong))
        self.assertNotEqual(result.get("slots", [{}])[0].get("entitlements_state"), "observed")
        blob = struct.pack(">II", 0xfade7171, len(payload) + 8) + payload
        for records in [[(5, 28), (5, 28)], [(5, 28), (7, 28)]]:
            data = region(records, blob)
            self.assertEqual(signature_facts(data, 0, len(data))["state"], "unavailable")

    def test_minimum_os_and_toolchain_sections_are_raw_qualified(self):
        build=struct.pack("<6I",0x32,24,1,0x000e0200,0x001b0000,0)
        segment=struct.pack("<II16sQQQQIIII",0x19,152,b"__TEXT",0,0,0,0,7,5,1,0)
        section=struct.pack("<16s16sQQIIIIIIII",b"__swift5_types",b"__TEXT",0,0,0,0,0,0,0,0,0,0)
        result=observe_macho(image([build,segment+section]))["slices"][0]
        self.assertEqual(result["minimum_os"],[{"command":50,"platform":1,"minimum":918016,"sdk":1769472,"offset":32}])
        self.assertEqual(result["sections"][0]["section"],"__swift5_types")

    def test_failed_stale_read_consumes_work_budget(self):
        from security_delta_corpus import file_metadata
        with tempfile.TemporaryDirectory(dir=ROOT / "local-evidence/security-delta-track-a") as folder:
            root=Path(folder); raw=plistlib.dumps({"owned":"value"})
            (root/"Info.plist").write_bytes(raw)
            calls=0
            def metadata(info):
                nonlocal calls
                calls+=1; result=file_metadata(info)
                if calls==2: return tuple(list(result[:3])+[result[3]+1]+list(result[4:]))
                return result
            with patch("security_delta_independent_oracle.file_metadata",side_effect=metadata):
                result=observe_bundle(root)
            self.assertEqual(result["plists"]["Info.plist"]["reason"],"source_stale")
            self.assertEqual(result["scope"]["read_source_bytes"],len(raw)+4)

    def test_document_publish_is_atomic_and_never_overwrites(self):
        from security_delta_independent_oracle import write_document
        with tempfile.TemporaryDirectory(dir=ROOT / "local-evidence/security-delta-track-a") as folder:
            destination = Path(folder) / "capture.json"
            with self.assertRaises(OracleRefusal):
                write_document(destination, {"value": "too large"}, maximum_bytes=4)
            self.assertFalse(destination.exists())
            write_document(destination, {"value": "retained"})
            with self.assertRaises(FileExistsError):
                write_document(destination, {"value": "replacement"})
            self.assertIn("retained", destination.read_text())
            self.assertEqual(list(Path(folder).iterdir()), [destination])

    def test_apple_tool_agreement_and_disagreement_are_retained(self):
        fact = {"uuid": "00010203-0405-0607-0809-0a0b0c0d0e0f", "architecture": "arm64"}
        line = "UUID: 00010203-0405-0607-0809-0A0B0C0D0E0F (arm64) <bundle>/Contents/MacOS/Main"
        self.assertEqual(compare_uuid_tool(line, [fact])["state"], "agree")
        self.assertEqual(compare_uuid_tool(line.replace("00010203", "ffffffff"), [fact])["state"], "disagreement")
        expected = [{"kind": "load", "path": "@rpath/A.dylib"}, {"kind": "load", "path": "@rpath/A.dylib"}]
        output = "cmd LC_LOAD_DYLIB\n name @rpath/A.dylib (offset 24)\n" * 2
        self.assertEqual(compare_loader_tool(output, expected)["state"], "agree")
        self.assertEqual(compare_loader_tool(output[:len(output)//2], expected)["state"], "disagreement")


if __name__ == "__main__":
    unittest.main()
