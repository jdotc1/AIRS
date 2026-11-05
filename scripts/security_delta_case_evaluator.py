#!/usr/bin/env python3
"""Adjudicate retained AIRS observations against independent raw facts.
No AIRS imports, capture, executable loading, or canonical-ID generation.
Unknown facts count in the denominator and never become agreement.
"""
import argparse
import base64
import os
import stat
from security_delta_corpus import load_manifests, open_directory_no_follow, CorpusRefusal
import collections
import json
from pathlib import Path
from security_delta_independent_oracle import write_document

class Unresolved(ValueError): pass

def compare_value(actual, expected):
    if actual is None or expected is None:
        return actual is expected
    a, b = actual['type'], expected['type']
    if a in ('signed','unsigned','normalizedInteger') and b == 'integer':
        return actual['value'] == expected['decimal']
    if a == 'boolean' and b == 'boolean': return type(actual['value']) is bool and actual['value'] == expected['value']
    if a == 'string' and b == 'string': return actual['value'].encode('utf-8') == expected['value'].encode('utf-8')
    if a in ('signed','unsigned','normalizedInteger','boolean','string') or b in ('integer','boolean','string'):
        return False
    if a == 'array' and b == 'array':
        return len(actual['value']) == len(expected['items']) and all(compare_value(x,y) for x,y in zip(actual['value'],expected['items']))
    if a == 'dictionary' and b == 'dictionary':
        aa=actual['value']; bb=expected['entries']
        ak=[x['key'].encode('utf-8') for x in aa]; bk=[x['key'].encode('utf-8') for x in bb]
        if len(set(ak)) != len(ak) or len(set(bk)) != len(bk): raise Unresolved('duplicate_typed_keys')
        lookup={x['key'].encode('utf-8'):x['value'] for x in bb}
        return set(ak)==set(bk) and all(compare_value(x['value'],lookup[x['key'].encode('utf-8')]) for x in aa)
    if a == 'realBits' and b == 'real': return actual['value'] == expected['bits']
    if a == 'dateBits' and b == 'date': raise Unresolved('oracle_date_bit_fidelity_unavailable')
    if a == 'data' and b == 'data': return actual['value'] == expected['base64']
    raise Unresolved('unsupported_typed_comparison')

def string(value): return {'type':'string','value':value}
def array(values): return {'type':'array','items':values}
def dictionary(values): return {'type':'dictionary','entries':[{'key':k,'value':v} for k,v in sorted(values.items(),key=lambda row:row[0].encode('utf-8'))]}
def version(value): return '.'.join(str(n) for n in (value>>16,(value>>8)&255,value&255))

def selected_slice(image, reference=None):
    if not image or image.get('state')!='observed': raise Unresolved('oracle_image_unavailable')
    slices=[s for s in image['slices'] if s['identity']['cpu_type']==0x100000c and s['identity']['cpu_subtype']==0]
    if len(slices)!=1: raise Unresolved('oracle_raw_slice_unresolved')
    item=slices[0]
    if reference and reference.get('slice'):
        r=reference['slice']; i=item['identity']
        # AIRS stores the original header word read in network byte order.
        raw_magic={0xfeedfacf:0xcffaedfe,0xfeedface:0xcefaedfe}.get(i['magic'],i['magic'])
        if any(r.get(k)!=v for k,v in {'cpuType':i['cpu_type'],'cpuSubtype':i['cpu_subtype'],'index':i['slice_index'],'offset':i['offset'],'size':i['size'],'headerMagic':raw_magic,'recordedSHA256':item['slice_digest']}.items()):
            raise Unresolved('raw_slice_reference_disagrees')
    return item

def loader_values(slice):
    rows=[]
    for row in slice['loader']:
        values={'architecture':string('arm64'),'command':string(row['kind']),'path':string(row['path'])}
        for old,new in [('current_version','currentVersion'),('compatibility_version','compatibilityVersion')]:
            if old in row: values[new]=string(version(row[old]))
        rows.append(dictionary(values))
    return array(rows)

def qualified_signature(slice):
    # Retained pre-repair captures contain enough slot/range metadata to assess
    # applicability, without re-reading or re-hashing unchanged source bytes.
    sig=slice['signature']
    if sum(c['command']==0x1d for c in slice['commands'])>1: raise Unresolved('signature_command_ambiguous')
    if sig['state']=='absent': return sig
    if sig['state']!='observed': raise Unresolved('oracle_signature_unavailable')
    slots=sig['slots']; types=[s['type'] for s in slots]
    if len(set(types))!=len(types): raise Unresolved('signature_slot_ambiguous')
    for n,slot in enumerate(slots):
        if slot['type']==5 and slot['magic']!=0xfade7171: raise Unresolved('entitlement_blob_magic_invalid')
        if any(slot['offset']<o['offset']+o['size'] and o['offset']<slot['offset']+slot['size'] for o in slots[:n]): raise Unresolved('signature_slot_ambiguous')
    return sig

def image_metadata(path, facts):
    owners=[(source,record) for source,record in facts.get('plists',{}).items() if source.endswith('Info.plist') and record.get('state')=='observed' and plist_component(source,record)==path]
    if len(owners)>1:raise Unresolved('ambiguous_executable_metadata')
    return owners[0] if owners else (None,None)

def image_kind(path, facts):
    source,metadata=image_metadata(path,facts)
    if source=='Contents/Info.plist':return 'app'
    if metadata:
        containers=[root for root in facts.get('bundle_roots',[]) if root and path.startswith(root+'/')]
        if containers:
            root=max(containers,key=lambda x:len(x.encode('utf-8')))
            return {'.app':'app','.xpc':'xpc','.appex':'extension','.framework':'framework'}.get(Path(root).suffix.lower(),'image')
    return 'helper' if path.startswith(('Contents/Helpers/','Contents/Library/LoginItems/')) else 'image'


def source_fact(observation, side, facts):
    category, subject=observation['category'],observation['subject']
    refs=[r for r in observation['evidence'] if r['side']==side and r['category']==category]
    reference=next((r for r in refs if not r.get('evidenceKey','').startswith('declaration:binding:')),None)
    if not reference: raise Unresolved('qualified_source_reference_unavailable')
    path=reference['relativeSource']
    if category in ('loadCommands','signatureEvidence','entitlements','componentInventory') and path.encode('utf-8')!=observation['componentPath'].encode('utf-8'): raise Unresolved('component_source_binding_mismatch')
    image=facts.get('images',{}).get(path)
    if category in ('informationPropertyList','privacyManifest'):
        source=facts.get('plists',{}).get(path)
        info_path=path if category=='informationPropertyList' else privacy_info_path(path)
        owner=plist_component(info_path,facts.get('plists',{}).get(info_path,{})) if info_path else None
        if not owner or owner.encode('utf-8')!=observation['componentPath'].encode('utf-8'): raise Unresolved('component_source_binding_mismatch')
        if source and source['state']=='observed':
            if subject=='presence': return 'observed',None
            if subject.startswith('key:'):
                value=source['values'].get(subject[4:]); return ('observed' if value is not None else 'absent'),value
        if category=='privacyManifest':
            recorded=facts.get('privacy',{}).get(path,{}).get('state')
            complete=facts.get('scope',{}).get('state')=='complete'
            obstructed=any(path==x['path'] or path.startswith(x['path']+'/') for x in facts.get('exclusions',[]))
            if recorded=='absent' or (not source and complete and not obstructed):return 'absent',None
        raise Unresolved('oracle_declaration_unavailable')
    if category=='loadCommands':
        value=loader_values(selected_slice(image,reference))
        if subject=='presence': return 'observed',None
        if subject=='key:commands': return 'observed',value
        if subject.startswith('dependency:'):
            _,kind,path=subject.split(':',2)
            values=[row for row in value['items'] if {e['key']:e['value'] for e in row['entries']}['command']==string(kind) and {e['key']:e['value'] for e in row['entries']}['path']==string(path)]
            # Dependency observations retain complete duplicate groups as arrays.
            return ('observed' if values else 'absent'),array(values) if values else None
        raise Unresolved('unsupported_loader_subject')
    if category=='signatureEvidence':
        if not image or image.get('state')!='observed': raise Unresolved('oracle_image_unavailable')
        if subject=='containerSHA256': return 'observed',string(image['container_digest'])
        slice=selected_slice(image,reference)
        if subject=='sliceSHA256': return 'observed',string(slice['slice_digest'])
        sig=qualified_signature(slice)
        if subject=='signatureState':
            state='signatureAbsent' if sig['state']=='absent' else 'collected' if any(s['type'] in (5,7) for s in sig['slots']) else 'entitlementsAbsent'
            return 'observed',string(state)
        if subject=='signatureSHA256': return ('observed',string(sig['digest'])) if sig['state']=='observed' else ('absent',None)
        if subject in ('xmlSlotSHA256','derSlotSHA256'):
            slot=next((s for s in sig.get('slots',[]) if s['type']==(5 if subject=='xmlSlotSHA256' else 7)),None)
            return ('observed',string(slot['digest'])) if slot else ('absent',None)
        raise Unresolved('unsupported_signature_subject')
    if category=='entitlements':
        slice=selected_slice(image,reference); sig=qualified_signature(slice)
        xml=next((s for s in sig.get('slots',[]) if s['type']==5),None)
        if not xml:
            if any(s['type']==7 for s in sig.get('slots',[])): raise Unresolved('der_semantics_unexamined')
            return 'absent',None
        if xml.get('entitlements_state')!='observed': raise Unresolved('oracle_entitlements_unavailable')
        if subject=='presence': return 'observed',None
        if subject.startswith('key:'):
            value=xml['entitlements'].get(subject[4:]);return ('observed' if value is not None else 'absent'),value
        raise Unresolved('unsupported_entitlement_subject')
    if category=='componentInventory':
        if subject=='component':
            if image and image.get('state')=='observed':return 'observed',None
            if not image and facts.get('scope',{}).get('state')=='complete' and not facts.get('exclusions'):return 'absent',None
            raise Unresolved('oracle_component_scope_incomplete')
        if subject=='kind':
            if not image or image.get('state')!='observed':raise Unresolved('oracle_image_unavailable')
            return 'observed',string(image_kind(path,facts))
        if subject in ('bundleIdentifier','version'):
            _,metadata=image_metadata(path,facts)
            if not metadata:raise Unresolved('oracle_bundle_label_unavailable')
            value=metadata['values'].get('CFBundleIdentifier' if subject=='bundleIdentifier' else 'CFBundleShortVersionString')
            if not value or value.get('type')!='string' or not value['value']:raise Unresolved('oracle_bundle_label_unavailable')
            return 'observed',value
        if subject.startswith('minimumOS:'):
            architecture=subject.split(':',1)[1]
            cpu,subtype={'arm64':(0x100000c,0),'x86_64':(0x1000007,3)}.get(architecture,(None,None))
            if not image or image.get('state')!='observed':raise Unresolved('oracle_image_unavailable')
            selected=[s for s in image['slices'] if s['identity']['cpu_type']==cpu and s['identity']['cpu_subtype']==subtype]
            if len(selected)!=1:raise Unresolved('oracle_raw_slice_unresolved')
            minimums=selected[0].get('additional_minimum_os',[])
            if len(minimums)!=1 or minimums[0]['platform']!=1:raise Unresolved('oracle_minimum_os_unavailable')
            return 'observed',string(version(minimums[0]['minimum']))
    if category=='componentInventory' and subject=='architectures':
        if not image or image.get('state')!='observed': raise Unresolved('oracle_image_unavailable')
        return 'observed',array([string(a) for a in sorted(set(s['architecture'] for s in image['slices']))])
    raise Unresolved('independent_subject_not_yet_qualified')

def dependency_expectation(observation, facts):
    _,kind,path=observation['subject'].split(':',2)
    groups=[]
    for side in ('previous','current'):
        refs=[r for r in observation['evidence'] if r['side']==side and r['category']=='loadCommands']
        if len(refs)!=1: raise Unresolved('qualified_source_reference_unavailable')
        image=facts[side].get('images',{}).get(refs[0]['relativeSource'])
        rows=selected_slice(image,refs[0])['loader']
        group=[{k:r[k] for k in ('kind','path','current_version','compatibility_version') if k in r} for r in rows if r['kind']==kind and r['path'].encode('utf-8')==path.encode('utf-8')]
        groups.append(sorted(json.dumps(r,sort_keys=True) for r in group))
    a,b=map(len,groups)
    changed=a!=b
    states=[('observed' if n else 'absent',{'type':'integer','decimal':str(n),'representation':'unspecified'} if changed else None) for n in (a,b)]
    disposition='unchanged' if groups[0]==groups[1] else 'observedAddition' if not a else 'observedRemoval' if not b else 'observedChange'
    return states,disposition


def adjudicate_observation(observation, facts):
    result={'observation_id':observation.get('id'),'category':observation['category'],'subject':observation['subject'],'component_path':observation['componentPath'],'disposition':observation['disposition']}
    if observation['disposition'] in ('unresolved','declined'):
        return dict(result,state='unresolved',reason='airs_conclusion_bounded')
    try:
        dependency=dependency_expectation(observation,facts) if observation['category']=='loadCommands' and observation['subject'].startswith('dependency:') else None
        expected=[]
        for side in ('previous','current'):
            state,value=dependency[0][0 if side=='previous' else 1] if dependency else source_fact(observation,side,facts[side]);expected.append((state,value))
            if state!=observation[side+'State'] or not compare_value(observation.get(side+'Value'),value):
                return dict(result,state='disagreement',reason=side+'_recorded_value_or_state_disagrees',expected=expected)
        a,b=expected
        disposition='unchanged' if a==b else 'observedAddition' if a[0]=='absent' else 'observedRemoval' if b[0]=='absent' else 'observedChange'
        if dependency: disposition=dependency[1]
        if disposition!=observation['disposition']:
            # Raw plist data cannot decide representation-only API differences.
            if any(v and v.get('type')=='integer' for _,v in expected): raise Unresolved('numeric_representation_unspecified')
            return dict(result,state='disagreement',reason='transition_disagrees',expected_disposition=disposition)
        return dict(result,state='supported')
    except Unresolved as error: return dict(result,state='unresolved',reason=str(error))

def plist_component(path, source):
    value=source.get('values',{}).get('CFBundleExecutable')
    if not value or value.get('type')!='string': return path if path=='Contents/Info.plist' else None
    name=value['value']
    if not name or '/' in name or name in ('.','..'): return None
    if path.endswith('Contents/Info.plist'): return path[:-len('Info.plist')]+'MacOS/'+name
    if path.endswith('Resources/Info.plist'): return path[:-len('Resources/Info.plist')]+name
    return None

def privacy_info_path(path):
    suffix='Contents/Resources/PrivacyInfo.xcprivacy'
    if path.endswith(suffix): return path[:-len(suffix)]+'Contents/Info.plist'
    suffix='Resources/PrivacyInfo.xcprivacy'
    if path.endswith(suffix): return path[:-len(suffix)]+'Resources/Info.plist'
    return None


def enumerate_changes(facts):
    """Independent expected-change population; never consults AIRS output."""
    rows=[]
    def emit(path,category,subject,a,b):
        if a==b:return
        disposition='observedAddition' if a is None else 'observedRemoval' if b is None else 'observedChange'
        rows.append(dict(component_path=path,category=category,subject=subject,disposition=disposition))
    previous,current=facts['previous'],facts['current']
    for path in sorted(set(previous.get('plists',{})) & set(current.get('plists',{})),key=lambda p:p.encode('utf-8')):
        a,b=previous['plists'][path],current['plists'][path]
        if a['state']!='observed' or b['state']!='observed':continue
        if path.endswith('Info.plist'):
            owner_a,owner_b=plist_component(path,a),plist_component(path,b)
            if not owner_a or not owner_b or owner_a.encode('utf-8')!=owner_b.encode('utf-8'):continue
            for key in ('CFBundleIdentifier','CFBundleShortVersionString','CFBundleVersion','CFBundlePackageType','LSMinimumSystemVersion','CFBundleSupportedPlatforms'):
                emit(owner_a,'informationPropertyList','key:'+key,a['values'].get(key),b['values'].get(key))
        elif path.endswith('PrivacyInfo.xcprivacy'):
            info=privacy_info_path(path)
            owner=plist_component(info,previous.get('plists',{}).get(info,{}))
            current_owner=plist_component(info,current.get('plists',{}).get(info,{}))
            if owner and current_owner and owner.encode('utf-8')!=current_owner.encode('utf-8'):
                if a['values']!=b['values']:rows.append(dict(component_path=owner,category='privacyManifest',subject='source_correspondence',disposition='unresolved',reason='exact_executable_correspondence_unaccepted'))
                continue
            if owner and current_owner:
                for key in sorted(set(a['values'])|set(b['values']),key=lambda k:k.encode('utf-8')):
                    emit(owner,'privacyManifest','key:'+key,a['values'].get(key),b['values'].get(key))
    for path in sorted(set(previous.get('images',{})) & set(current.get('images',{})),key=lambda p:p.encode('utf-8')):
        a,b=previous['images'][path],current['images'][path]
        if a['state']!='observed' or b['state']!='observed':continue
        emit(path,'signatureEvidence','containerSHA256',a['container_digest'],b['container_digest'])
        try: sa,sb=selected_slice(a),selected_slice(b)
        except Unresolved:continue
        emit(path,'signatureEvidence','sliceSHA256',sa['slice_digest'],sb['slice_digest'])
        emit(path,'loadCommands','key:commands',loader_values(sa),loader_values(sb))
        groups=[]
        for slice in (sa,sb):
            group={}
            for row in slice['loader']:
                if row['kind'] not in ('load','weak','reexport','upward','lazy'):continue
                key=(row['kind'],row['path']);group.setdefault(key,[]).append({k:row[k] for k in ('kind','path','current_version','compatibility_version') if k in row})
            groups.append({k:sorted(json.dumps(r,sort_keys=True) for r in v) for k,v in group.items()})
        for key in sorted(set(groups[0])|set(groups[1]),key=lambda k:(k[0].encode('utf-8'),k[1].encode('utf-8'))):
            emit(path,'loadCommands','dependency:'+key[0]+':'+key[1],groups[0].get(key),groups[1].get(key))
        try: siga,sigb=qualified_signature(sa),qualified_signature(sb)
        except Unresolved:continue
        emit(path,'signatureEvidence','signatureSHA256',siga.get('digest'),sigb.get('digest'))
        for kind,subject in ((5,'xmlSlotSHA256'),(7,'derSlotSHA256')):
            slots=[next((s for s in sig.get('slots',[]) if s['type']==kind),None) for sig in (siga,sigb)]
            emit(path,'signatureEvidence',subject,*[s['digest'] if s else None for s in slots])
        xml=[next((s for s in sig.get('slots',[]) if s['type']==5 and s.get('entitlements_state')=='observed'),None) for sig in (siga,sigb)]
        if all(xml):
            values=[s['entitlements'] for s in xml]
            for key in sorted(set(values[0])|set(values[1]),key=lambda k:k.encode('utf-8')):
                emit(path,'entitlements','key:'+key,values[0].get(key),values[1].get(key))
    return rows

def evaluate_expected_changes(report, expected):
    result=[]
    for row in expected:
        if row['disposition']=='unresolved':
            result.append(dict(row,state='unresolved'));continue
        related=[o for o in report['observations'] if o['componentPath'].encode('utf-8')==row['component_path'].encode('utf-8') and o['category']==row['category']]
        exact=next((o for o in related if o['subject'].encode('utf-8')==row['subject'].encode('utf-8')),None)
        if exact:
            state='true_positive' if exact['disposition']==row['disposition'] else 'unresolved' if exact['disposition'] in ('unresolved','declined') else 'false_negative'
        else:
            state='unresolved' if not related or any(o['subject'] in ('presence','slice','one-sided-context') and o['disposition'] in ('unresolved','declined') for o in related) else 'false_negative'
        result.append(dict(row,state=state))
    return result


def qualify_finding(finding, observations, facts, inventories):
    contributing=[observations.get(i) for i in finding['observationIDs']]
    if not contributing or any(o is None for o in contributing):return dict(state='disagreement',reason='dangling_observation_reference')
    required={json.dumps(r,sort_keys=True) for o in contributing for r in o['evidence']}
    retained={json.dumps(r,sort_keys=True) for r in finding['evidence']}
    if not required.issubset(retained) or len(finding['evidence'])>32:return dict(state='disagreement',reason='contributing_evidence_omitted')
    kind=finding['kind']
    changed=[o for o in contributing if o['disposition'] in ('observedAddition','observedRemoval','observedChange')]
    if kind=='componentMultiCategory':
        paths={o['componentPath'].encode('utf-8') for o in changed}
        categories={o['category'] for o in changed if o['category']!='componentInventory'}
        return dict(state='supported' if len(paths)==1 and len(categories)>=2 else 'disagreement',reason='same_component_cross_category_trigger')
    if kind in ('componentAdded','componentRemoved','xpcAdded'):
        wanted='observedRemoval' if kind=='componentRemoved' else 'observedAddition'
        valid=len(contributing)==1 and all(o['category']=='componentInventory' and o['subject']=='component' and o['disposition']==wanted for o in contributing)
        if valid and kind=='xpcAdded':
            try:valid=image_kind(contributing[0]['componentPath'],facts['current'])=='xpc'
            except (Unresolved,KeyError):return dict(state='unresolved',reason='independent_xpc_kind_unavailable')
        return dict(state='supported' if valid else 'disagreement',reason='component_surface_trigger')
    if kind in ('declarationChanged','signatureEvidenceChanged'):
        valid=bool(changed) and len(changed)==len(contributing) and all((o['category']=='signatureEvidence')==(kind=='signatureEvidenceChanged') for o in contributing)
        return dict(state='supported' if valid else 'disagreement',reason='declaration_change_trigger')
    if kind in ('coverageIncomplete','evidenceConflict'):return dict(state='unresolved',reason='bounded_or_conflict_conclusion')
    if kind not in ('relatedComponents','repeatedDeclaration'):return dict(state='unresolved',reason='unsupported_finding_kind')
    if len({o['componentPath'].encode('utf-8') for o in changed})<2:return dict(state='disagreement',reason='related_components_trigger')
    def ancestors(path,side):
        records=inventories[side]['components'];lookup={r['id']:r for r in records}
        record=next((r for r in records if r['relativePath'].encode('utf-8')==path.encode('utf-8')),None)
        result=set();visited=set()
        while record and record.get('parentID'):
            identity=record['parentID']
            if identity in visited or identity not in lookup:raise Unresolved('recorded_ancestry_invalid')
            visited.add(identity);parent=lookup[identity]
            source,_=image_metadata(parent['relativePath'],facts[side])
            if not source:raise Unresolved('independent_parent_metadata_unavailable')
            suffix='Contents/Info.plist' if source.endswith('Contents/Info.plist') else 'Resources/Info.plist'
            prefix=source[:-len(suffix)]
            if not record['relativePath'].encode('utf-8').startswith(prefix.encode('utf-8')):raise Unresolved('physical_parent_relationship_disagrees')
            result.add(parent['relativePath'].encode('utf-8'));record=parent
        return result
    try:
        common=None
        for observation in changed:
            sides=[]
            for side in ('previous','current'):
                if any(r['relativePath'].encode('utf-8')==observation['componentPath'].encode('utf-8') for r in inventories[side]['components']):sides.append(ancestors(observation['componentPath'],side))
            shared=set.intersection(*sides) if sides else set()
            common=shared if common is None else common & shared
        before_paths={r['relativePath'].encode('utf-8') for r in inventories['previous']['components']}
        after_paths={r['relativePath'].encode('utf-8') for r in inventories['current']['components']}
        common=(common or set()) & before_paths & after_paths
        if not common:return dict(state='disagreement',reason='shared_recorded_ancestor_unproven')
        if kind=='repeatedDeclaration':
            transitions={(o['category'],o['subject'].encode('utf-8'),o['disposition'],o['previousState'],o['currentState'],json.dumps(o.get('previousValue'),sort_keys=True),json.dumps(o.get('currentValue'),sort_keys=True)) for o in changed}
            if len(transitions)!=1:return dict(state='disagreement',reason='repeated_transition_disagrees')
        return dict(state='supported',reason='recorded_ancestry_and_source_facts')
    except (Unresolved,KeyError) as error:return dict(state='unresolved',reason=str(error))


def evaluate_case(report, facts, inventories=None):
    rows=[adjudicate_observation(o,facts) for o in report['observations']]
    index={r['observation_id']:r for r in rows}
    finding_rows=[]
    for finding in report['findings']:
        contributing=[index.get(i) for i in finding['observationIDs']]
        state='disagreement' if any(r and r['state']=='disagreement' for r in contributing) else 'supported' if contributing and all(r and r['state']=='supported' for r in contributing) else 'unresolved'
        rule=qualify_finding(finding,{o['id']:o for o in report['observations']},facts,inventories or {}) if state=='supported' else {'state':state,'reason':'constituent_source_state'}
        finding_rows.append({'finding_id':finding['id'],'kind':finding['kind'],**rule})
    expected=evaluate_expected_changes(report,enumerate_changes(facts))
    return {'expected_changes':expected,'expected_change_counts':dict(collections.Counter(r['state'] for r in expected)),'observations':rows,'findings':finding_rows,'observation_counts':dict(collections.Counter(r['state'] for r in rows)),
            'finding_counts':dict(collections.Counter(r['state'] for r in finding_rows)),
            'limitations':['Finding support includes constituent raw facts, required evidence and independently checked recorded ancestry/rule triggers. Wording is separately source-reviewed; no causal/runtime claim.',
            'Expected-change enumeration covers exact-location paired Info keys, present privacy keys, captured loader groups and raw byte/signature observations; missing sources, component surface and unsupported DER/minimum-OS are outside this denominator.']}

def parse_json(data):
    if len(data)>32*1048576: raise Unresolved('document_byte_limit')
    depth=0; quoted=False; escaped=False
    for c in data:
        if quoted:
            if escaped: escaped=False
            elif c==92: escaped=True
            elif c==34: quoted=False
        elif c==34: quoted=True
        elif c in (91,123):
            depth+=1
            if depth>64: raise Unresolved('document_depth_limit')
        elif c in (93,125): depth-=1
    def pairs(rows):
        result={}
        for k,v in rows:
            if k in result: raise Unresolved('duplicate_json_key')
            result[k]=v
        return result
    try:
        value=json.loads(data.decode('utf-8','strict'),object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(Unresolved('nonfinite_number')))
    except (UnicodeError,RecursionError,json.JSONDecodeError) as error: raise Unresolved('invalid_json') from error
    remaining=1000000
    def bound(item):
        nonlocal remaining
        remaining-=1
        if remaining<0: raise Unresolved('document_node_limit')
        if isinstance(item,dict):
            for v in item.values():bound(v)
        elif isinstance(item,list):
            for v in item:bound(v)
    bound(value)
    return value

def load_json(path,maximum=32*1048576):
    parent=open_directory_no_follow(path.parent)
    try: fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
    finally: os.close(parent)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>maximum: raise Unresolved('document_byte_limit')
        data=bytearray()
        while len(data)<=maximum:
            chunk=os.read(fd,min(65536,maximum+1-len(data)))
            if not chunk:break
            data.extend(chunk)
        after=os.fstat(fd)
        if len(data)>maximum: raise Unresolved('document_byte_limit')
        if (before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise Unresolved('source_stale')
        return parse_json(data)
    finally:os.close(fd)

def chunks(values):
    if not isinstance(values,list) or not 1<=len(values)<=64: raise Unresolved('invalid_archive_chunks')
    result=bytearray()
    for value in values:
        if not isinstance(value,str) or len(value)>32*1048576: raise Unresolved('invalid_archive_chunks')
        try:part=base64.b64decode(value,validate=True)
        except ValueError as error:raise Unresolved('invalid_archive_chunks') from error
        if len(part)>32*1048576-len(result):raise Unresolved('document_byte_limit')
        result.extend(part)
    return parse_json(result)

def verify_reference_binding(reference,path,inventories):
    side=reference['side']
    if side not in inventories or reference['inventoryID']!=inventories[side]['id']:raise Unresolved('side_inventory_binding_mismatch')
    identity=reference.get('componentID')
    if identity is None:
        if reference['category']!='componentInventory' or reference.get('evidenceKey')!='scope':raise Unresolved('component_reference_binding_mismatch')
        return
    if not isinstance(identity,str) or not identity:raise Unresolved('component_reference_binding_mismatch')
    component=next((c for c in inventories[side]['components'] if c['id']==identity),None)
    if not component or component['relativePath'].encode('utf-8')!=path.encode('utf-8'):raise Unresolved('component_reference_binding_mismatch')


def verify_retained_binding(report,archive,inventories):
    if report!=chunks(archive['reportChunks']):raise Unresolved('report_archive_mismatch')
    if report['identity']['architecture']!='arm64':raise Unresolved('unsupported_architecture')
    source=chunks(archive['reviewChunks'])
    attachments={a['id']:a for a in source['attachments']}
    if len(attachments)!=len(source['attachments']):raise Unresolved('duplicate_source_identity')
    reviews=[a for a in attachments.values() if a['kind']=='airs.component.review']
    if len(reviews)!=1:raise Unresolved('source_review_unavailable')
    review=chunks(reviews[0]['chunks'])
    for side in ('previous','current'):
        inventory=inventories[side]
        recorded=chunks(attachments[review[side+'ID']]['chunks'])['inventory']
        if inventory!=recorded or inventory['id']!=report['identity'][side+'InventoryID']:raise Unresolved('inventory_archive_mismatch')
        ids=[c['id'] for c in inventory['components']]
        if len(set(ids))!=len(ids) or len(ids)>128:raise Unresolved('duplicate_component_identity')
    observation_ids=[o['id'] for o in report['observations']]
    if len(set(observation_ids))!=len(observation_ids):raise Unresolved('duplicate_observation_identity')
    for observation in report['observations']:
        for reference in observation['evidence']:
            verify_reference_binding(reference,observation['componentPath'],inventories)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifests',type=Path,required=True);parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--sources',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--result-relative',default='adjudication.json')
    args=parser.parse_args(); relative=Path(args.result_relative)
    if relative.is_absolute() or any(p in ('','.','..') for p in relative.parts):parser.error('unsafe result path')
    try:
        sources=load_json(args.sources,1048576);lookup={s['sha256']:s for s in sources}
        if len(lookup)!=len(sources) or len(sources)>128:raise Unresolved('duplicate_source_identity')
        driver=load_json(args.cache/'capture-driver-v1.json',131072)
        case_lookup={c['caseID']:c for c in driver['cases']}
        if len(case_lookup)!=len(driver['cases']):raise Unresolved('duplicate_case_identity')
        results=[]
        for admitted in load_manifests(args.manifests):
            manifest=parse_json(admitted.canonical_bytes);case=manifest['case_id'];facts={}
            if admitted.architecture!='arm64':raise Unresolved('unsupported_architecture')
            for side in ('previous','current'):
                record=lookup[manifest[side]['sha256']]
                expected=args.cache/record['cache_bundle_relative']/record['app_relative_path']
                if str(expected)!=case_lookup[case][side] or record['asset']['url']!=manifest[side]['release_url']:raise Unresolved('capture_manifest_binding_mismatch')
                facts[side]=load_json(args.cache/'oracle'/(str(record['asset']['id'])+'.json'))
                repaired=args.cache/'plist-repairs'/(str(record['asset']['id'])+'.json')
                if repaired.exists():
                    observation=load_json(repaired,262144)
                    if observation['archive_sha256']!=record['sha256'] or observation['source']['path']!='Contents/Info.plist' or facts[side]['plists'].get('Contents/Info.plist',{}).get('state')!='unavailable':raise Unresolved('repaired_source_binding_mismatch')
                    facts[side]['plists']['Contents/Info.plist']=observation
                additional=load_json(args.cache/'additional-fields'/(str(record['asset']['id'])+'.json'))
                if additional['archive_sha256']!=record['sha256']:raise Unresolved('additional_source_binding_mismatch')
                for path,extra in additional['images'].items():
                    if extra['state']!='observed':continue
                    original=facts[side]['images'].get(path)
                    if not original or original['state']!='observed':raise Unresolved('additional_source_binding_mismatch')
                    for row in extra['slices']:
                        targets=[s for s in original['slices'] if s['identity']==row['identity']]
                        if len(targets)!=1:raise Unresolved('additional_slice_binding_mismatch')
                        targets[0]['additional_minimum_os']=row['minimum_os']
                        targets[0]['additional_sections']=row['sections']
            directory=args.cache/'captures-v1'/case
            report=load_json(directory/'report.json');archive=load_json(directory/'historical.json')
            inventories={side:load_json(directory/(side+'-inventory.json')) for side in ('previous','current')}
            verify_retained_binding(report,archive,inventories)
            result=evaluate_case(report,facts,inventories);result['case_id']=case
            result['provenance']='Acquisition receipt and capture-driver path binding; independent non-atomic raw facts. Native archive admission receipt reused separately.'
            results.append(result)
        write_document(args.output/relative,results)
        print(json.dumps({'cases':len(results),'observations':dict(sum((collections.Counter(r['observation_counts']) for r in results),collections.Counter())),
            'findings':dict(sum((collections.Counter(r['finding_counts']) for r in results),collections.Counter())),
            'expected_changes':dict(sum((collections.Counter(r['expected_change_counts']) for r in results),collections.Counter()))},sort_keys=True))
        return 0
    except (Unresolved,CorpusRefusal,OSError,KeyError,TypeError,AttributeError,ValueError) as error:
        print(json.dumps({'state':'refused','reason':getattr(error,'code',str(error) if isinstance(error,Unresolved) else 'invalid_qualification_input')}));return 2
if __name__=='__main__':raise SystemExit(main())
