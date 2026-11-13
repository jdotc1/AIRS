"""Independent, image-free validation of AIRS Navigator Results transport bytes.

This checker does not resolve evidence, inspect an image, or simulate store admission.
The implementation is standard-library only and does not import the exporter.
"""
import hashlib
import json
import re


class Rejected(ValueError):
    def __init__(self, code, path='$'):
        self.code, self.path = code, path


def require(condition, code='invalidRecord', path='$'):
    if not condition:
        raise Rejected(code, path)


def text(value):
    return type(value) is str and bool(value)


def integer(value, low=0, high=2**63-1):
    return type(value) is int and low <= value <= high


def matches(pattern, value):
    return type(value) is str and re.fullmatch(pattern, value, re.ASCII) is not None


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def identifier(prefix, fields):
    return prefix + '-' + hashlib.sha256(canonical(fields)).hexdigest()[:32]


def fields(value, required, optional=(), code='invalidRecord', path='$'):
    require(type(value) is dict, code, path)
    for name in required:
        require(name in value, code, path + '.' + name if path != '$' else name)
    require(set(value) <= set(required) | set(optional), code, path)


def parse(raw):
    """Bound construction itself, including deeply nested hostile input."""
    require(type(raw) is bytes, 'malformedJSON')
    require(len(raw) <= 4194304, 'budgetExceeded')
    try:
        source = raw.decode('utf-8')
    except UnicodeError:
        raise Rejected('malformedJSON') from None
    position = nodes = 0
    decoder = json.JSONDecoder()
    numeric = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?', re.ASCII)

    def space():
        nonlocal position
        while position < len(source) and source[position] in ' \t\r\n':
            position += 1

    def string(key=False):
        nonlocal position
        require(position < len(source) and source[position] == '"', 'malformedJSON')
        try:
            s, end = decoder.raw_decode(source, position)
            size = len(s.encode('utf-8'))
        except (ValueError, UnicodeError):
            raise Rejected('malformedJSON') from None
        position = end
        require(not any(ord(c) < 32 or 127 <= ord(c) <= 159 or
            ord(c) in (0x061c, 0x200e, 0x200f) or 0x202a <= ord(c) <= 0x202e or
            0x2066 <= ord(c) <= 0x2069 for c in s), 'unsafeText')
        require(size <= (64 if key else 4096), 'budgetExceeded')
        if key:
            require(matches(r'[A-Za-z_][A-Za-z0-9_]*', s), 'invalidKey')
        return s

    def value(depth):
        nonlocal position, nodes
        require(depth <= 32 and nodes < 65536, 'budgetExceeded')
        nodes += 1
        space()
        require(position < len(source), 'malformedJSON')
        token = source[position]
        if token == '"':
            return string()
        if token in '[{':
            object_mode = token == '{'
            close = '}' if object_mode else ']'
            container = {} if object_mode else []
            position += 1
            space()
            if position < len(source) and source[position] == close:
                position += 1
                return container
            while True:
                require(len(container) < 4096, 'budgetExceeded')
                space()
                if object_mode:
                    key = string(True)
                    require(key not in container, 'duplicateKey')
                    space()
                    require(position < len(source) and source[position] == ':', 'malformedJSON')
                    position += 1
                    container[key] = value(depth + 1)
                else:
                    container.append(value(depth + 1))
                space()
                require(position < len(source), 'malformedJSON')
                token = source[position]
                position += 1
                if token == close:
                    return container
                require(token == ',', 'malformedJSON')
        for word, scalar in (('true', True), ('false', False), ('null', None)):
            if source.startswith(word, position):
                position += len(word)
                return scalar
        match = numeric.match(source, position)
        require(match is not None, 'malformedJSON')
        token = match.group()
        require(not any(c in token for c in '.eE'), 'invalidNumber')
        require(len(token.lstrip('-')) <= 19, 'invalidNumber')
        number = int(token)
        require(-(2**63) <= number < 2**63, 'invalidNumber')
        position = match.end()
        return number

    result = value(0)
    space()
    require(position == len(source), 'malformedJSON')
    return result


SUBJECTS = set('image address range function type metadataRecord selector viewBody protocol field'.split())
PROVENANCE = set('loaderRecord decodedInstruction metadataRecord rule proofCertificate signatureRecord analystAction symbolGraph'.split())
REFUSALS = set('budgetExceeded cancelled preconditionFailed unsupportedToolchain outOfBounds malformedInput unknownSubject unknownFact conflictsWithAuthority notReversible'.split())
GAPS = set('unresolvedIndirectCall unboundGenericParameter unlinkedAsyncContinuation unreconstructedViewBody unknownType unnamedFunction unrecoveredStruct unresolvedObjCSend unknownCalleeEffects ambiguousLibraryIdentity unsupportedToolchain boundaryUncertain unresolvedTypeReference objcTypeReference unresolvedProtocol unknownContext missingFieldDescriptor malformedFieldDescriptor unresolvedSymbolicReference unresolvedConformance conflictingAnnotations staleAnnotation conflictingFacts budgetExceeded producerIncomplete'.split())
STRING_PREDICATES = set('hasName hasType callsTarget selectorOf asyncContinuationOf viewBodyType nominalKind superclass conformsTo metadataAccessorOf'.split())
BOOL_PREDICATES = set('isFunctionStart isGeneric isProtocol isPrivateOrLocal isImportedCType'.split())
OBJECT_PREDICATES = set('fieldLayout asyncInvocationChain libraryIdentity storedField enumCase methodTableEntry conformanceMethod pointerAuthKey'.split())


def subject(value, path):
    fields(value, ('kind', 'ref'), ('image',), path=path)
    require(type(value['kind']) is str and value['kind'] in SUBJECTS, path=path + '.kind')
    require(text(value['ref']), path=path + '.ref')
    require('image' not in value or text(value['image']), path=path + '.image')


def budget(value, path):
    fields(value, (), ('instructions', 'bytes', 'solverSteps', 'wallMillis'), path=path)
    require(all(integer(v) for v in value.values()), path=path)


def refusal(value, path):
    fields(value, ('code', 'detail', 'retryable'), path=path)
    require(type(value['code']) is str and value['code'] in REFUSALS and
            type(value['detail']) is str and type(value['retryable']) is bool, path=path)


def provenance(value, path):
    fields(value, ('kind', 'ref'), ('rule', 'ruleVersion'), path=path)
    require(type(value['kind']) is str and value['kind'] in PROVENANCE and text(value['ref']), path=path)
    require(('rule' in value) == ('ruleVersion' in value), path=path)
    if 'rule' in value:
        require(matches(r'airs\.[A-Za-z0-9_-]+', value['rule']), 'reservedRule', path + '.rule')
        require(value['ruleVersion'] == '1', 'reservedRule', path + '.ruleVersion')
    if value['kind'] == 'rule':
        require(matches(r'airs\.[A-Za-z0-9_-]+@1', value['ref']), 'reservedRule', path + '.ref')


def predicate_value(predicate, value, path):
    require(type(predicate) is str and predicate in STRING_PREDICATES | BOOL_PREDICATES | OBJECT_PREDICATES, path=path)
    expected = str if predicate in STRING_PREDICATES else bool if predicate in BOOL_PREDICATES else dict
    require(type(value) is expected, path=path)
    if predicate == 'nominalKind':
        require(value in ('class', 'struct', 'enum', 'protocol'), path=path)
    shapes = {
        'libraryIdentity': (('name', 'library'), ('libraryVersion',)),
        'storedField': (('name', 'type', 'var'), ()),
        'enumCase': (('name', 'payload', 'indirect'), ()),
        'methodTableEntry': (('index', 'implementation', 'kind'), ('name',)),
        'conformanceMethod': (('protocol', 'requirementIndex', 'implementation'), ('name',)),
        'pointerAuthKey': (('key', 'diversity', 'addressDiversified'), ()),
    }
    if predicate in shapes:
        fields(value, *shapes[predicate], path=path)
        for key, item in value.items():
            if key in ('var', 'indirect', 'addressDiversified'):
                require(type(item) is bool, path=path)
            elif key in ('index', 'requirementIndex', 'diversity'):
                require(integer(item), path=path)
            else:
                require(type(item) is str, path=path)
        if predicate == 'pointerAuthKey':
            require(value['key'] in ('IA', 'IB', 'DA', 'DB'), path=path)
        if predicate == 'methodTableEntry':
            require(value['kind'] in ('vtable', 'override'), path=path)


def fact(value, path, toolchain):
    fields(value, ('kind', 'schemaVersion', 'id', 'subject', 'predicate', 'value',
                   'status', 'provenance', 'toolchain', 'revert'), ('tier', 'derivedFrom'), path=path)
    require(value['kind'] == 'Fact' and type(value['schemaVersion']) is int and value['schemaVersion'] == 1, path=path)
    subject(value['subject'], path + '.subject')
    status = value['status']
    require(status in ('authoritative', 'derived', 'candidate', 'unknown'), path=path + '.status')
    require(('tier' in value) == (status in ('derived', 'candidate')), path=path + '.tier')
    if 'tier' in value:
        require(integer(value['tier'], 1, 3), path=path + '.tier')
    require(status != 'derived' or 'derivedFrom' in value, path=path + '.derivedFrom')
    require(status != 'authoritative' or 'derivedFrom' not in value, path=path + '.derivedFrom')
    if 'derivedFrom' in value:
        groups = value['derivedFrom']
        require(type(groups) is list and bool(groups), path=path + '.derivedFrom')
        for group in groups:
            require(type(group) is list and bool(group), path=path + '.derivedFrom')
            require(all(matches(r'f-[0-9a-f]{32}|ann:[^\n]+/(0|[1-9][0-9]*)', p) for p in group), path=path + '.derivedFrom')
            require(len(set(group)) == len(group), path=path + '.derivedFrom')
    if status == 'unknown':
        require(value['value'] is None, path=path + '.value')
        require(type(value['predicate']) is str and value['predicate'] in STRING_PREDICATES | BOOL_PREDICATES | OBJECT_PREDICATES, path=path + '.predicate')
    elif status == 'candidate':
        fields(value['value'], ('alternatives',), path=path + '.value')
        choices = value['value']['alternatives']
        require(type(choices) is list and len(choices) >= 2, path=path + '.value')
        require(len({canonical(c) for c in choices}) == len(choices), path=path + '.value')
        for choice in choices:
            predicate_value(value['predicate'], choice, path + '.value')
    else:
        predicate_value(value['predicate'], value['value'], path + '.value')
    ps = value['provenance']
    require(type(ps) is list and bool(ps), path=path + '.provenance')
    for i, p in enumerate(ps):
        provenance(p, path + f'.provenance[{i}]')
    require(text(value['toolchain']), path=path + '.toolchain')
    require(value['toolchain'] == toolchain, 'unsupportedToolchain', path + '.toolchain')
    rule = next((p['rule'] + '@' + p['ruleVersion'] for p in ps if 'rule' in p), '')
    ident = identifier('f', [value['subject'], value['predicate'], value['value'], rule])
    require(value['id'] == ident and value['revert'] == 'revert:' + ident, path=path + '.id')


def frontier(value, path, toolchain):
    fields(value, ('kind', 'schemaVersion', 'id', 'subject', 'gap', 'detail', 'blockedBy',
                   'missingEvidence', 'primitives', 'cost', 'leverage', 'reason', 'toolchain'), path=path)
    require(value['kind'] == 'FrontierItem' and type(value['schemaVersion']) is int and value['schemaVersion'] == 1, path=path)
    subject(value['subject'], path + '.subject')
    require(type(value['gap']) is str and value['gap'] in GAPS and type(value['detail']) is str, path=path)
    for key in ('blockedBy', 'missingEvidence', 'primitives', 'reason'):
        require(type(value[key]) is list, path=path + '.' + key)
    require(all(matches(r'f-[0-9a-f]{32}', p) for p in value['blockedBy']), path=path + '.blockedBy')
    require(len(set(value['blockedBy'])) == len(value['blockedBy']), path=path + '.blockedBy')
    require(all(type(p) is str for p in value['missingEvidence']), path=path + '.missingEvidence')
    for p in value['primitives']:
        fields(p, ('name', 'preconditions'), path=path + '.primitives')
        require(text(p['name']) and type(p['preconditions']) is list and
                all(type(c) is str for c in p['preconditions']), path=path + '.primitives')
    for r in value['reason']:
        refusal(r, path + '.reason')
    budget(value['cost'], path + '.cost')
    require(integer(value['leverage']), path=path + '.leverage')
    require(text(value['toolchain']), path=path + '.toolchain')
    require(value['toolchain'] == toolchain, 'unsupportedToolchain', path + '.toolchain')
    require(value['id'] == identifier('g', [value['subject'], value['gap'], value['detail']]), path=path + '.id')


def check(raw):
    """Return (accepted, refusal code or None, field path or None)."""
    try:
        document = parse(raw)
        fields(document, ('kind', 'formatVersion', 'identity', 'run', 'results'), code='invalidEnvelope')
        require(document['kind'] == 'airs.navigator_results', 'unsupportedFormat', 'kind')
        require(type(document['formatVersion']) is int and document['formatVersion'] == 1, 'unsupportedVersion', 'formatVersion')
        identity = document['identity']
        fields(identity, ('containerSHA256', 'sliceSHA256', 'sliceOffset', 'sliceSize',
                          'cpuType', 'cpuSubtype', 'uuid', 'preferredBase'), code='invalidEnvelope', path='identity')
        for key in ('containerSHA256', 'sliceSHA256'):
            require(matches(r'[0-9a-f]{64}', identity[key]), 'invalidEnvelope', 'identity.' + key)
        for key in ('cpuType', 'cpuSubtype'):
            require(integer(identity[key], -(2**31), 2**31-1), 'invalidEnvelope', 'identity.' + key)
        require(integer(identity['sliceOffset']), 'invalidEnvelope', 'identity.sliceOffset')
        require(integer(identity['sliceSize'], 1), 'invalidEnvelope', 'identity.sliceSize')
        require(identity['sliceOffset'] + identity['sliceSize'] < 2**63, 'invalidEnvelope', 'identity.sliceSize')
        require(identity['uuid'] is None or matches(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', identity['uuid']), 'invalidEnvelope', 'identity.uuid')
        require(matches(r'0x(?:0|[1-9a-f][0-9a-f]{0,15})', identity['preferredBase']), 'invalidEnvelope', 'identity.preferredBase')
        run = document['run']
        fields(run, ('producerName', 'producerVersion', 'contractVersion', 'completed', 'toolchain',
                     'resultCount', 'factCount', 'frontierCount', 'refusalCount'), code='invalidEnvelope', path='run')
        require(run['producerName'] == 'AIRS', 'invalidEnvelope', 'run.producerName')
        require(text(run['producerVersion']) and len(run['producerVersion'].encode()) <= 128, 'invalidEnvelope', 'run.producerVersion')
        require(type(run['contractVersion']) is int and run['contractVersion'] == 1, 'unsupportedVersion', 'run.contractVersion')
        require(type(run['completed']) is bool, 'invalidEnvelope', 'run.completed')
        require(text(run['toolchain']), 'invalidEnvelope', 'run.toolchain')
        for key, maximum in (('resultCount', 128), ('factCount', 1024), ('frontierCount', 1024), ('refusalCount', 128)):
            require(integer(run[key], 0, maximum), 'invalidEnvelope', 'run.' + key)
        results = document['results']
        require(type(results) is list, 'invalidEnvelope', 'results')
        require(len(results) <= 128, 'budgetExceeded', 'results')

        def arrays(v, path):
            if type(v) is list:
                require(len(v) <= 128, 'budgetExceeded', path)
                for i, child in enumerate(v):
                    arrays(child, path + f'[{i}]')
            elif type(v) is dict:
                for key, child in v.items():
                    arrays(child, path + '.' + key)
        nf = ng = nr = np = 0
        disclosed = False
        for i, r in enumerate(results):
            path = f'results[{i}]'
            require(type(r) is dict, path=path)
            for key in ('facts', 'frontier'):
                require(type(r.get(key)) is list, path=path + '.' + key)
            require(len(r['facts']) + len(r['frontier']) <= 128, 'budgetExceeded', path)
            nf += len(r['facts'])
            ng += len(r['frontier'])
            require(nf + ng <= 1024, 'budgetExceeded', 'results')
            nr += r.get('outcome') == 'refusal'
            arrays(r, path)
            for f in r['facts']:
                if type(f) is dict and type(f.get('provenance')) is list:
                    np += len(f['provenance'])
                    require(np <= 4096, 'budgetExceeded', 'results')
            disclosed |= any(type(g) is dict and g.get('gap') in ('producerIncomplete', 'budgetExceeded') for g in r['frontier'])
        for key, actual in (('resultCount', len(results)), ('factCount', nf), ('frontierCount', ng), ('refusalCount', nr)):
            require(run[key] == actual, 'countMismatch', 'run.' + key)
        require(run['completed'] or not results or disclosed, 'invalidEnvelope', 'run.completed')
        producer_refusal = None
        for i, r in enumerate(results):
            path = f'results[{i}]'
            fields(r, ('kind', 'schemaVersion', 'primitive', 'primitiveVersion', 'subject',
                       'budget', 'outcome', 'facts', 'frontier'), ('refusal',), path=path)
            require(r['kind'] == 'PrimitiveResult' and type(r['schemaVersion']) is int and r['schemaVersion'] == 1, path=path)
            require(text(r['primitive']), path=path + '.primitive')
            require(matches(r'airs\.[A-Za-z0-9_-]+', r['primitive']), 'reservedRule', path + '.primitive')
            require(r['primitiveVersion'] == '1', 'reservedRule', path + '.primitiveVersion')
            subject(r['subject'], path + '.subject')
            budget(r['budget'], path + '.budget')
            require(r['outcome'] in ('facts', 'narrowed', 'refusal'), path=path + '.outcome')
            require(('refusal' in r) == (r['outcome'] == 'refusal'), path=path + '.refusal')
            if r['outcome'] == 'refusal':
                require(not r['facts'], path=path + '.facts')
                refusal(r['refusal'], path + '.refusal')
                producer_refusal = path + '.refusal'
            elif r['outcome'] == 'facts':
                require(bool(r['facts']), path=path + '.facts')
            else:
                require(bool(r['frontier']), path=path + '.frontier')
            for j, f in enumerate(r['facts']):
                fact(f, path + f'.facts[{j}]', run['toolchain'])
            for j, g in enumerate(r['frontier']):
                frontier(g, path + f'.frontier[{j}]', run['toolchain'])
        if producer_refusal is not None:
            raise Rejected('producerRefusal', producer_refusal)
        return True, None, None
    except Rejected as error:
        return False, error.code, error.path
