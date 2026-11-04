"""Owned assembled windows relocated for regression; no runtime/CFI claims."""
import unittest
from test_swift_error_flow import image
from airs.swift_error_flow import recover_swift_error_flow

SCALAR=(0xb40000b5,0xaa1503e0,0x94000038,0x92800000,0x14000003,
        0x52824693,0x2a1303e0,0xf9400bfe,0xf94007f5,0xf84207f3,0xd65f03c0)
SPLIT=(0xb40000b5,0xaa1503e0,0x94000027,0x92800020,0x14000002,
       0x528acf00,0xa94057f3,0x910003bf,0xf94007fe,0xf84107fd,0xd65f03c0)
SYMBOL='_$s13AIRSEpilogues8validateyyKF'


def report(words):
    return recover_swift_error_flow(image(words,symbol=SYMBOL),include_error_regions=True,
        validate_region_entries=True,include_structured_presentation=True)

class OwnedEpilogueFixtureTests(unittest.TestCase):
    def test_assembled_w_copy_scalar_and_postload_outcome(self):
        call=report(SCALAR)['calls'][0]
        self.assertEqual(call['return_choice']['success']['constant_bits'],'0x0000000000001234')
        self.assertEqual(call['return_choice']['error']['constant_bits'],'0xffffffffffffffff')
        self.assertEqual(call['error_region']['success_interval']['instructions'][1]['kind'],'wmov')
        tail=call['error_region']['shared_epilogue']
        self.assertEqual(tail['instructions'][2]['sp_writeback_bytes'],32)
        self.assertFalse(tail['restore_state_proven'])

    def test_assembled_split_frame_outcome(self):
        call=report(SPLIT)['calls'][0]
        self.assertEqual(call['return_choice']['success']['constant_bits'],'0x0000000000005678')
        self.assertEqual(call['return_choice']['error']['constant_bits'],'0xfffffffffffffffe')
        tail=call['error_region']['shared_epilogue']
        self.assertEqual([w['word'] for w in tail['instructions'][1:]],['0x910003bf','0xf94007fe','0xf84107fd','0xd65f03c0'])
        self.assertEqual(tail['instructions'][3]['sp_writeback_bytes'],16)
        self.assertFalse(tail['restore_state_proven'])

    def test_removed_w_seed_does_not_turn_copy_into_literal(self):
        call=report(SCALAR[:5]+(0xd503201f,)+SCALAR[6:])['calls'][0]
        self.assertEqual(call['presentation']['status'],'eligible_structural_only')
        self.assertEqual(call['success_constant']['reason'],'success_x0_constant_not_known')
        self.assertEqual(call['return_choice']['status'],'unresolved')

    def test_wrong_split_pop_delta_is_not_an_equivalent_tail(self):
        call=report(SPLIT[:9]+(0xf84207fd,)+SPLIT[10:])['calls'][0]
        self.assertEqual(call['error_region']['status'],'declined')
        self.assertEqual(call['return_choice']['status'],'unresolved')

    def test_added_postload_side_entry_withholds_choice(self):
        source=4+len(SCALAR)*4;target=4+9*4
        branch=0x14000000|(((target-source)//4)&0x3ffffff)
        call=report(SCALAR+(branch,))['calls'][0]
        self.assertEqual(call['presentation']['status'],'blocked')
        self.assertEqual(call['return_choice']['status'],'unresolved')

    def test_cli_retains_assembled_outcomes_and_writeback_without_proof(self):
        import contextlib,io,json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from airs.cli import main
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            for index,words in enumerate((SCALAR,SPLIT)):
                source=Path(folder)/('assembled-'+str(index)+'.macho')
                source.write_bytes(image(words,symbol=SYMBOL).data)
                options=['swift-error-flow',str(source),'--include-error-regions','--validate-region-entries','--include-structured-presentation']
                for format in ('json','text'):
                    output=io.StringIO()
                    with contextlib.redirect_stdout(output):self.assertEqual(main(options+['--format',format]),0)
                    if format=='json':
                        call=json.loads(output.getvalue())['calls'][0]
                        self.assertEqual(call['return_choice']['status'],'structural_choice_candidate')
                        self.assertFalse(call['error_region']['shared_epilogue']['restore_state_proven'])
                    else:
                        self.assertIn('sp_writeback_bytes',output.getvalue())
                        self.assertIn('Source reconstruction: disabled',output.getvalue())
