"""Cross-domain workflow controls and honest handoff checks."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from design_audit import audit
from seed_ideation import load_spec


def fixtures(name='general_design'):
    spec = load_spec(str(ROOT / 'examples' / (name + '_spec.json')))
    work = json.loads((ROOT / 'examples' / (name + '_workbook.json')).read_text(encoding='utf-8'))
    return spec, work


class DesignWorkflowAuditTests(unittest.TestCase):
    def test_standard_compare_handoff_draft_is_allowed_without_fake_tests(self):
        spec, work = fixtures()
        report = audit(spec, work)
        self.assertTrue(report['structure_pass'], report['errors'])
        self.assertEqual(report['verification_status'], 'incomplete')
        self.assertTrue(report['semantic_review_required'])
        self.assertEqual(len(report['stage_pass']), 6)

    def test_quick_direct_without_research_theater_or_random_pool(self):
        spec, work = fixtures('quick_design')
        report = audit(spec, work)
        self.assertTrue(report['structure_pass'], report['errors'])
        self.assertEqual(len(work['concepts']), 1)
        self.assertFalse('ideation' in spec)

    def test_early_stage_only_needs_existing_material(self):
        spec, work = fixtures()
        report = audit(spec, {'brief': work['brief']}, 'frame')
        self.assertTrue(report['structure_pass'], report['errors'])
        self.assertEqual(set(report['stage_pass']), {'frame'})

    def test_missing_goal_blocks_frame(self):
        spec, work = fixtures()
        work['brief']['outcome'] = ''
        result = audit(spec, work, 'frame')
        self.assertFalse(result['structure_pass'])
        self.assertIn('frame:missing_outcome', result['errors'])

    def test_two_options_and_rejection_reason_needed_for_compare(self):
        spec, work = fixtures()
        work['concepts'] = work['concepts'][:1]
        self.assertFalse(audit(spec, work, 'explore')['structure_pass'])
        work['concepts'] = fixtures()[1]['concepts']
        work['decision']['rejected'] = []
        self.assertIn('decide:missing_alternative_reasons', audit(spec, work, 'decide')['errors'])

    def test_selection_must_pass_hard_requirements(self):
        spec, work = fixtures()
        work['concepts'][0]['requirement_checks']['R1']['status'] = 'uncertain'
        self.assertIn('decide:selected_noncompliant:C1:R1', audit(spec, work, 'decide')['errors'])

    def test_fake_user_approval_is_blocked(self):
        spec, work = fixtures()
        work['decision']['authority'] = 'user_approved'
        self.assertIn('decide:unsubstantiated_user_approval', audit(spec, work, 'decide')['errors'])

    def test_untraced_hard_requirement_blocks_specification(self):
        spec, work = fixtures()
        work['specification']['artifacts'][0]['requirements'] = ['R1']
        self.assertIn('specify:untraced_must:R2', audit(spec, work, 'specify')['errors'])

    def test_unrecognized_requirement_link_blocks_specification(self):
        spec, work = fixtures()
        work['specification']['artifacts'][0]['requirements'].append('INVENTED')
        self.assertIn('specify:unknown_requirement:D1:INVENTED', audit(spec, work, 'specify')['errors'])

    def test_repeated_acceptance_id_blocks_specification(self):
        spec, work = fixtures()
        accept = work['specification']['artifacts'][0]['acceptance'][0]
        work['specification']['artifacts'][0]['acceptance'].append(copy.deepcopy(accept))
        self.assertIn('specify:duplicate_acceptance_id:AC1', audit(spec, work, 'specify')['errors'])

    def test_unexecuted_verification_does_not_allow_validated_handoff(self):
        spec, work = fixtures()
        work['handoff']['status'] = 'validated'
        report = audit(spec, work)
        self.assertFalse(report['structure_pass'])
        self.assertIn('handoff:validation_not_supported', report['errors'])

    def test_missing_test_results_are_rejected(self):
        spec, work = fixtures()
        work['verification']['results'] = work['verification']['results'][:1]
        self.assertIn('verify:unreported_acceptance:AC2', audit(spec, work, 'verify')['errors'])

    def test_pass_without_test_evidence_is_rejected(self):
        spec, work = fixtures()
        work['verification']['results'][0].update({'status': 'pass', 'evidence': ''})
        self.assertIn('verify:pass_without_evidence:AC1', audit(spec, work, 'verify')['errors'])

    def test_declared_pass_is_explicitly_not_independent_proof(self):
        spec, work = fixtures()
        for row in work['verification']['results']:
            row['status'] = 'pass'
            row['evidence'] = f"test log for {row['acceptance_id']}"
        work['handoff']['status'] = 'validated'
        work['handoff']['remaining_work'] = []
        report = audit(spec, work)
        self.assertTrue(report['structure_pass'], report['errors'])
        self.assertEqual(report['verification_status'], 'declared_pass_review_required')
        self.assertTrue(report['semantic_review_required'])

    def test_nonpass_requires_issue_explanation(self):
        spec, work = fixtures()
        work['verification']['results'][0].pop('issue')
        self.assertIn('verify:unexplained_nonpass:AC1', audit(spec, work, 'verify')['errors'])

    def test_failures_produce_failed_not_validated(self):
        spec, work = fixtures()
        work['verification']['results'][0].update({'status': 'fail', 'issue': 'Regression case fails'})
        self.assertEqual(audit(spec, work)['verification_status'], 'failed')

    def test_cli_supports_stage_output_and_exit_codes(self):
        spec = ROOT / 'examples' / 'general_design_spec.json'
        work = ROOT / 'examples' / 'general_design_workbook.json'
        r = subprocess.run([sys.executable, str(ROOT/'scripts'/'design_audit.py'),
                            '--spec', str(spec), '--workbook', str(work), '--through', 'specify'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['through'], 'specify')

    def test_bad_strategy_rejected_in_spec(self):
        spec, work = fixtures()
        spec['design']['strategy'] = 'invented'
        with self.assertRaises(ValueError):
            audit(spec, work)


if __name__ == '__main__':
    unittest.main()
