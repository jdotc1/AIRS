#!/usr/bin/env python3
"""Independent raw plist/Mach-O oracle. Does not import AIRS analysis or serialization."""
from __future__ import annotations
import base64
import datetime
import hashlib
import math
import plistlib
import struct
import uuid
import xml.etree.ElementTree as ET
import os
import stat
import json
import re
import selectors
import subprocess
import time
import argparse
import tempfile
from pathlib import Path, PurePosixPath
from security_delta_corpus import open_directory_no_follow, file_metadata

MAX_IMAGE_BYTES = 256 * 1_048_576
MAX_PLIST_BYTES = 65_536
MAX_COMMANDS = 4096
MAX_SIGNATURE_BYTES = 512 * 1024


class OracleRefusal(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def reject(code):
    raise OracleRefusal(code)


def check_plist_keys(data):
    """Reject duplicate raw keys before plistlib can collapse them."""
    if data.startswith(b"bplist00"):
        if len(data) < 40:
            reject("plist_unavailable")
        offset_size, ref_size = data[-26:-24]
        count, top, table = struct.unpack_from(">QQQ", data, len(data) - 24)
        if not 1 <= offset_size <= 8 or not 1 <= ref_size <= 8 or not 0 < count <= 10000 or top >= count or table + count * offset_size > len(data) - 32:
            reject("plist_unavailable")
        offsets = [int.from_bytes(data[table + i * offset_size:table + (i + 1) * offset_size], "big") for i in range(count)]
        def length(position):
            if position >= table:
                reject("plist_unavailable")
            value, cursor = data[position] & 15, position + 1
            if value == 15:
                if cursor >= table or data[cursor] >> 4 != 1:
                    reject("plist_unavailable")
                size = 1 << (data[cursor] & 15)
                if size > 8 or cursor + 1 + size > table:
                    reject("plist_unavailable")
                value = int.from_bytes(data[cursor + 1:cursor + 1 + size], "big")
                cursor += 1 + size
            return value, cursor
        for position in offsets:
            if not 8 <= position < table:
                reject("plist_unavailable")
            if data[position] >> 4 != 13:
                continue
            size, cursor = length(position)
            if size > 10000 or cursor + 2 * size * ref_size > table:
                reject("plist_unavailable")
            keys = set()
            for i in range(size):
                ref = int.from_bytes(data[cursor + i * ref_size:cursor + (i + 1) * ref_size], "big")
                if ref >= count:
                    reject("plist_unavailable")
                start = offsets[ref]; kind = data[start] >> 4
                units, begin = length(start)
                width = 2 if kind == 6 else 1
                if kind not in (5, 6, 7) or begin + units * width > table:
                    reject("plist_unavailable")
                try:
                    key = data[begin:begin + units * width].decode({5: "ascii", 6: "utf-16-be", 7: "utf-8"}[kind]).encode("utf-8")
                except UnicodeError:
                    reject("plist_unavailable")
                if key in keys:
                    reject("plist_duplicate_key")
                keys.add(key)
    else:
        if b"<!ENTITY" in data.upper():
            reject("plist_entity_declined")
        try:
            tree = ET.fromstring(data)
        except ET.ParseError:
            reject("plist_unavailable")
        for dictionary in tree.iter("dict"):
            children = list(dictionary)
            if len(children) % 2:
                reject("plist_unavailable")
            keys = set()
            for child in children[::2]:
                if child.tag != "key":
                    reject("plist_unavailable")
                key = (child.text or "").encode("utf-8")
                if key in keys:
                    reject("plist_duplicate_key")
                keys.add(key)


def observe_plist(data):
    if len(data) > MAX_PLIST_BYTES:
        reject("plist_byte_limit")
    check_plist_keys(data)
    try:
        value = plistlib.loads(data)
    except (ValueError, TypeError, OverflowError, RecursionError, plistlib.InvalidFileException):
        reject("plist_unavailable")
    nodes = 0
    def typed(item, depth=0):
        nonlocal nodes
        nodes += 1
        if depth > 32 or nodes > 10000:
            reject("plist_structure_limit")
        if type(item) is bool:
            return {"type": "boolean", "value": item}
        if type(item) is int:
            return {"type": "integer", "decimal": str(item), "representation": "unspecified"}
        if type(item) is float:
            if not math.isfinite(item):
                reject("plist_nonfinite")
            return {"type": "real", "bits": struct.pack(">d", item).hex()}
        if isinstance(item, str):
            item.encode("utf-8", "strict")
            return {"type": "string", "value": item}
        if isinstance(item, bytes):
            return {"type": "data", "base64": base64.b64encode(item).decode("ascii")}
        if isinstance(item, datetime.datetime):
            date = item.replace(tzinfo=datetime.timezone.utc) if item.tzinfo is None else item
            return {"type": "date", "bits": struct.pack(">d", date.timestamp() - 978307200).hex()}
        if isinstance(item, list):
            return {"type": "array", "items": [typed(v, depth + 1) for v in item]}
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                reject("plist_key_unavailable")
            return {"type": "dictionary", "entries": [{"key": k, "value": typed(v, depth + 1)} for k, v in sorted(item.items(), key=lambda pair: pair[0].encode("utf-8"))]}
        reject("plist_type_unavailable")
    if not isinstance(value, dict):
        reject("plist_dictionary_required")
    return {key: typed(item) for key, item in value.items()}


def read_string(data, begin, end):
    if not 0 <= begin < end <= len(data):
        reject("load_string_unavailable")
    marker = data.find(b"\0", begin, end)
    if marker < 0:
        reject("load_string_unavailable")
    try:
        return data[begin:marker].decode("utf-8", "strict")
    except UnicodeError:
        reject("load_string_unavailable")


def signature_facts(data, begin, size):
    if size > MAX_SIGNATURE_BYTES:
        return {"state": "unavailable", "reason": "signature_byte_limit", "offset": begin, "size": size}
    if size < 12 or begin < 0 or begin + size > len(data):
        return {"state": "unavailable", "reason": "signature_region_invalid", "offset": begin, "size": size}
    region = data[begin:begin + size]
    magic, length, count = struct.unpack_from(">III", region)
    if magic != 0xfade0cc0 or length > size or length < 12 or count > 4096 or 12 + count * 8 > length:
        return {"state": "unavailable", "reason": "signature_superblob_invalid", "offset": begin, "size": size}
    result = {"state": "observed", "offset": begin, "size": size,
              "digest": hashlib.sha256(region).hexdigest(), "slots": []}
    for index in range(count):
        kind, offset = struct.unpack_from(">II", region, 12 + index * 8)
        if offset < 12 + count * 8 or offset + 8 > length:
            return {"state": "unavailable", "reason": "signature_slot_invalid", "offset": begin, "size": size}
        blob_magic, blob_length = struct.unpack_from(">II", region, offset)
        if blob_length < 8 or offset + blob_length > length:
            return {"state": "unavailable", "reason": "signature_slot_invalid", "offset": begin, "size": size}
        blob = region[offset:offset + blob_length]
        slot = {"index": index, "type": kind, "magic": blob_magic, "offset": begin + offset,
                "size": blob_length, "digest": hashlib.sha256(blob).hexdigest()}
        if kind == 5:
            try:
                slot["entitlements"] = observe_plist(blob[8:].rstrip(b"\0"))
                slot["entitlements_state"] = "observed"
            except OracleRefusal as error:
                slot["entitlements_state"] = "unavailable"; slot["reason"] = error.code
        elif kind == 0x10005:
            slot["der_semantics"] = "unexamined"
        result["slots"].append(slot)
    return result


def observe_macho(data):
    if len(data) > MAX_IMAGE_BYTES:
        reject("image_byte_limit")
    if len(data) < 4:
        reject("macho_header_unavailable")
    first = data[:4]
    fat = {b"\xca\xfe\xba\xbe": (">", 20), b"\xca\xfe\xba\xbf": (">", 32),
           b"\xbe\xba\xfe\xca": ("<", 20), b"\xbf\xba\xfe\xca": ("<", 32)}
    slices = []
    if first in fat:
        endian, record_size = fat[first]
        if len(data) < 8:
            reject("fat_header_unavailable")
        count = struct.unpack_from(endian + "I", data, 4)[0]
        if not 0 < count <= 16 or 8 + count * record_size > len(data):
            reject("fat_slice_limit_or_header")
        for index in range(count):
            record = 8 + index * record_size
            if record_size == 20:
                cpu, sub, offset, size, alignment = struct.unpack_from(endian + "5I", data, record)
            else:
                cpu, sub, offset, size, alignment, reserved = struct.unpack_from(endian + "IIQQII", data, record)
            if offset < 8 + count * record_size or not size or offset + size > len(data) or any(offset < b + n and b < offset + size for _, _, b, n in slices):
                reject("fat_slice_range_invalid")
            slices.append((cpu, sub, offset, size))
    else:
        slices.append((None, None, 0, len(data)))
    result = {"container_digest": hashlib.sha256(data).hexdigest(), "container_size": len(data), "slices": []}
    kinds = {0xc: "load", 0x80000018: "weak", 0x8000001f: "reexport", 0x80000023: "upward", 0x20: "lazy", 0xd: "installName", 0x8000001c: "rpath"}
    for index, (fat_cpu, fat_sub, offset, size) in enumerate(slices):
        magic = data[offset:offset + 4]
        variants = {b"\xcf\xfa\xed\xfe": ("<", 32), b"\xfe\xed\xfa\xcf": (">", 32),
                    b"\xce\xfa\xed\xfe": ("<", 28), b"\xfe\xed\xfa\xce": (">", 28)}
        if magic not in variants:
            reject("macho_magic_unavailable")
        endian, header_size = variants[magic]
        if size < header_size:
            reject("macho_header_unavailable")
        cpu, sub, filetype, count, command_size, flags = struct.unpack_from(endian + "6I", data, offset + 4)
        if fat_cpu is not None and (cpu != fat_cpu or sub != fat_sub):
            reject("fat_header_identity_mismatch")
        if count > MAX_COMMANDS or command_size > 1_048_576 or header_size + command_size > size:
            reject("load_command_limit_or_bounds")
        arch = "arm64e" if cpu == 0x100000c and sub & 0xffffff == 2 else "arm64" if cpu == 0x100000c else "x86_64" if cpu == 0x1000007 else "unsupported"
        fact = {"architecture": arch, "identity": {"cpu_type": cpu, "cpu_subtype": sub,
                "magic": int.from_bytes(magic, endian == "<" and "little" or "big"),
                "slice_index": index, "offset": offset, "size": size}, "filetype": filetype,
                "slice_digest": result["container_digest"] if offset == 0 and size == len(data) else hashlib.sha256(memoryview(data)[offset:offset + size]).hexdigest(),
                "loader": [], "commands": [], "uuid": None, "signature": {"state": "absent"}}
        cursor, end = offset + header_size, offset + header_size + command_size
        signatures = []
        for command_index in range(count):
            if cursor + 8 > end:
                reject("load_command_unavailable")
            command, length = struct.unpack_from(endian + "II", data, cursor)
            if length < 8 or length % 4 or cursor + length > end:
                reject("load_command_unavailable")
            fact["commands"].append({"index": command_index, "command": command, "offset": cursor, "size": length})
            if command in kinds:
                minimum = 12 if command == 0x8000001c else 24
                if length < minimum:
                    reject("load_command_unavailable")
                name_offset = struct.unpack_from(endian + "I", data, cursor + 8)[0]
                if name_offset < minimum:
                    reject("load_string_unavailable")
                record = {"kind": kinds[command], "command": command, "path": read_string(data, cursor + name_offset, cursor + length),
                          "index": command_index, "offset": cursor, "size": length}
                if minimum == 24:
                    stamp, current, compatibility = struct.unpack_from(endian + "III", data, cursor + 12)
                    record.update(timestamp=stamp, current_version=current, compatibility_version=compatibility)
                fact["loader"].append(record)
            elif command == 0x1b:
                if length != 24 or fact["uuid"] is not None:
                    reject("uuid_command_invalid")
                fact["uuid"] = str(uuid.UUID(bytes=data[cursor + 8:cursor + 24]))
            elif command == 0x1d:
                if length != 16:
                    reject("signature_command_invalid")
                begin, extent = struct.unpack_from(endian + "II", data, cursor + 8)
                if begin + extent > size:
                    fact["signature"] = {"state": "unavailable", "reason": "signature_region_invalid"}
                else:
                    signatures.append((offset + begin, extent))
            cursor += length
        if cursor != end:
            reject("load_command_size_mismatch")
        if len(signatures) == 1:
            fact["signature"] = signature_facts(data, *signatures[0])
        elif len(signatures) > 1:
            fact["signature"] = {"state": "unavailable", "reason": "signature_command_ambiguous"}
        result["slices"].append(fact)
    return result


def observe_bundle(root: Path, *, maximum_files=20000, maximum_fact_bytes=16 * 1_048_576,
                   cancelled=lambda: False):
    """Independent enumeration over no-follow descriptors, with explicit incomplete scope."""
    if cancelled():
        reject("cancelled")
    if type(maximum_files) is not int or not 0 < maximum_files <= 20000:
        reject("oracle_entry_limit")
    if type(maximum_fact_bytes) is not int or not 0 < maximum_fact_bytes <= 16 * 1_048_576:
        reject("oracle_output_limit")
    try:
        descriptor = open_directory_no_follow(root)
    except OSError:
        reject("bundle_source_unavailable")
    result = {"oracle_version": "security-delta-raw-oracle-v1", "images": {}, "plists": {},
              "privacy": {}, "bundle_roots": [""], "exclusions": [],
              "scope": {"state": "complete", "visited_entries": 0, "read_source_bytes": 0, "retained_fact_bytes": 0,
                        "omitted_count": 0, "omitted_count_exact": True, "details_complete": True}}
    scope = result["scope"]
    paths = set()
    directories = {""}
    def limit(reason):
        scope.update(state="truncated", reason=reason, omitted_count=max(1, scope["omitted_count"]),
                     omitted_count_exact=False, details_complete=False)
    def retain(target, key, value):
        size = len(key.encode("utf-8")) + 4 if key is not None else 1
        for chunk in json.JSONEncoder(ensure_ascii=False, allow_nan=False).iterencode(value):
            size += len(chunk.encode("utf-8"))
            if size > maximum_fact_bytes - scope["retained_fact_bytes"]:
                limit("oracle_output_limit"); return False
        scope["retained_fact_bytes"] += size
        if key is None:
            target.append(value)
        else:
            target[key] = value
        return True
    def name_bytes(name):
        try:
            return name.encode("utf-8", "strict")
        except UnicodeError:
            reject("invalid_utf8_path")
    def read(fd, maximum):
        before = file_metadata(os.fstat(fd))
        if before[2] > maximum:
            reject("source_byte_limit")
        if before[2] > 512 * 1_048_576 - scope["read_source_bytes"]:
            reject("oracle_read_byte_limit")
        os.lseek(fd, 0, os.SEEK_SET)
        data = bytearray()
        while True:
            if cancelled():
                reject("cancelled")
            part = os.read(fd, min(65536, maximum + 1 - len(data)))
            if not part:
                break
            data.extend(part)
            if len(data) > maximum:
                reject("source_byte_limit")
        if before != file_metadata(os.fstat(fd)) or len(data) != before[2]:
            reject("source_stale")
        scope["read_source_bytes"] += len(data)
        return bytes(data)
    def visit(directory, prefix, depth):
        if scope.get("reason") == "oracle_output_limit":
            return
        if depth > 32:
            limit("oracle_depth_limit"); return
        try:
            names = os.listdir(directory)
        except OSError:
            retain(result["exclusions"], None, {"path": prefix, "state": "unavailable", "reason": "directory_unavailable"})
            scope["state"] = "partial"; return
        if len(names) > maximum_files - scope["visited_entries"]:
            # Do not allocate a second sorted population after the bounded count fails.
            limit("oracle_entry_limit"); return
        for name in sorted(names, key=name_bytes):
            if scope.get("reason") == "oracle_output_limit":
                return
            if cancelled():
                reject("cancelled")
            if scope["visited_entries"] >= maximum_files:
                limit("oracle_entry_limit"); return
            scope["visited_entries"] += 1
            path = prefix + "/" + name if prefix else name
            if len(name_bytes(path)) > 4096:
                limit("oracle_path_limit"); return
            paths.add(path)
            try:
                item = os.stat(name, dir_fd=directory, follow_symlinks=False)
                if stat.S_ISLNK(item.st_mode):
                    retain(result["exclusions"], None, {"path": path, "state": "excluded", "reason": "symlink_not_followed"})
                    continue
                if stat.S_ISDIR(item.st_mode):
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                    directories.add(path)
                    if name.endswith((".app", ".xpc", ".appex", ".framework", ".bundle")):
                        if not retain(result["bundle_roots"], None, path):
                            os.close(child); return
                    try:
                        visit(child, path, depth + 1)
                    finally:
                        os.close(child)
                    continue
                if not stat.S_ISREG(item.st_mode):
                    retain(result["exclusions"], None, {"path": path, "state": "excluded", "reason": "special_file"})
                    continue
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                try:
                    if scope["read_source_bytes"] > 512 * 1_048_576 - 4:
                        limit("oracle_read_byte_limit"); return
                    header = os.read(fd, 4)
                    scope["read_source_bytes"] += len(header)
                    is_image = header in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xce",
                                          b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf", b"\xbe\xba\xfe\xca", b"\xbf\xba\xfe\xca")
                    candidate = is_image or "/MacOS/" in path or path.startswith("Contents/MacOS/")
                    is_plist = name in ("Info.plist", "PrivacyInfo.xcprivacy")
                    if not candidate and not is_plist:
                        continue
                    try:
                        raw = read(fd, MAX_IMAGE_BYTES if candidate else MAX_PLIST_BYTES)
                        source = {"path": path, "offset": 0, "size": len(raw)}
                        if candidate:
                            observed = observe_macho(raw)
                            source["sha256"] = observed["container_digest"]
                            retain(result["images"], path, {"state": "observed", "source": source, **observed})
                        else:
                            source["sha256"] = hashlib.sha256(raw).hexdigest()
                            values = observe_plist(raw)
                            retain(result["plists"], path, {"state": "observed", "source": source, "values": values})
                    except OracleRefusal as error:
                        if error.code == "cancelled":
                            raise
                        target = result["images"] if candidate else result["plists"]
                        retain(target, path, {"state": "unavailable", "reason": error.code, "source": {"path": path}})
                finally:
                    os.close(fd)
            except OSError:
                retain(result["exclusions"], None, {"path": path, "state": "unavailable", "reason": "source_unavailable"})
                if scope["state"] == "complete":
                    scope["state"] = "partial"
    try:
        visit(descriptor, "", 0)
    finally:
        os.close(descriptor)
    for path, fact in result["plists"].items():
        if path.endswith("PrivacyInfo.xcprivacy"):
            result["privacy"][path] = {"state": fact["state"], "reason": fact.get("reason")}
    for bundle in result["bundle_roots"]:
        resource = (bundle + "/" if bundle else "") + ("Resources" if bundle.endswith(".framework") else "Contents/Resources")
        path = resource + "/PrivacyInfo.xcprivacy"
        if path in result["privacy"]:
            continue
        obstruction = next((x for x in result["exclusions"] if path == x["path"] or path.startswith(x["path"] + "/")), None)
        if obstruction:
            result["privacy"][path] = {"state": obstruction["state"], "reason": obstruction["reason"]}
        elif scope["state"] == "complete" and (resource in directories or resource not in paths):
            result["privacy"][path] = {"state": "absent", "reason": "complete_no_follow_source_scope"}
        else:
            result["privacy"][path] = {"state": "unexamined", "reason": "oracle_scope_incomplete"}
    return result


def compare_uuid_tool(output, slices):
    expected = sorted((s["uuid"].lower(), s["architecture"]) for s in slices if s.get("uuid"))
    observed = sorted((m[0].lower(), m[1]) for m in re.findall(r"UUID: ([0-9A-Fa-f-]{36}) \(([^)]+)\)", output))
    state = "agree" if expected == observed and expected else "disagreement" if expected != observed else "unavailable"
    return {"state": state, "expected": expected, "observed": observed}


def compare_loader_tool(output, loader):
    names = {"LC_LOAD_DYLIB": "load", "LC_LOAD_WEAK_DYLIB": "weak", "LC_REEXPORT_DYLIB": "reexport",
             "LC_LOAD_UPWARD_DYLIB": "upward", "LC_LAZY_LOAD_DYLIB": "lazy", "LC_ID_DYLIB": "installName", "LC_RPATH": "rpath"}
    observed = []
    current = None
    for line in output.splitlines():
        command = re.match(r"\s*cmd (\S+)\s*$", line)
        if command:
            current = names.get(command[1])
        name = re.match(r"\s*(?:name|path) (.*) \(offset \d+\)\s*$", line)
        if name and current:
            observed.append((current, name[1])); current = None
    expected = [(item["kind"], item["path"]) for item in loader]
    return {"state": "agree" if expected == observed else "disagreement", "expected": expected, "observed": observed}


def bounded_tool(arguments, bundle, *, maximum_bytes=1_048_576, timeout=20):
    """Owned Apple display tools only; no shell, undrained pipes, or inspected execution."""
    process = subprocess.Popen(arguments, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    selector = selectors.DefaultSelector(); selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout
    retained = bytearray()
    reason = None
    try:
        while True:
            if time.monotonic() > deadline:
                reason = "tool_timeout"; break
            if not selector.select(0.25):
                continue
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                break
            if len(chunk) > maximum_bytes - len(retained):
                reason = "tool_output_limit"; break
            retained.extend(chunk)
        if reason is None:
            process.wait(timeout=5)
    finally:
        selector.close(); process.stdout.close()
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
    output = retained.decode("utf-8", "replace").replace(str(bundle), "<bundle>")
    return {"state": "unavailable" if reason or process.returncode else "observed",
            "reason": reason, "exit_code": process.returncode, "output": output,
            "retained_bytes": len(retained), "details_complete": reason is None}


def crosscheck_apple_tools(bundle, facts, requested_architecture):
    candidates = [path for path, image in facts["images"].items() if path.startswith("Contents/MacOS/") and image["state"] == "observed"]
    if not candidates:
        return {"state": "unavailable", "reason": "primary_image_unavailable"}
    path = sorted(candidates, key=lambda p: p.encode("utf-8"))[0]
    image = facts["images"][path]
    code = str(bundle / path)
    uuid_fact = bounded_tool(["xcrun", "dwarfdump", "--uuid", code], bundle)
    if uuid_fact["state"] == "observed":
        uuid_fact["comparison"] = compare_uuid_tool(uuid_fact["output"], image["slices"])
    loader_fact = bounded_tool(["xcrun", "otool", "-arch", requested_architecture, "-l", code], bundle)
    slices = [s for s in image["slices"] if s["architecture"] == requested_architecture]
    if loader_fact["state"] == "observed" and len(slices) == 1:
        loader_fact["comparison"] = compare_loader_tool(loader_fact["output"], slices[0]["loader"])
    entitlement_fact = bounded_tool(["codesign", "--display", "--entitlements", ":-", code], bundle)
    return {"source_path": path, "dwarfdump": uuid_fact, "otool": loader_fact, "codesign_display": entitlement_fact,
            "limitations": "Apple display tools supplement raw parsing; no signature verification or trust evaluation, no dynamic loading."}


def write_document(destination, value, *, maximum_bytes=32 * 1_048_576):
    """Publish complete bounded evidence once; preserve an existing destination."""
    if not 1 <= maximum_bytes <= 32 * 1_048_576:
        reject("oracle_document_limit")
    descriptor, temporary = tempfile.mkstemp(prefix=".oracle-", dir=destination.parent)
    count = 0
    try:
        with os.fdopen(descriptor, "wb") as stream:
            for chunk in json.JSONEncoder(sort_keys=True, ensure_ascii=False, allow_nan=False).iterencode(value):
                encoded = chunk.encode("utf-8")
                if len(encoded) > maximum_bytes - count:
                    reject("oracle_document_limit")
                stream.write(encoded); count += len(encoded)
            stream.flush(); os.fsync(stream.fileno())
        os.link(temporary, destination)
    finally:
        os.unlink(temporary)
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--architecture", choices=("arm64", "x86_64"), default="arm64")
    parser.add_argument("--apple-tools", action="store_true")
    arguments = parser.parse_args()
    try:
        result = observe_bundle(arguments.bundle)
        if arguments.apple_tools:
            result["apple_tools"] = crosscheck_apple_tools(arguments.bundle, result, arguments.architecture)
        count = write_document(arguments.output, result)
        print(json.dumps({"status": "captured", "scope": result["scope"], "images": len(result["images"]),
                          "plists": len(result["plists"]), "output_bytes": count}, sort_keys=True))
        return 0
    except (OracleRefusal, OSError) as error:
        print(json.dumps({"status": "refused", "code": getattr(error, "code", "oracle_io_unavailable")}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
