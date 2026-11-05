#!/usr/bin/env python3
"""Explicit opt-in reproduction of a private real-release corpus.
Third-party payloads remain local. Never launches inspected code. Uses gh only
for public publisher metadata/assets, and the existing bounded acquisition API.
"""
import argparse,datetime,json,re,os
from pathlib import Path
from urllib.parse import urlsplit
from security_delta_corpus import CorpusRefusal,load_manifests,fetch_github_asset,extract_archive,open_directory_no_follow
from security_delta_independent_oracle import observe_bundle,capture_recorded_fields,write_document,bounded_tool
from security_delta_case_evaluator import parse_json

def refuse(code):raise CorpusRefusal(code)

def plan_sources(manifests):
    sources={}
    for manifest in manifests:
        if manifest.architecture != "arm64":refuse("unsupported_architecture")
        document=parse_json(manifest.canonical_bytes)
        for side in ('previous','current'):
            source=document[side]
            try:identity=document['oracle']['acquisition'][side]['source_id']
            except (KeyError,TypeError):refuse('acquisition_metadata_unavailable')
            if not isinstance(identity,str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+:[1-9][0-9]{0,19}',identity):refuse('acquisition_source_identity')
            repository,asset=identity.rsplit(':',1);url=urlsplit(source['release_url']);parts=url.path.split('/')
            if url.hostname!='github.com' or len(parts)<7 or '/'.join(parts[1:3])!=repository or parts[3:5]!=['releases','download']:refuse('acquisition_source_binding_mismatch')
            record=dict(source_id=identity,repository=repository,asset_id=int(asset),source=source)
            if source['sha256'] in sources and sources[source['sha256']]!=record:refuse('duplicate_source_identity')
            sources[source['sha256']]=record
    if len(sources)>128:refuse('source_record_limit')
    return sorted(sources.values(),key=lambda r:r['source_id'].encode('utf-8'))

def prepare(manifests,output):
    plan=plan_sources(manifests)
    cache=output/'security-delta-real-corpus'
    # Do not re-download/re-hash a completed corpus, or resume a partial capture
    # by treating a serialized receipt as a fresh descriptor capability.
    if cache.exists():refuse('existing_corpus_preserved')
    cache.mkdir(mode=0o700)
    for directory in ('source-records','oracle','additional-fields'):(cache/directory).mkdir()
    records=[];downloaded=expanded=0
    for item in plan:
        repository=item['repository'];identity=item['asset_id'];source=item['source']
        metadata=bounded_tool(['gh','api','repos/'+repository+'/releases/assets/'+str(identity)],cache)
        if metadata['state']!='observed':refuse('publisher_metadata_unavailable')
        asset=parse_json(metadata['output'].encode())
        if asset.get('id')!=identity or asset.get('browser_download_url')!=source['release_url'] or type(asset.get('size')) is not int:refuse('publisher_asset_binding_mismatch')
        if asset['size']>1073741824-downloaded:refuse('aggregate_download_limit')
        folder=cache/repository.lower().replace('/','-');folder.mkdir(exist_ok=True)
        archive=folder/(str(identity)+'.zip');destination=folder/(str(identity)+'.bundle')
        admitted=fetch_github_asset(repository,identity,asset['size'],archive,source['sha256'])
        downloaded+=asset['size']
        extraction=extract_archive(admitted,destination,maximum_bytes=min(1073741824,2147483648-expanded))
        expanded+=extraction['expanded_bytes']
        bundle=destination/source['app_relative_path'];directory=open_directory_no_follow(bundle);os.close(directory)
        record=dict(source_id=item['source_id'],repository=repository,asset={'id':identity,'name':asset['name'],'url':source['release_url'],'size':asset['size']},sha256=admitted.sha256,
            archive_metadata=list(admitted.metadata),cache_archive_relative=str(archive.relative_to(cache)),cache_bundle_relative=str(destination.relative_to(cache)),app_relative_path=source['app_relative_path'],
            retrieved_at=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),license_note=source['license_note'],license_url=source['license_url'],status='admitted_release',extraction=extraction)
        write_document(cache/'source-records'/(str(identity)+'.json'),record)
        facts=observe_bundle(bundle)
        write_document(cache/'oracle'/(str(identity)+'.json'),facts)
        # Record ranges from this authorized capture without container rehash.
        additional=capture_recorded_fields(bundle,facts);additional['archive_sha256']=admitted.sha256
        additional['recorded_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        write_document(cache/'additional-fields'/(str(identity)+'.json'),additional)
        records.append(record)
    lookup={r['sha256']:r for r in records}
    cases=[]
    for manifest in manifests:
        value=parse_json(manifest.canonical_bytes);entry={'caseID':manifest.case_id}
        if manifest.architecture!='arm64':refuse('unsupported_architecture')
        for side in ('previous','current'):
            r=lookup[value[side]['sha256']];entry[side]=str(cache/r['cache_bundle_relative']/r['app_relative_path'])
        cases.append(entry)
    write_document(cache/'acquisitions.json',records)
    write_document(cache/'capture-driver-v1.json',{'architecture':'arm64','cases':cases,'output':str(cache/'captures-v1')})
    return {'state':'prepared','sources':len(records),'pairs':len(cases),'downloaded_bytes':downloaded,'expanded_bytes':expanded}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifests',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--plan-only',action='store_true',help='Validate acquisition identities without network or writes')
    args=parser.parse_args()
    try:
        manifests=load_manifests(args.manifests)
        if args.plan_only:result={'state':'planned','sources':len(plan_sources(manifests)),'pairs':len(manifests)}
        else:result=prepare(manifests,args.output)
        print(json.dumps(result,sort_keys=True));return 0
    except (CorpusRefusal,OSError,ValueError,KeyError,TypeError) as error:
        print(json.dumps({'state':'refused','reason':getattr(error,'code','preparation_input_unavailable')}));return 2
if __name__=='__main__':raise SystemExit(main())
