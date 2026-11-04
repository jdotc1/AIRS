"""Refused direct-edge diagnostics; synthetic words remain data only."""
import unittest

from airs.cfg import audit_current_function
from test_rbit_x_candidate import fixture, PRO, EPI, RET, NOP, BASE


class RefusedBranchTargetTests(unittest.TestCase):
    def test_branch_refusal_retains_signed_preferred_vm_target(self):
        for word, target in ((0x14000003, BASE + 12),
                             (0x17ffffff, BASE - 4),
                             (0x54000060, BASE + 12)):
            with self.subTest(word=hex(word)):
                result = audit_current_function(*fixture((word, NOP, RET), 0x02000000))
                self.assertEqual((result.verdict, result.reason_codes, result.checked_pcs),
                                 ('unresolved', ('cfg_edge_not_modeled',), ()))
                evidence = result.evidence[0]
                self.assertEqual(evidence.address, BASE)
                self.assertEqual(evidence.observed,
                                 f'ARM64 instruction word 0x{word:08x}; preferred VM target {target:#x}')

    def test_unrecognized_call_entry_retains_target_without_following_it(self):
        from unittest.mock import patch
        image, fn, entry = fixture(PRO + (0x11000400, 0x94000080) + EPI, 0x04000000, with_callee=True)
        original = type(image).bytes_at
        requests = []

        def read(selected, address, size):
            requests.append((address, size))
            return original(selected, address, size)

        with patch.object(type(image), 'bytes_at', new=read):
            result = audit_current_function(image, fn, entry)
        self.assertEqual((result.verdict, result.reason_codes, result.checked_pcs),
                         ('unresolved', ('cfg_call_target_not_modeled',), ()))
        self.assertEqual(result.evidence[0].address, BASE + 12)
        self.assertEqual(result.evidence[0].observed,
                         'ARM64 instruction word 0x94000080; preferred VM target 0x120c')
        self.assertNotIn((BASE + 0x20c, 4), requests)

    def test_target_attribution_requires_matching_direct_edge_kind(self):
        from dataclasses import replace
        from airs.cfg import _with_refusal_instruction
        from airs.types import AuditResult, Evidence
        for word, code in ((NOP, 'cfg_edge_not_modeled'),
                           (0xffffffff, 'cfg_edge_not_modeled'),
                           (0x94000001, 'cfg_edge_not_modeled'),
                           (0x14000001, 'cfg_call_target_not_modeled')):
            with self.subTest(word=hex(word), code=code):
                image, fn, _ = fixture((word, RET))
                result = AuditResult('unresolved', 'compact', 'frameless', 'metadata_only',
                                     (code,), evidence=(Evidence(code, 'refused', fn.start),))
                self.assertIs(_with_refusal_instruction(image, fn, result), result)
                existing = replace(result, evidence=(replace(result.evidence[0], observed='retained'),))
                self.assertIs(_with_refusal_instruction(image, fn, existing), existing)

    def test_call_target_sign_extension_and_zero_budget_keep_refusal(self):
        from dataclasses import replace
        from airs.cfg import _with_refusal_instruction
        from airs.types import AuditResult, Evidence, Limits
        image, fn, entry = fixture((0x97ffffff, RET))
        code = 'cfg_call_target_not_modeled'
        result = AuditResult('unresolved', 'compact', 'frame', 'metadata_only', (code,),
                             evidence=(Evidence(code, 'refused', fn.start),))
        decorated = _with_refusal_instruction(image, fn, result)
        self.assertEqual(decorated.evidence[0].observed,
                         'ARM64 instruction word 0x97ffffff; preferred VM target 0xffc')
        self.assertEqual(replace(decorated, evidence=result.evidence), result)
        limited = audit_current_function(*fixture((0x14000003, NOP, RET), 0x02000000),
                                         Limits(max_evidence_per_function=0))
        self.assertEqual(limited.verdict, 'unresolved')
        self.assertEqual(limited.evidence, ())
