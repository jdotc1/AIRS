"""Bounded terminal-safe rendering of in-process Swift structural producer output."""
from __future__ import annotations

import re
import struct
from types import SimpleNamespace

from .arm64 import ModelError
from .report_summary_text import _BoundedText
from .swift_error_flow import MODEL, REGION_MODEL, INCOMING_MODEL, PRESENTATION_MODEL, SUCCESS_RESULT_MODEL, SUCCESS_CONSTANT_MODEL, ERROR_CONSTANT_MODEL, RETURN_CHOICE_MODEL, FLAG_ENTRY_MODEL
from .swift_error_flow import (_adjusted_result_word, _bind_choice_call_word, _bind_choice_entry_ledgers, _bind_choice_postcall,
                               _bind_choice_result_aliases, _bind_choice_success_arm, _consistent_callee_declaration,
                               _return_choice, _shared_return_tail, decode_instruction)
from .types import InputError

MAXIMUM_TEXT_BYTES = 1024 * 1024
MAX_CALL_ROWS = 32
MAX_WORD_ROWS = 16
MAX_WINDOW_ROWS = 8
MAX_ENTRY_ROWS = 16
MAX_ISSUE_ROWS = 16
MAX_LIMITATION_ROWS = 16


def _consistent_return_choice(call: dict) -> dict | None:
    """Rebuild in-process outcome records for display, not admit saved reports."""
    choice = call.get('return_choice')
    presentation = call.get('presentation')
    if (not isinstance(choice, dict) or not isinstance(presentation, dict)
            or presentation.get('status') != 'eligible_structural_only'
            or choice.get('status') != 'structural_choice_candidate'
            or (choice.get('same_constant_bits') is not None
                and type(choice.get('same_constant_bits')) is not bool)
            or any(choice.get(key) is not False for key in ('source_reconstruction_allowed',
                'runtime_value_proven', 'exclusive_path_proven', 'caller_return_type_proven',
                'call_return_proven', 'handler_semantics_proven'))):
        return None
    try:
        rebuilt = _return_choice(call)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return None
    if rebuilt != choice:
        return None
    # Equality alone accepts integer/float widths and Boolean/integer flags.
    for path in ('success', 'error'):
        outcome = choice.get(path)
        if (not isinstance(outcome, dict)
                or (outcome.get('kind') == 'constant_bits'
                    and (type(outcome.get('bit_width')) is not int or outcome['bit_width'] != 64))):
            return None
    return rebuilt


def _bounded_error_interval_geometry(interval) -> bool:
    """Check retained interval geometry without reading or authenticating bytes."""
    if not isinstance(interval, dict):
        return False
    start_text, end_text = interval.get('start_pc'), interval.get('end_pc_exclusive')
    rows = interval.get('instructions')
    if (not isinstance(start_text, str) or re.fullmatch(r'0x[0-9a-f]{1,16}', start_text) is None
            or not isinstance(end_text, str) or not isinstance(rows, list) or not 1 <= len(rows) <= MAX_WORD_ROWS):
        return False
    try:
        start = int(start_text, 16)
    except ValueError:
        return False
    end = start + 4 * len(rows)
    if (not 0 <= start < end <= 1 << 64 or start % 4
            or start_text != hex(start) or end_text != hex(end)):
        return False
    return all(isinstance(row, dict) and row.get('pc') == hex(start + 4 * index)
               and isinstance(row.get('word'), str)
               and re.fullmatch(r'0x[0-9a-f]{8}', row['word']) is not None
               for index, row in enumerate(rows))


def _consistent_error_instruction_records(call: dict, region: dict) -> bool:
    """Reconcile bounded recorded words and metadata without reading the image."""
    try:
        rows = region['instructions']
        join_text = region['join_pc']
        if (not isinstance(join_text, str)
                or re.fullmatch(r'0x[0-9a-f]{1,16}', join_text) is None):
            return False
        join = int(join_text, 16)
        if join_text != hex(join) or join % 4:
            return False
        calls = 0
        for index, row in enumerate(rows):
            pc = int(row['pc'], 16)
            instruction = decode_instruction(int(row['word'], 16), pc)
            expected = {'pc': row['pc'], 'word': row['word'], 'kind': instruction.kind}
            if instruction.kind == 'bl':
                target = pc + instruction.immediate
                if not 0 <= target < 1 << 64 or target % 4:
                    return False
                expected.update(call_target_pc=hex(target), semantics='opaque_call')
                calls += 1
            elif instruction.kind == 'b':
                if (index != len(rows) - 1 or pc + instruction.immediate != join
                        or region.get('layout') == 'success_fallthrough_error_forward'
                        or region.get('end_pc_exclusive') != call.get('success_pc')):
                    return False
                expected['target_pc'] = hex(join)
            elif instruction.kind not in ('nop', 'mov', 'movz', 'movn', 'xmovk',
                                          'wmovz', 'wmovn', 'wmovk', 'wmov'):
                return False
            if row != expected:
                return False
        if rows[-1]['kind'] != 'b' and region['end_pc_exclusive'] != join_text:
            return False
        return type(region.get('opaque_call_count')) is int and region['opaque_call_count'] == calls
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, ModelError):
        return False


def _consistent_success_tail(call: dict, result: dict, tail_count: int) -> bool:
    """Check a bounded success tail against recorded words, without image access."""
    try:
        region = call['error_region']
        tail = region['shared_epilogue']
        rows = tail['instructions']
        evidence = result['instructions']
        join_text = region['join_pc']
        if (not isinstance(join_text, str) or not isinstance(rows, list)
                or not 1 <= len(rows) == tail_count <= MAX_WINDOW_ROWS
                or not isinstance(evidence, list) or not tail_count <= len(evidence) <= 24
                or any(not isinstance(row, dict) for row in rows + evidence)):
            return False
        join = int(join_text, 16)
        end = join + 4 * tail_count
        if (not 0 <= join < end <= 1 << 64 or join % 4 or join_text != hex(join)
                or tail.get('start_pc') != join_text or tail.get('end_pc_exclusive') != hex(end)
                or tail.get('restore_state_proven') is not False
                or any(row.get('phase') == 'return_tail' for row in evidence[:-tail_count])):
            return False
        for index, row in enumerate(rows):
            if (row.get('pc') != hex(join + 4 * index) or not isinstance(row.get('word'), str)
                    or re.fullmatch(r'0x[0-9a-f]{8}', row['word']) is None):
                return False
        packed = b''.join(struct.pack('<I', int(row['word'], 16)) for row in rows)
        rebuilt = _shared_return_tail(packed, SimpleNamespace(start=join, end=end), join)
        if rebuilt is None or rebuilt != tail:
            return False
        expected = rebuilt['instructions']
        for actual, reference in zip(rows, expected):
            if actual != reference or any(type(actual.get(key)) is not type(value) for key, value in reference.items()):
                return False
        for actual, reference in zip(evidence[-tail_count:], expected):
            expected_row = {**reference, 'phase': 'return_tail'}
            if actual != expected_row or any(type(actual.get(key)) is not type(value) for key, value in expected_row.items()):
                return False
        return result.get('return_pc') == call['return_choice'].get('return_pc') == expected[-1]['pc']
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, struct.error):
        return False


def _consistent_success_aliases(call: dict, result: dict, tail_count: int) -> bool:
    """Bind selected success records without requiring error-outcome evidence."""
    try:
        if not _consistent_success_tail(call, result, tail_count):
            return False
        join = int(call['error_region']['join_pc'], 16)
        arm = _bind_choice_success_arm(call, result, tail_count, join)
        _bind_choice_postcall(call, result, tail_count, len(arm))
        _bind_choice_entry_ledgers(call)
        _bind_choice_result_aliases(call, result, arm)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return False
    return True


def _literal_outcome_summary(choice: dict | None) -> str | None:
    if (choice is None or type(choice.get('same_constant_bits')) is not bool
            or any(choice[path].get('kind') != 'constant_bits' for path in ('success', 'error'))):
        return None
    return (f"success x0 bits {choice['success']['constant_bits']}; "
            f"error x0 bits {choice['error']['constant_bits']}")


def _call_result_outcome_summary(choice: dict | None) -> str | None:
    if choice is None or choice.get('same_constant_bits') is not None:
        return None
    success, error = choice['success'], choice['error']
    if (success.get('kind') != 'call_result' or success.get('register') != 'x0'
            or success.get('candidate_status') not in ('preserved_register_candidate', 'copied_register_candidate')
            or error.get('kind') != 'constant_bits'):
        return None
    kind = 'preserved' if success['candidate_status'] == 'preserved_register_candidate' else 'copied'
    return (f"success x0 {kind} call-result candidate; "
            f"error x0 bits {error['constant_bits']}")


def render_swift_error_text(report: dict, *, maximum_bytes: int = MAXIMUM_TEXT_BYTES) -> str:
    """Render bounded producer facts without new analysis or saved-report admission.

    Full counts and source omissions remain visible. All variable values use the
    existing ASCII JSON escaping and escaped-size preflight before allocation.
    Nothing is returned until the complete bounded text has been assembled.
    """
    if type(maximum_bytes) is not int or maximum_bytes < 0:
        raise InputError('invalid_report_size_limit', 'Swift text byte limit must be a nonnegative integer')
    if not isinstance(report, dict):
        raise InputError('swift_text_models', 'Swift text requires an in-process report object')
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
        if not isinstance(values, list):
            line(label + ' malformed detail (raw)', values)
            return
        for value in values[:limit]:
            line(label, value)
        line(label + ' detail rows omitted by renderer', max(0, len(values) - limit))

    def field_rows(label, record, key, limit):
        if key not in record:
            lines.append(label + ': unavailable (missing field)')
        else:
            rows(label, record[key], limit)

    def evidence(label, row_label, record, limit):
        if not isinstance(record, dict):
            line(label + ' malformed (raw)', record)
            return
        line(label, {key: value for key, value in record.items() if key != 'instructions'})
        field_rows(row_label, record, 'instructions', limit)

    def ledger(label, first, second, record):
        if not isinstance(record, dict):
            line(label + ' malformed (raw)', record)
            return
        line(label, {key: value for key, value in record.items()
                     if key not in ('unexpected_entries', 'unclassified_words')})
        field_rows(first, record, 'unexpected_entries', MAX_ENTRY_ROWS)
        field_rows(second, record, 'unclassified_words', MAX_ENTRY_ROWS)

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
    if not isinstance(calls, list):
        raise InputError('swift_text_calls', 'Swift text requires a list of retained call records')
    line('Retained call rows available', len(calls))
    for call in calls[:MAX_CALL_ROWS]:
        if not isinstance(call, dict):
            lines.append('Call candidate')
            line('  Call evidence malformed (raw)', call)
            lines.append('  Structured plan: withheld')
            continue
        presentation = call.get('presentation')
        if (not isinstance(presentation, dict)
                or presentation.get('status') not in ('eligible_structural_only', 'blocked', 'unresolved')
                or presentation.get('source_reconstruction_allowed') is not False):
            raise InputError('swift_text_presentation', 'Missing or unsupported structural presentation result')
        plan = presentation.get('display_plan')
        interval = plan.get('error_interval') if isinstance(plan, dict) else None
        condition = plan.get('condition') if isinstance(plan, dict) else None
        plan_tail = plan.get('shared_epilogue') if isinstance(plan, dict) else None
        def plan_words(value, limit):
            return (isinstance(value, list) and 1 <= len(value) <= limit
                    and all(isinstance(row, dict)
                            and all(isinstance(row.get(key), str) for key in ('pc', 'word', 'kind'))
                            for row in value))

        region_for_plan = call.get('error_region')
        region_scope_consistent = (isinstance(region_for_plan, dict)
                                   and region_for_plan.get('status') == 'structural_region_candidate'
                                   and region_for_plan.get('call_return_proven') is False
                                   and region_for_plan.get('join_reachability_proven') is False)
        expected_condition = {'test_pc': call.get('test_pc'), 'register': call.get('tested_register'),
                              'error_when': 'nonzero'}
        if call.get('test_kind') == 'cmp_zero_bcond':
            expected_condition.update({key: call.get(key) for key in ('comparison_pc', 'test_kind', 'test_condition')})
        shared = isinstance(plan, dict) and 'shared_epilogue' in plan
        success_interval = plan.get('success_interval') if isinstance(plan, dict) else None
        plan_renderable = (presentation['status'] == 'eligible_structural_only'
                           and presentation.get('reason') == 'complete_caller_local_direct_validation'
                           and 'postcall_entry_validation' not in presentation
                           and isinstance(plan, dict)
                           and plan.get('kind') == 'structural_error_interval'
                           and plan.get('label') == 'Structural error-path candidate'
                           and isinstance(plan.get('success_entry_pc'), str)
                           and plan['success_entry_pc'] == call.get('success_pc')
                           and isinstance(condition, dict) and condition == expected_condition
                           and all(isinstance(condition.get(key), str) for key in ('test_pc', 'register', 'error_when'))
                           and (call.get('test_kind') != 'cmp_zero_bcond' or
                                (isinstance(condition.get('comparison_pc'), str)
                                 and condition.get('test_condition') in ('eq', 'ne')))
                           and isinstance(interval, dict)
                           and all(isinstance(interval.get(key), str) for key in ('start_pc', 'end_pc_exclusive'))
                           and plan_words(interval.get('instructions'), 16)
                           and _bounded_error_interval_geometry(interval)
                           and region_scope_consistent
                           and interval == {key: region_for_plan.get(key) for key in ('start_pc', 'end_pc_exclusive', 'instructions')}
                           and _consistent_error_instruction_records(call, region_for_plan)
                           and interval['start_pc'] == call.get('error_pc')
                           and (shared == ('success_interval' in plan))
                           and (not shared or
                                (isinstance(plan_tail, dict) and isinstance(success_interval, dict)
                                 and plan_words(plan_tail.get('instructions'), 8)
                                 and plan_words(success_interval.get('instructions'), 8)
                                 and plan_tail.get('restore_state_proven') is False
                                 and isinstance(region_for_plan.get('shared_epilogue'), dict)
                                 and region_for_plan['shared_epilogue'].get('restore_state_proven') is False
                                 and (region_for_plan.get('layout') != 'success_fallthrough_error_forward'
                                      or (success_interval.get('instructions_complete') is True
                                          and isinstance(region_for_plan.get('success_interval'), dict)
                                          and region_for_plan['success_interval'].get('instructions_complete') is True))
                                 and plan_tail == region_for_plan.get('shared_epilogue')
                                 and success_interval == region_for_plan.get('success_interval'))))
        lines.append('Call candidate')
        line('  Call evidence', {key: call[key] for key in ('call_pc', 'call_image_offset', 'call_word', 'caller_pc', 'callee_pc', 'status') if key in call})
        if 'callee' in call:
            line('  Callee declaration (not runtime identity)', call['callee'])
        if 'reason' in call:
            line('  Edge decline reason', call['reason'])
        if 'success_result' in call:
            if report.get('success_result_model_version') != SUCCESS_RESULT_MODEL:
                raise InputError('swift_text_models', 'Success-result evidence requires its current model')
            result = call['success_result']
            evidence('  Success result (selected-path register evidence only)', '    Result-path instruction', result, 24)
        if 'success_constant' in call:
            if report.get('success_constant_model_version') != SUCCESS_CONSTANT_MODEL:
                raise InputError('swift_text_models', 'Success-constant evidence requires its current model')
            constant = call['success_constant']
            evidence('  Success constant (selected-path bits only)', '    Constant-path instruction', constant, 16)
        if 'error_constant' in call:
            if report.get('error_constant_model_version') != ERROR_CONSTANT_MODEL:
                raise InputError('swift_text_models', 'Error-constant evidence requires its current model')
            constant = call['error_constant']
            evidence('  Error constant (selected-path bits; call return unproven)', '    Error-constant instruction', constant, 24)
        if 'return_choice' in call:
            if report.get('return_choice_model_version') != RETURN_CHOICE_MODEL:
                raise InputError('swift_text_models', 'Return-choice evidence requires its current model')
            choice = call['return_choice']
            line('  Return choice (structural outcomes; source disabled)', choice)
            consistent_choice = _consistent_return_choice(call) if plan_renderable else None
            literal_summary = _literal_outcome_summary(consistent_choice)
            if literal_summary is not None:
                line('  Recorded literal outcomes (structural; runtime unproven)', literal_summary)
            call_result_summary = _call_result_outcome_summary(consistent_choice)
            if call_result_summary is not None:
                line('  Recorded call-result/error outcomes (structural; runtime unproven)', call_result_summary)
            success = choice.get('success') if isinstance(choice, dict) else None
            result = call.get('success_result')
            adjustment_word = _adjusted_result_word(result)
            plan = presentation.get('display_plan')
            tail = plan.get('shared_epilogue') if isinstance(plan, dict) else None
            tail_rows = tail.get('instructions') if isinstance(tail, dict) else None
            arm = plan.get('success_interval') if isinstance(plan, dict) else None
            arm_rows = arm.get('instructions') if isinstance(arm, dict) else None
            result_rows = result.get('instructions') if isinstance(result, dict) else None
            region = call.get('error_region')
            expected_condition = {'test_pc': call.get('test_pc'), 'register': call.get('tested_register'), 'error_when': 'nonzero'}
            if call.get('test_kind') == 'cmp_zero_bcond':
                expected_condition.update({key: call.get(key) for key in ('comparison_pc', 'test_kind', 'test_condition')})
            try:
                _bind_choice_call_word(call)
                recorded_call_bound = True
            except (KeyError, TypeError, ValueError):
                recorded_call_bound = False
            proof_flags = ('runtime_value_proven', 'source_reconstruction_allowed', 'exclusive_path_proven',
                           'caller_return_type_proven')
            if (plan_renderable and recorded_call_bound
                    and _consistent_callee_declaration(call.get('callee')) and call['callee']['result'] == 'Swift.Int'
                    and isinstance(result, dict) and isinstance(success, dict) and isinstance(plan, dict)
                    and choice.get('status') == 'structural_choice_candidate'
                    and result.get('status') == 'adjusted_register_candidate'
                    and success.get('kind') in ('call_result_add_immediate', 'call_result_sub_immediate')
                    and success.get('register') == result.get('register') == 'x0'
                    and success.get('operation') == result.get('operation')
                    and (success.get('kind'), success.get('operation')) in (('call_result_add_immediate', 'add_immediate_modulo'),
                                                                     ('call_result_sub_immediate', 'sub_immediate_modulo'))
                    and type(success.get('bit_width')) is int and success['bit_width'] == 64
                    and type(result.get('bit_width')) is int and result['bit_width'] == 64
                    and adjustment_word is not None
                    and type(success.get('immediate')) is int
                    and type(result.get('immediate')) is int and result['immediate'] == success['immediate']
                    and type(success.get('immediate_shift')) is int
                    and success['immediate_shift'] == result.get('immediate_shift')
                    and isinstance(call.get('call_pc'), str)
                    and choice.get('call_pc') == result.get('call_pc') == call['call_pc']
                    and isinstance(choice.get('return_pc'), str)
                    and choice['return_pc'] == result.get('return_pc')
                    and isinstance(tail, dict) and tail.get('restore_state_proven') is False
                    and result.get('return_tail_layout') == 'shared_epilogue'
                    and isinstance(region, dict)
                    and isinstance(arm_rows, list) and 1 <= len(arm_rows) <= MAX_WINDOW_ROWS
                    and isinstance(tail_rows, list) and 1 <= len(tail_rows) <= MAX_WINDOW_ROWS
                    and isinstance(result_rows, list) and len(result_rows) <= 24
                    and plan.get('success_interval') == region.get('success_interval')
                    and plan.get('shared_epilogue') == region.get('shared_epilogue')
                    and all(isinstance(row, dict) for row in arm_rows + result_rows)
                    and [(row.get('pc'), row.get('word')) for row in result_rows if row.get('phase') == 'success']
                        == [(row.get('pc'), row.get('word')) for row in arm_rows]
                    and sum(row.get('word') == f'0x{adjustment_word:08x}'
                            for row in arm_rows) == 1
                    and isinstance(tail_rows[-1], dict) and tail_rows[-1].get('pc') == choice['return_pc']
                    and isinstance(call.get('success_pc'), str)
                    and result.get('success_pc') == plan.get('success_entry_pc') == call['success_pc']
                    and isinstance(call.get('test_pc'), str) and isinstance(call.get('tested_register'), str)
                    and isinstance(choice.get('condition'), dict)
                    and choice['condition'] == plan.get('condition') == expected_condition
                    and all(choice.get(key) is False and result.get(key) is False for key in proof_flags)
                    and choice.get('call_return_proven') is False and choice.get('handler_semantics_proven') is False
                    and _consistent_success_aliases(call, result, len(tail_rows))):
                line('  Success operation (structural; runtime unproven)',
                     f"call result {'+' if success['operation'] == 'add_immediate_modulo' else '-'} {success['immediate']} modulo 2^64")
                if (consistent_choice is not None and consistent_choice.get('same_constant_bits') is None
                        and consistent_choice['error'].get('kind') == 'constant_bits'):
                    paired_success, paired_error = consistent_choice['success'], consistent_choice['error']
                    line('  Recorded adjusted-result/error outcomes (structural; runtime unproven)',
                         f"success x0 call result {'+' if paired_success['operation'] == 'add_immediate_modulo' else '-'} "
                         f"{paired_success['immediate']} modulo 2^64; error x0 bits {paired_error['constant_bits']}")
        line('  Recorded return edges', {key: call[key] for key in ('comparison_pc', 'test_pc', 'test_kind', 'test_condition', 'tested_register', 'success_pc', 'error_pc') if key in call})
        rows('  Post-call instruction evidence', call.get('window', []), MAX_WINDOW_ROWS)
        if 'flag_entry_validation' in call:
            if report.get('flag_entry_model_version') != FLAG_ENTRY_MODEL:
                raise InputError('swift_text_models', 'Flag-entry evidence requires its current model')
            line('  Flag-entry model', report['flag_entry_model_version'])
            entry = call['flag_entry_validation']
            ledger('  Flag-entry validation', '    Unexpected flag-window entry',
                   '    Unclassified flag-scan word', entry)
        line('  Presentation', {key: presentation[key] for key in ('status', 'reason') if key in presentation})
        if 'postcall_entry_validation' in presentation:
            ledger('  Post-call entry validation', '    Unexpected post-call entry',
                   '    Unclassified post-call scan word', presentation['postcall_entry_validation'])
        if plan_renderable:
            line('  Label', plan['label'])
            line('  Condition (structural)', plan['condition'])
            line('  Error interval', {key: interval[key] for key in ('start_pc', 'end_pc_exclusive')})
            rows('    Instruction', interval['instructions'], MAX_WORD_ROWS)
            line('  Success entry', plan['success_entry_pc'])
            if 'shared_epilogue' in plan:
                tail = plan['shared_epilogue']
                if isinstance(tail, dict):
                    line('  Shared restore/return candidate (state unproven)',
                         {key: value for key, value in tail.items() if key != 'instructions'})
                else:
                    line('  Shared restore/return candidate malformed (raw)', tail)
        else:
            lines.append('  Structured plan: withheld')
            if presentation['status'] == 'eligible_structural_only':
                if 'display_plan' in presentation:
                    label = ('  Structured plan withheld with inconsistent presentation reason (raw)'
                             if presentation.get('reason') != 'complete_caller_local_direct_validation' else
                             '  Structured plan withheld with conflicting post-call ledger (raw)'
                             if 'postcall_entry_validation' in presentation else
                             '  Structured plan withheld with inconsistent region scope (raw)'
                             if not region_scope_consistent else '  Structured plan malformed (raw)')
                    line(label, presentation['display_plan'])
                else:
                    lines.append('  Structured plan unavailable (missing field)')
            region = call.get('error_region')
            if isinstance(region, dict):
                line('  Region evidence', {key: region[key] for key in ('status', 'reason', 'start_pc', 'end_pc_exclusive',
                    'join_pc', 'call_return_proven', 'join_reachability_proven') if key in region})
                field_rows('    Region instruction evidence', region, 'instructions', MAX_WORD_ROWS)
        if 'error_region' not in call and presentation['status'] == 'eligible_structural_only':
            lines.append('  Region evidence: unavailable (missing field)')
        region = call.get('error_region', {})
        if not isinstance(region, dict):
            line('  Region evidence malformed (raw)', region)
            region = {}
        elif plan_renderable and ('instructions' not in region or not isinstance(region['instructions'], list)):
            field_rows('    Region instruction evidence', region, 'instructions', MAX_WORD_ROWS)
        for key, label in (('success_interval', 'Success-arm'), ('shared_epilogue', 'Shared tail')):
            interval = region.get(key)
            if isinstance(interval, dict):
                line('  ' + label + ' interval evidence', {k: v for k, v in interval.items() if k != 'instructions'})
                field_rows('    ' + label + ' instruction', interval, 'instructions', MAX_WORD_ROWS)
            elif key in region:
                line('  ' + label + ' interval malformed (raw)', interval)
        if 'incoming_validation' in region:
            ledger('  Incoming validation', '    Unexpected direct entry',
                   '    Unclassified word', region['incoming_validation'])
        elif region.get('status') == 'structural_region_candidate':
            lines.append('  Incoming validation: unavailable (missing field)')
        field_rows('  Candidate limitation', presentation, 'limitations', MAX_LIMITATION_ROWS)
    line('Retained call rows omitted by renderer', max(0, len(calls) - MAX_CALL_ROWS))
    lines.append('Renderer omissions are additional to producer omitted calls, unscanned words and truncated evidence details.')
    rows('Report limitation', report['limitations'], MAX_LIMITATION_ROWS)
    return lines.finish()
