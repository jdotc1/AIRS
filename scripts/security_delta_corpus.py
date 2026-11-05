#!/usr/bin/env python3
"""Opt-in corpus qualification protocol. Never launches inspected applications."""
from __future__ import annotations
import argparse
import base64
import binascii
import math
import hashlib
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import zipfile
import posixpath
import uuid
import selectors
import subprocess
import time
from urllib.parse import urlsplit

MAX_MANIFEST_BYTES = 262_144
MAX_CASES = 256
MAX_ARCHIVE_BYTES = 128 * 1_048_576
MAX_EXPANDED_BYTES = 1_073_741_824
MAX_ARCHIVE_ENTRIES = 20_000
COVERAGE_TAGS = frozenset(("simple", "frameworks", "services", "universal", "entitlements",
                           "privacy_manifest", "loader", "signature"))


class CorpusRefusal(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def refuse(code):
    raise CorpusRefusal(code)


def text(value, maximum=4096, *, allow_empty=False):
    if not isinstance(value, str) or (not value and not allow_empty):
        refuse("manifest_value")
    try:
        raw = value.encode("utf-8", "strict")
    except UnicodeError:
        refuse("invalid_utf8")
    if len(raw) > maximum:
        refuse("manifest_string_limit")
    return value


def relative_path(value):
    text(value)
    if "\\" in value or "\x00" in value or any(p in ("", ".", "..") for p in value.split("/")) or PurePosixPath(value).is_absolute():
        refuse("unsafe_relative_path")
    return value


def source_url(value):
    text(value, 8192)
    try:
        p = urlsplit(value)
        valid = p.scheme == "https" and p.hostname and not p.username and not p.password and not p.query and not p.fragment and p.port in (None, 443)
    except ValueError:
        valid = False
    if not valid or any(ord(c) < 33 for c in value):
        refuse("unsupported_source_url")
    return value


def fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or set(value) - set(required) - set(optional):
        refuse("manifest_fields")


def digest(value):
    if not isinstance(value, str) or re.fullmatch("[0-9a-f]{64}", value) is None:
        refuse("invalid_digest")
    return value


def timestamp(value):
    text(value, 32)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        refuse("invalid_timestamp")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        refuse("invalid_timestamp")


@dataclass(frozen=True)
class CorpusSource:
    version: str
    release_url: str
    sha256: str
    license_note: str
    license_url: str
    app_relative_path: str
    published_at: str
    archive_kind: str


@dataclass(frozen=True)
class CorpusManifest:
    case_id: str
    publisher: str
    application: str
    architecture: str
    previous: CorpusSource
    current: CorpusSource
    coverage_tags: tuple[str, ...]
    expected_json: bytes
    canonical_bytes: bytes


def validate_expected_fact(fact, source_digests):
    fields(fact, ("side", "source_path", "source_sha256", "archive_sha256", "locator", "state", "expected_value", "adjudicator"))
    side=fact["side"]
    if side not in ("previous", "current") or fact["archive_sha256"] != source_digests[side]:
        refuse("fact_source_binding_mismatch")
    relative_path(fact["source_path"]); digest(fact["source_sha256"]); text(fact["adjudicator"])
    locator=fact["locator"]
    fields(locator, ("kind",), ("key", "offset", "length", "slice"))
    if locator["kind"] not in ("plist_key", "macho_command", "signature_slot", "source_presence"):
        refuse("invalid_fact_locator")
    if locator["kind"] == "plist_key": text(locator.get("key"))
    for key in ("offset", "length"):
        if key in locator and (type(locator[key]) is not int or not 0 <= locator[key] <= 536870912):
            refuse("invalid_fact_locator")
    if "slice" in locator:
        fields(locator["slice"], ("cpu_type", "cpu_subtype", "magic", "index", "offset", "size"))
        if any(type(v) is not int or not 0 <= v <= 5368709120 for v in locator["slice"].values()): refuse("invalid_fact_locator")
    if fact["state"] not in ("observed", "absent", "unavailable", "unexamined", "excluded", "ambiguous", "stale", "truncated"):
        refuse("invalid_fact_state")
    def typed(value, depth=0):
        if depth > 32: refuse("typed_depth_limit")
        if not isinstance(value, dict) or "type" not in value: refuse("invalid_fact_value")
        kind=value["type"]
        value_keys={"boolean":("value",),"integer":("decimal","representation"),"real":("bits",),"date":("bits",),"string":("value",),"data":("base64",),"array":("items",),"dictionary":("entries",)}
        if not isinstance(kind,str) or kind not in value_keys: refuse("invalid_fact_value")
        fields(value, ("type",)+value_keys[kind])
        if kind=="boolean" and type(value["value"]) is not bool: refuse("invalid_fact_value")
        if kind=="integer":
            number=text(value["decimal"], 21)
            if re.fullmatch(r"-?(0|[1-9][0-9]*)",number) is None or not -(1<<63) <= int(number) < 1<<64 or value["representation"] != "unspecified": refuse("invalid_fact_value")
        if kind in ("real","date") and re.fullmatch(r"[0-9a-f]{16}",text(value["bits"],16)) is None: refuse("invalid_fact_value")
        if kind in ("real","date") and not math.isfinite(struct.unpack(">d",bytes.fromhex(value["bits"]))[0]): refuse("invalid_fact_value")
        if kind=="data":
            try:
                encoded=value["base64"]
                if not isinstance(encoded,str) or base64.b64encode(base64.b64decode(encoded,validate=True)).decode("ascii") != encoded: refuse("invalid_fact_value")
            except (ValueError,binascii.Error): refuse("invalid_fact_value")
        if kind in ("string","data"): text(value["value" if kind=="string" else "base64"], 65536, allow_empty=True)
        if kind=="array":
            if not isinstance(value["items"],list): refuse("invalid_fact_value")
            for child in value["items"]: typed(child,depth+1)
        if kind=="dictionary":
            if not isinstance(value["entries"],list): refuse("invalid_fact_value")
            seen=set()
            for entry in value["entries"]:
                fields(entry,("key","value")); key=text(entry["key"]).encode("utf-8")
                if key in seen: refuse("duplicate_fact_key")
                seen.add(key);typed(entry["value"],depth+1)
    if fact["state"]=="observed": typed(fact["expected_value"])
    elif fact["expected_value"] is not None: refuse("invalid_fact_state")


def decode_manifest(data: bytes) -> CorpusManifest:
    if len(data) > MAX_MANIFEST_BYTES:
        refuse("manifest_byte_limit")
    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                refuse("duplicate_json_key")
            result[key] = value
        return result
    try:
        doc = json.loads(data.decode("utf-8", "strict"), object_pairs_hook=pairs,
                         parse_constant=lambda _: refuse("nonfinite_number"))
    except UnicodeError:
        refuse("invalid_utf8")
    except RecursionError:
        refuse("manifest_structure_limit")
    except json.JSONDecodeError:
        refuse("invalid_json")
    nodes = 0
    def bound(value, depth=0):
        nonlocal nodes
        nodes += 1
        if depth > 24 or nodes > 8192:
            refuse("manifest_structure_limit")
        if isinstance(value, str):
            text(value) if value else None
        elif isinstance(value, (dict, list)):
            if len(value) > 4096:
                refuse("manifest_collection_limit")
            if isinstance(value, dict):
                for k, v in value.items():
                    text(k, 256); bound(v, depth + 1)
            else:
                for v in value:
                    bound(v, depth + 1)
    bound(doc)
    fields(doc, ("schema_version", "case_id", "publisher", "application", "selection", "previous", "current", "expected", "coverage_tags"),
           ("language_evidence", "oracle", "retrieved_at"))
    if type(doc["schema_version"]) is not int or doc["schema_version"] != 1:
        refuse("unsupported_schema_version")
    for key in ("case_id", "publisher", "application"):
        if re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,191}", text(doc[key], 192)) is None:
            refuse("invalid_case_identity")
    fields(doc["selection"], ("architecture", "purpose"))
    selection = doc["selection"]
    if selection["architecture"] not in ("arm64", "x86_64") or selection["purpose"] != "authentic_release_pair":
        refuse("invalid_selection")
    def source(raw):
        keys = tuple(CorpusSource.__dataclass_fields__)
        fields(raw, keys)
        text(raw["version"], 128); source_url(raw["release_url"]); digest(raw["sha256"])
        text(raw["license_note"]); source_url(raw["license_url"]); relative_path(raw["app_relative_path"])
        timestamp(raw["published_at"])
        if raw["archive_kind"] != "zip":
            refuse("unsupported_archive_kind")
        return CorpusSource(**raw)
    a, b = source(doc["previous"]), source(doc["current"])
    if a.sha256 == b.sha256:
        refuse("duplicate_release_bytes")
    if timestamp(a.published_at) >= timestamp(b.published_at) or a.version == b.version:
        refuse("comparison_direction")
    expected = doc["expected"]
    fields(expected, ("adjudication", "source_digests", "declaration_facts", "expected_refusals"), ("adjudicator",))
    fields(expected["source_digests"], ("previous", "current"))
    if expected["source_digests"] != {"previous": a.sha256, "current": b.sha256}:
        refuse("source_binding_mismatch")
    if expected["adjudication"] not in ("pending", "independently_adjudicated"):
        refuse("invalid_adjudication")
    for key in ("declaration_facts", "expected_refusals"):
        if not isinstance(expected[key], list) or len(expected[key]) > 1024:
            refuse("manifest_collection_limit")
    for fact in expected["declaration_facts"]:
        validate_expected_fact(fact, expected["source_digests"])
    for refusal in expected["expected_refusals"]:
        fields(refusal, ("side", "source_path", "archive_sha256", "code", "adjudicator"))
        side=refusal["side"]
        if side not in ("previous", "current") or refusal["archive_sha256"] != expected["source_digests"][side]: refuse("fact_source_binding_mismatch")
        relative_path(refusal["source_path"]);text(refusal["code"],128);text(refusal["adjudicator"])
    if expected["adjudication"] == "independently_adjudicated":
        text(expected.get("adjudicator"))
        if not expected["declaration_facts"]: refuse("unjustified_adjudication")
    tags = doc["coverage_tags"]
    if not isinstance(tags, list) or len(tags) > len(COVERAGE_TAGS):
        refuse("manifest_collection_limit")
    if any(not isinstance(t, str) or t not in COVERAGE_TAGS for t in tags) or len(set(tags)) != len(tags):
        refuse("invalid_coverage_tags")
    encode = lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return CorpusManifest(doc["case_id"], doc["publisher"], doc["application"], selection["architecture"],
                          a, b, tuple(tags), encode(expected), encode(doc))


def validate_corpus(manifests):
    if len(manifests) > MAX_CASES:
        refuse("case_limit")
    seen = set()
    for item in manifests:
        if item.case_id in seen:
            refuse("duplicate_case_id")
        seen.add(item.case_id)
    return tuple(sorted(manifests, key=lambda m: m.case_id.encode("utf-8")))


def open_directory_no_follow(directory: Path):
    """Walk every directory segment; O_NOFOLLOW on the last segment is insufficient."""
    path = directory.absolute()
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            if part in ("", ".", ".."):
                refuse("unsafe_relative_path")
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_fd
        result, descriptor = descriptor, None
        return result
    finally:
        if descriptor is not None:
            os.close(descriptor)


def bounded_directory_names(descriptor, maximum):
    """Retain at most the admitted population plus one sentinel, never list all."""
    names = []
    with os.scandir(descriptor) as entries:
        for entry in entries:
            if len(names) == maximum:
                refuse("directory_entry_limit")
            names.append(entry.name)
    return names


def load_manifests(directory: Path):
    descriptor = open_directory_no_follow(directory)
    try:
        try:
            names = sorted(bounded_directory_names(descriptor, MAX_CASES))
        except CorpusRefusal as error:
            if error.code == "directory_entry_limit": refuse("case_limit")
            raise
        result = []
        for name in names:
            if not name.endswith(".json"):
                continue
            try:
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
            except OSError:
                refuse("manifest_source_unavailable")
            try:
                before = os.fstat(fd)
                if not stat.S_ISREG(before.st_mode):
                    refuse("manifest_special_file")
                data = os.read(fd, MAX_MANIFEST_BYTES + 1)
                after = os.fstat(fd)
                if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
                    refuse("manifest_source_stale")
                result.append(decode_manifest(data))
            finally:
                os.close(fd)
        return validate_corpus(result)
    finally:
        os.close(descriptor)


def file_metadata(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_mode)


def open_regular_no_follow(path: Path):
    parent = open_directory_no_follow(path.absolute().parent)
    try:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        refuse("archive_special_file")
    return descriptor


@dataclass(frozen=True)
class AdmittedArchive:
    path: Path
    sha256: str
    metadata: tuple[int, ...]


def capture_chunks(chunks, destination: Path, expected_size: int, expected_sha256: str | None,
                   *, cancelled=lambda: False):
    """First acquisition hashes streamed bytes once; publication follows only complete admission."""
    if type(expected_size) is not int or not 0 < expected_size <= MAX_ARCHIVE_BYTES:
        refuse("archive_byte_limit")
    if expected_sha256 is not None:
        digest(expected_sha256)
    if cancelled():
        refuse("cancelled")
    parent = open_directory_no_follow(destination.absolute().parent)
    temporary = ".partial-" + str(uuid.uuid4())
    try:
        try:
            os.stat(destination.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            refuse("archive_destination_exists")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        value = hashlib.sha256()
        count = 0
        try:
            with os.fdopen(descriptor, "wb") as output:
                for chunk in chunks:
                    if cancelled():
                        refuse("cancelled")
                    count += len(chunk)
                    if count > expected_size or count > MAX_ARCHIVE_BYTES:
                        refuse("archive_size_mismatch")
                    output.write(chunk)
                    value.update(chunk)
                if count != expected_size:
                    refuse("archive_size_mismatch")
                actual = value.hexdigest()
                if expected_sha256 is not None and actual != expected_sha256:
                    refuse("archive_digest_mismatch")
                output.flush()
                os.fsync(output.fileno())
            # Hard-link publication refuses any racing destination, without replacement.
            os.link(temporary, destination.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
            os.unlink(temporary, dir_fd=parent)
            metadata = file_metadata(os.stat(destination.name, dir_fd=parent, follow_symlinks=False))
            return AdmittedArchive(destination.absolute(), actual, metadata)
        except BaseException:
            # Only the owned unpublished temporary is removed; existing destinations survive.
            try:
                os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError:
                pass
            raise
    finally:
        os.close(parent)


def fetch_github_asset(repository: str, asset_id: int, size: int, destination: Path,
                       expected_sha256: str | None, *, cancelled=lambda: False):
    """One bounded authenticated official-asset download; credentials never enter records."""
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) is None or type(asset_id) is not int or asset_id <= 0:
        refuse("unsupported_source_url")
    if type(size) is not int or not 0 < size <= MAX_ARCHIVE_BYTES:
        refuse("archive_byte_limit")
    if expected_sha256 is not None:
        digest(expected_sha256)
    if cancelled():
        refuse("cancelled")
    process = subprocess.Popen(["gh", "api", f"repos/{repository}/releases/assets/{asset_id}",
                                "-H", "Accept: application/octet-stream"],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + 180
    def chunks():
        while True:
            if cancelled():
                refuse("cancelled")
            if time.monotonic() > deadline:
                refuse("acquisition_timeout")
            if not selector.select(0.25):
                continue
            value = os.read(process.stdout.fileno(), 65536)
            if not value:
                break
            yield value
        if process.wait(timeout=5) != 0:
            refuse("source_unavailable")
    try:
        return capture_chunks(chunks(), destination, size, expected_sha256, cancelled=cancelled)
    finally:
        selector.close()
        process.stdout.close()
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)


def admit_archive(path: Path, expected_sha256: str, cancelled=lambda: False):
    digest(expected_sha256)
    if cancelled():
        refuse("cancelled")
    descriptor = open_regular_no_follow(path)
    try:
        before = file_metadata(os.fstat(descriptor))
        if before[2] > MAX_ARCHIVE_BYTES:
            refuse("archive_byte_limit")
        value = hashlib.sha256()
        count = 0
        while True:
            if cancelled():
                refuse("cancelled")
            chunk = os.read(descriptor, 65536)
            if not chunk:
                break
            count += len(chunk)
            if count > MAX_ARCHIVE_BYTES:
                refuse("archive_byte_limit")
            value.update(chunk)
        if before != file_metadata(os.fstat(descriptor)) or count != before[2]:
            refuse("archive_source_stale")
        if value.hexdigest() != expected_sha256:
            refuse("archive_digest_mismatch")
        return AdmittedArchive(path.absolute(), expected_sha256, before)
    finally:
        os.close(descriptor)


def zip_directory_budget(stream):
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(max(0, size - 65557))
    tail = stream.read(65557)
    index = tail.rfind(b"PK\x05\x06")
    if index < 0 or index + 22 > len(tail):
        refuse("archive_invalid_zip")
    disk, directory_disk, disk_count, count, directory_size, directory_offset, comment = struct.unpack_from("<4H2IH", tail, index + 4)
    if disk or directory_disk or disk_count != count or count == 65535:
        refuse("archive_unsupported_zip")
    if count > MAX_ARCHIVE_ENTRIES or directory_size > 16 * 1_048_576:
        refuse("archive_entry_limit")
    eocd = max(0, size - 65557) + index
    if eocd + 22 + comment != size or directory_offset + directory_size != eocd:
        refuse("archive_invalid_zip")
    stream.seek(0)


def extraction_directory(parent, relative, identities):
    descriptor = os.dup(parent)
    prefix = []
    try:
        for part in relative:
            prefix.append(part)
            try:
                os.mkdir(part, mode=0o755, dir_fd=descriptor)
            except FileExistsError:
                pass
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            info = os.fstat(next_fd)
            identity = (info.st_dev, info.st_ino)
            exact = "/".join(prefix).encode("utf-8")
            if identity in identities and identities[identity] != exact:
                os.close(next_fd)
                refuse("archive_path_collision")
            identities[identity] = exact
            os.close(descriptor)
            descriptor = next_fd
        result, descriptor = descriptor, None
        return result
    finally:
        if descriptor is not None:
            os.close(descriptor)


def extract_archive(admitted: AdmittedArchive, destination: Path, *, maximum_bytes=MAX_EXPANDED_BYTES,
                    cancelled=lambda: False):
    """Extract once into a new private directory; never execute or follow archive links."""
    if cancelled():
        refuse("cancelled")
    if type(maximum_bytes) is not int or not 0 < maximum_bytes <= MAX_EXPANDED_BYTES:
        refuse("invalid_archive_limit")
    descriptor = open_regular_no_follow(admitted.path)
    if file_metadata(os.fstat(descriptor)) != admitted.metadata:
        os.close(descriptor)
        refuse("archive_source_stale")
    with os.fdopen(descriptor, "rb") as stream:
        zip_directory_budget(stream)
        try:
            archive = zipfile.ZipFile(stream)
        except (zipfile.BadZipFile, UnicodeError):
            refuse("archive_invalid_zip")
        with archive:
            nodes = {}
            total = 0
            for entry in archive.infolist():
                name = entry.filename[:-1] if entry.is_dir() else entry.filename
                relative_path(name)
                if name in nodes:
                    refuse("archive_duplicate_path")
                kind = stat.S_IFMT(entry.external_attr >> 16)
                if kind not in (0, stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK) or entry.flag_bits & 1:
                    refuse("archive_unsupported_entry")
                total += entry.file_size
                if entry.file_size > 256 * 1_048_576 or total > maximum_bytes:
                    refuse("archive_expanded_limit")
                if len(nodes) >= MAX_ARCHIVE_ENTRIES:
                    refuse("archive_entry_limit")
                node_kind = "directory" if entry.is_dir() else "link" if kind == stat.S_IFLNK else "file"
                target = None
                if node_kind == "link":
                    if entry.file_size > 4096:
                        refuse("archive_link_limit")
                    try:
                        target = archive.read(entry).decode("utf-8", "strict")
                    except (UnicodeError, zipfile.BadZipFile):
                        refuse("archive_invalid_link")
                    if not target or target.startswith("/") or "\\" in target or "\x00" in target:
                        refuse("archive_symlink_escape")
                    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
                    if resolved == ".." or resolved.startswith("../"):
                        refuse("archive_symlink_escape")
                nodes[name] = (entry, node_kind, target)
            for name in nodes:
                parent = PurePosixPath(name).parent
                while str(parent) != ".":
                    if str(parent) in nodes and nodes[str(parent)][1] != "directory":
                        refuse("archive_link_ancestor")
                    parent = parent.parent
            if cancelled():
                refuse("cancelled")
            parent = open_directory_no_follow(destination.absolute().parent)
            try:
                os.mkdir(destination.name, mode=0o700, dir_fd=parent)
                root = os.open(destination.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            finally:
                os.close(parent)
            files = links = opaque = 0
            directory_identities = {}
            try:
                for name, (entry, kind, target) in sorted(nodes.items(), key=lambda item: item[0].encode("utf-8")):
                    if cancelled():
                        refuse("cancelled")
                    parts = PurePosixPath(name).parts
                    directory = extraction_directory(root, parts if kind == "directory" else parts[:-1], directory_identities)
                    try:
                        if kind == "directory":
                            continue
                        if kind == "link":
                            os.symlink(target, parts[-1], dir_fd=directory)
                            links += 1
                            continue
                        try:
                            out = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                          (entry.external_attr >> 16) & 0o777 or 0o644, dir_fd=directory)
                        except FileExistsError:
                            refuse("archive_path_collision")
                        with os.fdopen(out, "wb") as output, archive.open(entry) as source:
                            count = 0
                            while True:
                                if cancelled():
                                    refuse("cancelled")
                                chunk = source.read(65536)
                                if not chunk:
                                    break
                                count += len(chunk)
                                if count > entry.file_size:
                                    refuse("archive_size_mismatch")
                                output.write(chunk)
                            if count != entry.file_size:
                                refuse("archive_size_mismatch")
                        files += 1
                        if name.lower().endswith((".zip", ".tar", ".gz", ".xz", ".dmg", ".pkg")):
                            opaque += 1
                    finally:
                        os.close(directory)
            except zipfile.BadZipFile:
                refuse("archive_crc_mismatch")
            finally:
                os.close(root)
            if file_metadata(os.fstat(stream.fileno())) != admitted.metadata:
                refuse("archive_source_stale")
            return {"files": files, "symlinks": links, "expanded_bytes": total,
                    "opaque_archives": opaque, "detail_list_complete": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-manifests", type=Path)
    args = parser.parse_args()
    if args.check_manifests is None:
        parser.error("Select an explicit operation")
    try:
        records = load_manifests(args.check_manifests)
        print(json.dumps({"status": "validated", "cases": len(records), "case_ids": [m.case_id for m in records]}, sort_keys=True))
        return 0
    except (CorpusRefusal, OSError) as error:
        print(json.dumps({"status": "refused", "code": getattr(error, "code", "manifest_source_unavailable")}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
