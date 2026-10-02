from pathlib import Path
import json, tempfile, hashlib
import ifcopenshell
from adapters.ifc_bonsai import load_ifc_neutral_scene
from test.fixtures.ifc4_description_fixture import write_ifc4_description_fixture
out=Path('outputs/design/space_field_ifc_input_contract_experiment'); out.mkdir(parents=True,exist_ok=True)
live=Path('outputs/full-rhino-ifc-2026-09-23/live-rhino-10500-furniture-groups.ifc')
def counts(f): return {k:len(f.by_type(k)) for k in ['IfcSpace','IfcOpeningElement','IfcRelVoidsElement','IfcRelFillsElement','IfcDoor','IfcWall','IfcFurniture']}
def summary(s):
 d=s.to_dict(); return {'analysis_domain':d.get('analysis_domain'),'counts':{k:len(d.get(k,[])) for k in ['source_objects','geometries','openings','uncertainties']},'uncertainty_codes':sorted({u['code'] for u in d.get('uncertainties',[])})}
rows=[]; lf=ifcopenshell.open(str(live)); rows.append({'case':'live_ifc','ifc_observed':{'schema':lf.schema,'counts':counts(lf)},'adapter_output':'not_run_timeout_guard','provenance':'direct_observation'})
with tempfile.TemporaryDirectory(dir=str(out)) as td:
 p=Path(td)/'fixture.ifc'; ids=write_ifc4_description_fixture(p); f=ifcopenshell.open(str(p))
 for case,dom in [('fixture_no_domain',None),('fixture_explicit_domain',ids['room'])]:
  s=load_ifc_neutral_scene(p,analysis_domain_source_id=dom); rows.append({'case':case,'ifc_observed':{'schema':f.schema,'counts':counts(f)},'adapter_output':summary(s),'provenance':'adapter_output'})
 f.by_guid(ids['room']).Representation=None; s=load_ifc_neutral_scene(f,analysis_domain_source_id=ids['room']); rows.append({'case':'fixture_domain_missing_geometry','adapter_output':summary(s),'provenance':'adapter_output'})
 f2=ifcopenshell.open(str(p)); [f2.remove(r) for r in list(f2.by_type('IfcRelVoidsElement'))]; s=load_ifc_neutral_scene(f2,analysis_domain_source_id=ids['room']); d=summary(s); d['opening_host_refs']=[o['host_refs'] for o in s.to_dict()['openings']]; rows.append({'case':'fixture_opening_relation_missing','adapter_output':d,'provenance':'adapter_output'})
for st in ('partial','conflict','unsupported'): rows.append({'case':st,'proposed_status':st,'current_unified_api':False,'provenance':'design_observation'})
report={'schema':'d6-space-field-ifc-input-contract-experiment-v1','date':'2026-10-01','rows':rows,'downstream_gate':{'no_qualified_domain':{'free_space':'not_available','components':'not_available','connectivity':'not_available','path':'not_available'},'diagnostic_view_bounds':'diagnostic_only'},'limitations':['No production free-space algorithm executed','status vocabulary is proposed, not current unified API','fixture variants mutated only in memory']}
(out/'experiment_results.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
(out/'provenance.json').write_text(json.dumps({'source_files':[str(live),'test/fixtures/ifc4_description_fixture.py','adapters/ifc_bonsai.py','features/scene_contract.py','features/neutral_scene_views.py'],'observed_vs_derived':{'ifc':'direct observation','adapter':'NeutralSceneV2 output','status':'design observation'}},indent=2,sort_keys=True)+'\n')
print(json.dumps({'rows':len(rows),'result':str(out/'experiment_results.json')}))



