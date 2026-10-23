#!/usr/bin/env python3
"""Audit unmet user-information needs before expensive seeded ideation.

This is a *structured elicitation aid*, not a natural-language understanding engine.
The Agent supplies evidence-backed statuses after reviewing the current request and
available context. Domain question banks are suggestions, never user requirements.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any

BANK_DIR=Path(__file__).resolve().parents[1]/'references'/'question_banks'
STATUSES={'confirmed','inferred','unknown','delegated','not_applicable'}

def _is_str(value:Any)->bool:
    return isinstance(value,str) and bool(value.strip())

def load_bank(domain:str)->list[dict[str,Any]]:
    generic=json.loads((BANK_DIR/'generic.json').read_text(encoding='utf8'))['slots']
    other=[] if domain=='generic' else json.loads((BANK_DIR/f'{domain}.json').read_text(encoding='utf8'))['slots']
    keys=[x['id'] for x in [*generic,*other]]
    if len(keys)!=len(set(keys)):raise ValueError('duplicate question ids')
    return [*generic,*other]

def audit(spec:dict[str,Any],domain:str|None=None,max_questions:int=1)->dict[str,Any]:
    if not isinstance(spec,dict) or not _is_str(spec.get('request')):raise ValueError('nonempty request is required')
    if not 1<=max_questions<=5:raise ValueError('max_questions must be 1..5')
    config=spec.get('elicitation',{})
    if not isinstance(config,dict):raise ValueError('elicitation must be an object')
    d=domain or config.get('domain','generic')
    bank=load_bank(d)
    facts=config.get('facts',{})
    if not isinstance(facts,dict):raise ValueError('elicitation.facts must be an object')
    unknown=set(facts)-{x['id'] for x in bank}
    if unknown:raise ValueError('unknown elicitation slots: '+', '.join(sorted(unknown)))
    relevance=config.get('relevance',{})
    if not isinstance(relevance,dict):raise ValueError('elicitation.relevance must be an object')
    if set(relevance)-{x['id'] for x in bank}:
        raise ValueError('unknown elicitation relevance key')
    rows=[];pending=[];warning=[]
    for slot in bank:
        sid=slot['id']
        importance=slot['importance']
        relevant=relevance.get(sid,'default')
        if relevant not in {'default','high','low','irrelevant'}:
            raise ValueError('relevance values: default/high/low/irrelevant')
        fact=facts.get(sid,{'status':'unknown'})
        if not isinstance(fact,dict):raise ValueError(f'elicitation.facts.{sid} must be object')
        status=fact.get('status','unknown')
        if status not in STATUSES:raise ValueError(f'unknown status for {sid}: {status}')
        if status in {'confirmed','inferred','delegated'}:
            if not _is_str(fact.get('value')) or not _is_str(fact.get('evidence')):
                raise ValueError(f'{sid} {status} requires value + evidence')
            if status=='delegated' and fact.get('source')!='user':
                raise ValueError(f'{sid} delegated must cite explicit user delegation')
            if status=='confirmed' and fact.get('source') not in ('user','reference'):
                raise ValueError(f'{sid} confirmed source must be user/reference')
        if status=='not_applicable' and not _is_str(fact.get('evidence')):
            raise ValueError(f'{sid} not_applicable requires evidence')
        if relevant=='irrelevant' or status=='not_applicable':
            classification='skipped'
        elif status in ('confirmed','delegated'):
            classification='grounded'
        elif status=='inferred':
            # Inferences are not silently promoted to user authorization.
            classification='needs_confirmation' if importance=='critical' or relevant=='high' else 'provisional'
        elif importance=='critical' or relevant=='high':
            classification='needs_clarification'
        else:
            classification='non_blocking_unknown'
        row={'id':sid,'importance':importance,'status':status,
             'classification':classification,'question':slot['question'],
             'why_it_matters':slot['why_it_matters']}
        rows.append(row)
        if classification in ('needs_confirmation','needs_clarification'):
            pending.append(row)
        elif classification in ('provisional','non_blocking_unknown'):
            warning.append({'id':sid,'status':classification})
    rank={'critical':0,'high':1,'optional':2}
    pending.sort(key=lambda x:(rank[x['importance']],0 if x['classification']=='needs_clarification' else 1))
    selected=pending[:max_questions]
    return {'tool':'seeded-ideation','version':'1.4.0','domain':d,
            'ready_for_ideation':not pending,'status':'ready' if not pending else 'needs_clarification',
            'questions_to_ask_now':selected,'remaining_questions':len(pending)-len(selected),
            'pending_total':len(pending),'non_blocking_unknowns':warning,
            'slot_audit':rows,
            'instructions':('Ask at most the listed high-impact question(s) conversationally, then update the brief with the user answer and rerun.'
                if pending else 'Proceed; state consequential provisional assumptions explicitly. Do not claim the script proved semantic completeness.'),
            'limitation':'Agent-authored relevance and evidence; no semantic verification of user text or reference truth.'}

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--spec',required=True)
    ap.add_argument('--domain',choices=['generic','cards','ui','software','writing'],default=None)
    ap.add_argument('--max-questions',type=int,default=1)
    ap.add_argument('--enforce',action='store_true',help='nonzero exit when clarification is required')
    ap.add_argument('--format',choices=['json','text'],default='json')
    a=ap.parse_args()
    try:
        spec=json.loads(Path(a.spec).read_text(encoding='utf8'))
        result=audit(spec,a.domain,a.max_questions)
        if a.format=='json':print(json.dumps(result,ensure_ascii=False,indent=2))
        else:
            print(f"readiness={result['status']}, pending={result['pending_total']}")
            for q in result['questions_to_ask_now']:
                print(f"{q['id']}: {q['question']}  ({q['why_it_matters']})")
        return 1 if a.enforce and not result['ready_for_ideation'] else 0
    except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:
        ap.error(str(e))
    return 2

if __name__=='__main__':sys.exit(main())
