# Large-pool independent-seed ideation and selection (v1.6)

## Goal

Generate many *short* concepts, drop those inconsistent with the user's actual instructions, cluster repeated approaches, and spend detailed elaboration only on the best few. Example: target 4 creative directions, initial pool 256. The proportions are a **budget choice**, not a creativity law.

## 1. Build the request spec first

Requirements with `level: must` are exclusion conditions. `prefer` and `explore` guide scoring; they do not become artificial bans. User-permitted redesigns are not breaches of existing reference material. Check whether constraints apply to each proposal or the final set (e.g. `max_new_attributes` is a union across four finalists).

## 2. Batch candidate generation

Independently draw **256 different seeds, one seed per path**; then generate 8 batches × 32 short concepts, but don't just assign a unique number to near-synonymous adjectives. The Agent must actually write the concept, store an idea ID, describe its mechanism/idea in 1–3 sentences, note the origin character connection, and attach candidate-level reasoning. Consider prompt diversification along request-relevant axes. **Route prompt count does not equal candidate idea count.**

If generated pool quality plateaus, probe missing modes of thought rather than expanding redundant styles. If user asks for rapid suggestions, reduce P or stop early and disclose what was done.

## 3. Required machine-readable candidate schema

`pool.json` for `scripts/funnel_select.py`:

```json
{
  "items": [
    {
      "id": "idea-0001",
      "path_number": 1,
      "seed": "K7M28QVAT3XPH6RD",
      "seed_fingerprint": "<compute from seed_ideation.fingerprint(seed)>",
      "concept": "Short unique design description, not only a route label",
      "position": "core differentiated role in the user's vocabulary",
      "mechanism_signature": "time:handoff:on-completion",
      "mechanism_tags": ["handoff", "production", "timing"],
      "new_attributes": [],
      "requirement_checks": {
        "R1": {"status": "pass", "evidence": "Why it fits the actual R1 requirement"},
        "R2": {"status": "fail", "evidence": "Conflicts with the user's R2 restriction"}
      },
      "scores": {"fit": 4.5, "usefulness": 4, "feasibility": 4, "novelty": 3}
    }
  ]
}
```

- When using a v1.6 plan, pass `--plan plan.json` to the selector, and record `path_number`, exact path `seed`, and `seed_fingerprint` for **every** candidate. The script rejects missing, repeated or inconsistent path↔seed mapping. Replace the placeholder fingerprint in the schema with the actual output from the manifest. An isolated candidate without a plan can still be filtered, but no lineage audit is claimed.
- Every `must` requirement (by exact `id`; fallback `MUST-n` if none) **must** have `pass` and nonblank evidence to survive. `fail`, `uncertain`, missing checks, or missing evidence block selection. Do not label unsupported assumptions as `pass`.
- `mechanism_signature` and `mechanism_tags` are agent-assigned descriptions; the script cannot validate their semantic truth. Use stable standardized signatures for true duplicates and tags shared by related concepts. Changing labels only to evade deduplication is invalid.
- Scores 0–5 are **judgment calls**, not measurements; give lower fit to irrelevant approaches no matter how novel. Weights: fit 0.40, usefulness 0.25, feasibility 0.20, novelty 0.15. Diversity is a separate small rerank using tag overlap and repeated position.
- Do not use low scoring as a substitute for identifying hard violations. Screening comes first.
- Before selection, the candidate set should include every actually generated short idea; do not report a complete 256-pool if 256 routes were issued but only 40 ideas were authored.

## 4. Selection steps

1. **256 raw ideas**: short, distinguishable concept sketches.
2. **Hard filter**: remove ideas contradicting any user `must` requirement. Mark uncertain as quarantined until checked.
3. **Deduplicate**: collapse same-mechanism variants; cross-check clusters for mislabeled duplicates.
4. **64 coarse shortlist**: breadth, user relevance, feasible without invented dependencies.
5. **16 semifinals**: score fit/usefulness/feasibility/novelty, weigh differentiation across core ideas.
6. **4 finalists**: satisfy group-level budgets and required distinct roles; expand and re-audit detailed outcomes.

Intermediate counts are maxima or targets: if only 47 pass hard rules, report 47, not 64. If 256 are poor, don't call the best four strong merely because they rank highest. Demand a minimum quality justified by the task and regenerate when needed.

## 5. Caveats and implementation

`funnel_select.py` performs structural checks on *provided* Agent reviews, excludes non-passes, deduplicates exact declared signatures, and uses deterministic diversity-aware reranking. It does not run a semantic evaluator, discover latent factual errors, or prove the idea objectively best. An independent reviewer or project tests should challenge finalists, particularly high-stakes or engine-specific constraints.

Do not confuse 256 independently sampled seeds with 256 actually written design concepts; claiming the latter requires recording each concept. Do not invent screening statistics. Do not claim an LLM-generated prose response is deterministic merely because route cards are replayable. Keep the seed separate from project/runtime simulation seeds.
