"""Explicit model firewall for the separately qualified broad Swift pipeline.

Historical model labels describe their original subsets forever. A new registry
entry is a contract identity, not evidence that its pipeline is implemented.
"""
from dataclasses import dataclass
from types import MappingProxyType

from .types import InputError

BROAD_PROFILE = 'broad-v1'
BROAD_MODEL = 'swift-broad-error-flow-v1'
BROAD_WITNESS_MODEL = 'swift-outcome-witness-v2'
BROAD_VALIDATION_MODEL = 'swift-outcome-validation-v2'


@dataclass(frozen=True, slots=True)
class SwiftProfile:
    edge_model: str
    return_choice_model: str | None
    witness_model: str
    validation_model: str


PROFILES = MappingProxyType({
    'legacy': SwiftProfile('swift-sync-error-edges-v37', 'swift-return-choice-v45',
                           'swift-outcome-witness-v1', 'swift-outcome-validation-v1'),
    'methods': SwiftProfile('swift-sync-error-edges-v38', 'swift-return-choice-v46',
                            'swift-outcome-witness-v1', 'swift-outcome-validation-v1'),
    BROAD_PROFILE: SwiftProfile(BROAD_MODEL, None, BROAD_WITNESS_MODEL, BROAD_VALIDATION_MODEL),
})


def validate_broad_options(*, include_outcome_witnesses: bool,
                           include_error_regions: bool, validate_region_entries: bool,
                           include_structured_presentation: bool,
                           include_swift_methods: bool) -> None:
    """Validate broad CLI prerequisites before any input resolution or reading."""
    if include_swift_methods or not (include_outcome_witnesses and include_error_regions
                                    and validate_region_entries and include_structured_presentation):
        raise InputError('swift_broad_options',
                         'broad-v1 requires --include-outcome-witnesses, --include-error-regions, '
                         '--validate-region-entries and --include-structured-presentation; '
                         '--include-swift-methods is a separate historical profile')
