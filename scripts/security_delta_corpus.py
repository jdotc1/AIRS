#!/usr/bin/env python3
"""Opt-in corpus qualification protocol. Never launches inspected applications."""
from __future__ import annotations
import argparse
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from urllib.parse import urlsplit

MAX_MANIFEST_BYTES = 262_144
MAX_CASES = 256
COVERAGE_TAGS = frozenset(("simple", "frameworks", "services", "universal", "entitlements",
                           "privacy_manifest", "loader", "signature"))


class CorpusRefusal(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def refuse(code):
    raise CorpusRefusal(code)


def text(value, maximum=4096):
    if not isinstance(value, str) or not value:
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


def load_manifests(directory: Path):
    descriptor = open_directory_no_follow(directory)
    try:
        names = sorted(os.listdir(descriptor))
        if len(names) > MAX_CASES:
            refuse("case_limit")
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
