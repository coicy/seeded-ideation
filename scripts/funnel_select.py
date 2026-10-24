#!/usr/bin/env python3
"""Requirement-first multi-stage selection from AI-written candidate pools.

This script is a transparent mechanical gate and heuristic reranker. The AI/user
must still evaluate natural-language requirements and supply evidence; scores and
tags are claims, NOT verified facts or objective creative-quality measures.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any
from seed_ideation import checksum, validate_spec, VERSION, load_plan, fingerprint

WEIGHTS={'fit':0.40, 'usefulness':0.25, 'feasibility':0.20, 'novelty':0.15}


def must_ids(spec:dict[str,Any])->list[str]:
    return [str(r.get('id') or f'MUST-{i+1}') for i,r in enumerate(spec.get('requirements',[]))
            if r.get('level','must')=='must']


def assess(item:Any,required_ids:list[str])->list[str]:
    """Fail closed on must rules *before* requiring detailed ranking fields.

    Rejected sketches need not be polished or numerically scored.
    """
    reasons=[]
    if not isinstance(item,dict):return ['not_object']
    if not isinstance(item.get('id'),str) or not item['id'].strip():reasons.append('missing_id')
    if not isinstance(item.get('concept'),str) or not item['concept'].strip():reasons.append('missing_concept')
    checks=item.get('requirement_checks',{})
    for rid in required_ids:
        c=checks.get(rid) if isinstance(checks,dict) else None
        if not isinstance(c,dict):reasons.append(f'not_reviewed:{rid}');continue
        status=c.get('status')
        if status not in ('pass','fail','uncertain'):
            reasons.append(f'not_reviewed:{rid}')
        elif status!='pass':reasons.append(f'{status}:{rid}')
        elif not isinstance(c.get('evidence'),str) or not c['evidence'].strip():
            reasons.append(f'no_evidence:{rid}')
    if reasons:return reasons  # Stop before scoring an ineligible idea.
    if not isinstance(item.get('position'),str) or not item['position'].strip():reasons.append('missing_position')
    if not isinstance(item.get('mechanism_signature'),str) or not item['mechanism_signature'].strip():reasons.append('missing_mechanism_signature')
    mtags=item.get('mechanism_tags')
    if not isinstance(mtags,list) or not mtags or any(not isinstance(v,str) or not v.strip() for v in mtags):
        reasons.append('missing_mechanism_tags')
    a=item.get('new_attributes',[])
    if not isinstance(a,list) or any(not isinstance(v,str) or not v.strip() for v in a):
        reasons.append('invalid_new_attributes')
    scores=item.get('scores')
    if not isinstance(scores,dict):reasons.append('missing_scores')
    else:
        for key in WEIGHTS:
            v=scores.get(key)
            if isinstance(v,bool) or not isinstance(v,(float,int)) or not 0<=v<=5:
                reasons.append(f'invalid_score:{key}')
    return reasons


def quality(item:dict[str,Any])->float:
    return sum(WEIGHTS[k]*item['scores'][k] for k in WEIGHTS)


def tags(item:dict[str,Any])->set[str]:
    return set(s.strip().lower() for s in item['mechanism_tags'])


def jaccard(a:set[str],b:set[str])->float:
    return len(a&b)/len(a|b) if (a or b) else 1


def pick(items:list[dict[str,Any]],n:int,*,
         attr_limit:int|None=None, min_positions:int=0)->list[dict[str,Any]]:
    selected=[]; positions=set(); attributes=set()
    remaining=list(items)
    while remaining and len(selected)<n:
        candidates=[]
        for it in remaining:
            next_attrs=attributes | set(it.get('new_attributes',[]))
            if attr_limit is not None and len(next_attrs)>attr_limit:continue
            next_positions=positions|{it['position']}
            left=n-(len(selected)+1)
            if len(next_positions)+left<min_positions:continue
            similarity=max((jaccard(tags(it),tags(old)) for old in selected),default=0)
            position_duplicate = 1 if it['position'] in positions else 0
            # No novelty-only optimization: useful, relevant and feasible candidates dominate.
            score=quality(it) - 0.70*similarity - 0.22*position_duplicate
            candidates.append((score,quality(it),it['id'],it))
        if not candidates:break
        choice=sorted(candidates,key=lambda x:(-x[0],-x[1],x[2]))[0][3]
        selected.append(choice);positions.add(choice['position'])
        attributes.update(choice.get('new_attributes',[]));remaining.remove(choice)
    return selected


def choose_final_beam(items:list[dict[str,Any]],n:int,*,
                      attr_limit:int|None=None,min_positions:int=0,
                      beam_width:int=256)->list[dict[str,Any]]:
    """Search sets rather than greedily locking in a globally costly early attribute."""
    # Sort by quality, then stable ID; only extend to higher indices to avoid permutations.
    items=sorted(items,key=lambda x:(-quality(x),x['id']))
    # (chosen_indices, used_attr, distinct_positions, score)
    states=[((),frozenset(),frozenset(),0.0)]
    best_partial=()
    for depth in range(n):
        generated=[]
        for indices,used,positions,score in states:
            for i in range(indices[-1]+1 if indices else 0,len(items)):
                if len(items)-(i+1)<n-(depth+1):continue
                item=items[i]
                attrs=used|frozenset(item.get('new_attributes',[]))
                if attr_limit is not None and len(attrs)>attr_limit:continue
                positions_next=positions|{item['position']}
                if len(positions_next)+n-(depth+1)<min_positions:continue
                # Avoid choosing a candidate if no remaining positions can make the quota.
                future_positions={it['position'] for it in items[i+1:]}
                if len(positions_next|future_positions)<min_positions:continue
                previous=[items[j] for j in indices]
                similarity=max((jaccard(tags(item),tags(x)) for x in previous),default=0.0)
                repeated=1 if item['position'] in positions else 0
                value=score+quality(item)-0.70*similarity-0.22*repeated
                generated.append((indices+(i,),attrs,positions_next,value))
        if not generated:break
        # Deterministic and bounded beam; it is not a proof of global optimum.
        generated.sort(key=lambda x:(-x[3],tuple(items[i]['id'] for i in x[0])))
        states=generated[:beam_width]
        best_partial=states[0][0]
    completed=[state for state in states if len(state[0])==n
               and len(state[2])>=min_positions]
    if completed:
        best=max(completed,key=lambda x:(x[3],tuple(items[i]['id'] for i in x[0])))
        return [items[i] for i in best[0]]
    return [items[i] for i in best_partial]


def audit_seed_lineage(entries:list[Any],plan:dict[str,Any])->dict[str,Any]:
    """Fail closed when candidate/seed identity is not a 1:1 mapping.

    This verifies declarations and manifest links, not whether an agent actually
    used its assigned seed to compose the idea.
    """
    expected={p['number']:p for p in plan['paths']}
    seen_numbers=set();seen_seeds=set()
    for index,item in enumerate(entries,1):
        if not isinstance(item,dict):raise ValueError(f'item {index} lacks seed lineage object')
        number=item.get('path_number');seed=item.get('seed')
        if type(number) is not int or number not in expected:
            raise ValueError(f'item {index} lacks valid path_number from plan')
        if not isinstance(seed,str) or seed!=expected[number]['seed']:
            raise ValueError(f'item {index} seed mismatch for path {number}')
        if item.get('seed_fingerprint')!=fingerprint(seed):
            raise ValueError(f'item {index} seed fingerprint mismatch')
        if number in seen_numbers or seed in seen_seeds:
            raise ValueError(f'duplicate candidate seed/path for path {number}')
        seen_numbers.add(number);seen_seeds.add(seed)
    return {'status':'declared_path_linkage_checked',
            'manifest_fingerprint':plan['manifest_fingerprint'],
            'candidate_paths':len(seen_numbers),
            'missing_paths':len(expected)-len(seen_numbers),
            'semantic_seed_usage_verified':False}


def funnel(spec:dict[str,Any],data:dict[str,Any],
           plan:dict[str,Any]|None=None)->dict[str,Any]:
    validate_spec(spec)
    entries=data.get('items')
    if not isinstance(entries,list):raise ValueError('pool document must contain items array')
    lineage=audit_seed_lineage(entries,plan) if plan is not None else None
    goal=spec.get('deliverables',{}).get('items',4)
    ideation=spec.get('ideation',{})
    target_pool=ideation.get('pool_size',min(256,goal*16))
    if ideation.get('require_full_pool',False) and len(entries)<target_pool:
        return {'selection_complete':False, 'reason':'incomplete_pool',
                'observed_pool':len(entries),'required_pool':target_pool,'finalists':[],
                'seed_lineage':lineage}
    required_ids=must_ids(spec)
    rejected=[];eligible=[];seen_id=set()
    for index,item in enumerate(entries):
        reasons=assess(item,required_ids)
        if isinstance(item,dict) and isinstance(item.get('id'),str):
            if item['id'] in seen_id:reasons.append('duplicate_id')
            seen_id.add(item['id'])
        if reasons:rejected.append({'index':index+1,'id':item.get('id') if isinstance(item,dict) else None,'reasons':reasons})
        else:eligible.append(item)
    # Deduplication is deterministic but depends on agent-defined mechanism signatures.
    signatures={}; duplicates=[]
    for it in sorted(eligible,key=lambda x:(-quality(x),x['id'])):
        sig=it['mechanism_signature'].strip().lower()
        if sig in signatures:
            duplicates.append({'id':it['id'],'duplicate_of':signatures[sig]['id'],'signature':sig})
        else:signatures[sig]=it
    survivors=list(signatures.values())
    # Coarse-to-fine stages; 256 -> 64 -> 16 -> 4 when goal is 4.
    stages=[];current=survivors
    sizes=[]
    for n in (goal*16,goal*4,goal):
        n=min(n,len(current))
        if n not in sizes:sizes.append(n)
    # Sizes must never increase even when a severe rejection reduces the pool.
    positions_needed=spec.get('deliverables',{}).get('min_distinct_positions',0)
    attr_limit=spec.get('deliverables',{}).get('max_new_attributes')
    for n in sizes:
        final_stage = n==goal
        current=(choose_final_beam(current,n,attr_limit=attr_limit,
                      min_positions=positions_needed) if final_stage else pick(current,n))
        stages.append({'remaining':len(current),'requested':n,
                       'ids':[x['id'] for x in current], 'phase':'final' if final_stage else 'shortlist'})
    finalists=current[:goal]
    positions=set(x['position'] for x in finalists)
    attrs=set(a for x in finalists for a in x.get('new_attributes',[]))
    pass_all=(len(finalists)==goal and len(positions)>=positions_needed
              and (attr_limit is None or len(attrs)<=attr_limit))
    reason= 'complete' if pass_all else 'insufficient_eligible_or_diverse_candidates'
    return {'tool':'seeded-ideation','version':VERSION,'spec_fingerprint':checksum(spec),
            'selection_complete':pass_all,'reason':reason,
            'observed_pool':len(entries),'required_pool':target_pool,
            'seed_lineage':lineage,'eligible_before_dedup':len(eligible),'rejected':len(rejected),
            'rejection_counts':dict(Counter(reason for row in rejected for reason in row['reasons'])),
            'rejection_samples':rejected[:20],
            'deduplicated':len(duplicates),'duplicate_samples':duplicates[:20],
            'survivors':len(survivors),'stages':stages,
            'finalists':[{'id':x['id'],'concept':x['concept'],'position':x['position'],
                          'quality_5':round(quality(x),3),'mechanism_tags':x['mechanism_tags'],
                          'new_attributes':x.get('new_attributes',[])} for x in finalists],
            'declared_distinct_positions':len(positions),'selected_new_attributes':sorted(attrs),
            'mandatory_followup':'Expand final candidates and validate all full-length requirements/variants; declared compliance and scores are not independently verified.'}


def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',required=True)
    p.add_argument('--candidates',required=True,help='JSON object {"items": [...]}; short idea evaluations')
    p.add_argument('--output',help='optional report path')
    p.add_argument('--plan',help='v1.6 seed manifest: enforce one seed per candidate path')
    args=p.parse_args()
    try:
        spec=validate_spec(json.loads(Path(args.spec).read_text(encoding='utf8')))
        plan=load_plan(args.plan,spec) if args.plan else None
        result=funnel(spec,json.loads(Path(args.candidates).read_text(encoding='utf8')),plan=plan)
        payload=json.dumps(result,ensure_ascii=False,indent=2)
        if args.output:Path(args.output).write_text(payload+'\n',encoding='utf8')
        else:print(payload)
        return 0 if result['selection_complete'] else 1
    except (ValueError,OSError,json.JSONDecodeError) as err:
        p.error(str(err))
    return 2

if __name__=='__main__':sys.exit(main())
