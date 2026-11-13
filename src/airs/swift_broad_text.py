"""Bounded terminal-safe rendering of recorded broad-profile checks."""
import json
from .types import InputError

MAX_TEXT_BYTES=1024*1024


MAX_TABLE_LINES=64


def _object(report,name):
    value=report.get(name)
    if type(value) is not dict:raise InputError('swift_broad_text_shape',name+' must be an object')
    return value


def _v4_lines(report,safe):
    # The v4 header, accounting and import table. Every group is a bounded object; table entries are capped.
    lines=['Import effect admission: a declaration licenses by name only; the callee, its binding and its result are not claimed.']
    capabilities=_object(report,'capabilities')
    for name in ('report_model','effect_admission_model','declaration_syntax_model','grammar_pin',
                 'caller_error_test_model'):
        lines.append('capabilities.'+name+': '+safe(capabilities.get(name)))
    for name in ('premises','not_claimed'):
        values=capabilities.get(name)
        if type(values) is not list:raise InputError('swift_broad_text_shape','capabilities.'+name+' must be an array')
        for value in values[:16]:lines.append('capabilities.'+name+': '+safe(value))
    for group in ('limits','omission_causes','omitted_by_kind','unselected_call_counts','scan'):
        table=_object(report,group)
        for name in sorted(table)[:64]:lines.append(group+'.'+safe(name)+': '+safe(table[name]))
    block=_object(report,'import_calls')
    for name in ('complete','attributed_calls','attributed_swift_calls','distinct_symbols'):
        lines.append('import_calls.'+name+': '+safe(block.get(name)))
    residual=block.get('residual')
    if type(residual) is not dict:raise InputError('swift_broad_text_shape','import_calls.residual must be an object')
    for name in sorted(residual)[:16]:lines.append('import_calls.residual.'+safe(name)+': '+safe(residual[name]))
    entries=block.get('entries')
    if type(entries) is not list:raise InputError('swift_broad_text_shape','import_calls.entries must be an array')
    for entry in entries[:MAX_TABLE_LINES]:
        if type(entry) is not dict:raise InputError('swift_broad_text_shape','Import table entry must be an object')
        lines.append('import '+safe(entry.get('symbol'))+': '+safe(entry.get('decision'))+'; reason '+safe(entry.get('reason'))+
                     '; calls '+safe(entry.get('calls'))+'; retained '+safe(entry.get('retained'))+
                     '; skipped '+safe(entry.get('skipped_non_throwing'))+'; not swift '+safe(entry.get('not_swift_calls'))+
                     '; omitted '+safe(entry.get('omitted')))
    if len(entries)>MAX_TABLE_LINES:lines.append('Additional import table entries omitted from text: '+str(len(entries)-MAX_TABLE_LINES))
    grid=_object(report,'decision_by_shape')
    for decision in sorted(grid)[:8]:
        shapes=grid[decision]
        if type(shapes) is not dict:raise InputError('swift_broad_text_shape','decision_by_shape rows must be objects')
        for shape in sorted(shapes)[:8]:lines.append('decision_by_shape.'+safe(decision)+'.'+safe(shape)+': '+safe(shapes[shape]))
    summary=_object(report,'decision_summary')
    names=summary.get('names')
    if type(names) is not dict:raise InputError('swift_broad_text_shape','decision_summary.names must be an object')
    for name in sorted(names)[:8]:lines.append('decision_summary.names.'+safe(name)+': '+safe(names[name]))
    reasons=summary.get('undecided_by_reason')
    if type(reasons) is not dict:raise InputError('swift_broad_text_shape','decision_summary.undecided_by_reason must be an object')
    for name in sorted(reasons)[:32]:
        item=reasons[name]
        if type(item) is not dict:raise InputError('swift_broad_text_shape','Undecided reason entries must be objects')
        lines.append('decision_summary.undecided_by_reason.'+safe(name)+': names '+safe(item.get('names'))+'; calls '+safe(item.get('calls')))
    return lines


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
            or (report.get('model_version')=='swift-broad-error-flow-extended-v4'
                and report.get('profile')=='broad-extended-v4')
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
    caller_profiles=('broad-extended-v2','broad-extended-v3','broad-extended-v4')
    v4=report.get('profile')=='broad-extended-v4'
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
    indirect=report.get('profile') in ('broad-extended-v3','broad-extended-v4')
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
    if v4:lines.extend(_v4_lines(report,safe))
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
                         '; '+safe(admission.get('call_kind'))+'; declaration '+safe(declaration.get('decision' if v4 else 'status')))
        elif imports and type(admission) is dict and admission.get('model_version')=='swift-broad-import-callsite-v1':
            declaration=admission.get('declaration') or {}
            if type(declaration) is not dict:raise InputError('swift_broad_text_shape','Declaration must be an object')
            detail.append('  import '+safe(admission.get('symbol'))+'; stub '+safe(admission.get('callee_stub_pc'))+
                         '; '+safe(admission.get('call_kind'))+'; declaration '+safe(declaration.get('decision' if v4 else 'status')))
        else:
            detail.append('  test '+safe(post.get('test_pc'))+'; success '+safe(post.get('success_successor_pc'))+
                         '; error '+safe(post.get('error_successor_pc')))
        if report.get('profile') in caller_profiles and 'caller_error_test' in row:
            fact=row['caller_error_test']
            if type(fact) is not dict:raise InputError('swift_broad_text_shape','Caller error test must be an object')
            detail.append('  caller x21 shape '+safe(fact.get('shape'))+'; no callee behaviour claim')
        if v4 and 'effect_admission' in row:
            effect=row['effect_admission']
            if type(effect) is not dict:raise InputError('swift_broad_text_shape','Effect admission must be an object')
            detail.append('  licence '+safe(effect.get('licence_class'))+'; caller relation '+safe(effect.get('caller_relation'))+
                          '; declared by name only, no callee behaviour claim')
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
