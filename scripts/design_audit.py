#!/usr/bin/env python3
"""Stage-aware, evidence-preserving structural audit for general design work.

This tool validates *declared* reasoning, traceability and verification status.
It does not judge design quality, prove user acceptance, or execute prototypes.
Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from seed_ideation import checksum, load_spec, VERSION

STAGES = ('frame', 'explore', 'decide', 'specify', 'verify', 'handoff')
MODES = ('quick', 'standard', 'rigorous')


def nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def array(value: Any) -> list:
    return value if isinstance(value, list) else []


def ids(values: list) -> set[str]:
    return {x['id'] for x in values if isinstance(x, dict) and nonblank(x.get('id'))}


def requirement_ids(spec: dict) -> list[str]:
    return [str(r.get('id') or f'REQ-{i+1}') for i, r in enumerate(spec.get('requirements', []))
            if r.get('level', 'must') == 'must']


def audit(spec: dict, work: dict, through: str = 'handoff') -> dict:
    """Validate a reusable design record stage by stage, stopping at `through`."""
    if through not in STAGES:
        raise ValueError(f'unknown stage: {through}')
    if not isinstance(work, dict):
        raise ValueError('workbook must be a JSON object')

    profile = spec.get('design', {})
    mode = profile.get('mode', 'standard')
    strategy = profile.get('strategy', 'compare')
    if mode not in MODES or strategy not in ('direct', 'compare'):
        raise ValueError('design.mode must be quick/standard/rigorous and design.strategy direct/compare')
    errors: list[str] = []
    warnings: list[str] = []
    staged: dict[str, bool] = {}

    def check(ok: bool, code: str) -> None:
        if not ok:
            errors.append(code)

    def note(ok: bool, code: str) -> None:
        if not ok:
            warnings.append(code)

    brief = work.get('brief', {})
    discovery = work.get('discovery', {})
    concepts = array(work.get('concepts'))
    decision = work.get('decision', {})
    detail = work.get('specification', {})
    verification = work.get('verification', {})
    handoff = work.get('handoff', {})

    need = requirement_ids(spec)
    stop_at = STAGES.index(through)

    if stop_at >= 0:
        check(isinstance(brief, dict), 'frame:brief_missing')
        if not isinstance(brief, dict): brief = {}
        for key in ('problem', 'users', 'outcome'):
            value = brief.get(key)
            check(bool(array(value)) if key == 'users' else nonblank(value), f'frame:missing_{key}')
        criteria = array(brief.get('success_criteria'))
        check(bool(criteria), 'frame:missing_success_criteria')
        for i, criterion in enumerate(criteria):
            check(isinstance(criterion, dict) and
                  all(nonblank(criterion.get(k)) for k in ('id', 'criterion', 'method')),
                  f'frame:invalid_success_criterion:{i}')
        scope = brief.get('scope', {})
        check(isinstance(scope, dict) and bool(array(scope.get('in'))), 'frame:missing_in_scope')
        if mode != 'quick':
            note(bool(array(scope.get('out'))), 'frame:undefined_out_of_scope')
        assumptions = array(brief.get('assumptions'))
        for a in assumptions:
            if not isinstance(a, dict) or not nonblank(a.get('text')) or a.get('status') not in ('unverified', 'validated', 'rejected'):
                errors.append('frame:invalid_assumption')
            elif a['status'] == 'unverified':
                note(nonblank(a.get('validation')), f'frame:assumption_without_validation:{a.get("id", "?")}')
        staged['frame'] = not any(x.startswith('frame:') for x in errors)

    if stop_at >= 1:
        check(isinstance(discovery, dict), 'explore:missing_discovery')
        if not isinstance(discovery, dict): discovery = {}
        findings = array(discovery.get('findings'))
        if not findings:
            check(nonblank(discovery.get('not_needed_reason')), 'explore:research_missing_without_rationale')
        for i, finding in enumerate(findings):
            check(isinstance(finding, dict) and
                  all(nonblank(finding.get(k)) for k in ('id', 'claim', 'source', 'evidence')) and
                  finding.get('confidence') in ('high', 'medium', 'low'), f'explore:invalid_finding:{i}')
            if isinstance(finding, dict) and finding.get('source') == 'assumption':
                note(True if finding.get('confidence') == 'low' else False,
                     f'explore:assumption_overconfident:{finding.get("id", i)}')
        minimum = 1 if mode == 'quick' or strategy == 'direct' else 2
        check(len(concepts) >= minimum, f'explore:insufficient_concepts:need_{minimum}')
        seen: set[str] = set()
        for i, concept in enumerate(concepts):
            if not isinstance(concept, dict):
                errors.append(f'explore:invalid_concept:{i}')
                continue
            cid = concept.get('id')
            check(nonblank(cid), f'explore:missing_concept_id:{i}')
            if nonblank(cid) and cid in seen: errors.append(f'explore:duplicate_concept_id:{cid}')
            if nonblank(cid): seen.add(cid)
            check(nonblank(concept.get('summary')), f'explore:missing_summary:{cid}')
            check(nonblank(concept.get('principle')), f'explore:missing_principle:{cid}')
            tradeoffs = concept.get('tradeoffs', {})
            check(isinstance(tradeoffs, dict) and bool(array(tradeoffs.get('benefits'))) and
                  bool(array(tradeoffs.get('costs'))), f'explore:missing_tradeoffs:{cid}')
            checks = concept.get('requirement_checks', {})
            for rid in need:
                row = checks.get(rid) if isinstance(checks, dict) else None
                check(isinstance(row, dict) and row.get('status') in ('pass', 'fail', 'uncertain') and
                      nonblank(row.get('evidence')), f'explore:unreviewed_requirement:{cid}:{rid}')
        if mode == 'rigorous':
            note(bool(findings), 'explore:rigorous_mode_no_findings')
        staged['explore'] = not any(x.startswith('explore:') for x in errors)

    if stop_at >= 2:
        if not isinstance(decision, dict): decision = {}
        choices = array(decision.get('selected'))
        check(bool(choices), 'decide:missing_selection')
        check(nonblank(decision.get('rationale')), 'decide:missing_rationale')
        valid_concepts = ids(concepts)
        for cid in choices:
            check(cid in valid_concepts, f'decide:unknown_concept:{cid}')
            option = next((x for x in concepts if isinstance(x, dict) and x.get('id') == cid), {})
            for rid in need:
                row = option.get('requirement_checks', {}).get(rid, {}) if isinstance(option.get('requirement_checks'), dict) else {}
                check(row.get('status') == 'pass' and nonblank(row.get('evidence')),
                      f'decide:selected_noncompliant:{cid}:{rid}')
        check(decision.get('authority') in ('agent_proposal', 'user_approved'), 'decide:missing_authority')
        if decision.get('authority') == 'user_approved':
            check(nonblank(decision.get('approval_evidence')), 'decide:unsubstantiated_user_approval')
        if len(concepts) > 1:
            rejected = array(decision.get('rejected'))
            rejected_ids = {x.get('id') for x in rejected if isinstance(x, dict) and nonblank(x.get('reason'))}
            check((valid_concepts - set(choices)) <= rejected_ids, 'decide:missing_alternative_reasons')
        staged['decide'] = not any(x.startswith('decide:') for x in errors)

    artifacts = array(detail.get('artifacts')) if isinstance(detail, dict) else []
    acceptances: dict[str, str] = {}
    if stop_at >= 3:
        check(bool(artifacts), 'specify:missing_artifacts')
        known_ids = ids(artifacts)
        check(len(known_ids) == len(artifacts), 'specify:missing_or_duplicate_artifact_id')
        covered = set()
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                errors.append('specify:invalid_artifact')
                continue
            aid = artifact.get('id', '?')
            check(nonblank(artifact.get('name')) and nonblank(artifact.get('type')), f'specify:missing_artifact_metadata:{aid}')
            check(nonblank(artifact.get('content')) or nonblank(artifact.get('location')), f'specify:missing_artifact_content:{aid}')
            traced = array(artifact.get('requirements'))
            for rid in traced:
                check(rid in need or rid in [r.get('id') for r in spec.get('requirements', [])],
                      f'specify:unknown_requirement:{aid}:{rid}')
            covered.update(traced)
            accepts = array(artifact.get('acceptance'))
            check(bool(accepts), f'specify:missing_acceptance:{aid}')
            for row in accepts:
                if not isinstance(row, dict) or not all(nonblank(row.get(k)) for k in ('id', 'criterion', 'method')):
                    errors.append(f'specify:invalid_acceptance:{aid}')
                    continue
                if row['id'] in acceptances: errors.append(f'specify:duplicate_acceptance_id:{row["id"]}')
                acceptances[row['id']] = aid
            note(bool(array(artifact.get('edge_cases'))) or nonblank(artifact.get('edge_cases_not_applicable')),
                 f'specify:unexamined_edge_cases:{aid}')
        for rid in need: check(rid in covered, f'specify:untraced_must:{rid}')
        staged['specify'] = not any(x.startswith('specify:') for x in errors)

    verification_status = 'not_assessed'
    if stop_at >= 4:
        if not isinstance(verification, dict): verification = {}
        results = array(verification.get('results'))
        observed: dict[str, str] = {}
        for row in results:
            if not isinstance(row, dict) or row.get('acceptance_id') not in acceptances:
                errors.append('verify:unknown_acceptance_id')
                continue
            criterion = row['acceptance_id']
            check(criterion not in observed, f'verify:duplicate_result:{criterion}')
            status = row.get('status')
            check(status in ('pass', 'fail', 'not_run', 'blocked'), f'verify:invalid_status:{criterion}')
            check(nonblank(row.get('method')), f'verify:missing_method:{criterion}')
            if status == 'pass': check(nonblank(row.get('evidence')), f'verify:pass_without_evidence:{criterion}')
            if status in ('fail', 'not_run', 'blocked'):
                check(nonblank(row.get('issue')), f'verify:unexplained_nonpass:{criterion}')
            observed[criterion] = status
        for aid in acceptances:
            check(aid in observed, f'verify:unreported_acceptance:{aid}')
        if acceptances and all(observed.get(k) == 'pass' for k in acceptances):
            verification_status = 'declared_pass_review_required'
        elif any(x == 'fail' for x in observed.values()):
            verification_status = 'failed'
        else:
            verification_status = 'incomplete'
        staged['verify'] = not any(x.startswith('verify:') for x in errors)

    if stop_at >= 5:
        if not isinstance(handoff, dict): handoff = {}
        check(handoff.get('status') in ('draft', 'review_ready', 'validated'), 'handoff:missing_status')
        check(nonblank(handoff.get('summary')), 'handoff:missing_summary')
        supplied = array(handoff.get('deliverables'))
        covered = {x.get('artifact_id') for x in supplied if isinstance(x, dict) and nonblank(x.get('location'))}
        for aid in ids(artifacts): check(aid in covered, f'handoff:missing_delivery:{aid}')
        if handoff.get('status') == 'validated':
            check(verification_status == 'declared_pass_review_required', 'handoff:validation_not_supported')
        if verification_status != 'declared_pass_review_required':
            check(bool(array(handoff.get('remaining_work'))) or nonblank(handoff.get('no_further_work_reason')),
                  'handoff:unresolved_work_not_declared')
        staged['handoff'] = not any(x.startswith('handoff:') for x in errors)

    return {
        'tool': 'seeded-ideation-design-audit', 'version': VERSION,
        'spec_fingerprint': checksum(spec), 'through': through, 'mode': mode,
        'structure_pass': not errors, 'stage_pass': staged,
        'errors': errors, 'warnings': warnings,
        'verification_status': verification_status,
        'semantic_review_required': True,
        'notes': 'Checks declared coverage and evidence shape, not quality, originality, factual correctness, test execution, or user approval.'
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec', required=True)
    p.add_argument('--workbook', required=True)
    p.add_argument('--through', choices=STAGES, default='handoff')
    p.add_argument('--output')
    a = p.parse_args()
    try:
        spec = load_spec(a.spec)
        workbook = json.loads(Path(a.workbook).read_text(encoding='utf-8'))
        report = audit(spec, workbook, a.through)
        result = json.dumps(report, indent=2, ensure_ascii=False) + '\n'
        if a.output: Path(a.output).write_text(result, encoding='utf-8')
        else: print(result, end='')
        return 0 if report['structure_pass'] else 1
    except (ValueError, OSError, json.JSONDecodeError) as err:
        p.error(str(err))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
