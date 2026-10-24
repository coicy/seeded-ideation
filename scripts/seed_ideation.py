#!/usr/bin/env python3
"""Requirement-led seed ideation. Generate/replay/mutate creative briefs; audit declared counts.

Only Python standard library. Generated creative instructions are reproducible from
seed + normalized spec + tool version; LLM output is not guaranteed deterministic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import sys
import unicodedata
from pathlib import Path
from typing import Any, Optional

from glyphs import SHAPES

VERSION = '1.5.0'
ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
DEFAULT_LENGTH = 16
MAX_SEED_LENGTH = 64
ROLES = ['形态', '发音/韵律', '位置/结构', '关系/反向']
OPEN_AXES = [
    ('scope','作用对象与尺度'), ('selection','目标选择与条件'),
    ('timing','时序与触发'), ('interaction','现有元素的互动方式'),
    ('tradeoff','代价与取舍'), ('feedback','反馈与可观察性'),
    ('representation','表达形式与信息结构'), ('edge_case','特殊情形与边界'),
]


def canonicalize_seed(value: str) -> str:
    result = ''.join(c for c in unicodedata.normalize('NFKC', value).upper()
                     if c != '-' and not c.isspace())
    if not 4 <= len(result) <= MAX_SEED_LENGTH:
        raise ValueError('seed must have 4-64 non-separator characters')
    if any(unicodedata.category(c).startswith('C') for c in result):
        raise ValueError('seed cannot contain control/invisible characters')
    return result


def random_seed(length: int = DEFAULT_LENGTH) -> str:
    if not 4 <= length <= MAX_SEED_LENGTH:
        raise ValueError('seed length must be between 4 and 64')
    return ''.join(secrets.choice(ALPHABET) for _ in range(length))


def mutate_seed(seed: str, edits: int = 2) -> tuple[str,list[int]]:
    if not 1 <= edits <= min(8,len(seed)):
        raise ValueError('edits must be in 1..min(8, seed_length)')
    positions = sorted(secrets.SystemRandom().sample(range(len(seed)),edits))
    chars = list(seed)
    for i in positions:
        chars[i] = secrets.choice([c for c in ALPHABET if c != chars[i]])
    return ''.join(chars), [i+1 for i in positions]


def digest(seed: str, spec_hash: str, *parts: object) -> bytes:
    return hashlib.sha256('|'.join(['seeded-ideation',VERSION,seed,spec_hash,
                                    *(str(p) for p in parts)]).encode('utf8')).digest()


def checksum(value: Any) -> str:
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,
                   separators=(',',':')).encode('utf8')).hexdigest()[:16]


def _nonblank(x: Any) -> bool:
    return isinstance(x,str) and bool(x.strip())


def validate_spec(spec: dict[str,Any]) -> dict[str,Any]:
    if not isinstance(spec,dict) or not _nonblank(spec.get('request')):
        raise ValueError('spec requires a nonempty request string')
    r = spec.get('requirements',[])
    if not isinstance(r,list) or any(not isinstance(x,dict) or not _nonblank(x.get('text'))
                                    or x.get('level','must') not in ('must','prefer','explore')
                                    or x.get('source','user') not in ('user','reference','inferred')
                                    for x in r):
        raise ValueError('requirements must be an array of {text, level?, source?, id?}')
    ids = [x.get('id') for x in r if x.get('id')]
    if len(ids)!=len(set(ids)):
        raise ValueError('duplicate requirement ids')
    axes = spec.get('freedoms',[])
    if not isinstance(axes,list) or any(not isinstance(x,dict) or not _nonblank(x.get('name')) for x in axes):
        raise ValueError('freedoms must be an array of {name, id?, description?}')
    d=spec.get('deliverables',{})
    if not isinstance(d,dict): raise ValueError('deliverables must be an object')
    for k in ('items','variants_min','variants_max','min_distinct_positions','max_new_attributes'):
        if k in d and (type(d[k]) is not int or d[k]<0):
            raise ValueError(f'deliverables.{k} must be a nonnegative integer')
    if d.get('items',4)>200 or d.get('items',4)<1:
        raise ValueError('deliverables.items must be 1..200')
    if d.get('variants_min',0)>d.get('variants_max',d.get('variants_min',0)):
        raise ValueError('variants_min cannot exceed variants_max')
    if d.get('min_distinct_positions',0)>d.get('items',4):
        raise ValueError('min_distinct_positions cannot exceed items')
    ideation=spec.get('ideation',{})
    if not isinstance(ideation,dict): raise ValueError('ideation must be an object')
    for k in ('pool_size','batch_size'):
        if k in ideation and (type(ideation[k]) is not int or not 1 <= ideation[k] <= 4096):
            raise ValueError(f'ideation.{k} must be an integer between 1 and 4096')
    if type(ideation.get('require_full_pool',False)) is not bool:
        raise ValueError('ideation.require_full_pool must be boolean')
    if ideation.get('pool_size',d.get('items',4)*16)<d.get('items',4):
        raise ValueError('ideation.pool_size cannot be less than final items')
    profile=spec.get('design',{})
    if not isinstance(profile,dict): raise ValueError('design must be an object')
    if profile.get('mode','standard') not in ('quick','standard','rigorous'):
        raise ValueError('design.mode must be quick, standard or rigorous')
    if profile.get('strategy','compare') not in ('direct','compare'):
        raise ValueError('design.strategy must be direct or compare')
    context=spec.get('context',{})
    if not isinstance(context,dict): raise ValueError('context must be an object')
    if not isinstance(spec.get('unknowns',[]),list): raise ValueError('unknowns must be an array')
    return spec


def load_spec(path: str) -> dict[str,Any]:
    try: value=json.loads(Path(path).read_text(encoding='utf8'))
    except (OSError,json.JSONDecodeError) as e: raise ValueError(f'invalid spec: {e}') from e
    return validate_spec(value)


def quick_spec(args: argparse.Namespace) -> dict[str,Any]:
    if not args.request:
        raise ValueError('supply --request or --spec; creative requirements cannot be guessed from domain alone')
    requirements = ([{'id':f'CLI-{i+1}', 'text':x, 'level':'must','source':'user'}
                      for i,x in enumerate(args.hard or [])] +
                    [{'id':f'PREF-{i+1}', 'text':x, 'level':'prefer','source':'user'}
                      for i,x in enumerate(args.prefer or [])])
    return validate_spec({'request':args.request,'context':{'summary':args.context or ''},
                          'requirements':requirements,
                          'freedoms':[{'name':x} for x in (args.axis or [])],
                          'deliverables':{'items':args.count if args.count is not None else 4},
                          'ideation':{'pool_size':args.pool_size} if args.pool_size else {}})


def get_anchors(seed:str,spec_hash:str,candidate_index:int)->list[dict[str,Any]]:
    positions=sorted(range(len(seed)),key=lambda p:digest(seed,spec_hash,'anchor',candidate_index,p))[:4]
    return [{'position':p+1,'char':seed[p],'role':ROLES[j],
             'shape_hint':SHAPES.get(seed[p],'自行观察字形、音韵或语义')}
            for j,p in enumerate(positions)]


def make_brief(seed:str,spec:dict[str,Any],count:Optional[int]=None,wildness:int=3,start_index:int=0)->dict[str,Any]:
    validate_spec(spec)
    if not 1<=wildness<=5: raise ValueError('wildness must be 1..5')
    n=count if count is not None else spec.get('deliverables',{}).get('items',4)
    if not 1<=n<=4096: raise ValueError('count must be 1..4096')
    if not 0<=start_index<=4095 or start_index+n>4096: raise ValueError('candidate index out of bounds')
    sid=checksum(spec)
    axes=spec.get('freedoms') or [{'id':a,'name':b,'description':'仅在本次用户请求允许时应用'} for a,b in OPEN_AXES]
    order=sorted(range(len(axes)),key=lambda i:digest(seed,sid,'axis',i))
    routes=[]
    for offset in range(n):
        idx=start_index+offset
        axis=axes[order[idx % len(axes)]]
        routes.append({'number':idx+1,'exploration_axis':axis,
                       'anchors':get_anchors(seed,sid,idx),
                       'instructions':[
                           '从至少两个种子字符提炼联想，不把字形词典当成机制指令。',
                           '先满足用户本次要求和硬约束；在允许的部分映射联想。',
                           '如果联想与当前需求无关，重解释字符，不改写用户需求。',
                           '候选与其他候选应在决策或因果结构上有实质差异，不只调整名字和参数。',
                       ]})
    return {'tool':'seeded-ideation','version':VERSION,'seed':seed,
            'formatted_seed':'-'.join(seed[i:i+4] for i in range(0,len(seed),4)),
            'seed_fingerprint':hashlib.sha256(seed.encode('utf8')).hexdigest()[:12],
            'spec_fingerprint':sid,'request':spec['request'],
            'context':spec.get('context',{}),'requirements':spec.get('requirements',[]),
            'freedoms':spec.get('freedoms',[]),
            'deliverables':spec.get('deliverables',{}),'unknowns':spec.get('unknowns',[]),
            'count':n,'start_index':start_index,'wildness':wildness,'candidates':routes,
            'agent_instructions':[
                '用户当前要求是此次设计的最高任务意图；既有项目资料用于正确理解背景，不能被误当成用户永不允许修改的规则。',
                '辨别明确硬约束、偏好、用户明确授权修改的范围、背景资料与未定义内容；禁止自行把偏好升格为硬规则。',
                '如果用户明确要求突破既有设计，应在授权范围探索改变；如果用户要求保持一致，应保持一致。',
                '如果用户未说明是否允许重构，基于目标给出低依赖的方案或标注超出当前实现的成本；仅在决定性歧义时询问。',
                '新属性/新机制不默认为零，也不能因为发散强度高就任意增加；新增复杂度必须直接服务当前用户要求。',
                '先定义与用户要求相关的可变设计轴；每条创意联想写成 字符→联想→相关轴→设计效果→目标收益。',
                '不得强制修改核心循环/引入异域机制。异域类比只是一种可选思考手段，并非必做项目。',
                '候选生成后按当前请求的限制进行审查，区分明确冲突、潜在工程依赖、没有证据的猜测。',
                '交付足量内容，覆盖用户要求的数量、变体、独立定位和差异，不用少量示例冒充完整交付。',
                '种子和指令卡可确定性回放；自然语言生成不保证字节级重现；不把设计种子混同项目模拟种子。',
            ]}


def make_plan(seed:str,spec:dict[str,Any],wildness:int=3,
              pool_size:Optional[int]=None,batch_size:Optional[int]=None)->dict[str,Any]:
    validate_spec(spec)
    ideation=spec.get('ideation',{})
    final_count=spec.get('deliverables',{}).get('items',4)
    pool=pool_size if pool_size is not None else ideation.get('pool_size',min(256,final_count*16))
    batch=batch_size if batch_size is not None else ideation.get('batch_size',32)
    if type(pool) is not int or not final_count<=pool<=4096: raise ValueError('pool_size must be between final item count and 4096')
    if type(batch) is not int or not 1<=batch<=4096: raise ValueError('batch_size must be 1..4096')
    if not 1<=wildness<=5: raise ValueError('wildness must be 1..5')
    return {
      'tool':'seeded-ideation','version':VERSION,'seed':seed,
      'formatted_seed':'-'.join(seed[i:i+4] for i in range(0,len(seed),4)),
      'spec_fingerprint':checksum(spec),'final_items':final_count,
      'planned_initial_candidates':pool,'initial_candidates_generated':0,
      'batch_size':batch,'wildness':wildness,
      'require_full_pool':ideation.get('require_full_pool',False),
      'batches':[{'batch':i+1,'start':start+1,'count':min(batch,pool-start)}
                 for i,start in enumerate(range(0,pool,batch))],
      'selection_stages':[
        'Generate brief one-line concepts for every planned route; a route card is NOT itself a generated idea.',
        'Semantic must-rule gate per idea with evidence: pass/fail/uncertain. Exclude fail and uncertain, even if inventive.',
        'Deduplicate mechanisms, cluster distinct approaches and identify gaps; regenerate within the original request if needed.',
        'Assess fit, usefulness, feasibility and novelty; rerank for diversity under group-wide budgets.',
        'Expand ONLY the selected final items, then re-check full requirements and variants.'
      ]
    }


def mechanical_validate(spec:dict[str,Any],candidate_doc:dict[str,Any])->dict[str,Any]:
    """Checks measurable output-shape rules ONLY; never asserts semantic correctness."""
    validate_spec(spec)
    d=spec.get('deliverables',{})
    items=candidate_doc.get('items')
    if not isinstance(items,list): raise ValueError('candidate document must contain items array')
    errors=[]
    if 'items' in d and len(items)!=d['items']:
        errors.append(f'item count {len(items)} != {d["items"]}')
    seen=set(); positions=set(); attributes=set()
    for i,item in enumerate(items):
        if not isinstance(item,dict):
            errors.append(f'items[{i}] not object');continue
        key=item.get('id')
        if not _nonblank(key): errors.append(f'items[{i}] lacks id')
        elif key in seen: errors.append(f'duplicate id {key}')
        else: seen.add(key)
        position=item.get('position')
        if _nonblank(position): positions.add(position.strip())
        else: errors.append(f'items[{i}] lacks position')
        variants=item.get('variants',[])
        if not isinstance(variants,list): errors.append(f'items[{i}].variants not array')
        else:
            if len(variants)<d.get('variants_min',0):
                errors.append(f'items[{i}].variants below minimum')
            if 'variants_max' in d and len(variants)>d['variants_max']:
                errors.append(f'items[{i}].variants above maximum')
        added=item.get('new_attributes',[])
        if not isinstance(added,list) or any(not _nonblank(x) for x in added):
            errors.append(f'items[{i}].new_attributes must be array of names')
        else: attributes.update(added)
    if len(positions)<d.get('min_distinct_positions',0):
        errors.append(f'position labels {len(positions)} < {d["min_distinct_positions"]}')
    if 'max_new_attributes' in d and len(attributes)>d['max_new_attributes']:
        errors.append(f'new attributes {len(attributes)} > {d["max_new_attributes"]}')
    return {'tool':'seeded-ideation','version':VERSION,'mechanical_pass':not errors,
            'semantic_review_required':True,'errors':errors,
            'observed':{'items':len(items),'declared_positions':len(positions),
                        'unique_new_attributes':len(attributes)},
            'notes':'声明式结构检查：不验证职位是否真的独立、变体是否有意义、数量以外的自然语言规则，必须人工审查。'}


def as_markdown(brief:dict[str,Any])->str:
    lines=['# Seeded Ideation / 需求驱动创意指令卡',
           f'- 种子：`{brief["formatted_seed"]}`',
           f'- 版本：`{brief["version"]}`；需求指纹：`{brief["spec_fingerprint"]}`',
           f'- 当前要求：{brief["request"]}',
           f'- 发散强度：{brief["wildness"]}/5；候选数：{brief["count"]}']
    if brief.get('context'): lines.append(f'- 已提供背景：{json.dumps(brief["context"],ensure_ascii=False)}')
    if brief['requirements']:
        lines+=['','## 用户约束、偏好及来源']
        for r in brief['requirements']:
            lines.append(f'- [{r.get("level","must")}/{r.get("source","user")}] {r.get("id", "")}: {r["text"]}')
    if brief.get('deliverables'): lines.extend(['','## 可量化交付要求',
                                  json.dumps(brief['deliverables'],ensure_ascii=False)])
    if brief['unknowns']: lines+=['','## 尚未确定的事项']+[f'- {u}' for u in brief['unknowns']]
    lines+=['','## 种子字符',' · '.join(f'{i+1}:{x}' for i,x in enumerate(brief['seed']))]
    for c in brief['candidates']:
        lines+=['',f'## 候选 {c["number"]} / {c["exploration_axis"]["name"]}']
        for a in c['anchors']:
            lines.append(f'- `{a["char"]}`（位置 {a["position"]} / {a["role"]}）→ {a["shape_hint"]}')
        lines+=['- 先映射当前要求，再提出方案；不得把联想当成外加需求。']
    lines+=['','## Agent 执行说明']
    lines += [f'{i}. {s}' for i,s in enumerate(brief['agent_instructions'],1)]
    return '\n'.join(lines)+'\n'


def main(argv:Optional[list[str]]=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',nargs='?',default='new',choices=['new','replay','mutate','validate','plan','batch'])
    p.add_argument('--seed');p.add_argument('--length',type=int,default=DEFAULT_LENGTH)
    p.add_argument('--edits',type=int,default=2)
    p.add_argument('--spec',help='JSON file describing this user request, its requirements and freedoms')
    p.add_argument('--request',help='current user request; required unless --spec is supplied')
    p.add_argument('--context',help='project background or existing design summary (not automatically immutable)')
    p.add_argument('--hard',action='append',help='explicit hard constraint (repeatable)')
    p.add_argument('--prefer',action='append',help='preference (repeatable)')
    p.add_argument('--axis',action='append',help='allowed exploration axis (repeatable)')
    p.add_argument('--count',type=int,default=None,help='route count; defaults to spec deliverables.items')
    p.add_argument('--pool-size',type=int,default=None,help='ideation route pool size, e.g. 256 (plan/batch)')
    p.add_argument('--batch-size',type=int,default=None,help='routes per batch, e.g. 32 (plan/batch)')
    p.add_argument('--start',type=int,default=None,help='1-based global route start (batch)')
    p.add_argument('--wildness',type=int,default=3)
    p.add_argument('--format',choices=['json','markdown'],default='markdown')
    p.add_argument('--candidates',help='candidate JSON for structural validation')
    p.add_argument('--require-ready',action='store_true',help='refuse plan/batch if user-need interview is unresolved')
    a=p.parse_args(argv)
    try:
        spec=load_spec(a.spec) if a.spec else quick_spec(a)
        if a.action in ('plan','batch') and (a.require_ready or 'elicitation' in spec):
            from brief_gate import audit
            readiness=audit(spec)
            if not readiness['ready_for_ideation']:
                qs='; '.join(f"{q['id']}: {q['question']}" for q in readiness['questions_to_ask_now'])
                raise ValueError(f"clarification required before ideation (pending={readiness['pending_total']}): {qs}")
        if a.action=='validate':
            if not a.candidates: p.error('validate requires --candidates')
            proposals=json.loads(Path(a.candidates).read_text(encoding='utf8'))
            result=mechanical_validate(spec,proposals)
            print(json.dumps(result,ensure_ascii=False,indent=2))
            return 0 if result['mechanical_pass'] else 1
        if a.action in ('new','plan'):
            if a.action=='new' and a.seed: p.error('new generates a seed; use replay --seed')
            seed=canonicalize_seed(a.seed) if a.seed else random_seed(a.length)
        else:
            if not a.seed: p.error(f'{a.action} requires --seed')
            seed=canonicalize_seed(a.seed)
        changed=[]
        if a.action=='mutate': seed,changed=mutate_seed(seed,a.edits)
        if a.action=='plan':
            plan=make_plan(seed,spec,a.wildness,a.pool_size,a.batch_size)
            print(json.dumps(plan,ensure_ascii=False,indent=2))
            return 0
        if a.action=='batch':
            if a.start is None or a.start<1: p.error('batch requires --start >= 1')
            plan=make_plan(seed,spec,a.wildness,a.pool_size,a.batch_size)
            if a.start>plan['planned_initial_candidates']: p.error('start exceeds pool_size')
            number=min(plan['batch_size'],plan['planned_initial_candidates']-a.start+1)
            brief=make_brief(seed,spec,number,a.wildness,start_index=a.start-1)
            brief['planned_initial_candidates']=plan['planned_initial_candidates']
        else:
            brief=make_brief(seed,spec,a.count,a.wildness)
        if changed: brief['mutation_positions_1_based']=changed
        print(json.dumps(brief,ensure_ascii=False,indent=2) if a.format=='json' else as_markdown(brief))
        return 0
    except (ValueError,OSError,json.JSONDecodeError) as e:
        p.error(str(e))
    return 2

if __name__=='__main__': sys.exit(main())
