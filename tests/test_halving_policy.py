"""Regression for minimum 64 independent seeds and an exact 50% elimination each round."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from seed_ideation import make_plan, minimum_pool_size, halving_rounds, validate_spec, load_plan
from funnel_select import funnel


def item(i,path,*,status='pass',signature=None):
    return {
        'id':f'idea-{i:03}', 'concept':f'Distinct proposed mechanism {i}',
        'path_number':path['number'], 'seed':path['seed'], 'seed_fingerprint':path['seed_fingerprint'],
        'position':f'position-{i%16}', 'mechanism_signature':signature or f'mechanism-{i}',
        'mechanism_tags':[f'focus-{i%19}', f'behavior-{i%13}'], 'new_attributes':[],
        'requirement_checks':{'MUST-1':{'status':status,'evidence':'explicitly checked requirement'}},
        'scores':{'fit':4+(i%3)/5,'usefulness':4,'feasibility':4,'novelty':3.5}
    }


def spec(k=4):
    return {'request':'Design alternatives from a diverse independent seed pool',
            'requirements':[{'text':'Must serve the stated user need','level':'must','source':'user'}],
            'deliverables':{'items':k,'min_distinct_positions':min(k,4)}}


class HalfPolicy(unittest.TestCase):
    def test_minimums_and_exact_schedules(self):
        expectations={1:(64,[32,16,8,4,2,1]), 3:(96,[48,24,12,6,3]),
                      4:(64,[32,16,8,4]), 5:(80,[40,20,10,5]),
                      20:(80,[40,20]), 64:(128,[64]), 200:(400,[200])}
        for target,(size,rounds) in expectations.items():
            with self.subTest(target=target):
                self.assertEqual(minimum_pool_size(target),size)
                plan=make_plan(spec(target))
                self.assertEqual(plan['seed_count'],size)
                self.assertEqual(plan['halving_rounds'],rounds)
                self.assertEqual(len({p['seed'] for p in plan['paths']}),size)
                self.assertTrue(plan['require_full_pool'])

    def test_reject_below_floor_and_non_exact_halves(self):
        for count,target in [(4,4),(32,4),(63,4),(64,3),(70,4),(256,3),(4096,3)]:
            with self.subTest(count=count,target=target):
                with self.assertRaises(ValueError): halving_rounds(count,target)
        self.assertEqual(halving_rounds(256,4),[128,64,32,16,8,4])
        self.assertEqual(halving_rounds(320,20),[160,80,40,20])

    def test_spec_pool_is_enforced(self):
        for count in (16,40,72):
            draft=spec(4);draft['ideation']={'pool_size':count}
            with self.assertRaises(ValueError): validate_spec(draft)
        draft=spec(3);draft['ideation']={'pool_size':96}
        self.assertIs(validate_spec(draft),draft)

    def test_new_defaults_to_64_and_rejects_smaller_count(self):
        def cli(*args):
            return subprocess.run([sys.executable,str(ROOT/'scripts/seed_ideation.py'),
                                   *args],capture_output=True,text=True)
        result=cli('new','--request','Provide four design ideas','--format','json')
        self.assertEqual(result.returncode,0,result.stderr)
        j=json.loads(result.stdout)
        self.assertEqual(j['count'],64)
        self.assertEqual(j['halving_rounds'],[32,16,8,4])
        self.assertEqual(len({c['seed'] for c in j['candidates']}),64)
        bad=cli('new','--request','Provide four ideas','--count','32')
        self.assertNotEqual(bad.returncode,0)
        self.assertIn('at least 64',bad.stderr)
        single=cli('replay','--request','Re-check one prior path',
                   '--seed','K7M28QVAT3XPH6RD','--format','json')
        self.assertEqual(single.returncode,0,single.stderr)
        self.assertEqual(json.loads(single.stdout)['count'],1)

    def test_manifest_rejects_halving_schedule_tampering(self):
        draft=spec(4);p=make_plan(draft)
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'plan.json'
            for bad in ([16,8,4],[32,15,8,4],[],[32,16,8,4,4]):
                mutated=json.loads(json.dumps(p))
                mutated['halving_rounds']=bad
                file.write_text(json.dumps(mutated),encoding='utf8')
                with self.assertRaisesRegex(ValueError,'schedule mismatch'):
                    load_plan(str(file),draft)

    def test_exact_halving_64_to_4(self):
        draft=spec(4);p=make_plan(draft)
        pool=[item(i,path) for i,path in enumerate(p['paths'])]
        report=funnel(draft,{'items':pool},p)
        self.assertTrue(report['selection_complete'],report)
        self.assertEqual(report['observed_pool'],64)
        self.assertEqual([x['remaining'] for x in report['stages']],[32,16,8,4])
        self.assertTrue(all(x['exact_half'] for x in report['stages']))
        self.assertEqual(len(report['finalists']),4)

    def test_non_power_of_two_goal_96_to_3(self):
        draft=spec(3);p=make_plan(draft)
        report=funnel(draft,{'items':[item(i,path) for i,path in enumerate(p['paths'])]},p)
        self.assertTrue(report['selection_complete'],report)
        self.assertEqual([x['remaining'] for x in report['stages']],[48,24,12,6,3])

    def test_rejected_and_duplicate_proposals_count_in_first_elimination(self):
        draft=spec(4);p=make_plan(draft)
        pool=[item(i,path) for i,path in enumerate(p['paths'])]
        pool[0]['requirement_checks']['MUST-1']['status']='fail'
        pool[1]['requirement_checks']['MUST-1']['status']='uncertain'
        pool[2]['mechanism_signature']=pool[3]['mechanism_signature']
        result=funnel(draft,{'items':pool},p)
        self.assertTrue(result['selection_complete'],result)
        self.assertEqual(result['rejected'],2)
        self.assertEqual(result['deduplicated'],1)
        self.assertEqual(result['survivors'],61)
        self.assertEqual([s['remaining'] for s in result['stages']],[32,16,8,4])

    def test_not_enough_compliant_for_first_half_fails_closed(self):
        draft=spec(4);p=make_plan(draft)
        pool=[item(i,path,status='fail' if i<35 else 'pass') for i,path in enumerate(p['paths'])]
        report=funnel(draft,{'items':pool},p)
        self.assertFalse(report['selection_complete'])
        self.assertEqual(report['reason'],'insufficient_eligible_for_exact_halving')
        self.assertEqual(report['stages'][0]['requested'],32)
        self.assertEqual(report['stages'][0]['remaining'],29)
        self.assertEqual(report['finalists'],[])

    def test_missing_seed_path_or_no_plan_rejected(self):
        draft=spec(4);p=make_plan(draft)
        pool=[item(i,path) for i,path in enumerate(p['paths'])]
        with self.assertRaisesRegex(ValueError,'requires --plan'):funnel(draft,{'items':pool})
        partial=funnel(draft,{'items':pool[:-1]},p)
        self.assertFalse(partial['selection_complete'])
        self.assertEqual(partial['reason'],'incomplete_pool')
        self.assertEqual(partial['seed_lineage']['missing_paths'],1)


if __name__=='__main__':unittest.main()
