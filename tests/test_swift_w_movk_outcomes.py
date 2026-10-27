"""Known-seeded W MOVK updates preserve low lanes and clear upper X bits."""
import unittest
from test_swift_success_constants import success
from test_swift_w_constants import wide


def wmovk(value,shift=0,rd=0):
    return 0x72800000 | ((shift//16)<<21) | (value<<5) | rd

class WMovkFirstTests(unittest.TestCase):
    def test_w_movk_completes_a_zero_extended_word(self):
        call=success((wide(0x1234),wmovk(0xabcd,16)))['calls'][0]
        self.assertEqual(call['success_constant']['status'],'constant_register_candidate')
        self.assertEqual(call['success_constant']['constant_bits'],'0x00000000abcd1234')
        self.assertEqual(call['return_choice']['status'],'structural_choice_candidate')

class WMovkBoundaryTests(unittest.TestCase):
    def test_w_update_clears_known_upper_x_bits(self):
        result=success((0x92800000,wmovk(0,16)))['calls'][0]['success_constant']
        self.assertEqual(result['constant_bits'],'0x000000000000ffff')

    def test_repeated_low_lane_updates_replace_instead_of_or(self):
        result=success((wide(0,negate=True),wmovk(0),wmovk(0x1234)))['calls'][0]['success_constant']
        self.assertEqual(result['constant_bits'],'0x00000000ffff1234')

    def test_unknown_prior_remains_unknown_even_with_both_lane_updates(self):
        for body in ((wmovk(1),),(wmovk(1),wmovk(2,16))):
            call=success(body)['calls'][0]
            self.assertEqual(call['presentation']['status'],'eligible_structural_only')
            self.assertEqual(call['success_constant']['reason'],'success_x0_constant_not_known')
            self.assertEqual(call['success_result']['status'],'declined')

    def test_unknown_overwrite_and_opaque_calls_destroy_seed(self):
        from test_swift_error_constants import error_arm
        result=success((wide(1),0xaa1303e0,wmovk(2,16)))['calls'][0]['success_constant']
        self.assertEqual(result['reason'],'success_x0_constant_not_known')
        result=error_arm((wide(1),0x94000100,wmovk(2,16)))['calls'][0]['error_constant']
        self.assertEqual(result['reason'],'error_x0_constant_not_known')

    def test_written_saved_result_alias_is_invalidated(self):
        call=success((0xaa0003f3,wmovk(1,rd=19),0xaa1303e0))['calls'][0]
        self.assertEqual(call['success_result']['status'],'declined')
        self.assertEqual(call['success_constant']['status'],'declined')

    def test_other_alias_survives_and_wzr_update_is_discarded(self):
        call=success((wmovk(1,rd=19),))['calls'][0]
        self.assertEqual(call['success_result']['status'],'preserved_register_candidate')
        result=success((wide(42),wmovk(0xffff,16,rd=31)))['calls'][0]['success_constant']
        self.assertEqual(result['constant_bits'],'0x000000000000002a')

    def test_error_arm_can_assign_after_last_opaque_call(self):
        from test_swift_error_constants import error_arm
        call=error_arm((0x94000100,wide(0x1234),wmovk(0xabcd,16)))['calls'][0]
        self.assertEqual(call['error_constant']['constant_bits'],'0x00000000abcd1234')
        self.assertFalse(call['error_constant']['call_return_proven'])
        self.assertEqual(call['return_choice']['status'],'structural_choice_candidate')

    def test_forward_layout_has_updates_on_both_arms(self):
        from test_swift_success_result import report
        words=(0xb5000095,wide(0x1234),wmovk(0xabcd,16),0x14000003,
               wide(0,negate=True),wmovk(0,16),0xd65f03c0)
        choice=report(words)['calls'][0]['return_choice']
        self.assertEqual(choice['success']['constant_bits'],'0x00000000abcd1234')
        self.assertEqual(choice['error']['constant_bits'],'0x000000000000ffff')
        self.assertFalse(choice['source_reconstruction_allowed'])

    def test_reserved_shifts_postcall_and_tail_updates_stay_refused(self):
        from test_swift_success_result import report
        from test_swift_shared_epilogue import WORDS
        for shift in (32,48):
            self.assertEqual(success((wide(1),wmovk(2,shift)))['calls'][0]['success_constant']['status'],'declined')
        self.assertEqual(report((wmovk(1,rd=19),)+WORDS)['calls'][0]['status'],'declined')
        self.assertEqual(report(WORDS[:6]+(wmovk(1),0xd65f03c0))['calls'][0]['success_constant']['status'],'declined')

    def test_exact_limits_and_overflow_with_updates(self):
        from test_swift_success_result import NOP
        body=(wide(1),)+(wmovk(2,16),)*7
        result=success(body,(NOP,)*7+(0xd65f03c0,),error_call=0x94000100)['calls'][0]['success_constant']
        self.assertEqual(result['status'],'constant_register_candidate')
        self.assertEqual(len(result['instructions']),16)
        self.assertEqual(success(body+(wmovk(3),),error_call=0x94000100)['calls'][0]['success_constant']['status'],'declined')

class WMovkCLIControls(unittest.TestCase):
    def test_cli_retains_w_update_bits_and_raw_word(self):
        import contextlib,io,json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from test_swift_error_flow import image
        from test_swift_shared_epilogue import WORDS
        from airs.cli import main
        words=WORDS[:4]+(0x14000003,wide(0x1234),wmovk(0xabcd,16))+WORDS[6:]
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source=Path(folder)/'w-movk-outcome.macho'
            source.write_bytes(image(words).data)
            options=['swift-error-flow',str(source),'--include-error-regions','--validate-region-entries','--include-structured-presentation']
            for format in ('json','text'):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):self.assertEqual(main(options+['--format',format]),0)
                if format=='json':
                    value=json.loads(output.getvalue())
                    self.assertEqual(value['calls'][0]['success_constant']['constant_bits'],'0x00000000abcd1234')
                    self.assertEqual(value['error_region_model_version'],'swift-sync-error-region-v10')
                else:
                    self.assertIn('wmovk',output.getvalue())
                    self.assertIn('0x00000000abcd1234',output.getvalue())
                    self.assertIn('Source reconstruction: disabled',output.getvalue())
