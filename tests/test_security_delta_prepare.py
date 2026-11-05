from security_delta_fixture_support import owned_temporary_directory
"""Planning-only orchestration tests; network is never invoked."""
import json,sys,unittest,io,zipfile,plistlib,hashlib,tempfile
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in (ROOT/'scripts',ROOT/'tests'):sys.path.insert(0,str(p))
from test_security_delta_corpus_manifest import owned_manifest
from security_delta_corpus import decode_manifest,CorpusRefusal
from security_delta_prepare import plan_sources
class SecurityDeltaPrepareTests(unittest.TestCase):
    def fixture(self):
        value=owned_manifest()
        for side,version,identity in [('previous','1',1),('current','2',2)]:
            value[side]['release_url']='https://github.com/owned/project/releases/download/'+version+'/Owned.zip'
        value['oracle']={'acquisition':{side:{'source_id':'owned/project:'+str(identity)} for side,identity in [('previous',1),('current',2)]}}
        return value
    def test_unsupported_architecture_refuses_before_network_or_output(self):
        from security_delta_prepare import prepare
        value=self.fixture();value['selection']['architecture']='x86_64'
        manifest=decode_manifest(json.dumps(value).encode())
        with owned_temporary_directory() as folder:
            with patch('security_delta_prepare.bounded_tool') as network:
                with self.assertRaises(CorpusRefusal) as error:prepare([manifest],Path(folder))
                self.assertEqual(error.exception.code,'unsupported_architecture')
                network.assert_not_called()
            self.assertFalse((Path(folder)/'security-delta-real-corpus').exists())

    def test_owned_end_to_end_preparation_and_existing_output_refusal(self):
        from security_delta_prepare import prepare
        from security_delta_corpus import capture_chunks
        from test_security_delta_independent_oracle import image
        value=self.fixture();payloads={}
        for side,identity in (("previous",1),("current",2)):
            buffer=io.BytesIO()
            with zipfile.ZipFile(buffer,"w") as archive:
                archive.writestr("Owned.app/Contents/MacOS/Main",image())
                archive.writestr("Owned.app/Contents/Info.plist",plistlib.dumps({"CFBundleExecutable":"Main","CFBundleVersion":str(identity)}))
            payloads[identity]=buffer.getvalue();value[side]['sha256']=hashlib.sha256(payloads[identity]).hexdigest()
            value['expected']['source_digests'][side]=value[side]['sha256']
        manifest=decode_manifest(json.dumps(value).encode())
        def metadata(arguments,*args):
            identity=int(arguments[-1].rsplit('/',1)[-1]);side='previous' if identity==1 else 'current'
            return {'state':'observed','output':json.dumps({'id':identity,'browser_download_url':value[side]['release_url'],'size':len(payloads[identity]),'name':'Owned.zip'})}
        def fetch(repository,identity,size,destination,digest):
            return capture_chunks([payloads[identity]],destination,expected_size=size,expected_sha256=digest)
        with owned_temporary_directory() as folder:
            with patch('security_delta_prepare.bounded_tool',side_effect=metadata),patch('security_delta_prepare.fetch_github_asset',side_effect=fetch):
                result=prepare([manifest],Path(folder))
                self.assertEqual((result['sources'],result['pairs']),(2,1))
                driver=json.loads((Path(folder)/'security-delta-real-corpus/capture-driver-v1.json').read_text())
                self.assertEqual(driver['architecture'],'arm64')
                with self.assertRaises(CorpusRefusal) as refused:prepare([manifest],Path(folder))
                self.assertEqual(refused.exception.code,'existing_corpus_preserved')

    def test_distinct_sources_are_deduplicated_without_network(self):
        value=self.fixture(); manifest=decode_manifest(json.dumps(value).encode())
        self.assertEqual(len(plan_sources([manifest])),2)
        self.assertEqual(len(plan_sources([manifest,manifest])),2)
    def test_asset_id_cannot_substitute_another_publisher(self):
        value=self.fixture();value['oracle']['acquisition']['current']['source_id']='different/project:2'
        with self.assertRaises(CorpusRefusal):plan_sources([decode_manifest(json.dumps(value).encode())])
    def test_missing_acquisition_metadata_is_an_explicit_refusal(self):
        value=self.fixture();value.pop('oracle')
        with self.assertRaises(CorpusRefusal):plan_sources([decode_manifest(json.dumps(value).encode())])
if __name__=='__main__':unittest.main()
