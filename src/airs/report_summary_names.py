"""Literal function-name selection over saved summary detail only."""
from __future__ import annotations

from copy import deepcopy

from .types import InputError


def validate_summary_name(value: str | None) -> str | None:
    """Admit bounded literal text before report I/O; never normalize names."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise InputError('invalid_summary_name', 'Name query must be literal nonblank UTF-8 text of 1 to 256 bytes without ASCII controls')
    try:
        size = len(value.encode('utf-8'))
    except UnicodeEncodeError as exc:
        raise InputError('invalid_summary_name', 'Name query must be valid UTF-8 text') from exc
    if not value.strip() or size > 256 or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise InputError('invalid_summary_name', 'Name query must be literal nonblank UTF-8 text of 1 to 256 bytes without ASCII controls')
    return value


def select_summary_names(summary: dict, contains: str | None = None) -> dict:
    """Detach selected, unlimited details and retain literal substring matches.

    Prior verdict/reason selection metadata and full source counts are unchanged.
    Missing names do not match. Apply before detail ordering and limiting.
    """
    query = validate_summary_name(contains)
    result = deepcopy(summary)
    if query is None:
        return result
    input_count = len(result['findings'])
    result['findings'] = [finding for finding in result['findings']
                          if isinstance(finding.get('function', {}).get('name'), str)
                          and query in finding['function']['name']]
    selected_count = len(result['findings'])
    result['finding_name_selection'] = {
        'contains': query, 'case_sensitive': True, 'normalization': 'none',
        'input_count': input_count, 'selected_count': selected_count,
        'omitted_count': input_count - selected_count,
    }
    return result
