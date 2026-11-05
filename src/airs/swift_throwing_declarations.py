"""Exact bounded declaration syntax; ABI admission is a separate byte check."""
from dataclasses import dataclass
import re

DECLARATION_MODEL = 'swift-throwing-declarations-v1'
METHOD_MODEL = 'swift-sync-error-edges-v38'
METHOD_RETURN_CHOICE_MODEL = 'swift-return-choice-v46'

@dataclass(frozen=True, slots=True)
class ThrowingDeclaration:
    symbol: str
    module: str
    callable_kind: str
    type_name: str | None
    function_name: str
    parameter_types: tuple[str, ...]
    result_type: str
    error_register: str = 'x21'
    convention: str = 'swift_sync_untyped_throws'
    evidence_source: str = 'exact_external_symbol_grammar'

    def record(self):
        value = dict(module=self.module, name=self.function_name,
                     parameters=list(self.parameter_types), result=self.result_type,
                     convention=self.convention, error_register=self.error_register,
                     source=self.evidence_source)
        if self.callable_kind == 'struct_instance_method':
            value.update(callable_kind=self.callable_kind, type_name=self.type_name,
                         declaration_model_version=DECLARATION_MODEL)
        return value

def parse_throwing_declaration(symbol: str, *, allow_methods: bool = False) -> ThrowingDeclaration | None:
    if not isinstance(symbol, str):
        return None
    name = symbol[1:] if symbol.startswith('_$s') else symbol
    if not name.startswith('$s') or len(name) > 512:
        return None
    cursor = 2
    def identifier():
        nonlocal cursor
        match = re.match(r'[1-9][0-9]{0,2}', name[cursor:])
        if match is None:
            return None
        size = int(match.group()); cursor += len(match.group())
        if size > 128:
            return None
        value = name[cursor:cursor+size]; cursor += size
        return value if len(value) == size and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', value) else None
    module, second = identifier(), identifier()
    if module is None or second is None:
        return None
    kind, owner, function = 'free_function', None, second
    if name[cursor:cursor+1] == 'V':
        if not allow_methods:
            return None
        cursor += 1
        function = identifier()
        if function is None:
            return None
        kind, owner = 'struct_instance_method', second
    signatures = {'yS2iKF': (('Swift.Int',), 'Swift.Int'),
                  'yySiKF': (('Swift.Int',), 'Swift.Void'),
                  'SiyKF': ((), 'Swift.Int'), 'yyKF': ((), 'Swift.Void')}
    signature = signatures.get(name[cursor:])
    if signature is None or (owner is not None and name[cursor:] == 'yyKF'):
        return None
    return ThrowingDeclaration(symbol, module, kind, owner, function, *signature)
