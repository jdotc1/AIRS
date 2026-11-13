"""Bounded wiring of the indirect target models into profile broad-extended-v3.

Tier 1 (`swift-indirect-target-shape-v1`) records where an indirect call target was loaded
from; tier 2 (`swift-value-witness-admission-v1`) admits a call proven to use a value-witness
function slot as non-throwing by ABI. This module only normalizes their records for a report
row and builds the symbol lookup from the report's own attributed names. It does no I/O.
"""
from .swift_indirect_target_shape import MODEL as SHAPE_MODEL
from .swift_value_witness_admission import MODEL as ADMISSION_MODEL, admit_value_witness

ADMITTED_REASON = 'value_witness_abi_nonthrowing'
# Flat per-site charge on top of one word per function word (each site decodes its function).
SITE_WORK = 512
_CALL_KINDS = frozenset(('metadata_accessor_call', 'imported_metadata_accessor_call', 'runtime_metadata_call'))


def make_symbol_lookup(functions, stubs):
    """Symbol knowledge from the report's own tables: attributed import stubs and named function entries.

    The reader names unsymbolized functions sub_<address>; that is a placeholder, not symbol knowledge.
    """
    def lookup(address):
        if stubs is not None:
            found = stubs.lookup(address)
            if found is not None and found[0] == 'attributed':
                return found[1].symbol, 'import_stub'
        function = functions.get(address)
        if function is not None:
            name = function.name
            if type(name) is not str or name == 'sub_%x' % address:
                name = None
            return name, 'function_entry'
        return None
    return lookup


def _hex(value):
    return hex(value) if type(value) is int else None


def _shape(tier1):
    return dict(model=tier1['model'], site_pc=_hex(tier1['site_pc']), site_kind=tier1['site_kind'],
                **{'class': tier1['class']}, slot_offset=tier1['slot_offset'],
                unknown_reason=tier1['unknown_reason'],
                deciding_instructions=[dict(pc=hex(d['pc']), word='0x%08x' % d['word'], role=d['role'])
                                       for d in tier1['deciding_instructions']],
                evidence=tier1['evidence'], class_before_join_refusal=tier1['class_before_join_refusal'],
                slot_address=_hex(tier1['slot_address']), slot_section=tier1['slot_section'],
                claims_callee_behaviour=False, bounds=dict(tier1['bounds']))


def _metadata_callee(result):
    """Target of the recorded metadata-defining bl, recomputed from its recorded word."""
    if result['provenance_kind'] not in _CALL_KINDS:
        return None
    for row in result['evidence']:
        if row['role'] == 'metadata_call_result' and row['word'] & 0xfc000000 == 0x94000000:
            offset = row['word'] & 0x3ffffff
            if offset & 0x2000000:
                offset -= 0x4000000
            return hex(row['pc'] + 4 * offset)
    return None


def _witness(result):
    return dict(model=result['model'], admitted=result['admitted'], provenance_kind=result['provenance_kind'],
                first_failing_condition=result['first_failing_condition'], reason=result['reason'],
                site_pc=_hex(result['site_pc']), site_kind=result['site_kind'], slot_offset=result['slot_offset'],
                metadata_register=result['metadata_register'], symbol=result['symbol'],
                metadata_callee_pc=_metadata_callee(result), claims_callee_behaviour=False,
                abi_basis=result['abi_basis'])


def _failed(site_pc):
    shape = dict(model=SHAPE_MODEL, site_pc=_hex(site_pc), site_kind=None, slot_offset=None,
                 unknown_reason='analysis_failed', deciding_instructions=[], evidence=None,
                 class_before_join_refusal=None, slot_address=None, slot_section=None,
                 claims_callee_behaviour=False, bounds=dict(window_words=256, max_register_hops=6, max_function_words=262144),
                 **{'class': 'unknown'})
    witness = dict(model=ADMISSION_MODEL, admitted=False, provenance_kind='unknown', first_failing_condition=1,
                   reason='analysis_failed', site_pc=_hex(site_pc), site_kind=None, slot_offset=None,
                   metadata_register=None, symbol=None, metadata_callee_pc=None, claims_callee_behaviour=False,
                   abi_basis=None)
    return shape, witness


def indirect_target_facts(image, function, site_pc, symbol_lookup):
    """(shape record, admission record, work) for one indirect branch site; never raises.

    The two models decode the whole containing function once for this site, so the work charge is
    the function's word count plus SITE_WORK.
    """
    work = function.size // 4 + SITE_WORK
    try:
        try:
            words = image.bytes_at(function.start, function.size)
        except Exception:
            words = b''
        result = admit_value_witness(words, function.start, site_pc, symbol_lookup, sections=image.sections)
        return _shape(result['tier1']), _witness(result), work
    except Exception:
        return (*_failed(site_pc), work)
