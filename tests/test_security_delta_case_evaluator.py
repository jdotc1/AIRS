"""Owned adjudication fixtures; expected facts never originate in AIRS report values."""
import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from security_delta_case_evaluator import compare_value, adjudicate_observation, Unresolved

class SecurityDeltaCaseEvaluatorTests(unittest.TestCase):
    def test_boolean_is_not_integer(self):
        self.assertFalse(compare_value({'type':'boolean','value':True},{'type':'integer','decimal':'1','representation':'unspecified'}))
    def test_numeric_value_survives_historical_fidelity(self):
        self.assertTrue(compare_value({'type':'normalizedInteger','value':'1'},{'type':'integer','decimal':'1','representation':'unspecified'}))
        self.assertFalse(compare_value({'type':'signed','value':'-1'},{'type':'integer','decimal':'1','representation':'unspecified'}))
    def test_order_is_not_discarded(self):
        self.assertFalse(compare_value({'type':'array','value':[{'type':'string','value':'a'},{'type':'string','value':'b'}]}, {'type':'array','items':[{'type':'string','value':'b'},{'type':'string','value':'a'}]}))
    def test_unknown_typed_value_does_not_pass(self):
        with self.assertRaises(Unresolved): compare_value({'type':'future','value':1},{'type':'future','value':1})
    def test_source_key_change_and_wrong_value(self):
        previous={'plists':{'Contents/Info.plist':{'state':'observed','values':{'CFBundleExecutable':{'type':'string','value':'Main'},'CFBundleVersion':{'type':'string','value':'1'}}}}}
        current={'plists':{'Contents/Info.plist':{'state':'observed','values':{'CFBundleExecutable':{'type':'string','value':'Main'},'CFBundleVersion':{'type':'string','value':'2'}}}}}
        observation={'category':'informationPropertyList','subject':'key:CFBundleVersion','componentPath':'Contents/MacOS/Main','disposition':'observedChange','previousState':'observed','currentState':'observed','previousValue':{'type':'string','value':'1'},'currentValue':{'type':'string','value':'2'},'evidence':[{'side':'previous','relativeSource':'Contents/Info.plist','category':'informationPropertyList'},{'side':'current','relativeSource':'Contents/Info.plist','category':'informationPropertyList'}]}
        self.assertEqual(adjudicate_observation(observation,{'previous':previous,'current':current})['state'],'supported')
        observation['currentValue']['value']='forged'
        self.assertEqual(adjudicate_observation(observation,{'previous':previous,'current':current})['state'],'disagreement')
    def test_qualification_input_caps_duplicates_and_symlinks(self):
        from security_delta_case_evaluator import load_json,parse_json
        import tempfile,os
        for raw in [b'{"x":1,"x":2}',b'['*65+b'0'+b']'*65,b'{"x":NaN}',b'\xff']:
            with self.assertRaises(Unresolved):parse_json(raw)
        with tempfile.TemporaryDirectory(dir=ROOT/"local-evidence/security-delta-track-a") as folder:
            path=Path(folder)/"input.json";path.write_bytes(b'{"owned":true}')
            self.assertEqual(load_json(path,32),{"owned":True})
            with self.assertRaises(Unresolved):load_json(path,4)
            link=Path(folder)/"link.json";link.symlink_to(path)
            with self.assertRaises(OSError):load_json(link)

    def test_privacy_owner_mapping_root_nested_and_framework(self):
        from security_delta_case_evaluator import enumerate_changes
        for prefix,info,privacy in [("","Contents/Info.plist","Contents/Resources/PrivacyInfo.xcprivacy"),("Contents/XPCServices/Owned.xpc/","Contents/Info.plist","Contents/Resources/PrivacyInfo.xcprivacy"),("Contents/Frameworks/Owned.framework/Versions/A/","Resources/Info.plist","Resources/PrivacyInfo.xcprivacy")]:
            def facts(value):
                return {"images":{},"plists":{prefix+info:{"state":"observed","values":{"CFBundleExecutable":{"type":"string","value":"Main"}}},prefix+privacy:{"state":"observed","values":{"NSPrivacyTracking":{"type":"boolean","value":value}}}}}
            expected=enumerate_changes({"previous":facts(False),"current":facts(True)})
            self.assertEqual(len(expected),1,prefix)
            self.assertEqual(expected[0]["category"],"privacyManifest")

    def test_relabelled_component_cannot_borrow_source(self):
        facts={"plists":{"Contents/Info.plist":{"state":"observed","values":{"CFBundleExecutable":{"type":"string","value":"Main"}}}}}
        o={"category":"informationPropertyList","subject":"presence","componentPath":"Contents/MacOS/Different","disposition":"unchanged","previousState":"observed","currentState":"observed","evidence":[{"side":s,"category":"informationPropertyList","relativeSource":"Contents/Info.plist"} for s in ("previous","current")]}
        self.assertNotEqual(adjudicate_observation(o,{"previous":facts,"current":facts})["state"],"supported")

    def test_independent_change_enumeration_detects_missing_result(self):
        from security_delta_case_evaluator import enumerate_changes, evaluate_expected_changes
        def facts(version):
            return {"plists":{"Contents/Info.plist":{"state":"observed","values":{"CFBundleExecutable":{"type":"string","value":"Main"},"CFBundleVersion":{"type":"string","value":version}}}},"images":{},"privacy":{}}
        expected=enumerate_changes({"previous":facts("1"),"current":facts("2")})
        self.assertEqual(len(expected),1)
        report={"observations":[{"componentPath":"Contents/MacOS/Main","category":"informationPropertyList","subject":"presence","disposition":"unchanged"}]}
        self.assertEqual(evaluate_expected_changes(report,expected)[0]["state"],"false_negative")
        report["observations"][0]["disposition"]="unresolved"
        self.assertEqual(evaluate_expected_changes(report,expected)[0]["state"],"unresolved")

    def test_dependency_count_observation_uses_raw_group_membership(self):
        def facts(rows):
            return {"images":{"Main":{"state":"observed","slices":[{"identity":{"cpu_type":0x100000c,"cpu_subtype":0},"loader":rows}]}}}
        row={"kind":"load","path":"A","current_version":65536,"compatibility_version":65536}
        observation={"category":"loadCommands","subject":"dependency:load:A","componentPath":"Main","disposition":"observedAddition","previousState":"absent","currentState":"observed","previousValue":{"type":"signed","value":"0"},"currentValue":{"type":"signed","value":"1"},"evidence":[{"side":side,"relativeSource":"Main","category":"loadCommands"} for side in ("previous","current")]}
        self.assertEqual(adjudicate_observation(observation,{"previous":facts([]),"current":facts([row])})["state"],"supported")
        observation.update(disposition="observedChange",previousState="observed",previousValue=None,currentValue=None)
        changed=dict(row,current_version=131072)
        self.assertEqual(adjudicate_observation(observation,{"previous":facts([row]),"current":facts([changed])})["state"],"supported")
        self.assertEqual(adjudicate_observation(observation,{"previous":facts([row]),"current":facts([row])})["state"],"disagreement")

    def test_missing_source_stays_unresolved(self):
        observation={'category':'informationPropertyList','subject':'presence','componentPath':'x','disposition':'unchanged','previousState':'observed','currentState':'observed','evidence':[]}
        self.assertEqual(adjudicate_observation(observation,{'previous':{},'current':{}})['state'],'unresolved')

if __name__=='__main__': unittest.main()
