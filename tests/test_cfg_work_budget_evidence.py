"""Explicit bounded CFG visit counts; no target execution or corpus work."""
from dataclasses import replace
import unittest

from airs.cfg import audit_current_function
from airs.engine import _serialize_evidence
from airs.types import Limits
from test_rbit_x_candidate import fixture, BASE, NOP, RET


def run(limit, evidence=1):
    image, fn, entry = fixture((0x11000400, NOP, RET), 0x02000000)
    return audit_current_function(image, fn, entry,
                                  replace(Limits(), max_cfg_steps_per_function=limit,
                                          max_evidence_per_function=evidence))


class CFGWorkBudgetEvidenceTests(unittest.TestCase):
    def test_exhaustion_records_limit_completed_visits_and_next_pc(self):
        for limit in (0, 1, 2):
            with self.subTest(limit=limit):
                result = run(limit)
                self.assertEqual((result.verdict, result.reason_codes, result.scope, result.checked_pcs),
                                 ('unresolved', ('cfg_work_limit',), 'metadata_only', ()))
                self.assertEqual(result.cfg_steps, limit)
                self.assertEqual(len(result.evidence), 1)
                evidence = result.evidence[0]
                self.assertEqual(evidence.address, BASE + 4 * limit)
                self.assertEqual(evidence.expected, f'configured CFG state-visit limit {limit}')
                self.assertEqual(evidence.observed, f'{limit} completed CFG state visits; next visit refused')
                self.assertEqual(_serialize_evidence(evidence)['address'], hex(BASE + 4 * limit))

    def test_zero_evidence_budget_preserves_exhaustion_without_rows(self):
        one = run(1)
        zero = run(1, 0)
        self.assertEqual(zero.evidence, ())
        self.assertEqual(replace(one, evidence=()), zero)

    def test_exact_completion_boundary_keeps_supported_leaf_result(self):
        result = run(3)
        self.assertEqual((result.verdict, result.scope, result.reason_codes),
                         ('agreement', 'modeled_leaf_body', ('supported_model_agreement',)))
        self.assertEqual(result.cfg_steps, 3)
        self.assertEqual(result.checked_pcs, (BASE, BASE + 4))
        self.assertFalse(any(e.code == 'cfg_work_limit' for e in result.evidence))

    def test_other_resource_refusals_do_not_acquire_work_count_diagnostics(self):
        image, fn, entry = fixture((0x11000400, NOP, RET), 0x02000000)
        result = audit_current_function(image, fn, entry,
                                        replace(Limits(), max_observations_per_function=0))
        self.assertEqual(result.reason_codes, ('observation_limit',))
        self.assertEqual(result.checked_pcs, ())
        self.assertIsNone(result.evidence[0].expected)
        self.assertIsNone(result.evidence[0].observed)
