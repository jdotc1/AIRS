"""Terminal scalar SP post-index loads; explicit writeback, no frame proof."""
import unittest
from test_swift_scalar_restore_tail import with_tail


def pop(rd=19,delta=16,rn=31):
    return 0xf8400400 | ((delta&0x1ff)<<12) | (rn<<5) | rd

class PostScalarFirstTests(unittest.TestCase):
    def test_scalar_postindex_then_ret_retains_writeback_evidence(self):
        call=with_tail((pop(),0xd65f03c0))['calls'][0]
        self.assertEqual(call['success_result']['status'],'preserved_register_candidate')
        tail=call['error_region']['shared_epilogue']
        self.assertEqual(tail['instructions'][0]['kind'],'xldr_post')
        self.assertEqual(tail['instructions'][0]['sp_writeback_bytes'],16)
        self.assertFalse(tail['restore_state_proven'])

class PostScalarBoundaryTests(unittest.TestCase):
    def test_saved_register_and_positive_delta_boundaries(self):
        for rd in (19,30):
            for delta in (16,240):
                call=with_tail((pop(rd,delta),0xd65f03c0))['calls'][0]
                self.assertEqual(call['success_result']['status'],'preserved_register_candidate')
                self.assertEqual(call['error_region']['shared_epilogue']['instructions'][0]['sp_writeback_bytes'],delta)

    def test_zero_negative_unaligned_and_outside_delta_refuse(self):
        for delta in (0,-16,-256,8,248,255):
            self.assertEqual(with_tail((pop(delta=delta),0xd65f03c0))['calls'][0]['success_result']['status'],'declined')

    def test_result_volatile_zr_nonsp_w_store_and_preindex_refuse(self):
        for word in (pop(0),pop(18),pop(31),pop(rn=29),pop()&~(1<<30),pop()&~(1<<22),pop()|(1<<11)):
            self.assertEqual(with_tail((word,0xd65f03c0))['calls'][0]['success_result']['status'],'declined')

    def test_adapter_retains_signed_offset_and_original_word(self):
        from airs.swift_error_flow import decode_instruction
        value=decode_instruction(pop(30,-16),0x1000)
        self.assertEqual((value.kind,value.word,value.address,value.rd,value.rn,value.immediate,value.addressing),
                         ('xldr_post',pop(30,-16),0x1000,30,31,-16,'post'))

    def test_ret_must_immediately_follow_postload(self):
        from test_swift_success_result import NOP
        for following in (NOP,pop(),0xd65f0000,0xffffffff):
            self.assertEqual(with_tail((pop(),following,0xd65f03c0))['calls'][0]['success_result']['status'],'declined')

    def test_exact_eight_word_tail_and_one_word_over(self):
        from test_swift_success_result import NOP
        call=with_tail((NOP,)*6+(pop(),0xd65f03c0))['calls'][0]
        self.assertEqual(call['success_result']['status'],'preserved_register_candidate')
        self.assertEqual(len(call['error_region']['shared_epilogue']['instructions']),8)
        self.assertEqual(with_tail((NOP,)*7+(pop(),0xd65f03c0))['calls'][0]['success_result']['status'],'declined')

    def test_unsigned_scalar_and_pair_restores_can_precede_terminal_pop(self):
        from test_swift_scalar_restore_tail import load
        call=with_tail((load(19),0xa9427bfd,pop(20),0xd65f03c0))['calls'][0]
        self.assertEqual(call['success_result']['status'],'preserved_register_candidate')
        self.assertFalse(call['error_region']['shared_epilogue']['restore_state_proven'])

    def test_forward_layout_and_success_entry_fallback(self):
        from test_swift_forward_error_arm import WORDS as forward
        from test_swift_success_return_tail import WORDS as direct
        from test_swift_success_result import report
        for words in (forward[:6]+(pop(),0xd65f03c0),direct[:-1]+(pop(),0xd65f03c0)):
            call=report(words)['calls'][0]
            self.assertEqual(call['return_choice']['status'],'structural_choice_candidate')
            self.assertFalse(call['return_choice']['runtime_value_proven'])

    def test_tail_side_entry_and_partial_prefix_withhold(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        from test_swift_success_result import report,NOP
        from test_swift_shared_epilogue import WORDS
        words=WORDS[:5]+(NOP,pop(),0xd65f03c0)
        self.assertEqual(report(words+(0x17fffffe,))['calls'][0]['presentation']['status'],'blocked')
        for limit in (8,9):
            call=report(words,limits=replace(DEFAULT_LIMITS,max_instructions_per_function=limit))['calls'][0]
            self.assertEqual(call['success_result']['status'],'declined')

    def test_scalar_postload_stays_outside_arm_and_postcall_subsets(self):
        from test_swift_success_constants import success
        from test_swift_success_result import report
        from test_swift_shared_epilogue import WORDS
        self.assertEqual(success((pop(),))['calls'][0]['success_constant']['status'],'declined')
        self.assertEqual(report((pop(),)+WORDS)['calls'][0]['status'],'declined')

class PostScalarCLIControls(unittest.TestCase):
    def test_cli_records_postindex_word_and_sp_writeback_without_proof(self):
        import contextlib,io,json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from test_swift_error_flow import image
        from test_swift_success_result import NOP
        from test_swift_shared_epilogue import WORDS
        from airs.cli import main
        words=WORDS[:5]+(NOP,pop(),0xd65f03c0)
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source=Path(folder)/'postindexed-scalar-tail.macho'
            source.write_bytes(image(words).data)
            options=['swift-error-flow',str(source),'--include-error-regions','--validate-region-entries','--include-structured-presentation']
            for format in ('json','text'):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):self.assertEqual(main(options+['--format',format]),0)
                if format=='json':
                    value=json.loads(output.getvalue());tail=value['calls'][0]['error_region']['shared_epilogue']
                    self.assertEqual(tail['instructions'][0]['sp_writeback_bytes'],16)
                    self.assertFalse(tail['restore_state_proven'])
                    self.assertEqual(value['region_incoming_model_version'],'swift-region-direct-entries-v7')
                else:
                    self.assertIn('0xf84107f3',output.getvalue())
                    self.assertIn('sp_writeback_bytes',output.getvalue())
                    self.assertIn('Source reconstruction: disabled',output.getvalue())
