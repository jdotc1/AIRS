"""Order saved-inventory reason detail without changing evidence or counts."""
from __future__ import annotations

from copy import deepcopy

from .types import InputError


def validate_coverage_order(value: str) -> str:
    """Validate the presentation order before saved-report I/O."""
    if not isinstance(value, str) or value not in ('count', 'reason'):
        raise InputError('invalid_coverage_order', 'Coverage order must be count or reason')
    return value


def order_coverage_reasons(inventory: dict, order: str = 'count') -> dict:
    """Detach a complete selected inventory and optionally sort literal codes.

    The aggregation's default count order and output shape are preserved. Apply
    after reason selection and before limiting; full evidence context is unchanged.
    """
    selected_order = validate_coverage_order(order)
    result = deepcopy(inventory)
    if selected_order == 'count':
        return result
    result['reasons'].sort(key=lambda row: row['reason'])
    result['reason_order'] = 'reason'
    return result
