"""Construct bounded candidates. Only a separate byte validator grants eligibility."""
from .swift_outcome_witness_models import (
    WITNESS_MODEL, VALIDATION_MODEL, LEGACY_PROFILE, PROFILES,
    DEFAULT_WITNESS_LIMITS, bounded_copy, image_identity, source_models,
)


def build_outcome_witness(image, function, call: dict, *, limits=DEFAULT_WITNESS_LIMITS,
                          model_profile=LEGACY_PROFILE) -> dict:
    result = {'schema_version': 1, 'model_version': WITNESS_MODEL,
              'validation_model_version': VALIDATION_MODEL, 'status': 'unresolved',
              'reason': 'validation_required', 'source_reconstruction_allowed': False,
              'call_return_proven': False, 'runtime_branch_proven': False,
              'handler_semantics_proven': False,
              'limitations': ['Structural observations only; reachability, exclusive entry, call return and handler semantics remain unproven.']}
    try:
        if model_profile not in PROFILES or type(call) is not dict:
            raise ValueError('witness_input')
        evidence = bounded_copy({k: v for k, v in call.items() if k not in ('outcome_witness', 'presentation')}, limits)
        result.update(image=image_identity(image),
            caller={'start_pc': hex(function.start), 'end_pc_exclusive': hex(function.end),
                    'boundary_source': function.boundary_source},
            model_profile=model_profile, source_models=source_models(model_profile), evidence=evidence)
        # Deterministic textual identity avoids rereading or hashing admitted source.
        result['witness_id'] = ':'.join((WITNESS_MODEL, image.slice_sha256, hex(function.start), evidence['call_pc']))
        graph = []
        for key, label in (('call_pc', 'call'), ('test_pc', 'test'), ('success_pc', 'success'), ('error_pc', 'error')):
            if key in evidence:
                graph.append({'id': label, 'pc': evidence[key]})
        region = evidence.get('error_region', {})
        if type(region) is dict and 'join_pc' in region:
            graph.append({'id': 'join', 'pc': region['join_pc']})
        ids = {n['id'] for n in graph}
        pairs = [('call', 'test'), ('test', 'success'), ('test', 'error'), ('error', 'join'), ('success', 'join')]
        def provenance(a):
            if a == 'test': return evidence['test_pc']
            if a == 'error': return region['instructions'][-1]['pc']
            if a == 'success': return region['success_interval']['instructions'][-1]['pc']
            return evidence['call_pc']
        edges = [{'from': a, 'to': b, 'provenance_pc': provenance(a),
                  'relationship': 'recorded_structural'} for a, b in pairs if a in ids and b in ids]
        if len(graph) > limits.max_nodes or len(edges) > limits.max_edges:
            raise ValueError('witness_graph_limit')
        result.update(graph={'nodes': graph, 'edges': edges}, accounting={'nodes': len(graph), 'edges': len(edges)})
        bounded_copy(result, limits)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
        return {k: result[k] for k in ('schema_version', 'model_version', 'validation_model_version',
            'source_reconstruction_allowed', 'call_return_proven', 'runtime_branch_proven', 'handler_semantics_proven')} | {
                'status': 'unresolved', 'reason': str(error), 'details_complete': False}
    return result
