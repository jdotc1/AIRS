"""Bounded terminal-safe rendering of in-process Swift structural producer output."""
from __future__ import annotations

from .report_summary_text import _BoundedText
from .swift_error_flow import MODEL, REGION_MODEL, INCOMING_MODEL, PRESENTATION_MODEL
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
        line('  Recorded return edges', {key: call[key] for key in ('test_pc', 'tested_register', 'success_pc', 'error_pc') if key in call})
        rows('  Post-call instruction evidence', call.get('window', []), MAX_WINDOW_ROWS)
        line('  Presentation', {key: presentation[key] for key in ('status', 'reason')})
        if presentation['status'] == 'eligible_structural_only':
            plan = presentation['display_plan']
            line('  Label', plan['label'])
            line('  Condition (structural)', plan['condition'])
            interval = plan['error_interval']
            line('  Error interval', {key: interval[key] for key in ('start_pc', 'end_pc_exclusive')})
            rows('    Instruction', interval['instructions'], MAX_WORD_ROWS)
            line('  Success entry', plan['success_entry_pc'])
        else:
            lines.append('  Structured plan: withheld')
            region = call.get('error_region')
            if isinstance(region, dict):
                line('  Region evidence', {key: region[key] for key in ('status', 'reason', 'start_pc', 'end_pc_exclusive',
                    'join_pc', 'call_return_proven', 'join_reachability_proven') if key in region})
                rows('    Region instruction evidence', region['instructions'], MAX_WORD_ROWS)
        region = call.get('error_region', {})
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
