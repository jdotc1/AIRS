"""Synthetic exact-label admission controls; no binary analysis."""
import unittest
from airs.analysis_models import CFG_MODELS, KNOWN_MODELS, EVALUATED_CFI_MODELS

class AnalysisModelRegistryTests(unittest.TestCase):
    def test_exact_registry_relationships(self):
        self.assertEqual(len(CFG_MODELS), 46)
        self.assertEqual(KNOWN_MODELS - CFG_MODELS, {"arm64-linear-v1", "arm64-linear-dwarf-v2"})
        self.assertEqual(EVALUATED_CFI_MODELS - CFG_MODELS, {"arm64-linear-dwarf-v2"})
        self.assertIsInstance(CFG_MODELS, frozenset)
        for label in ("arm64-bounded-cls-v47-future", "arm64-bounded-cls-v48", "ARM64-bounded-cls-v47"):
            self.assertNotIn(label, KNOWN_MODELS)

    def test_every_cfg_label_retains_exact_subtype_and_dwarf_policy(self):
        from airs.report import validate_report
        from airs.types import InputError
        from test_report_v32_admission_candidate import synthetic_report, replace_mode
        for label in CFG_MODELS:
            with self.subTest(label=label):
                report = synthetic_report(label)
                self.assertIs(validate_report(report), report)
                report['image']['cpu_subtype'] = 0x80000000
                with self.assertRaises(InputError):
                    validate_report(report)
                report['image']['cpu_subtype'] = 0
                replace_mode(report, mode='dwarf', scope='synchronous_call_sites', encoding='0x3000004', coverage='dwarf_evaluated')
                self.assertIs(validate_report(report), report)
                report['findings'][0]['coverage'] = 'dwarf_reference'
                with self.assertRaises(InputError):
                    validate_report(report)

    def test_native_registry_has_identical_exact_cfg_labels(self):
        from pathlib import Path
        import re
        source = (Path(__file__).resolve().parents[1] / 'native/Sources/AIRSCore/AnalysisModels.swift').read_text()
        native_cfg = source.split('static let cfg:', 1)[1].split('static let known', 1)[0]
        self.assertEqual(set(re.findall(r'"(arm64-[^"]+)"', native_cfg)), CFG_MODELS)
