import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BRIEF=ROOT/'scripts'/'brief_gate.py'
SEED=ROOT/'scripts'/'seed_ideation.py'
MISSING=ROOT/'examples'/'cards_brief_missing.json'
READY=ROOT/'examples'/'cards_brief_resolved_example.json'

def call(script,*args):
    return subprocess.run([sys.executable,str(script),*args],text=True,capture_output=True)

class ElicitationTests(unittest.TestCase):
    def test_first_question_is_output_ambiguity_not_blanket_questionnaire(self):
        result=call(BRIEF,'--spec',str(MISSING),'--max-questions','1')
        self.assertEqual(result.returncode,0,result.stderr)
        r=json.loads(result.stdout)
        self.assertEqual(r['status'],'needs_clarification')
        self.assertEqual(len(r['questions_to_ask_now']),1)
        self.assertEqual(r['questions_to_ask_now'][0]['id'],'deliverable_interpretation')
        self.assertGreater(r['remaining_questions'],0)

    def test_structured_hypothetical_resolved_brief_ready(self):
        result=call(BRIEF,'--spec',str(READY),'--enforce')
        self.assertEqual(result.returncode,0,result.stderr)
        r=json.loads(result.stdout)
        self.assertTrue(r['ready_for_ideation'])
        self.assertEqual(r['pending_total'],0)
        self.assertGreater(len(r['non_blocking_unknowns']),0)

    def test_plan_fails_closed_with_provided_unresolved_brief(self):
        r=call(SEED,'plan','--spec',str(MISSING),'--require-ready')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('clarification required',r.stderr)

    def test_plan_allowed_after_brief_confirmed(self):
        r=call(SEED,'plan','--spec',str(READY),'--require-ready','--pool-size','256')
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads(r.stdout)['planned_initial_candidates'],256)

    def test_inferred_critical_is_not_user_confirmation(self):
        spec=json.loads(READY.read_text(encoding='utf8'))
        spec['elicitation']['facts']['deliverable_interpretation']={
          'status':'inferred','value':'我猜是4组每组5张', 'evidence':'agent根据数字推断'}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'spec.json';path.write_text(json.dumps(spec,ensure_ascii=False),encoding='utf8')
            r=call(BRIEF,'--spec',str(path))
        result=json.loads(r.stdout)
        self.assertEqual(result['questions_to_ask_now'][0]['id'],'deliverable_interpretation')
        self.assertEqual(result['questions_to_ask_now'][0]['classification'],'needs_confirmation')

    def test_delegation_requires_explicit_user_evidence(self):
        spec=json.loads(READY.read_text(encoding='utf8'))
        spec['elicitation']['facts']['cards_synergy']={'status':'delegated',
          'value':'由代理自行决定','source':'inferred','evidence':'用户没提所以假定授权'}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'spec.json';path.write_text(json.dumps(spec,ensure_ascii=False),encoding='utf8')
            r=call(BRIEF,'--spec',str(path))
        self.assertNotEqual(r.returncode,0)
        self.assertIn('must cite explicit user delegation',r.stderr)

    def test_domain_neutral_generic(self):
        spec={'request':'构思4个展览主题','elicitation':{'domain':'generic', 'facts':{
          'deliverable_interpretation':{'status':'confirmed','value':'四个完整主题','source':'user','evidence':'用户要求四个主题'},
          'desired_outcome':{'status':'confirmed','value':'激发参与','source':'user','evidence':'用户明确目标参与'},
        }}}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'spec.json';path.write_text(json.dumps(spec,ensure_ascii=False),encoding='utf8')
            r=call(BRIEF,'--spec',str(path))
        a=json.loads(r.stdout)
        self.assertEqual(a['domain'],'generic')
        self.assertTrue(a['ready_for_ideation'])
        self.assertFalse(any('cards_' in row['id'] for row in a['slot_audit']))

    def test_high_relevance_option_questions_without_mandating_all(self):
        spec=json.loads(READY.read_text(encoding='utf8'))
        spec['elicitation']['facts']['cards_variants']={'status':'unknown'}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'spec.json';path.write_text(json.dumps(spec,ensure_ascii=False),encoding='utf8')
            r=call(BRIEF,'--spec',str(path))
        a=json.loads(r.stdout)
        self.assertFalse(a['ready_for_ideation'])
        self.assertEqual(a['questions_to_ask_now'][0]['id'],'cards_variants')

    def test_missing_evidence_rejected(self):
        spec=json.loads(READY.read_text(encoding='utf8'))
        del spec['elicitation']['facts']['desired_outcome']['evidence']
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'spec.json';path.write_text(json.dumps(spec,ensure_ascii=False),encoding='utf8')
            r=call(BRIEF,'--spec',str(path))
        self.assertNotEqual(r.returncode,0)
        self.assertIn('requires value + evidence',r.stderr)

if __name__=='__main__':unittest.main()
