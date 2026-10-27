"""Owned compiler-emitted windows, relocated in synthetic images; never executed."""
import unittest
from test_swift_error_flow import image
from airs.swift_error_flow import recover_swift_error_flow

# OwnedWordOutcomes.swift, optimized ARM64. Relative branches are retained;
# caller identity/admission of these synthetic images is separate from the dylib.
WORDS = (0xb40000d5,0xaa1503e0,0x94000082,0x528acf00,0x72a24680,
         0x14000003,0x5299bde0,0x72b13560,0xa9427bfd,0xa94157f6,
         0x9100c3ff,0xd65f03c0)
WIDTH = (0xb40000b5,0xaa1503e0,0x94000070,0x92800000,0x14000002,
         0x12800000,0xa9427bfd,0xa94157f6,0x9100c3ff,0xd65f03c0)
SYMBOL = '_$s15AIRSWordChoices8validateyyKF'


def report(words):
    return recover_swift_error_flow(image(words,symbol=SYMBOL),include_error_regions=True,
        validate_region_entries=True,include_structured_presentation=True)

class OwnedWordOutcomeTests(unittest.TestCase):
    def test_compiler_word_literal_pair_is_preserved(self):
        call=report(WORDS)['calls'][0]
        self.assertEqual(call['return_choice']['success']['constant_bits'],'0x0000000089abcdef')
        self.assertEqual(call['return_choice']['error']['constant_bits'],'0x0000000012345678')
        self.assertEqual([w['kind'] for w in call['error_region']['success_interval']['instructions']],['wmovz','wmovk'])

    def test_compiler_width_pair_is_not_conflated(self):
        choice=report(WIDTH)['calls'][0]['return_choice']
        self.assertEqual(choice['success']['constant_bits'],'0x00000000ffffffff')
        self.assertEqual(choice['error']['constant_bits'],'0xffffffffffffffff')
        self.assertFalse(choice['same_constant_bits'])
        self.assertFalse(choice['source_reconstruction_allowed'])

    def test_removed_error_seed_does_not_become_partial_known_value(self):
        call=report(WORDS[:3]+(0xd503201f,)+WORDS[4:])['calls'][0]
        self.assertEqual(call['presentation']['status'],'eligible_structural_only')
        self.assertEqual(call['error_constant']['reason'],'error_x0_constant_not_known')
        self.assertEqual(call['return_choice']['status'],'unresolved')

    def test_changed_width_bit_changes_bits_instead_of_only_label(self):
        choice=report(WIDTH[:5]+(0x92800000,)+WIDTH[6:])['calls'][0]['return_choice']
        self.assertEqual(choice['success']['constant_bits'],'0xffffffffffffffff')
        self.assertTrue(choice['same_constant_bits'])

    def test_added_direct_success_entry_conflict_withholds_choice(self):
        source=4+len(WORDS)*4;target=4+6*4
        branch=0x14000000|(((target-source)//4)&0x3ffffff)
        call=report(WORDS+(branch,))['calls'][0]
        self.assertEqual(call['presentation']['status'],'blocked')
        self.assertEqual(call['return_choice']['status'],'unresolved')

    def test_cli_keeps_compiler_width_patterns_and_source_disabled(self):
        import contextlib,io,json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from airs.cli import main
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source=Path(folder)/'owned-width-window.macho'
            source.write_bytes(image(WIDTH,symbol=SYMBOL).data)
            options=['swift-error-flow',str(source),'--include-error-regions','--validate-region-entries','--include-structured-presentation']
            for format in ('json','text'):
                output=io.StringIO()
                with contextlib.redirect_stdout(output):self.assertEqual(main(options+['--format',format]),0)
                if format=='json':
                    choice=json.loads(output.getvalue())['calls'][0]['return_choice']
                    self.assertFalse(choice['same_constant_bits'])
                else:
                    self.assertIn('0x00000000ffffffff',output.getvalue())
                    self.assertIn('0xffffffffffffffff',output.getvalue())
                    self.assertIn('Source reconstruction: disabled',output.getvalue())
