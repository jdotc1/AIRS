"""ABI admission of value-witness callees (tier 2, model swift-value-witness-admission-v1).

Value witnesses are runtime-defined functions that take no swifterror register and cannot
throw. A call that is proven to go through a function slot of a value witness table can
therefore be admitted as non-throwing by ABI. The tier 1 shape alone does not prove that:
loading at -8 from an arbitrary pointer is not a value-witness load. Admission needs all of:

1. tier 1 decides `value_witness` with a function slot (and no join in the slice);
2. the metadata register Xm (the base of the `ldur Xt, [Xm, #-8]` table load) is x0 returned
   by a direct `bl` (reached through optional `mov` / `add #0` copies) to one of
   (a) an exact in-image function entry whose symbol the declaration grammar v2 decides as
       the type metadata accessor,
   (b) an attributed import stub whose symbol the declaration grammar v2 decides as the
       type metadata accessor,
   (c) an attributed import stub for exactly one of RUNTIME_METADATA_FUNCTIONS;
3. no write to any register on a definition-to-use interval of the traced chain (a call
   clobbers x0..x17 and x30).

Object isa loads, generic metadata passed in entry registers, stack transport of the
metadata or of a chain value, and swift_getObjCClassMetadata are refused with stable
reasons. Anything refused keeps its row exactly as it is: this module changes no row.

The caller supplies symbol knowledge as a function, so the module does no I/O:
`symbol_lookup(address)` returns None, or `(symbol, kind)` (or an object with `.symbol` and
`.kind`), where kind is 'function_entry' (address is an exact in-image function entry; symbol
may be None) or 'import_stub' (address is an attributed import stub; symbol is its name).
Any other kind is refused. The function is called at most once per analysis.
"""
from .swift_declaration_grammar import parse_declaration
from .swift_indirect_target_shape import _leaf, _walk, analyze_indirect_target

MODEL = 'swift-value-witness-admission-v1'
# Exact C names after removal of at most one Mach-O leading underscore. No prefix or wildcard
# match. Each returns type metadata (or a MetadataResponse whose first component is the type
# metadata) in x0. This list is an ABI premise of the design, not a runtime verification.
RUNTIME_METADATA_FUNCTIONS = frozenset((
    'swift_getGenericMetadata',
    'swift_getTypeByMangledNameInContext',
    'swift_getTypeByMangledNameInContextInMetadataState',
    'swift_getTypeByMangledNameInContext2',
    'swift_getTypeByMangledNameInContextInMetadataState2',
    'swift_checkMetadataState',
    'swift_getExistentialTypeMetadata',
    'swift_getAssociatedTypeWitness',
))
OBJC_CLASS_METADATA = 'swift_getObjCClassMetadata'
PROVENANCE_KINDS = ('metadata_accessor_call', 'imported_metadata_accessor_call', 'runtime_metadata_call',
                    'isa_load', 'entry_register', 'stack_transport', 'objc_class_metadata', 'unknown')
ADMITTED_KINDS = frozenset(PROVENANCE_KINDS[:3])
MAX_SYMBOL_CHARS = 4096
_OK = 'meets_tier2_conditions'


def _first_clobber(function, reg, low, high):
    """Address of the first instruction strictly between low and high that overwrites reg."""
    for ins in function.ins[(low - function.start) // 4 + 1:(high - function.start) // 4]:
        if reg in ins['writes'] or (ins['kind'] in ('bl', 'blr', 'blra') and (reg <= 17 or reg == 30)):
            return ins['pc']
    return None


def _lookup(symbol_lookup, address):
    """Normalize the caller's answer to (symbol, kind) or (None, refusal reason)."""
    if not callable(symbol_lookup):
        return None, 'symbol_lookup_unavailable'
    try:
        info = symbol_lookup(address)
    except Exception:
        return None, 'symbol_lookup_failed'
    if info is None:
        return None, 'direct_target_unattributed'
    try:
        if isinstance(info, (tuple, list)) and len(info) == 2:
            symbol, kind = info
        else:
            symbol, kind = info.symbol, info.kind
    except Exception:
        return None, 'symbol_lookup_invalid_result'
    if kind not in ('function_entry', 'import_stub'):
        return None, 'direct_target_not_function_entry_or_stub'
    if symbol is not None and (type(symbol) is not str or len(symbol) > MAX_SYMBOL_CHARS):
        return None, 'symbol_lookup_invalid_result'
    return (symbol, kind), None


def _is_metadata_accessor(symbol, parse=None):
    # `parse` lets one run share a declaration cache with this check; the default is the grammar itself.
    decision = (parse_declaration if parse is None else parse)(symbol)
    identity = decision.identity
    ok = identity is not None and identity.entity == 'TypeMetadataAccessFunction' and not decision.reason
    return ok, decision.reason


def _provenance(metadata, symbol_lookup, parse=None):
    """(provenance kind, reason, symbol, admitted) for the definition of the metadata register."""
    n = metadata
    while n['kind'] == 'copy':
        n = n['child']
    kind = n['kind']
    if kind == 'entry_live':
        return 'entry_register', 'entry_metadata_signature_unmapped', None, False
    if kind == 'load' and n['via'] == 'ldr' and n['off'] == 0 and not n['pair']:
        return 'isa_load', 'isa_is_not_proven_swift_metadata', None, False
    if kind == 'stack_reload' or (kind == 'unknown' and n.get('reason') == 'stack_slot_without_store'):
        return 'stack_transport', 'metadata_stack_transport_not_admitted', None, False
    if kind != 'call_result':
        return 'unknown', n.get('reason') or 'metadata_definition_' + kind, None, False
    if n['reg'] != 0:
        return 'unknown', 'metadata_result_not_x0', None, False
    if n['call_kind'] != 'bl':
        return 'unknown', 'metadata_call_not_direct_bl', None, False
    found, problem = _lookup(symbol_lookup, n['callee'])
    if problem:
        return 'unknown', problem, None, False
    symbol, where = found
    if symbol is None:
        return 'unknown', 'direct_target_symbol_missing', None, False
    if where == 'import_stub':
        canonical = symbol[1:] if symbol.startswith('_') else symbol
        if canonical in RUNTIME_METADATA_FUNCTIONS:
            return 'runtime_metadata_call', _OK, symbol, True
        if canonical == OBJC_CLASS_METADATA:
            return 'objc_class_metadata', 'objc_class_metadata_not_admitted', symbol, False
        ok, reason = _is_metadata_accessor(symbol, parse)
        if ok:
            return 'imported_metadata_accessor_call', _OK, symbol, True
        return 'unknown', 'runtime_symbol_not_allowlisted', symbol, False
    ok, reason = _is_metadata_accessor(symbol, parse)
    if ok:
        return 'metadata_accessor_call', _OK, symbol, True
    return 'unknown', 'grammar_' + (reason or 'not_metadata_accessor'), symbol, False


def _result(tier1, *, admitted=False, kind='unknown', failing=None, reason='', metadata=None, symbol=None):
    return dict(model=MODEL, admitted=admitted, provenance_kind=kind, first_failing_condition=failing,
                reason=reason, site_pc=tier1['site_pc'], site_kind=tier1['site_kind'],
                slot_offset=tier1['slot_offset'], metadata_register=metadata, symbol=symbol,
                evidence=[dict(d) for d in tier1['deciding_instructions']], tier1=tier1,
                claims_callee_behaviour=False,
                abi_basis='value_witness_function_slots_cannot_throw' if admitted else None)


def admit_value_witness(words, function_start, site_pc, symbol_lookup, *, branch_targets=None, sections=(),
                        parse=None):
    """Decide tier 2 admission for one indirect branch site. Never raises; returns a dict.

    Keys: model, admitted, provenance_kind (one of PROVENANCE_KINDS), first_failing_condition
    (None, 1, 2 or 3), reason (a stable code; 'meets_tier2_conditions' when admitted),
    site_pc, site_kind, slot_offset, metadata_register, symbol, evidence (deciding
    instructions), tier1 (the full tier 1 record), claims_callee_behaviour (always False)
    and abi_basis. Arguments are those of analyze_indirect_target plus symbol_lookup.
    """
    analysis = analyze_indirect_target(words, function_start, site_pc, branch_targets=branch_targets,
                                       sections=sections)
    tier1 = analysis.record
    try:
        return _admit(analysis, symbol_lookup, parse)
    except Exception:  # totality: refuse, never raise
        return _result(tier1, failing=1, reason='analysis_failed')


def _admit(analysis, symbol_lookup, parse=None):
    tier1 = analysis.record
    if tier1['class'] != 'value_witness' or analysis.function is None:
        reason = tier1['unknown_reason'] if tier1['class'] == 'unknown' and tier1['unknown_reason'] \
            else 'tier1_class_' + tier1['class']
        return _result(tier1, failing=1, reason=reason)
    F, root, target = analysis.function, analysis.root, analysis.target
    # Condition 2 needs the definition to reach the use on every path. The tier 1 census
    # exemption for a single-writer callee-saved register does not prove that (the writer need
    # not dominate the use), so tier 2 checks every definition-to-use interval for a join itself.
    for node in _walk(root):
        if node.get('pc') is None or node.get('consumer') is None or node['kind'] in ('entry_live', 'unknown'):
            continue
        if F.join_between(node['pc'], node['consumer']):
            return _result(tier1, kind='unknown', failing=2, reason='join_in_slice')
    table = _leaf(target['base'])
    metadata_register = 'x%d' % table['rn']
    kind, reason, symbol, ok = _provenance(table['base'], symbol_lookup, parse)
    if not ok:
        return _result(tier1, kind=kind, failing=2, reason=reason, metadata=metadata_register, symbol=symbol)
    # Condition 3. The backward slice already stops at the nearest definition, so a clobber on
    # a traced interval normally changes the provenance instead; this independent pass over
    # every definition-to-use interval keeps the condition from depending on that.
    for node in _walk(root):
        if node['kind'] == 'stack_reload':
            return _result(tier1, kind=kind, failing=3, reason='stack_transport_not_admitted',
                           metadata=metadata_register, symbol=symbol)
    for node in _walk(root):
        if node.get('reg') is None or node.get('pc') is None or node.get('consumer') is None \
                or node['kind'] in ('entry_live', 'unknown'):
            continue
        bad = _first_clobber(F, node['reg'], node['pc'], node['consumer'])
        if bad is not None:
            return _result(tier1, kind=kind, failing=3, reason='register_x%d_written_at_%#x' % (node['reg'], bad),
                           metadata=metadata_register, symbol=symbol)
    return _result(tier1, admitted=True, kind=kind, failing=None, reason=_OK,
                   metadata=metadata_register, symbol=symbol)
