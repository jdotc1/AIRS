"""Select reason detail by supplied-report count without changing evidence facts."""
from __future__ import annotations

from copy import deepcopy

from .types import InputError


def validate_coverage_minimum_count(value: int | None) -> int | None:
    """Validate the optional positive threshold before saved-report I/O."""
    if value is not None and (type(value) is not int or value < 1):
        raise InputError('invalid_coverage_minimum_count', 'Minimum reason count must be a positive integer')
    return value


def select_coverage_frequency(inventory: dict, minimum_count: int | None = None) -> dict:
    """Detach selected unlimited inventory detail, retaining inclusive counts.

    Apply after reason-code selection and before ordering/limiting. Counts measure
    supplied saved reports only; they do not establish representative prevalence.
    Full summary, reports, duplicate/conflict and reason-selection context remain.
    """
    minimum = validate_coverage_minimum_count(minimum_count)
    result = deepcopy(inventory)
    if minimum is None:
        return result
    input_count = len(result['reasons'])
    result['reasons'] = [row for row in result['reasons'] if row['count'] >= minimum]
    selected_count = len(result['reasons'])
    result['reason_frequency_selection'] = {
        'minimum_count': minimum, 'input_count': input_count,
        'selected_count': selected_count, 'omitted_count': input_count - selected_count,
    }
    return result
