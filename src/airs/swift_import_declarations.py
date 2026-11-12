"""Closed-grammar Swift declaration *syntax* for imported symbols (swift-import-declaration-syntax-v1).

Decides, from an imported symbol alone, whether a call to it can be skipped as
"cannot raise a Swift error".  Only four entities are admitted (function,
metadata accessor, initializer, allocating initializer); every accessor,
thunk, specialization, generic, closure, async, isolation or typed-throws form
declines with an explicit reason, and no partial identity is ever returned.
A wrong "cannot raise" hides a throwing call, so every doubt resolves to decline.
"""
from dataclasses import dataclass, fields
from enum import Enum
import re

from .swift_declaration_profiles import (BroadDeclarationResult, ParseLimits, SwiftContext,
                                         SwiftType, UnsupportedReason)

IMPORT_SYNTAX_MODEL = 'swift-import-declaration-syntax-v1'
# The native report reader refuses JSON nested more than 32 levels deep. It counts
# the report object as level 0 and every member or element, scalar or container,
# as one level below its parent. In a broad-imports report an identity object is
# at level 5 (report, calls, row, admission, declaration, identity), so no value
# inside a serialised identity may lie more than 27 levels below the identity.
_NATIVE_NESTING_LIMIT = 32
_IDENTITY_REPORT_LEVEL = 5
_MAX_IDENTITY_VALUE_DEPTH = _NATIVE_NESTING_LIMIT - _IDENTITY_REPORT_LEVEL


class ImportEntity(str, Enum):
    FUNCTION = 'function'
    METADATA_ACCESSOR = 'metadata_accessor'
    INITIALIZER = 'initializer'
    ALLOCATING_INITIALIZER = 'allocating_initializer'


@dataclass(frozen=True, slots=True)
class ImportedDeclaration:
    symbol: str
    module: str
    context: tuple[SwiftContext, ...]
    entity: ImportEntity
    name: str
    parameter_labels: tuple[str | None, ...]
    parameter_types: tuple[SwiftType, ...]
    result_type: SwiftType | None
    throws: bool
    syntax_model: str = IMPORT_SYNTAX_MODEL


class _Decline(Exception):
    def __init__(self, reason, detail, offset):
        super().__init__(detail)
        self.reason, self.detail, self.offset = reason, detail, offset


_R = UnsupportedReason
_KNOWN = {'b': 'Bool', 'd': 'Double', 'f': 'Float', 'i': 'Int', 'u': 'UInt', 'S': 'String',
          's': 'Substring', 'J': 'Character', 'O': 'ObjectIdentifier', 'V': 'UnsafeRawPointer',
          'v': 'UnsafeMutableRawPointer', 'W': 'UnsafeRawBufferPointer',
          'w': 'UnsafeMutableRawBufferPointer'}
_PROTOCOL_LETTERS = frozenset('ejklmtxyzBEFGHKLMQTUXYZ')
_NOMINAL = {'V': 'struct', 'O': 'enum', 'C': 'class'}
_LITERAL = re.compile(r'[A-Za-z_][A-Za-z_0-9$]*')
_FRAGMENT = re.compile(r'[A-Za-z_0-9$]+')
_NUMBER = re.compile(r'[0-9]+')
_FUNCTION_TYPE_X = frozenset(('XE', 'XK', 'Xf', 'XB', 'XC', 'XL'))
_ASYNC_Y = frozenset(('Ya', 'Yb', 'Yc', 'YA', 'YC', 'YT', 'Yi', 'Yu'))


class _Item:
    """One operand-stack entry or substitution-table entry.

    kind: ident, module, ext, type, proto, empty, first.  Types carry the
    SwiftType built when they were pushed, a structural identity key (for
    initializer Self), the defining module and the context chain.
    """
    __slots__ = ('kind', 'text', 'swift', 'tkind', 'nominal', 'depth', 'key', 'in_ext',
                 'home', 'chain', 'shared', 'variadic', 'base', 'module', 'elements', 'word_origin')

    def __init__(self, kind, text='', **fields):
        self.kind, self.text = kind, text
        self.swift = self.tkind = self.nominal = self.key = self.base = self.module = None
        self.elements = ()
        self.depth, self.in_ext, self.home, self.chain = 0, False, 'Swift', ()
        self.shared = self.variadic = False
        self.word_origin = False
        for name, value in fields.items():
            setattr(self, name, value)

    def derived(self, **fields):
        clone = _Item(self.kind, self.text)
        for name in _Item.__slots__:
            setattr(clone, name, getattr(self, name))
        for name, value in fields.items():
            setattr(clone, name, value)
        return clone


_EMPTY, _FIRST = _Item('empty'), _Item('first')


class _ImportParser:
    def __init__(self, symbol, limits):
        self.limits = limits
        self.text = symbol[1:] if symbol.startswith('_') else symbol
        self.pos = 2
        self.subs, self.words, self.stack = [], [], []
        self.throws = False
        self.nodes = 0
        self.work = 0

    # ---- bounds -------------------------------------------------------------------
    def decline(self, reason, detail, at=None):
        raise _Decline(reason, detail, self.pos if at is None else at)

    def limit(self, exceeded, detail, at=None):
        if exceeded:
            self.decline(_R.RESOURCE_LIMIT, detail, at)

    def tick(self, amount=1):
        self.work += amount
        self.limit(self.work > self.limits.max_symbol_length * 4, 'work limit')

    def peek(self, size=1):
        return self.text[self.pos:self.pos + size]

    def push(self, item):
        self.limit(len(self.stack) >= self.limits.max_nodes, 'operand stack limit')
        self.stack.append(item)

    def pop(self, at=None):
        if not self.stack:
            self.decline(_R.INVALID_GRAMMAR, 'missing operand', at)
        return self.stack.pop()

    def add_sub(self, item):
        self.limit(len(self.subs) >= self.limits.max_substitutions, 'substitution table limit')
        self.subs.append(item)

    # ---- identifiers --------------------------------------------------------------
    def literal(self, fragment=False):
        match = re.match(r'[1-9][0-9]*', self.text[self.pos:])
        if not match:
            self.decline(_R.INVALID_GRAMMAR, 'expected identifier literal length')
        self.limit(len(match[0]) > 6 or int(match[0]) > self.limits.max_identifier_length, 'identifier length limit')
        size = int(match[0])
        self.pos += len(match[0])
        value = self.text[self.pos:self.pos + size]
        if len(value) != size or not (_FRAGMENT if fragment else _LITERAL).fullmatch(value):
            self.decline(_R.INVALID_GRAMMAR, 'invalid or truncated identifier literal')
        self.pos += size
        begin = None
        for index in range(len(value) + 1):
            char = value[index] if index < len(value) else ''
            if begin is not None and (not char or char == '_' or (char.isupper() and not value[index - 1].isupper())):
                if index - begin >= 2 and len(self.words) < 26:
                    self.words.append(value[begin:index])
                begin = None
            if begin is None and char and not char.isdigit() and char != '_':
                begin = index
        return value

    def identifier(self):
        word_origin = self.peek() == '0'
        if self.peek(2) == '00':
            self.decline(_R.UNICODE_IDENTIFIER, 'Punycode identifier')
        if self.peek() != '0':
            value = self.literal()
        else:
            self.pos += 1
            parts, more, closed = [], True, False
            while self.pos < len(self.text):
                self.tick()
                while more and self.peek().isalpha():
                    char = self.text[self.pos]
                    index = ord(char.lower()) - 97
                    if index >= len(self.words):
                        self.decline(_R.UNKNOWN_SUBSTITUTION, 'word substitution index is absent')
                    parts.append(self.words[index])
                    self.pos += 1
                    if char.isupper():
                        more = False
                if self.peek() == '0':
                    self.pos += 1
                    closed = True
                    break
                parts.append(self.literal(fragment=True))
                if not more:
                    closed = True
                    break
            if not closed:
                self.decline(_R.INVALID_GRAMMAR, 'unterminated word-substituted identifier')
            value = ''.join(parts)
            if len(value) > self.limits.max_identifier_length or not _LITERAL.fullmatch(value):
                self.decline(_R.INVALID_GRAMMAR, 'invalid expanded identifier')
        item = _Item('ident', value, word_origin=word_origin)
        self.add_sub(item)
        return item

    # ---- types --------------------------------------------------------------------
    def new_type(self, name, tkind, nominal=None, arguments=(), **fields):
        self.nodes += 1
        self.limit(self.nodes > self.limits.max_nodes, 'AST node limit')
        depth = 1 + max((a.depth for a in arguments), default=0)
        self.limit(depth > self.limits.max_type_depth, 'type depth limit')
        swift = SwiftType(name, tuple(a.swift for a in arguments), nominal_kind=nominal)
        return _Item('type', name, swift=swift, tkind=tkind, nominal=nominal, depth=depth, **fields)

    def pop_type(self, at, allow_modifiers=False, allow_tuple=False):
        item = self.pop(at)
        if item is _EMPTY:
            return self.new_type('Swift.Void', 'void')
        if item.kind != 'type':
            if item.kind == 'proto':
                self.decline(_R.PROTOCOL_CONTEXT, 'protocol in type position', at)
            self.decline(_R.INVALID_GRAMMAR, 'non-type operand', at)
        if item.tkind == 'array_unbound':
            self.decline(_R.UNSUPPORTED_PRODUCTION, 'unbound generic nominal', at)
        if item.tkind == 'tuple' and not allow_tuple:
            self.decline(_R.UNSUPPORTED_PRODUCTION, 'tuple is not a type here', at)
        if not allow_modifiers and (item.shared or item.variadic):
            self.decline(_R.INVALID_GRAMMAR, 'parameter modifier outside parameter position', at)
        return item

    def pop_context(self, at):
        item = self.pop(at)
        if item.kind == 'ident':
            if item.word_origin:
                self.decline(_R.WORD_SUBSTITUTION, 'word-substituted module identifier', at)
            return _Item('module', item.text)
        if item.kind in ('module', 'ext'):
            return item
        if item.kind == 'type' and item.tkind in ('nominal', 'known') and not (item.shared or item.variadic):
            return item
        if item.kind == 'proto':
            self.decline(_R.PROTOCOL_CONTEXT, 'protocol used as a nominal context', at)
        self.decline(_R.INVALID_GRAMMAR, 'invalid nominal context', at)

    @staticmethod
    def context_name(ctx):
        return ctx.base.text if ctx.kind == 'ext' else ctx.text

    # ---- operator loop (iterative; no recursion anywhere) ---------------------------
    def parse(self):
        text = self.text
        while self.pos < len(text):
            self.tick()
            at = self.pos
            char = text[at]
            tail = text[at:]
            if char.isdigit():
                self.push(self.identifier())
            elif char == 's':
                self.pos += 1
                self.push(_Item('module', 'Swift'))
            elif char == 'S':
                self.standard_substitution()
            elif char == 'A':
                self.multi_substitution()
            elif char in _NOMINAL or char == 'P':
                self.nominal(char, at)
            elif char == 'E':
                self.extension(at)
            elif char == 'y':
                if text[at + 1:at + 2] == 'p':
                    self.pos += 2
                    self.push(self.new_type('Any', 'any'))
                else:
                    self.pos += 1
                    self.push(_EMPTY)
            elif char == '_':
                self.pos += 1
                self.push(_FIRST)
            elif char == 'h':
                self.pos += 1
                item = self.pop_type(at)
                if item.tkind == 'void':
                    self.decline(_R.INVALID_GRAMMAR, 'shared marker lacks type', at)
                self.push(item.derived(shared=True))
            elif char == 'd':
                self.pos += 1
                item = self.pop_type(at, allow_modifiers=True)
                if item.variadic or item.tkind == 'void':
                    self.decline(_R.INVALID_GRAMMAR, 'variadic marker misplaced', at)
                self.push(item.derived(variadic=True))
            elif char == 't':
                self.pos += 1
                self.tuple(at)
            elif char == 'G':
                self.pos += 1
                self.bound_generic(at)
            elif char == 'K':
                if self.throws:
                    self.decline(_R.INVALID_GRAMMAR, 'duplicate throws annotation')
                if text[at + 1:at + 2] not in ('F', 'c'):
                    self.decline(_R.INVALID_GRAMMAR, 'throws marker not at entity function-type position')
                self.pos += 1
                self.throws = True
            elif char == 'c':
                if tail in ('cfC', 'cfc'):
                    return self.initializer(at, tail[2] == 'C')
                self.decline(_R.CLOSURE_TYPE, 'function type operand; rethrows cannot be decided')
            elif char == 'F':
                return self.function(at)
            elif tail == 'Ma':
                return self.metadata_accessor(at)
            elif char == 'Y':
                if tail.startswith('YK'):
                    self.decline(_R.TYPED_THROWS, 'typed throws')
                if tail[:2] in _ASYNC_Y:
                    self.decline(_R.ASYNC_CONTEXT, 'async, isolation or sendability annotation')
                self.decline(_R.UNSUPPORTED_PRODUCTION, 'unsupported Y annotation')
            elif char == 'X':
                if tail[:2] in _FUNCTION_TYPE_X:
                    self.decline(_R.CLOSURE_TYPE, 'function type operand')
                self.decline(_R.UNSUPPORTED_PRODUCTION, 'unsupported X production')
            elif char == 'T':
                self.decline(_R.THUNK_OR_SPECIALIZATION, 'thunk or specialization')
            elif char in 'xqlrRQ':
                self.decline(_R.GENERIC_REQUIREMENTS, 'generic parameter, signature or opaque type')
            elif char in 'vi':
                self.decline(_R.UNSUPPORTED_PRODUCTION, 'accessor entity: effects are not encoded in accessor manglings')
            else:
                self.decline(_R.UNSUPPORTED_PRODUCTION, 'unsupported grammar operator: ' + char)
        self.decline(_R.INVALID_GRAMMAR, 'missing entity operator')

    # ---- substitutions ----------------------------------------------------------------
    def repeat_count(self, digits, at):
        if digits[0] == '0':
            self.decline(_R.INVALID_GRAMMAR, 'repeat count with a leading zero', at)
        self.limit(len(digits) > 6 or int(digits) > self.limits.max_parameters, 'repeat count limit', at)
        if int(digits) < 2:
            self.decline(_R.INVALID_GRAMMAR, 'repeat count below 2', at)
        return int(digits)

    def standard_substitution(self):
        at = self.pos
        following = self.text[at + 1:at + 2]
        if following == 'g':
            self.pos += 2
            wrapped = self.pop_type(at)
            if wrapped.tkind == 'void':
                self.decline(_R.INVALID_GRAMMAR, 'optional lacks type', at)
            item = self.new_type('Optional', 'optional', None, (wrapped,), elements=(wrapped,))
            self.add_sub(item)
            self.push(item)
            return
        if following == 'o':
            self.pos += 2
            self.push(_Item('module', '__C'))
            return
        if following == 'C':
            self.pos += 2
            self.push(_Item('module', '__C_Synthesized'))
            return
        self.pos += 1
        match = _NUMBER.match(self.text, self.pos)
        count = 1
        if match:
            self.pos += len(match[0])
            count = self.repeat_count(match[0], at)
        code = self.peek()
        if code in _KNOWN:
            self.pos += 1
            for _ in range(count):
                self.tick()
                name = _KNOWN[code]
                self.push(self.new_type('Swift.' + name, 'known', 'struct', key=('known', name),
                                        chain=(SwiftContext(name, 'struct'),)))
            return
        if code == 'a' and count == 1:
            self.pos += 1
            self.push(self.new_type('Swift.Array', 'array_unbound'))
            return
        if code in _PROTOCOL_LETTERS:
            self.decline(_R.PROTOCOL_CONTEXT, 'standard protocol substitution', at)
        self.decline(_R.UNKNOWN_SUBSTITUTION, 'standard substitution outside the closed table', at)

    def multi_substitution(self):
        at = self.pos
        self.pos += 1
        while True:
            self.tick()
            match = re.match(r'([0-9]+)?([a-zA-Z_])', self.text[self.pos:])
            if not match:
                self.decline(_R.UNKNOWN_SUBSTITUTION, 'unsupported substitution encoding', at)
            self.pos += len(match[0])
            letter = match[2]
            if letter == '_':
                self.decline(_R.UNKNOWN_SUBSTITUTION, 'substitution index >= 26 is not admitted', at)
            count = self.repeat_count(match[1], at) if match[1] else 1
            index = ord(letter.lower()) - 97
            if index >= len(self.subs):
                self.decline(_R.UNKNOWN_SUBSTITUTION, 'substitution index is absent', at)
            entry = self.subs[index]
            for _ in range(count):
                self.tick()
                self.push(entry.derived(shared=False, variadic=False) if entry.kind == 'type' else entry)
            if letter.isupper():
                return

    # ---- contexts -----------------------------------------------------------------------
    def nominal(self, char, at):
        self.pos += 1
        name = self.pop(at)
        if name.kind != 'ident':
            self.decline(_R.INVALID_GRAMMAR, 'nominal lacks identifier', at)
        ctx = self.pop_context(at)
        full = self.context_name(ctx) + '.' + name.text
        if char == 'P':
            item = _Item('proto', full)
        else:
            if ctx.kind == 'module':
                home, parent, key_ctx = ctx.text, (), ('module', ctx.text)
            elif ctx.kind == 'ext':
                home, parent, key_ctx = ctx.module, ctx.chain, ('ext', ctx.base.key, ctx.module)
            else:
                home, parent, key_ctx = ctx.home, ctx.chain, ctx.key
            chain = parent + (SwiftContext(name.text, _NOMINAL[char]),)
            self.limit(len(chain) > self.limits.max_context_depth, 'context nesting limit', at)
            item = self.new_type(full, 'nominal', _NOMINAL[char], key=(_NOMINAL[char], key_ctx, name.text),
                                 home=home, chain=chain,
                                 in_ext=ctx.kind == 'ext' or (ctx.kind == 'type' and ctx.in_ext))
        self.add_sub(item)
        self.push(item)

    def extension(self, at):
        self.pos += 1
        module = self.pop(at)
        if module.kind == 'ident':
            if module.word_origin:
                self.decline(_R.WORD_SUBSTITUTION, 'word-substituted module identifier', at)
            module = _Item('module', module.text)
        if module.kind != 'module':
            self.decline(_R.INVALID_GRAMMAR, 'extension lacks module', at)
        base = self.pop(at)
        if base.kind == 'proto':
            self.decline(_R.PROTOCOL_CONTEXT, 'protocol extension context', at)
        if not (base.kind == 'type' and base.tkind in ('nominal', 'known') and not (base.shared or base.variadic)):
            self.decline(_R.INVALID_GRAMMAR, 'extension of a non-nominal', at)
        if base.in_ext or any(entry.kind == 'ext' for entry in self.stack):
            self.decline(_R.UNSUPPORTED_PRODUCTION, 'nested extension', at)
        # The extension stands in for the extended nominal in the recorded chain.
        chain = base.chain[:-1] + (SwiftContext(base.text, 'extension'),)
        self.push(_Item('ext', module.text, base=base, module=module.text, chain=chain))

    # ---- tuples and generics ------------------------------------------------------------
    def tuple(self, at):
        elements = []
        while True:
            self.tick()
            if not self.stack:
                self.decline(_R.INVALID_GRAMMAR, 'tuple lacks first-element marker', at)
            top = self.stack[-1]
            if top is _FIRST:
                self.stack.pop()
                break
            if top.kind != 'type':
                self.decline(_R.INVALID_GRAMMAR, 'non-type tuple element', at)
            elements.append(self.stack.pop())
            self.limit(len(elements) >= self.limits.max_parameters, 'tuple element limit', at)
        if not self.stack or self.stack[-1].kind != 'type':
            self.decline(_R.INVALID_GRAMMAR, 'tuple first element missing', at)
        elements.append(self.stack.pop())
        elements.reverse()
        self.limit(len(elements) > self.limits.max_parameters, 'tuple element limit', at)
        for element in elements:
            if element.tkind in ('tuple', 'void', 'array_unbound'):
                self.decline(_R.UNSUPPORTED_PRODUCTION, 'nested or unbound tuple element', at)
        self.push(self.new_type('Tuple', 'tuple', None, tuple(elements), elements=tuple(elements)))

    def bound_generic(self, at):
        arguments = []
        while self.stack and self.stack[-1].kind == 'type':
            self.tick()
            arguments.append(self.pop_type(at))
        if not self.stack or self.stack[-1] is not _EMPTY:
            self.decline(_R.INVALID_GRAMMAR, 'generic arguments lack start marker', at)
        self.stack.pop()
        if not self.stack or self.stack[-1].kind != 'type' or self.stack[-1].tkind != 'array_unbound':
            self.decline(_R.UNSUPPORTED_PRODUCTION, 'bound generic other than Swift.Array', at)
        self.stack.pop()
        if len(arguments) != 1 or arguments[0].tkind == 'void':
            self.decline(_R.UNSUPPORTED_PRODUCTION, 'Array needs exactly one argument', at)
        item = self.new_type('Swift.Array', 'array', 'struct', (arguments[0],))
        self.add_sub(item)
        self.push(item)

    # ---- entities ---------------------------------------------------------------------------
    def signature(self, at):
        params = self.pop_type(at, allow_modifiers=True, allow_tuple=True)
        if params.tkind == 'void':
            plist = ()
        elif params.tkind == 'tuple':
            plist = params.swift.arguments
            modifiers = [e.variadic for e in params.elements]
        else:
            if params.variadic:
                self.decline(_R.INVALID_GRAMMAR, 'variadic outside a parameter tuple', at)
            plist, modifiers = (params.swift,), [False]
        result = self.pop_type(at)
        self.limit(len(plist) > self.limits.max_parameters, 'parameter count limit', at)
        if not plist:
            return (), (), result
        if self.stack and self.stack[-1] is _EMPTY:
            self.stack.pop()
            if params.tkind == 'tuple' and len(plist) == 1 and not modifiers[0]:
                self.decline(_R.INVALID_GRAMMAR, 'unlabeled one-element parameter tuple', at)
            return (None,) * len(plist), plist, result
        if params.tkind != 'tuple':
            self.decline(_R.INVALID_GRAMMAR, 'labeled parameters require a parameter tuple', at)
        if len(self.stack) < len(plist):
            self.decline(_R.INVALID_GRAMMAR, 'parameter label/type arity mismatch', at)
        raw = self.stack[-len(plist):]
        del self.stack[-len(plist):]
        if not all(entry.kind == 'ident' or entry is _FIRST for entry in raw):
            self.decline(_R.INVALID_GRAMMAR, 'parameter label/type arity mismatch', at)
        if all(entry is _FIRST for entry in raw):
            self.decline(_R.INVALID_GRAMMAR, 'all-unlabeled label list (mangler emits y)', at)
        return tuple(None if entry is _FIRST else entry.text for entry in raw), plist, result

    def entity_context(self, at):
        if len(self.stack) != 1:
            self.decline(_R.INVALID_GRAMMAR, 'unexpected operands before the entity', at)
        return self.pop_context(at)

    @staticmethod
    def module_of(ctx):
        if ctx.kind == 'ext':
            return ctx.module
        return ctx.home

    def declaration(self, entity, module, context, name, labels, params, result):
        return dict(entity=entity, module=module, context=context, name=name, labels=labels,
                    params=params, result=result, throws=self.throws)

    def metadata_accessor(self, at):
        self.pos = len(self.text)
        if (len(self.stack) != 1 or self.stack[0].kind != 'type' or self.stack[0].tkind != 'nominal'
                or self.stack[0].shared or self.stack[0].variadic):
            self.decline(_R.UNSUPPORTED_PRODUCTION if len(self.stack) == 1 else _R.INVALID_GRAMMAR,
                         'metadata accessor needs exactly one V/C/O nominal type', at)
        if self.throws:
            self.decline(_R.INVALID_GRAMMAR, 'throws marker not at entity function-type position', at)
        item = self.stack[0]
        return self.declaration(ImportEntity.METADATA_ACCESSOR, item.home, item.chain, '', (), (), None)

    def initializer(self, at, allocating):
        self.pos = len(self.text)
        labels, params, result = self.signature(at)
        ctx = self.entity_context(at)
        if ctx.kind == 'module':
            self.decline(_R.INVALID_GRAMMAR, 'initializer lacks nominal context', at)
        self_type = ctx.base if ctx.kind == 'ext' else ctx

        def same(a, b):
            return a.tkind in ('nominal', 'known') and a.key is not None and a.key == b.key
        if not (same(result, self_type) or (result.tkind == 'optional' and same(result.elements[0], self_type))):
            self.decline(_R.INVALID_GRAMMAR, 'initializer result is not Self or Self?', at)
        entity = ImportEntity.ALLOCATING_INITIALIZER if allocating else ImportEntity.INITIALIZER
        return self.declaration(entity, self.module_of(ctx), ctx.chain, '', labels, params, result.swift)

    def function(self, at):
        self.pos += 1
        static = self.peek() == 'Z'
        if static:
            self.pos += 1
        if self.pos != len(self.text):
            self.decline(_R.THUNK_OR_SPECIALIZATION if self.peek() == 'T' else _R.UNCONSUMED_SUFFIX,
                         'unconsumed suffix after F')
        labels, params, result = self.signature(at)
        if not self.stack or self.stack[-1].kind != 'ident':
            self.decline(_R.INVALID_GRAMMAR, 'function lacks name', at)
        name = self.stack.pop().text
        ctx = self.entity_context(at)
        if ctx.kind == 'module':
            if static:
                self.decline(_R.INVALID_GRAMMAR, 'static function lacks nominal context', at)
            module, context = ctx.text, ()
        else:
            base = ctx.base if ctx.kind == 'ext' else ctx
            if base.nominal != 'struct':
                self.decline(_R.UNSUPPORTED_PRODUCTION, 'method in a non-struct context', at)
            module, context = self.module_of(ctx), ctx.chain
        return self.declaration(ImportEntity.FUNCTION, module, context, name, labels, params, result.swift)


def parse_import_declaration(symbol: str, *, limits: ParseLimits = ParseLimits()) -> BroadDeclarationResult:
    """Parse a fully consumed, closed-grammar imported symbol, or return a typed refusal.

    Success identifies source-level syntax only: the entity cannot raise a Swift
    error unless ``identity.throws`` is true.  Nothing here proves ABI support or
    call-target identity.
    """
    if not isinstance(symbol, str) or not symbol.isascii() or any(ord(c) < 32 for c in symbol):
        return BroadDeclarationResult(None, UnsupportedReason.INVALID_INPUT, 'expected an ASCII external symbol without symbolic references')
    if not isinstance(limits, ParseLimits) or any(not isinstance(getattr(limits, f), int) or getattr(limits, f) < 1 for f in limits.__dataclass_fields__):
        return BroadDeclarationResult(None, UnsupportedReason.INVALID_INPUT, 'limits must be positive integers')
    if len(symbol) > limits.max_symbol_length:
        return BroadDeclarationResult(None, UnsupportedReason.RESOURCE_LIMIT, 'symbol length limit')
    if not (symbol.startswith('$s') or symbol.startswith('_$s')):
        return BroadDeclarationResult(None, UnsupportedReason.INVALID_INPUT, 'expected stable Swift external symbol prefix')
    parser = _ImportParser(symbol, limits)
    try:
        fields = parser.parse()
    except _Decline as error:
        return BroadDeclarationResult(None, error.reason, error.detail, error.offset)
    identity = ImportedDeclaration(symbol, fields['module'], fields['context'], fields['entity'], fields['name'],
                                   fields['labels'], fields['params'], fields['result'], fields['throws'])
    if _serialised_depth_exceeded(identity):
        return BroadDeclarationResult(None, _R.RESOURCE_LIMIT, 'serialised identity depth limit', parser.pos)
    return BroadDeclarationResult(identity)


def _serialised_depth_exceeded(identity):
    # These identity dataclasses become dicts through asdict; their tuples become
    # JSON lists. Every field value and tuple element, scalar or container, is one
    # level below its parent; the identity itself is level 0. Walk the actual graph
    # without recursive serialization; revisiting a shared container only at a
    # greater depth bounds visits per container to the depth limit.
    pending = [(identity, 0)]
    seen = {}
    while pending:
        value, depth = pending.pop()
        if depth > _MAX_IDENTITY_VALUE_DEPTH:
            return True
        if not isinstance(value, (ImportedDeclaration, SwiftContext, SwiftType, tuple)):
            continue
        if seen.get(id(value), -1) >= depth:
            continue
        seen[id(value)] = depth
        children = value if isinstance(value, tuple) else (getattr(value, field.name) for field in fields(value))
        pending.extend((child, depth + 1) for child in children)
    return False
