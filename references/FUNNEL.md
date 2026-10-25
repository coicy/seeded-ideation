# Large-pool independent-seed ideation and selection (v1.7)

## Goal

Generate many *short* concepts, drop those inconsistent with the user's actual instructions, cluster repeated approaches, and spend detailed elaboration only on the best few. Example: target 4 creative directions, initial pool 256. The **64-seed floor and 50% per-round elimination are mandatory for this seeded divergent workflow**. Direct design tasks may use no random pool.

## 1. Build the request spec first

Requirements with `level: must` are exclusion conditions. `prefer` and `explore` guide scoring; they do not become artificial bans. User-permitted redesigns are not breaches of existing reference material. Check whether constraints apply to each proposal or the final set (e.g. `max_new_attributes` is a union across four finalists).

## 2. Batch candidate generation

Independently draw **at least 64 different seeds, one seed per path**; for the 256-seed example, generate 8 batches × 32 short concepts, but don't just assign a unique number to near-synonymous adjectives. The Agent must actually write the concept, store an idea ID, describe its mechanism/idea in 1–3 sentences, note the origin character connection, and attach candidate-level reasoning. Consider prompt diversification along request-relevant axes. **Route prompt count does not equal candidate idea count.**

If pool quality plateaus, probe missing modes of thought rather than expanding redundant styles. Never mark an incomplete pool as complete. For quick tasks that cannot afford 64 real sketches, switch to the separate direct design workflow and disclose that no seeded funnel was run.

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

- **Always** pass `--plan plan.json` to the seeded selector. Record `path_number`, exact path `seed`, and `seed_fingerprint` for **every** candidate; without a full 64+ seed manifest, the seeded selector refuses to run. Replace the placeholder fingerprint with the value from the manifest. This verifies declared identity, not semantic compliance.
- Every `must` requirement (by exact `id`; fallback `MUST-n` if none) **must** have `pass` and nonblank evidence to survive. `fail`, `uncertain`, missing checks, or missing evidence block selection. Do not label unsupported assumptions as `pass`.
- `mechanism_signature` and `mechanism_tags` are agent-assigned descriptions; the script cannot validate their semantic truth. Use stable standardized signatures for true duplicates and tags shared by related concepts. Changing labels only to evade deduplication is invalid.
- Scores 0–5 are **judgment calls**, not measurements; give lower fit to irrelevant approaches no matter how novel. Weights: fit 0.40, usefulness 0.25, feasibility 0.20, novelty 0.15. Diversity is a separate small rerank using tag overlap and repeated position.
- Do not use low scoring as a substitute for identifying hard violations. Screening comes first.
- Before selection, the candidate set should include every actually generated short idea; do not report a complete 256-pool if 256 routes were issued but only 40 ideas were authored.

## 4. Selection steps

1. **64 independently seeded paths by default for four finalists**: create and record 64 real short concepts.
2. **Pre-gate review**: mark each idea `pass/fail/uncertain` on every hard requirement; identify duplicates. These count against the **first round's eliminated half**, not an extra unreported selection round.
3. **Round 1: 64 → 32** by fit, user value, feasibility and structural diversity. There must be 32 eligible, distinct entries; otherwise halt with `selection_complete=false`.
4. **Round 2: 32 → 16** by comparative design quality and differences.
5. **Round 3: 16 → 8** by deeper trade-offs and feasibility.
6. **Round 4: 8 → 4** by final portfolio/group budgets and role diversity; then elaborate and re-audit.

For 256→4 the full schedule is **256→128→64→32→16→8→4**, not the former quartering shortcut. For three finalists, choose 96 initial seeds: **96→48→24→12→6→3**. Each step must retain exactly half of the *planned preceding round*. If hard failures or duplicates leave fewer than the required half in round one, report the shortfall; never fabricate replacements or call a failed round complete.

## 5. Caveats and implementation

`funnel_select.py` performs structural checks on *provided* Agent reviews, excludes non-passes, deduplicates exact declared signatures, and uses deterministic diversity-aware reranking. It does not run a semantic evaluator, discover latent factual errors, or prove the idea objectively best. An independent reviewer or project tests should challenge finalists, particularly high-stakes or engine-specific constraints.

Do not confuse 256 independently sampled seeds with 256 actually written design concepts; claiming the latter requires recording each concept. Do not invent screening statistics. Do not claim an LLM-generated prose response is deterministic merely because route cards are replayable. Keep the seed separate from project/runtime simulation seeds.
