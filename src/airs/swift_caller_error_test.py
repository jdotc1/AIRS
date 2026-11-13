"""Bounded caller-side x21 observations, never a claim about a callee."""
from __future__ import annotations

import struct
from types import SimpleNamespace
from .analysis_models import SWIFT_CALLER_ERROR_TEST_MODEL
from .arm64 import ModelError, _signed
from .swift_error_flow import _edges, decode_instruction

MODEL = SWIFT_CALLER_ERROR_TEST_MODEL
PRECALL_WORDS = 4


def _direct_entry_indices(data):
    """Caller-local direct targets; no reachability or indirect-entry claim.

    Use the same raw direct-edge classes as the GOT entry screen, including
    condition codes outside the edge interpreter's semantic subset.
    """
    entries = set()
    for index, (word,) in enumerate(struct.iter_unpack('<I', data)):
        if word & 0x7c000000 == 0x14000000:
            entries.add(index + _signed(word & 0x3ffffff, 26))
        elif word & 0xff000000 == 0x54000000 or word & 0x7e000000 == 0x34000000:
            entries.add(index + _signed((word >> 5) & 0x7ffff, 19))
        elif word & 0x7e000000 == 0x36000000:
            entries.add(index + _signed((word >> 5) & 0x3fff, 14))
    return entries


def _precall_instruction(word, pc):
    # ADR/ADRP and unsigned-offset scalar loads have one destination and no
    # base writeback. Their general address bases need no value interpretation.
    if word & 0x1f000000 == 0x10000000:
        return SimpleNamespace(kind='adrp' if word & 0x80000000 else 'adr', rd=word & 31)
    if word & 0xffc00000 in (0xf9400000, 0xb9400000):
        return SimpleNamespace(kind='xldr' if word & 0x40000000 else 'wldr', rd=word & 31)
    return decode_instruction(word, pc)


def _preserves_x21(instruction):
    """A closed gap subset: unknown writes and intervening control flow refuse."""
    kind = instruction.kind
    if kind == 'nop':
        return True
    if kind in ('mov', 'wmov', 'movz', 'movn', 'xmovk', 'wmovz', 'wmovn',
                'wmovk', 'add', 'sub', 'adr', 'adrp', 'xldr', 'wldr'):
        return instruction.rd != 21
    if kind == 'ldp':
        return (21 not in (instruction.rd, instruction.rt2)
                and (instruction.addressing == 'offset' or instruction.rn != 21))
    if kind == 'stp':
        return instruction.addressing == 'offset' or instruction.rn != 21
    return False


def precall_x21_zero(words, call_index, caller_start_index, entry_indices):
    """Inspect at most four prior words, with indices relative to ``words``.

    ``words`` holds ``(pc, word)`` pairs or plain integer words; for plain words the
    PC is a byte offset (four times the word index). ``entry_indices`` contains
    caller-local direct branch target indices; None means the scan is unavailable.
    A found zero needs no words before itself. If the search reaches caller start
    without finding one, the short window is reported explicitly.
    """
    window = []
    result = dict(status='precall_entries_unchecked' if entry_indices is None else 'x21_not_zeroed',
                  window=window)

    def at(index):
        item = words[index]
        return item if isinstance(item, tuple) else (index * 4, item)
    if not 0 <= caller_start_index <= call_index < len(words) or call_index == caller_start_index:
        return dict(status='precall_window_outside_caller', window=window)
    lower = max(caller_start_index, call_index - PRECALL_WORDS)
    for index in range(call_index - 1, lower - 1, -1):
        pc, word = at(index)
        try:
            instruction = _precall_instruction(word, pc)
        except ModelError:
            window.insert(0, dict(pc=hex(pc), word=f'0x{word:08x}', kind='unmodeled'))
            return result
        window.insert(0, dict(pc=hex(pc), word=f'0x{word:08x}', kind=instruction.kind))
        if word == 0xaa1f03f5:
            if entry_indices is None:
                result['status'] = 'precall_entries_unchecked'
            elif any(target in entry_indices for target in range(index + 1, call_index + 1)):
                return result
            else:
                result.update(status='x21_zeroed', zero_pc=hex(pc))
            return result
        if not _preserves_x21(instruction):
            return result
    if call_index - caller_start_index < PRECALL_WORDS:
        result['status'] = 'precall_window_outside_caller'
    return result


def caller_error_test_from_bytes(data, function, call_offset, entry_indices=None):
    """Return the caller fact for caller-relative bytes and byte call offset.

    ``function.start/end`` are VM addresses, as for the unchanged edge model.
    Entry indices are word indices relative to this caller's byte buffer. No scan
    is performed here. The coordinator supplies its cached direct-target scan.
    """
    # Read only the bounded prefix needed for this call; do not unpack a whole
    # caller again for every imported site. The helper's indices remain local.
    start = max(0, call_offset - PRECALL_WORDS * 4)
    prefix = data[start:call_offset + 4]
    words = [word for (word,) in struct.iter_unpack('<I', prefix)]
    local_call = (call_offset - start) // 4
    local_entries = (None if entry_indices is None else
                     {index - start // 4 for index in range(start // 4 + 1, call_offset // 4 + 1)
                      if index in entry_indices})
    precall = precall_x21_zero(words, local_call, 0, local_entries)
    for row in precall['window']:
        row['pc'] = hex(function.start + start + int(row['pc'], 16))
    if 'zero_pc' in precall:
        precall['zero_pc'] = hex(function.start + start + int(precall['zero_pc'], 16))
    return _compose(precall, _edges(data, function, call_offset))


def _compose(precall, postcall):
    before = precall['status'] == 'x21_zeroed'
    after = postcall.get('status') == 'recovered_candidate'
    shape = ('swifterror_idiom' if before and after else 'precall_zero_only' if before
             else 'postcall_test_only' if after else 'none')
    return dict(model=MODEL, postcall=postcall, precall=precall, shape=shape,
                claims_callee_behaviour=False)


def caller_error_test(words, call_index, caller_start_index, caller_end_index, entry_indices=None):
    """Return the caller fact for ``words[caller_start_index:caller_end_index]``.

    ``words`` is a sequence of ``(pc, word)`` pairs. All indices are relative to it;
    ``caller_end_index`` is exclusive and ``entry_indices`` is as for
    ``precall_x21_zero``. A tail ``B`` has no local return point, so the post-call
    window is empty for it and it never reads as a returned error test.
    """
    precall = precall_x21_zero(words, call_index, caller_start_index, entry_indices)
    end = caller_end_index
    if words[call_index][1] & 0xfc000000 == 0x14000000:
        end = call_index + 1
    data = b''.join(struct.pack('<I', word) for _, word in words[caller_start_index:end])
    function = SimpleNamespace(start=words[caller_start_index][0], end=words[caller_end_index - 1][0] + 4)
    return _compose(precall, _edges(data, function, (call_index - caller_start_index) * 4))
