"""Known-seeded 64-bit MOVK literals on bounded Swift outcome arms."""
import unittest
from test_swift_success_constants import success


def movz(value, shift=0, rd=0):
    return 0xd2800000 | ((shift // 16) << 21) | (value << 5) | rd

def movk(value, shift=0, rd=0):
    return 0xf2800000 | ((shift // 16) << 21) | (value << 5) | rd

class MovkOutcomeFirstTests(unittest.TestCase):
    def test_complete_seed_then_four_lane_literal(self):
        call = success((movz(0x1234), movk(0x5678,16), movk(0x9abc,32), movk(0xdef0,48)))['calls'][0]
        self.assertEqual(call['success_constant']['status'], 'constant_register_candidate')
        self.assertEqual(call['success_constant']['constant_bits'], '0xdef09abc56781234')
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')

class MovkOutcomeBoundaryTests(unittest.TestCase):
    def test_movn_seed_and_replacement_clear_old_lane_bits(self):
        call = success((0x92800000, movk(0,16), movk(0x1234,16)))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0xffffffff1234ffff')

    def test_bare_updates_never_create_a_known_value(self):
        for body in ((movk(1),), tuple(movk(i+1,i*16) for i in range(4))):
            call = success(body)['calls'][0]
            self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
            self.assertEqual(call['success_constant']['reason'], 'success_x0_constant_not_known')
            self.assertEqual(call['success_result']['status'], 'declined')

    def test_unknown_overwrite_then_movk_stays_unknown(self):
        result = success((movz(1), 0xaa1303e0, movk(2,16)))['calls'][0]['success_constant']
        self.assertEqual(result['reason'], 'success_x0_constant_not_known')

    def test_movk_on_saved_result_kills_its_alias(self):
        call = success((0xaa0003f3, movk(1,rd=19), 0xaa1303e0))['calls'][0]
        self.assertEqual(call['success_result']['status'], 'declined')
        self.assertEqual(call['success_constant']['status'], 'declined')

    def test_other_register_update_does_not_destroy_x0_result(self):
        call = success((movk(1,rd=19),))['calls'][0]
        self.assertEqual(call['success_result']['status'], 'preserved_register_candidate')

    def test_zero_register_update_is_discarded(self):
        result = success((movz(42), movk(0xffff,48,rd=31)))['calls'][0]['success_constant']
        self.assertEqual(result['constant_bits'], '0x000000000000002a')

    def test_error_arm_can_build_a_full_literal_after_call(self):
        from test_swift_error_constants import error_arm
        call = error_arm((0x94000100, movz(0x1234), movk(0xabcd,48)))['calls'][0]
        self.assertEqual(call['error_constant']['constant_bits'], '0xabcd000000001234')
        self.assertFalse(call['error_constant']['call_return_proven'])
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')

    def test_opaque_call_invalidates_seed_before_partial_update(self):
        from test_swift_error_constants import error_arm
        result = error_arm((movz(1), 0x94000100, movk(2,16)))['calls'][0]['error_constant']
        self.assertEqual(result['reason'], 'error_x0_constant_not_known')

    def test_w_reserved_forms_and_postcall_updates_remain_refused(self):
        from test_swift_success_result import report
        from test_swift_shared_epilogue import WORDS
        for word in (0x72c00020, 0x72e00020):
            self.assertEqual(success((movz(1),word))['calls'][0]['success_constant']['status'], 'declined')
        call = report((movk(1,rd=19),) + WORDS)['calls'][0]
        self.assertEqual(call['status'], 'declined')

    def test_exact_arm_and_tail_limits_with_updates(self):
        from test_swift_success_result import NOP
        body=(movz(1),) + (movk(2,16),)*7
        result=success(body,(NOP,)*7+(0xd65f03c0,),error_call=0x94000100)['calls'][0]['success_constant']
        self.assertEqual(result['status'],'constant_register_candidate')
        self.assertEqual(len(result['instructions']),16)
        self.assertEqual(success(body+(movk(3,32),),error_call=0x94000100)['calls'][0]['success_constant']['status'],'declined')

class MovkOutcomeCLIControls(unittest.TestCase):
    def test_cli_retains_full_literal_and_raw_updates(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from test_swift_error_flow import image
        from test_swift_shared_epilogue import WORDS
        from airs.cli import main
        body=(movz(0x1234),movk(0xabcd,48))
        words=WORDS[:4]+(0x14000003,)+body+WORDS[6:]
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source=Path(folder)/'movk-outcomes.macho'
            source.write_bytes(image(words).data)
            options=['swift-error-flow',str(source),'--include-error-regions','--validate-region-entries','--include-structured-presentation']
            for format in ('json','text'):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(options+['--format',format]),0)
                if format=='json':
                    value=json.loads(output.getvalue())
                    self.assertEqual(value['calls'][0]['success_constant']['constant_bits'],'0xabcd000000001234')
                    self.assertEqual(value['error_region_model_version'],'swift-sync-error-region-v22')
                else:
                    self.assertIn('0xabcd000000001234',output.getvalue())
                    self.assertIn('xmovk',output.getvalue())
                    self.assertIn('Source reconstruction: disabled',output.getvalue())

class MovkOutcomeForwardLayoutTests(unittest.TestCase):
    def test_updates_on_both_forward_layout_arms(self):
        from test_swift_success_result import report
        words=(0xb5000095,movz(0x1234),movk(0x5678,16),0x14000003,
               0x92800000,movk(0xabcd,48),0xd65f03c0)
        call=report(words)['calls'][0]
        self.assertEqual(call['error_region']['layout'],'success_fallthrough_error_forward')
        self.assertEqual(call['success_constant']['constant_bits'],'0x0000000056781234')
        self.assertEqual(call['error_constant']['constant_bits'],'0xabcdffffffffffff')
        self.assertEqual(call['return_choice']['status'],'structural_choice_candidate')
        self.assertFalse(call['return_choice']['source_reconstruction_allowed'])
