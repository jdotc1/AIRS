"""Bounded unknown-recovery diagnostics on new typed instruction inputs."""
import unittest
from dataclasses import replace

from airs.cfg import audit_current_function
from airs.engine import _serialize_evidence
from airs.types import Limits
from test_rbit_x_candidate import fixture, PAIR_PRO, PAIR_EPI, CALL, BASE

CLS_X19_X19 = 0xdac01673


class CFGUnknownRecoveryEvidenceTests(unittest.TestCase):
    def test_first_unknown_retains_register_pc_and_recovery_values(self):
        image, fn, entry = fixture(PAIR_PRO + (CLS_X19_X19, CALL) + PAIR_EPI,
                                   0x04000000, with_callee=True)
        result = audit_current_function(image, fn, entry)
        self.assertEqual((result.verdict, result.reason_codes, result.scope, result.checked_pcs),
                         ('unresolved', ('unknown_recovery_value',), 'synchronous_call_sites', ()))
        self.assertEqual(len(result.evidence), 1)
        evidence = result.evidence[0]
        self.assertEqual(evidence.address, BASE + 20)
        self.assertEqual(evidence.expected, 'original x19')
        self.assertTrue(evidence.observed.startswith('unknown ('), evidence.observed)
        self.assertIn('x19', evidence.message)
        self.assertIn('known-reachable', evidence.message)
        self.assertEqual(_serialize_evidence(evidence)['address'], '0x1014')

    def test_complete_unknown_count_is_preserved_with_one_or_zero_rows(self):
        image, fn, entry = fixture(PAIR_PRO + (CLS_X19_X19, CALL, CALL) + PAIR_EPI,
                                   0x04000000, with_callee=True)
        one = audit_current_function(image, fn, entry, replace(Limits(), max_evidence_per_function=1))
        self.assertTrue(one.evidence[0].message.startswith('2 required CFG recovery values are unknown;'))
        self.assertEqual(one.evidence[0].address, BASE + 20)
        zero = audit_current_function(image, fn, entry, replace(Limits(), max_evidence_per_function=0))
        self.assertEqual(zero.evidence, ())
        self.assertEqual(replace(one, evidence=()), zero)

    def test_later_unknown_overrides_concrete_mismatch_without_checked_pcs(self):
        # MOVZ X19 establishes a concrete mismatch; CLS X19,X0 after the call
        # consumes ABI-clobbered X0 and makes the later recovery unknown.
        words = PAIR_PRO + (0xd28000f3, CALL, 0xdac01413, CALL) + PAIR_EPI
        result = audit_current_function(*fixture(words, 0x04000000, with_callee=True),
                                        replace(Limits(), max_evidence_per_function=1))
        self.assertEqual((result.verdict, result.reason_codes, result.checked_pcs),
                         ('unresolved', ('unknown_recovery_value',), ()))
        self.assertEqual(result.evidence[0].address, BASE + 28)
        self.assertEqual(result.evidence[0].expected, 'original x19')
        self.assertTrue(result.evidence[0].observed.startswith('unknown ('))

    def test_possible_path_unknown_is_not_labeled_known_reachable(self):
        # Unknown entry flags fork both paths. Only the fallthrough performs CLS.
        words = PAIR_PRO + (0x54000040, CLS_X19_X19, CALL) + PAIR_EPI
        result = audit_current_function(*fixture(words, 0x04000000, with_callee=True))
        self.assertEqual(result.verdict, 'unresolved')
        self.assertEqual(result.reason_codes, ('unknown_recovery_value',))
        self.assertEqual(result.checked_pcs, ())
        self.assertIn('conservative possible', result.evidence[0].message)
        self.assertNotIn('known-reachable', result.evidence[0].message)
        self.assertEqual(result.evidence[0].address, BASE + 24)
