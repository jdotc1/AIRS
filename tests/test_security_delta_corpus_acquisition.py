from security_delta_fixture_support import owned_temporary_directory
"""Owned archive attacks; the authentic corpus is a separate opt-in input."""
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from security_delta_corpus import CorpusRefusal, admit_archive, extract_archive, capture_chunks, fetch_github_asset


class SecurityDeltaCorpusAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = owned_temporary_directory()
        self.root = Path(self.temp.name)
        self.count = 0

    def tearDown(self):
        self.temp.cleanup()

    def archive(self, entries):
        self.count += 1
        path = self.root / (str(self.count) + ".zip")
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name, content, kind in entries:
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = ((stat.S_IFLNK | 0o777) if kind == "link" else (stat.S_IFREG | 0o644)) << 16
                z.writestr(info, content)
        return path

    def admitted(self, path):
        return admit_archive(path, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_owned_archive_extracts_without_execution(self):
        path = self.archive([("Owned.app/Contents/Info.plist", b"raw", "file")])
        token = self.admitted(path)
        result = extract_archive(token, self.root / "extracted")
        self.assertEqual(result["files"], 1)
        self.assertEqual((self.root / "extracted/Owned.app/Contents/Info.plist").read_bytes(), b"raw")

    def test_same_name_modified_bytes_refuse_digest(self):
        path = self.archive([("Owned.app/file", b"one", "file")])
        expected = hashlib.sha256(path.read_bytes()).hexdigest()
        path.write_bytes(b"modified same name")
        with self.assertRaises(CorpusRefusal) as result:
            admit_archive(path, expected)
        self.assertEqual(result.exception.code, "archive_digest_mismatch")

    def test_escape_absolute_and_external_symlink_refuse(self):
        for i, (name, data, kind) in enumerate([
            ("../escape", b"x", "file"), ("/absolute", b"x", "file"),
            ("Owned.app/link", b"../../outside", "link"), ("Owned.app/link", b"/outside", "link"),
        ]):
            token = self.admitted(self.archive([(name, data, kind)]))
            with self.assertRaises(CorpusRefusal):
                extract_archive(token, self.root / ("bad" + str(i)))
        self.assertFalse((self.root / "escape").exists())

    def test_safe_internal_link_is_preserved_not_followed(self):
        token = self.admitted(self.archive([("Owned.app/Actual/data", b"ok", "file"),
                                             ("Owned.app/Current", b"Actual", "link")]))
        result = extract_archive(token, self.root / "links")
        self.assertEqual(result["symlinks"], 1)
        self.assertTrue((self.root / "links/Owned.app/Current").is_symlink())

    def test_link_ancestor_cannot_receive_regular_file(self):
        token = self.admitted(self.archive([("Owned.app/Current", b"Actual", "link"),
                                             ("Owned.app/Current/data", b"bad", "file")]))
        with self.assertRaises(CorpusRefusal) as result:
            extract_archive(token, self.root / "ancestor")
        self.assertEqual(result.exception.code, "archive_link_ancestor")

    def test_stale_admission_cannot_extract(self):
        path = self.archive([("Owned.app/file", b"ok", "file")]); token = self.admitted(path)
        path.write_bytes(b"changed")
        with self.assertRaises(CorpusRefusal) as result:
            extract_archive(token, self.root / "stale")
        self.assertEqual(result.exception.code, "archive_source_stale")

    def test_cancel_before_open_and_lower_budget(self):
        token = self.admitted(self.archive([("Owned.app/file", b"abcd", "file")]))
        with self.assertRaises(CorpusRefusal) as result:
            extract_archive(token, self.root / "cancelled", cancelled=lambda: True)
        self.assertEqual(result.exception.code, "cancelled")
        self.assertFalse((self.root / "cancelled").exists())
        with self.assertRaises(CorpusRefusal) as result:
            extract_archive(token, self.root / "limited", maximum_bytes=3)
        self.assertEqual(result.exception.code, "archive_expanded_limit")

    def test_archive_symlink_source_refuses(self):
        real = self.archive([("Owned.app/file", b"x", "file")]); alias = self.root / "alias.zip"
        alias.symlink_to(real)
        with self.assertRaises((CorpusRefusal, OSError)):
            admit_archive(alias, "a" * 64)

    def test_nested_archive_stays_opaque_and_is_accounted(self):
        nested = io.BytesIO()
        with zipfile.ZipFile(nested, "w") as z:
            z.writestr("escape", b"x" * 1000)
        token = self.admitted(self.archive([("Owned.app/resources/payload.zip", nested.getvalue(), "file")]))
        result = extract_archive(token, self.root / "opaque")
        self.assertEqual(result["opaque_archives"], 1)
        self.assertFalse((self.root / "opaque/escape").exists())

    def test_unicode_directory_alias_cannot_silently_merge(self):
        token = self.admitted(self.archive([("Owned.app/\u00e9/one", b"a", "file"),
                                             ("Owned.app/e\u0301/two", b"b", "file")]))
        try:
            extract_archive(token, self.root / "unicode")
        except CorpusRefusal as error:
            self.assertEqual(error.code, "archive_path_collision")
        else:
            self.assertEqual(len(os.listdir(self.root / "unicode/Owned.app")), 2,
                             "Filesystem-equivalent exact paths must refuse rather than merge")

    def test_download_capture_hashes_once_and_never_overwrites(self):
        data = b"owned transfer bytes"
        path = self.root / "download.zip"
        token = capture_chunks(iter([data[:4], data[4:]]), path, len(data), hashlib.sha256(data).hexdigest())
        self.assertEqual(token.sha256, hashlib.sha256(data).hexdigest())
        self.assertEqual(path.read_bytes(), data)
        with self.assertRaises((CorpusRefusal, FileExistsError)):
            capture_chunks(iter([b"other"]), path, 5, None)
        self.assertEqual(path.read_bytes(), data)

    def test_download_mismatch_size_and_cancellation_are_not_final_files(self):
        for i, (chunks, size, expected, cancel, code) in enumerate([
            ([b"wrong"], 5, "a" * 64, lambda: False, "archive_digest_mismatch"),
            ([b"too long"], 2, None, lambda: False, "archive_size_mismatch"),
            ([b"x"], 1, None, lambda: True, "cancelled"),
        ]):
            path = self.root / ("refused" + str(i) + ".zip")
            with self.assertRaises(CorpusRefusal) as result:
                capture_chunks(iter(chunks), path, size, expected, cancelled=cancel)
            self.assertEqual(result.exception.code, code)
            self.assertFalse(path.exists())

    def test_invalid_download_budget_does_not_start_network_process(self):
        with patch("security_delta_corpus.subprocess.Popen", side_effect=AssertionError("network started")) as process:
            with self.assertRaises(CorpusRefusal) as result:
                fetch_github_asset("owned/app", 1, 0, self.root / "no.zip", None)
            self.assertEqual(result.exception.code, "archive_byte_limit")
            process.assert_not_called()


if __name__ == "__main__":
    unittest.main()
