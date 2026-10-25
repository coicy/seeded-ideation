import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/'examples'/'four_ideas_funnel.json'
SEED='K7M28QVAT3XPH6RD'


def route(*args):
    return subprocess.run([sys.executable,str(ROOT/'scripts'/'seed_ideation.py'),*args],text=True,capture_output=True)


def pool_item(i, position=None, sig=None, attrs=None, status='pass', evidence='mechanism matches the stated needs'):
    return {'id':f'i{i:03d}','concept':f'Short distinct concept {i}',
            'position':position or f'role-{i%12}',
            'mechanism_signature':sig or f'operation-{i}',
            'mechanism_tags':[f'operation-{i%17}', f'axis-{i%11}'],
            'new_attributes':attrs if attrs is not None else [],
            'requirement_checks':{'R1':{'status':status,'evidence':evidence},
                                  'R2':{'status':'pass','evidence':'describes workflow and benefit'}},
            'scores':{'fit':3+(i%5)/3,'usefulness':3.3,
                      'feasibility':3.6,'novelty':3.5+(i%3)/3}}


def attach_lineage(items,plan):
    for item,path in zip(items,plan['paths']):
        item['path_number']=path['number']
        item['seed']=path['seed']
        item['seed_fingerprint']=path['seed_fingerprint']


class FunnelTests(unittest.TestCase):
    def test_plan_256_4_and_8_batches(self):
        r=route('plan','--spec',str(SPEC),'--format','json')
        self.assertEqual(r.returncode,0,r.stderr)
        j=json.loads(r.stdout)
        self.assertEqual((j['planned_initial_candidates'],j['final_items'],j['batch_size']),(256,4,32))
        self.assertEqual(j['seed_model'],'independent-per-path')
        self.assertEqual(len(j['paths']),256)
        self.assertEqual(len(set(x['seed'] for x in j['paths'])),256)
        self.assertEqual(j['initial_candidates_generated'],0)
        self.assertEqual([b['start'] for b in j['batches']],[1,33,65,97,129,161,193,225])
        self.assertNotIn('seed',j)  # no misleading master seed

    def test_repeatable_batch_global_indices(self):
        with tempfile.TemporaryDirectory() as d:
            plan=Path(d)/'plan.json'
            p=route('plan','--spec',str(SPEC))
            self.assertEqual(p.returncode,0,p.stderr)
            plan.write_text(p.stdout,encoding='utf8')
            args=('batch','--plan',str(plan),'--spec',str(SPEC),'--start','33','--format','json')
            a=route(*args);b=route(*args)
            self.assertEqual(a.returncode,0,a.stderr)
            self.assertEqual(a.stdout,b.stdout)
            doc=json.loads(a.stdout)
            self.assertEqual(doc['start_index'],32)
            self.assertEqual((doc['candidates'][0]['number'],doc['candidates'][-1]['number']),(33,64))
            self.assertEqual(len(set(x['seed'] for x in doc['candidates'])),32)
            tail=route('batch','--plan',str(plan),'--spec',str(SPEC),'--start','255','--format','json')
            self.assertEqual(tail.returncode,0,tail.stderr)
            self.assertEqual([x['number'] for x in json.loads(tail.stdout)['candidates']],[255,256])
            single=route('replay','--plan',str(plan),'--spec',str(SPEC),'--start','35','--format','json')
            self.assertEqual(single.returncode,0,single.stderr)
            self.assertEqual(json.loads(single.stdout)['candidates'][0],doc['candidates'][2])

    def test_256_pool_rejects_fail_uncertain_and_dedups(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        from funnel_select import funnel
        from seed_ideation import make_plan
        spec=json.loads(SPEC.read_text(encoding='utf8'))
        items=[pool_item(i) for i in range(256)]
        items[0]['requirement_checks']['R1']={'status':'fail','evidence':'contradiction'}
        items[1]['requirement_checks']['R1']={'status':'uncertain','evidence':'cannot verify'}
        items[2]['requirement_checks']['R1']={'status':'pass','evidence':''}
        items[4]['mechanism_signature']=items[3]['mechanism_signature']
        plan=make_plan(spec)
        attach_lineage(items,plan)
        report=funnel(spec,{'items':items},plan=plan)
        self.assertTrue(report['selection_complete'],report)
        self.assertEqual(report['observed_pool'],256)
        self.assertEqual(report['rejected'],3)
        self.assertEqual(report['deduplicated'],1)
        self.assertEqual([stage['remaining'] for stage in report['stages']],[128,64,32,16,8,4])
        self.assertEqual(len(report['finalists']),4)
        self.assertEqual(report['declared_distinct_positions'],4)
        self.assertTrue(set(row['id'] for row in report['finalists']).isdisjoint({'i000','i001','i002'}))

    def test_incomplete_pool_is_not_mislabeled_complete(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        from funnel_select import funnel
        from seed_ideation import make_plan
        spec=json.loads(SPEC.read_text(encoding='utf8'))
        plan=make_plan(spec)
        items=[pool_item(i) for i in range(30)]
        attach_lineage(items,plan)
        report=funnel(spec,{'items':items},plan=plan)
        self.assertFalse(report['selection_complete'])
        self.assertEqual(report['reason'],'incomplete_pool')

    def test_global_budget_avoids_greedy_attr_lockin(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        from funnel_select import choose_final_beam
        items=[pool_item(i,position=f'role{i}',attrs=['a'] if i==0 else ['b']) for i in range(10)]
        items[0]['scores']={'fit':5,'usefulness':5,'feasibility':5,'novelty':5}
        result=choose_final_beam(items,4,attr_limit=1,min_positions=4)
        self.assertEqual(len(result),4)
        self.assertEqual({x['new_attributes'][0] for x in result},{'b'})

    def test_unreviewed_or_no_mechanism_is_excluded(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        from funnel_select import assess
        item=pool_item(1)
        item['mechanism_tags']=[]
        item['requirement_checks'].pop('R2')
        errs=assess(item,['R1','R2'])
        self.assertIn('not_reviewed:R2',errs)
        item['requirement_checks']['R2']={'status':'pass','evidence':'supported'}
        self.assertIn('missing_mechanism_tags',assess(item,['R1','R2']))

    def test_rejected_sketch_needs_no_quality_scores(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        from funnel_select import assess
        item={'id':'x','concept':'fails constraint','requirement_checks':{'R1':{'status':'fail','evidence':'forbidden'},'R2':{'status':'pass','evidence':'yes'}}}
        self.assertEqual(assess(item,['R1','R2']),['fail:R1'])

    def test_cli_end_to_end(self):
        items=[pool_item(i) for i in range(256)]
        with tempfile.TemporaryDirectory() as d:
            pool=Path(d)/'pool.json'; pool.write_text(json.dumps({'items':items}),encoding='utf8')
            plan_file=Path(d)/'plan.json'
            sys.path.insert(0,str(ROOT/'scripts'))
            from seed_ideation import make_plan
            plan=make_plan(json.loads(SPEC.read_text(encoding='utf8')))
            attach_lineage(items,plan)
            pool.write_text(json.dumps({'items':items}),encoding='utf8')
            plan_file.write_text(json.dumps(plan),encoding='utf8')
            report=Path(d)/'report.json'
            r=subprocess.run([sys.executable,str(ROOT/'scripts'/'funnel_select.py'),
                              '--spec',str(SPEC),'--candidates',str(pool),'--plan',str(plan_file),'--output',str(report)],
                             capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertTrue(json.loads(report.read_text())['selection_complete'])


if __name__=='__main__':unittest.main()
