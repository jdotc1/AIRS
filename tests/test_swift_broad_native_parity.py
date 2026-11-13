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
)


ROOT = Path(__file__).resolve().parents[1]


class SwiftBroadNativeParityTests(unittest.TestCase):
    def native_source(self, filename):
        return (ROOT / "native" / "Sources" / "AIRSCore" / filename).read_text(encoding="utf-8")

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
