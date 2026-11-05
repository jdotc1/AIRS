"""Bounded Swift declaration *syntax*, deliberately separate from ABI admission.

No external demangler, image access, register inference or call-target claim.
Unsupported productions retain an explicit reason instead of partial identities.
"""
from dataclasses import dataclass, replace
from enum import Enum
import re


class CallableKind(str, Enum):
    FREE_FUNCTION = 'free_function'
    STRUCT_INSTANCE_METHOD = 'struct_instance_method'
    ENUM_INSTANCE_METHOD = 'enum_instance_method'
    CLASS_INSTANCE_METHOD = 'class_instance_method'
    STATIC_METHOD = 'static_method'
    GENERIC_SPECIALIZATION = 'generic_specialization'


class UnsupportedReason(str, Enum):
    INVALID_INPUT = 'invalid_input'
    RESOURCE_LIMIT = 'resource_limit'
    INVALID_GRAMMAR = 'invalid_grammar'
    UNKNOWN_SUBSTITUTION = 'unknown_substitution'
    UNSUPPORTED_PRODUCTION = 'unsupported_production'
    UNCONSUMED_SUFFIX = 'unconsumed_suffix'
    UNICODE_IDENTIFIER = 'unicode_identifier'
    WORD_SUBSTITUTION = 'word_substitution'
    ASYNC_CONTEXT = 'async_context'
    TYPED_THROWS = 'typed_throws'
    THUNK_OR_SPECIALIZATION = 'thunk_or_specialization'
    CLOSURE_TYPE = 'closure_type'
    GENERIC_REQUIREMENTS = 'generic_requirements'
    PROTOCOL_CONTEXT = 'protocol_context'


@dataclass(frozen=True, slots=True)
class ParseLimits:
    max_symbol_length: int = 4096
    max_identifier_length: int = 256
    max_context_depth: int = 16
    max_nodes: int = 256
    max_substitutions: int = 128
    max_parameters: int = 64
    max_type_depth: int = 16
    max_generic_parameters: int = 32


@dataclass(frozen=True, slots=True)
class SwiftContext:
    name: str
    kind: str


@dataclass(frozen=True, slots=True)
class SwiftType:
    name: str
    arguments: tuple['SwiftType', ...] = ()
    inout: bool = False
    label: str | None = None
    generic_depth: int | None = None
    generic_index: int | None = None
    nominal_kind: str | None = None


@dataclass(frozen=True, slots=True)
class SwiftGenericRequirement:
    protocol: str
    parameter_depth: int
    parameter_index: int


class SpecializationKind(str, Enum):
    GENERIC_REABSTRACTED = 'generic_reabstracted'
    GENERIC_NOT_REABSTRACTED = 'generic_not_reabstracted'
    GENERIC_RESILIENT = 'generic_resilient'


@dataclass(frozen=True, slots=True)
class SwiftGenericBinding:
    parameter_depth: int
    parameter_index: int
    replacement: SwiftType


@dataclass(frozen=True, slots=True)
class SwiftSpecialization:
    template_symbol: str
    kind: SpecializationKind
    pass_id: int
    serialized: bool
    async_removed: bool
    representation_changed: bool
    dropped_argument_ordinals: tuple[int, ...]
    bindings: tuple[SwiftGenericBinding, ...]
    substituted_parameter_types: tuple[SwiftType, ...]
    substituted_result_type: SwiftType


@dataclass(frozen=True, slots=True)
class SwiftCallableIdentity:
    symbol: str
    module: str
    context: tuple[SwiftContext, ...]
    callable_kind: CallableKind
    function_name: str
    parameter_labels: tuple[str | None, ...]
    parameter_types: tuple[SwiftType, ...]
    result_type: SwiftType
    throws: bool
    generic_parameter_counts: tuple[int, ...] = ()
    generic_requirements: tuple[SwiftGenericRequirement, ...] = ()
    original_callable_kind: CallableKind | None = None
    specialization: SwiftSpecialization | None = None
    syntax_model: str = 'swift-broad-declaration-syntax-v1'


@dataclass(frozen=True, slots=True)
class BroadDeclarationResult:
    identity: SwiftCallableIdentity | None
    unsupported_reason: UnsupportedReason | None = None
    detail: str = ''
    offset: int = 0

    @property
    def supported(self) -> bool:
        return self.identity is not None and self.unsupported_reason is None


class _Decline(Exception):
    def __init__(self, reason, detail):
        self.reason, self.detail = reason, detail


_EMPTY = object()
_FIRST = object()
_BUILTINS = {'i': 'Swift.Int', 'u': 'Swift.UInt', 'b': 'Swift.Bool',
             'f': 'Swift.Float', 'd': 'Swift.Double', 'S': 'Swift.String'}
_NOMINAL = {'V': 'struct', 'O': 'enum', 'C': 'class'}


class _Parser:
    def __init__(self, symbol, limits):
        self.original, self.limits = symbol, limits
        self.text = symbol[1:] if symbol.startswith('_$s') else symbol
        self.pos = 2
        self.substitutions = []
        self.nodes = 0
        self.depths = {}
        self.words = []

    def decline(self, reason, detail):
        raise _Decline(reason, detail)

    def limit(self, condition, detail):
        if condition:
            self.decline(UnsupportedReason.RESOURCE_LIMIT, detail)

    def add_substitution(self, value):
        self.limit(len(self.substitutions) >= self.limits.max_substitutions, 'substitution table limit')
        self.substitutions.append(value)

    def literal_identifier_part(self, *, fragment=False):
        match = re.match(r'[1-9][0-9]*', self.text[self.pos:])
        if not match:
            self.decline(UnsupportedReason.INVALID_GRAMMAR, 'expected identifier literal length')
        self.limit(len(match[0]) > 6, 'identifier length digit limit')
        size = int(match[0])
        self.limit(size > self.limits.max_identifier_length, 'identifier length limit')
        self.pos += len(match[0])
        value = self.text[self.pos:self.pos + size]
        pattern = r'[A-Za-z_0-9$]+' if fragment else r'[A-Za-z_][A-Za-z_0-9$]*'
        if len(value) != size or not re.fullmatch(pattern, value):
            self.decline(UnsupportedReason.INVALID_GRAMMAR, 'invalid or truncated identifier literal')
        self.pos += size
        # The 26-entry word dictionary follows the literal fragments, not the
        # expanded references (which must never shift subsequent word indices).
        begin = None
        for i in range(len(value) + 1):
            char = value[i] if i < len(value) else ''
            if begin is not None and (not char or char == '_' or (char.isupper() and not value[i - 1].isupper())):
                word = value[begin:i]
                if len(word) >= 2 and len(self.words) < 26:
                    self.words.append(word)
                begin = None
            if begin is None and char and not char.isdigit() and char != '_':
                begin = i
        return value

    def identifier(self):
        if self.text[self.pos:].startswith('00'):
            self.decline(UnsupportedReason.UNICODE_IDENTIFIER, 'Punycode identifier encoding is not implemented')
        if self.text[self.pos:self.pos + 1] != '0':
            value = self.literal_identifier_part()
        else:
            self.pos += 1
            parts, more_words = [], True
            while self.pos < len(self.text):
                while more_words and self.text[self.pos:self.pos + 1].isalpha():
                    char = self.text[self.pos]
                    index = ord(char.lower()) - ord('a')
                    if index >= len(self.words):
                        self.decline(UnsupportedReason.UNKNOWN_SUBSTITUTION, 'word substitution index is absent')
                    parts.append(self.words[index]); self.pos += 1
                    if char.isupper():
                        more_words = False
                if self.text[self.pos:self.pos + 1] == '0':
                    self.pos += 1
                    break
                parts.append(self.literal_identifier_part(fragment=True))
                self.limit(sum(map(len, parts)) > self.limits.max_identifier_length, 'expanded identifier length limit')
                if not more_words:
                    break
            else:
                self.decline(UnsupportedReason.INVALID_GRAMMAR, 'unterminated word-substituted identifier')
            value = ''.join(parts)
            self.limit(len(value) > self.limits.max_identifier_length, 'expanded identifier length limit')
            if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9$]*', value):
                self.decline(UnsupportedReason.INVALID_GRAMMAR, 'invalid expanded identifier')
        self.add_substitution(value)
        return value

    def pop_type(self, stack):
        if not stack:
            self.decline(UnsupportedReason.INVALID_GRAMMAR, 'missing type operand')
        value = stack.pop()
        if value is _EMPTY:
            return SwiftType('Swift.Void')
        if not isinstance(value, SwiftType):
            self.decline(UnsupportedReason.INVALID_GRAMMAR, 'non-type operand')
        return value

    def type_node(self, name, arguments=(), **kwargs):
        self.nodes += 1
        self.limit(self.nodes > self.limits.max_nodes, 'AST node limit')
        depth = 1 + max((self.depths.get(id(a), 1) for a in arguments), default=0)
        self.limit(depth > self.limits.max_type_depth, 'type depth limit')
        node = SwiftType(name, arguments, **kwargs)
        self.depths[id(node)] = depth
        return node

    def index(self):
        if self.text[self.pos:self.pos + 1] == '_':
            self.pos += 1
            return 0
        match = re.match(r'[1-9][0-9]{0,5}_', self.text[self.pos:])
        if not match:
            self.decline(UnsupportedReason.INVALID_GRAMMAR, 'invalid index')
        self.pos += len(match[0])
        return int(match[0][:-1]) + 1

    def specialization(self, template):
        """Consume supported concrete replacement-list and generic attributes.

        DroppedArgument ordinals retain Swift's raw demangler numbering. They
        are not source-parameter indices and never remove formal AST entries.
        """
        start = self.pos
        tail = self.text[self.pos:]
        if tail.startswith('T'):
            detail = ('function-signature specialization may change argument/return ABI'
                      if tail.startswith('Tf') else 'unsupported thunk or specialization production')
            self.decline(UnsupportedReason.THUNK_OR_SPECIALIZATION, detail)
        if not tail.startswith(('S', 's')):
            self.decline(UnsupportedReason.UNCONSUMED_SUFFIX, 'unconsumed declaration suffix')
        replacements = []
        marker_seen = False
        while self.pos < len(self.text) and self.text[self.pos] != 'T':
            tail = self.text[self.pos:]
            if tail.startswith('_'):
                if marker_seen or len(replacements) != 1:
                    self.decline(UnsupportedReason.INVALID_GRAMMAR, 'replacement type-list marker requires exactly one preceding type')
                marker_seen = True; self.pos += 1
                continue
            if tail.startswith('Sg'):
                if not replacements or (marker_seen and len(replacements) == 1):
                    self.decline(UnsupportedReason.INVALID_GRAMMAR, 'optional replacement lacks a type before its list delimiter')
                self.pos += 2
                replacements[-1] = self.type_node('Optional', (replacements[-1],))
                continue
            if len(tail) >= 2 and tail[0] == 'S' and tail[1] in _BUILTINS:
                replacements.append(self.type_node(_BUILTINS[tail[1]], nominal_kind='struct'))
                self.pos += 2
            elif tail.startswith('s'):
                self.pos += 1
                name = self.identifier()
                if name not in {'Int8', 'Int16', 'Int32', 'Int64', 'UInt8', 'UInt16', 'UInt32', 'UInt64'} or self.text[self.pos:self.pos + 1] != 'V':
                    self.decline(UnsupportedReason.THUNK_OR_SPECIALIZATION, 'unsupported concrete replacement type')
                self.pos += 1
                replacements.append(self.type_node('Swift.' + name, nominal_kind='struct'))
            else:
                self.decline(UnsupportedReason.THUNK_OR_SPECIALIZATION, 'unsupported specialization replacement grammar')
            self.limit(len(replacements) > self.limits.max_generic_parameters, 'specialization replacement count limit')
        if not marker_seen or not replacements or self.text[self.pos:self.pos + 1] != 'T':
            self.decline(UnsupportedReason.INVALID_GRAMMAR, 'incomplete generic specialization type list')
        self.pos += 1
        dropped = []
        while self.text[self.pos:self.pos + 1] == 't':
            self.pos += 1
            number = re.match(r'[1-9][0-9]*', self.text[self.pos:])
            if number:
                self.limit(len(number[0]) > 6, 'dropped argument ordinal digit limit')
                ordinal = int(number[0]) + 1
                self.pos += len(number[0])
            else:
                ordinal = 0
            self.limit(ordinal > self.limits.max_parameters or len(dropped) >= self.limits.max_parameters, 'dropped argument limit')
            if ordinal in dropped:
                self.decline(UnsupportedReason.INVALID_GRAMMAR, 'duplicate dropped argument ordinal')
            dropped.append(ordinal)
        kind_code = self.text[self.pos:self.pos + 1]
        kinds = {'g': SpecializationKind.GENERIC_REABSTRACTED,
                 'G': SpecializationKind.GENERIC_NOT_REABSTRACTED,
                 'B': SpecializationKind.GENERIC_RESILIENT}
        if kind_code not in kinds:
            self.decline(UnsupportedReason.THUNK_OR_SPECIALIZATION, 'unsupported generic specialization kind')
        self.pos += 1
        attributes = []
        for flag in ('q', 'a', 'r'):
            present = self.text[self.pos:self.pos + 1] == flag
            attributes.append(present)
            if present:
                self.pos += 1
        pass_char = self.text[self.pos:self.pos + 1]
        if len(pass_char) != 1 or pass_char not in '0123456789':
            self.decline(UnsupportedReason.INVALID_GRAMMAR, 'specialization requires a single known pass digit after ordered flags')
        self.pos += 1
        if self.pos != len(self.text):
            self.decline(UnsupportedReason.UNCONSUMED_SUFFIX, 'unconsumed specialization suffix')
        # Only one-level concrete bindings have a proven correspondence in this
        # subset. Multiple parent environments/partial substitutions decline.
        if len(template.generic_parameter_counts) != 1 or template.generic_parameter_counts[0] != len(replacements):
            self.decline(UnsupportedReason.GENERIC_REQUIREMENTS, 'concrete replacement count does not match one supported generic environment')
        bindings = tuple(SwiftGenericBinding(0, index, node) for index, node in enumerate(replacements))
        memo = {}
        def substitute(root):
            pending = [(root, False)]
            while pending:
                node, ready = pending.pop()
                if id(node) in memo:
                    continue
                if node.generic_depth is not None:
                    replacement = replacements[node.generic_index]
                    if node.inout or node.label is not None:
                        original_depth = self.depths.get(id(replacement), 1)
                        replacement = replace(replacement, inout=node.inout, label=node.label)
                        self.depths[id(replacement)] = original_depth
                    memo[id(node)] = replacement
                elif ready:
                    args = tuple(memo[id(arg)] for arg in node.arguments)
                    memo[id(node)] = self.type_node(node.name, args, inout=node.inout,
                                                   label=node.label, nominal_kind=node.nominal_kind)
                else:
                    pending.append((node, True))
                    pending.extend((arg, False) for arg in node.arguments)
            return memo[id(root)]
        parameters = tuple(substitute(node) for node in template.parameter_types)
        result = substitute(template.result_type)
        offset = int(self.original.startswith('_$s'))
        specialization = SwiftSpecialization(self.original[:start + offset], kinds[kind_code], int(pass_char),
                                             *attributes, tuple(dropped), bindings, parameters, result)
        return replace(template, callable_kind=CallableKind.GENERIC_SPECIALIZATION,
                       original_callable_kind=template.callable_kind, specialization=specialization)

    def parse(self):
        module = self.identifier()
        context = []
        while True:
            name = self.identifier()
            code = self.text[self.pos:self.pos + 1]
            if code == 'P':
                self.decline(UnsupportedReason.PROTOCOL_CONTEXT, 'protocol declaration/requirement needs separate qualification')
            if code not in _NOMINAL:
                function = name
                break
            self.pos += 1
            context.append(SwiftContext(name, _NOMINAL[code]))
            self.limit(len(context) > self.limits.max_context_depth, 'context nesting limit')
            self.add_substitution(self.type_node('.'.join([module, *(c.name for c in context)]), nominal_kind=_NOMINAL[code]))
        stack = []
        throwing = False
        generic_counts = ()
        requirements = []
        while self.pos < len(self.text):
            self.limit(len(stack) > self.limits.max_nodes, 'operand stack limit')
            tail = self.text[self.pos:]
            code = tail[0]
            if (throwing or generic_counts) and code not in ('F', 'l', 'r'):
                # Once annotations start, no further type/label operands belong
                # to this declaration signature.
                if code not in ('T', 'Y', 'c', 'X', 'R') and not tail.startswith('Sz'):
                    self.decline(UnsupportedReason.INVALID_GRAMMAR, 'operand after signature annotation')
            if code in ('K', 'l', 'r'):
                if len(stack) < 2 or not all(isinstance(x, SwiftType) or x is _EMPTY for x in stack[-2:]):
                    self.decline(UnsupportedReason.INVALID_GRAMMAR, 'signature annotation lacks result/parameters')
            if tail.startswith(('Ya', 'Yb', 'Yc', 'YA', 'YC', 'YT')):
                self.decline(UnsupportedReason.ASYNC_CONTEXT, 'async/isolation/sendability annotation requires separate qualification')
            if tail.startswith('YK'):
                self.decline(UnsupportedReason.TYPED_THROWS, 'typed throws annotation requires separate qualification')
            if tail.startswith(('XE', 'XK')) or code == 'c':
                self.decline(UnsupportedReason.CLOSURE_TYPE, 'function/closure parameter type requires separate qualification; rethrows cannot be inferred')
            if code == 'T':
                self.decline(UnsupportedReason.THUNK_OR_SPECIALIZATION, 'thunk or specialization requires separate qualification')
            if code.isdigit():
                stack.append(self.identifier())
                continue
            self.pos += 1
            if code == 'y':
                stack.append(_EMPTY)
            elif code == '_':
                stack.append(_FIRST)
            elif code == 'K':
                if throwing:
                    self.decline(UnsupportedReason.INVALID_GRAMMAR, 'duplicate throws annotation')
                throwing = True
            elif code == 'S':
                if self.text[self.pos:self.pos + 1] == 'g':
                    self.pos += 1
                    node = self.type_node('Optional', (self.pop_type(stack),))
                    self.add_substitution(node); stack.append(node)
                    continue
                count_match = re.match(r'[1-9][0-9]{0,5}', self.text[self.pos:])
                count = 1
                if count_match:
                    count = int(count_match[0]); self.pos += len(count_match[0])
                self.limit(count > self.limits.max_nodes, 'repeat substitution limit')
                kind = self.text[self.pos:self.pos + 1]
                if kind == 'z' and count == 1:
                    self.pos += 1
                    stack.append(self.type_node('Protocol:Swift.BinaryInteger'))
                    continue
                if kind == 'a' and count == 1:
                    self.pos += 1
                    stack.append(self.type_node('Swift.Array', nominal_kind='struct'))
                    continue
                if kind not in _BUILTINS:
                    self.decline(UnsupportedReason.UNKNOWN_SUBSTITUTION, 'unknown standard type substitution')
                self.pos += 1
                stack.extend(self.type_node(_BUILTINS[kind], nominal_kind='struct') for _ in range(count))
            elif code in _NOMINAL or code == 'P':
                if code == 'P':
                    self.decline(UnsupportedReason.PROTOCOL_CONTEXT, 'protocol type needs separate qualification')
                if len(stack) < 2 or not isinstance(stack[-1], str):
                    self.decline(UnsupportedReason.INVALID_GRAMMAR, 'nominal type lacks name/context')
                name = stack.pop(); owner = stack.pop()
                if isinstance(owner, SwiftType):
                    if owner.nominal_kind not in ('struct', 'enum', 'class') or owner.arguments or owner.inout:
                        self.decline(UnsupportedReason.INVALID_GRAMMAR, 'unsupported non-nominal or bound nominal context')
                    owner = owner.name
                if not isinstance(owner, str):
                    self.decline(UnsupportedReason.INVALID_GRAMMAR, 'invalid nominal context')
                node = self.type_node(owner + '.' + name, nominal_kind=_NOMINAL[code])
                self.add_substitution(node); stack.append(node)
            elif code == 's':
                name = self.identifier()
                if self.text[self.pos:self.pos + 1] == 'R':
                    self.decline(UnsupportedReason.GENERIC_REQUIREMENTS, 'generic protocol requirement needs separate qualification')
                if self.text[self.pos:self.pos + 1] != 'V' or name not in {'Int8', 'Int16', 'Int32', 'Int64', 'UInt8', 'UInt16', 'UInt32', 'UInt64'}:
                    self.decline(UnsupportedReason.UNSUPPORTED_PRODUCTION, 'unsupported Swift nominal type')
                self.pos += 1
                node = self.type_node('Swift.' + name, nominal_kind='struct')
                self.add_substitution(node); stack.append(node)
            elif code == 'A':
                # Bounded single/repeated substitutions; multi-substitution runs
                # decline until the exact insertion rules have independent evidence.
                match = re.match(r'([1-9][0-9]{0,5})?([A-Z])', self.text[self.pos:])
                if not match:
                    self.decline(UnsupportedReason.UNKNOWN_SUBSTITUTION, 'unsupported substitution encoding')
                self.pos += len(match[0])
                count, index = int(match[1] or '1'), ord(match[2]) - ord('A')
                self.limit(count > self.limits.max_nodes, 'repeat substitution limit')
                if index >= len(self.substitutions):
                    self.decline(UnsupportedReason.UNKNOWN_SUBSTITUTION, 'substitution index is absent')
                stack.extend([self.substitutions[index]] * count)
            elif code == 'G':
                arguments = []
                while stack and stack[-1] is not _EMPTY:
                    arguments.append(self.pop_type(stack))
                if not stack:
                    self.decline(UnsupportedReason.INVALID_GRAMMAR, 'generic arguments lack start marker')
                stack.pop(); nominal = self.pop_type(stack)
                if nominal.name != 'Swift.Array' or len(arguments) != 1:
                    self.decline(UnsupportedReason.UNSUPPORTED_PRODUCTION, 'unsupported bound generic shape')
                node = self.type_node(nominal.name, tuple(reversed(arguments)))
                self.add_substitution(node); stack.append(node)
            elif code == 'x' or code == 'q':
                depth, index = 0, 0
                if code == 'q':
                    if self.text[self.pos:self.pos + 1] == 'd':
                        self.pos += 1; depth = self.index() + 1; index = self.index()
                    elif self.text[self.pos:self.pos + 1] == 'z':
                        self.pos += 1
                    else:
                        index = self.index() + 1
                self.limit(depth > self.limits.max_context_depth or index >= self.limits.max_generic_parameters, 'generic parameter index limit')
                stack.append(self.type_node('GenericParameter', generic_depth=depth, generic_index=index))
            elif code == 'z':
                original = self.pop_type(stack)
                node = replace(original, inout=True)
                self.depths[id(node)] = self.depths.get(id(original), 1)
                stack.append(node)
            elif code == 't':
                elements = []
                while stack and stack[-1] is not _FIRST:
                    elements.append(self.pop_type(stack))
                if not stack:
                    self.decline(UnsupportedReason.INVALID_GRAMMAR, 'tuple lacks first-element separator')
                stack.pop(); elements.append(self.pop_type(stack)); elements.reverse()
                self.limit(len(elements) > self.limits.max_parameters, 'tuple element limit')
                stack.append(self.type_node('Tuple', tuple(elements)))
            elif code == 'l':
                if generic_counts:
                    self.decline(UnsupportedReason.INVALID_GRAMMAR, 'duplicate generic signature')
                generic_counts = (1,)
            elif code == 'r':
                if generic_counts:
                    self.decline(UnsupportedReason.INVALID_GRAMMAR, 'duplicate generic signature')
                counts = []
                while self.pos < len(self.text) and self.text[self.pos] != 'l':
                    if self.text[self.pos] == 'z':
                        self.pos += 1; counts.append(0)
                    else:
                        counts.append(self.index() + 1)
                    self.limit(sum(counts) > self.limits.max_generic_parameters or len(counts) > self.limits.max_context_depth, 'generic signature limit')
                if self.pos >= len(self.text):
                    self.decline(UnsupportedReason.INVALID_GRAMMAR, 'unterminated generic signature')
                self.pos += 1; generic_counts = tuple(counts) or (1,)
            elif code == 'R':
                protocol = self.pop_type(stack)
                if protocol.name != 'Protocol:Swift.BinaryInteger':
                    self.decline(UnsupportedReason.GENERIC_REQUIREMENTS, 'unsupported generic requirement')
                if self.text[self.pos:self.pos + 1] != 'z':
                    self.decline(UnsupportedReason.GENERIC_REQUIREMENTS, 'unsupported generic requirement parameter index')
                self.pos += 1
                requirements.append(SwiftGenericRequirement('Swift.BinaryInteger', 0, 0))
            elif code == 'F':
                params = self.pop_type(stack); result = self.pop_type(stack)
                parameters = () if params.name == 'Swift.Void' else params.arguments if params.name == 'Tuple' else (params,)
                self.limit(len(parameters) > self.limits.max_parameters, 'parameter count limit')
                if stack == [_EMPTY]:
                    labels = (None,) * len(parameters)
                elif not stack and not parameters:
                    labels = ()
                elif len(stack) == len(parameters) and all(isinstance(x, str) or x is _FIRST for x in stack):
                    labels = tuple(None if x is _FIRST else x for x in stack)
                else:
                    self.decline(UnsupportedReason.INVALID_GRAMMAR, 'parameter label/type arity mismatch')
                if requirements and not generic_counts:
                    self.decline(UnsupportedReason.GENERIC_REQUIREMENTS, 'requirement lacks generic signature')
                for requirement in requirements:
                    depth, index = requirement.parameter_depth, requirement.parameter_index
                    if depth >= len(generic_counts) or index >= generic_counts[depth]:
                        self.decline(UnsupportedReason.GENERIC_REQUIREMENTS, 'generic requirement references an unbound parameter')
                pending, visited = [result, *parameters], set()
                while pending:
                    node = pending.pop()
                    if id(node) in visited:
                        continue
                    visited.add(id(node))
                    if node.generic_depth is not None:
                        if node.generic_depth >= len(generic_counts) or node.generic_index >= generic_counts[node.generic_depth]:
                            self.decline(UnsupportedReason.GENERIC_REQUIREMENTS, 'generic parameter lacks a supported binding signature (including generic parent contexts)')
                    pending.extend(node.arguments)
                static = self.text[self.pos:self.pos + 1] == 'Z'
                if static:
                    self.pos += 1
                    if not context:
                        self.decline(UnsupportedReason.INVALID_GRAMMAR, 'static function lacks nominal context')
                kind = CallableKind.STATIC_METHOD if static else CallableKind(context[-1].kind + '_instance_method') if context else CallableKind.FREE_FUNCTION
                identity = SwiftCallableIdentity(self.original, module, tuple(context), kind, function, labels, tuple(parameters), result, throwing, generic_counts, tuple(requirements))
                if self.pos != len(self.text):
                    return self.specialization(identity)
                return identity
            else:
                self.decline(UnsupportedReason.UNSUPPORTED_PRODUCTION, 'unsupported grammar operator: ' + code)
        self.decline(UnsupportedReason.INVALID_GRAMMAR, 'missing function declaration operator')


def parse_broad_declaration(symbol: str, *, limits: ParseLimits = ParseLimits()) -> BroadDeclarationResult:
    """Parse a fully consumed bounded subset, or return a typed refusal.

    Success identifies source-level syntax only. ABI support, synchronous error
    register location, target identity and emitted lowering need separate evidence.
    """
    if not isinstance(symbol, str) or not symbol.isascii() or any(ord(c) < 32 for c in symbol):
        return BroadDeclarationResult(None, UnsupportedReason.INVALID_INPUT, 'expected an ASCII external symbol without symbolic references')
    if not isinstance(limits, ParseLimits) or any(not isinstance(getattr(limits, f), int) or getattr(limits, f) < 1 for f in limits.__dataclass_fields__):
        return BroadDeclarationResult(None, UnsupportedReason.INVALID_INPUT, 'limits must be positive integers')
    if len(symbol) > limits.max_symbol_length:
        return BroadDeclarationResult(None, UnsupportedReason.RESOURCE_LIMIT, 'symbol length limit')
    if not (symbol.startswith('$s') or symbol.startswith('_$s')):
        return BroadDeclarationResult(None, UnsupportedReason.INVALID_INPUT, 'expected stable Swift external symbol prefix')
    parser = _Parser(symbol, limits)
    try:
        return BroadDeclarationResult(parser.parse())
    except _Decline as error:
        return BroadDeclarationResult(None, error.reason, error.detail, parser.pos)
