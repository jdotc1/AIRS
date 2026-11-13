# Generated from registry/models.json; do not edit by hand.
"""Exact historical report-admission identities, independent of engine capability.

Unknown labels keep generic import validation. Never infer admission from a
version number or prefix: historical aliases and policy differences are explicit.
"""

CFG_MODELS = frozenset((
    'arm64-bounded-cfg-v3',
    'arm64-bounded-calls-v4',
    'arm64-bounded-dwarf-cfg-v5',
    'arm64-bounded-returns-v6',
    'arm64-bounded-teardowns-v7',
    'arm64-bounded-suffixes-v8',
    'arm64-bounded-conditional-v9',
    'arm64-bounded-conditions-v10',
    'arm64-bounded-flags-v11',
    'arm64-bounded-register-flags-v12',
    'arm64-bounded-shifted-flags-v13',
    'arm64-bounded-extended-flags-v14',
    'arm64-bounded-logical-flags-v15',
    'arm64-bounded-logical-immediate-v16',
    'arm64-bounded-nonflag-immediate-v17',
    'arm64-bounded-nonflag-register-v18',
    'arm64-bounded-carry-v19',
    'arm64-bounded-conditional-compare-v20',
    'arm64-bounded-conditional-select-v21',
    'arm64-bounded-bitfield-v22',
    'arm64-bounded-extract-v23',
    'arm64-bounded-variable-shift-v24',
    'arm64-bounded-multiply-v25',
    'arm64-bounded-widening-multiply-v26',
    'arm64-bounded-high-multiply-v27',
    'arm64-bounded-loops-v28',
    'arm64-bounded-loop-calls-v29',
    'arm64-bounded-cfa-register-v30',
    'arm64-bounded-sequential-loops-v31',
    'arm64-bounded-clz-v32',
    'arm64-bounded-rbit-v33',
    'arm64-bounded-udiv-v34',
    'arm64-bounded-x-stack-v35',
    'arm64-bounded-fp-x-stack-v36',
    'arm64-bounded-sdiv-v37',
    'arm64-bounded-w-rbit-v38',
    'arm64-bounded-equivalent-compact-v39',
    'arm64-bounded-local-fde-v40',
    'arm64-bounded-cfi-control-v41',
    'arm64-bounded-w-sdiv-v42',
    'arm64-bounded-w-udiv-v43',
    'arm64-bounded-rev-v44',
    'arm64-bounded-rev16-v45',
    'arm64-bounded-rev32-v46',
    'arm64-bounded-cls-v47',
    'arm64-bounded-movk-v48',
    'arm64-bounded-compare-branch-v49',
    'arm64-bounded-test-bit-branch-v50',
    'arm64-bounded-extract-class-v51',
    'arm64-bounded-cfi-control-v36',
))
KNOWN_MODELS = CFG_MODELS | frozenset(('arm64-linear-v1', 'arm64-linear-dwarf-v2'))
EVALUATED_CFI_MODELS = CFG_MODELS | frozenset(('arm64-linear-dwarf-v2',))
CURRENT_MODEL = 'arm64-bounded-extract-class-v51'
SWIFT_CALLER_ERROR_TEST_MODEL = 'swift-caller-error-test-v1'
SWIFT_IMPORT_EFFECT_ADMISSION_MODEL = 'swift-import-effect-admission-v1'
SWIFT_INDIRECT_TARGET_SHAPE_MODEL = 'swift-indirect-target-shape-v1'
SWIFT_VALUE_WITNESS_ADMISSION_MODEL = 'swift-value-witness-admission-v1'
SWIFT_BROAD_PAIRS = (
    ('swift-broad-error-flow-v1', 'broad-v1'),
    ('swift-broad-error-flow-large-v1', 'broad-large-v1'),
    ('swift-broad-error-flow-extended-v1', 'broad-extended-v1'),
    ('swift-broad-error-flow-imports-v1', 'broad-imports-v1'),
    ('swift-broad-error-flow-imports-got-v1', 'broad-imports-got-v1'),
    ('swift-broad-error-flow-extended-v2', 'broad-extended-v2'),
    ('swift-broad-error-flow-extended-v3', 'broad-extended-v3'),
    ('swift-broad-error-flow-extended-v4', 'broad-extended-v4'),
)
SWIFT_BROAD_ENGINE_ONLY_PROFILES = frozenset(('broad-imports-got-v1', 'broad-extended-v4'))
