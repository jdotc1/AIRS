"""Bounded supplemental witness contracts; no runtime/source semantics."""
from dataclasses import dataclass, fields
import json

WITNESS_MODEL = 'swift-outcome-witness-v1'
VALIDATION_MODEL = 'swift-outcome-validation-v1'
LEGACY_PROFILE = 'legacy'
METHOD_PROFILE = 'methods'
PROFILES = {
    LEGACY_PROFILE: ('swift-sync-error-edges-v37', 'swift-return-choice-v45'),
    METHOD_PROFILE: ('swift-sync-error-edges-v38', 'swift-return-choice-v46'),
}

@dataclass(frozen=True, slots=True)
class WitnessLimits:
    max_instructions: int = 64
    max_caller_words: int = 4096
    max_steps: int = 512
    max_total_work: int = 262144
    max_nodes: int = 16
    max_edges: int = 24
    max_depth: int = 8
    max_bytes: int = 65536
    max_container_items: int = 4096
    max_string: int = 2048

    def __post_init__(self):
        if any(type(getattr(self, f.name)) is not int or getattr(self, f.name) < 0 for f in fields(self)):
            raise ValueError('Witness limits must be nonnegative integers')

DEFAULT_WITNESS_LIMITS = WitnessLimits()

def source_models(profile):
    edge, choice = PROFILES[profile]
    result = {'edge': edge, 'return_choice': choice,
        'region': 'swift-sync-error-region-v24', 'incoming': 'swift-region-direct-entries-v7',
        'presentation': 'swift-structural-presentation-v10', 'success_result': 'swift-success-result-v24',
        'success_constant': 'swift-success-constant-v17', 'error_constant': 'swift-error-constant-v19',
        'flag_entry': 'swift-compare-flag-entries-v1'}
    if profile == METHOD_PROFILE: result['declaration'] = 'swift-throwing-declarations-v1'
    return result

@dataclass(frozen=True, slots=True)
class WitnessIdentity:
    slice_sha256: str
    caller_pc: str
    call_pc: str
    model: str = WITNESS_MODEL


def bounded_copy(value, limits=DEFAULT_WITNESS_LIMITS):
    """Preflight before copying or JSON allocation; reject cycles and wide inputs."""
    todo = [(value, 0)]; count = 0; chars = 0
    while todo:
        obj, depth = todo.pop(); count += 1
        if count > limits.max_container_items or depth > limits.max_depth:
            raise ValueError('witness_memory_limit')
        if type(obj) is dict:
            if len(obj) > limits.max_container_items - count:
                raise ValueError('witness_memory_limit')
            for key, child in obj.items():
                if type(key) is not str or len(key) > limits.max_string:
                    raise ValueError('witness_container')
                chars += len(key); todo.append((child, depth + 1))
        elif type(obj) is list:
            if len(obj) > limits.max_container_items - count:
                raise ValueError('witness_memory_limit')
            todo.extend((child, depth + 1) for child in obj)
        elif type(obj) is str:
            if len(obj) > limits.max_string:
                raise ValueError('witness_string_limit')
            chars += len(obj)
        elif obj is not None and type(obj) not in (int, bool):
            raise ValueError('witness_container')
        if chars > limits.max_bytes:
            raise ValueError('witness_output_limit')
    chunks=[]; size=0
    for chunk in json.JSONEncoder(sort_keys=True, ensure_ascii=True, allow_nan=False).iterencode(value):
        size += len(chunk)
        if size > limits.max_bytes: raise ValueError('witness_output_limit')
        chunks.append(chunk)
    return json.loads(''.join(chunks))


def image_identity(image):
    return {k: getattr(image, k) for k in ('architecture', 'cpu_subtype', 'uuid',
        'slice_sha256', 'container_sha256', 'slice_offset', 'slice_size')} | {'preferred_base': hex(image.preferred_base)}
