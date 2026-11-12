#!/usr/bin/env python3
"""Compare the AIRS ARM64 decoders with recorded disassembler vectors.

The harness never runs a disassembler. It reads tab-separated vector files laid
out under --vectors-root, decodes every word with the linear and the CFG AIRS
decoders, and classifies each (word, decoder) pair against the recorded text.

Rule under test: AIRS may refuse any word it does not model, but every word it
admits must match the oracle's instruction and its SP/FP effects, and AIRS must
never call a word invalid when the oracle decodes it. See
docs/ARM64_ORACLE_HARNESS.md. Inputs are data; nothing is executed.
"""
from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from airs import arm64, cfg  # noqa: E402
from airs.arm64 import ModelError  # noqa: E402

HARNESS_VERSION = 1
SCHEMA = 1
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_LINE_BYTES = 8192
PART_ROWS = 2000
M64 = (1 << 64) - 1

# Input files: path under --vectors-root -> (label, columns). The columns
# 'objdump' (mnemonic and operands in one field) or 'mnemonic'+'operands' carry
# the oracle text; 'address' is optional (absent: branch targets are wildcards).
SPECS = {
    'arm64-coverage-vectors/vectors.tsv': ('coverage', ('group', 'address', 'word', 'objdump')),
    'arm64-feature-vectors/vectors.tsv': ('feature', ('group', 'address', 'word', 'mnemonic', 'operands', 'source')),
    'arm64-feature-vectors/boundary.tsv': ('feature-boundary', ('address', 'word', 'mnemonic', 'operands')),
    'arm64-reserved-vectors/vectors.tsv': ('reserved', ('group', 'address', 'word', 'objdump')),
    'arm64-shipping-vectors/vectors.tsv': ('shipping', ('group', 'word', 'mnemonic', 'operands', 'source')),
    'arm64-shipping-vectors/boundary.tsv': ('shipping-boundary', ('word', 'mnemonic', 'operands')),
}

# Known-input pins (git blob id, bytes, data rows, unknown rows). They are
# enforced by default: a missing or differing input refuses the run (exit 3).
# --allow-unpinned turns enforcement off; it exists for synthetic tests only.
PINS = {
    'arm64-coverage-vectors/vectors.tsv': ('76c91ab46e085f0dc350eba8b19509884638ecca', 92770, 1835, 1022),
    'arm64-feature-vectors/vectors.tsv': ('068c3113e072c4bc791c8378cf6721390c28551a', 22381, 319, 0),
    'arm64-feature-vectors/boundary.tsv': ('1bc245c94b73bb7427020872e9d945bb8f20fac1', 102149, 3126, 1516),
    'arm64-reserved-vectors/vectors.tsv': ('447156190b8b6bc96260e21e9b0b27c0975f7992', 33889, 693, 275),
    'arm64-shipping-vectors/vectors.tsv': ('c126f0cfb048aaf49e11d37e0bd91b4370aa3345', 54257, 901, 0),
    'arm64-shipping-vectors/boundary.tsv': ('be7bcf4f27417957b0bb83a83159a64ef7d8a204', 812177, 27989, 7701),
}

# ModelError codes. Only the invalid_* codes claim the word is reserved; every
# other code means "valid ISA, outside what AIRS models".
VALIDITY_CODES = frozenset((
    'invalid_instruction_word', 'invalid_movk_shift', 'invalid_logical_immediate',
    'invalid_extract_encoding', 'invalid_bitfield_encoding',
))
SCOPE_CODES = frozenset((
    'unsupported_pauth', 'unsupported_control_flow', 'unsupported_memory_base',
    'ambiguous_pair_registers', 'ambiguous_writeback', 'unsupported_instruction',
    'cfg_condition_not_modeled', 'cfg_wsp_not_modeled', 'cfg_shift_not_modeled',
    'cfg_extended_sp_not_modeled', 'cfg_extend_not_modeled', 'cfg_logical_shift_not_modeled',
    'cfg_logical_sp_destination_not_modeled', 'cfg_memory_base_not_modeled',
))

BLOCKING = frozenset((
    'OVER-ADMIT', 'WRONG-ADMIT', 'FALSE-INVALID', 'DECODER-EXCEPTION', 'UNPARSEABLE', 'ORACLE-CONFLICT',
))
CATEGORIES = ('AGREE', 'AGREE-REJECT', 'BOTH-REJECT', 'SCOPE-DECLINE') + tuple(sorted(BLOCKING))

COND = ('eq', 'ne', 'hs', 'lo', 'mi', 'pl', 'vs', 'vc', 'hi', 'ls', 'ge', 'lt', 'gt', 'le', 'al', 'nv')
COND_ALIASES = {'cs': 'hs', 'cc': 'lo'}
DISAGREEMENT_COLUMNS = (
    'category', 'level', 'decoder', 'file', 'lines', 'group', 'address', 'word', 'airs_result',
    'detail', 'oracle_mnemonic', 'oracle_operands', 'reason', 'oracle_elsewhere',
)


class HarnessRefusal(Exception):
    """A usage, safety, or derivation failure (exit code 2)."""


class PinRefusal(HarnessRefusal):
    """An input is missing or differs from its pin (exit code 3)."""


# --------------------------------------------------------------------------
# Kind table: every kind either decoder can emit, with its family and width.
# --------------------------------------------------------------------------
KIND_TABLE: dict[str, tuple[str, str, int]] = {}


def _fam(family: str, ops: tuple[str, ...], suffix: str = '', prefixes: str = 'wx') -> None:
    for op in ops:
        for p in prefixes:
            KIND_TABLE[p + op + suffix] = (family, op, 32 if p == 'w' else 64)


def _one(kind: str, family: str, op: str, width: int) -> None:
    KIND_TABLE[kind] = (family, op, width)


_one('nop', 'nop', 'nop', 0)
_one('ret', 'ret', 'ret', 0)
_one('bl', 'branch', 'bl', 64)
_one('b', 'branch', 'b', 64)
_one('bcond', 'bcond', 'b', 64)
_one('stp', 'pair', 'stp', 64)
_one('ldp', 'pair', 'ldp', 64)
_one('add', 'addsub', 'add', 64)
_one('sub', 'addsub', 'sub', 64)
_one('mov', 'mov', 'mov', 64)
_one('movz', 'movwide', 'movz', 64)
_one('movn', 'movwide', 'movn', 64)
_fam('movk', ('movk',))
_fam('div', ('udiv', 'sdiv'))
_fam('unary', ('rev16', 'rev', 'rbit', 'cls', 'clz'))
_one('xrev32', 'unary', 'rev32', 64)
_fam('ccmp', ('ccmp', 'ccmn'), '_imm')
_fam('ccmp', ('ccmp', 'ccmn'), '_reg')
_fam('adc', ('adc', 'adcs', 'sbc', 'sbcs'))
_one('wadd', 'addimm', 'add', 32)
_one('wadds', 'addimm', 'adds', 32)
_one('wsubs', 'addimm', 'subs', 32)
_one('xadds', 'addimm', 'adds', 64)
_one('xsubs', 'addimm', 'subs', 64)
_fam('addreg', ('adds', 'subs'), '_reg')
_fam('addext', ('adds', 'subs'), '_ext')
_fam('logreg', ('and', 'bic', 'orr', 'orn', 'eor', 'eon'), '_reg')
_fam('logreg', ('ands', 'bics'))
_fam('logimm', ('and', 'orr', 'eor', 'ands'), '_imm')
_one('smulh', 'mulh', 'smulh', 64)
_one('umulh', 'mulh', 'umulh', 64)
for _k in ('smaddl', 'smsubl', 'umaddl', 'umsubl'):
    _one(_k, 'widen', _k, 64)
_fam('madd', ('madd', 'msub'))
_fam('shiftv', ('lslv', 'lsrv', 'asrv', 'rorv'))
_fam('extr', ('extr',))
_fam('bitfield', ('sbfm', 'bfm', 'ubfm'))
_one('wlsl', 'wlsl', 'lsl', 32)
_one('xstr', 'mem', 'str', 64)
_one('xldr', 'mem', 'ldr', 64)
_one('wstr', 'mem', 'str', 32)
_one('wldr', 'mem', 'ldr', 32)
_fam('csel', ('csel', 'csinc', 'csinv', 'csneg'))
_fam('tb', ('tbz', 'tbnz'))
_fam('cb', ('cbz', 'cbnz'))


# --------------------------------------------------------------------------
# Source-derived kind/code inventory (abstract interpretation over ast).
# --------------------------------------------------------------------------
class DerivationError(Exception):
    pass


class _NS:
    """Abstract value: not a tracked string value."""


NS = _NS()


class _Dict:
    __slots__ = ('inner',)

    def __init__(self, inner):
        self.inner = inner


def _join(a, b):
    if isinstance(a, frozenset) and isinstance(b, frozenset):
        return a | b
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [_join(x, y) for x, y in zip(a, b)]
    if isinstance(a, _Dict) and isinstance(b, _Dict):
        return _Dict(_join(a.inner, b.inner))
    return NS


def _join_all(items):
    items = list(items)
    if not items:
        return NS
    result = items[0]
    for item in items[1:]:
        result = _join(result, item)
    return result


def _ev(node, env):
    if isinstance(node, ast.Constant):
        return frozenset((node.value,)) if isinstance(node.value, str) else NS
    if isinstance(node, ast.Name):
        return env.get(node.id, NS)
    if isinstance(node, (ast.Tuple, ast.List)):
        return [_ev(e, env) for e in node.elts]
    if isinstance(node, ast.Dict):
        return _Dict(_join_all(_ev(v, env) for v in node.values))
    if isinstance(node, ast.IfExp):
        return _join(_ev(node.body, env), _ev(node.orelse, env))
    if isinstance(node, ast.BinOp):
        if not isinstance(node.op, ast.Add):
            return NS
        left, right = _ev(node.left, env), _ev(node.right, env)
        if isinstance(left, frozenset) and isinstance(right, frozenset):
            return frozenset(x + y for x in left for y in right)
        return NS
    if isinstance(node, ast.Subscript):
        value = _ev(node.value, env)
        if isinstance(value, list):
            index = node.slice
            if isinstance(index, ast.Constant) and isinstance(index.value, int) and -len(value) <= index.value < len(value):
                return value[index.value]
            return _join_all(value)
        if isinstance(value, _Dict):
            return value.inner
        return NS
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'get':
        value = _ev(node.func.value, env)
        return value.inner if isinstance(value, _Dict) else NS
    return NS


def _assign(target, value, env):
    if isinstance(target, ast.Name):
        env[target.id] = value
    elif isinstance(target, (ast.Tuple, ast.List)):
        if isinstance(value, _Dict):
            value = value.inner
        if isinstance(value, list) and len(value) == len(target.elts):
            for sub, item in zip(target.elts, value):
                _assign(sub, item, env)
        else:
            for sub in target.elts:
                _assign(sub, NS, env)


class _Derived:
    def __init__(self):
        self.kinds: set[str] = set()
        self.codes: set[str] = set()
        self.includes_linear = False


def _walk(statements, env, out):
    for statement in statements:
        if isinstance(statement, ast.Assign):
            value = _ev(statement.value, env)
            for target in statement.targets:
                _assign(target, value, env)
        elif isinstance(statement, (ast.AugAssign, ast.AnnAssign)):
            if isinstance(statement.target, ast.Name):
                env[statement.target.id] = NS
        elif isinstance(statement, (ast.Expr, ast.Pass, ast.Import, ast.ImportFrom)):
            continue
        elif isinstance(statement, ast.Return):
            _derive_return(statement, env, out)
            return False
        elif isinstance(statement, ast.Raise):
            _derive_raise(statement, env, out)
            return False
        elif isinstance(statement, ast.If):
            body_env, else_env = dict(env), dict(env)
            body_falls = _walk(statement.body, body_env, out)
            else_falls = _walk(statement.orelse, else_env, out)
            if not body_falls and not else_falls:
                return False
            if body_falls and else_falls:
                merged = {k: _join(body_env.get(k, NS), else_env.get(k, NS)) for k in set(body_env) | set(else_env)}
            else:
                merged = body_env if body_falls else else_env
            env.clear()
            env.update(merged)
        else:
            raise DerivationError(f'unsupported statement {type(statement).__name__} at line {statement.lineno}')
    return True


def _derive_return(statement, env, out):
    call = statement.value
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
        raise DerivationError(f'unsupported return at line {statement.lineno}')
    if call.func.id == 'decode_linear':
        out.includes_linear = True
        return
    if call.func.id != 'Instruction':
        raise DerivationError(f'unsupported return call {call.func.id} at line {statement.lineno}')
    kind_node = call.args[2] if len(call.args) > 2 else next((k.value for k in call.keywords if k.arg == 'kind'), None)
    if kind_node is None:
        raise DerivationError(f'Instruction without kind at line {statement.lineno}')
    kinds = _ev(kind_node, env)
    if not isinstance(kinds, frozenset) or not kinds:
        raise DerivationError(f'cannot derive kind at line {statement.lineno}')
    out.kinds |= kinds


def _derive_raise(statement, env, out):
    call = statement.exc
    if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == 'ModelError' and call.args):
        raise DerivationError(f'unsupported raise at line {statement.lineno}')
    codes = _ev(call.args[0], env)
    if not isinstance(codes, frozenset) or not codes:
        raise DerivationError(f'cannot derive error code at line {statement.lineno}')
    out.codes |= codes


def derive_decoder(source: str) -> _Derived:
    """Derive the kinds and ModelError codes decode_instruction can produce."""
    tree = ast.parse(source)
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'decode_instruction']
    if len(functions) != 1:
        raise DerivationError('decode_instruction not found exactly once')
    out = _Derived()
    _walk(functions[0].body, {}, out)
    return out


def derive_inventory(arm64_source: str, cfg_source: str):
    """Return {decoder: (kinds, codes)} with the linear fallthrough merged into cfg."""
    linear = derive_decoder(arm64_source)
    chained = derive_decoder(cfg_source)
    cfg_kinds, cfg_codes = set(chained.kinds), set(chained.codes)
    if chained.includes_linear:
        cfg_kinds |= linear.kinds
        cfg_codes |= linear.codes
    return {'linear': (set(linear.kinds), set(linear.codes)), 'cfg': (cfg_kinds, cfg_codes)}


def check_inventory(inventory, kind_table, fp_kinds, validity_codes, scope_codes):
    """Return (errors, stale-table warnings). Errors are fatal."""
    errors, emitted = [], set()
    known_codes = set(validity_codes) | set(scope_codes)
    for decoder, (kinds, codes) in sorted(inventory.items()):
        emitted |= kinds
        for kind in sorted(kinds - set(kind_table)):
            errors.append(f'{decoder} can emit kind {kind!r} that the kind table does not cover')
        for code in sorted(codes - known_codes):
            errors.append(f'{decoder} can raise code {code!r} that is not classified as validity or scope')
    for kind in sorted(set(fp_kinds) - set(kind_table)):
        errors.append(f'frame-pointer kind {kind!r} is missing from the kind table')
    return errors, sorted(set(kind_table) - emitted)


# --------------------------------------------------------------------------
# Oracle text: parsing and canonical operand form.
# --------------------------------------------------------------------------
_COMMENT = re.compile(r'\s*(?:;|//).*$')
_SYMBOL = re.compile(r'\s*<[^<>]*>\s*$')
_REG = re.compile(r'^([xw])(\d{1,2})$')
_IMM = re.compile(r'^#(-?)(0x[0-9a-f]+|\d+)$')
_MOD = re.compile(r'^(lsl|lsr|asr|ror|uxtb|uxth|uxtw|uxtx|sxtb|sxth|sxtw|sxtx)(?:\s+#(-?)(0x[0-9a-f]+|\d+))?$')
_TARGET = re.compile(r'^0x[0-9a-f]+$')
_MEM = re.compile(r'^\[([^\]]*)\](!?)$')
_WORD = re.compile(r'^[0-9a-fA-F]{8}$')
_ADDRESS = re.compile(r'^0x[0-9a-fA-F]+$')
NORMALIZED_MNEMONICS = frozenset(('mov', 'and', 'orr', 'eor', 'ands', 'tst', 'movz', 'movn'))
NO_DESTINATION = frozenset(('cmp', 'cmn', 'tst', 'ccmp', 'ccmn', 'stp', 'str', 'cbz', 'cbnz', 'tbz', 'tbnz', 'b', 'bl', 'ret', 'nop'))


class Oracle:
    __slots__ = ('state', 'mnemonic', 'tokens', 'text')

    def __init__(self, state, mnemonic='', tokens=(), text=''):
        self.state, self.mnemonic, self.tokens, self.text = state, mnemonic, tuple(tokens), text


def _split_operands(text):
    tokens, depth, current = [], 0, []
    for ch in text:
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
        if ch == ',' and depth == 0:
            tokens.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    tail = ''.join(current).strip()
    if tail or tokens:
        tokens.append(tail)
    return tokens


def _int(sign, digits):
    return -int(digits, 0) if sign else int(digits, 0)


def _canon_register(t):
    if t in ('sp', 'wsp', 'xzr', 'wzr'):
        return t
    if t == 'fp':
        return 'x29'
    if t == 'lr':
        return 'x30'
    m = _REG.match(t)
    if m and int(m.group(2)) <= 30:
        return m.group(1) + str(int(m.group(2)))
    return None


def _canon_token(raw, address_known):
    t = raw.strip().lower()
    register = _canon_register(t)
    if register:
        return register
    m = _IMM.match(t)
    if m:
        return '#%d' % _int(m.group(1), m.group(2))
    m = _MOD.match(t)
    if m:
        name, sign, digits = m.groups()
        if digits is None:
            return name
        amount = _int(sign, digits)
        if amount == 0 and (name == 'lsl' or name.startswith(('u', 's'))):
            return name if name != 'lsl' else ''
        return '%s #%d' % (name, amount)
    t = COND_ALIASES.get(t, t)
    if t in COND:
        return t
    if _TARGET.match(t):
        return '@%d' % int(t, 16) if address_known else '@?'
    m = _MEM.match(t)
    if m:
        parts = [p.strip() for p in m.group(1).split(',')]
        base = _canon_register(parts[0]) if parts else None
        if base and len(parts) == 1:
            return '[%s]%s' % (base, m.group(2))
        if base and len(parts) == 2:
            offset = _IMM.match(parts[1])
            if offset:
                value = _int(offset.group(1), offset.group(2))
                return '[%s]%s' % (base, m.group(2)) if value == 0 else '[%s,#%d]%s' % (base, value, m.group(2))
    return '?raw:' + t


def normalize(mnemonic, tokens):
    """Reduce immediates modulo the register width for the mnemonics that print signed."""
    if mnemonic in NORMALIZED_MNEMONICS and tokens:
        mask = (1 << (32 if tokens[0].startswith('w') else 64)) - 1
        tokens = tuple('#%d' % (int(t[1:]) & mask) if t.startswith('#') and t[1:].lstrip('-').isdigit() else t for t in tokens)
    return mnemonic, tuple(tokens)


def parse_oracle(mnemonic_field, operand_field, address_known):
    """Return an Oracle: state is 'unknown', 'valid', or 'bad'."""
    mnemonic = mnemonic_field.strip().lower()
    text = (mnemonic_field.strip() + ' ' + operand_field.strip()).strip()
    if mnemonic == '<unknown>':
        return Oracle('unknown', text='<unknown>')
    if not mnemonic or re.search(r'\s', mnemonic) or not re.match(r'^[a-z][a-z0-9_.]*$', mnemonic):
        return Oracle('bad', text=text)
    if mnemonic.startswith('b.'):
        mnemonic = 'b.' + COND_ALIASES.get(mnemonic[2:], mnemonic[2:])
    operands = _SYMBOL.sub('', _COMMENT.sub('', operand_field)).strip()
    tokens = [_canon_token(t, address_known) for t in _split_operands(operands)]
    tokens = [t for t in tokens if t != '']
    mnemonic, tokens = normalize(mnemonic, tokens)
    return Oracle('valid', mnemonic, tokens, text)


def oracle_effects(mnemonic, tokens):
    """SP/FP effects implied by the oracle text: destination registers and writeback bases."""
    if mnemonic in NO_DESTINATION or mnemonic.startswith('b.'):
        dests = []
    else:
        dests = list(tokens[:2] if mnemonic == 'ldp' else tokens[:1])
    writes_sp = any(d in ('sp', 'wsp') for d in dests)
    writes_fp = any(d in ('x29', 'w29') for d in dests)
    for index, token in enumerate(tokens):
        if token.startswith('['):
            base = token[1:].split(']')[0].split(',')[0]
            post = token.endswith(']') and index + 1 < len(tokens) and tokens[index + 1].startswith('#')
            if token.endswith(']!') or post:
                writes_sp |= base == 'sp'
                writes_fp |= base == 'x29'
    return writes_sp, writes_fp


# --------------------------------------------------------------------------
# Expected oracle forms for an admitted AIRS instruction.
# --------------------------------------------------------------------------
def _r(width, n, sp=False):
    if n == 31:
        return ('sp' if width == 64 else 'wsp') if sp else ('xzr' if width == 64 else 'wzr')
    return ('x' if width == 64 else 'w') + str(n)


def _i(value):
    return '#%d' % value


def _shift_tail(name, amount):
    if name == 'lsl' and amount == 0:
        return ()
    return ('%s #%d' % (name, amount),)


def _imm12_tails(value):
    tails = [(_i(value),)]
    if value % 4096 == 0 and value >> 12 <= 0xfff:
        tails.append((_i(value >> 12), 'lsl #12'))
    return tails


def _target(i, known):
    return '@%d' % ((i.address + i.immediate) & M64) if known else '@?'


def _mem(base, offset, suffix=''):
    return '[%s]%s' % (base, suffix) if offset == 0 else '[%s,%s]%s' % (base, _i(offset), suffix)


def _f_nop(i, op, w, known):
    return [('nop', ())]


def _f_ret(i, op, w, known):
    if i.rn == 30:
        return [('ret', ()), ('ret', ('x30',))]
    return [('ret', (_r(64, i.rn),))]


def _f_branch(i, op, w, known):
    return [(op, (_target(i, known),))]


def _f_bcond(i, op, w, known):
    return [('b.' + COND[int(i.addressing)], (_target(i, known),))]


def _f_pair(i, op, w, known):
    base = _r(64, i.rn, True)
    regs = (_r(64, i.rd), _r(64, i.rt2))
    if i.addressing == 'offset':
        return [(op, regs + (_mem(base, i.immediate),))]
    if i.addressing == 'pre':
        return [(op, regs + (_mem(base, i.immediate, '!'),))]
    return [(op, regs + ('[%s]' % base, _i(i.immediate)))]


def _f_addsub(i, op, w, known):
    d, n = _r(64, i.rd, True), _r(64, i.rn, True)
    forms = [(op, (d, n) + tail) for tail in _imm12_tails(i.immediate)]
    if op == 'add' and i.immediate == 0 and (i.rd == 31 or i.rn == 31):
        forms.append(('mov', (d, n)))
    return forms


def _f_mov(i, op, w, known):
    d, m = _r(64, i.rd), _r(64, i.rn)
    return [('mov', (d, m)), ('orr', (d, 'xzr', m))]


def _movwide_group(value):
    if value == 0:
        return [(0, shift) for shift in (0, 16, 32, 48)]
    shift = ((value & -value).bit_length() - 1) // 16 * 16
    return [(value >> shift, shift)]


def _f_movwide(i, op, w, known):
    d = _r(64, i.rd)
    forms = []
    for imm16, shift in _movwide_group(i.immediate):
        forms.append((op, (d, _i(imm16)) + (('lsl #%d' % shift,) if shift else ())))
    value = i.immediate if op == 'movz' else ~i.immediate & M64
    forms.append(('mov', (d, _i(value))))
    return forms


def _f_movk(i, op, w, known):
    shift = int(i.addressing)
    return [('movk', (_r(w, i.rd), _i(i.immediate)) + (('lsl #%d' % shift,) if shift else ()))]


def _f_div(i, op, w, known):
    return [(op, (_r(w, i.rd), _r(w, i.rn), _r(w, i.rt2)))]


def _f_unary(i, op, w, known):
    return [(op, (_r(w, i.rd), _r(w, i.rn)))]


def _f_ccmp(i, op, w, known):
    second = _i(i.rt2) if i.kind.endswith('_imm') else _r(w, i.rt2)
    return [(op, (_r(w, i.rn), second, _i(i.immediate), COND[int(i.addressing)]))]


def _f_adc(i, op, w, known):
    d, n, m = _r(w, i.rd), _r(w, i.rn), _r(w, i.rt2)
    forms = [(op, (d, n, m))]
    if op in ('sbc', 'sbcs') and i.rn == 31:
        forms.append(('ngc' if op == 'sbc' else 'ngcs', (d, m)))
    return forms


def _f_addimm(i, op, w, known):
    d, n = _r(w, i.rd), _r(w, i.rn)
    forms = []
    for tail in _imm12_tails(i.immediate):
        forms.append((op, (d, n) + tail))
        if i.rd == 31 and op != 'add':
            forms.append(('cmn' if op == 'adds' else 'cmp', (n,) + tail))
    return forms


def _f_addreg(i, op, w, known):
    d, n, m = _r(w, i.rd), _r(w, i.rn), _r(w, i.rt2)
    tail = _shift_tail(i.addressing, i.immediate)
    forms = [(op, (d, n, m) + tail)]
    if i.rd == 31:
        forms.append(('cmn' if op == 'adds' else 'cmp', (n, m) + tail))
    if op == 'subs' and i.rn == 31:
        forms.append(('negs', (d, m) + tail))
    return forms


def _f_addext(i, op, w, known):
    wide_rm = w == 64 and i.addressing in ('uxtx', 'sxtx')
    d, n, m = _r(w, i.rd), _r(w, i.rn), _r(64 if wide_rm else 32, i.rt2)
    ext = i.addressing + (' #%d' % i.immediate if i.immediate else '')
    forms = [(op, (d, n, m, ext))]
    if i.rd == 31:
        forms.append(('cmn' if op == 'adds' else 'cmp', (n, m, ext)))
    return forms


def _f_logreg(i, op, w, known):
    d, n, m = _r(w, i.rd), _r(w, i.rn), _r(w, i.rt2)
    tail = _shift_tail(i.addressing, i.immediate)
    forms = [(op, (d, n, m) + tail)]
    if op == 'orr' and i.rn == 31 and not tail:
        forms.append(('mov', (d, m)))
    if op == 'orn' and i.rn == 31:
        forms.append(('mvn', (d, m) + tail))
    if op == 'ands' and i.rd == 31:
        forms.append(('tst', (n, m) + tail))
    return forms


def _f_logimm(i, op, w, known):
    d, n = _r(w, i.rd), _r(w, i.rn)
    forms = [(op, (d, n, _i(i.immediate)))]
    if op == 'ands' and i.rd == 31:
        forms.append(('tst', (n, _i(i.immediate))))
    if op == 'orr' and i.rn == 31:
        forms.append(('mov', (d, _i(i.immediate))))
    return forms


def _f_mulh(i, op, w, known):
    return [(op, (_r(64, i.rd), _r(64, i.rn), _r(64, i.rt2)))]


_WIDEN_ALIAS = {'smaddl': 'smull', 'smsubl': 'smnegl', 'umaddl': 'umull', 'umsubl': 'umnegl'}


def _f_widen(i, op, w, known):
    d, n, m = _r(64, i.rd), _r(32, i.rn), _r(32, i.rt2)
    forms = [(op, (d, n, m, _r(64, i.immediate)))]
    if i.immediate == 31:
        forms.append((_WIDEN_ALIAS[op], (d, n, m)))
    return forms


def _f_madd(i, op, w, known):
    d, n, m = _r(w, i.rd), _r(w, i.rn), _r(w, i.rt2)
    forms = [(op, (d, n, m, _r(w, i.immediate)))]
    if i.immediate == 31:
        forms.append(('mul' if op == 'madd' else 'mneg', (d, n, m)))
    return forms


def _f_shiftv(i, op, w, known):
    regs = (_r(w, i.rd), _r(w, i.rn), _r(w, i.rt2))
    return [(op, regs), (op[:-1], regs)]


def _f_extr(i, op, w, known):
    d, n, m = _r(w, i.rd), _r(w, i.rn), _r(w, i.rt2)
    forms = [('extr', (d, n, m, _i(i.immediate)))]
    if i.rn == i.rt2:
        forms.append(('ror', (d, n, _i(i.immediate))))
    return forms


def _bitfield_forms(i, op, w, immr, imms):
    d, n = _r(w, i.rd), _r(w, i.rn)
    forms = [(op, (d, n, _i(immr), _i(imms)))]
    n32 = _r(32, i.rn)
    if op == 'sbfm':
        if imms == w - 1:
            forms.append(('asr', (d, n, _i(immr))))
        if immr == 0 and imms in (7, 15):
            forms.append(('sxtb' if imms == 7 else 'sxth', (d, n32)))
        if w == 64 and immr == 0 and imms == 31:
            forms.append(('sxtw', (d, n32)))
        if imms >= immr:
            forms.append(('sbfx', (d, n, _i(immr), _i(imms - immr + 1))))
        else:
            forms.append(('sbfiz', (d, n, _i(w - immr), _i(imms + 1))))
    elif op == 'ubfm':
        if imms == w - 1:
            forms.append(('lsr', (d, n, _i(immr))))
        elif imms + 1 == immr:
            forms.append(('lsl', (d, n, _i(w - immr))))
        if w == 32 and immr == 0 and imms in (7, 15):
            forms.append(('uxtb' if imms == 7 else 'uxth', (d, n)))
        if imms >= immr:
            forms.append(('ubfx', (d, n, _i(immr), _i(imms - immr + 1))))
        else:
            forms.append(('ubfiz', (d, n, _i(w - immr), _i(imms + 1))))
    else:
        if imms >= immr:
            forms.append(('bfxil', (d, n, _i(immr), _i(imms - immr + 1))))
        else:
            forms.append(('bfi', (d, n, _i(w - immr), _i(imms + 1))))
            if i.rn == 31:
                forms.append(('bfc', (d, _i(w - immr), _i(imms + 1))))
    return forms


def _f_bitfield(i, op, w, known):
    return _bitfield_forms(i, op, w, int(i.addressing), i.immediate)


def _f_wlsl(i, op, w, known):
    immr = 32 - i.immediate
    return _bitfield_forms(i, 'ubfm', 32, immr, immr - 1)


def _f_mem(i, op, w, known):
    return [(op, (_r(w, i.rd), _mem(_r(64, i.rn, True), i.immediate)))]


def _f_csel(i, op, w, known):
    cond = int(i.addressing)
    d, n, m = _r(w, i.rd), _r(w, i.rn), _r(w, i.rt2)
    forms = [(op, (d, n, m, COND[cond]))]
    inverse = COND[cond ^ 1]
    if i.rn == i.rt2:
        if op == 'csinc':
            forms.append(('cset', (d, inverse)) if i.rn == 31 else ('cinc', (d, n, inverse)))
        elif op == 'csinv':
            forms.append(('csetm', (d, inverse)) if i.rn == 31 else ('cinv', (d, n, inverse)))
        elif op == 'csneg':
            forms.append(('cneg', (d, n, inverse)))
    return forms


def _f_tb(i, op, w, known):
    return [(op, (_r(w, i.rn), _i(int(i.addressing)), _target(i, known)))]


def _f_cb(i, op, w, known):
    return [(op, (_r(w, i.rn), _target(i, known)))]


FAMILIES = {
    'nop': _f_nop, 'ret': _f_ret, 'branch': _f_branch, 'bcond': _f_bcond, 'pair': _f_pair,
    'addsub': _f_addsub, 'mov': _f_mov, 'movwide': _f_movwide, 'movk': _f_movk, 'div': _f_div,
    'unary': _f_unary, 'ccmp': _f_ccmp, 'adc': _f_adc, 'addimm': _f_addimm, 'addreg': _f_addreg,
    'addext': _f_addext, 'logreg': _f_logreg, 'logimm': _f_logimm, 'mulh': _f_mulh,
    'widen': _f_widen, 'madd': _f_madd, 'shiftv': _f_shiftv, 'extr': _f_extr,
    'bitfield': _f_bitfield, 'wlsl': _f_wlsl, 'mem': _f_mem, 'csel': _f_csel, 'tb': _f_tb, 'cb': _f_cb,
}


def expected_forms(ins, address_known):
    """All (mnemonic, canonical operands) an oracle may print for this admitted instruction."""
    family, op, width = KIND_TABLE[ins.kind]
    return {normalize(m, t) for m, t in FAMILIES[family](ins, op, width, address_known)}


# --------------------------------------------------------------------------
# Classification.
# --------------------------------------------------------------------------
def run_decoder(function, word, address):
    try:
        return 'ok', function(word, address)
    except ModelError as error:
        return 'refuse', error.code
    except Exception as error:  # noqa: BLE001 - a decoder crash is itself a finding
        return 'exception', '%s: %s' % (type(error).__name__, str(error)[:120])


def classify(result, oracle, address_known):
    """Return (category, level, reason, detail, airs_result) for one decoder result."""
    state, payload = result
    if state == 'exception':
        return 'DECODER-EXCEPTION', '', 'exception', payload, 'exception'
    if state == 'refuse':
        airs = 'refuse:' + payload
        if payload in VALIDITY_CODES:
            if oracle.state == 'unknown':
                return 'AGREE-REJECT', '', 'validity-code', payload, airs
            return 'FALSE-INVALID', '', 'false-invalid', 'AIRS claims %s but the oracle decodes it' % payload, airs
        if payload not in SCOPE_CODES:
            return 'DECODER-EXCEPTION', '', 'unknown-code', 'unclassified error code ' + payload, airs
        if oracle.state == 'unknown':
            return 'BOTH-REJECT', '', 'scope-code', payload, airs
        return 'SCOPE-DECLINE', '', 'scope-code', payload, airs
    ins = payload
    airs = 'ok:' + str(getattr(ins, 'kind', '?'))
    if getattr(ins, 'kind', None) not in KIND_TABLE:
        return 'DECODER-EXCEPTION', '', 'unknown-kind', 'kind not in the kind table', airs
    if oracle.state == 'unknown':
        return 'OVER-ADMIT', '', 'over-admit', 'AIRS admits %s but the oracle rejects the word' % ins.kind, airs
    if oracle.state == 'bad':
        return 'WRONG-ADMIT', 'O', 'unparsed-operand', 'oracle text not understood: ' + oracle.text[:80], airs
    try:
        forms = expected_forms(ins, address_known)
    except Exception as error:  # noqa: BLE001
        return 'DECODER-EXCEPTION', '', 'comparator', '%s: %s' % (type(error).__name__, error), airs
    mnemonics = {m for m, _ in forms}
    if oracle.mnemonic not in mnemonics:
        return 'WRONG-ADMIT', 'F', 'mnemonic', 'oracle %s; expected one of %s' % (oracle.mnemonic, ','.join(sorted(mnemonics))), airs
    if (oracle.mnemonic, oracle.tokens) not in forms:
        raw = any(t.startswith('?raw') for t in oracle.tokens)
        detail = 'oracle %s %s; expected %s' % (oracle.mnemonic, ' | '.join(oracle.tokens),
                                                '; '.join(sorted(' | '.join(t) for m, t in forms if m == oracle.mnemonic)))
        return 'WRONG-ADMIT', 'O', 'unparsed-operand' if raw else 'operands', detail, airs
    sp, fp = oracle_effects(oracle.mnemonic, oracle.tokens)
    if sp != ins.changes_sp or fp != ins.changes_fp:
        detail = 'oracle sp=%d fp=%d; AIRS sp=%d fp=%d' % (sp, fp, ins.changes_sp, ins.changes_fp)
        return 'WRONG-ADMIT', 'P', 'effects', detail, airs
    return 'AGREE', '', 'match', ins.kind, airs


DECODERS = (('linear', arm64.decode_instruction), ('cfg', cfg.decode_instruction))


# --------------------------------------------------------------------------
# Input files.
# --------------------------------------------------------------------------
class Entry:
    __slots__ = ('lines', 'group', 'word_hex', 'word', 'address', 'oracle')

    def __init__(self, line, group, word_hex, address, oracle):
        self.lines = [line]
        self.group, self.word_hex, self.word = group, word_hex, int(word_hex, 16)
        self.address, self.oracle = address, oracle


class Parsed:
    def __init__(self):
        self.entries: list[Entry] = []
        self.bad: list[tuple[int, str, str]] = []
        self.conflicts: list[tuple[Entry, int, str]] = []
        self.rows = self.unknown = self.comments = self.blanks = 0
        self.words: dict[str, str] = {}


def parse_file(relpath, data, limit, specs=None):
    """Parse one vector file's bytes. Whole-file counts are independent of limit."""
    label, columns = (SPECS if specs is None else specs)[relpath]
    parsed = Parsed()
    seen: dict[tuple[str, int | None], Entry] = {}
    pieces = data.split(b'\n')
    if pieces and pieces[-1] == b'':
        pieces.pop()
    for number, raw in enumerate(pieces, 1):
        if len(raw) > MAX_LINE_BYTES:
            parsed.rows += 1
            parsed.bad.append((number, 'line-too-long', raw[:80].decode('utf-8', 'replace')))
            continue
        try:
            line = raw.decode('utf-8').rstrip('\r')
        except UnicodeDecodeError:
            parsed.rows += 1
            parsed.bad.append((number, 'bad-utf8', raw[:80].decode('utf-8', 'replace')))
            continue
        if not line.strip():
            parsed.blanks += 1
            continue
        if line.startswith('#'):
            parsed.comments += 1
            continue
        parsed.rows += 1
        fields = line.split('\t')
        if len(fields) != len(columns):
            parsed.bad.append((number, 'column-count-%d-expected-%d' % (len(fields), len(columns)), line[:120]))
            continue
        row = dict(zip(columns, fields))
        word = row['word'].strip()
        if not _WORD.match(word):
            parsed.bad.append((number, 'bad-word', line[:120]))
            continue
        address = None
        if 'address' in row:
            if not _ADDRESS.match(row['address'].strip()):
                parsed.bad.append((number, 'bad-address', line[:120]))
                continue
            address = int(row['address'].strip(), 16)
        known = address is not None
        if 'objdump' in row:
            text = row['objdump'].strip()
            pair = re.split(r'\s+', text, maxsplit=1)
            oracle = parse_oracle(pair[0], pair[1] if len(pair) > 1 else '', known)
        else:
            oracle = parse_oracle(row['mnemonic'], row['operands'], known)
        if oracle.state == 'bad':
            parsed.bad.append((number, 'bad-oracle-text', line[:120]))
            continue
        word = word.lower()
        parsed.unknown += oracle.state == 'unknown'
        state = 'unknown' if oracle.state == 'unknown' else 'valid'
        previous = parsed.words.get(word)
        parsed.words[word] = state if previous in (None, state) else 'mixed'
        key = (word, address)
        if key in seen:
            first_entry = seen[key]
            first_entry.lines.append(number)
            if (first_entry.oracle.state, first_entry.oracle.mnemonic, first_entry.oracle.tokens) != (oracle.state, oracle.mnemonic, oracle.tokens):
                parsed.conflicts.append((first_entry, number, oracle.text))
            continue
        if limit is not None and len(seen) >= limit:
            continue
        entry = Entry(number, row.get('group', ''), word, address, oracle)
        seen[key] = entry
        parsed.entries.append(entry)
    return parsed


def _git_blob_id(data):
    digest = hashlib.sha1(b'blob %d\0' % len(data))
    digest.update(data)
    return digest.hexdigest()


def _clean(text):
    return re.sub(r'[\t\r\n]+', ' ', str(text))


# --------------------------------------------------------------------------
# Driver.
# --------------------------------------------------------------------------
def run_harness(vectors_root, decoders=DECODERS, limit=None, allow_unpinned=False, rowsink=None, generated=None):
    """Decode every input row; return (summary, blocking_rows)."""
    root = Path(vectors_root) if generated is None else Path(generated).parent
    specs = SPECS if generated is None else {'generated.tsv': ('generated', ('address', 'word', 'mnemonic', 'operands'))}
    present = {}
    manifest = {}
    for relpath in sorted(specs):
        path = root / relpath if generated is None else Path(generated)
        if not path.is_file():
            manifest[relpath] = {'present': False}
            continue
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise HarnessRefusal('%s is %d bytes, over the %d byte input limit' % (relpath, size, MAX_FILE_BYTES))
        data = path.read_bytes()
        parsed = parse_file(relpath, data, limit, specs)
        blob = _git_blob_id(data)
        pin = PINS.get(relpath) if generated is None else None
        if pin is None:
            status = 'unpinned'
        else:
            status = 'match' if pin == (blob, len(data), parsed.rows, parsed.unknown) else 'mismatch'
        manifest[relpath] = {
            'present': True, 'sha256': hashlib.sha256(data).hexdigest(), 'git_blob_id': blob, 'bytes': len(data),
            'rows': parsed.rows, 'unknown_rows': parsed.unknown, 'comment_lines': parsed.comments,
            'blank_lines': parsed.blanks, 'malformed_rows': len(parsed.bad), 'decoded_rows': len(parsed.entries),
            'pin': status,
        }
        present[relpath] = parsed
    if not present:
        raise HarnessRefusal('no known vector file found under the vectors root')
    if generated is None and not allow_unpinned:
        bad = sorted(r for r in SPECS if manifest[r].get('pin') != 'match')
        if bad:
            raise PinRefusal('input missing or not matching its pin: ' + ', '.join(bad))

    word_states: dict[str, dict[str, str]] = {}
    for relpath, parsed in present.items():
        for word, state in parsed.words.items():
            word_states.setdefault(word, {})[specs[relpath][0]] = state
    names = [name for name, _ in decoders]
    counts = {r: {d: Counter() for d in names + ['-']} for r in present}
    refusals = {kind: {d: Counter() for d in names} for kind in ('SCOPE-DECLINE', 'AGREE-REJECT', 'BOTH-REJECT')}
    agree_by_kind = {d: Counter() for d in names}
    blocking = []

    def elsewhere(word, label):
        parts = ['%s:%s' % (other, state) for other, state in sorted(word_states.get(word, {}).items()) if other != label]
        return ','.join(parts)

    def add_blocking(relpath, entry, decoder, category, level, reason, detail, airs):
        label = specs[relpath][0]
        oracle = entry.oracle
        blocking.append({
            'category': category, 'level': level, 'decoder': decoder, 'file': relpath,
            'lines': ','.join(str(n) for n in sorted(entry.lines)), 'group': entry.group,
            'address': '' if entry.address is None else '%#x' % entry.address, 'word': entry.word_hex,
            'airs_result': airs, 'detail': _clean(detail), 'oracle_mnemonic': _clean(oracle.mnemonic or oracle.state),
            'oracle_operands': _clean(' | '.join(oracle.tokens)), 'reason': reason,
            'oracle_elsewhere': elsewhere(entry.word_hex, label),
        })

    for relpath, parsed in present.items():
        for number, reason, text in parsed.bad:
            counts[relpath]['-']['UNPARSEABLE'] += 1
            blocking.append({
                'category': 'UNPARSEABLE', 'level': '', 'decoder': '-', 'file': relpath, 'lines': str(number),
                'group': '', 'address': '', 'word': '', 'airs_result': '', 'detail': _clean(text),
                'oracle_mnemonic': '', 'oracle_operands': '', 'reason': reason, 'oracle_elsewhere': '',
            })
        for entry, number, text in parsed.conflicts:
            counts[relpath]['-']['ORACLE-CONFLICT'] += 1
            add_blocking(relpath, entry, '-', 'ORACLE-CONFLICT', '', 'same-file-duplicate',
                         'line %d says %s; first says %s' % (number, text, entry.oracle.text), '')
        for entry in parsed.entries:
            known = entry.address is not None
            for name, function in decoders:
                result = run_decoder(function, entry.word, entry.address or 0)
                category, level, reason, detail, airs = classify(result, entry.oracle, known)
                counts[relpath][name][category] += 1
                if category in refusals:
                    refusals[category][name][detail] += 1
                elif category == 'AGREE':
                    agree_by_kind[name][detail] += 1
                if category in BLOCKING:
                    add_blocking(relpath, entry, name, category, level, reason, detail, airs)
                if rowsink is not None:
                    rowsink((relpath, entry.lines[0], entry.group, entry.address, entry.word_hex,
                             entry.oracle.text, name, category, level, airs))

    blocking.sort(key=lambda r: (r['file'], int(r['lines'].split(',')[0]), r['decoder'], r['category'], r['word']))
    totals = {d: Counter() for d in names + ['-']}
    for relpath in counts:
        for d, counter in counts[relpath].items():
            totals[d].update(counter)
    differing = sorted(w for w, states in word_states.items() if len(set(states.values())) > 1 or 'mixed' in states.values())
    summary = {
        'schema': SCHEMA, 'harness_version': HARNESS_VERSION,
        'run': {'limit': limit, 'allow_unpinned': bool(allow_unpinned)},
        'inputs': manifest,
        'counts': {r: {d: dict(sorted(c.items())) for d, c in by.items() if c} for r, by in sorted(counts.items())},
        'totals': {d: dict(sorted(c.items())) for d, c in totals.items() if c},
        'scope_decline_by_code': {d: dict(sorted(refusals['SCOPE-DECLINE'][d].items())) for d in names},
        'agree_reject_by_code': {d: dict(sorted(refusals['AGREE-REJECT'][d].items())) for d in names},
        'both_reject_by_code': {d: dict(sorted(refusals['BOTH-REJECT'][d].items())) for d in names},
        'agree_by_kind': {d: dict(sorted(agree_by_kind[d].items())) for d in names},
        'blocking_total': len(blocking),
        'blocking_by_category': dict(sorted(Counter(r['category'] for r in blocking).items())),
        'cross_file_validity': {
            'note': 'words the oracle files disagree on (valid in one file, unknown in another); informational',
            'words_differing': len(differing), 'first_words': differing[:20],
        },
    }
    if generated is not None:
        summary['run']['input_mode'] = 'generated'
        summary['inputs']['generated.tsv']['pin'] = 'not-applicable'
    return summary, blocking


# --------------------------------------------------------------------------
# Output safety and writing.
# --------------------------------------------------------------------------
def out_dir_allowed(path, root, gitignore_lines):
    """An output inside the repository must sit under a plain ignored directory pattern."""
    resolved, base = Path(os.path.realpath(path)), Path(os.path.realpath(root))
    try:
        parts = resolved.relative_to(base).parts
    except ValueError:
        return True
    if not parts or parts[0] == '.git':
        return False
    for line in gitignore_lines:
        pattern = line.strip()
        if not pattern or pattern.startswith(('#', '!')) or not pattern.endswith('/'):
            continue
        if any(c in pattern for c in '*?['):
            continue
        anchored = pattern.startswith('/') or '/' in pattern.strip('/')
        wanted = tuple(pattern.strip('/').split('/'))
        if anchored:
            if parts[:len(wanted)] == wanted:
                return True
        elif wanted[0] in parts:
            return True
    return False


def _write_tsv(path, header, rows):
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        handle.write('\t'.join(header) + '\n')
        for row in rows:
            handle.write('\t'.join(_clean(row[c]) for c in header) + '\n')


def _output_names(out):
    names = [out / 'summary.json', out / 'run-info.json', out / 'rows.tsv.gz'] + sorted(out.glob('disagreements*.tsv'))
    return [p for p in names if p.exists()]


def write_outputs(out, summary, blocking):
    parts = [blocking[i:i + PART_ROWS] for i in range(0, len(blocking), PART_ROWS)] or [[]]
    names = ['disagreements.tsv'] if len(parts) == 1 else ['disagreements-%04d.tsv' % n for n in range(1, len(parts) + 1)]
    for name, chunk in zip(names, parts):
        _write_tsv(out / name, DISAGREEMENT_COLUMNS, chunk)
    summary['disagreement_files'] = names
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Compare AIRS ARM64 decoders with recorded disassembler vectors.')
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--vectors-root', help='directory laid out like the golden fixtures')
    inputs.add_argument('--generated', help='one generated address/word/mnemonic/operands TSV')
    parser.add_argument('--require-kind-coverage', action='store_true', help='fail if any derived kind never agrees')
    parser.add_argument('--out', required=True, help='output directory (outside the repository or under an ignored directory)')
    parser.add_argument('--limit', type=int, default=None, help='decode only the first N distinct rows of each file')
    parser.add_argument('--full', action='store_true', help='also write rows.tsv.gz with every classified row')
    parser.add_argument('--overwrite', action='store_true', help='replace existing harness outputs')
    parser.add_argument('--allow-unpinned', action='store_true', help='accept missing or changed inputs (synthetic tests only)')
    args = parser.parse_args(argv)
    started = time.process_time()
    try:
        if args.limit is not None and args.limit < 1:
            raise HarnessRefusal('--limit must be at least 1')
        sources = {name: Path(module.__file__).read_text(encoding='utf-8') for name, module in (('arm64.py', arm64), ('cfg.py', cfg))}
        try:
            inventory = derive_inventory(sources['arm64.py'], sources['cfg.py'])
        except DerivationError as error:
            raise HarnessRefusal('cannot derive the decoder kind inventory: %s' % error)
        errors, stale = check_inventory(inventory, KIND_TABLE, arm64._FP_DESTINATION_KINDS, VALIDITY_CODES, SCOPE_CODES)
        if errors:
            raise HarnessRefusal('kind table check failed: ' + '; '.join(errors))
        vectors = Path(args.vectors_root) if args.vectors_root else None
        if vectors is not None and not vectors.is_dir():
            raise HarnessRefusal('--vectors-root is not a directory')
        out = Path(args.out)
        ignore = ROOT / '.gitignore'
        lines = ignore.read_text(encoding='utf-8').splitlines() if ignore.is_file() else []
        if not out_dir_allowed(out, ROOT, lines):
            raise HarnessRefusal('--out would write inside the repository outside an ignored directory')
        if vectors is not None:
            real_out, real_vectors = Path(os.path.realpath(out)), Path(os.path.realpath(vectors))
            if real_out == real_vectors or real_vectors in real_out.parents:
                raise HarnessRefusal('--out must not be inside --vectors-root')
        elif Path(args.generated).resolve() in {p.resolve() for p in _output_names(out)}:
            raise HarnessRefusal('--generated must not be an output file')
        existing = _output_names(out) if out.is_dir() else []
        if existing and not args.overwrite:
            raise HarnessRefusal('refusing to overwrite existing outputs (use --overwrite): ' + ', '.join(p.name for p in existing))
        out.mkdir(parents=True, exist_ok=True)
        for path in existing:
            path.unlink()
        sink = None
        gz = None
        if args.full:
            handle = open(out / 'rows.tsv.gz', 'wb')
            gz = gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0)

            def sink(row):
                fields = list(row)
                fields[1] = str(fields[1])
                fields[3] = '' if fields[3] is None else '%#x' % fields[3]
                gz.write(('\t'.join(_clean(v) for v in fields) + '\n').encode('utf-8'))
        try:
            summary, blocking = run_harness(vectors, limit=args.limit, allow_unpinned=args.allow_unpinned, rowsink=sink, generated=args.generated)
        finally:
            if gz is not None:
                gz.close()
                handle.close()
        summary['decoder_sources'] = {name: hashlib.sha256(text.encode('utf-8')).hexdigest() for name, text in sorted(sources.items())}
        summary['derived_inventory'] = {d: {'kinds': sorted(k), 'codes': sorted(c)} for d, (k, c) in sorted(inventory.items())}
        summary['kind_table'] = {'size': len(KIND_TABLE), 'never_emitted': stale}
        summary['kinds_never_agreeing'] = {
            d: sorted(inventory[d][0] - set(summary['agree_by_kind'][d])) for d in sorted(inventory)}
        summary['run']['full'] = bool(args.full)
        write_outputs(out, summary, blocking)
        info = {'cpu_seconds': round(time.process_time() - started, 3), 'python': sys.version.split()[0]}
        (out / 'run-info.json').write_text(json.dumps(info, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    except PinRefusal as error:
        print('arm64-oracle-diff: %s' % error, file=sys.stderr)
        return 3
    except HarnessRefusal as error:
        print('arm64-oracle-diff: %s' % error, file=sys.stderr)
        return 2
    except Exception as error:  # noqa: BLE001
        print('arm64-oracle-diff: internal error: %s: %s' % (type(error).__name__, error), file=sys.stderr)
        return 2
    print('blocking rows: %d' % summary['blocking_total'])
    missing = {d: kinds for d, kinds in summary['kinds_never_agreeing'].items() if kinds}
    if args.require_kind_coverage and missing:
        print('arm64-oracle-diff: kinds never agreeing: ' + '; '.join(
            d + ': ' + ','.join(kinds) for d, kinds in missing.items()), file=sys.stderr)
        return 1
    return 1 if summary['blocking_total'] else 0


if __name__ == '__main__':
    sys.exit(main())
