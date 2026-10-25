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

VERSION = '1.7.0'
MIN_INDEPENDENT_SEEDS = 64
MAX_POOL_SIZE = 4096
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


def minimum_pool_size(final_items:int)->int:
    """Smallest exact-halving population >=64 with at least one selection round."""
    if type(final_items) is not int or not 1<=final_items<=200:
        raise ValueError('final_items must be 1..200')
    count=final_items*2
    while count<MIN_INDEPENDENT_SEEDS:
        count*=2
    if count>MAX_POOL_SIZE: raise ValueError('final output too large for seed budget')
    return count


def halving_rounds(pool_size:int, final_items:int)->list[int]:
    """Return exact round quotas, with no arbitrary final trimming."""
    minimum=minimum_pool_size(final_items)
    if type(pool_size) is not int or pool_size<minimum or pool_size>MAX_POOL_SIZE:
        raise ValueError(f'pool_size must be >= {minimum} (at least {MIN_INDEPENDENT_SEEDS} independent seeds) and <= {MAX_POOL_SIZE}')
    rounds=[];remaining=pool_size
    while remaining>final_items and remaining%2==0:
        remaining//=2
        rounds.append(remaining)
    if remaining!=final_items:
        suggestion=minimum
        while suggestion<pool_size and suggestion<=MAX_POOL_SIZE:
            suggestion*=2
        raise ValueError(f'pool_size {pool_size} cannot halve exactly to {final_items} finalists; '
                         f'use {suggestion} instead' if suggestion<=MAX_POOL_SIZE else
                         f'pool_size {pool_size} cannot halve exactly to {final_items} finalists within {MAX_POOL_SIZE}')
    return rounds


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
    if 'pool_size' in ideation:
        halving_rounds(ideation['pool_size'],d.get('items',4))
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


def get_anchors(seed:str,spec_hash:str)->list[dict[str,Any]]:
    positions=sorted(range(len(seed)),key=lambda p:digest(seed,spec_hash,'anchor',p))[:4]
    return [{'position':p+1,'char':seed[p],'role':ROLES[j],
             'shape_hint':SHAPES.get(seed[p],'自行观察字形、音韵或语义')}
            for j,p in enumerate(positions)]


def formatted_seed(seed:str)->str:
    return '-'.join(seed[i:i+4] for i in range(0,len(seed),4))


def fingerprint(seed:str)->str:
    return hashlib.sha256(seed.encode('utf8')).hexdigest()[:12]


def independent_paths(count:int,length:int=DEFAULT_LENGTH,start:int=1)->list[dict[str,Any]]:
    """Draw one fresh, *independent* cryptographic random seed for EACH path.

    This is not a master seed with indexed derivatives. Persist the returned
    manifest to replay a run; independently sampled draws cannot be regenerated
    from a single master string.
    """
    if type(count) is not int or not 1<=count<=MAX_POOL_SIZE:raise ValueError('seed count must be 1..4096')
    if type(start) is not int or start<1 or start+count-1>4096:raise ValueError('path number out of bounds')
    if type(length) is not int or not 4<=length<=MAX_SEED_LENGTH:
        raise ValueError('seed length must be 4..64')
    used=set();paths=[]
    for number in range(start,start+count):
        seed=random_seed(length)
        while seed in used:seed=random_seed(length)
        used.add(seed)
        paths.append({'number':number,'seed':seed,'formatted_seed':formatted_seed(seed),
                      'seed_fingerprint':fingerprint(seed)})
    return paths


def manifest_fingerprint(spec_hash:str,paths:list[dict[str,Any]])->str:
    return checksum({'schema':'one-independent-seed-per-path-v1',
                     'spec_fingerprint':spec_hash,
                     'paths':[(p['number'],p['seed']) for p in paths]})


def make_route(path:dict[str,Any],spec:dict[str,Any],wildness:int)->dict[str,Any]:
    seed=canonicalize_seed(path['seed'])
    sid=checksum(spec)
    axes=spec.get('freedoms') or [{'id':a,'name':b,'description':'仅在本次用户请求允许时应用'} for a,b in OPEN_AXES]
    axis=axes[sorted(range(len(axes)),key=lambda i:digest(seed,sid,'axis',i))[0]]
    return {'number':path['number'],'seed':seed,
            'formatted_seed':formatted_seed(seed),'seed_fingerprint':fingerprint(seed),
            'exploration_axis':axis,'anchors':get_anchors(seed,sid),
            'instructions':[
                '本候选有自己的独立种子。仅从本种子提取联想，不借用其他候选的种子或把批次编号当随机因子。',
                '从至少两个种子字符提炼联想，不把字形词典当成机制指令。',
                '先满足用户本次要求和硬约束；在允许的部分映射联想。',
                '如果联想与当前需求无关，重解释字符，不改写用户需求。',
                '候选与其他候选应在决策或因果结构上有实质差异，不只调整名字和参数。',
            ]}


def make_brief_from_paths(paths:list[dict[str,Any]],spec:dict[str,Any],wildness:int=3)->dict[str,Any]:
    validate_spec(spec)
    if not 1<=wildness<=5:raise ValueError('wildness must be 1..5')
    if not paths:raise ValueError('paths cannot be empty')
    if len(paths)>4096:raise ValueError('too many paths')
    seen_seeds=set();seen_numbers=set()
    for path in paths:
        seed=canonicalize_seed(path['seed'])
        number=path['number']
        if type(number) is not int or not 1<=number<=4096 or number in seen_numbers:
            raise ValueError('path numbers must be unique integers in 1..4096')
        if seed in seen_seeds:raise ValueError('duplicate seed assigned to multiple paths')
        if path.get('seed_fingerprint',fingerprint(seed))!=fingerprint(seed):
            raise ValueError('seed fingerprint does not match seed')
        seen_seeds.add(seed);seen_numbers.add(number)
    routes=[make_route(path,spec,wildness) for path in paths]
    return {'tool':'seeded-ideation','version':VERSION,'seed_model':'independent-per-path',
            'seeds':[{'number':r['number'],'seed':r['seed'],
                      'seed_fingerprint':r['seed_fingerprint']} for r in routes],
            'spec_fingerprint':checksum(spec),'request':spec['request'],
            'context':spec.get('context',{}),'requirements':spec.get('requirements',[]),
            'freedoms':spec.get('freedoms',[]),
            'deliverables':spec.get('deliverables',{}),'unknowns':spec.get('unknowns',[]),
            'count':len(routes),'start_index':min(seen_numbers)-1,'wildness':wildness,
            'candidates':routes,
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
                '每个候选只对应自己的一个独立随机种子；记录全部种子以便逐条重放。随机路线可重放，LLM输出仍不保证逐字一致。',
            ]}


def make_brief(seed:str,spec:dict[str,Any],count:Optional[int]=None,
               wildness:int=3,start_index:int=0)->dict[str,Any]:
    """Replay ONE path from ONE seed. Multiple paths require multiple seeds."""
    if count not in (None,1):raise ValueError('one seed may only map to one path; use new/plan for many')
    canonical=canonicalize_seed(seed)
    return make_brief_from_paths([{'number':start_index+1,'seed':canonical}],spec,wildness)


def make_plan(spec:dict[str,Any],wildness:int=3,
              pool_size:Optional[int]=None,batch_size:Optional[int]=None,
              seed_length:int=DEFAULT_LENGTH)->dict[str,Any]:
    validate_spec(spec)
    ideation=spec.get('ideation',{})
    final_count=spec.get('deliverables',{}).get('items',4)
    pool=pool_size if pool_size is not None else ideation.get('pool_size',minimum_pool_size(final_count))
    round_quotas=halving_rounds(pool,final_count)
    batch=batch_size if batch_size is not None else ideation.get('batch_size',32)
    if type(batch) is not int or not 1<=batch<=4096:
        raise ValueError('batch_size must be 1..4096')
    if not 1<=wildness<=5:raise ValueError('wildness must be 1..5')
    paths=independent_paths(pool,seed_length)
    sid=checksum(spec)
    return {
      'tool':'seeded-ideation','version':VERSION,'seed_model':'independent-per-path',
      'spec_fingerprint':sid,'manifest_fingerprint':manifest_fingerprint(sid,paths),
      'final_items':final_count,'planned_initial_candidates':pool,
      'initial_candidates_generated':0,'seed_count':len(paths),'paths':paths,
      'minimum_seed_count':MIN_INDEPENDENT_SEEDS,'halving_rounds':round_quotas,
      'round_rule':'exact-half-until-final',
      'batch_size':batch,'wildness':wildness,
      'require_full_pool':True,
      'batches':[{'batch':i+1,'start':start+1,'count':min(batch,pool-start)}
                 for i,start in enumerate(range(0,pool,batch))],
      'selection_stages':[
        'Every path has an independently sampled seed; save this plan JSON before generating batches.',
        'Generate one actual brief concept for every planned seed path; route prompts alone are not concepts.',
        'Semantic hard-rule gate per idea with evidence; reject failures and uncertain claims.',
        'Deduplicate similar approaches; each round must hit the scheduled exact-half quota, or stop and report a shortfall.',
        'Expand only the selected finalists; retest full requirements and meaningful differences.'
      ]
    }


def load_plan(path:str,spec:dict[str,Any])->dict[str,Any]:
    try:plan=json.loads(Path(path).read_text(encoding='utf8'))
    except (OSError,json.JSONDecodeError) as e:raise ValueError(f'invalid plan: {e}') from e
    if not isinstance(plan,dict) or plan.get('seed_model')!='independent-per-path':
        raise ValueError('legacy plan unsupported; regenerate a v1.7 independent-seed plan')
    if plan.get('version')!=VERSION:raise ValueError('plan version differs; generate a new plan')
    if plan.get('spec_fingerprint')!=checksum(spec):
        raise ValueError('plan spec fingerprint mismatch; use the original request spec')
    paths=plan.get('paths')
    if not isinstance(paths,list) or not paths or len(paths)>4096:
        raise ValueError('plan paths missing or invalid')
    if len(paths)!=plan.get('seed_count') or len(paths)!=plan.get('planned_initial_candidates'):
        raise ValueError('plan seed count differs from path count')
    rounds=halving_rounds(len(paths),spec.get('deliverables',{}).get('items',4))
    if plan.get('halving_rounds')!=rounds or plan.get('round_rule')!='exact-half-until-final' or plan.get('minimum_seed_count')!=MIN_INDEPENDENT_SEEDS:
        raise ValueError('plan half-elimination schedule mismatch')
    if plan.get('require_full_pool') is not True:
        raise ValueError('plan must require a complete seed population')
    seen=set()
    for i,path in enumerate(paths):
        if not isinstance(path,dict) or path.get('number')!=i+1:
            raise ValueError('plan paths must have consecutive 1-based numbers')
        seed=path.get('seed')
        if not isinstance(seed,str) or canonicalize_seed(seed)!=seed or not all(c in ALPHABET for c in seed):
            raise ValueError(f'plan path {i+1} has invalid generated seed')
        if seed in seen:raise ValueError('plan contains duplicate seeds')
        seen.add(seed)
        if path.get('formatted_seed')!=formatted_seed(seed) or path.get('seed_fingerprint')!=fingerprint(seed):
            raise ValueError(f'plan path {i+1} seed metadata mismatch')
    if plan.get('manifest_fingerprint')!=manifest_fingerprint(checksum(spec),paths):
        raise ValueError('plan manifest fingerprint mismatch')
    if type(plan.get('batch_size')) is not int or plan['batch_size']<1:
        raise ValueError('plan batch_size invalid')
    if type(plan.get('wildness')) is not int or not 1<=plan['wildness']<=5:
        raise ValueError('plan wildness invalid')
    return plan


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
           f'- 每条路径独立的种子数：{len(brief["seeds"])}',
           f'- 版本：`{brief["version"]}`；需求指纹：`{brief["spec_fingerprint"]}`',
           f'- 当前要求：{brief["request"]}',
           f'- 发散强度：{brief["wildness"]}/5；路径数：{brief["count"]}']
    if brief.get('context'):lines.append(f'- 已提供背景：{json.dumps(brief["context"],ensure_ascii=False)}')
    if brief['requirements']:
        lines+=['','## 用户约束、偏好及来源']
        for r in brief['requirements']:
            lines.append(f'- [{r.get("level","must")}/{r.get("source","user")}] {r.get("id", "")}: {r["text"]}')
    if brief.get('deliverables'):lines.extend(['','## 可量化交付要求',
                                      json.dumps(brief['deliverables'],ensure_ascii=False)])
    if brief['unknowns']:lines+=['','## 尚未确定的事项']+[f'- {u}' for u in brief['unknowns']]
    for c in brief['candidates']:
        lines+=['',f'## 路径 {c["number"]} / 独立种子 `{c["formatted_seed"]}`',
                f'- 探索方向：{c["exploration_axis"]["name"]}']
        for a in c['anchors']:
            lines.append(f'- `{a["char"]}`（位置 {a["position"]} / {a["role"]}）→ {a["shape_hint"]}')
        lines+=['- 先映射当前要求，再提出方案；不得把联想当成外加需求。']
    lines+=['','## Agent 执行说明']
    lines += [f'{i}. {s}' for i,s in enumerate(brief['agent_instructions'],1)]
    return '\n'.join(lines)+'\n'


def main(argv:Optional[list[str]]=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',nargs='?',default='new',choices=['new','replay','mutate','validate','plan','batch'])
    p.add_argument('--seed',help='one existing seed: replay or mutate ONE path')
    p.add_argument('--plan',help='immutable v1.7 per-path seed manifest (batch or replay)')
    p.add_argument('--length',type=int,default=DEFAULT_LENGTH,help='independent seed length (4..64)')
    p.add_argument('--edits',type=int,default=2)
    p.add_argument('--spec',help='JSON file describing this user request')
    p.add_argument('--request',help='current user request, unless --spec is supplied')
    p.add_argument('--context',help='project background (not immutable by default)')
    p.add_argument('--hard',action='append',help='hard constraint (repeatable)')
    p.add_argument('--prefer',action='append',help='preference (repeatable)')
    p.add_argument('--axis',action='append',help='exploration axis (repeatable)')
    p.add_argument('--count',type=int,default=None,help='new: independent seeds, minimum 64, must halve exactly to final items')
    p.add_argument('--pool-size',type=int,default=None,help='plan: independently drawn path count')
    p.add_argument('--batch-size',type=int,default=None,help='plan: paths per batch')
    p.add_argument('--start',type=int,default=None,help='1-based path number (batch or plan replay)')
    p.add_argument('--wildness',type=int,default=3)
    p.add_argument('--format',choices=['json','markdown'],default='markdown')
    p.add_argument('--candidates',help='final design JSON for structural validation')
    p.add_argument('--require-ready',action='store_true',help='refuse plan/batch if interview unresolved')
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
            if not a.candidates:p.error('validate requires --candidates')
            proposals=json.loads(Path(a.candidates).read_text(encoding='utf8'))
            result=mechanical_validate(spec,proposals)
            print(json.dumps(result,ensure_ascii=False,indent=2))
            return 0 if result['mechanical_pass'] else 1
        if a.action in ('new','plan') and (a.seed or a.plan):
            raise ValueError(f'{a.action} generates new independent seeds; omit --seed and --plan')
        if a.action=='plan':
            plan=make_plan(spec,a.wildness,a.pool_size,a.batch_size,a.length)
            print(json.dumps(plan,ensure_ascii=False,indent=2))
            return 0
        if a.action=='new':
            number=a.count if a.count is not None else spec.get('ideation',{}).get('pool_size',minimum_pool_size(spec.get('deliverables',{}).get('items',4)))
            halving_rounds(number,spec.get('deliverables',{}).get('items',4))
            paths=independent_paths(number,a.length)
            brief=make_brief_from_paths(paths,spec,a.wildness)
            brief['halving_rounds']=halving_rounds(number,spec.get('deliverables',{}).get('items',4))
        elif a.action=='batch':
            if not a.plan or a.seed:raise ValueError('batch requires --plan plan.json; do not supply --seed')
            if a.start is None or a.start<1:raise ValueError('batch requires --start >= 1')
            plan=load_plan(a.plan,spec)
            if a.start>len(plan['paths']):raise ValueError('start exceeds seed path count')
            paths=plan['paths'][a.start-1:a.start-1+plan['batch_size']]
            brief=make_brief_from_paths(paths,spec,plan['wildness'])
            brief['manifest_fingerprint']=plan['manifest_fingerprint']
            brief['planned_initial_candidates']=len(plan['paths'])
        elif a.action=='replay':
            if a.count not in (None,1):raise ValueError('one seed maps to one path; use plan or new for several')
            if bool(a.seed)==bool(a.plan):raise ValueError('replay requires exactly one of --seed or --plan')
            if a.plan:
                if a.start is None or a.start<1:raise ValueError('plan replay requires --start (path number)')
                plan=load_plan(a.plan,spec)
                if a.start>len(plan['paths']):raise ValueError('start exceeds seed path count')
                brief=make_brief_from_paths([plan['paths'][a.start-1]],spec,plan['wildness'])
                brief['manifest_fingerprint']=plan['manifest_fingerprint']
            else:
                brief=make_brief(a.seed,spec,1,a.wildness,(a.start or 1)-1)
        else: # mutate: still exactly one old seed -> one new seed -> one new path.
            if not a.seed or a.plan:raise ValueError('mutate requires --seed (one path), not --plan')
            seed,changed=mutate_seed(canonicalize_seed(a.seed),a.edits)
            brief=make_brief(seed,spec,1,a.wildness,(a.start or 1)-1)
            brief['mutation_positions_1_based']=changed
            brief['mutation_from_fingerprint']=fingerprint(canonicalize_seed(a.seed))
        print(json.dumps(brief,ensure_ascii=False,indent=2) if a.format=='json' else as_markdown(brief))
        return 0
    except (ValueError,OSError,json.JSONDecodeError) as e:
        p.error(str(e))
    return 2

if __name__=='__main__':sys.exit(main())
