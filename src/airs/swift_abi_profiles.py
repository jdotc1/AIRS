"""Bounded selected-image Swift metadata and independently qualified ABI tuples.

Syntax is not ABI evidence. Registry membership is an internal reviewed capability;
callers cannot certify a declaration by supplying a dictionary of register names.
"""
from dataclasses import dataclass, replace
import struct
from types import MappingProxyType

from .swift_declaration_profiles import (
    BroadDeclarationResult, CallableKind, SwiftCallableIdentity, parse_broad_declaration,
)
from .types import InputError


@dataclass(frozen=True, slots=True)
class ABILimits:
    max_entries: int = 1024
    max_context_depth: int = 16
    max_string_bytes: int = 256
    max_work: int = 32768
    max_sections: int = 256
    max_function_bytes: int = 1024
    max_functions: int = 10000


@dataclass(frozen=True, slots=True)
class ABICapabilities:
    identifier: str
    architecture: str
    language_mode: str
    execution: str
    error_convention: str
    error_register: str
    research_only: bool = True
    async_supported: bool = False
    typed_throws_supported: bool = False
    witness_dispatch_supported: bool = False
    virtual_dispatch_supported: bool = False
    unproved_generics_supported: bool = False


SYNC_ARM64_SWIFT6 = ABICapabilities(
    'swift6-arm64-sync-untyped-research-v1', 'arm64', '6', 'synchronous',
    'ordinary_untyped_throws', 'x21')
STABLE_ARM64_SWIFT6 = replace(SYNC_ARM64_SWIFT6,
    identifier='swift6-arm64-sync-untyped-stable-research-v2')
ABI_PROFILES = MappingProxyType({p.identifier: p for p in (SYNC_ARM64_SWIFT6, STABLE_ARM64_SWIFT6)})


@dataclass(frozen=True, slots=True)
class ABICallsiteQualification:
    """Work request, never a caller-issued ABI certificate."""
    profile_id: str
    call_pc: int
    caller_start: int
    target_pc: int
    callsite_capability: object | None = None
ABI_REFERENCES = (
    'https://github.com/swiftlang/swift/blob/main/docs/ABI/CallingConventionSummary.rst',
    'https://github.com/swiftlang/swift/blob/main/docs/ABI/CallingConvention.rst',
    'https://github.com/swiftlang/swift/blob/main/include/swift/ABI/Metadata.h',
    'https://github.com/swiftlang/swift/blob/main/include/swift/ABI/MetadataValues.h',
)


@dataclass(frozen=True, slots=True)
class LoweringObservation:
    evidence_id: str
    slice_sha256: str
    source_sha256: str
    compiler: str
    target: str
    optimization: str
    symbol: str
    parameter_types: tuple[str, ...]
    result_type: str
    parameter_locations: tuple[str, ...]
    result_location: str
    # PC and raw little-endian instruction bytes retained from existing objdump.
    observations: tuple[tuple[int, str, str], ...]
    source_capture: str
    disassembly_capture: str
    callable_kind: CallableKind = CallableKind.FREE_FUNCTION
    context: tuple[tuple[str, str], ...] = ()
    receiver_location: str | None = None


# These are reviewed observations, not a symbol-name lookup that fabricates
# evidence. Source, compiler receipt and existing disassembly were inspected;
# no compiler, disassembler or binary provenance pass was rerun.
_OWNED_SOURCE = '8bbf3cb29081cc00045b62df203944101f9340716db8dae3eff628dddab60894'
_COMPILER = 'Apple Swift 6.4.2 (swiftlang-6.4.2.1.9 clang-2100.4.1.1)'
_SYMBOL = '$s10BroadOwned15broad_transformyS2iKF'
LOWERING_QUALIFICATIONS = MappingProxyType({
    'owned-initial-v1-O-transform-int': LoweringObservation(
        'owned-initial-v1-O-transform-int',
        'ebdc1bbab109b9721a1024aa29210bf9ddd33589f833a7204faecc8e81d32857',
        _OWNED_SOURCE, _COMPILER, 'arm64-apple-macosx14.0', '-O', _SYMBOL,
        ('Swift.Int',), 'Swift.Int', ('x0',), 'x0',
        ((0xbe0, '1f0014eb', 'Int argument comparison in x0'),
         (0xc0c, 'f50300aa', 'ordinary error assigned to x21'),
         (0xc1c, '0004008b', 'Int success result in x0')),
        'broad-swift-initial-v1/BroadOwned.swift:3-5',
        'broad-swift-initial-v1/objdump-O.txt:18-44'),
    'owned-initial-v1-Onone-transform-int': LoweringObservation(
        'owned-initial-v1-Onone-transform-int',
        '051cd7cab111884c8d2b53dc1ef06920948e9ba5b72e6e6e21dc9161c47b9230',
        _OWNED_SOURCE, _COMPILER, 'arm64-apple-macosx14.0', '-Onone', _SYMBOL,
        ('Swift.Int',), 'Swift.Int', ('x0',), 'x0',
        ((0xc70, 'e00f00f9', 'Int argument saved from x0'),
         (0xcbc, 'f50300aa', 'ordinary error assigned to x21'),
         (0xcf0, '007d099b', 'Int success result in x0')),
        'broad-swift-initial-v1/BroadOwned.swift:3-5',
        'broad-swift-initial-v1/objdump-Onone.txt:34-76'),
    'owned-initial-v1-O-struct0080': LoweringObservation(
        'owned-initial-v1-O-struct0080',
        'ebdc1bbab109b9721a1024aa29210bf9ddd33589f833a7204faecc8e81d32857',
        _OWNED_SOURCE, _COMPILER, 'arm64-apple-macosx14.0', '-O',
        '$s10BroadOwned0A9Owner0080V15broad_case_0080ySis5Int32V_SbSdtKF',
        ('Swift.Int32', 'Swift.Bool', 'Swift.Double'), 'Swift.Int', ('w0', 'x1', 'd0'), 'x0',
        ((0x74ec, '880240f9', 'indirect value receiver addressed by x20'),
         (0x74f0, '29004092', 'Bool argument bit in x1'),
         (0x74f4, '29c1208b', 'Int32 argument in w0'),
         (0x74f8, '0a00789e', 'Double argument in d0'),
         (0x7530, 'f50300aa', 'ordinary error assigned to x21'),
         (0x7540, '804e0191', 'Int success result in x0'),
         (0x757c, '150080d2c9ffff97b50000b4', 'caller clears x21, direct calls, tests x21')),
        'broad-swift-initial-v1/BroadOwned.swift:1127-1135',
        'broad-swift-initial-v1/objdump-O.txt:7235-7295',
        CallableKind.STRUCT_INSTANCE_METHOD, (('BroadOwner0080', 'struct'),), 'indirect x20'),
    'owned-initial-v1-O-enum0180': LoweringObservation(
        'owned-initial-v1-O-enum0180',
        'ebdc1bbab109b9721a1024aa29210bf9ddd33589f833a7204faecc8e81d32857',
        _OWNED_SOURCE, _COMPILER, 'arm64-apple-macosx14.0', '-O',
        '$s10BroadOwned0A9Owner0180O15broad_case_0180ySis5Int32V_SbSdtKF',
        ('Swift.Int32', 'Swift.Bool', 'Swift.Double'), 'Swift.Int', ('w0', 'x1', 'd0'), 'x0',
        ((0x102f0, '880240f9', 'indirect enum receiver addressed by x20'),
         (0x102f4, '29004092', 'Bool argument bit in x1'),
         (0x102f8, '29c1208b', 'Int32 argument in w0'),
         (0x102fc, '0a00789e', 'Double argument in d0'),
         (0x10338, 'f50300aa', 'ordinary error assigned to x21'),
         (0x10348, '00dd0291', 'Int success result in x0'),
         (0x10384, '150080d2c8ffff97b50000b4', 'caller clears x21, direct calls, tests x21')),
        'broad-swift-initial-v1/BroadOwned.swift:2727-2736',
        'broad-swift-initial-v1/objdump-O.txt:16924-16998',
        CallableKind.ENUM_INSTANCE_METHOD, (('BroadOwner0180', 'enum'),), 'indirect x20'),
    'owned-initial-v1-O-class0249': LoweringObservation(
        'owned-initial-v1-O-class0249',
        'ebdc1bbab109b9721a1024aa29210bf9ddd33589f833a7204faecc8e81d32857',
        _OWNED_SOURCE, _COMPILER, 'arm64-apple-macosx14.0', '-O',
        '$s10BroadOwned0A9Owner0249C15broad_case_0249ySis5Int32V_S2itKF',
        ('Swift.Int32', 'Swift.Int', 'Swift.Int'), 'Swift.Int', ('w0', 'x1', 'x2'), 'x0',
        ((0x16fb8, '28c0208b', 'Int32 w0 and Int x1 arguments'),
         (0x16fbc, '890a40f9', 'class reference receiver in x20'),
         (0x16fc0, '0801028b', 'Int argument in x2'),
         (0x16fc8, '00f103f1', 'Int success result in x0'),
         (0x16ff8, 'f50300aa', 'ordinary error assigned to x21'),
         (0x17058, '150080d2d4ffff97b50000b4', 'caller clears x21, direct calls, tests x21')),
        'broad-swift-initial-v1/BroadOwned.swift:3886-3894',
        'broad-swift-initial-v1/objdump-O.txt:24353-24411',
        CallableKind.CLASS_INSTANCE_METHOD, (('BroadOwner0249', 'class'),), 'reference x20'),
})


class _Unresolved(Exception):
    pass


class _MetadataReader:
    def __init__(self, image, limits):
        self.image, self.limits, self.work = image, limits, 0
        self.footprint = {}

    def read(self, pc, size):
        # Charge before access, including failed accesses. Prevent address wrap.
        if size < 0 or pc < 0 or pc + size > 1 << 64:
            raise _Unresolved('malformed_nominal_metadata')
        self.work += size
        if self.work > self.limits.max_work:
            raise _Unresolved('metadata_resource_limit')
        if len(self.image.sections) > self.limits.max_sections:
            raise _Unresolved('metadata_resource_limit')
        mappings = [(index, section) for index, section in enumerate(self.image.sections)
                    if section.address <= pc and pc + size <= section.end]
        if len(mappings) != 1:
            raise _Unresolved('ambiguous_or_unmapped_abi_bytes')
        index, section = mappings[0]
        offset = section.file_offset + pc - section.address
        if (section.address < 0 or section.size < 0 or section.end > 1 << 64
                or section.file_offset < 0 or offset < 0
                or (section.flags & 0xff) in (0x1, 0xc, 0x12)
                or offset + size > self.image.slice_size
                or offset + size > len(self.image.data)):
            raise _Unresolved('abi_bytes_outside_selected_slice')
        raw = self.image.bytes_at(pc, size)
        if len(raw) != size:
            raise _Unresolved('malformed_nominal_metadata')
        for delta, byte in enumerate(raw):
            self.footprint[index, pc + delta] = byte
        return raw

    def binding(self):
        ranges = []
        previous_index = None
        for (index, pc), byte in sorted(self.footprint.items()):
            if ranges and index == previous_index and pc == ranges[-1]['pc'] + len(ranges[-1]['raw']) // 2:
                ranges[-1]['raw'] += f'{byte:02x}'
            else:
                ranges.append({'pc': pc, 'raw': f'{byte:02x}'})
            previous_index = index
        return {'schema': 'airs.swift-abi-binding.v1',
                'slice': {'sha256': self.image.slice_sha256, 'offset': self.image.slice_offset,
                          'size': self.image.slice_size, 'architecture': self.image.architecture},
                'sections': _section_snapshot(self.image), 'ranges': ranges,
                'work_bytes': self.work}

    def word(self, pc):
        return struct.unpack('<I', self.read(pc, 4))[0]

    def relative(self, pc, *, context=False):
        raw = self.read(pc, 4)
        offset = struct.unpack('<i', raw)[0]
        if not offset or (context and offset & 1):
            raise _Unresolved('indirect_or_null_context_pointer')
        target = pc + offset
        if not 0 <= target < 1 << 64:
            raise _Unresolved('malformed_nominal_metadata')
        return target

    def string(self, pc):
        raw = bytearray()
        for i in range(self.limits.max_string_bytes):
            byte = self.read(pc + i, 1)
            raw.extend(byte)
            if byte == b'\0':
                name = raw[:-1].decode('ascii')
                if not name:
                    raise _Unresolved('malformed_nominal_metadata')
                return name, raw.hex()
        raise _Unresolved('metadata_resource_limit')

    def record(self, pc):
        if pc & 3:
            raise _Unresolved('malformed_nominal_metadata')
        flags = self.word(pc)
        kind = flags & 31
        if flags & 0x80:
            raise _Unresolved('generic_context_unqualified')
        # Only the known kind and uniqueness bit are qualified here; version,
        # import information, vtable and other kind-specific tails stay explicit.
        known = 0x5f | (0x80000000 if kind == 16 else 0)
        if flags & ~known:
            raise _Unresolved('descriptor_flags_unqualified')
        if kind not in (0, 16, 17, 18):
            raise _Unresolved('context_kind_unqualified')
        size = {0: 12, 16: 44, 17: 28, 18: 28}[kind]
        raw = self.read(pc, size)
        name_pc = self.relative(pc + 8)
        name, raw_name = self.string(name_pc)
        return {'descriptor_pc': hex(pc), 'descriptor_flags': hex(flags),
                'kind': {0: 'module', 16: 'class', 17: 'struct', 18: 'enum'}[kind],
                'name': name, 'name_pc': hex(name_pc), 'raw_name': raw_name,
                'raw_descriptor': raw.hex()}


def _section_snapshot(image):
    return [{'segment': s.segment, 'name': s.name, 'address': s.address,
             'size': s.size, 'file_offset': s.file_offset, 'flags': s.flags}
            for s in image.sections]


def swift_abi_binding_matches(image, record, *, limits=ABILimits(), callsite_capability=None):
    """Check critical bytes/mappings of a retained record, without source hashing.

    This checks custody of existing evidence, not authenticity of a caller-made
    receipt or a new lowering capability. Never upgrades an unresolved result.
    """
    try:
        if 'callsite_binding' in record:
            from .swift_callsite_admission import callsite_binding_matches
            if record['callsite_binding'].get('session_required'):
                from .swift_callsite_admission import validate_callsite_capability
                retained = validate_callsite_capability(image, callsite_capability)
                if retained is None or retained.get('binding') != record['callsite_binding']:
                    return False
            elif not callsite_binding_matches(image, {'binding': record['callsite_binding']}):
                return False
        binding = record['binding']
        if (binding['schema'] != 'airs.swift-abi-binding.v1'
                or len(image.sections) > limits.max_sections
                or binding['sections'] != _section_snapshot(image)
                or binding['slice'] != {'sha256': image.slice_sha256, 'offset': image.slice_offset,
                                        'size': image.slice_size, 'architecture': image.architecture}
                or not binding['ranges'] or len(binding['ranges']) > limits.max_work):
            return False
        reader = _MetadataReader(image, limits)
        for span in binding['ranges']:
            raw = span['raw']
            if not isinstance(raw, str) or len(raw) > limits.max_work * 2:
                return False
            expected = bytes.fromhex(raw)
            if not expected or reader.read(span['pc'], len(expected)) != expected:
                return False
        return True
    except (KeyError, TypeError, AttributeError, ValueError, InputError, _Unresolved):
        return False


def admit_nominal_context(image, declaration, *, limits=ABILimits(), _reader=None):
    """Resolve one exact, unique nominal-parent chain in the selected slice.

    Any unexamined/unknown record can hide an alias, so a partially scanned
    section never establishes uniqueness. Duplicate references to one descriptor
    are deduplicated; distinct descriptors for the same identity are ambiguous.
    """
    result = {'status': 'unresolved', 'reason': 'nominal_context_not_found'}
    if len(declaration.context) > limits.max_context_depth:
        return {**result, 'reason': 'metadata_resource_limit'}
    section = image.section('__TEXT', '__swift5_types')
    if section is None:
        return result
    if (section.size < 0 or section.size % 4 or section.size // 4 > limits.max_entries
            or section.address < 0 or section.address + section.size > 1 << 64):
        return {**result, 'reason': 'metadata_resource_limit'}
    if len(image.sections) > limits.max_sections:
        return {**result, 'reason': 'metadata_resource_limit'}
    directories = [s for s in image.sections if s.segment == '__TEXT' and s.name == '__swift5_types']
    if len(directories) > 1:
        return {**result, 'reason': 'ambiguous_metadata_directory'}
    reader = _reader if _reader is not None else _MetadataReader(image, limits)
    matches, visited = [], set()
    try:
        for offset in range(0, section.size, 4):
            entry = section.address + offset
            descriptor = reader.relative(entry, context=True)
            if descriptor in visited:
                continue
            visited.add(descriptor)
            # Genericity adds a trailing context, not a different nominal-name
            # prefix. Skip a provably different leaf before demanding its parent
            # or lowering qualification. Unknown formats remain conservative.
            leaf_flags = reader.word(descriptor)
            leaf_kind = leaf_flags & 31
            if leaf_kind in (16, 17, 18) and not leaf_flags & 0xff00:
                leaf_name, _ = reader.string(reader.relative(descriptor + 8))
                if declaration.context and leaf_name != declaration.context[-1].name:
                    continue
            records, chain_seen, pc = [], set(), descriptor
            for depth in range(limits.max_context_depth + 1):
                if pc in chain_seen:
                    raise _Unresolved('cyclic_context_parent')
                chain_seen.add(pc)
                record = reader.record(pc)
                if record['kind'] == 'module':
                    if reader.word(pc + 4) != 0:
                        raise _Unresolved('module_parent_unqualified')
                    module = record
                    break
                if depth >= limits.max_context_depth:
                    raise _Unresolved('metadata_resource_limit')
                records.append(record)
                pc = reader.relative(pc + 4, context=True)
            else:
                raise _Unresolved('metadata_resource_limit')
            chain = tuple((r['name'], r['kind']) for r in reversed(records))
            expected = tuple((c.name, c.kind) for c in declaration.context)
            if chain == expected and module['name'] == declaration.module:
                matches.append({'entry_pc': hex(entry), 'raw_entry': reader.read(entry, 4).hex(),
                                'records': list(reversed(records)), 'module': module})
        if len(matches) == 1:
            return {'status': 'admitted_nominal_context', **matches[0],
                    'slice': {'sha256': image.slice_sha256, 'offset': image.slice_offset,
                              'size': image.slice_size, 'architecture': image.architecture},
                    'work_bytes': reader.work, 'binding': reader.binding()}
        if len(matches) > 1:
            return {**result, 'reason': 'ambiguous_nominal_context', 'match_count': len(matches)}
    except _Unresolved as exc:
        return {**result, 'reason': str(exc)}
    except (InputError, ValueError, UnicodeError, struct.error):
        return {**result, 'reason': 'malformed_nominal_metadata'}
    return result


def admit_swift_abi(image, declaration, *, qualification=None, limits=ABILimits()):
    """Admit a reviewed ABI tuple, retaining independent syntax/context evidence.

    A qualification is an internal registry ID, never caller-provided evidence.
    None performs the same exact-image lookup automatically. Existing image
    digests are reused as provenance; this function does not rehash the input.
    """
    result = {'status': 'unresolved', 'reason': 'lowering_not_qualified',
              'profile': SYNC_ARM64_SWIFT6.identifier, 'research_only': True,
              'evidence': {}}
    def unresolved(reason):
        return {**result, 'reason': reason}
    if not isinstance(limits, ABILimits) or any(type(v) is not int or v < 0 for v in (
            limits.max_entries, limits.max_context_depth, limits.max_string_bytes, limits.max_work,
            limits.max_sections, limits.max_function_bytes, limits.max_functions)):
        return unresolved('invalid_abi_limits')
    if isinstance(declaration, BroadDeclarationResult):
        if not declaration.supported:
            reason = declaration.unsupported_reason
            return unresolved(reason.value if reason else 'declaration_unqualified')
        declaration = declaration.identity
    if not isinstance(declaration, SwiftCallableIdentity):
        return unresolved('declaration_unqualified')
    if isinstance(qualification, ABICallsiteQualification):
        return _admit_stable_callsite(image, declaration, qualification, limits)
    if image.architecture != 'arm64':
        return unresolved('architecture_unqualified')
    if qualification is not None and (type(qualification) is not str or qualification not in LOWERING_QUALIFICATIONS):
        return unresolved('untrusted_qualification')
    if declaration.generic_parameter_counts or declaration.generic_requirements:
        return unresolved('generic_callable_unqualified')
    reader = _MetadataReader(image, limits)
    if declaration.context:
        context = admit_nominal_context(image, declaration, limits=limits, _reader=reader)
        result['evidence']['nominal_context'] = context
        if context['status'] != 'admitted_nominal_context':
            return unresolved(context['reason'])
    candidates = (LOWERING_QUALIFICATIONS[qualification],) if qualification else LOWERING_QUALIFICATIONS.values()
    for observation in candidates:
        if (image.slice_sha256 != observation.slice_sha256
                or declaration.symbol.lstrip('_') != observation.symbol
                or declaration.callable_kind != observation.callable_kind
                or tuple((c.name, c.kind) for c in declaration.context) != observation.context
                or not declaration.throws
                or tuple(t.name for t in declaration.parameter_types) != observation.parameter_types
                or declaration.result_type.name != observation.result_type
                or any(t.inout or t.arguments or t.generic_depth is not None for t in
                       (*declaration.parameter_types, declaration.result_type))):
            continue
        # Frozen dataclasses prevent mutation, not construction of contradictory
        # fields. Bind the complete syntax identity to the reviewed symbol.
        expected_identity = parse_broad_declaration(observation.symbol).identity
        if replace(declaration, symbol=observation.symbol) != expected_identity:
            continue
        try:
            for pc, raw, _ in observation.observations:
                expected = bytes.fromhex(raw)
                if reader.read(pc, len(expected)) != expected:
                    return unresolved('qualification_bytes_mismatch')
        except _Unresolved as exc:
            return unresolved(str(exc))
        except InputError:
            return unresolved('qualification_bytes_unavailable')
        result['evidence']['lowering'] = {
            'qualification_id': observation.evidence_id, 'source_sha256': observation.source_sha256,
            'slice_sha256': observation.slice_sha256, 'compiler': observation.compiler,
            'target': observation.target, 'language_mode': '6', 'optimization': observation.optimization,
            'source_capture': observation.source_capture, 'disassembly_capture': observation.disassembly_capture,
            'observations': [{'pc': hex(pc), 'raw_bytes': raw, 'meaning': meaning}
                             for pc, raw, meaning in observation.observations],
            'public_abi_references': list(ABI_REFERENCES),
            'verification': 'reused_existing_source_compile_and_disassembly_captures',
        }
        return {**result, 'status': 'admitted', 'reason': 'qualified_owned_lowering',
                'binding': reader.binding(),
                'error_register': SYNC_ARM64_SWIFT6.error_register,
                'argument_locations': list(observation.parameter_locations),
                'receiver_location': observation.receiver_location,
                'result_location': observation.result_location}
    return result


@dataclass(frozen=True, slots=True)
class StorageCapability:
    evidence_id: str
    category: str
    locations: tuple[str, ...]
    bit_width: int | None
    indirect: bool = False
    layout_bytes: int | None = None
    signed: bool | None = None


# Builtin rules are explicit selected stable-ABI assumptions corroborated by
# the retained v2 observations below. Owned resilient layouts require frozen
# captured-source lineage; their names never qualify arbitrary binaries.
_V2_SLICES = frozenset((
    '4b64cd20639936c261573c00a339d4f2e3f9105d530fdb9ed3848097cd7d5ba6',
    'd2503590aac4ecdb74158ebe11864d3bb1491c17bb171b26f94ac5f3cf37202f',
    '50a122aeda215ff81cc26d32559c05ecf0190a02ea1a4db338bcb35951fc6b88',
))
_V2_SOURCE = '611642c714017e9e404d201d6346f0b323a5c13752132f03f01e65dd9703ae18'
# Frozen capture lineage, independently retained by compile.v2 receipts. The
# second compiler uses the representative subset with the same generated type
# definitions; its selected source identity is distinct from reference evidence.
_SECOND_SOURCE = 'ca091dde5345cda398ef78f95b6969abd0736acd508961a705654c9bedffb5cf'
OWNED_SOURCE_BY_SLICE = MappingProxyType({
    **{digest: _V2_SOURCE for digest in _V2_SLICES},
    '35f5565c675d9d4c328e310bfc1adaa2bd58afc8b3905bd888f009cd03f7cd76': _SECOND_SOURCE,
    'df089ae590af31adb53dd119c40eee667d333b8f8874f46615cc98c3007a96b9': _SECOND_SOURCE,
    '450a078fb5260574736b8b7daf0792ed92b52c4c2b374af45d123b01b5c9b974': _SECOND_SOURCE,
})
STABLE_STORAGE_CAPABILITIES = MappingProxyType({
    **{'Swift.' + name: StorageCapability('swift-stable-v2-' + name.lower(),
        'integer', ('x0',), bits, signed=signed)
       for name, bits, signed in (
           ('Int', 64, True), ('UInt', 64, False), ('Int8', 8, True), ('UInt8', 8, False),
           ('Int16', 16, True), ('UInt16', 16, False), ('Int32', 32, True), ('UInt32', 32, False),
           ('Int64', 64, True), ('UInt64', 64, False))},
    'Swift.Bool': StorageCapability('swift-stable-v2-bool', 'boolean', ('x0',), 1),
    'Swift.Void': StorageCapability('swift-stable-v2-void', 'void', (), 0),
    'Swift.Float': StorageCapability('swift-stable-v2-float', 'floating_point', ('s0',), 32),
    'Swift.Double': StorageCapability('swift-stable-v2-double', 'floating_point', ('d0',), 64),
    'Optional<Swift.Int>': StorageCapability('swift-stable-v2-optional-int', 'optional_integer', ('x0', 'w1'), None),
    'Tuple<Swift.Int,Swift.Bool>': StorageCapability('swift-stable-v2-tuple-int-bool', 'tuple', ('x0', 'w1'), None),
    'BroadOwned.BroadSmall': StorageCapability('owned-v2-resilient-small', 'resilient_struct', ('indirect x8',), None, True, 16),
    'BroadOwned.BroadLarge': StorageCapability('owned-v2-resilient-large', 'resilient_struct', ('indirect x8',), None, True, 64),
    'BroadOwned.BroadPayload': StorageCapability('owned-v2-resilient-payload', 'resilient_payload_enum', ('indirect x8',), None, True, 8),
    'BroadOwned.BroadTag': StorageCapability('owned-v2-resilient-tag', 'resilient_tag_enum', ('indirect x8',), None, True, 1),
    'BroadOwned.BroadReference': StorageCapability('owned-v2-reference', 'class_reference', ('x0',), 64),
})

# PC/raw words from previously uninspected v2-O forms, read from retained objdump
# and corroborated against the captured image for each new admission. These are
# research capability provenance, not an assertion that any matching word proves
# an outcome or a value. Public ABI rules provide the explicit convention.
STABLE_LOWERING_OBSERVATIONS = (
    (0x1a88, 'c0035fd6', 'Void return', 'broad_case_0023'),
    (0x1c58, '60720051', 'Int8 result w0', 'broad_case_0025'),
    (0x12f8, '0001271e', 'Float result s0', 'broad_case_0012'),
    (0x26a4, '0001629e', 'Double conversion result d0', 'broad_case_0036'),
    (0x2828, 'e1179f1a', 'Optional<Int> tag w1 alongside x0', 'broad_case_0037'),
    (0x28f4, '092900a9', 'resilient small result store through x8', 'broad_case_0038'),
    (0x2a24, '000d803d', 'resilient large result vector store through x8', 'broad_case_0039'),
    (0x1598, '090100f9', 'single-payload enum result through x8', 'broad_case_0017'),
    (0x2c54, '09010039', 'resilient tag result byte through x8', 'broad_case_0041'),
    (0x1c720, '01010012', 'tuple Bool field w1 alongside x0', 'broad_case_0341'),
    (0x2ed0, '140800f9', 'reference object accessed through return x0', 'broad_case_0043'),
    (0x1c4f0, '3401028b', 'concrete generic Int remains explicit x2', 'broad_case_0340'),
)


def _type_key(node):
    if node.arguments:
        return node.name + '<' + ','.join(_type_key(a) for a in node.arguments) + '>'
    return node.name


def _storage_for(node, owned):
    if node.inout or node.generic_depth is not None:
        return None
    key = _type_key(node)
    capability = STABLE_STORAGE_CAPABILITIES.get(key)
    if capability and (not key.startswith('BroadOwned.') or owned):
        return capability
    return None


def _argument_storage(parameters, owned):
    integer, floating = 0, 0
    result = []
    for node in parameters:
        key = _type_key(node)
        if node.generic_depth is not None:
            return None
        if node.inout:
            if key != 'Swift.Int':
                return None
            locations, evidence = (f'indirect x{integer}',), 'swift-stable-v2-inout-int'
            integer += 1
        elif key in ('Swift.Float', 'Swift.Double'):
            locations = (('s' if key == 'Swift.Float' else 'd') + str(floating),)
            floating += 1
            evidence = STABLE_STORAGE_CAPABILITIES[key].evidence_id
        elif key in STABLE_STORAGE_CAPABILITIES and key.startswith('Swift.') and key != 'Swift.Void':
            cap = STABLE_STORAGE_CAPABILITIES[key]
            locations = (('w' if cap.bit_width < 64 else 'x') + str(integer),)
            integer += 1
            evidence = cap.evidence_id
        elif key == 'Tuple<Swift.Int,Swift.Bool>':
            locations = (f'x{integer}', f'w{integer+1}')
            integer += 2
            evidence = 'swift-stable-v2-tuple-int-bool'
        elif owned and key in ('BroadOwned.BroadSmall', 'BroadOwned.BroadLarge'):
            locations = (f'indirect x{integer}',)
            integer += 1
            evidence = 'owned-v2-resilient-argument'
        elif owned and key in ('Swift.String', 'Swift.Array<Swift.Int>'):
            count = 2 if key == 'Swift.String' else 1
            locations = tuple(f'x{i}' for i in range(integer, integer+count))
            integer += count
            evidence = 'owned-v2-string-array-argument'
        else:
            return None
        if integer > 8 or floating > 8:
            return None
        result.append({'type': key, 'locations': list(locations), 'evidence_id': evidence,
                       'inout': node.inout})
    return result


def _writes_gpr(word, register):
    if word & 31 != register:
        return False
    if _prefix_data_processing_allocated(word) is False:
        return False
    if word & 0x1fe00000 == 0x1a800000:
        from .arm64 import ModelError
        from .swift_broad_instructions import decode_instruction
        try:
            decode_instruction(word)
        except ModelError:
            return False
    if word & 0x1fe00000 == 0x1b000000 and word & 0x7fe00000 != 0x1b000000:
        return False
    # Explicit destination-producing arithmetic/logical/move-wide families;
    # never treat a branch, store, comparison-to-zr or an arbitrary word as Rd.
    return (word & 0x1f000000 in (0x11000000, 0x0b000000, 0x0a000000)
            or word & 0x1f800000 in (0x12000000, 0x12800000, 0x13000000)
            or word & 0x1fe00000 in (0x1a800000, 0x1b000000))


def _result_corroboration(words, capability):
    if capability.category == 'void':
        return any(w == 0xd65f03c0 for w in words)
    if capability.indirect:
        # Only directly addressed x8 result stores are currently qualified.
        # A copied/reloaded result buffer requires a separate alias proof.
        return any(_indirect_result_store_word(w) for w in words)
    if capability.locations == ('s0',) or capability.locations == ('d0',):
        # Scalar FP conversion/move/arithmetic with a real FP destination 0.
        single = capability.locations == ('s0',)
        unary = (0x9e220000, 0x1e270000) if single else (0x9e620000, 0x9e670000)
        binary = (0x1e211800, 0x1e212800) if single else (0x1e611800, 0x1e612800)
        return any(w & 31 == 0 and (
            any(w & 0xfffffc00 == base for base in unary)
            or any(w & 0xffe0fc00 == base & 0xffe0fc00 for base in binary)) for w in words)
    required = [int(location[1:]) for location in capability.locations]
    return all(any(_writes_gpr(word, register) for word in words) for register in required)


def _admit_stable_callsite(image, declaration, request, limits):
    from dataclasses import asdict
    from .swift_callsite_admission import admit_broad_swift_callsite, CallsiteLimits
    result = {'status': 'unresolved', 'reason': 'stable_abi_unqualified',
              'profile': STABLE_ARM64_SWIFT6.identifier, 'research_only': True,
              'compiler_verified': False, 'profile_assumption': 'explicit_selected_swift6_stable_arm64_sync_untyped',
              'call_return_proven': False, 'error_state_proven': False,
              'work_steps': 0, 'evidence': {}}
    reader, callsite_work = None, 0
    def decline(reason):
        return {**result, 'reason': reason,
                'work_steps': callsite_work + (reader.work if reader else 0)}
    if (request.profile_id != STABLE_ARM64_SWIFT6.identifier
            or any(type(x) is not int or not 0 <= x < 1 << 64 for x in
                   (request.call_pc, request.caller_start, request.target_pc))):
        return decline('invalid_callsite_qualification_request')
    if image.architecture != 'arm64' or not declaration.throws:
        return decline('stable_profile_declaration_unqualified')
    canonical = parse_broad_declaration(declaration.symbol)
    if not canonical.supported or canonical.identity != declaration:
        return decline('declaration_identity_mismatch')
    if len(image.functions) > limits.max_functions:
        return decline('abi_function_limit')
    callers = [f for f in image.functions if f.start == request.caller_start]
    targets = [f for f in image.functions if f.start == request.target_pc]
    if len(callers) != 1 or len(targets) != 1:
        return decline('abi_exact_function_required')
    caller, target = callers[0], targets[0]
    if target.name.lstrip('_') != declaration.symbol.lstrip('_'):
        return decline('abi_target_symbol_mismatch')
    # B5 proves raw nlist/LC_FUNCTION_STARTS/section custody and target identity;
    # this layer adds ABI patterns, not a second symbol-name-only inference.
    if request.callsite_capability is not None:
        from .swift_callsite_admission import validate_callsite_capability
        callsite = validate_callsite_capability(image, request.callsite_capability)
        if callsite is None:
            return decline('untrusted_callsite_capability')
        # Construction was charged by the caller. Charge only this new custody
        # check/copy work, not the original B5 admission again.
        callsite_work = callsite['work_steps']
    else:
        callsite = admit_broad_swift_callsite(image, caller, request.call_pc,
            limits=CallsiteLimits(max_work=2_000_000))
        callsite_work = callsite['work_steps']
    if (callsite.get('call_pc') != request.call_pc
            or callsite.get('caller_start') != request.caller_start
            or callsite.get('symbol', '').lstrip('_') != declaration.symbol.lstrip('_')):
        return decline('callsite_capability_request_mismatch')
    if callsite['status'] != 'admitted_callsite' or callsite.get('callee_pc') != request.target_pc:
        return decline('abi_callsite_' + callsite['reason'])
    if callsite.get('call_kind') != 'bl':
        return decline('stable_abi_direct_bl_required')
    selected_source = OWNED_SOURCE_BY_SLICE.get(image.slice_sha256)
    owned = selected_source is not None
    parameters, output = declaration.parameter_types, declaration.result_type
    specialization = declaration.specialization
    if specialization:
        if (not owned or specialization.async_removed or specialization.representation_changed
                or specialization.kind.value != 'generic_reabstracted'
                or any(b.replacement.name != 'Swift.Int' for b in specialization.bindings)):
            return decline('specialization_lowering_unqualified')
        parameters, output = specialization.substituted_parameter_types, specialization.substituted_result_type
    elif declaration.generic_parameter_counts or declaration.generic_requirements:
        return decline('generic_callable_unqualified')
    storage = _storage_for(output, owned)
    arguments = _argument_storage(parameters, owned)
    if storage is None or arguments is None:
        return decline('storage_shape_unqualified')
    if specialization and (specialization.pass_id != 5 or specialization.serialized
            or specialization.dropped_argument_ordinals not in ((), (2,), (3,), (4,))):
        return decline('specialization_dropped_argument_unqualified')
    if target.size <= 0 or target.size % 4 or target.size > limits.max_function_bytes:
        return decline('abi_function_byte_limit')
    reader = _MetadataReader(image, limits)
    try:
        if declaration.context:
            context = admit_nominal_context(image, declaration, limits=limits, _reader=reader)
            result['evidence']['nominal_context'] = context
            if context['status'] != 'admitted_nominal_context':
                return decline(context['reason'])
        before_start = max(caller.start, request.call_pc - 128)
        after_end = min(caller.end, request.call_pc + 68)
        before = list(struct.unpack('<' + 'I' * ((request.call_pc-before_start)//4),
                                    reader.read(before_start, request.call_pc-before_start)))
        after = list(struct.unpack('<' + 'I' * ((after_end-request.call_pc-4)//4),
                                   reader.read(request.call_pc+4, after_end-request.call_pc-4)))
        # Geometry observations are not ABI prerequisites. A propagating caller
        # can inherit the Swift error-register convention and have no test.
        # Merely seeing a clear does not prove it survives intervening control
        # flow/calls; that is the independent caller-state validator's work.
        caller_error_observations = {
            'clear_instruction_pcs': [hex(before_start + i * 4) for i, w in enumerate(before)
                                      if w in (0xd2800015, 0x52800015, 0xaa1f03f5)],
            'test_instruction_pcs': [hex(request.call_pc + 4 + i * 4) for i, w in enumerate(after)
                                     if w & 0x7e00001f == 0x34000015],
            'incoming_state_proven': False, 'scope': 'instruction_presence_not_path_or_state_proof',
        }
        code = reader.read(target.start, target.size)
        words = struct.unpack('<' + 'I' * (len(code)//4), code)
        if specialization and not _concrete_arguments_corroborated(words, arguments):
            return decline('specialization_argument_locations_unqualified')
        transport_copy = any(_error_transport_word(w) for w in words)
        preserved_leaf = not transport_copy and _leaf_preserves_x21(words)
        if not transport_copy and not preserved_leaf:
            return decline('callee_error_transport_unqualified')
        if not _result_corroboration(words, storage):
            return decline('callee_result_storage_unqualified')
        receiver = None
        original_kind = declaration.original_callable_kind or declaration.callable_kind
        if original_kind in (CallableKind.STRUCT_INSTANCE_METHOD, CallableKind.ENUM_INSTANCE_METHOD):
            if not owned:
                return decline('value_receiver_lowering_unqualified')
            receiver = 'indirect x20'
        elif original_kind == CallableKind.CLASS_INSTANCE_METHOD:
            receiver = 'reference x20'
        result['evidence']['lowering'] = {
            'qualification_id': storage.evidence_id, 'source_evidence_id': 'owned-v2-fixed-initial-lowering-observations',
            'source_sha256': _V2_SOURCE, 'reference_slice_sha256': next(iter(sorted(_V2_SLICES))),
            'selected_source_sha256': selected_source, 'selected_slice_sha256': image.slice_sha256,
            'compiler': _COMPILER, 'target': 'arm64-apple-macosx14.0',
            'public_abi_references': list(ABI_REFERENCES),
            'observations': [{'pc': hex(pc), 'raw_bytes': raw, 'meaning': meaning, 'source_case': case}
                             for pc, raw, meaning, case in STABLE_LOWERING_OBSERVATIONS],
            'specialization': asdict(specialization) if specialization else None,
            'specialization_argument_corroboration': ({
                'formal_locations_present_before_clobber_or_control_transfer': True,
                'dropped_ordinal_semantics': 'not_interpreted_as_formal_parameter_indices',
                'hidden_metadata_argument_locations': 'not_claimed',
            } if specialization else None),
            'assumption': result['profile_assumption'], 'compiler_verified': False,
            'callee_error_transport_observation': (
                'mov_to_x21_from_distinct_nonzero_gpr_presence' if transport_copy
                else 'x21_preserved_by_exact_straightline_leaf_effects'),
            'callee_error_observation': {
                'mode': 'distinct_nonzero_gpr_copy' if transport_copy else 'preserved_x21_leaf',
                'register': 'x21',
                'scope': 'instruction_effects_if_normal_return_not_incoming_state_or_object_type',
                'entry_pc': hex(target.start), 'return_pc': hex(target.end - 4) if preserved_leaf else None,
                'word_count': len(words), 'preserves_incoming_x21': True if preserved_leaf else None,
                'incoming_state_proven': False, 'error_object_type_proven': False,
            },
            'error_object_type_proven': False,
        }
        return {**result, 'status': 'admitted', 'reason': 'qualified_stable_abi_patterns',
                'family': _stable_family(declaration, owned),
                'caller_error_observations': caller_error_observations,
                'profile_preconditions': ['well_formed_swift_stable_arm64_calling_convention',
                    'synchronous_untyped_throws', 'caller_supplies_error_register_state_required_by_convention'],
                'family_evidence': {'source_sha256': selected_source,
                                    'compiled_target_pc': hex(target.start),
                                    'direct_call_pc': hex(request.call_pc),
                                    'scope': 'source_lineage_plus_exact_emitted_target_not_runtime_dispatch'},
                'error_register': 'x21', 'argument_storage': arguments,
                'argument_locations': [a['locations'] for a in arguments],
                'receiver_location': receiver, 'result_type': _type_key(output),
                'result_storage': asdict(storage) | {'locations': list(storage.locations)},
                'result_location': storage.locations[0] if storage.locations else None,
                'binding': reader.binding(), 'callsite_binding': callsite['binding'],
                'callsite_symbol_evidence': callsite.get('symbol_evidence'),
                'work_bytes': reader.work, 'work_steps': callsite_work + reader.work,
                'abi_shape': {'arguments': arguments, 'receiver': receiver,
                              'result': asdict(storage), 'error_register': 'x21',
                              'specialized': specialization is not None}}
    except (_Unresolved, InputError, ValueError, struct.error) as error:
        return decline(str(error) if isinstance(error, _Unresolved) else 'malformed_abi_bytes')


def _stable_family(declaration, owned):
    """Family lineage is distinct from proof of the emitted direct target."""
    if declaration.specialization:
        return 'concrete_generic_specialization'
    if not declaration.context:
        return 'free'
    leaf = declaration.context[-1]
    # These two source attributes have no unique mangling bit. Only the exact
    # captured source/slice lineage supplies extension/final classification.
    if owned and declaration.module == 'BroadOwned' and leaf.name.startswith('BroadOwner'):
        suffix = leaf.name[len('BroadOwner'):]
        if len(suffix) == 4 and suffix.isdigit():
            index = int(suffix)
            if index in range(297, 340, 3):
                return 'extension'
            if index in range(235, 295, 2):
                return 'direct_final_class'
    if leaf.kind == 'enum':
        return 'enum'
    if declaration.callable_kind == CallableKind.STATIC_METHOD:
        return 'static_type'
    if leaf.kind == 'struct':
        return 'struct'
    return 'direct_class_research'


def _concrete_arguments_corroborated(words, arguments):
    """Observe every formal GPR input before clobber/control transfer.

    DroppedArgument ordinals are not translated into source parameter indices.
    All substituted formal locations must remain present in emitted code; no
    hidden metadata/context argument location is claimed by this check.
    """
    wanted = {int(location.rsplit(' ', 1)[-1][1:]) for argument in arguments
              for location in argument['locations'] if location.rsplit(' ', 1)[-1][0] in 'xw'}
    live, observed = set(wanted), set()
    for word in words:
        if (word & 0x7c000000 == 0x14000000 or word & 0xff000000 == 0x54000000
                or word & 0x7e000000 in (0x34000000, 0x36000000)
                or word & 0xfe000000 == 0xd6000000):
            break
        rd, rn, rm = word & 31, (word >> 5) & 31, (word >> 16) & 31
        reads, writes = set(), set()
        if _prefix_data_processing_allocated(word) is False:
            break
        if word & 0x1f000000 == 0x11000000:  # add/sub immediate, including cmp
            reads.add(rn); writes.add(rd)
        elif word & 0x1f000000 in (0x0b000000, 0x0a000000):
            reads.update((rn, rm)); writes.add(rd)
        elif word & 0x1f800000 in (0x12000000, 0x13000000):
            reads.add(rn); writes.add(rd)
        elif word & 0x1f800000 == 0x12800000 or word & 0x1f000000 == 0x10000000:
            writes.add(rd)
        elif word & 0x3a000000 == 0x28000000:  # integer pair load/store
            mode = (word >> 23) & 3
            if mode == 0 or (mode in (1, 3) and rn != 31):
                break
            if not word & 0x04000000 and (word >> 30) & 3 not in (0, 2):
                break
            if word & 0x04000000 and (word >> 30) & 3 not in (0, 1, 2):
                break
            if word & 0x00400000 and rd == (word >> 10) & 31:
                break
            reads.add(rn)
            if word & 0x04000000:  # SIMD pair data are a separate register bank
                pass
            elif word & 0x00400000:
                writes.update((rd, (word >> 10) & 31))
            else:
                reads.update((rd, (word >> 10) & 31))
        elif word & 0x3a000000 == 0x38000000:  # integer load/store
            unsigned_offset = word & 0x3b000000 == 0x39000000
            unscaled = word & 0x3b200c00 == 0x38000000
            if not (unsigned_offset or unscaled):
                break
            if not word & 0x04000000 and (word >> 22) & 3 not in (0, 1):
                break
            if word & 0x04000000 and (word >> 22) & 3 in (2, 3) and (word >> 30) & 3 != 0:
                break
            reads.add(rn)
            if not word & 0x04000000:
                (writes if word & 0x00400000 else reads).add(rd)
        elif word == 0xd503201f:
            pass
        else:
            # An unknown instruction can write Rs, a base, flags or several
            # registers. Guessing only Rd would preserve counterfeit origins.
            break
        observed.update(reads & live)
        live.difference_update(writes)
    return wanted <= observed


def _error_transport_word(word):
    """Instruction presence only; neither a self/zero move nor object proof."""
    return word & 0xffe0ffff == 0xaa0003f5 and (word >> 16) & 31 not in (21, 31)


def _leaf_preserves_x21(words):
    """Exact instruction-effect proof, conditional on normal leaf return.

    No input value, source-level error type, execution or call-return claim is
    established. Unknown effects, any opaque/control transfer, and even a
    self-write to GPR x21 conservatively refuse this mode.
    """
    from .arm64 import ModelError, _FP_DESTINATION_KINDS
    from .swift_broad_instructions import (
        decode_instruction, destination_register_bank, FP_FLAG_KINDS,
    )
    if (not words or len(words) > 256 or words[-1] != 0xd65f03c0
            or any(w == 0xd65f03c0 for w in words[:-1])):
        return False
    memory = frozenset(('stp', 'ldp', 'xldr', 'wldr', 'xstr', 'wstr',
                        'xldr_post', 'wstrb', 'wstrh', 'wldrb', 'wldrh'))
    loads = frozenset(('ldp', 'xldr', 'wldr', 'xldr_post', 'wldrb', 'wldrh'))
    for word in words[:-1]:
        if (word & 0x7c000000 == 0x14000000 or word & 0xff000000 == 0x54000000
                or word & 0x7e000000 in (0x34000000, 0x36000000)
                or word & 0xfe000000 == 0xd6000000):
            return False
        rd = word & 31
        # This exact allocation guard also covers non-flag register ADD/SUB,
        # which the historical descriptor subset intentionally does not model.
        if _writes_gpr(word, rd):
            if rd == 21:
                return False
            continue
        try:
            instruction = decode_instruction(word)
        except ModelError:
            return False
        if instruction.kind == 'nop' or instruction.kind in FP_FLAG_KINDS:
            continue
        bank = destination_register_bank(instruction)
        if bank == 'fp':
            continue
        if instruction.kind in memory:
            if instruction.addressing not in ('', 'offset', 'pre', 'post'):
                return False
            if instruction.addressing in ('pre', 'post') and instruction.rn == 21:
                return False
            if instruction.kind in loads and (instruction.rd == 21
                    or instruction.kind == 'ldp' and instruction.rt2 == 21):
                return False
            continue
        if bank == 'gpr' or instruction.kind in _FP_DESTINATION_KINDS:
            if instruction.rd == 21:
                return False
            continue
        return False
    return True


def _indirect_result_store_word(word):
    """Allocated no-writeback STR/STP forms through x8, never loads/prefetch."""
    if (word >> 5) & 31 != 8:
        return False
    vector, size = bool(word & 0x04000000), (word >> 30) & 3
    if word & 0x3b000000 == 0x39000000:
        opc = (word >> 22) & 3
        return opc == 0 or (vector and opc == 2 and size == 0)
    if word & 0x3b000000 == 0x29000000 and not word & 0x00400000:
        return (word >> 23) & 3 == 2 and (size in (0, 1, 2) if vector else size in (0, 2))
    return False


def _prefix_data_processing_allocated(word):
    """Validate allocation before using coarse read/write operand classes.

    None means a different instruction class. Plain non-flag ADD/SUB register
    forms are checked here because the historical decoder intentionally omits
    them; logical-immediate and bitfield allocation reuse its checked decoder.
    """
    family = word & 0x1f000000
    wide = bool(word & 0x80000000)
    if family == 0x11000000:
        return word & 0x1f800000 == 0x11000000
    if family == 0x0b000000:
        if word & 0x00200000:
            option, amount = (word >> 13) & 7, (word >> 10) & 7
            return (not word & 0x00c00000 and amount <= 4
                    and (wide or option not in (3, 7)))
        return (word >> 22) & 3 != 3 and (wide or (word >> 10) & 63 < 32)
    if family == 0x0a000000:
        return wide or (word >> 10) & 63 < 32
    if word & 0x1f800000 in (0x12000000, 0x13000000):
        from .arm64 import ModelError
        from .swift_broad_instructions import decode_instruction
        try:
            decode_instruction(word)
        except ModelError:
            return False
        return True
    if word & 0x1f800000 == 0x12800000:
        return (word >> 29) & 3 != 1 and (wide or (word >> 21) & 3 < 2)
    if family == 0x10000000:
        return True
    return None
