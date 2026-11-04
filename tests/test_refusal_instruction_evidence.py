"""Instruction refusal diagnostics on new tiny typed inputs, never executed."""
import unittest

from airs.cfg import audit_current_function
from airs.engine import _serialize_evidence
from test_rbit_x_candidate import fixture, RET, PRO, EPI


class RefusalInstructionEvidenceTests(unittest.TestCase):
    def test_current_refusals_retain_exact_word_pc_and_unresolved_scope(self):
        for word, code in ((0xd503233f, 'unsupported_pauth'),
                           (0xd61f0000, 'unsupported_control_flow'),
                           (0xffffffff, 'unsupported_instruction')):
            with self.subTest(word=hex(word)):
                image, function, entry = fixture(PRO + (word,) + EPI, with_callee=True)
                result = audit_current_function(image, function, entry)
                self.assertEqual(result.verdict, 'unresolved')
                self.assertEqual(result.scope, 'metadata_only')
                self.assertEqual(result.checked_pcs, ())
                self.assertEqual(result.reason_codes, (code,))
                evidence = next(e for e in result.evidence if e.code == code)
                self.assertEqual(evidence.address, function.start + 8)
                self.assertEqual(evidence.observed, f'ARM64 instruction word 0x{word:08x}')
                wire = _serialize_evidence(evidence)
                self.assertEqual(wire['address'], hex(function.start + 8))
                self.assertEqual(wire['observed'], evidence.observed)

    def test_optional_diagnostics_do_not_change_results_or_invent_bytes(self):
        from dataclasses import replace
        from unittest.mock import patch
        from airs.cfg import _with_refusal_instruction
        from airs.types import AuditResult, Evidence, InputError
        image, function, _ = fixture((0xffffffff, RET))
        base = AuditResult('unresolved', 'compact', 'frame', 'metadata_only',
                           ('unsupported_instruction',))
        for address in (None, function.start + 1, function.start - 4, function.end):
            result = replace(base, evidence=(Evidence('unsupported_instruction', 'refused', address),))
            with self.subTest(address=address):
                self.assertIs(_with_refusal_instruction(image, function, result), result)
        result = replace(base, evidence=(Evidence('unsupported_instruction', 'refused', function.start),))
        with patch.object(type(image), 'bytes_at', side_effect=InputError('unmapped_bytes', 'No bytes')):
            self.assertIs(_with_refusal_instruction(image, function, result), result)
        for changed in (replace(result, verdict='agreement'),
                        replace(result, evidence=()),
                        replace(result, reason_codes=('different_refusal',)),
                        replace(result, evidence=(replace(result.evidence[0], observed='existing evidence'),))):
            self.assertIs(_with_refusal_instruction(image, function, changed), changed)
        for changed_image in (replace(image, architecture='arm64e'), replace(image, cpu_subtype=0x80000000)):
            self.assertIs(_with_refusal_instruction(changed_image, function, result), result)

    def test_budget_zero_and_legacy_auditor_remain_unmodified(self):
        from dataclasses import replace
        from airs.audit import audit_function
        from airs.types import Limits
        image, function, entry = fixture(PRO + (0xd503233f,) + EPI)
        historical = audit_function(image, function, entry)
        current = audit_current_function(image, function, entry)
        self.assertEqual(replace(current, evidence=historical.evidence), historical)
        self.assertIsNone(historical.evidence[0].observed)
        limited = audit_current_function(image, function, entry, Limits(max_evidence_per_function=0))
        self.assertEqual(limited.evidence, ())
        self.assertEqual(limited.verdict, 'unresolved')
