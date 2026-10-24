"""Bound saved coverage reason detail without changing full inventory facts."""
from __future__ import annotations

from copy import deepcopy

from .types import InputError


def validate_coverage_limit(value: int | None) -> int | None:
    """Validate the presentation bound before any saved-report I/O."""
    if value is None:
        return None
    if type(value) is not int or not 0 <= value <= 200_000:
        raise InputError('invalid_coverage_limit', 'Coverage limit must be an integer from 0 to 200000')
    return value


def limit_coverage_reasons(inventory: dict, maximum_reasons: int | None = None) -> dict:
    """Detach a complete selected inventory, retaining its ranked reason prefix.

    Counts, report rows, conflicts and reason-selection provenance are unchanged.
    Omission is presentation only; no finding becomes supported or resolved.
    """
    maximum = validate_coverage_limit(maximum_reasons)
    result = deepcopy(inventory)
    if maximum is None:
        return result
    selected_count = len(result['reasons'])
    result['reasons'] = result['reasons'][:maximum]
    returned_count = len(result['reasons'])
    result['reason_limit'] = {
        'maximum': maximum, 'returned_count': returned_count,
        'omitted_count': selected_count - returned_count,
        'selected_count': selected_count,
    }
    return result
