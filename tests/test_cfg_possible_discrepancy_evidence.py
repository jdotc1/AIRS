"""Possible-path diagnostic values must never imply a supported mismatch."""
from dataclasses import replace
import unittest

from airs.cfg import audit_current_function
from airs.engine import _serialize_evidence
from airs.types import Limits
from test_rbit_x_candidate import fixture, PAIR_PRO, PAIR_EPI, CALL, BASE


def candidate(limits=Limits()):
    # Unknown entry flags; taken branch skips MOVZ X19,#7, both paths call.
    words = PAIR_PRO + (0x54000040, 0xd28000f3, CALL) + PAIR_EPI
    return audit_current_function(*fixture(words, 0x04000000, with_callee=True), limits)


class CFGPossibleDiscrepancyEvidenceTests(unittest.TestCase):
    def test_possible_discrepancy_retains_pc_register_and_values(self):
        result = candidate()
        self.assertEqual((result.verdict, result.reason_codes, result.scope, result.checked_pcs),
                         ('unresolved', ('cfg_path_feasibility_unknown',), 'synchronous_call_sites', ()))
        self.assertEqual(len(result.evidence), 1)
        evidence = result.evidence[0]
        self.assertEqual(evidence.address, BASE + 24)
        self.assertEqual(evidence.expected, 'original x19')
        self.assertEqual(evidence.observed, 'constant 0x7')
        self.assertIn('x19', evidence.message)
        self.assertIn('conservative possible', evidence.message)
        self.assertNotIn('known-reachable', evidence.message)
        self.assertEqual(_serialize_evidence(evidence)['address'], '0x1018')

    def test_one_and_zero_evidence_budgets_do_not_change_verdict(self):
        one = candidate(replace(Limits(), max_evidence_per_function=1))
        zero = candidate(replace(Limits(), max_evidence_per_function=0))
        self.assertEqual(len(one.evidence), 1)
        self.assertEqual(one.evidence[0].observed, 'constant 0x7')
        self.assertEqual(zero.evidence, ())
        self.assertEqual(replace(one, evidence=()), zero)

    def test_known_reachable_discrepancy_keeps_supported_mismatch(self):
        words = PAIR_PRO + (0x11000400, 0xd28000f3, CALL) + PAIR_EPI
        result = audit_current_function(*fixture(words, 0x04000000, with_callee=True))
        self.assertEqual(result.verdict, 'inconsistency')
        self.assertEqual(result.reason_codes, ('caller_state_mismatch',))
        self.assertEqual(result.checked_pcs, (BASE + 24,))
        self.assertEqual(result.evidence[0].expected, 'original x19')
        self.assertEqual(result.evidence[0].observed, 'constant 0x7')
        self.assertIn('known-reachable', result.evidence[0].message)

    def test_unknown_still_overrides_possible_discrepancy(self):
        # Unknown entry flags choose between concrete X19 and CLS of original X19.
        words = PAIR_PRO + (0x54000060, 0xd28000f3, 0x14000002, 0xdac01673, CALL) + PAIR_EPI
        result = audit_current_function(*fixture(words, 0x04000000, with_callee=True),
                                        replace(Limits(), max_evidence_per_function=1))
        self.assertEqual((result.verdict, result.reason_codes, result.checked_pcs),
                         ('unresolved', ('unknown_recovery_value',), ()))
        self.assertTrue(result.evidence[0].observed.startswith('unknown ('))
        self.assertNotIn('recovery discrepancy exists', result.evidence[0].message)
