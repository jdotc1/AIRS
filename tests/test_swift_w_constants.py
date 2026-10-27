"""W move-wide seeds zero-extend into X registers; local Swift adapter only."""
import unittest
from test_swift_success_constants import success


def wide(value, shift=0, rd=0, negate=False):
    return (0x12800000 if negate else 0x52800000) | ((shift//16)<<21) | (value<<5) | rd

class WConstantFirstTests(unittest.TestCase):
    def test_w_movn_zero_extends_not_sign_extends(self):
        call=success((wide(0,negate=True),))['calls'][0]
        self.assertEqual(call['success_constant']['status'],'constant_register_candidate')
        self.assertEqual(call['success_constant']['constant_bits'],'0x00000000ffffffff')
        self.assertEqual(call['return_choice']['status'],'structural_choice_candidate')

class WConstantBoundaryTests(unittest.TestCase):
    def test_shifted_w_movz_and_movn_patterns(self):
        for word,bits in ((wide(0x1234,16),'0x0000000012340000'),
                          (wide(0x1234,16,negate=True),'0x00000000edcbffff')):
            self.assertEqual(success((word,))['calls'][0]['success_constant']['constant_bits'],bits)

    def test_w_seed_clears_prior_upper_bits(self):
        result=success((0x92800000,wide(42)))['calls'][0]['success_constant']
        self.assertEqual(result['constant_bits'],'0x000000000000002a')

    def test_local_adapter_retains_word_fields_and_rejects_reserved_shifts(self):
        from airs.swift_error_flow import decode_instruction
        from airs.arm64 import ModelError
        word=wide(0x1234,16,rd=19)
        value=decode_instruction(word,0x1000)
        self.assertEqual((value.kind,value.word,value.address,value.rd,value.immediate),('wmovz',word,0x1000,19,0x12340000))
        for word in (wide(1,32),wide(1,48,negate=True),-1,1<<32):
            with self.assertRaises(ModelError):decode_instruction(word)

    def test_w_seed_can_feed_existing_x_movk_and_x_copy(self):
        from test_swift_movk_outcomes import movk
        result=success((wide(0xffff,negate=True,rd=19),movk(0xabcd,48,rd=19),0xaa1303e0))['calls'][0]['success_constant']
        self.assertEqual(result['constant_bits'],'0xabcd0000ffff0000')

    def test_w_write_kills_saved_result_alias(self):
        call=success((0xaa0003f3,wide(1,rd=19),0xaa1303e0))['calls'][0]
        self.assertEqual(call['success_result']['status'],'declined')
        self.assertEqual(call['success_constant']['constant_bits'],'0x0000000000000001')

    def test_zero_register_writes_do_not_create_sp_or_storage(self):
        result=success((wide(1,rd=31),0xaa1f03e0))['calls'][0]['success_constant']
        self.assertEqual(result['constant_bits'],'0x0000000000000000')

    def test_error_arm_uses_zero_extension_and_call_invalidation(self):
        from test_swift_error_constants import error_arm
        call=error_arm((0x94000100,wide(0,negate=True)))['calls'][0]
        self.assertEqual(call['error_constant']['constant_bits'],'0x00000000ffffffff')
        self.assertFalse(call['error_constant']['call_return_proven'])
        call=error_arm((wide(1),0x94000100))['calls'][0]
        self.assertEqual(call['error_constant']['reason'],'error_x0_constant_not_known')

    def test_forward_layout_accepts_both_w_seed_kinds(self):
        from test_swift_success_result import report
        words=(0xb5000075,wide(1),0x14000002,wide(0,negate=True),0xd65f03c0)
        call=report(words)['calls'][0]
        self.assertEqual(call['error_region']['layout'],'success_fallthrough_error_forward')
        self.assertEqual(call['return_choice']['success']['constant_bits'],'0x0000000000000001')
        self.assertEqual(call['return_choice']['error']['constant_bits'],'0x00000000ffffffff')

    def test_w_movk_postcall_seeds_and_tail_seeds_remain_outside_scope(self):
        from test_swift_success_result import report
        from test_swift_shared_epilogue import WORDS
        self.assertEqual(success((wide(1),0x72800020))['calls'][0]['success_constant']['status'],'declined')
        self.assertEqual(report((wide(1,rd=19),)+WORDS)['calls'][0]['status'],'declined')
        call=report(WORDS[:6]+(wide(1),0xd65f03c0))['calls'][0]
        self.assertEqual(call['success_constant']['status'],'declined')

    def test_exact_bound_and_overflow_keep_existing_limits(self):
        from test_swift_success_result import NOP
        result=success((wide(1),)*8,(NOP,)*7+(0xd65f03c0,),error_call=0x94000100)['calls'][0]['success_constant']
        self.assertEqual(result['status'],'constant_register_candidate')
        self.assertEqual(len(result['instructions']),16)
        self.assertEqual(success((wide(1),)*9,error_call=0x94000100)['calls'][0]['success_constant']['status'],'declined')

class WConstantCLIControls(unittest.TestCase):
    def test_cli_preserves_raw_w_word_and_zero_extended_pattern(self):
        import contextlib,io,json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from test_swift_error_flow import image
        from test_swift_shared_epilogue import WORDS
        from airs.cli import main
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source=Path(folder)/'w-constant.macho'
            source.write_bytes(image(WORDS[:5]+(wide(0,negate=True),)+WORDS[6:]).data)
            options=['swift-error-flow',str(source),'--include-error-regions','--validate-region-entries','--include-structured-presentation']
            for format in ('json','text'):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):self.assertEqual(main(options+['--format',format]),0)
                if format=='json':
                    value=json.loads(output.getvalue())
                    self.assertEqual(value['calls'][0]['success_constant']['constant_bits'],'0x00000000ffffffff')
                    self.assertEqual(value['region_incoming_model_version'],'swift-region-direct-entries-v4')
                else:
                    self.assertIn('0x12800000',output.getvalue())
                    self.assertIn('wmovn',output.getvalue())
                    self.assertIn('Source reconstruction: disabled',output.getvalue())
