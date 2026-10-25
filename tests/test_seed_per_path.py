import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts'/'seed_ideation.py'
SPEC=ROOT/'examples'/'four_ideas_funnel.json'

def cli(*args):
    return subprocess.run([sys.executable,str(SCRIPT),*args],text=True,capture_output=True)

class IndependentSeedTests(unittest.TestCase):
    def test_new_provides_one_unique_seed_per_route(self):
        r=cli('new','--spec',str(SPEC),'--count','64','--format','json')
        self.assertEqual(r.returncode,0,r.stderr)
        x=json.loads(r.stdout)
        self.assertEqual(len(x['seeds']),64)
        self.assertEqual(len(x['candidates']),64)
        self.assertEqual(len({c['seed'] for c in x['candidates']}),64)
        self.assertEqual([c['number'] for c in x['candidates']],list(range(1,65)))
        self.assertTrue(all(c['seed']==x['seeds'][i]['seed'] for i,c in enumerate(x['candidates'])))

    def test_same_seed_same_design_route_independent_of_index(self):
        seed='K7M28QVAT3XPH6RD'
        a=cli('replay','--spec',str(SPEC),'--seed',seed,'--start','1','--format','json')
        b=cli('replay','--spec',str(SPEC),'--seed',seed,'--start','22','--format','json')
        self.assertEqual(a.returncode,0,a.stderr);self.assertEqual(b.returncode,0,b.stderr)
        a=json.loads(a.stdout)['candidates'][0];b=json.loads(b.stdout)['candidates'][0]
        self.assertEqual(a['exploration_axis'],b['exploration_axis'])
        self.assertEqual(a['anchors'],b['anchors'])
        self.assertNotEqual(a['number'],b['number'])

    def test_plan_is_independently_generated_and_replayable(self):
        a=cli('plan','--spec',str(SPEC),'--pool-size','64')
        b=cli('plan','--spec',str(SPEC),'--pool-size','64')
        self.assertEqual(a.returncode,0,a.stderr);self.assertEqual(b.returncode,0,b.stderr)
        x=json.loads(a.stdout);y=json.loads(b.stdout)
        self.assertEqual(len(set(p['seed'] for p in x['paths'])),64)
        self.assertNotEqual([p['seed'] for p in x['paths']],[p['seed'] for p in y['paths']])
        with tempfile.TemporaryDirectory() as d:
            plan=Path(d)/'manifest.json';plan.write_text(a.stdout,encoding='utf8')
            x1=cli('batch','--plan',str(plan),'--spec',str(SPEC),'--start','1','--format','json')
            x2=cli('batch','--plan',str(plan),'--spec',str(SPEC),'--start','33','--format','json')
            self.assertEqual(x1.returncode,0,x1.stderr);self.assertEqual(x2.returncode,0,x2.stderr)
            seeds=[r['seed'] for r in json.loads(x1.stdout)['candidates']+json.loads(x2.stdout)['candidates']]
            self.assertEqual(seeds,[p['seed'] for p in x['paths']])

    def test_duplicate_and_modified_manifest_fails_closed(self):
        original=cli('plan','--spec',str(SPEC),'--pool-size','64')
        self.assertEqual(original.returncode,0,original.stderr)
        with tempfile.TemporaryDirectory() as d:
            plan=Path(d)/'plan.json'
            for field in ('duplicate','modified','wrong_spec','legacy'):
                x=json.loads(original.stdout)
                if field=='duplicate': x['paths'][1]['seed']=x['paths'][0]['seed']
                if field=='modified': x['paths'][0]['seed']='ABCD'
                if field=='wrong_spec': x['spec_fingerprint']='bad'
                if field=='legacy': x['seed_model']='one-master-seed'
                plan.write_text(json.dumps(x),encoding='utf8')
                result=cli('batch','--plan',str(plan),'--spec',str(SPEC),'--start','1','--format','json')
                self.assertNotEqual(result.returncode,0,field)

    def test_reject_ambiguous_old_interface(self):
        x=cli('batch','--spec',str(SPEC),'--seed','K7M28QVAT3XPH6RD','--start','1')
        self.assertNotEqual(x.returncode,0)
        self.assertIn('--plan',x.stderr)
        x=cli('plan','--spec',str(SPEC),'--seed','K7M28QVAT3XPH6RD')
        self.assertNotEqual(x.returncode,0)
        x=cli('replay','--spec',str(SPEC),'--seed','K7M28QVAT3XPH6RD','--count','4')
        self.assertNotEqual(x.returncode,0)

class SeedFunnelLineageTests(unittest.TestCase):
    def test_selector_checks_linkage_without_faking_semantics(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        from seed_ideation import make_plan
        from funnel_select import audit_seed_lineage
        spec=json.loads(SPEC.read_text(encoding='utf8'))
        manifest=make_plan(spec,pool_size=64)
        pool=[{'path_number':p['number'],'seed':p['seed'],
               'seed_fingerprint':p['seed_fingerprint']} for p in manifest['paths']]
        result=audit_seed_lineage(pool,manifest)
        self.assertEqual(result['candidate_paths'],64)
        self.assertFalse(result['semantic_seed_usage_verified'])
        broken=[dict(p) for p in pool]
        broken[1]['path_number']=1
        with self.assertRaises(ValueError):audit_seed_lineage(broken,manifest)
        broken=[dict(p) for p in pool]
        broken[2]['seed']=pool[1]['seed']
        with self.assertRaises(ValueError):audit_seed_lineage(broken,manifest)
