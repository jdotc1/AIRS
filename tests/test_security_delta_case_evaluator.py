from security_delta_fixture_support import owned_temporary_directory
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
    def test_datetime_normalization_cannot_prove_original_date_bits(self):
        with self.assertRaises(Unresolved):
            compare_value({'type':'dateBits','value':'3ff0000000000000'}, {'type':'date','bits':'3ff0000000000000'})

    def test_null_component_reference_is_reserved_for_inventory_scope(self):
        from security_delta_case_evaluator import verify_reference_binding
        inventories={"previous":{"id":"inventory","components":[]}}
        reference={"side":"previous","inventoryID":"inventory","category":"informationPropertyList","componentID":None,"evidenceKey":"declaration:presence"}
        with self.assertRaises(Unresolved):verify_reference_binding(reference,"Main",inventories)
        reference.update(category="componentInventory",evidenceKey="scope")
        verify_reference_binding(reference,"Main",inventories)
        reference["componentID"]=""
        with self.assertRaises(Unresolved):verify_reference_binding(reference,"Main",inventories)

    def test_finding_kind_cannot_promote_unchanged_source(self):
        from security_delta_case_evaluator import qualify_finding
        observation={"id":"owned","category":"informationPropertyList","subject":"key:owned","componentPath":"Main","disposition":"unchanged","evidence":[{"side":"previous","relativeSource":"Info"}]}
        for kind in ("componentAdded","componentRemoved","xpcAdded","declarationChanged","signatureEvidenceChanged"):
            finding={"kind":kind,"observationIDs":["owned"],"evidence":observation["evidence"]}
            self.assertEqual(qualify_finding(finding,{"owned":observation},{},{})["state"],"disagreement",kind)
        observation["disposition"]="observedChange"
        finding["kind"]="declarationChanged"
        self.assertEqual(qualify_finding(finding,{"owned":observation},{},{})["state"],"supported")

    def test_multicategory_rule_requires_same_component_and_complete_evidence(self):
        from security_delta_case_evaluator import qualify_finding
        a={"id":"a","category":"informationPropertyList","componentPath":"Main","disposition":"observedChange","evidence":[{"side":"previous","relativeSource":"Info"}]}
        b={"id":"b","category":"loadCommands","componentPath":"Other","disposition":"observedChange","evidence":[{"side":"previous","relativeSource":"Other"}]}
        finding={"kind":"componentMultiCategory","observationIDs":["a","b"],"evidence":a["evidence"]+b["evidence"]}
        self.assertEqual(qualify_finding(finding,{"a":a,"b":b},{},{})["state"],"disagreement")
        b["componentPath"]="Main"
        self.assertEqual(qualify_finding(finding,{"a":a,"b":b},{},{})["state"],"supported")
        finding["evidence"]=a["evidence"]
        self.assertEqual(qualify_finding(finding,{"a":a,"b":b},{},{})["state"],"disagreement")

    def test_inventory_facts_use_exact_executable_and_raw_minimum(self):
        from security_delta_case_evaluator import source_fact
        facts={"plists":{"Contents/Info.plist":{"state":"observed","values":{"CFBundleExecutable":{"type":"string","value":"Main"},"CFBundleIdentifier":{"type":"string","value":"owned"},"CFBundleShortVersionString":{"type":"string","value":"1"}}}},"images":{"Contents/MacOS/Main":{"state":"observed","slices":[{"identity":{"cpu_type":0x100000c,"cpu_subtype":0},"additional_minimum_os":[{"platform":1,"minimum":918016}]}]}}}
        o={"category":"componentInventory","subject":"kind","componentPath":"Contents/MacOS/Main","evidence":[{"category":"componentInventory","side":"previous","relativeSource":"Contents/MacOS/Main"}]}
        self.assertEqual(source_fact(o,"previous",facts),("observed",{"type":"string","value":"app"}))
        o["subject"]="minimumOS:arm64"
        self.assertEqual(source_fact(o,"previous",facts),("observed",{"type":"string","value":"14.2.0"}))

    def test_qualification_input_caps_duplicates_and_symlinks(self):
        from security_delta_case_evaluator import load_json,parse_json
        import tempfile,os
        for raw in [b'{"x":1,"x":2}',b'['*65+b'0'+b']'*65,b'{"x":NaN}',b'\xff']:
            with self.assertRaises(Unresolved):parse_json(raw)
        with owned_temporary_directory() as folder:
            path=Path(folder)/"input.json";path.write_bytes(b'{"owned":true}')
            self.assertEqual(load_json(path,32),{"owned":True})
            with self.assertRaises(Unresolved):load_json(path,4)
            link=Path(folder)/"link.json";link.symlink_to(path)
            with self.assertRaises(OSError):load_json(link)

    def test_privacy_changed_executable_correspondence_is_unresolved(self):
        from security_delta_case_evaluator import enumerate_changes
        def facts(name,value):
            return {"images":{},"plists":{"Contents/Info.plist":{"state":"observed","values":{"CFBundleExecutable":{"type":"string","value":name}}},"Contents/Resources/PrivacyInfo.xcprivacy":{"state":"observed","values":{"NSPrivacyTracking":{"type":"boolean","value":value}}}}}
        rows=enumerate_changes({"previous":facts("Old",False),"current":facts("New",True)})
        self.assertTrue(rows)
        self.assertTrue(all(row['disposition']=='unresolved' for row in rows))

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
