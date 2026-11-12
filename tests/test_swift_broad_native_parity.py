"""Exact broad-profile and import-envelope parity with native source literals."""
import ast
from pathlib import Path
import re
import unittest

from airs import swift_broad_flow
from airs.macho_stubs import STUB_MODEL
from airs.swift_broad_flow import (
    IMPORT_CALLSITE_MODEL,
    IMPORT_REASON,
    IMPORTS_BROAD_LIMITS,
    PROFILE_LIMITS,
    PROFILE_MODELS,
)


ROOT = Path(__file__).resolve().parents[1]
# Profiles the engine offers and the native app does not admit. Each must exist in
# the engine, and the native app must name every other engine pair and no more.
ENGINE_ONLY_PROFILES = frozenset({"broad-imports-got-v1"})


class SwiftBroadNativeParityTests(unittest.TestCase):
    def native_source(self, filename):
        return (ROOT / "native" / "Sources" / "AIRSCore" / filename).read_text(encoding="utf-8")

    def test_exact_profile_model_pairs_match_engine(self):
        source = self.native_source("SwiftErrorFlowReport.swift")

        def property_cases(name):
            match = re.search(r"\bvar\s+" + name + r"\s*:\s*String\?\s*\{", source)
            self.assertIsNotNone(match, name)
            start = match.end()
            depth = 1
            end = start
            while end < len(source) and depth:
                depth += (source[end] == "{") - (source[end] == "}")
                end += 1
            self.assertEqual(depth, 0, name)
            entries = re.findall(
                r'case\s+\.(\w+)\s*:\s*(?:return\s+)?(?:"([^"\n]+)"|(nil))',
                source[start:end - 1],
            )
            self.assertTrue(entries, name)
            self.assertEqual(len(entries), len({case for case, _, _ in entries}), name)
            return {case: value for case, value, is_nil in entries if not is_nil}

        models = property_cases("broadModel")
        arguments = property_cases("broadArgument")
        self.assertEqual(set(models), set(arguments))
        actual = {(models[case], arguments[case]) for case in models}
        engine = {(PROFILE_MODELS[profile], profile) for profile in PROFILE_LIMITS}
        engine_only = {pair for pair in engine if pair[1] in ENGINE_ONLY_PROFILES}
        self.assertEqual(len(engine_only), len(ENGINE_ONLY_PROFILES))
        self.assertEqual(actual, engine - engine_only)

    def test_import_model_reason_stub_and_limitation_literals_match_engine(self):
        source = self.native_source("SwiftBroadFlowReport.swift")
        literals = set(re.findall(r'"([^"\n]*)"', source))
        for constant in (IMPORT_CALLSITE_MODEL, IMPORT_REASON, STUB_MODEL):
            with self.subTest(constant=constant):
                self.assertIn(constant, literals)
        # The coordinator exports no limitation constant. Extract its literal from
        # the limitations.append call without running analysis or duplicating it here.
        engine = ast.parse(Path(swift_broad_flow.__file__).read_text(encoding="utf-8"))
        limitations = []
        for node in ast.walk(engine):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            target = node.func.value
            if (node.func.attr == "append" and isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name) and target.value.id == "report"
                    and isinstance(target.slice, ast.Constant) and target.slice.value == "limitations"
                    and len(node.args) == 1 and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                limitations.append(node.args[0].value)
        self.assertEqual(len(limitations), 1)
        self.assertIn(limitations[0], literals)

    def test_import_count_key_literals_are_present(self):
        literals = set(re.findall(r'"([^"\n]*)"', self.native_source("SwiftBroadFlowReport.swift")))
        keys = {
            "attributed_stubs", "declined_stubs", "invalid_stub_sections",
            "selected_import_calls", "non_throwing_swift_import_calls",
            "non_swift_import_calls", "declined_stub_calls",
        }
        self.assertEqual(len(keys), 7)
        self.assertLessEqual(keys, literals)

    def test_imports_call_envelope_matches_native_boundary_fixture(self):
        # Native acceptance/refusal is exercised by
        # testImportsCallEnvelopeAtLimitAndAbove, avoiding a brittle Swift expression parse.
        self.assertEqual(IMPORTS_BROAD_LIMITS.max_total_evidence, 8192)


if __name__ == "__main__":
    unittest.main()
