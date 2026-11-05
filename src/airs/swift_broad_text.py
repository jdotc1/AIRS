"""Bounded terminal-safe rendering of recorded broad-profile checks."""
import json
from .types import InputError

MAX_TEXT_BYTES=1024*1024


def render_swift_broad_text(report):
    if (type(report) is not dict or not (report.get('model_version')=='swift-broad-error-flow-v1'
            or (report.get('model_version')=='swift-broad-error-flow-large-v1'
                and report.get('profile')=='broad-large-v1')
            or (report.get('model_version')=='swift-broad-error-flow-extended-v1'
                and report.get('profile')=='broad-extended-v1'))):
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
        detail.append('  test '+safe(post.get('test_pc'))+'; success '+safe(post.get('success_successor_pc'))+
                     '; error '+safe(post.get('error_successor_pc')))
        cost=sum(len(line)+1 for line in detail)
        if size+cost>MAX_TEXT_BYTES-128:break
        lines.extend(detail);size+=cost;shown+=1
    if len(calls)>shown:lines.append('Additional call rows omitted from text: '+str(len(calls)-shown))
    return '\n'.join(lines)+'\n'
