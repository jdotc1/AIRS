#!/usr/bin/env python3
"""Generate exact Python and Swift admission registries from registry/models.json."""
import argparse
import json
from pathlib import Path
import re
import sys


OUTPUTS = ('src/airs/analysis_models.py', 'native/Sources/AIRSCore/AnalysisModels.swift')


def exact_keys(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f'expected exactly these keys: {", ".join(keys)}')


def label(value):
    if not isinstance(value, str) or re.fullmatch(r'[a-z0-9-]+', value) is None:
        raise ValueError('labels must be non-empty strings containing only [a-z0-9-]')


def unique(values, description):
    if len(values) != len(set(values)):
        raise ValueError(f'duplicate {description}')


def validate(source):
    exact_keys(source, ('cfg_models', 'linear_models', 'current_model', 'swift_broad_pairs', 'swift_caller_error_test_model'))
    for key in ('cfg_models', 'linear_models', 'swift_broad_pairs'):
        if not isinstance(source[key], list):
            raise ValueError(f'{key} must be an array')
    labels = list(source['cfg_models'])
    for item in source['linear_models']:
        exact_keys(item, ('label', 'evaluated_cfi'))
        labels.append(item['label'])
        if type(item['evaluated_cfi']) is not bool:
            raise ValueError('evaluated_cfi must be a boolean')
    for value in labels:
        label(value)
    unique(labels, 'label')
    label(source['current_model'])
    if source['current_model'] not in source['cfg_models']:
        raise ValueError('current_model must be in cfg_models')
    models, profiles = [], []
    for item in source['swift_broad_pairs']:
        exact_keys(item, ('model', 'profile', 'native_admitted'))
        label(item['model'])
        label(item['profile'])
        if type(item['native_admitted']) is not bool:
            raise ValueError('native_admitted must be a boolean')
        models.append(item['model'])
        profiles.append(item['profile'])
    label(source['swift_caller_error_test_model'])
    unique(labels + models + [source['swift_caller_error_test_model']], 'model')
    unique(profiles, 'profile')
    return source


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate object key: {key}')
        result[key] = value
    return result


def render(source):
    cfg = source['cfg_models']
    linear = [item['label'] for item in source['linear_models']]
    evaluated = [item['label'] for item in source['linear_models'] if item['evaluated_cfi']]
    pairs = source['swift_broad_pairs']
    comment = 'Generated from registry/models.json; do not edit by hand.'
    python = [
        '# ' + comment,
        '"""Exact historical report-admission identities, independent of engine capability.',
        '',
        'Unknown labels keep generic import validation. Never infer admission from a',
        'version number or prefix: historical aliases and policy differences are explicit.',
        '"""', '', 'CFG_MODELS = frozenset((',
        *(f'    {value!r},' for value in cfg), '))',
        f'KNOWN_MODELS = CFG_MODELS | frozenset({tuple(linear)!r})',
        f'EVALUATED_CFI_MODELS = CFG_MODELS | frozenset({tuple(evaluated)!r})',
        f'CURRENT_MODEL = {source["current_model"]!r}',
        f'SWIFT_CALLER_ERROR_TEST_MODEL = {source["swift_caller_error_test_model"]!r}',
        'SWIFT_BROAD_PAIRS = (',
        *(f'    {(item["model"], item["profile"])!r},' for item in pairs), ')',
        'SWIFT_BROAD_ENGINE_ONLY_PROFILES = frozenset(' + repr(tuple(
            item['profile'] for item in pairs if not item['native_admitted'])) + ')',
    ]
    swift = [
        '// ' + comment,
        '// Exact report-admission identities, not a claim of current engine capability.',
        '// Unknown and future labels retain generic import validation.',
        'enum AnalysisModels {', '    static let cfg: Set<String> = [',
        *(f'        "{value}",' for value in cfg), '    ]',
        '    /// The one current engine model. Must equal the engine ANALYSIS_MODEL_VERSION; reuse is pinned to it.',
        f'    static let current = "{source["current_model"]}"',
        f'    static let known = cfg.union({json.dumps(linear)})',
        f'    static let evaluatedCFI = cfg.union({json.dumps(evaluated)})',
        f'    static let swiftCallerErrorTest = "{source["swift_caller_error_test_model"]}"',
        '    static let swiftBroadNativePairs: [(model: String, profile: String)] = [',
        *(f'        (model: "{item["model"]}", profile: "{item["profile"]}"),'
          for item in pairs if item['native_admitted']), '    ]', '}',
    ]
    return ('\n'.join(python) + '\n', '\n'.join(swift) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        source = validate(json.loads((args.root / 'registry/models.json').read_text(encoding='utf-8'),
                                     object_pairs_hook=object_pairs))
        rendered = render(source)
        stale = False
        for name, content in zip(OUTPUTS, rendered):
            path = args.root / name
            expected = content.encode('utf-8')
            if args.check:
                if not path.is_file() or path.read_bytes() != expected:
                    print(f'stale generated file: {name}', file=sys.stderr)
                    stale = True
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(expected)
        return 1 if stale else 0
    except (OSError, ValueError) as error:
        print(f'model registry: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
