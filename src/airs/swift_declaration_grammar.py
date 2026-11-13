"""Bounded Swift declaration syntax, pinned to swift-6.4.2-RELEASE.

Production references below name sections/productions in docs/ABI/Mangling.rst
at PINNED_TOOLCHAIN_TAG. The pinned demangler resolves specification ambiguity.
This is a text parser: it performs no I/O and establishes no runtime behavior.
"""
from dataclasses import dataclass, fields, replace
import json

SYNTAX_MODEL = 'swift-declaration-syntax-v2'
PINNED_TOOLCHAIN_TAG = 'swift-6.4.2-RELEASE'
REASONS = frozenset({'invalid_input', 'thunk_or_specialization',
    'unknown_substitution', 'truncated', 'malformed_symbol', 'trailing_input',
    'unsupported_production', 'limit_exceeded', 'typed_throws', 'accessor',
    'not_function_entity'})
_ACCESSORS = {
    'g': 'Getter', 's': 'Setter', 'm': 'MaterializeForSet', 'G': 'GlobalGetter',
    'w': 'WillSet', 'W': 'DidSet', 'r': 'ReadAccessor', 'M': 'ModifyAccessor',
    'x': 'YieldingMutateAccessor', 'y': 'YieldingBorrowAccessor',
    'b': 'BorrowAccessor', 'z': 'MutateAccessor', 'i': 'InitAccessor',
    'au': 'UnsafeMutableAddressor', 'aO': 'OwningMutableAddressor',
    'ao': 'NativeOwningMutableAddressor', 'aP': 'NativePinningMutableAddressor',
    'lu': 'UnsafeAddressor', 'lO': 'OwningAddressor',
    'lo': 'NativeOwningAddressor', 'lp': 'NativePinningAddressor',
}
ENTITY_KINDS = frozenset(_ACCESSORS.values()) | frozenset({
    'Function', 'Allocator', 'Constructor', 'Destructor', 'Deallocator',
    'IsolatedDeallocator', 'TypeMetadataAccessFunction'})


@dataclass(frozen=True, slots=True)
class GrammarLimits:
    max_symbol_length: int = 4096
    max_identifier_length: int = 256
    max_context_depth: int = 16
    max_nodes: int = 256
    max_substitutions: int = 128
    max_parameters: int = 64
    max_type_depth: int = 16
    max_generic_parameters: int = 32
    max_generic_requirements: int = 64


@dataclass(frozen=True, slots=True)
class ContextElement:
    kind: str
    name: str


@dataclass(frozen=True, slots=True)
class Effects:
    throws: bool = False
    typed_throws: 'TypeNode | None' = None
    is_async: bool = False
    isolation: str | None = None


@dataclass(frozen=True, slots=True)
class TypeNode:
    kind: str
    name: str = ''
    args: tuple['TypeNode', ...] = ()
    labels: tuple[str | None, ...] = ()
    modifiers: tuple[str, ...] = ()
    convention: str | None = None
    effects: Effects | None = None


@dataclass(frozen=True, slots=True)
class Requirement:
    kind: str
    subject: TypeNode
    constraint: TypeNode | str


@dataclass(frozen=True, slots=True)
class GenericSignature:
    parameter_counts: tuple[int, ...]
    requirements: tuple[Requirement, ...]


def _json_value(value):
    # Admitted identities have already passed the iterative depth/size checks.
    if hasattr(type(value), '__dataclass_fields__'):
        return {f.name: _json_value(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, tuple):
        return [_json_value(v) for v in value]
    return value


@dataclass(frozen=True, slots=True)
class DeclarationIdentity:
    entity: str
    context: tuple[ContextElement, ...]
    name: str
    labels: tuple[str | None, ...] = ()
    parameters: tuple[TypeNode, ...] = ()
    result: TypeNode | None = None
    generic_signature: GenericSignature | None = None
    effects: Effects = Effects()
    name_discriminator: str | None = None

    def oracle_projection(self):
        return dict(entity=self.entity, context=[[c.kind, c.name] for c in self.context],
                    name=self.name, labels=list(self.labels),
                    parameter_count=len(self.parameters))

    def to_json(self):
        return _json_value(self)

    def serialize(self):
        return json.dumps(self.to_json(), sort_keys=True, separators=(',', ':'),
                          ensure_ascii=True).encode('ascii')


@dataclass(frozen=True, slots=True)
class DeclarationResult:
    symbol: str
    identity: DeclarationIdentity | None = None
    throw_decision: str = 'undecided'
    reason: str = 'invalid_input'
    detail: str = ''
    offset: int | None = 0
    syntax_model: str = SYNTAX_MODEL


@dataclass(frozen=True, slots=True)
class _Name:
    text: str
    discriminator: str | None = None


@dataclass(frozen=True, slots=True)
class _Context:
    path: tuple[ContextElement, ...]
    signature: GenericSignature | None = None


@dataclass(frozen=True, slots=True)
class _Type:
    node: TypeNode
    path: tuple[ContextElement, ...] = ()
    signature: GenericSignature | None = None
    depth: int = 1
    size: int = 1


@dataclass(frozen=True, slots=True)
class _Annotation:
    kind: str
    value: object = None


class _Decline(Exception):
    def __init__(self, reason, detail='', offset=None):
        self.reason, self.detail, self.offset = reason, detail, offset


# Types / standard-substitutions. Data is organized by nominal kind; the
# current standard type names follow StandardTypesMangling.def, not old aliases.
_STANDARD = {}
for _kind, _pairs in (
    ('struct', 'A:AutoreleasingUnsafeMutablePointer a:Array b:Bool D:Dictionary '
     'd:Double f:Float h:Set I:DefaultIndices i:Int J:Character N:ClosedRange '
     'n:Range O:ObjectIdentifier P:UnsafePointer p:UnsafeMutablePointer '
     'R:UnsafeBufferPointer r:UnsafeMutableBufferPointer S:String s:Substring '
     'u:UInt V:UnsafeRawPointer v:UnsafeMutableRawPointer W:UnsafeRawBufferPointer '
     'w:UnsafeMutableRawBufferPointer'),
    ('enum', 'q:Optional'),
    ('protocol', 'B:BinaryFloatingPoint E:Encodable e:Decodable F:FloatingPoint '
     'G:RandomNumberGenerator H:Hashable j:Numeric K:BidirectionalCollection '
     'k:RandomAccessCollection L:Comparable l:Collection M:MutableCollection '
     'm:RangeReplaceableCollection Q:Equatable T:Sequence t:IteratorProtocol '
     'U:UnsignedInteger X:RangeExpression x:Strideable Y:RawRepresentable '
     'y:StringProtocol Z:SignedInteger z:BinaryInteger'),
    ('struct', 'cC:CheckedContinuation cc:UnsafeContinuation cE:CancellationError '
     'ce:UnownedSerialExecutor cG:TaskGroup cg:ThrowingTaskGroup cJ:UnownedJob '
     'cP:TaskPriority cS:AsyncStream cs:AsyncThrowingStream cT:Task ct:UnsafeCurrentTask'),
    ('protocol', 'cA:Actor cF:Executor cf:SerialExecutor ch:TaskExecutor '
     'cI:AsyncIteratorProtocol ci:AsyncSequence'),
    ('class', 'cM:MainActor'),
):
    for _pair in _pairs.split():
        _code, _name = _pair.split(':')
        _STANDARD[_code] = (_kind, _name)
del _kind, _pairs, _pair, _code, _name

_EMPTY, _FIRST, _VARIADIC = 'empty', 'first', 'variadic'
_CONVENTIONS = {'E': 'noescape', 'A': 'escaping_autoclosure', 'f': 'thin',
                'K': 'autoclosure', 'U': 'uncurried', 'L': 'escaping_block',
                'B': 'block', 'C': 'c'}


class _Parser:
    """Postfix production machine; each iteration consumes text or stack items."""
    def __init__(self, text, limits, start):
        self.text, self.limits, self.pos = text, limits, start
        self.stack, self.subs, self.words = [], [], []
        self.requirements = 0
        self.completed = False

    def fail(self, reason='malformed_symbol', detail='', offset=None):
        raise _Decline(reason, detail, self.pos if offset is None else offset)

    def budget(self, field, count):
        if count > getattr(self.limits, field):
            self.fail('limit_exceeded', field)

    def peek(self):
        return self.text[self.pos:self.pos + 1]

    def take(self):
        if self.pos >= len(self.text):
            self.fail('truncated')
        c = self.text[self.pos]
        self.pos += 1
        return c

    def eat(self, token):
        if self.text.startswith(token, self.pos):
            self.pos += len(token)
            return True
        return False

    def number(self):
        start, n = self.pos, 0
        while self.peek() and self.peek().isdigit():
            n = n * 10 + int(self.take())
        if self.pos == start:
            self.fail('truncated' if not self.peek() else 'malformed_symbol')
        return n

    def index(self):
        if self.eat('_'):
            return 0
        n = self.number()
        if not self.eat('_'):
            self.fail('truncated' if not self.peek() else 'malformed_symbol')
        return n + 1

    def pop(self, cls=None):
        if not self.stack:
            self.fail()
        value = self.stack.pop()
        if cls is not None and not isinstance(value, cls):
            if isinstance(value, _Annotation) and value.kind == 'unsupported':
                self.fail('unsupported_production', value.value)
            self.fail()
        return value

    def top_is(self, cls):
        return bool(self.stack) and isinstance(self.stack[-1], cls)

    def marker(self, value):
        if self.stack and self.stack[-1] == value:
            self.stack.pop()
            return True
        return False

    def substitute(self, value):
        self.budget('max_substitutions', len(self.subs) + 1)
        self.subs.append(value)
        return value

    def path(self, path):
        self.budget('max_context_depth', len(path))
        return tuple(path)

    def context(self):
        value = self.pop()
        if isinstance(value, _Name):
            return _Context(self.path((ContextElement('module', value.text),)))
        if isinstance(value, _Context):
            return value
        if isinstance(value, _Type) and value.path:
            return _Context(self.path(value.path), value.signature)
        if isinstance(value, DeclarationIdentity):
            return _Context(self.path(value.context + (ContextElement('local', value.name),)))
        self.fail()

    def ty(self, kind, name='', args=(), labels=(), modifiers=(), convention=None,
           effects=None, path=(), signature=None):
        depth = 1 + max((a.depth for a in args), default=0)
        size = 1 + sum(a.size for a in args)
        self.budget('max_type_depth', depth)
        # Keep a shared DAG while parsing. The final iterative occurrence walk
        # stops at max_nodes without expanding or serializing the whole DAG.
        # Temporary function wrappers and nominal contexts do not count.
        return _Type(TypeNode(kind, name, tuple(a.node for a in args), tuple(labels),
                              tuple(modifiers), convention, effects), tuple(path),
                     signature, depth, size)

    def modify(self, modifier):
        value = self.pop(_Type)
        return replace(value, node=replace(value.node,
                       modifiers=value.node.modifiers + (modifier,)))

    def nominal(self, kind):
        name, context = self.pop(_Name), self.context()
        path = self.path(context.path + (ContextElement(kind, name.text),))
        qualified = '.'.join(c.name for c in path if c.kind != 'extension')
        return self.substitute(self.ty('nominal', qualified, path=path,
                                      signature=context.signature))

    def identifier(self):
        # Identifiers / identifier, IDENTIFIER-PART, word substitutions, Punycode.
        word_mode = self.eat('0')
        puny = word_mode and self.eat('0')
        word_mode = word_mode and not puny
        parts = []
        while True:
            while word_mode and self.peek() and self.peek().isalpha():
                code = self.take()
                index = ord(code.lower()) - ord('a')
                if index >= len(self.words):
                    self.fail('unknown_substitution', 'identifier word')
                parts.append(self.words[index])
                if code.isupper():
                    word_mode = False
            if self.eat('0'):
                break
            n = self.number()
            self.budget('max_identifier_length', n)
            if n == 0:
                self.fail()
            if puny:
                self.eat('_')
            if self.pos + n > len(self.text):
                self.fail('truncated', offset=len(self.text))
            part = self.text[self.pos:self.pos + n]
            self.pos += n
            if puny:
                # Identifiers / Punycode: delimiter and encoding digit alphabet
                # differ from RFC 3492; basic characters remain unchanged.
                head, sep, tail = part.rpartition('_')
                encoded = tail if sep else part
                encoded = encoded.translate(str.maketrans('ABCDEFGHIJ', '0123456789'))
                part = (head + '-' + encoded if sep else encoded).encode('ascii').decode('punycode')
            else:
                start = None
                for i in range(len(part) + 1):
                    char = part[i:i + 1]
                    end = not char or char == '_' or (char.isupper() and i and not part[i - 1].isupper())
                    if start is not None and end:
                        if i - start >= 2 and len(self.words) < 26:
                            self.words.append(part[start:i])
                        start = None
                    if start is None and char and char != '_' and not char.isdigit():
                        start = i
            parts.append(part)
            if not word_mode:
                break
        text = ''.join(parts)
        if not text:
            self.fail()
        return self.substitute(_Name(text))

    def substitutions(self):
        # Substitutions / substitution, including merged and repeated references.
        while True:
            count = self.number() if self.peek().isdigit() else None
            c = self.take()
            if c == '_':
                index, repeats, last = 26 if count is None else count + 27, 1, True
            elif c.isalpha():
                index, repeats, last = ord(c.lower()) - ord('a'), count or 1, c.isupper()
            else:
                self.fail()
            if index >= len(self.subs):
                self.fail('unknown_substitution')
            self.budget('max_nodes', repeats)
            self.stack.extend([self.subs[index]] * repeats)
            if last:
                return

    def standard(self):
        # Types / standard-substitutions and the optional shortcut.
        if self.eat('o'):
            return _Context((ContextElement('module', '__C'),))
        if self.eat('C'):
            return _Context((ContextElement('module', '__C_Synthesized'),))
        if self.eat('g'):
            return self.substitute(self.ty('bound_generic', 'Swift.Optional', (self.pop(_Type),)))
        count = self.number() if self.peek().isdigit() else 1
        code = self.take()
        if code == 'c':
            code += self.take()
        if code not in _STANDARD:
            self.fail('unknown_substitution', 'standard type')
        kind, name = _STANDARD[code]
        path = (ContextElement('module', 'Swift'), ContextElement(kind, name))
        value = self.ty('nominal', 'Swift.' + name, path=path)
        self.budget('max_nodes', count)
        self.stack.extend([value] * (count - 1))
        return value

    def generic_param(self):
        # Types / GENERIC-PARAM-INDEX.
        if self.eat('d'):
            depth, index = self.index() + 1, self.index()
        elif self.eat('z'):
            depth, index = 0, 0
        elif self.eat('s'):
            self.fail('unsupported_production', 'constrained existential Self')
        else:
            depth, index = 0, self.index() + 1
        return self.ty('generic_param', 'τ_%d_%d' % (depth, index))

    def protocol(self):
        if self.top_is(_Type):
            value = self.pop(_Type)
            if value.path and value.path[-1].kind == 'protocol':
                return value
            self.fail()
        name, context = self.pop(_Name), self.context()
        path = self.path(context.path + (ContextElement('protocol', name.text),))
        return self.ty('nominal', '.'.join(c.name for c in path), path=path)

    def sequence(self, kind):
        # Types / type-list, protocol-list, pack-element-list.
        values, labels = [], []
        if not self.marker(_EMPTY):
            while True:
                first = self.marker(_FIRST)
                variadic = kind == 'tuple' and self.marker(_VARIADIC)
                label = self.pop(_Name).text if kind == 'tuple' and self.top_is(_Name) else None
                value = self.protocol() if kind == 'protocol' else self.pop(_Type)
                if variadic:
                    value = replace(value, node=replace(value.node,
                                    modifiers=value.node.modifiers + ('variadic',)))
                values.append(value)
                labels.append(label)
                if first:
                    break
        values.reverse()
        labels.reverse()
        if kind == 'protocol':
            return self.ty('existential' if len(values) <= 1 else 'composition', args=values)
        return self.ty(kind, args=values, labels=labels if kind == 'tuple' else ())

    def associated(self, base, compound=False):
        # Types / assoc-type-name and assoc-type-list.
        names = []
        while True:
            first = self.marker(_FIRST) if compound else True
            if self.top_is(_Type) and self.stack[-1].path and self.stack[-1].path[-1].kind == 'protocol':
                self.pop(_Type)
            names.append(self.pop(_Name).text)
            if first:
                break
        if base is None:
            base = self.pop(_Type)
        for name in reversed(names):
            base = self.ty('dependent_member', name, (base,))
        return base

    def requirement(self):
        # Generics / requirement, generic-param-pack-marker, inverse requirement.
        forms = {'b': ('base_class', 'generic'), 'c': ('base_class', 'assoc'),
                 'C': ('base_class', 'compound'), 'B': ('base_class', 'sub'),
                 's': ('same_type', 'generic'), 't': ('same_type', 'assoc'),
                 'T': ('same_type', 'compound'), 'S': ('same_type', 'sub'),
                 'l': ('layout', 'generic'), 'm': ('layout', 'assoc'),
                 'M': ('layout', 'compound'), 'L': ('layout', 'sub'),
                 'p': ('conformance', 'assoc'), 'P': ('conformance', 'compound'),
                 'Q': ('conformance', 'sub'), 'h': ('same_shape', 'generic'),
                 'v': ('pack_marker', 'generic'), 'i': ('inverse', 'generic'),
                 'I': ('inverse', 'sub'), 'j': ('inverse', 'assoc'),
                 'J': ('inverse', 'compound')}
        c = self.peek()
        if c == 'V':
            self.fail('unsupported_production', 'generic-param-value-marker')
        if c in forms:
            self.take()
            kind, form = forms[c]
        else:
            kind, form = 'conformance', 'generic'
        inverse = self.index() if kind == 'inverse' else None
        subject = self.pop(_Type) if form == 'sub' else self.generic_param()
        if form in ('assoc', 'compound'):
            subject = self.substitute(self.associated(subject, form == 'compound'))
        if kind == 'conformance':
            constraint = self.protocol().node
        elif kind in ('same_type', 'base_class', 'same_shape'):
            constraint = self.pop(_Type).node
        elif kind == 'pack_marker':
            constraint = ''
        elif kind == 'inverse':
            constraint = str(inverse)
        else:
            constraint = self.take()
            if constraint not in 'URNC DTB E e M m S'.replace(' ', ''):
                self.fail()
            if constraint in 'EeMmS':
                extra = [self.index()]
                if constraint in 'EM':
                    extra.append(self.index())
                constraint += ':' + ':'.join(map(str, extra))
        self.requirements += 1
        self.budget('max_generic_requirements', self.requirements)
        return Requirement(kind, subject.node, constraint)

    def signature(self, explicit):
        # Generics / generic-signature, GENERIC-PARAM-COUNT.
        counts = []
        if explicit:
            while not self.eat('l'):
                counts.append(0 if self.eat('z') else self.index() + 1)
                self.budget('max_generic_parameters', sum(counts))
        else:
            counts.append(1)
        self.budget('max_generic_parameters', sum(counts))
        reqs = []
        while self.top_is(Requirement):
            reqs.append(self.pop())
        return GenericSignature(tuple(counts), tuple(reversed(reqs)))

    def annotation(self):
        # Types / async, throws, function-isolation and list-type.
        c = self.take()
        modifiers = {'i': 'isolated', 'k': 'noDerivative', 'u': 'sending'}
        if c in modifiers:
            return self.modify(modifiers[c])
        if c in 'acAKbT':
            value = self.pop(_Type) if c in 'cK' else None
            return _Annotation(c, value)
        self.fail('unsupported_production', 'function annotation Y' + c)

    def function_parts(self):
        # Types / function-signature. Only direct annotations are inspected.
        ann = {}
        for code in ('T', 'isolation', 'K', 'b', 'a'):
            if self.top_is(_Annotation):
                a = self.stack[-1]
                matches = a.kind in ('c', 'A') if code == 'isolation' else a.kind == code
                if matches:
                    ann[a.kind] = self.pop().value
        if self.top_is(_Annotation):
            self.fail()
        argument = None if self.marker(_EMPTY) else self.pop(_Type)
        result = self.ty('void') if self.marker(_EMPTY) else self.pop(_Type)
        if argument is None:
            params = ()
        elif argument.node.kind == 'tuple':
            params = argument.node.args
        else:
            params = (argument.node,)
        self.budget('max_parameters', len(params))
        isolation = None
        if 'c' in ann:
            isolation = 'global_actor:' + ann['c'].node.name
        elif 'A' in ann:
            isolation = 'isolated_any'
        elif any('isolated' in p.modifiers for p in params):
            isolation = 'isolated_parameter'
        typed = ann.get('K')
        effects = Effects('K' in ann and typed is None,
                          typed.node if typed else None, 'a' in ann, isolation)
        if 'T' in ann:
            result = replace(result, node=replace(result.node,
                             modifiers=result.node.modifiers + ('sending',)))
        return params, result, effects, argument

    def function_type(self, convention='thick'):
        params, result, effects, argument = self.function_parts()
        # Reuse node metadata from the argument tree without a recursive walk.
        depth = max(result.depth, (argument.depth if argument else 0)) + 1
        size = result.size + (argument.size if argument else 0) + 1
        if argument and argument.node.kind == 'tuple':
            depth = max(result.depth + 1, argument.depth)
            size -= 1
        if effects.typed_throws:
            # The typed error is already bounded independently when parsed.
            size += 1
        self.budget('max_type_depth', depth)
        modifiers = ('autoclosure',) if convention in ('autoclosure', 'escaping_autoclosure') else ()
        return _Type(TypeNode('function', args=params + (result.node,),
                             modifiers=modifiers, convention=convention, effects=effects),
                     depth=depth, size=size)

    def labels(self, count):
        if self.marker(_EMPTY):
            return (None,) * count
        labels = []
        for _ in range(count):
            if self.marker(_FIRST):
                labels.append(None)
            else:
                labels.append(self.pop(_Name).text)
        return tuple(reversed(labels))

    def plain_function(self):
        signature = self.pop() if self.top_is(GenericSignature) else None
        params, result, effects, _ = self.function_parts()
        labels = self.labels(len(params))
        name, context = self.pop(_Name), self.context()
        return DeclarationIdentity('Function', context.path, name.text, labels, params,
                                   result.node, signature, effects, name.discriminator)

    def typed_entity(self, kind):
        private = None
        if self.top_is(_Name) and self.stack[-1].discriminator is not None:
            private = self.pop(_Name)
        value = self.pop(_Type)
        node = value.node
        if node.kind != 'function':
            self.fail()
        params, result = node.args[:-1], node.args[-1]
        labels = self.labels(len(params))
        context = self.context()
        return DeclarationIdentity(kind, context.path, 'init', labels, params, result,
                                   value.signature, node.effects or Effects(),
                                   private.discriminator if private else None)

    def accessor(self, subscript=False):
        value = self.pop(_Type)
        if subscript:
            if value.node.kind != 'function':
                self.fail()
            params, result = value.node.args[:-1], value.node.args[-1]
            labels = self.labels(len(params))
            name = _Name('subscript')
        else:
            params, result, labels = (), value.node, ()
            name = self.pop(_Name)
        context = self.context()
        c = self.take()
        if c in 'al':
            c += self.take()
        if c == 'p':
            return _Annotation('nonfunction')
        if c not in _ACCESSORS:
            self.fail()
        return DeclarationIdentity(_ACCESSORS[c], context.path, name.text, labels,
                                   params, result, value.signature,
                                   value.node.effects if subscript else Effects(),
                                   name.discriminator)

    def bound_generic(self):
        # Types / bound-generic-type; argument lists run outermost first.
        lists = []
        while True:
            args = []
            while self.top_is(_Type):
                args.append(self.pop(_Type))
            lists.append(tuple(reversed(args)))
            if self.marker(_EMPTY):
                break
            if not self.marker(_FIRST):
                self.fail()
        nominal = self.pop(_Type)
        if nominal.node.kind != 'nominal' or not nominal.path:
            self.fail()
        if len(lists) > sum(c.kind not in ('module', 'extension') for c in nominal.path):
            self.fail()
        args = tuple(a for group in reversed(lists) for a in group)
        return self.substitute(self.ty('bound_generic', nominal.node.name, args,
                                      path=nominal.path, signature=nominal.signature))

    def special(self):
        # Types / FUNCTION-KIND, METATYPE-REPR, existential-layout, sugar.
        c = self.take()
        if c in _CONVENTIONS:
            return self.function_type(_CONVENTIONS[c])
        if c == 'z':
            code = self.take()
            if code not in 'BC':
                self.fail()
            n = self.number()
            self.budget('max_identifier_length', n)
            if self.pos + n > len(self.text):
                self.fail('truncated')
            self.pos += n
            return self.function_type(_CONVENTIONS[code])
        if c in 'Mmp':
            if c in 'Mm' and self.take() not in 'tTo':
                self.fail()
            return self.ty('metatype' if c == 'M' else 'existential_metatype', args=(self.pop(_Type),))
        if c == 'S':
            code = self.take()
            if code not in 'qaD':
                self.fail('unsupported_production', 'sugared type XS' + code)
            right = self.pop(_Type)
            args = (self.pop(_Type), right) if code == 'D' else (right,)
            return self.ty('bound_generic', {'q': 'Swift.Optional', 'a': 'Swift.Array',
                           'D': 'Swift.Dictionary'}[code], args)
        if c == 'Z':
            self.sequence('pack')
            name, context = self.pop(_Name), self.context()
            return _Context(self.path(context.path + (ContextElement('anonymous', name.text),)))
        if c in 'lc':
            superclass = self.pop(_Type) if c == 'c' else self.ty('nominal', 'Swift.AnyObject')
            protocols = self.sequence('protocol')
            # Preserve the class constraint as a composition member.
            return self.ty('composition', args=(protocols, superclass))
        self.fail('unsupported_production', 'special type X' + c)

    def archetype(self):
        c = self.take()
        if c == 'O':
            # Types / opaque-type-decl-name. This marker is also the operand
            # of an opaque descriptor, which is not a callable declaration.
            return _Annotation('opaque_decl', self.context())
        if c == 'r':
            return self.ty('opaque')
        if c == 'R':
            return self.ty('opaque', str(self.index()))
        if c in 'yzYZxX':
            base = (self.generic_param() if c in 'yY' else
                    self.ty('generic_param', 'τ_0_0') if c in 'zZ' else None)
            return self.substitute(self.associated(base, c in 'YZX'))
        if c == 'a':
            name, base = self.pop(_Name), self.pop(_Type)
            return self.substitute(self.ty('dependent_member', name.text, (base,)))
        if c == 'p':
            count, pattern = self.pop(_Type), self.pop(_Type)
            return self.ty('pack_expansion', args=(pattern, count))
        if c == 'P':
            return self.sequence('pack')
        self.fail('unsupported_production', 'archetype Q' + c)

    def builtin(self):
        # Types / builtin types. Builtin names have no declaration context.
        c = self.take()
        names = {'b': 'BridgeObject', 'B': 'UnsafeValueBuffer', 'c': 'RawUnsafeContinuation',
                 'D': 'DefaultActorStorage', 'd': 'NonDefaultDistributedActorStorage',
                 'e': 'Executor', 'I': 'IntLiteral', 'j': 'Job', 'P': 'PackIndex',
                 'O': 'UnknownObject', 'o': 'NativeObject', 'p': 'RawPointer',
                 't': 'SILToken', 'w': 'Word', 'A': 'ImplicitActor'}
        if c in 'if':
            name = ('Int' if c == 'i' else 'Float') + str(self.index() - 1)
        elif c in names:
            name = names[c]
        else:
            self.fail('unsupported_production', 'builtin B' + c)
        return self.ty('nominal', 'Builtin.' + name)

    def impl_function(self):
        # Types / impl-function-type. Parse the attribute envelope so a global
        # reabstraction suffix can be recognized, but do not admit SIL types:
        # their ownership/yield conventions have no public TypeNode fields.
        if self.peek() in ('s', 'I'):
            self.fail('unsupported_production', 'impl-function substitutions')
        if self.top_is(GenericSignature):
            self.pop()
            self.eat('P')
        self.eat('e')
        self.eat('A')
        self.eat('N')
        if self.peek() and self.peek() in 'dlfr':
            self.take()
        if self.take() not in 'ygxt':
            self.fail()
        if self.peek() and self.peek() in 'BCMOKW':
            self.take()
        elif self.text.startswith(('zB', 'zC'), self.pos):
            self.pos += 2
            n = self.number()
            self.budget('max_identifier_length', n)
            if self.pos + n > len(self.text):
                self.fail('truncated')
            self.pos += n
        if self.peek() and self.peek() in 'AIG':
            self.take()
        self.eat('h')
        self.eat('H')
        self.eat('T')
        count = 0
        while self.peek() and self.peek() in 'iclb nXxygevpm'.replace(' ', ''):
            self.take()
            self.eat('w')
            self.eat('T')
            self.eat('I')
            self.eat('L')
            count += 1
            self.budget('max_parameters', count)
        while self.peek() and self.peek() in 'roduaklgm':
            self.take()
            self.eat('w')
            count += 1
        while self.eat('Y'):
            if self.take() not in 'iclbnXxygevpm':
                self.fail()
            count += 1
        if self.eat('z'):
            if self.take() not in 'roduaklgm':
                self.fail()
            count += 1
        if not self.eat('_'):
            self.fail('truncated' if not self.peek() else 'malformed_symbol')
        for _ in range(count):
            self.pop(_Type)
        return _Annotation('unsupported', 'impl-function-type')

    def run(self):
        # Mangling grammar / global and Declaration Contexts / entity-spec.
        while self.pos < len(self.text):
            start = self.pos
            c = self.take()
            value = None
            if c.isdigit():
                self.pos -= 1
                value = self.identifier()
            elif c == 'A':
                self.substitutions()
            elif c == 'S':
                value = self.standard()
            elif c == 's':
                value = _Context((ContextElement('module', 'Swift'),))
            elif c in 'VCOPa':
                value = self.nominal({'V': 'struct', 'C': 'class', 'O': 'enum',
                                      'P': 'protocol', 'a': 'type_alias'}[c])
            elif c == 'E':
                signature = self.pop() if self.top_is(GenericSignature) else None
                module, extended = self.context(), self.pop(_Type)
                if len(module.path) != 1 or module.path[0].kind != 'module' or not extended.path:
                    self.fail()
                value = _Context(self.path((ContextElement('extension', module.path[0].name),)
                                           + extended.path), signature)
            elif c == 'F':
                value = self.plain_function()
            elif c == 'c':
                value = self.function_type()
            elif c == 'f':
                code = self.take()
                if code in 'Cc':
                    value = self.typed_entity('Allocator' if code == 'C' else 'Constructor')
                elif code in 'dDZ':
                    context = self.context()
                    value = DeclarationIdentity({'d': 'Destructor', 'D': 'Deallocator',
                        'Z': 'IsolatedDeallocator'}[code], context.path, 'deinit')
                elif code in 'Uu':
                    index = self.index()
                    closure_type = self.pop(_Type)
                    if closure_type.node.kind != 'function':
                        self.fail()
                    context = self.context()
                    value = _Context(self.path(context.path +
                                     (ContextElement('local', str(index)),)))
                elif code in 'EeiPFW':
                    # entity-spec: storage/property initialization helpers are
                    # outside the rule-2 callable entities.
                    self.pop()
                    value = _Annotation('nonfunction')
                else:
                    self.fail('unsupported_production', 'function entity f' + code)
            elif c in 'vi':
                value = self.accessor(c == 'i')
            elif c == 'M':
                code = self.take()
                if code == 'a':
                    nominal = self.pop(_Type)
                    if not nominal.path:
                        self.fail()
                    value = DeclarationIdentity('TypeMetadataAccessFunction', nominal.path[:-1],
                                                 nominal.path[-1].name)
                else:
                    self.fail('not_function_entity', 'metadata global')
            elif c in 'NWwD':
                if c == 'W' and self.eat('O'):
                    self.fail('thunk_or_specialization', 'outlined operation', start)
                self.fail('not_function_entity')
            elif c == 'T':
                # Global / thunk and specialization operators. These cannot
                # contribute an admissible identity, even with a valid prefix.
                if self.peek() in ('l', 'L', 'M', 'n', 'N', 'b'):
                    self.fail('not_function_entity', 'associated requirement descriptor', start)
                if self.peek() and self.peek() in 'TcjqoODdEFaAmXxIYQCzZVWSRrygGBtsipPfKkHhveuUJw':
                    self.fail('thunk_or_specialization', offset=start)
                self.fail('malformed_symbol' if self.peek() else 'truncated')
            elif c == 'Z':
                if not self.top_is(DeclarationIdentity):
                    self.fail()
                entity = self.pop(DeclarationIdentity)
                value = _Annotation('static_accessor' if entity.entity in _ACCESSORS.values()
                                    else 'nonfunction')
            elif c == 'G':
                value = self.bound_generic()
            elif c == 't':
                value = self.sequence('tuple')
            elif c == 'p':
                value = self.sequence('protocol')
            elif c == 'm':
                value = self.ty('metatype', args=(self.pop(_Type),))
            elif c == 'X':
                value = self.special()
            elif c == 'Q':
                value = self.archetype()
            elif c == 'q':
                value = self.generic_param()
            elif c == 'x':
                value = self.ty('generic_param', 'τ_0_0')
            elif c in 'ynhz_d':
                if c in 'zhn':
                    value = self.modify({'z': 'inout', 'h': 'shared', 'n': 'owned'}[c])
                else:
                    value = {'y': _EMPTY, '_': _FIRST, 'd': _VARIADIC}[c]
            elif c == 'K':
                value = _Annotation('K')
            elif c == 'Y':
                value = self.annotation()
            elif c == 'R':
                value = self.requirement()
            elif c in 'lr':
                value = self.signature(c == 'r')
            elif c == 'u':
                sig, ty = self.pop(GenericSignature), self.pop(_Type)
                value = replace(ty, signature=sig)
            elif c == 'L':
                if self.eat('L'):
                    discriminator, name = self.pop(_Name), self.pop(_Name)
                    value = replace(name, discriminator=discriminator.text)
                elif self.eat('l'):
                    discriminator = self.pop(_Name)
                    value = _Name('', discriminator.text)
                elif self.peek() and self.peek() in 'abcdefghijABCDEFGHIJ':
                    relation = self.take()
                    value = replace(self.pop(_Name), discriminator='related:' + relation)
                else:
                    discriminator = str(self.index())
                    value = replace(self.pop(_Name), discriminator=discriminator)
            elif c == 'o':
                name = self.pop(_Name)
                # Identifiers / OPERATOR-FIXITY.
                spelling = {'a': '&', 'c': '@', 'd': '/', 'e': '=', 'g': '>',
                            'l': '<', 'm': '*', 'n': '!', 'o': '|', 'p': '+',
                            'q': '?', 'r': '%', 's': '-', 't': '~', 'x': '^', 'z': '.'}
                operator = ''.join(spelling[ch] if ch.isascii() else ch for ch in name.text)
                if self.take() not in 'ipP':
                    self.fail()
                value = _Name(operator, name.discriminator)
            elif c == 'B':
                value = self.builtin()
            elif c == 'I':
                value = self.impl_function()
            else:
                self.fail('trailing_input' if self.completed else 'malformed_symbol', offset=start)
            if value is not None:
                self.stack.append(value)
            if isinstance(value, DeclarationIdentity):
                self.completed = True
            # At most input-length production steps; repeats are separately
            # limited, and no parser operation recurses.
            if self.pos <= start:
                self.fail()
        if len(self.stack) == 1 and isinstance(self.stack[0], DeclarationIdentity):
            identity = self.stack[0]
            self.validate(identity)
            return identity
        if len(self.stack) == 1 and isinstance(self.stack[0], _Type) and self.stack[0].path:
            self.fail('not_function_entity')
        if len(self.stack) == 1 and isinstance(self.stack[0], _Annotation) and self.stack[0].kind == 'nonfunction':
            self.fail('not_function_entity')
        if len(self.stack) == 1 and isinstance(self.stack[0], _Annotation) and self.stack[0].kind == 'static_accessor':
            self.fail('accessor')
        if len(self.stack) == 1 and isinstance(self.stack[0], _Context):
            self.fail('not_function_entity')
        if any(isinstance(v, _Annotation) and v.kind == 'unsupported' for v in self.stack):
            self.fail('unsupported_production', 'impl-function-type')
        self.fail('truncated' if not self.completed else 'trailing_input')

    def validate(self, identity):
        # The API counts retained TypeNode occurrences, not temporary stack
        # nodes (outer function/parameter tuple and nominal contexts disappear).
        pending, count, too_deep = [(identity, 0)], 0, False
        while pending:
            value, depth = pending.pop()
            too_deep |= depth > 27
            if isinstance(value, TypeNode):
                count += 1
                self.budget('max_nodes', count)
            if hasattr(type(value), '__dataclass_fields__'):
                pending.extend((getattr(value, f.name), depth + 1) for f in fields(value))
            elif isinstance(value, tuple):
                pending.extend((v, depth + 1) for v in value)
        if too_deep:
            self.fail('limit_exceeded', 'identity_depth')


def parse_declaration(symbol, limits=GrammarLimits()):
    """Return a deterministic declaration or an explicit, bounded decline."""
    text = ''
    parser = None
    try:
        # Exact built-in text types prevent hostile user-defined protocol hooks.
        if type(symbol) is bytes:
            text = symbol.decode('ascii')
        elif type(symbol) is str:
            text = symbol
        else:
            return DeclarationResult('')
        if not text or not text.isascii():
            return DeclarationResult(text)
        if type(limits) is not GrammarLimits or any(type(getattr(limits, f.name)) is not int
                or getattr(limits, f.name) < 0 for f in fields(GrammarLimits)):
            return DeclarationResult(text, detail='invalid limits')
        if len(text) > limits.max_symbol_length:
            return DeclarationResult(text, reason='limit_exceeded', detail='max_symbol_length')
        start = 1 if text.startswith('_') else 0
        if not text.startswith('$s', start):
            return DeclarationResult(text)
        parser = _Parser(text, limits, start + 2)
        identity = parser.run()
        effects = identity.effects
        if identity.entity in _ACCESSORS.values():
            decision, reason = 'undecided', 'accessor'
        elif effects.typed_throws is not None and effects.typed_throws.name == 'Swift.Never':
            decision, reason = 'undecided', 'typed_throws'
        elif effects.throws or effects.typed_throws is not None:
            decision, reason = 'throwing', ''
        elif effects.is_async:
            decision, reason = 'async', ''
        else:
            decision, reason = 'non_throwing', ''
        return DeclarationResult(text, identity, decision, reason, '', len(text) if reason else None)
    except _Decline as error:
        return DeclarationResult(text, reason=error.reason, detail=error.detail[:160],
                                 offset=max(0, min(len(text), error.offset or 0)))
    except Exception:
        return DeclarationResult(text, reason='malformed_symbol' if parser else 'invalid_input',
                                 offset=min(len(text), parser.pos) if parser else 0)
