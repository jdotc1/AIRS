"""Bounded terminal-safe rendering of in-process Swift structural producer output."""
from __future__ import annotations

from .report_summary_text import _BoundedText
from .swift_error_flow import MODEL, REGION_MODEL, INCOMING_MODEL, PRESENTATION_MODEL, SUCCESS_RESULT_MODEL, SUCCESS_CONSTANT_MODEL, ERROR_CONSTANT_MODEL, RETURN_CHOICE_MODEL, FLAG_ENTRY_MODEL
from .types import InputError

MAXIMUM_TEXT_BYTES = 1024 * 1024
MAX_CALL_ROWS = 32
MAX_WORD_ROWS = 16
MAX_WINDOW_ROWS = 8
MAX_ENTRY_ROWS = 16
MAX_ISSUE_ROWS = 16
MAX_LIMITATION_ROWS = 16


def render_swift_error_text(report: dict, *, maximum_bytes: int = MAXIMUM_TEXT_BYTES) -> str:
    """Render bounded producer facts without new analysis or saved-report admission.

    Full counts and source omissions remain visible. All variable values use the
    existing ASCII JSON escaping and escaped-size preflight before allocation.
    Nothing is returned until the complete bounded text has been assembled.
    """
    if type(maximum_bytes) is not int or maximum_bytes < 0:
        raise InputError('invalid_report_size_limit', 'Swift text byte limit must be a nonnegative integer')
    if (report.get('report_kind') != 'airs.swift_error_flow' or report.get('model_version') != MODEL
            or report.get('error_region_model_version') != REGION_MODEL
            or report.get('region_incoming_model_version') != INCOMING_MODEL
            or report.get('structured_presentation_model_version') != PRESENTATION_MODEL):
        raise InputError('swift_text_models', 'Swift text requires current in-process edge, region, entry and presentation models')
    if report.get('success_result_model_version') not in (None, SUCCESS_RESULT_MODEL):
        raise InputError('swift_text_models', 'Unsupported success-result evidence model')
    if report.get('success_constant_model_version') not in (None, SUCCESS_CONSTANT_MODEL):
        raise InputError('swift_text_models', 'Unsupported success-constant evidence model')
    if report.get('error_constant_model_version') not in (None, ERROR_CONSTANT_MODEL):
        raise InputError('swift_text_models', 'Unsupported error-constant evidence model')
    if report.get('return_choice_model_version') not in (None, RETURN_CHOICE_MODEL):
        raise InputError('swift_text_models', 'Unsupported return-choice evidence model')
    lines = _BoundedText(min(maximum_bytes, MAXIMUM_TEXT_BYTES))

    def line(label, value):
        lines.append(label + ': ' + lines.quoted(value))

    def rows(label, values, limit):
        for value in values[:limit]:
            line(label, value)
        line(label + ' detail rows omitted by renderer', max(0, len(values) - limit))

    lines.append('AIRS Swift error-path structural review')
    lines.append('Source reconstruction: disabled')
    lines.append('Structural candidates only; reachability, exclusive entry, call return and handler meaning remain unproven.')
    lines.append('Caller-local direct-edge checks do not exclude indirect or external entries. Calls remain opaque.')
    line('Address space', report['address_space'])
    line('Image identity (producer facts; not reverified)', report['image'])
    line('Models', {key: report[key] for key in ('model_version', 'error_region_model_version',
                                               'region_incoming_model_version', 'structured_presentation_model_version')})
    if 'success_result_model_version' in report:
        line('Success-result model', report['success_result_model_version'])
    if 'success_constant_model_version' in report:
        line('Success-constant model', report['success_constant_model_version'])
    if 'error_constant_model_version' in report:
        line('Error-constant model', report['error_constant_model_version'])
    if 'return_choice_model_version' in report:
        line('Return-choice model', report['return_choice_model_version'])
    line('Full producer summary (not filtered by displayed rows)', report['summary'])
    line('Word scan complete', report['word_scan_complete'])
    line('Call details complete', report['call_details_complete'])
    rows('Edge decline reason totals', report['reasons'], MAX_ISSUE_ROWS)
    rows('Input issue', report['input_issues'], MAX_ISSUE_ROWS)
    calls = report['calls']
    line('Retained call rows available', len(calls))
    for call in calls[:MAX_CALL_ROWS]:
        presentation = call.get('presentation')
        if (not isinstance(presentation, dict)
                or presentation.get('status') not in ('eligible_structural_only', 'blocked', 'unresolved')
                or presentation.get('source_reconstruction_allowed') is not False):
            raise InputError('swift_text_presentation', 'Missing or unsupported structural presentation result')
        lines.append('Call candidate')
        line('  Call evidence', {key: call[key] for key in ('call_pc', 'call_image_offset', 'call_word', 'caller_pc', 'callee_pc', 'status')})
        if 'callee' in call:
            line('  Callee declaration (not runtime identity)', call['callee'])
        if 'reason' in call:
            line('  Edge decline reason', call['reason'])
        if 'success_result' in call:
            if report.get('success_result_model_version') != SUCCESS_RESULT_MODEL:
                raise InputError('swift_text_models', 'Success-result evidence requires its current model')
            result = call['success_result']
            line('  Success result (selected-path register evidence only)',
                 {key: value for key, value in result.items() if key != 'instructions'})
            rows('    Result-path instruction', result.get('instructions', []), 24)
        if 'success_constant' in call:
            if report.get('success_constant_model_version') != SUCCESS_CONSTANT_MODEL:
                raise InputError('swift_text_models', 'Success-constant evidence requires its current model')
            constant = call['success_constant']
            line('  Success constant (selected-path bits only)',
                 {key: value for key, value in constant.items() if key != 'instructions'})
            rows('    Constant-path instruction', constant.get('instructions', []), 16)
        if 'error_constant' in call:
            if report.get('error_constant_model_version') != ERROR_CONSTANT_MODEL:
                raise InputError('swift_text_models', 'Error-constant evidence requires its current model')
            constant = call['error_constant']
            line('  Error constant (selected-path bits; call return unproven)',
                 {key: value for key, value in constant.items() if key != 'instructions'})
            rows('    Error-constant instruction', constant.get('instructions', []), 24)
        if 'return_choice' in call:
            if report.get('return_choice_model_version') != RETURN_CHOICE_MODEL:
                raise InputError('swift_text_models', 'Return-choice evidence requires its current model')
            choice = call['return_choice']
            line('  Return choice (structural outcomes; source disabled)', choice)
            success = choice.get('success') if isinstance(choice, dict) else None
            result = call.get('success_result')
            plan = presentation.get('display_plan')
            tail = plan.get('shared_epilogue') if isinstance(plan, dict) else None
            tail_rows = tail.get('instructions') if isinstance(tail, dict) else None
            expected_condition = {'test_pc': call.get('test_pc'), 'register': call.get('tested_register'), 'error_when': 'nonzero'}
            if call.get('test_kind') == 'cmp_zero_bcond':
                expected_condition.update({key: call.get(key) for key in ('comparison_pc', 'test_kind', 'test_condition')})
            proof_flags = ('runtime_value_proven', 'source_reconstruction_allowed', 'exclusive_path_proven',
                           'caller_return_type_proven')
            if (presentation['status'] == 'eligible_structural_only'
                    and isinstance(result, dict) and isinstance(success, dict) and isinstance(plan, dict)
                    and choice.get('status') == 'structural_choice_candidate'
                    and result.get('status') == 'adjusted_register_candidate'
                    and success.get('kind') == 'call_result_add_immediate'
                    and success.get('register') == result.get('register') == 'x0'
                    and success.get('operation') == result.get('operation') == 'add_immediate_modulo'
                    and type(success.get('bit_width')) is int and success['bit_width'] == 64
                    and type(result.get('bit_width')) is int and result['bit_width'] == 64
                    and type(success.get('immediate')) is int and 1 <= success['immediate'] <= 4095
                    and type(result.get('immediate')) is int and result['immediate'] == success['immediate']
                    and isinstance(call.get('call_pc'), str)
                    and choice.get('call_pc') == result.get('call_pc') == call['call_pc']
                    and isinstance(choice.get('return_pc'), str)
                    and choice['return_pc'] == result.get('return_pc')
                    and isinstance(tail, dict) and tail.get('restore_state_proven') is False
                    and result.get('return_tail_layout') == 'shared_epilogue'
                    and isinstance(tail_rows, list) and bool(tail_rows)
                    and isinstance(tail_rows[-1], dict) and tail_rows[-1].get('pc') == choice['return_pc']
                    and isinstance(call.get('success_pc'), str)
                    and result.get('success_pc') == plan.get('success_entry_pc') == call['success_pc']
                    and isinstance(call.get('test_pc'), str) and isinstance(call.get('tested_register'), str)
                    and isinstance(choice.get('condition'), dict)
                    and choice['condition'] == plan.get('condition') == expected_condition
                    and all(choice.get(key) is False and result.get(key) is False for key in proof_flags)
                    and choice.get('call_return_proven') is False and choice.get('handler_semantics_proven') is False):
                line('  Success operation (structural; runtime unproven)',
                     f"call result + {success['immediate']} modulo 2^64")
        line('  Recorded return edges', {key: call[key] for key in ('comparison_pc', 'test_pc', 'test_kind', 'test_condition', 'tested_register', 'success_pc', 'error_pc') if key in call})
        rows('  Post-call instruction evidence', call.get('window', []), MAX_WINDOW_ROWS)
        if 'flag_entry_validation' in call:
            if report.get('flag_entry_model_version') != FLAG_ENTRY_MODEL:
                raise InputError('swift_text_models', 'Flag-entry evidence requires its current model')
            line('  Flag-entry model', report['flag_entry_model_version'])
            entry = call['flag_entry_validation']
            line('  Flag-entry validation', {key: value for key, value in entry.items()
                                          if key not in ('unexpected_entries', 'unclassified_words')})
            rows('    Unexpected flag-window entry', entry['unexpected_entries'], MAX_ENTRY_ROWS)
            rows('    Unclassified flag-scan word', entry['unclassified_words'], MAX_ENTRY_ROWS)
        line('  Presentation', {key: presentation[key] for key in ('status', 'reason')})
        if presentation['status'] == 'eligible_structural_only':
            plan = presentation['display_plan']
            line('  Label', plan['label'])
            line('  Condition (structural)', plan['condition'])
            interval = plan['error_interval']
            line('  Error interval', {key: interval[key] for key in ('start_pc', 'end_pc_exclusive')})
            rows('    Instruction', interval['instructions'], MAX_WORD_ROWS)
            line('  Success entry', plan['success_entry_pc'])
            if 'shared_epilogue' in plan:
                line('  Shared restore/return candidate (state unproven)',
                     {key: value for key, value in plan['shared_epilogue'].items() if key != 'instructions'})
        else:
            lines.append('  Structured plan: withheld')
            region = call.get('error_region')
            if isinstance(region, dict):
                line('  Region evidence', {key: region[key] for key in ('status', 'reason', 'start_pc', 'end_pc_exclusive',
                    'join_pc', 'call_return_proven', 'join_reachability_proven') if key in region})
                rows('    Region instruction evidence', region['instructions'], MAX_WORD_ROWS)
        region = call.get('error_region', {})
        for key, label in (('success_interval', 'Success-arm'), ('shared_epilogue', 'Shared tail')):
            interval = region.get(key)
            if isinstance(interval, dict):
                line('  ' + label + ' interval evidence', {k: v for k, v in interval.items() if k != 'instructions'})
                rows('    ' + label + ' instruction', interval['instructions'], MAX_WORD_ROWS)
        entry = region.get('incoming_validation')
        if isinstance(entry, dict):
            line('  Incoming validation', {key: value for key, value in entry.items()
                                         if key not in ('unexpected_entries', 'unclassified_words')})
            rows('    Unexpected direct entry', entry['unexpected_entries'], MAX_ENTRY_ROWS)
            rows('    Unclassified word', entry['unclassified_words'], MAX_ENTRY_ROWS)
        rows('  Candidate limitation', presentation['limitations'], MAX_LIMITATION_ROWS)
    line('Retained call rows omitted by renderer', max(0, len(calls) - MAX_CALL_ROWS))
    lines.append('Renderer omissions are additional to producer omitted calls, unscanned words and truncated evidence details.')
    rows('Report limitation', report['limitations'], MAX_LIMITATION_ROWS)
    return lines.finish()
