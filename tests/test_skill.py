import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts'/'seed_ideation.py'
EX=ROOT/'examples'
SEED='L7DVM8ASW8AWR3TA'


def run(*args):
    return subprocess.run([sys.executable,str(SCRIPT),*args],text=True,capture_output=True)


class RequestLedSkillTests(unittest.TestCase):
    def test_request_required_if_spec_missing(self):
        r=run('new')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('--request or --spec',r.stderr)

    def test_existing_game_can_allow_up_to_seven_attributes(self):
        r=run('replay','--seed',SEED,'--spec',str(EX/'settlement_cards.json'),'--format','json','--wildness','5')
        self.assertEqual(r.returncode,0,r.stderr)
        obj=json.loads(r.stdout)
        self.assertEqual(obj['deliverables']['max_new_attributes'],7)
        self.assertEqual(obj['count'],20)
        self.assertEqual(len(obj['candidates']),20)
        self.assertNotIn('novelty_budget',obj)
        self.assertEqual(obj['candidates'][0]['exploration_axis']['name'] in [v['name'] for v in obj['freedoms']],True)

    def test_same_seed_and_spec_replay_is_deterministic(self):
        args=['replay','--seed',SEED,'--spec',str(EX/'settlement_cards.json'),'--format','json']
        a=run(*args); b=run(*args)
        self.assertEqual(a.returncode,0,a.stderr)
        self.assertEqual(a.stdout,b.stdout)

    def test_approved_redesign_does_not_force_old_constraints(self):
        r=run('replay','--seed',SEED,'--spec',str(EX/'ux_redesign.json'),'--format','json')
        self.assertEqual(r.returncode,0,r.stderr)
        obj=json.loads(r.stdout)
        self.assertIn('不必沿用旧的栏目',obj['request'])
        self.assertEqual(len(obj['candidates']),4)
        self.assertFalse(any('anchored' in str(x) for x in obj.values()))

    def test_non_game_use_is_supported(self):
        r=run('replay','--seed',SEED,'--spec',str(EX/'writing_campaign.json'),'--format','json')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads(r.stdout)['count'],5)

    def test_direct_short_form(self):
        r=run('replay','--seed',SEED,'--request','设计四种界面布局',
              '--hard','移动端可用','--prefer','操作简单','--axis','界面构图','--format','json')
        self.assertEqual(r.returncode,0,r.stderr)
        obj=json.loads(r.stdout)
        self.assertEqual(obj['freedoms'][0]['name'],'界面构图')
        self.assertEqual([x['level'] for x in obj['requirements']],['must','prefer'])

    def test_validator_measurable_pass(self):
        items=[]
        for i in range(20):
            items.append({'id':f'C{i+1:02d}','position':f'定位{i%8}',
                          'variants':['a','b'],'new_attributes':[f'field{i%7}']})
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'items.json'; p.write_text(json.dumps({'items':items}),encoding='utf8')
            r=run('validate','--spec',str(EX/'settlement_cards.json'),'--candidates',str(p))
        self.assertEqual(r.returncode,0,r.stderr)
        data=json.loads(r.stdout)
        self.assertTrue(data['mechanical_pass'])
        self.assertTrue(data['semantic_review_required'])
        self.assertEqual(data['observed']['unique_new_attributes'],7)

    def test_validator_rejects_eighth_global_field(self):
        items=[]
        for i in range(20):
            items.append({'id':f'C{i+1:02d}','position':f'定位{i%8}',
                          'variants':['a','b'],'new_attributes':[f'field{i%8}']})
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'items.json'; p.write_text(json.dumps({'items':items}),encoding='utf8')
            r=run('validate','--spec',str(EX/'settlement_cards.json'),'--candidates',str(p))
        self.assertEqual(r.returncode,1)
        self.assertIn('new attributes 8 > 7',r.stdout)

    def test_validator_rejects_too_few_variants(self):
        items=[{'id':f'C{i+1:02d}','position':f'定位{i%8}',
               'variants':['a','b'] if i else ['a'],'new_attributes':[]} for i in range(20)]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'items.json'; p.write_text(json.dumps({'items':items}),encoding='utf8')
            r=run('validate','--spec',str(EX/'settlement_cards.json'),'--candidates',str(p))
        self.assertEqual(r.returncode,1)
        self.assertIn('variants below minimum',r.stdout)

    def test_unbounded_attributes_not_implicitly_zero(self):
        items=[{'id':f'id{i}','position':f'方向{i}','new_attributes':[f'p{i}'],
                'variants':[]} for i in range(4)]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'items.json'; p.write_text(json.dumps({'items':items}),encoding='utf8')
            r=run('validate','--spec',str(EX/'ux_redesign.json'),'--candidates',str(p))
        self.assertEqual(r.returncode,0,r.stderr)

    def test_invalid_spec_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text('{"request":"hi","deliverables":{"items":0}}',encoding='utf8')
            r=run('new','--spec',str(p))
        self.assertNotEqual(r.returncode,0)
        self.assertIn('items must be',r.stderr)

    def test_new_seed_and_mutation(self):
        spec=str(EX/'ux_redesign.json')
        a=run('new','--spec',spec,'--format','json')
        self.assertEqual(a.returncode,0,a.stderr)
        seed=json.loads(a.stdout)['seed']
        self.assertEqual(len(seed),16)
        b=run('mutate','--seed',seed,'--spec',spec,'--edits','2','--format','json')
        self.assertEqual(b.returncode,0,b.stderr)
        obj=json.loads(b.stdout)
        self.assertEqual(len(obj['mutation_positions_1_based']),2)
        self.assertNotEqual(obj['seed'],seed)


if __name__=='__main__':unittest.main()
