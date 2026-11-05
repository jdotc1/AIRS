"""New harness utilities only; never run the corpus qualification here."""
import importlib.util
from pathlib import Path
import unittest
from copy import deepcopy

spec=importlib.util.spec_from_file_location('broad_qualification',Path(__file__).resolve().parents[1]/'scripts/swift_broad_qualification.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)


class B11MeasuringContractTests(unittest.TestCase):
    def selected(self, *, shared=False, alias=False):
        rows=[dict(pc='0x1000',word='0x94000008',kind='bl'),
            dict(pc='0x1004',word='0xb4000055',kind='xcbz'),
            dict(pc='0x1008',word='0xd65f03c0',kind='ret'),
            dict(pc='0x100c',word='0xd65f03c0',kind='ret')]
        succ='0x1008' if shared else '0x100c'
        edges=[dict(source_pc='0x1000',target_pc='0x1004',kind='call_return_candidate'),
            dict(source_pc='0x1004',target_pc=succ,kind='conditional_taken'),
            dict(source_pc='0x1004',target_pc='0x1008',kind='conditional_fallthrough')]
        edges += [dict(source_pc=r['pc'],target_pc=None,kind='return') for r in rows[2:]]
        candidate=dict(call=dict(pc='0x1000'),identity=dict(slice_sha256='authored-image',container_sha256='authored-container'),
            post_call=dict(test_pc='0x1004',test_word='0xb4000055',test_register='x19' if alias else 'x21',
                trace=['0x1004'],success_successor_pc=succ,error_successor_pc='0x1008'),
            cfg=dict(blocks=[dict(instructions=rows)],edges=edges),value_facts=dict(observations=[]))
        partition=dict(success_only_pcs=[] if shared else ['0x100c'],error_only_pcs=[] if shared else ['0x1008'],
            shared_pcs=['0x1008'] if shared else [],unreachable_pcs=['0x1000','0x1004'])
        validation=dict(eligible=True,status='eligible_structural_only',reason='authored checked fixture',
            fact_statuses=dict(cfg='checked',post_call='checked',regions='checked'),region_partition=partition,
            return_observations=[dict(arm=arm,return_pc=pc,value=['constant',3,64],status='modeled_symbolic_value',
                raw_error_register_value=['constant',0,64]) for arm,pc in [('success',succ),('error','0x1008')]])
        return candidate,validation

    def test_prefix_variations_and_padding_cannot_manufacture_ten_geometries(self):
        candidate,validation=self.selected();expected=h.geometry(candidate,validation)
        self.assertIsNotNone(expected);keys=set()
        for mask in range(16):
            c=deepcopy(candidate)
            for index,kind in enumerate(('mov','stp','b','xcbnz')):
                if mask&(1<<index):
                    pc=hex(0xf00+4*index)
                    c['cfg']['blocks'][0]['instructions'].append(dict(pc=pc,word='0xd503201f',kind=kind))
                    c['cfg']['edges'].append(dict(source_pc=pc,target_pc='0x1000',kind='branch'))
            keys.add(h.geometry(c,validation))
        self.assertEqual(keys,{expected})
        # An arm data operation, NOP and B-to-RET contract to the same topology.
        c=deepcopy(candidate);v=deepcopy(validation)
        c['post_call']['success_successor_pc']='0x1010'
        c['cfg']['edges'][1]['target_pc']='0x1010'
        c['cfg']['blocks'][0]['instructions'] += [dict(pc='0x1010',word='0xd2800020',kind='movz'),
            dict(pc='0x1014',word='0xd503201f',kind='nop'),dict(pc='0x1018',word='0x17fffffd',kind='b')]
        c['cfg']['edges'].append(dict(source_pc='0x1018',target_pc='0x100c',kind='branch'))
        v['region_partition']['success_only_pcs']+=['0x1010','0x1014','0x1018']
        self.assertEqual(h.geometry(c,v),expected)

    def test_geometry_normalizes_addresses_alias_names_and_retains_shared_topology(self):
        c,v=self.selected(alias=True);expected=h.geometry(c,v)
        def relocate(value):
            if isinstance(value,dict):return {k:relocate(x) for k,x in value.items()}
            if isinstance(value,list):return [relocate(x) for x in value]
            if isinstance(value,str) and value in {'0x1000','0x1004','0x1008','0x100c'}:return hex(int(value,16)+0x8000)
            return value
        other=relocate(c);other['post_call']['test_register']='x20'
        self.assertEqual(h.geometry(other,relocate(v)),expected)
        shared,sv=self.selected(shared=True,alias=True)
        self.assertNotEqual(h.geometry(shared,sv),expected)
        broken=deepcopy(c);broken['post_call']['success_successor_pc']='0xdead'
        self.assertIsNone(h.geometry(broken,v))
        v['fact_statuses']['regions']='unchecked'
        self.assertIsNone(h.geometry(c,v))

    def test_required_inventory_rejects_miscellaneous_features_and_source_only_labels(self):
        c,v=self.selected()
        row=dict(capture='primary',mode='O',call_pc=0x1000,candidate=c,validation=v,
            source_callers=[dict(case_id='new-case',caller='broad_caller_0000_0',source_geometry='nested_handlers')],
            observed_emitted_challenges=['unrelated-'+str(i) for i in range(20)])
        row['required_challenge_dispositions']=h.required_challenge_dispositions(row)
        inventory=h.challenge_inventory([row],[],[])
        self.assertEqual(set(inventory['entries']),set(h.REQUIRED_CHALLENGES))
        self.assertEqual(len(inventory['entries']),12);self.assertFalse(inventory['complete'])
        self.assertTrue(inventory['entries']['cbz']['observed'])
        self.assertEqual(inventory['entries']['nested_handlers']['dispositions'],dict(collapsed=1))
        self.assertFalse(inventory['entries']['nested_handlers']['observed'])
        evidence=inventory['entries']['cbz']['examples'][0]
        self.assertEqual(evidence['raw_evidence'],[dict(pc='0x1004',word='0xb4000055')])
        self.assertTrue(evidence['checked_cfg']);self.assertFalse(evidence['source_semantics_recovered'])

    def test_absence_needs_index_and_complete_matching_caller_bytes(self):
        row=dict(capture='primary',mode='O',feature='indexed_owned_call_absence',
            source_callers=[dict(case_id='new-absence',caller='broad_caller_0001_0',source_geometry='inline_absence_challenge')])
        before=h.required_challenge_dispositions(row)[0]
        self.assertEqual(before['disposition'],'unproven');self.assertFalse(before['actual_form_observed'])
        row['absence_callers']=[dict(caller_token='broad_caller_0001_0',caller_pc='0x3000',complete=True,
            call_instruction_count=0,extent_evidence=[dict(pc='0x3000',word='0xd65f03c0')])]
        after=h.required_challenge_dispositions(row)[0]
        self.assertEqual(after['disposition'],'observed');self.assertTrue(after['actual_form_observed'])
        self.assertIn('cause unproven',after['reason'])

    def test_new_proof_flags_are_asserted_not_deleted(self):
        for name in ('runtime_propagation_proven','source_handler_proven','incoming_state_proven'):
            candidate=dict(cfg={name:False},accounting=dict(encoded_bytes=0))
            self.assertEqual(h.attack_kind(('cfg',name)),'proofscope')
            self.assertIs(h.delete_claim(candidate,('cfg',name))['cfg'][name],True)

    def test_seven_family_controls_fit_inside_existing_negative_budget(self):
        rows=[]
        for i,family in enumerate(h.FAMILIES):
            candidate=dict(call=dict(declaration=dict(identity=dict(callable_kind=family))),
                identity={str(n):n for n in range(300)})
            rows.append(dict(capture='primary',mode='O',call_pc=0x4000+i*4,family=family,
                _context=(None,None,candidate,None)))
        plan=h.negative_plan(rows)
        self.assertEqual(len(plan),280)
        controls=[row['family'] for _,row,_,control in plan if control]
        self.assertEqual(controls,list(h.FAMILIES))
        self.assertEqual(len({(row['call_pc'],path) for _,row,path,_ in plan}),280)

    def test_source_category_minima_and_nonrename_diversity_are_separate(self):
        cases=[]
        for category,count in h.SOURCE_MINIMUMS.items():
            for n in range(count):
                cases.append(dict(case_id=category+str(n),category=category,return_family='Int',parameter_form='one',
                    dispatch='direct',signature_shape=str(n),feature_vector=[category,'Int','one','direct','throws',False,False,n]))
        good=h.source_inventory(cases)
        self.assertTrue(good['categories_complete']);self.assertTrue(good['diversity_reconciled'])
        changed=deepcopy(cases);changed[-1]['category']='struct';changed[-1]['feature_vector'][0]='struct'
        self.assertFalse(h.source_inventory(changed)['categories_complete'])
        renamed=deepcopy(cases);renamed[1]['feature_vector']=renamed[0]['feature_vector']
        self.assertFalse(h.source_inventory(renamed)['diversity_reconciled'])

    def test_mocked_latency_rss_reports_platform_scope_and_failed_unit(self):
        ticks=iter((0,1,3,4,5,8))
        metrics=h.PerformanceMeasurements(clock=lambda:next(ticks),rusage=lambda:4096,platform='darwin')
        self.assertEqual(metrics.call('physical_call',lambda:42),42)
        with self.assertRaises(ValueError):metrics.call('retained_negative',lambda:(_ for _ in ()).throw(ValueError()))
        record=metrics.snapshot()
        self.assertTrue(record['complete']);self.assertEqual(record['total_elapsed_seconds'],8)
        self.assertEqual(record['per_unit_summary']['physical_call']['max_seconds'],2)
        self.assertEqual(record['per_unit_summary']['retained_negative']['failed_units'],1)
        self.assertEqual(record['peak_rss']['raw_unit'],'bytes');self.assertEqual(record['peak_rss']['bytes'],4096)
        self.assertIsNone(record['bounds']['process_rss_ceiling'])
        linux=h.PerformanceMeasurements(clock=lambda:1,rusage=lambda:7,platform='linux')
        linux.call('physical_call',lambda:None)
        self.assertEqual(linux.snapshot()['peak_rss']['bytes'],7168)
        missing=h.PerformanceMeasurements(clock=lambda:1,rusage=lambda:None,platform='unknown')
        missing.call('physical_call',lambda:None)
        self.assertFalse(missing.snapshot()['complete'])

    def test_packager_and_harness_require_the_same_complete_gate_inventory(self):
        spec=importlib.util.spec_from_file_location('new_gate_packager',Path(__file__).resolve().parents[1]/'scripts/package_swift_broad_handback.py')
        packager=importlib.util.module_from_spec(spec);spec.loader.exec_module(packager)
        self.assertEqual(packager.MANDATORY_GATES,h.MANDATORY_GATES)
        self.assertEqual(len(h.MANDATORY_GATES),26)
        self.assertTrue({'measured_latency_rss','source_category_minima','source_diversity_reconciled',
            'seven_family_negative_controls'}<=h.MANDATORY_GATES)

    def test_mocked_one_shot_plumbing_records_all_measurement_gates(self):
        import contextlib,io,tempfile
        from types import SimpleNamespace
        from unittest.mock import patch
        case=dict(case_id='new-mock-case',category='free',return_family='Int',parameter_form='one',dispatch='direct',
            signature_shape='new',feature_vector=['free','Int','one','direct','throws',False,False,'add'],
            source_callsites=[dict(caller='broad_caller_0000_0',geometry='handled')])
        manifest=dict(cases=[case],generator_version='authored-new-mock')
        call=dict(owned_target_confirmed=True,pc='0x1000',target_pc='0x2000',
            caller_aliases_nm=['broad_caller_0000_0'],owned_target_case_ids=['new-mock-case'])
        index=dict(modes={mode:dict(calls=[call],cases=[]) for mode in ('Onone','O','Osize')})
        receipt=dict(source_sha256='authored-unhashed',modes={mode:dict(library=mode+'.mock') for mode in index['modes']})
        reviews=[dict(source_revision='new-mock-head',scope='whole_broad_branch',decision='passed',
            unresolved_findings=[],correction_history=[],reviewer=x) for x in ('new-mock-1','new-mock-2')]
        fn=SimpleNamespace(start=0x1000,end=0x1010,name='broad_caller_0000_0')
        image=SimpleNamespace(functions=[fn],slice_sha256='authored-unhashed',container_sha256='authored-unhashed',uuid=None,slice_index=0)
        reads=iter(reviews+[manifest,index,receipt,manifest,index,receipt]);ticks=iter(range(100))
        metrics=h.PerformanceMeasurements(clock=lambda:next(ticks),rusage=lambda:8192,platform='darwin')
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'local-evidence') as directory:
            args=SimpleNamespace(capture=Path(directory)/'primary',second_capture=Path(directory)/'second',
                output=Path(directory)/'output',review=[Path('review-a'),Path('review-b')])
            with patch.object(h.subprocess,'check_output',side_effect=['new-mock-head','','']), \
                 patch.object(h,'read_bounded_json',side_effect=lambda *a,**k:next(reads)), \
                 patch.object(h,'validate_capture_prerequisites',return_value={'authored_mock':True}), \
                 patch.object(h,'compiler_identity',side_effect=lambda directory,receipt:dict(capture_directory=str(directory),compiler_path=str(directory),compiler_version=directory.name)), \
                 patch('airs.swift_owned_image.load_owned_swift_image',return_value=image), \
                 patch('airs.swift_callsite_admission.create_callsite_session',return_value=SimpleNamespace(initial_work_steps=1)), \
                 patch('airs.swift_outcome_validator_v2.create_independent_swift_image_ledger',return_value=SimpleNamespace(initial_work_steps=1,status='ready')), \
                 patch.object(h,'scan_source_callers',side_effect=lambda *a:iter(())), \
                 patch.object(h,'analyze_call',return_value=(dict(status='unresolved',reason='authored_mock',work_steps=1),None,None,None)) as analyze, \
                 patch.object(h,'raw_negatives',return_value=[]), \
                 patch.object(h,'write_qualification_outputs') as output,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(h.run(args,metrics),2)
            report=output.call_args.args[1]
            self.assertEqual(analyze.call_count,6)  # six NEW mock units, zero actual image analysis
            self.assertEqual(set(report['gates']),h.MANDATORY_GATES)
            self.assertTrue(report['gates']['measured_latency_rss'])
            self.assertFalse(report['gates']['observed_emitted_challenges_12'])
            self.assertFalse(report['gates']['negative_300_zero_false_eligible'])
            self.assertTrue((args.output/'FINAL-PASS-STARTED.json').exists())

    def test_failure_record_preserves_available_mocked_metrics_without_retry(self):
        import contextlib,io,json,tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'local-evidence') as directory:
            output=Path(directory)/'failure';output.mkdir()
            (output/'FINAL-PASS-STARTED.json').write_text('{"authored_mock":true}')
            ticks=iter((0,2));metrics=h.PerformanceMeasurements(clock=lambda:next(ticks),rusage=lambda:None,platform='unknown')
            with patch.object(h,'PerformanceMeasurements',return_value=metrics), \
                 patch.object(h,'run',side_effect=RuntimeError('authored new failure')) as run, \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(h.main(['--capture','unused-primary','--second-capture','unused-second',
                    '--output',str(output),'--execute-final']),2)
            self.assertEqual(run.call_count,1)
            failure=json.loads((output/'FAILURE.json').read_text())
            self.assertEqual(failure['measurements']['total_elapsed_seconds'],2)
            self.assertFalse(failure['measurements']['complete'])
            self.assertEqual(failure['measurements']['peak_rss']['status'],'unavailable')

    def test_missing_selected_contract_is_incomplete_without_aborting_stratification(self):
        c,v=self.selected();del c['post_call']['trace']
        row=dict(capture='primary',mode='O',call_pc=0x1000,target_pc='0x2000',family='free',lowering='x0',
            geometry=h.geometry(c,v),candidate=c,validation=v,
            source_callers=[dict(case_id='new-malformed',caller='broad_caller_0000_0',source_geometry='handled')])
        self.assertIsNone(row['geometry']);self.assertEqual(h.required_challenge_dispositions(row),[])
        self.assertEqual(row['challenge_measurement_status'],'incomplete_independent_result_contract')
        other=dict(row,call_pc=0x2000,geometry='checked-other')
        self.assertEqual(len(h.stratified_select([row,other],2)),2)

    def test_reserved_family_mutation_is_not_reused_by_global_pool(self):
        rows=[]
        for index in range(8):
            candidate=dict(call=dict(declaration=dict(identity=dict(callable_kind='free'))),identity=dict(call_pc=str(index)))
            rows.append(dict(capture='primary',mode='O',call_pc=0x8000+4*index,family='free',_context=(None,None,candidate,None)))
        plan=h.negative_plan(rows)
        self.assertEqual(sum(path==('call','declaration','identity','callable_kind') for _,_,path,_ in plan),1)

    def nested_row(self,c,v,pc=0x1000):
        c['identity']['caller']=dict(start_pc='0x1000',end_pc_exclusive='0x1044')
        v['fact_statuses']['abi']='checked';c['call']['word']='0x94000008'
        row=dict(capture='primary',mode='O',call_pc=pc,candidate=c,validation=v,
            source_callers=[dict(case_id='new-nested',caller='broad_caller_0000_0',source_geometry='nested_handlers')])
        row['required_challenge_dispositions']=h.required_challenge_dispositions(row)
        return row

    def test_unrelated_extra_condition_does_not_count_nested_error_corridor(self):
        c,v=self.selected()
        c['cfg']['blocks'][0]['instructions'][2].update(kind='xcbz',word='0xb4000050')
        c['cfg']['blocks'][0]['instructions'].append(dict(pc='0x1010',kind='ret',word='0xd65f03c0'))
        v['region_partition']['error_only_pcs'].append('0x1010')
        row=self.nested_row(c,v)
        h.reconcile_nested_challenges([row],h.WorkBudget(1000),h.RetentionBudget(100000))
        record=next(x for x in row['required_challenge_dispositions'] if x['challenge']=='nested_handlers')
        self.assertEqual(record['disposition'],'unproven');self.assertFalse(record['actual_form_observed'])
        self.assertIn('not sufficient',record['reason'])

    def test_nested_inventory_links_only_independently_checked_inner_call_error_corridor(self):
        outer,ov=self.selected();outer['post_call']['success_successor_pc']='0x1040'
        outer['cfg']['blocks'][0]['instructions']=[dict(pc=pc,kind=kind,word=word) for pc,kind,word in (
            ('0x1000','bl','0x94000008'),('0x1004','xcbz','0xb40001f5'),('0x1008','bl','0x94000008'),
            ('0x100c','xcbz','0xb4000055'),('0x1010','ret','0xd65f03c0'),('0x1014','ret','0xd65f03c0'),('0x1040','ret','0xd65f03c0'))]
        ov['region_partition'].update(success_only_pcs=['0x1040'],error_only_pcs=['0x1008','0x100c','0x1010','0x1014'])
        outer_row=self.nested_row(outer,ov)
        inner,iv=self.selected();inner['call']['pc']='0x1008'
        inner['post_call'].update(test_pc='0x100c',trace=['0x100c'],success_successor_pc='0x1014',error_successor_pc='0x1010')
        inner['cfg']['blocks'][0]['instructions']=deepcopy(outer['cfg']['blocks'][0]['instructions'])
        iv['region_partition'].update(success_only_pcs=['0x1014'],error_only_pcs=['0x1010'])
        inner_row=self.nested_row(inner,iv,0x1008)
        budget=h.WorkBudget(10000);retention=h.RetentionBudget(100000)
        h.reconcile_nested_challenges([outer_row,inner_row],budget,retention)
        record=next(x for x in outer_row['required_challenge_dispositions'] if x['challenge']=='nested_handlers')
        self.assertTrue(record['actual_form_observed']);self.assertEqual(record['nested_corridor']['call_pc'],'0x1008')
        self.assertEqual(record['nested_corridor']['outer_arm'],'error');self.assertGreater(retention.used,0)
        self.assertFalse(record['source_semantics_recovered'])
        # Changed independent ABI state cannot supply the same linkage.
        changed_outer=self.nested_row(deepcopy(outer),deepcopy(ov));inner_row['validation']['fact_statuses']['abi']='unchecked'
        h.reconcile_nested_challenges([changed_outer,inner_row],h.WorkBudget(10000),h.RetentionBudget(100000))
        changed=next(x for x in changed_outer['required_challenge_dispositions'] if x['challenge']=='nested_handlers')
        self.assertFalse(changed['actual_form_observed'])

    def test_shared_exception_terminal_is_not_a_shared_epilogue(self):
        c,v=self.selected(shared=True)
        c['cfg']['blocks'][0]['instructions'][2].update(kind='brk',word='0xd4200000')
        v['return_observations']=[];v['exception_observations']=[dict(pc='0x1008',arm='success'),dict(pc='0x1008',arm='error')]
        row=dict(capture='primary',mode='O',call_pc=0x1000,candidate=c,validation=v,
            source_callers=[dict(case_id='new-shared-trap',caller='broad_caller_0000_0',source_geometry='handled')])
        self.assertNotIn('shared_epilogue',{x['challenge'] for x in h.required_challenge_dispositions(row)})

    def test_checked_postcall_register_alias_does_not_multiply_geometry(self):
        direct,validation=self.selected()
        mapping={'0x1004':'0x1008','0x1008':'0x100c','0x100c':'0x1010'}
        def relocate(value):
            if isinstance(value,dict):return {k:relocate(v) for k,v in value.items()}
            if isinstance(value,list):return [relocate(v) for v in value]
            return mapping.get(value,value) if isinstance(value,str) else value
        alias=relocate(direct);av=relocate(validation)
        alias['cfg']['blocks'][0]['instructions'].append(dict(pc='0x1004',word='0xaa1503f3',kind='mov'))
        alias['cfg']['edges'][0]['target_pc']='0x1004'
        alias['post_call'].update(trace=['0x1004','0x1008'],test_register='x19',test_word='0xb4000053')
        next(r for r in alias['cfg']['blocks'][0]['instructions'] if r['pc']=='0x1008')['word']='0xb4000053'
        alias['value_facts']['observations']=[dict(pc='0x1004',origins=[dict(register='x19',origin='checked error alias')])]
        self.assertIsNotNone(h.geometry(alias,av))
        self.assertEqual(h.geometry(direct,validation),h.geometry(alias,av))


class QualificationHarnessTests(unittest.TestCase):
    def test_negative_changes_real_claim_and_refreshes_size(self):
        c=dict(identity=dict(call_pc='0x1000'),accounting=dict(encoded_bytes=0))
        h.seal_size(c)
        changed=h.delete_claim(c,('identity','call_pc'))
        self.assertEqual(changed['identity'],{})
        self.assertEqual(changed['accounting']['encoded_bytes'],len(h.canonical(changed)))
        self.assertEqual(c['identity']['call_pc'],'0x1000')

    def test_differentiation_counts_paths_not_bad_spellings(self):
        c=dict(identity=dict(call_pc='0x1000'),call=dict(binding=dict(secret='x'),reason='info'),
            cfg=dict(blocks=[dict(instructions=[dict(word='0x12345678')])]))
        paths=list(h.semantic_mutations(c))
        self.assertIn(('cfg','blocks',0,'instructions',0,'word'),paths)
        self.assertFalse(any('binding' in p or 'reason' in p for p in paths))
        self.assertEqual(len(paths),len(set(paths)))

    def test_stratified_repeat_selection_is_bounded_and_stable(self):
        rows=[dict(capture='primary',mode=m,family=f,geometry='g',lowering='x0',call_pc=i,target_pc='0x1000')
            for m in ('O','Onone','Osize') for f in ('free','struct') for i in range(30)]
        a=h.stratified_select(rows);b=h.stratified_select(list(reversed(rows)))
        self.assertEqual(a,b);self.assertEqual(len(a),100)
        self.assertEqual(len({(r['mode'],r['family']) for r in a[:6]}),6)

    def test_prepare_does_not_read_capture_or_create_output(self):
        import contextlib,io,tempfile
        with tempfile.TemporaryDirectory() as parent:
            output=Path(parent)/'uncreated'
            with contextlib.redirect_stdout(io.StringIO()) as result:
                code=h.main(['--output',str(output),'--capture','missing-primary','--second-capture','missing-second'])
            self.assertEqual(code,0);self.assertIn('UNRUN',result.getvalue())
            self.assertFalse(output.exists())

    def test_claim_domains_include_dispatch_nominal_entry_and_values(self):
        expected={('call','declaration','identity','callable_kind'):'dispatch',
            ('call','declaration','identity','context',0,'name'):'nominal',
            ('cfg','blocks',0,'predecessors',0,'source_pc'):'entry',
            ('value_facts','seed','register'):'valueattachment'}
        for path,kind in expected.items():self.assertEqual(h.attack_kind(path),kind)

    def test_shape_uses_admitted_name_free_storage_contract(self):
        shape=dict(arguments=[dict(locations=['w0'],width=32)],result=dict(locations=['x0'],width=64))
        self.assertEqual(h.emitted_shape(None,dict(status='admitted',abi_shape=shape)),h.canonical(shape))
        self.assertIsNone(h.emitted_shape(None,dict(status='unresolved')))

    def test_geometry_does_not_count_register_renaming_or_displacement(self):
        first=dict(post_call=dict(test_word='0xb4000055'),cfg=dict(blocks=[],returns=[]))
        second=dict(post_call=dict(test_word='0xb4008054'),cfg=dict(blocks=[],returns=[]))
        self.assertEqual(h.geometry(first,{}),h.geometry(second,{}))

    def test_unvalidated_source_labels_cannot_count_observed_challenges(self):
        self.assertEqual(h.observed_features({'source_geometry':'defer'},None,{}),[])
        self.assertEqual(h.observed_features({},dict(eligible=False),{}),[])

    def test_public_json_removes_all_private_custody_capabilities(self):
        self.assertEqual(h.public(dict(binding={},callsite_binding={},keep=True)),dict(keep=True))

    def test_optional_abi_field_is_changed_not_omitted(self):
        c=dict(call=dict(abi=dict(result_location='x0')),accounting=dict(encoded_bytes=0))
        changed=h.delete_claim(c,('call','abi','result_location'))
        self.assertIn('result_location',changed['call']['abi'])
        self.assertNotEqual(changed['call']['abi']['result_location'],'x0')

    def test_work_reservation_precedes_execution_and_charges_actual_once(self):
        budget=h.WorkBudget(100)
        self.assertTrue(budget.reserve('call',80));budget.charge('call',20,80)
        self.assertTrue(budget.reserve('call',80));budget.charge('call',30,80)
        self.assertFalse(budget.reserve('call',80))
        self.assertEqual(budget.report()['actual_steps'],50)
        self.assertEqual(budget.report()['omitted_units'],dict(call=1))
        with self.assertRaises(ValueError):budget.charge('call',81,80)

    def test_single_image_session_is_forwarded_for_refused_calls(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        image=object();fn=object();session=object()
        record=dict(status='declined',reason='test_noncall',work_steps=3)
        capability=SimpleNamespace(record=lambda:dict(record))
        with patch('airs.swift_callsite_admission.admit_callsite_capability',return_value=capability) as admit:
            admission,decl,candidate,validation=h.analyze_call(image,fn,0x1000,session=session)
        self.assertIs(admit.call_args.kwargs['session'],session)
        self.assertEqual(admission,record)
        self.assertIsNone(candidate);self.assertIsNone(validation)

    def test_private_capability_flows_only_to_abi_request(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        image=SimpleNamespace(path='mock harness input');fn=SimpleNamespace(start=0x1000)
        session=object();candidate={'mock_candidate':True};validation={'eligible':False}
        record=dict(status='admitted_callsite',symbol='_$s4Test3fooyS2iKF',callee_pc=0x1010,work_steps=4)
        capability=SimpleNamespace(record=lambda:dict(record))
        with patch('airs.swift_callsite_admission.admit_callsite_capability',return_value=capability), \
             patch('airs.swift_abi_profiles.admit_swift_abi',return_value=dict(status='admitted',binding={'private':'ABI'},callsite_binding={'private':'callsite'})) as abi, \
             patch('airs.swift_outcome_witness_v2.build_broad_swift_witness',return_value=candidate) as build, \
             patch('airs.swift_outcome_validator_v2.validate_broad_swift_witness',return_value=validation) as validate:
            h.analyze_call(image,fn,0x1000,session=session)
        self.assertIs(abi.call_args.kwargs['qualification'].callsite_capability,capability)
        self.assertEqual(build.call_args.args[2]['abi'],dict(status='admitted'))
        self.assertNotIn('binding',build.call_args.args[2])
        self.assertEqual(validate.call_args.args,(image,fn,candidate))
        self.assertEqual(validate.call_args.kwargs,{})

    def test_private_output_records_leave_complete_artifact_packaging_pending(self):
        import json,tempfile
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory);report=dict(state='INCOMPLETE',gates={})
            reviews=[dict(record=dict(reviewer='example-reviewer'))]
            h.write_qualification_outputs(output,report,reviews)
            self.assertEqual({p.name for p in output.iterdir()},{'qualification.json','reviews.json','README.txt'})
            saved=json.loads((output/'qualification.json').read_text())
            self.assertEqual(saved['artifact_packaging']['state'],'pending')
            self.assertEqual(json.loads((output/'reviews.json').read_text()),reviews)
            self.assertIn('PENDING separate sanitized complete handback',(output/'README.txt').read_text())

    def test_both_capture_directories_are_required_without_personal_defaults(self):
        import contextlib,io
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as missing:
                h.main(['--output','qualification-output'])
        self.assertEqual(missing.exception.code,2)

    def test_scope_negative_asserts_forbidden_proof_instead_of_harmless_omission(self):
        flags={key:False for key in h.SCOPE_FLAGS}
        c=dict(cfg=flags,accounting=dict(encoded_bytes=0))
        for key in h.SCOPE_FLAGS:
            changed=h.delete_claim(c,('cfg',key))
            self.assertIs(changed['cfg'][key],True)
            self.assertEqual(h.attack_kind(('cfg',key)),'proofscope')
            self.assertIs(c['cfg'][key],False)

    def test_second_compiler_requires_distinct_capture_path_and_version(self):
        a=dict(capture_directory='capture-a',compiler_path='compiler-a',compiler_version='Swift-A')
        b=dict(capture_directory='capture-b',compiler_path='compiler-b',compiler_version='Swift-B')
        self.assertTrue(h.distinct_compilers(a,b))
        for key in a:
            copied=dict(b);copied[key]=a[key]
            self.assertFalse(h.distinct_compilers(a,copied))

    def test_input_preflight_bounds_bytes_tokens_depth_and_array_counts(self):
        import json,tempfile
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'input.json'
            for content,kwargs in [('{"x":"'+'a'*32+'"}',dict(max_bytes=12)),
                    ('{"x":[1,2,3,4]}',dict(max_tokens=5)),
                    ('{"x":[[[[0]]]]}',dict(max_depth=3))]:
                path.write_text(content)
                with self.assertRaises(h.JSONBoundError):h.read_bounded_json(path,**kwargs)
            with self.assertRaises(h.JSONBoundError):
                h.validate_capture_counts(dict(cases=[{}]*1001),dict(modes={}),dict(modes={}))
            with self.assertRaises(h.JSONBoundError):
                h.validate_capture_counts(dict(cases=[]),dict(modes=dict(O=dict(calls=[{}]*10001))),dict(modes=dict(O={})))

    def test_aggregate_retention_and_streamed_report_stop_at_explicit_caps(self):
        import tempfile
        budget=h.RetentionBudget(80)
        self.assertTrue(budget.admit(dict(word='x'*20)))
        self.assertFalse(budget.admit(dict(word='x'*60)))
        self.assertEqual(budget.omitted['physical_call_record'],1)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'bounded.json'
            with self.assertRaises(h.JSONBoundError):h.write_bounded_json(path,dict(words=['x'*40]*3),64)
            self.assertFalse(path.exists())
            self.assertLessEqual(path.with_name('bounded.json.partial').stat().st_size,64)

    def test_raw_unsupported_challenges_use_authored_words_and_preserve_pc_bytes(self):
        words=[0xd63f0100,0xd61f0100,0xd4200000,0x14000100,0xd65f03c0]
        observed={r['feature']:r for r in h.classify_raw_words(words,0x1000)}
        self.assertTrue({'raw_indirect_blr','raw_indirect_tail_br','raw_trap_brk','raw_direct_tail_escape',
            'lexical_call_and_later_ret_without_error_test'}<=set(observed))
        self.assertEqual(observed['raw_indirect_blr']['evidence'],[dict(pc='0x1000',word='0xd63f0100')])
        # A local direct hop and NOP cannot manufacture indirect/tail/trap evidence.
        control={r['feature'] for r in h.classify_raw_words([0x14000001,0xd503201f,0xd65f03c0],0x1000)}
        self.assertFalse(control&{'raw_direct_tail_escape','raw_indirect_blr','raw_trap_brk'})

    def test_index_absence_is_explicit_unconfirmed_and_not_source_inlining_intent(self):
        zero=dict(case_id='case-a',confirmed_owned_target_calls=0,actual_call_instructions=0,
            emission_status='optimized_away_or_no_owned_call_observed')
        actual=dict(zero,case_id='case-b',actual_call_instructions=1)
        intended=dict(case_id='case-c',inline_absence_challenge=True)
        rows=h.index_absence_observations([zero,actual,intended])
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['case_id'],'case-a')
        self.assertEqual(rows[0]['disposition'],'unconfirmed_owned_call_absence_not_inlining_proof')

    def test_raw_caller_records_stream_before_scanning_the_next_function(self):
        from types import SimpleNamespace
        class Image:
            functions=[SimpleNamespace(name='broad_caller_0000_0',start=0x1000,size=4),
                SimpleNamespace(name='broad_caller_0001_0',start=0x1004,size=4)]
            reads=0
            def bytes_at(self,pc,size):self.reads+=1;return bytes.fromhex('c0035fd6')
        image=Image();budget=h.WorkBudget(10000)
        rows=h.scan_source_callers(image,{'broad_caller_0000_0','broad_caller_0001_0'},budget)
        self.assertEqual(image.reads,0)
        self.assertTrue(next(rows)['complete']);self.assertEqual(image.reads,1)
        self.assertEqual(budget.used,len('broad_caller_0000_0')+1+3)

    def test_lexical_later_return_does_not_claim_cfg_reachability(self):
        observed={r['feature']:r for r in h.classify_raw_words([0x94000004,0x14000000,0xd65f03c0],0x1000)}
        row=observed['lexical_call_and_later_ret_without_error_test']
        self.assertEqual(row['scope'],'lexical_instruction_syntax_only_not_reachability')

    def test_independent_validator_ledger_is_forwarded_without_producer_session(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        image=SimpleNamespace(path='authored ledger plumbing');fn=SimpleNamespace(start=0x1000)
        producer_session=object();independent_ledger=object();candidate={'authored':True}
        capability=SimpleNamespace(record=lambda:dict(status='admitted_callsite',
            symbol='_$s4Test3fooyS2iKF',callee_pc=0x1010,work_steps=4))
        with patch('airs.swift_callsite_admission.admit_callsite_capability',return_value=capability) as callsite, \
             patch('airs.swift_abi_profiles.admit_swift_abi',return_value=dict(status='admitted')) as abi, \
             patch('airs.swift_outcome_witness_v2.build_broad_swift_witness',return_value=candidate) as build, \
             patch('airs.swift_outcome_validator_v2.validate_broad_swift_witness',return_value={'eligible':False}) as validate:
            h.analyze_call(image,fn,0x1000,session=producer_session,image_ledger=independent_ledger)
        self.assertIs(callsite.call_args.kwargs['session'],producer_session)
        self.assertIs(abi.call_args.kwargs['qualification'].callsite_capability,capability)
        self.assertEqual(build.call_args.kwargs,{})
        self.assertEqual(validate.call_args.args,(image,fn,candidate))
        self.assertEqual(validate.call_args.kwargs,{'_image_ledger':independent_ledger})

    def test_standalone_validator_image_work_is_charged_separately_once(self):
        admission=dict(work_steps=4,abi=dict(work_steps=5))
        candidate=dict(accounting=dict(work=6))
        standalone=dict(accounting=dict(work=7,image_work_charged_here=11))
        reused=dict(accounting=dict(work=7,image_work_charged_here=0))
        self.assertEqual(h.unit_work(admission,candidate,standalone),33)
        self.assertEqual(h.unit_work(admission,candidate,reused),22)

    def test_exception_scope_attacks_assert_proof_and_skip_optional_description(self):
        c=dict(cfg=dict(exception_resume_proven=False,
            external_exception_handling_unmodeled=True,
            exception_transfers=[dict(resume_proven=False)]),accounting=dict(encoded_bytes=0))
        paths=list(h.semantic_mutations(c))
        self.assertNotIn(('cfg','external_exception_handling_unmodeled'),paths)
        for path in [('cfg','exception_resume_proven'),('cfg','exception_transfers',0,'resume_proven')]:
            self.assertIn(path,paths);changed=h.delete_claim(c,path)
            value=changed
            for key in path:value=value[key]
            self.assertIs(value,True);self.assertEqual(h.attack_kind(path),'proofscope')

    def test_representative_index_is_second_only_pre_marker_metadata_admission(self):
        from copy import deepcopy
        manifest=dict(cases=[dict(source_callsites=[]) for _ in range(64)])
        index=dict(state='indexed_representative',modes={mode:dict(calls=[dict(
            owned_target_confirmed=True,pc='0x1000')]) for mode in ('Onone','O','Osize')})
        receipt=dict(schema='airs.owned-swift-broad-compile.v2',state='indexed',
            modes={mode:{} for mode in ('Onone','O','Osize')})
        accepted=h.validate_capture_prerequisites('second',manifest,index,receipt)
        self.assertEqual(accepted['scope'],'representative_second_compiler')
        self.assertEqual(accepted['confirmed_physical_calls'],3)
        self.assertEqual(accepted['minimum_required_calls'],1)
        with self.assertRaisesRegex(ValueError,'primary requires complete indexed'):
            h.validate_capture_prerequisites('primary',manifest,index,receipt)
        empty=deepcopy(index)
        for mode in empty['modes'].values():
            for call in mode['calls']:call['owned_target_confirmed']=False
        with self.assertRaisesRegex(ValueError,'confirmed physical call'):
            h.validate_capture_prerequisites('second',manifest,empty,receipt)
        missing=deepcopy(index);missing['modes']['O']['calls']=[]
        with self.assertRaisesRegex(ValueError,'modes must contain'):
            h.validate_capture_prerequisites('second',manifest,missing,receipt)

    def test_repair2_owned_absence_allows_indexed_runtime_call_with_exact_source_mapping(self):
        case=dict(case_id='owned-a',inline_absence_challenge=True)
        link=dict(case_id='owned-a',caller='broad_caller_0000_0',source_geometry='inline_absence_challenge')
        transfers=h.caller_transfer_inventory([0x94000040,0xd65f03c0],0x1000)
        scan=dict(caller_token=link['caller'],complete=True,control_transfer_inventory_complete=True,
            control_transfers=transfers,extent_evidence=[dict(pc='0x1000',word='0x94000040')])
        index={'0x1000':dict(pc='0x1000',instruction_word='0x94000040',target_pc='0x1100',
            call_kind='direct',owned_target_case_ids=[])}
        mapping=dict(complete=True,targets=[dict(pc='0x2000',symbol='authored-owned-target')])
        row=h.source_callee_absence_observation(case,link,scan,index,mapping)
        self.assertTrue(row['complete']);self.assertFalse(row['inlining_cause_proven'])
        row.update(capture='primary',mode='O',image_identity={})
        record=next(x for x in h.required_challenge_dispositions(row) if x['challenge']=='optimized_inlined_absence')
        self.assertTrue(record['actual_form_observed'])

    def test_repair2_owned_absence_refuses_unknown_indirect_real_target_and_partial_mapping(self):
        from copy import deepcopy
        case=dict(case_id='owned-a',inline_absence_challenge=True)
        link=dict(source_geometry='inline_absence_challenge',caller='broad_caller_0000_0')
        mapping=dict(complete=True,targets=[dict(pc='0x1100')])
        index={'0x1000':dict(instruction_word='0x94000040',target_pc='0x1100',call_kind='direct')}
        for words in ([0xd63f0100,0xd65f03c0],[0x94000040,0xd65f03c0],[0x14000040,0xd65f03c0]):
            scan=dict(complete=True,control_transfer_inventory_complete=True,
                control_transfers=h.caller_transfer_inventory(words,0x1000))
            row=h.source_callee_absence_observation(case,link,scan,index,mapping)
            self.assertFalse(row['complete'])
        scan=dict(complete=True,control_transfer_inventory_complete=True,control_transfers=[])
        self.assertFalse(h.source_callee_absence_observation(case,link,scan,{},dict(complete=False,targets=[]))['complete'])
        # A zero-call aggregate index alone no longer establishes the challenge.
        legacy=dict(feature='indexed_owned_call_absence',capture='primary',mode='O',source_callers=[link],
            absence_callers=[dict(complete=True,call_instruction_count=0,caller_token=link['caller'])])
        self.assertFalse(any(x['actual_form_observed'] for x in h.required_challenge_dispositions(legacy)
            if x['challenge']=='optimized_inlined_absence'))

    def test_repair2_transfer_inventory_covers_escaping_conditional_and_internal_hop_control(self):
        words=[0x14000001,0xd63f0100,0x54000800,0xd65f03c0]
        rows=h.caller_transfer_inventory(words,0x1000)
        self.assertEqual([r['kind'] for r in rows],['unresolved_indirect','conditional_escape'])
        self.assertEqual(rows[1]['target_pc'],'0x1108')

    def test_repair2_selected_arm_cmp_is_distinct_from_primary_error_zero_test(self):
        c,v=B11MeasuringContractTests().selected()
        c['cfg']['blocks'][0]['instructions'] += [dict(pc='0x1010',word='0xeb09011f',kind='xsubs_reg'),
            dict(pc='0x1014',word='0x5400022c',kind='bcond')]
        v['region_partition']['success_only_pcs']+=['0x1010','0x1014']
        row=dict(capture='primary',mode='O',candidate=c,validation=v,
            source_callers=[dict(caller='authored-caller',source_geometry='handled')])
        records=h.required_challenge_dispositions(row)
        comparison=next(r for r in records if r['challenge']=='cmp_conditional')
        self.assertTrue(comparison['actual_form_observed'])
        self.assertFalse(comparison['comparison_form']['error_zero_test'])
        self.assertEqual(comparison['raw_evidence'],[dict(pc='0x1010',word='0xeb09011f'),dict(pc='0x1014',word='0x5400022c')])
        self.assertTrue(any(r['challenge']=='cbz' for r in records))

    def test_repair2_arm_cmp_refuses_prefix_reserved_and_non_cmp_subs(self):
        from copy import deepcopy
        base,validation=B11MeasuringContractTests().selected()
        for word in ('0xeb09011e','0xebc9011f','0x6b09811f'):
            c=deepcopy(base);v=deepcopy(validation)
            c['cfg']['blocks'][0]['instructions'] += [dict(pc='0x1010',word=word,kind='xsubs_reg'),
                dict(pc='0x1014',word='0x5400022c',kind='bcond')]
            v['region_partition']['success_only_pcs']+=['0x1010','0x1014']
            self.assertEqual(h.selected_arm_cmp_conditions(c,v),[])
        c=deepcopy(base)
        c['cfg']['blocks'][0]['instructions']=[dict(pc='0xff0',word='0xeb09011f',kind='xsubs_reg'),
            dict(pc='0xff4',word='0x5400022c',kind='bcond')]+c['cfg']['blocks'][0]['instructions']
        self.assertEqual(h.selected_arm_cmp_conditions(c,validation),[])

    def supplemental_receipt_fixture(self):
        c,v=B11MeasuringContractTests().selected()
        identity=dict(slice_sha256='a'*64,container_sha256='a'*64,slice_offset='0x0',slice_size='0x100',
            architecture='arm64',cpu_subtype=0,uuid=None,preferred_base='0x0',slice_index=0,container_slice_count=1)
        c.update(model_version='swift-outcome-witness-v2',validation_model='swift-outcome-validation-v2',
            eligible=False,completeness=dict(complete=True,missing=[]))
        c['identity']=dict(identity,call_pc='0x1000',caller=dict(start_pc='0x1000',end_pc_exclusive='0x1010'))
        c['call']['word']='0x94000008'
        v.update(model_version='swift-outcome-validation-v2',completeness=dict(complete=True,missing=[]),
            facts={k:'independently checked authored fixture' for k in ('identity','call','abi','cfg','post_call','regions')})
        v['fact_statuses'].update({k:'checked' for k in ('identity','call','abi','cfg','post_call','regions')})
        for key in ('runtime_branch_proven','call_return_proven','error_state_proven','source_reconstruction_allowed','handler_semantics_proven','exclusive_entry_proven'):v[key]=False
        row=dict(capture='supplemental',mode='O',call_pc=0x1000,caller_pc='0x1000',eligible=True,
            image_identity=identity,candidate=c,validation=v,admission=dict(model_version='swift-broad-callsite-v1',call_pc=0x1000),
            source_callers=[dict(caller='authored-supplement',source_geometry='local_error_conversion')])
        row['required_challenge_dispositions']=h.required_challenge_dispositions(row)
        inventory=h.challenge_inventory([row],[],[],capture_role='supplemental',challenges=h.SUPPLEMENTAL_CHALLENGES)
        return dict(schema='airs.swift-broad-supplemental-study.v1',source_revision='frozen-authored-head',
            role='supplemental_challenge_only',state='INCOMPLETE',not_primary_positive_credit=True,not_second_compiler_credit=True,
            supplemental_capture_evidence=dict(used=True,role='supplemental_challenge_only',source_sha256='b'*64,
                images=dict(Onone='c'*64,O='a'*64,Osize='d'*64)),observation_count=1,observations=[row],required_challenge_inventory=inventory)

    def test_supplemental_receipt_reuse_merges_only_allowed_challenge_without_primary_credit(self):
        receipt=self.supplemental_receipt_fixture()
        accepted=h.validate_supplemental_study(receipt,'frozen-authored-head')
        primary=h.challenge_inventory([],[],[])
        merged=h.merge_supplemental_challenges(primary,accepted)
        self.assertTrue(merged['entries']['local_error_conversion']['observed'])
        self.assertFalse(primary['entries']['local_error_conversion']['observed'])
        self.assertFalse(merged['entries']['nested_handlers']['observed'])
        self.assertFalse(merged['entries']['cbz']['observed'])
        self.assertNotIn('primary_eligible',merged)

    def test_supplemental_receipt_rejects_stale_unknown_forged_or_unchecked_claims(self):
        from copy import deepcopy
        base=self.supplemental_receipt_fixture()
        mutations=[lambda x:x.update(source_revision='stale'),
            lambda x:x['supplemental_capture_evidence']['images'].update(O='e'*64),
            lambda x:x.update(observation_count=2),
            lambda x:x['required_challenge_inventory']['entries']['local_error_conversion'].update(observed=False),
            lambda x:x['observations'][0]['validation']['fact_statuses'].update(cfg='unchecked'),
            lambda x:x['observations'][0]['required_challenge_dispositions'].append(dict(challenge='invented')),
            lambda x:x['observations'][0]['candidate']['call'].update(word='0x94000009')]
        for change in mutations:
            receipt=deepcopy(base);change(receipt)
            with self.assertRaises(ValueError):h.validate_supplemental_study(receipt,'frozen-authored-head')

    def test_supplemental_receipt_preserves_refusal_without_observed_credit(self):
        receipt=self.supplemental_receipt_fixture();row=receipt['observations'][0]
        row.update(eligible=False,candidate=None,validation=dict(model_version='swift-outcome-validation-v2',eligible=False,status='unresolved'),required_challenge_dispositions=[])
        receipt['required_challenge_inventory']=h.challenge_inventory([row],[],[],capture_role='supplemental',challenges=h.SUPPLEMENTAL_CHALLENGES)
        self.assertIs(h.validate_supplemental_study(receipt,'frozen-authored-head'),receipt)
        self.assertFalse(receipt['required_challenge_inventory']['complete'])
