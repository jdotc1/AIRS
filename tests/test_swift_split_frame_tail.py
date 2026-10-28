"""Exact FP reset plus split LR/FP scalar restore; structural evidence only."""
import unittest
from test_swift_scalar_restore_tail import load,with_tail
from test_swift_postindexed_scalar_tail import pop

RESET=0x910003bf
RETURN=0xd65f03c0
TAIL=(RESET,load(30,8),pop(29,16),RETURN)

class SplitFrameFirstTests(unittest.TestCase):
    def test_exact_split_frame_restore_tail_is_recognized(self):
        call=with_tail(TAIL)['calls'][0]
        self.assertEqual(call['success_result']['status'],'preserved_register_candidate')
        tail=call['error_region']['shared_epilogue']
        self.assertEqual([row['word'] for row in tail['instructions']],[f'0x{word:08x}' for word in TAIL])
        self.assertEqual(tail['instructions'][2]['sp_writeback_bytes'],16)
        self.assertFalse(tail['restore_state_proven'])

class SplitFrameBoundaryTests(unittest.TestCase):
    def test_reset_encoding_remains_exact(self):
        for reset in (0x914003bf,0x910043bf,0x110003bf,0x910003fd):
            self.assertEqual(with_tail((reset,)+TAIL[1:])['calls'][0]['success_result']['status'],'declined')

    def test_lr_load_register_offset_width_and_base_remain_exact(self):
        for first in (load(29,8),load(30,0),load(30,16),load(30,8,rn=29),load(30,8)&~(1<<30),load(30,8)&~(1<<22)):
            self.assertEqual(with_tail((RESET,first)+TAIL[2:])['calls'][0]['success_result']['status'],'declined')

    def test_fp_pop_register_increment_and_base_remain_exact(self):
        for second in (pop(30),pop(19),pop(29,32),pop(29,0),pop(29,-16),pop(29,rn=29)):
            self.assertEqual(with_tail(TAIL[:2]+(second,RETURN))['calls'][0]['success_result']['status'],'declined')

    def test_intervening_words_swapped_loads_and_return_variants_refuse(self):
        from test_swift_success_result import NOP
        for words in ((RESET,NOP)+TAIL[1:],TAIL[:2]+(NOP,)+TAIL[2:],TAIL[:3]+(NOP,RETURN),
                      (RESET,TAIL[2],TAIL[1],RETURN),TAIL[:3]+(0xd65f0000,),TAIL[:3]+(0xffffffff,)):
            self.assertEqual(with_tail(words)['calls'][0]['success_result']['status'],'declined')

    def test_exact_eight_word_tail_and_overflow(self):
        from test_swift_success_result import NOP
        call=with_tail((NOP,)*4+TAIL)['calls'][0]
        self.assertEqual(call['success_result']['status'],'preserved_register_candidate')
        self.assertEqual(len(call['error_region']['shared_epilogue']['instructions']),8)
        self.assertEqual(with_tail((NOP,)*5+TAIL)['calls'][0]['success_result']['status'],'declined')

    def test_all_lookahead_words_must_fit_scanned_prefix(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        from test_swift_success_result import report,NOP
        from test_swift_shared_epilogue import WORDS
        for limit in (8,9,10,11):
            call=report(WORDS[:5]+(NOP,)+TAIL,limits=replace(DEFAULT_LIMITS,max_instructions_per_function=limit))['calls'][0]
            self.assertEqual(call['success_result']['status'],'declined')
            if limit<11:self.assertEqual(call['error_region']['status'],'declined')

    def test_both_arm_layout_and_success_entry_fallback(self):
        from test_swift_forward_error_arm import WORDS as forward
        from test_swift_success_return_tail import WORDS as direct
        from test_swift_success_result import report
        for words in (forward[:6]+TAIL,direct[:-1]+TAIL):
            call=report(words)['calls'][0]
            self.assertEqual(call['return_choice']['status'],'structural_choice_candidate')
            self.assertFalse(call['return_choice']['runtime_value_proven'])

    def test_side_entries_to_each_split_tail_word_block(self):
        from test_swift_success_result import report,NOP
        from test_swift_shared_epilogue import WORDS
        words=WORDS[:5]+(NOP,)+TAIL;source=4+len(words)*4
        for index in range(4):
            target=28+index*4;branch=0x14000000|(((target-source)//4)&0x3ffffff)
            call=report(words+(branch,))['calls'][0]
            self.assertEqual(call['presentation']['status'],'blocked')
            self.assertEqual(call['return_choice']['status'],'unresolved')

    def test_unsigned_restore_prefix_and_old_pair_tail_still_compose(self):
        call=with_tail((load(19),)+TAIL)['calls'][0]
        self.assertEqual(call['success_result']['status'],'preserved_register_candidate')
        self.assertFalse(call['error_region']['shared_epilogue']['restore_state_proven'])
        call=with_tail((RESET,0xa8c17bfd,RETURN))['calls'][0]
        self.assertEqual(call['success_result']['status'],'preserved_register_candidate')

    def test_no_result_or_frame_proofs_are_promoted(self):
        call=with_tail(TAIL)['calls'][0]
        for key in ('runtime_value_proven','exclusive_path_proven','caller_return_type_proven','source_reconstruction_allowed'):
            self.assertFalse(call['success_result'][key])
        self.assertFalse(call['error_region']['join_reachability_proven'])
        self.assertFalse(call['error_region']['shared_epilogue']['restore_state_proven'])

class SplitFrameCLIControls(unittest.TestCase):
    def test_cli_retains_exact_split_words_and_writeback(self):
        import contextlib,io,json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from test_swift_error_flow import image
        from test_swift_success_result import NOP
        from test_swift_shared_epilogue import WORDS
        from airs.cli import main
        words=WORDS[:5]+(NOP,)+TAIL
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source=Path(folder)/'split-frame-tail.macho'
            source.write_bytes(image(words).data)
            options=['swift-error-flow',str(source),'--include-error-regions','--validate-region-entries','--include-structured-presentation']
            for format in ('json','text'):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):self.assertEqual(main(options+['--format',format]),0)
                if format=='json':
                    value=json.loads(output.getvalue());tail=value['calls'][0]['error_region']['shared_epilogue']
                    self.assertEqual(tail['instructions'][2]['sp_writeback_bytes'],16)
                    self.assertFalse(tail['restore_state_proven'])
                    self.assertEqual(value['error_region_model_version'],'swift-sync-error-region-v23')
                else:
                    for word in TAIL:self.assertIn(f'0x{word:08x}',output.getvalue())
                    self.assertIn('Source reconstruction: disabled',output.getvalue())
