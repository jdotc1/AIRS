"""Golden comparison of historical declaration parsers on owned text names."""
import argparse
import dataclasses
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'fixtures/swift-declaration-grammar'
GOLDEN = DIRECTORY / 'v1-golden.json'


def snapshot():
    # The historical parsers are used only here; their answers do not define v2.
    from airs.swift_declaration_profiles import parse_broad_declaration
    from airs.swift_import_declarations import parse_import_declaration
    fixture = json.loads((ROOT / 'fixtures/swift-error-flow/broad-imports/expected.json').read_text())
    symbols = {row['symbol'] for row in fixture['stub_calls'] if row['symbol'].startswith('_$s')}
    synthetic = [line.strip() for line in (DIRECTORY / 'synthetic-names.txt').read_text().splitlines()
                 if line.strip() and not line.startswith('#')]
    if not synthetic:
        raise ValueError('synthetic name list must not be empty')
    symbols.update(synthetic)
    results = {symbol: {'broad': dataclasses.asdict(parse_broad_declaration(symbol)),
                        'imports': dataclasses.asdict(parse_import_declaration(symbol))}
               for symbol in sorted(symbols)}
    # Normalize tuples to the JSON representation used by the golden file.
    return json.loads(json.dumps({'schema_version': 1, 'symbols': results},
                                 sort_keys=True, ensure_ascii=True))


class HistoricalDeclarationIsolationTests(unittest.TestCase):
    def test_historical_outputs(self):
        if not GOLDEN.exists():
            self.skipTest('historical declaration golden has not been generated')
        self.assertEqual(json.loads(GOLDEN.read_text()), snapshot())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-golden', action='store_true')
    args, rest = parser.parse_known_args()
    if args.write_golden:
        if rest:
            parser.error('unexpected arguments with --write-golden')
        # Exclusive creation prevents accidentally replacing accepted evidence.
        payload = json.dumps(snapshot(), sort_keys=True, indent=2, ensure_ascii=True) + '\n'
        with GOLDEN.open('x', encoding='utf-8') as output:
            output.write(payload)
    else:
        unittest.main(argv=[__file__] + rest)
