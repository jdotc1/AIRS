"""Bounded terminal-safe rendering of recorded broad-profile checks."""
import json
from .types import InputError

MAX_TEXT_BYTES=1024*1024


def render_swift_broad_text(report):
    if (type(report) is not dict or not (report.get('model_version')=='swift-broad-error-flow-v1'
            or (report.get('model_version')=='swift-broad-error-flow-large-v1'
                and report.get('profile')=='broad-large-v1')
            or (report.get('model_version')=='swift-broad-error-flow-extended-v1'
                and report.get('profile')=='broad-extended-v1')
            or (report.get('model_version')=='swift-broad-error-flow-extended-v2'
                and report.get('profile')=='broad-extended-v2')
            or (report.get('model_version')=='swift-broad-error-flow-extended-v3'
                and report.get('profile')=='broad-extended-v3')
            or (report.get('model_version')=='swift-broad-error-flow-imports-v1'
                and report.get('profile')=='broad-imports-v1')
            or (report.get('model_version')=='swift-broad-error-flow-imports-got-v1'
                and report.get('profile')=='broad-imports-got-v1'))):
        raise InputError('swift_broad_text_model','Unsupported broad report model')
    # JSON quoting escapes terminal control characters; it does not authenticate
    # imported reports or promote recorded validator outcomes to fresh checks.
    def safe(value):
        if type(value) is str:text=value[:2048]
        elif value is None or type(value) is bool:text=str(value)
        elif type(value) is int and -(1<<64)<=value<1<<64:text=str(value)
        else:text='<unsupported scalar>'
        return json.dumps(text,ensure_ascii=True)
    identity=report.get('identity') or {}
    if type(identity) is not dict:raise InputError('swift_broad_text_shape','Identity must be an object')
    lines=['AIRS broad Swift structural observations (research profile)',
        'Recorded checks only; rendering does not reread or authenticate source bytes.',
        'No runtime reachability, call return, exclusive entry or source semantics are proven.',
        'Profile: '+safe(report.get('profile')),
        'Selected slice: '+safe(identity.get('slice_sha256'))]
    for name in ('word_scan_complete','call_details_complete','outcome_witnesses_complete',
                 'scanned_words','selected_call_candidates','omitted_calls'):
        lines.append(name+': '+safe(report.get(name)))
    caller_profiles=('broad-extended-v2','broad-extended-v3')
    imports=report.get('profile') in ('broad-imports-v1','broad-imports-got-v1')+caller_profiles
    got=report.get('profile') in ('broad-imports-got-v1',)+caller_profiles
    if imports:
        # Imported callees are attribution and declaration syntax only.
        lines.append('Imported stub calls: attribution and declaration syntax only; no ABI, witness or runtime binding.')
        for name in ('import_stub_model','import_stubs_complete','import_stub_reason'):
            lines.append(name+': '+safe(report.get(name)))
        counts=report.get('import_stub_counts') or {}
        if type(counts) is not dict:raise InputError('swift_broad_text_shape','Import stub counts must be an object')
        for name in ('attributed_stubs','declined_stubs','invalid_stub_sections','selected_import_calls',
                     'non_throwing_swift_import_calls','non_swift_import_calls','declined_stub_calls'):
            lines.append('import_stub_counts.'+name+': '+safe(counts.get(name)))
    if got:
        # GOT-loaded BLR calls are attribution only from two agreeing binding tables.
        lines.append('GOT-loaded BLR calls: attribution only from two agreeing binding tables; no ABI, witness or runtime binding.')
        for name in ('got_binding_model','chained_fixups_model','got_window_model','got_bindings_complete',
                     'got_binding_reason','chained_fixups_status'):
            lines.append(name+': '+safe(report.get(name)))
        counts=report.get('got_counts') or {}
        if type(counts) is not dict:raise InputError('swift_broad_text_shape','GOT counts must be an object')
        for name in ('got_slots','agreeing_got_slots','declined_got_slots','blr_instructions','got_candidates',
                     'attributed_got_calls','declined_got_calls','selected_got_calls',
                     'non_throwing_swift_got_calls','non_swift_got_calls'):
            lines.append('got_counts.'+name+': '+safe(counts.get(name)))
        for key in ('got_decline_counts','got_slot_decline_counts'):
            table=report.get(key) or {}
            if type(table) is not dict:raise InputError('swift_broad_text_shape','GOT decline counts must be an object')
            for name in sorted(table)[:64]:
                lines.append(key+'.'+safe(name)+': '+safe(table[name]))
    indirect=report.get('profile')=='broad-extended-v3'
    if indirect:
        lines.append('Indirect target shape: where an indirect call target was loaded from; no callee behaviour is claimed.')
        lines.append('Value-witness admission: ABI non-throwing only for calls proven to use a value witness function slot.')
        for name in ('indirect_target_shape_model','value_witness_admission_model'):
            lines.append(name+': '+safe(report.get(name)))
        for key in ('indirect_target_shape_counts','value_witness_admission_counts','value_witness_refusal_condition_counts'):
            table=report.get(key) or {}
            if type(table) is not dict:raise InputError('swift_broad_text_shape','Indirect target counts must be an object')
            for name in sorted(table)[:64]:
                lines.append(key+'.'+safe(name)+': '+safe(table[name]))
    calls=report.get('calls',[])
    if type(calls) is not list:raise InputError('swift_broad_text_shape','Calls must be an array')
    size=sum(len(line)+1 for line in lines);shown=0
    for row in calls[:256]:
        if type(row) is not dict:raise InputError('swift_broad_text_shape','Call must be an object')
        verdict=row.get('validation') or row.get('admission') or {}
        if type(verdict) is not dict:raise InputError('swift_broad_text_shape','Verdict must be an object')
        detail=['Call '+safe(row.get('call_pc'))+': '+safe(verdict.get('status'))+'; '+safe(verdict.get('reason'))]
        candidate=row.get('candidate') or {}
        if type(candidate) is not dict:raise InputError('swift_broad_text_shape','Candidate must be an object')
        post=candidate.get('post_call') or {}
        if type(post) is not dict:raise InputError('swift_broad_text_shape','Post-call must be an object')
        admission=row.get('admission') or {}
        if got and type(admission) is dict and admission.get('model_version')=='swift-broad-got-callsite-v1':
            declaration=admission.get('declaration') or {}
            if type(declaration) is not dict:raise InputError('swift_broad_text_shape','Declaration must be an object')
            detail.append('  import '+safe(admission.get('symbol'))+'; slot '+safe(admission.get('slot_address'))+
                         '; '+safe(admission.get('call_kind'))+'; declaration '+safe(declaration.get('status')))
        elif imports and type(admission) is dict and admission.get('model_version')=='swift-broad-import-callsite-v1':
            declaration=admission.get('declaration') or {}
            if type(declaration) is not dict:raise InputError('swift_broad_text_shape','Declaration must be an object')
            detail.append('  import '+safe(admission.get('symbol'))+'; stub '+safe(admission.get('callee_stub_pc'))+
                         '; '+safe(admission.get('call_kind'))+'; declaration '+safe(declaration.get('status')))
        else:
            detail.append('  test '+safe(post.get('test_pc'))+'; success '+safe(post.get('success_successor_pc'))+
                         '; error '+safe(post.get('error_successor_pc')))
        if report.get('profile') in caller_profiles and 'caller_error_test' in row:
            fact=row['caller_error_test']
            if type(fact) is not dict:raise InputError('swift_broad_text_shape','Caller error test must be an object')
            detail.append('  caller x21 shape '+safe(fact.get('shape'))+'; no callee behaviour claim')
        if indirect and 'indirect_target_shape' in row:
            shape=row['indirect_target_shape'];witness=row.get('value_witness_admission')
            if type(shape) is not dict or type(witness) is not dict:
                raise InputError('swift_broad_text_shape','Indirect target records must be objects')
            detail.append('  indirect target '+safe(shape.get('class'))+'; slot '+safe(shape.get('slot_offset'))+
                         '; reason '+safe(shape.get('unknown_reason'))+'; no callee behaviour claim')
            detail.append('  value witness admitted '+safe(witness.get('admitted'))+'; '+safe(witness.get('provenance_kind'))+
                         '; condition '+safe(witness.get('first_failing_condition'))+'; '+safe(witness.get('reason')))
        cost=sum(len(line)+1 for line in detail)
        if size+cost>MAX_TEXT_BYTES-128:break
        lines.extend(detail);size+=cost;shown+=1
    if len(calls)>shown:lines.append('Additional call rows omitted from text: '+str(len(calls)-shown))
    return '\n'.join(lines)+'\n'
