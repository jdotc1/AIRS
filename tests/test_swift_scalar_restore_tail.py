"""Bounded scalar SP restore shapes, never frame/state/runtime proof."""
import unittest
from test_swift_success_result import report,NOP
from test_swift_shared_epilogue import WORDS


def load(rd=19,offset=16,rn=31):
    return 0xf9400000 | ((offset//8)<<10) | (rn<<5) | rd

def with_tail(tail):
    return report(WORDS[:5]+(NOP,)+tuple(tail))

class ScalarRestoreFirstTests(unittest.TestCase):
    def test_scalar_saved_register_restores_preserve_x0_candidate(self):
        value=with_tail((load(19),load(30,8),0x9100c3ff,0xd65f03c0))
        call=value['calls'][0]
        self.assertEqual(call['presentation']['status'],'eligible_structural_only')
        self.assertEqual(call['success_result']['status'],'preserved_register_candidate')
        self.assertEqual([w['kind'] for w in call['error_region']['shared_epilogue']['instructions']],['xldr','xldr','add','ret'])
        self.assertFalse(call['error_region']['shared_epilogue']['restore_state_proven'])

class ScalarRestoreBoundaryTests(unittest.TestCase):
    def test_first_last_saved_register_and_offset_edges(self):
        for rd in (19,30):
            for offset in (0,4096):
                call=with_tail((load(rd,offset),0xd65f03c0))['calls'][0]
                self.assertEqual(call['success_result']['status'],'preserved_register_candidate')
        self.assertEqual(with_tail((load(19,4104),0xd65f03c0))['calls'][0]['success_result']['status'],'declined')

    def test_result_volatile_zero_and_frame_base_loads_refuse(self):
        for word in (load(0),load(18),load(31),load(19,rn=29),0xb9400bf3,0xf8410ff3):
            self.assertEqual(with_tail((word,0xd65f03c0))['calls'][0]['success_result']['status'],'declined')

    def test_mixed_pair_scalar_and_stack_adjustment_tail(self):
        call=with_tail((load(19),0xa9427bfd,0x9100c3ff,0xd65f03c0))['calls'][0]
        self.assertEqual(call['success_result']['status'],'preserved_register_candidate')
        self.assertFalse(call['error_region']['shared_epilogue']['restore_state_proven'])

    def test_exact_eight_word_tail_and_overflow(self):
        call=with_tail((load(19),)*7+(0xd65f03c0,))['calls'][0]
        self.assertEqual(call['success_result']['status'],'preserved_register_candidate')
        self.assertEqual(len(call['error_region']['shared_epilogue']['instructions']),8)
        call=with_tail((load(19),)*8+(0xd65f03c0,))['calls'][0]
        self.assertEqual(call['success_result']['status'],'declined')

    def test_missing_or_nonstandard_return_withholds(self):
        for tail in ((load(19),0xd65f0000),(load(19),0xffffffff),(load(19),0x14000000)):
            self.assertEqual(with_tail(tail)['calls'][0]['success_result']['status'],'declined')

    def test_forward_layout_scalar_tail(self):
        from test_swift_forward_error_arm import WORDS as forward
        value=report(forward[:6]+(load(19),0xd65f03c0))
        call=value['calls'][0]
        self.assertEqual(call['return_choice']['status'],'structural_choice_candidate')
        self.assertEqual(call['error_region']['layout'],'success_fallthrough_error_forward')
        self.assertFalse(call['return_choice']['runtime_value_proven'])

    def test_success_entry_scalar_tail_composes_with_error_literal(self):
        from test_swift_success_return_tail import WORDS as direct
        call=report(direct[:-1]+(load(19),0xd65f03c0))['calls'][0]
        self.assertEqual(call['success_result']['return_tail_layout'],'success_entry')
        self.assertEqual(call['return_choice']['status'],'structural_choice_candidate')
        self.assertEqual(call['return_choice']['success']['kind'],'call_result')

    def test_side_entry_into_scalar_tail_withholds(self):
        words=WORDS[:5]+(NOP,load(19),0xd65f03c0)
        # Branch after the return into the scalar tail entry.
        call=report(words+(0x17fffffe,))['calls'][0]
        self.assertEqual(call['presentation']['status'],'blocked')
        self.assertEqual(call['return_choice']['status'],'unresolved')

    def test_partial_caller_scan_does_not_prove_entry_absence(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        words=WORDS[:5]+(NOP,load(19),0xd65f03c0)
        call=report(words,limits=replace(DEFAULT_LIMITS,max_instructions_per_function=9))['calls'][0]
        self.assertEqual(call['success_result']['status'],'declined')

    def test_saved_copy_metadata_is_before_scalar_restore(self):
        # Result is copied through x19, then x19 is restored from SP in the tail.
        words=(0xaa0003f3,0xaa1f03e0)+WORDS[:5]+(0xaa1303e0,load(19),0xd65f03c0)
        call=report(words)['calls'][0]
        self.assertEqual(call['success_result']['status'],'copied_register_candidate')
        self.assertEqual(call['success_result']['result_registers_before_tail'],['x0','x19'])
        self.assertFalse(call['success_result']['runtime_value_proven'])

class ScalarRestoreCLIControls(unittest.TestCase):
    def test_cli_retains_scalar_load_word_and_unproven_restore_flag(self):
        import contextlib,io,json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from test_swift_error_flow import image
        from airs.cli import main
        words=WORDS[:5]+(NOP,load(19),0xd65f03c0)
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source=Path(folder)/'scalar-restore-tail.macho'
            source.write_bytes(image(words).data)
            options=['swift-error-flow',str(source),'--include-error-regions','--validate-region-entries','--include-structured-presentation']
            for format in ('json','text'):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):self.assertEqual(main(options+['--format',format]),0)
                if format=='json':
                    value=json.loads(output.getvalue());call=value['calls'][0]
                    self.assertEqual(call['success_result']['status'],'preserved_register_candidate')
                    self.assertFalse(call['error_region']['shared_epilogue']['restore_state_proven'])
                    self.assertEqual(value['error_region_model_version'],'swift-sync-error-region-v23')
                else:
                    self.assertIn('0xf9400bf3',output.getvalue())
                    self.assertIn('xldr',output.getvalue())
                    self.assertIn('Source reconstruction: disabled',output.getvalue())
