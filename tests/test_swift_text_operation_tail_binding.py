"""Reconcile standalone success-operation return-tail evidence."""
from copy import deepcopy
import unittest

from airs.swift_error_text import render_swift_error_text
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_literal_outcome_summary import report
from test_swift_shared_epilogue import WORDS

OPERATION = 'Success operation (structural; runtime unproven):'
PAIR = 'Recorded adjusted-result/error outcomes (structural; runtime unproven):'


class OperationTailBindingTests(unittest.TestCase):
    def test_stale_or_malformed_tail_suffix_withholds_operation(self):
        for name, layout in LAYOUTS:
            original = report(layout((0x91001400,)))
            self.assertIn(OPERATION, render_swift_error_text(original))
            for change in ('word', 'kind', 'pc', 'phase', 'missing', 'extra', 'early'):
                value = deepcopy(original); outcome = value['calls'][0]['success_result']; rows = outcome['instructions']
                if change == 'word': rows[-1]['word'] = '0xd503201f'
                elif change == 'kind': rows[-1]['kind'] = 'nop'
                elif change == 'pc': rows[-1]['pc'] = '0x0'
                elif change == 'phase': rows[-1]['phase'] = 'success'
                elif change == 'missing': rows.pop()
                elif change == 'extra': rows[-1]['extra'] = True
                else: rows[0]['phase'] = 'return_tail'
                with self.subTest(layout=name, change=change):
                    text = render_swift_error_text(value)
                    self.assertNotIn(OPERATION, text); self.assertNotIn(PAIR, text)
                    self.assertIn('Result-path instruction:', text)

    def test_synchronized_nonreturn_tail_is_refused(self):
        for name, layout in LAYOUTS:
            value = report(layout((0x91001400,))); call = value['calls'][0]
            for tail in (call['error_region']['shared_epilogue'], call['presentation']['display_plan']['shared_epilogue']):
                tail['instructions'][-1].update(word='0xd503201f', kind='nop')
            call['success_result']['instructions'][-1].update(word='0xd503201f', kind='nop')
            with self.subTest(layout=name):
                text = render_swift_error_text(value)
                self.assertNotIn(OPERATION, text)
                self.assertIn('Result-path instruction:', text)

    def test_valid_add_sub_and_eight_word_tail_do_not_require_error_outcome(self):
        for name, layout in LAYOUTS:
            for word in (0x91001400, 0xd1001400):
                value = report(layout((word,))); del value['calls'][0]['error_constant']
                with self.subTest(layout=name, word=word):
                    self.assertIn(OPERATION, render_swift_error_text(value))
        value = report(WORDS[:5] + (0x91001400,) + (0xd503201f,) * 7 + (0xd65f03c0,))
        del value['calls'][0]['error_constant']
        self.assertIn(OPERATION, render_swift_error_text(value))

    def test_recorded_restore_shapes_and_typed_writeback(self):
        from test_swift_postindexed_scalar_tail import pop
        from test_swift_split_frame_tail import TAIL
        for tail in ((pop(), 0xd65f03c0), TAIL, (0xa9427bfd, 0x9100c3ff, 0xd65f03c0)):
            value = report(WORDS[:5] + (0x91001400,) + tail)
            del value['calls'][0]['error_constant']
            with self.subTest(tail=tail):
                self.assertIn(OPERATION, render_swift_error_text(value))
        value = report(WORDS[:5] + (0x91001400,) + (pop(), 0xd65f03c0))
        result = value['calls'][0]['success_result']
        for row in result['instructions']:
            if 'sp_writeback_bytes' in row:
                row['sp_writeback_bytes'] = float(row['sp_writeback_bytes'])
                break
        else:
            self.fail('Expected a recorded scalar writeback')
        self.assertNotIn(OPERATION, render_swift_error_text(value))
