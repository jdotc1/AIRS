"""Canonical W copies truncate known constants; never preserve unknown X results."""
import unittest
from test_swift_success_constants import success
from test_swift_w_constants import wide


def wcopy(destination,source):
    return 0x2a0003e0 | (source<<16) | destination

class WCopyFirstTests(unittest.TestCase):
    def test_known_w_literal_copies_to_return_register(self):
        call=success((wide(0x1234,16,rd=19),wcopy(0,19)))['calls'][0]
        self.assertEqual(call['success_constant']['status'],'constant_register_candidate')
        self.assertEqual(call['success_constant']['constant_bits'],'0x0000000012340000')
        self.assertEqual(call['return_choice']['status'],'structural_choice_candidate')

class WCopyBoundaryTests(unittest.TestCase):
    def test_x_constant_is_truncated_but_x_copy_retains_upper_bits(self):
        for copy,bits in ((wcopy(0,19),'0x00000000ffffffff'),(0xaa1303e0,'0xffffffffffffffff')):
            self.assertEqual(success((0x92800013,copy))['calls'][0]['success_constant']['constant_bits'],bits)

    def test_known_transitive_w_copies_and_self_copy(self):
        result=success((wide(42,rd=19),wcopy(20,19),wcopy(0,20),wcopy(0,0)))['calls'][0]['success_constant']
        self.assertEqual(result['constant_bits'],'0x000000000000002a')

    def test_unknown_source_kills_a_prior_constant(self):
        call=success((wide(1),wcopy(0,19)))['calls'][0]
        self.assertEqual(call['success_constant']['reason'],'success_x0_constant_not_known')

    def test_w_copy_never_preserves_unknown_64bit_call_result(self):
        for body in ((wcopy(0,0),),(0xaa0003f3,wcopy(0,19))):
            call=success(body)['calls'][0]
            self.assertEqual(call['success_result']['status'],'declined')
            self.assertEqual(call['success_constant']['status'],'declined')

    def test_other_destination_preserves_original_x0_and_zr_is_not_sp(self):
        call=success((wcopy(19,0),))['calls'][0]
        self.assertEqual(call['success_result']['status'],'preserved_register_candidate')
        result=success((wide(1,rd=19),wcopy(31,19),wcopy(0,31)))['calls'][0]['success_constant']
        self.assertEqual(result['constant_bits'],'0x0000000000000000')

    def test_only_canonical_alias_is_recognized_and_raw_fields_retained(self):
        from airs.swift_error_flow import decode_instruction
        word=wcopy(0,19);value=decode_instruction(word,0x1000)
        self.assertEqual((value.kind,value.word,value.address,value.rd,value.rn),('wmov',word,0x1000,0,19))
        # Shift amount/type, nonzero first operand, and inverted source are not MOV.
        for modified in (word|(1<<10),word|(1<<22),word^(1<<5),word|(1<<21)):
            self.assertNotEqual(decode_instruction(modified).kind,'wmov')
            self.assertEqual(success((wide(1,rd=19),modified))['calls'][0]['success_constant']['status'],'declined')

    def test_error_arm_copy_after_call_and_invalidation_before_call(self):
        from test_swift_error_constants import error_arm
        call=error_arm((0x94000100,wide(42,rd=19),wcopy(0,19)))['calls'][0]
        self.assertEqual(call['error_constant']['constant_bits'],'0x000000000000002a')
        self.assertFalse(call['error_constant']['call_return_proven'])
        call=error_arm((wide(42,rd=19),0x94000100,wcopy(0,19)))['calls'][0]
        self.assertEqual(call['error_constant']['reason'],'error_x0_constant_not_known')

    def test_forward_layout_copies_on_both_arms(self):
        from test_swift_success_result import report
        words=(0xb5000095,wide(1,rd=19),wcopy(0,19),0x14000003,
               wide(0,negate=True,rd=19),wcopy(0,19),0xd65f03c0)
        choice=report(words)['calls'][0]['return_choice']
        self.assertEqual(choice['success']['constant_bits'],'0x0000000000000001')
        self.assertEqual(choice['error']['constant_bits'],'0x00000000ffffffff')

    def test_postcall_and_tail_copy_scope_remains_refused(self):
        from test_swift_success_result import report
        from test_swift_shared_epilogue import WORDS
        self.assertEqual(report((wcopy(19,21),)+WORDS)['calls'][0]['status'],'declined')
        self.assertEqual(report(WORDS[:6]+(wcopy(0,19),0xd65f03c0))['calls'][0]['success_constant']['status'],'declined')

    def test_exact_limits_and_overflow_with_copy_chains(self):
        from test_swift_success_result import NOP
        body=(wide(1,rd=19),)+(wcopy(0,19),)*7
        result=success(body,(NOP,)*7+(0xd65f03c0,),error_call=0x94000100)['calls'][0]['success_constant']
        self.assertEqual(result['status'],'constant_register_candidate')
        self.assertEqual(len(result['instructions']),16)
        self.assertEqual(success(body+(wcopy(0,0),),error_call=0x94000100)['calls'][0]['success_constant']['status'],'declined')

class WCopyCLIControls(unittest.TestCase):
    def test_cli_reports_zero_extended_copy_after_void_call(self):
        import contextlib,io,json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from test_swift_error_flow import image
        from test_swift_shared_epilogue import WORDS
        from airs.cli import main
        words=WORDS[:4]+(0x14000003,wide(0,negate=True,rd=19),wcopy(0,19))+WORDS[6:]
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source=Path(folder)/'w-copy-outcome.macho'
            source.write_bytes(image(words,symbol='_$s4Demo8validateyyKF').data)
            options=['swift-error-flow',str(source),'--include-error-regions','--validate-region-entries','--include-structured-presentation']
            for format in ('json','text'):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):self.assertEqual(main(options+['--format',format]),0)
                if format=='json':
                    value=json.loads(output.getvalue());call=value['calls'][0]
                    self.assertEqual(call['callee']['result'],'Swift.Void')
                    self.assertEqual(call['success_constant']['constant_bits'],'0x00000000ffffffff')
                    self.assertEqual(call['success_result']['status'],'declined')
                    self.assertEqual(value['error_region_model_version'],'swift-sync-error-region-v12')
                else:
                    self.assertIn('wmov',output.getvalue())
                    self.assertIn('0x2a1303e0',output.getvalue())
                    self.assertIn('Source reconstruction: disabled',output.getvalue())
