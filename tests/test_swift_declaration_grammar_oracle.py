"""Text-only differential gates against the toolchain's demangler tree."""
import collections
import json
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
FUNCTION_TYPES = {
    'FunctionType', 'NoEscapeFunctionType', 'ThinFunctionType',
    'UncurriedFunctionType', 'AutoClosureType', 'EscapingAutoClosureType',
    'ObjCBlock', 'EscapingObjCBlock', 'CFunctionPointer',
}
CONTEXT_KINDS = {
    'Module': 'module', 'Structure': 'struct', 'Enum': 'enum',
    'Class': 'class', 'Protocol': 'protocol', 'TypeAlias': 'type_alias',
}
EFFECTS = {'ThrowsAnnotation', 'TypedThrowsAnnotation', 'AsyncAnnotation'}
NAME_KINDS = {'Identifier', 'PrefixOperator', 'PostfixOperator', 'InfixOperator',
              'LocalDeclName', 'PrivateDeclName', 'RelatedEntityDeclName'}


class Node:
    def __init__(self, kind, text=None, index=None):
        self.kind, self.text, self.index = kind, text, index
        self.children = []


def child(node, kind):
    found = [n for n in node.children if n.kind == kind]
    if len(found) != 1:
        raise ValueError(f'{node.kind}: expected one {kind}, found {len(found)}')
    return found[0]


def parse_tree(text):
    root, stack = None, []
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r'( *)kind=([A-Za-z0-9_]+)(.*)', line)
        if match is None:
            raise ValueError('unrecognized demangler tree line: ' + line[:200])
        indent, kind, attributes = match.groups()
        level = len(indent) // 2
        if len(indent) % 2 or level > len(stack):
            raise ValueError('invalid tree indentation')
        text_match = re.search(r', text=(".*")$', attributes)
        index_match = re.search(r', index=(\d+)', attributes)
        node = Node(kind, json.loads(text_match[1]) if text_match else None,
                    int(index_match[1]) if index_match else None)
        if level == 0:
            if root is not None:
                raise ValueError('multiple tree roots')
            root = node
        else:
            stack[level - 1].children.append(node)
        stack[level:] = [node]
    if root is None or root.kind != 'Global':
        raise ValueError('no Global tree')
    return root


def decl_name(node):
    if node.kind in {'Identifier', 'PrefixOperator', 'PostfixOperator', 'InfixOperator'}:
        if node.text is None:
            raise ValueError('missing declaration name')
        return node.text
    if node.kind == 'PrivateDeclName':
        # The discriminator is the first Identifier, the name the last.
        return decl_name(node.children[-1])
    if node.kind in {'LocalDeclName', 'RelatedEntityDeclName'}:
        names = [n for n in node.children if n.kind in NAME_KINDS]
        if len(names) == 1:
            return decl_name(names[0])
    raise ValueError('unsupported declaration name: ' + node.kind)


def entity_name(node):
    names = [n for n in node.children if n.kind in NAME_KINDS]
    if names:
        if len(names) != 1:
            raise ValueError('ambiguous entity name')
        return decl_name(names[0])
    # Identity names for initializer, deinitializer and subscript entities.
    conventional = {'Allocator': 'init', 'Constructor': 'init',
                    'Destructor': 'deinit', 'Deallocator': 'deinit',
                    'IsolatedDeallocator': 'deinit', 'Subscript': 'subscript'}
    if node.kind in conventional:
        return conventional[node.kind]
    raise ValueError('unnamed entity: ' + node.kind)


def context_path(node):
    if node.kind == 'Type':
        if len(node.children) != 1:
            raise ValueError('ambiguous context Type')
        return context_path(node.children[0])
    if node.kind == 'Module':
        return [['module', node.text]]
    if node.kind in CONTEXT_KINDS:
        return context_path(node.children[0]) + [[CONTEXT_KINDS[node.kind], entity_name(node)]]
    if node.kind == 'Extension':
        module = child(node, 'Module')
        extended = [n for n in node.children if n.kind not in {'Module', 'DependentGenericSignature'}]
        if len(extended) != 1:
            raise ValueError('ambiguous extension context')
        return [['extension', module.text]] + context_path(extended[0])
    if node.kind == 'AnonymousContext':
        name = child(node, 'Identifier').text
        parent = [n for n in node.children if n.kind not in {'Identifier', 'TypeList'}]
        if len(parent) != 1:
            raise ValueError('ambiguous anonymous context')
        return context_path(parent[0]) + [['anonymous', name]]
    if node.kind in {'Function', 'Allocator', 'Constructor', 'Destructor', 'Deallocator'}:
        return context_path(node.children[0]) + [['local', entity_name(node)]]
    if node.kind in {'ExplicitClosure', 'ImplicitClosure'}:
        return context_path(node.children[0]) + [['local', str(child(node, 'Number').index)]]
    if node.kind.startswith('BoundGeneric'):
        return context_path(child(node, 'Type'))
    raise ValueError('unprojected context kind: ' + node.kind)


def outer_function(entity):
    types = [n for n in entity.children if n.kind == 'Type']
    if not types:
        return None
    if len(types) != 1:
        raise ValueError('ambiguous entity Type')
    node = types[0]
    # Never descend into ArgumentTuple or ReturnType searching for effects.
    while node.kind in {'Type', 'DependentGenericType'}:
        children = [n for n in node.children if n.kind != 'DependentGenericSignature']
        if len(children) != 1:
            raise ValueError('ambiguous outer type wrapper')
        node = children[0]
    return node if node.kind in FUNCTION_TYPES else None


def oracle_projection(tree):
    if len(tree.children) != 1:
        raise ValueError('Global has attributes or more than one entity')
    entity = tree.children[0]
    kind = entity.kind
    if kind == 'Static':
        # Contract compares the node directly under Global, including this wrapper.
        raise ValueError('Static wrapper is not a rule-2 entity')
    if kind == 'TypeMetadataAccessFunction':
        nominal = child(entity, 'Type')
        if len(nominal.children) != 1:
            raise ValueError('ambiguous metadata type')
        nominal = nominal.children[0]
        path = context_path(nominal)
        return dict(entity=kind, context=path[:-1], name=path[-1][1],
                    labels=[], parameter_count=0), set()
    function = outer_function(entity)
    if kind not in {'Function', 'Allocator', 'Constructor', 'Destructor', 'Deallocator',
                    'IsolatedDeallocator'}:
        raise ValueError('decided entity is outside rule 2: ' + kind)
    if function is None:
        if kind not in {'Destructor', 'Deallocator', 'IsolatedDeallocator'}:
            raise ValueError('no outer function type')
        count, effects = 0, set()
    else:
        arguments = child(child(function, 'ArgumentTuple'), 'Type')
        if len(arguments.children) != 1:
            raise ValueError('ambiguous argument Type')
        arguments = arguments.children[0]
        count = len(arguments.children) if arguments.kind == 'Tuple' else 1
        effects = {n.kind for n in function.children if n.kind in EFFECTS}
    lists = [n for n in entity.children if n.kind == 'LabelList']
    if len(lists) > 1:
        raise ValueError('multiple label lists')
    labels = []
    if lists:
        for label in lists[0].children:
            if label.kind == 'FirstElementMarker':
                labels.append(None)
            elif label.kind == 'Identifier':
                labels.append(label.text)
            else:
                raise ValueError('unprojected label kind: ' + label.kind)
    if not labels:
        labels = [None] * count
    if len(labels) != count:
        raise ValueError('label count does not match parameter count')
    return dict(entity=kind, context=context_path(entity.children[0]),
                name=entity_name(entity), labels=labels, parameter_count=count), effects


def demangle_batch(symbols):
    completed = subprocess.run(['xcrun', 'swift-demangle', '--tree-only'],
                               input='\n'.join(symbols) + '\n', text=True,
                               capture_output=True, timeout=60, check=True)
    chunks = re.split(r'^Demangling for ', completed.stdout, flags=re.MULTILINE)
    if chunks[0].strip() or len(chunks) != len(symbols) + 1:
        raise ValueError('demangler output count/framing mismatch')
    output = []
    for expected, chunk in zip(symbols, chunks[1:]):
        heading, separator, body = chunk.partition('\n')
        if not separator or heading != expected:
            raise ValueError('demangler output symbol order mismatch')
        output.append(body)
    return output


def input_sets():
    fixture = json.loads((ROOT / 'fixtures/swift-error-flow/broad-imports/expected.json').read_text())
    owned = sorted({r['symbol'] for r in fixture['stub_calls'] if r['symbol'].startswith('_$s')})
    if len(owned) != 19:
        raise ValueError('owned import fixture must contain 19 Swift symbols')
    names = ROOT / 'fixtures/swift-declaration-grammar/synthetic-names.txt'
    synthetic = sorted({line.strip() for line in names.read_text().splitlines()
                        if line.strip() and not line.startswith('#')})
    if not synthetic or any(not re.match(r'^_?\$s', n) for n in synthetic):
        raise ValueError('synthetic name list is absent, empty, or contains non-Swift names')
    sdk = Path(subprocess.run(['xcrun', '--show-sdk-path'], capture_output=True,
                              text=True, timeout=30, check=True).stdout.strip())
    every = int(os.environ.get('AIRS_GRAMMAR_SDK_EVERY', '1'))
    if every < 1:
        raise ValueError('AIRS_GRAMMAR_SDK_EVERY must be positive')
    groups = {'owned_imports': owned, 'owned_synthetic': synthetic}
    for relative in ('usr/lib/swift/libswiftCore.tbd',
                     'usr/lib/swift/libswift_Concurrency.tbd',
                     'System/Library/Frameworks/Foundation.framework/Foundation.tbd'):
        # Text stubs only. Quotes, commas, whitespace and brackets delimit YAML names.
        text = (sdk / relative).read_text(encoding='utf-8')
        symbols = sorted(set(re.findall(r'(?<![\w$])_?\$s[^\s\x27",\[\]{}]+', text)))
        if not symbols:
            raise ValueError('no Swift symbols in SDK text stub: ' + relative)
        groups[relative] = symbols[::every]
    sampled = sum(len(v) for k, v in groups.items() if k.endswith('.tbd'))
    if os.environ.get('CI') != 'true' and sampled > 1000:
        raise ValueError('local SDK sample exceeds 1000; increase AIRS_GRAMMAR_SDK_EVERY')
    return groups, every


class DeclarationGrammarOracleTests(unittest.TestCase):
    def setUp(self):
        # Skip from setUp, not setUpClass, so the skip is recorded under the
        # test method's id that the CI allow-list names.
        try:
            found = subprocess.run(['xcrun', '--find', 'swift-demangle'],
                                   capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise unittest.SkipTest('swift-demangle unavailable') from error
        if found.returncode:
            raise unittest.SkipTest('swift-demangle unavailable')

    def test_differential(self):
        from airs.swift_declaration_grammar import parse_declaration
        groups, every = input_sets()
        coverage = {'schema_version': 1, 'sdk_every': every, 'inputs': {},
                    'soundness_disagreements': 0, 'identity_mismatches': 0}
        failures = []
        for source, symbols in groups.items():
            counts = collections.Counter(total=len(symbols))
            reasons = collections.Counter()
            for start in range(0, len(symbols), 128):
                batch = symbols[start:start + 128]
                for symbol, raw in zip(batch, demangle_batch(batch)):
                    result = parse_declaration(symbol)
                    if result.throw_decision == 'undecided':
                        reasons[result.reason] += 1
                        continue
                    counts['decided'] += 1
                    counts[result.throw_decision] += 1
                    actual = result.identity.oracle_projection() if result.identity else None
                    try:
                        expected, effects = oracle_projection(parse_tree(raw))
                        identity_bad = actual != expected
                        soundness_bad = result.throw_decision == 'non_throwing' and bool(effects)
                    except (ValueError, IndexError, TypeError, json.JSONDecodeError) as error:
                        expected = {'projection_error': str(error), 'tree': raw}
                        identity_bad = True
                        # An unprojectable decided tree cannot certify soundness.
                        soundness_bad = result.throw_decision == 'non_throwing'
                    coverage['identity_mismatches'] += int(identity_bad)
                    coverage['soundness_disagreements'] += int(soundness_bad)
                    if (identity_bad or soundness_bad) and len(failures) < 50:
                        failures.append({'symbol': symbol, 'airs': actual, 'oracle': expected,
                                         'decision': result.throw_decision,
                                         'soundness': soundness_bad, 'identity': identity_bad})
            coverage['inputs'][source] = {
                **counts, 'decided_share': counts['decided'] / counts['total'],
                'non_throwing_share': counts['non_throwing'] / counts['decided'] if counts['decided'] else 0,
                'counts_by_reason': dict(sorted(reasons.items())),
            }
        output = os.environ.get('AIRS_GRAMMAR_COVERAGE_OUT')
        if output:
            path = Path(output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(coverage, sort_keys=True, indent=2) + '\n')
        if failures:
            print(json.dumps(failures, ensure_ascii=True, sort_keys=True, indent=2))
        self.assertEqual(coverage['soundness_disagreements'], 0, 'outer-effect soundness gate')
        self.assertEqual(coverage['identity_mismatches'], 0, 'identity projection gate')


if __name__ == '__main__':
    unittest.main()
