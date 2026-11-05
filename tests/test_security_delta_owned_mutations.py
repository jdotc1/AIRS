"""Forty named owned mutations; no third-party bytes and no live applications."""
import copy,json,plistlib,struct,sys,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT/'scripts',ROOT/'tests'):sys.path.insert(0,str(p))
from test_security_delta_corpus_manifest import owned_manifest
from test_security_delta_independent_oracle import image,dylib
from security_delta_corpus import decode_manifest,CorpusRefusal,bounded_directory_names
from security_delta_independent_oracle import observe_macho,observe_plist,observe_bundle,OracleRefusal

class SecurityDeltaOwnedMutationTests(unittest.TestCase):pass

def manifest_case(name, mutate):
    def test(self):
        value=owned_manifest();mutate(value)
        with self.assertRaises(CorpusRefusal):decode_manifest(json.dumps(value).encode())
    setattr(SecurityDeltaOwnedMutationTests,'test_'+name,test)

def at(*path,value):
    def mutate(doc):
        for key in path[:-1]:doc=doc[key]
        doc[path[-1]]=value
    return mutate

mutations=[
('001_schema_future',at('schema_version',value=2)),('002_case_escape',at('case_id',value='../escape')),
('003_arch_unknown',at('selection','architecture',value='arm64-label-guess')),('004_purpose_unknown',at('selection','purpose',value='same_release')),
('005_digest_missing',lambda d:d['previous'].pop('sha256')),('006_digest_uppercase',at('previous','sha256',value='A'*64)),
('007_license_missing',lambda d:d['previous'].pop('license_note')),('008_http',at('previous','release_url',value='http://example.org/a.zip')),
('009_credentials',at('previous','release_url',value='https://name:password@example.org/a.zip')),('010_tracker',at('previous','release_url',value='https://example.org/a.zip?token=owned')),
('011_path_escape',at('previous','app_relative_path',value='../Owned.app')),('012_absolute_path',at('current','app_relative_path',value='/Owned.app')),
('013_unknown_field',at('unknown',value=True)),('014_reversed_date',at('current','published_at',value='2024-01-01T00:00:00Z')),
('015_same_version',at('current','version',value='1')),('016_same_archive',at('current','sha256',value='a'*64)),
('017_swapped_digest',at('expected','source_digests','current',value='a'*64)),('018_unknown_adjudication',at('expected','adjudication',value='safe')),
('019_bare_fact',at('expected','declaration_facts',value=['unproven'])),('020_missing_adjudicator',at('expected','adjudication',value='independently_adjudicated')),
('021_missing_locator',at('expected','declaration_facts',value=[{'side':'previous'}])),('022_unknown_refusal',at('expected','expected_refusals',value=['unavailable'])),
('023_nul_path',at('previous','app_relative_path',value='Owned\0.app')),('024_unsupported_archive',at('previous','archive_kind',value='nested-auto-unpack'))]
for name,mutate in mutations:manifest_case(name,mutate)

raw=[('025_empty',b''),('026_short',b'\xcf\xfa\xed\xfe'),('027_unknown_magic',b'owned'*8),
('028_excess_commands',struct.pack('<8I',0xfeedfacf,0x100000c,0,2,4097,0,0,0)),
('029_command_bytes',struct.pack('<8I',0xfeedfacf,0x100000c,0,2,0,1048577,0,0)),
('030_zero_command',image([struct.pack('<II',12,0)])),('031_bad_name_offset',image([struct.pack('<6I',12,24,0,0,0,0)])),
('032_duplicate_uuid',image([struct.pack('<II',0x1b,24)+bytes(16)]*2))]
for name,data in raw:
    def test(self,data=data):
        with self.assertRaises(OracleRefusal):observe_macho(data)
    setattr(SecurityDeltaOwnedMutationTests,'test_'+name,test)

def bad_binary_offset():
    raw=bytearray(plistlib.dumps({'owned':'value'},fmt=plistlib.FMT_BINARY));width=raw[-26];count,top,table=struct.unpack_from('>QQQ',raw,len(raw)-24)
    # Dictionary object 0 references key object 1, whose offset is untrusted.
    raw[table+width:table+2*width]=bytes([255])*width
    return bytes(raw)
nested='owned'
for _ in range(34):nested=[nested]
plists=[('033_invalid_xml',b'<plist><dict>'),('034_duplicate_xml',b'<plist><dict><key>x</key><true/><key>x</key><false/></dict></plist>'),
('035_invalid_utf8_xml',b'<plist><dict><key>\xff</key><true/></dict></plist>'),('036_array_root',plistlib.dumps([])),
('037_nonfinite',plistlib.dumps({'x':float('inf')},fmt=plistlib.FMT_BINARY)),('038_depth',plistlib.dumps({'x':nested})),
('039_binary_key_offset',bad_binary_offset())]
for name,data in plists:
    def test(self,data=data):
        with self.assertRaises(OracleRefusal):observe_plist(data)
    setattr(SecurityDeltaOwnedMutationTests,'test_'+name,test)

def test_bounded_enumeration(self):
    consumed=[]
    def entries():
        for i in range(1000000):consumed.append(i);yield SimpleNamespace(name=str(i))
    class Stream:
        def __enter__(self):return entries()
        def __exit__(self,*args):pass
    with patch('security_delta_corpus.os.scandir',return_value=Stream()):
        with self.assertRaises(CorpusRefusal):bounded_directory_names(0,3)
    self.assertEqual(len(consumed),4)
setattr(SecurityDeltaOwnedMutationTests,'test_040_directory_population_is_not_materialized',test_bounded_enumeration)
if __name__=='__main__':unittest.main()
