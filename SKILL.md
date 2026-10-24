---
name: seeded-ideation
description: "General design workflow for framing, researching, ideating, comparing, specifying, verifying, iterating and delivering work across games, software, UX, services, visual design, content and other domains. Seeded creative exploration is optional, with auditable constraints and evidence."
compatibility: "Python 3.9+, standard library only. No network required."
---

# Seeded Ideation v1.5 — 通用设计工作流 · 可选随机创意探索

## Guiding principles

**用户定义目标与边界；种子负责拓展可探索的联想；筛选负责删去不合格、重复和价值较低的候选。**

The final output must be selected from **actual generated ideas**, not merely from seed route cards. A route card is a prompt, **not** an idea. Do not claim "256 candidates explored" if only 256 character prompts were generated. Do not generate 256 full GDDs just to discard 252: initial candidates should be concise, progressively elaborate only survivors.

The skill is **domain-neutral**. Existing project rules must be interpreted in light of the current user request. Never import game-specific constraints, or treat a user preference as an immutable requirement. Equally, do not use high wildness as a license to override the user's instructions.

## Primary workflow: design from problem to deliverable

**Do not automatically start with random ideation.** Determine whether the request is to create a design, modify an existing design, critique one, compare alternatives, or implement an agreed design. Select `quick`, `standard`, or `rigorous` effort; choose `direct` for one desired solution or `compare` for genuine alternatives. See `references/DESIGN_WORKFLOW.md`. Existing user/project sources are authoritative only to the extent actually inspected and applicable.

1. **FRAME**: define actual user problem, audience, current state, desired outcome, scope, must/prefer/explore constraints and their provenance, acceptance/success criteria. Ask only when an unresolved choice materially prevents progress; otherwise record a reversible assumption. Use `brief_gate.py` for a substantial unresolved brief.
2. **EXPLORE**: inspect source designs and relevant evidence, identify gaps and alternatives. If requested breadth, novelty or divergent mechanisms make randomness useful, invoke the *optional* seed/funnel subworkflow below. Otherwise use direct design synthesis, systematic variation or a short comparison. No fabricated research, no mandatory 256 candidates.
3. **DECIDE**: compare compliance, user value, technical and creative tradeoffs, implementation/maintenance cost and risk; note rejected options. Distinguish an Agent recommendation from **actual user approval**. Do not turn a proposed direction into a binding product decision.
4. **SPECIFY**: produce the requested *real* output (design spec, diagrams/source, rules, flows, interface contracts, working code, assets, etc.) at sufficient precision for use. Link mandatory requirements to artifacts, define observable acceptance criteria and cover failure/boundary cases.
5. **VERIFY AND ITERATE**: walkthrough, test, prototype, simulate, review or explicitly mark verification pending. When tests fail, revise affected design and rerun relevant checks. `pass` needs observed evidence, not optimism; machine structural checks are not semantic or empirical validation.
6. **HANDOFF**: provide actual artifacts and locations, tradeoffs, changes, unresolved items, tests and next actions. Use honest statuses `draft`, `review_ready` or `validated`; never claim validated if acceptance remains untested. Save a detailed audit record when the size/risk justifies it.

Use `scripts/design_audit.py` with the optional cross-domain `workbook.json` when the task is substantial or needs traceability:

```bash
python scripts/design_audit.py --spec examples/general_design_spec.json \
  --workbook examples/general_design_workbook.json --through specify
python scripts/design_audit.py --spec examples/general_design_spec.json \
  --workbook examples/general_design_workbook.json --through handoff
```

For one simple self-contained design, `examples/quick_design_spec.json` + `examples/quick_design_workbook.json` illustrate a lightweight direct path. A passed structural audit means *declared fields and links are present*, **not** that a design is correct, a prototype was run, or a user approved it. See `references/DELIVERY_CONTRACT.md`.

### Optional divergent branch: seed → candidate pool → funnel

Use this only when the user wants *multiple meaningfully different proposals*, or the goal demonstrably benefits from broader exploration. Preserve v1.4 commands and reproducible seed routes; the old workflow below describes this **subprocess**, not an obligation on every design request.

## Divergent ideation subworkflow (for multiple candidate proposals)

1. **Understand request and interview before ideation**: extract the deliverable count `K`, current request, references, explicit `must` constraints, `prefer` criteria, allowed freedoms, unknowns. Fetch relevant project context when necessary. Write a provisional request spec; see `references/SPEC.md` and **`references/ELICITATION.md`**. Before any substantial pool, inspect which design-defining answers are still missing and ask the smallest number of high-impact questions, usually **one per turn**. Do not assume what a group means, what experience the user wants, or how variants are used. Read earlier answers before asking again. Validate readiness with `python scripts/brief_gate.py --spec request.json --max-questions 1`. The latest user request determines whether earlier behavior is preserved, extended or replaced.
2. **Define rejection criteria only AFTER the brief is sufficiently resolved**: distinguish hard no-go conditions, merely inconvenient dependencies, and soft preferences. Include global budgets (e.g. total new attributes across finalists). Do not invent hard constraints.
3. **Choose a pool size**: `P >= K`. For demanding high-diversity tasks, a large funnel like **P=256, K=4** is reasonable when time/context permits. For small tasks use a smaller factor (e.g. 8–16×) or a progressive expansion. **256 is an illustrative budget, not a universal obligation.** User-specified P wins when practicable; disclose if resources require a smaller pool. Record actual pool size, not the planned number.
4. **Create one seed and route plan**:
   ```bash
   python scripts/seed_ideation.py plan --spec request.json --require-ready --pool-size 256 --batch-size 32 --wildness 5 > plan.json
   ```
   This outputs the seed, planned candidate count and eight batch ranges. No candidate *ideas* exist yet.
5. **Generate the ideas in batches**: for each plan batch, run `batch --seed ... --spec request.json --pool-size 256 --batch-size 32 --start 1`, then starts 33, 65, ..., 225. Every route specifies a global ID and seed-character association. The Agent must produce **one or more original brief concepts per chosen route**, at least one per planned index if claiming the full P. A concise concept includes title, one-sentence mechanism, user value, differentiation axis and main dependency. Distinguish ideation stage from final detailed variants. Capture results in `pool.json` without silently omitting weak candidates.
6. **Semantic MUST screening**: for each candidate, judge *each* current hard requirement as `pass`, `fail` or `uncertain`, with a short concrete justification. Only `pass` with evidence may survive. `fail` or `uncertain` are excluded from selection and require rework or verification, rather than being transformed into vague conditions. This is **not** automated natural-language reasoning: the Agent supplies evidence; users can inspect it.
7. **Deduplicate, cluster, rerank**: remove identical mechanism signatures; cluster look-alike solutions even when named differently. Score each remaining candidate 0–5 on relevance/fit, user value, feasibility and novelty, grounded in the actual request. Avoid optimizing novelty at the expense of usefulness. Choose diverse finalists using mechanism tags and user-required role diversity. See `references/FUNNEL.md`.
8. **Select down through explicit gates**: for P=256, K=4, a default funnel is **256 → 64 → 16 → 4** (with failures/dedup possibly reducing the actual first stage). Use `scripts/funnel_select.py` to audit fail-closed requirement checks, counts, duplicates and a *heuristic* diversity rerank. Ensure global selected-set constraints (not individual-only constraints) are satisfied. If there are fewer than K suitable candidates, generate a fresh batch focused on missing directions and screen them again, or report the shortfall. **Never invent four compliant options to fill a quota.**
9. **Re-check the user brief when selection exposes a gap**: if many ideas rely on the same unanswered question, the best finalists represent incompatible interpretations, or user goals were under-specified, stop and ask one key follow-up. Do not treat an inferred choice as a newly approved requirement.
10. **Elaborate survivors only**: write detailed proposals and requested variants for the selected K. Rerun the full semantic requirement audit because elaboration can introduce conflicts. `validate` checks declared output counts and budgets; it does NOT prove correctness.
11. **Report a lightweight audit trail**: seed, spec fingerprint, P planned / P actually generated, hard-fail / uncertain / duplicate counts, stage sizes, why finalists beat alternatives, and unresolved doubts. The user normally receives only K polished results plus a brief selection summary; save or attach raw pools only if useful/requested.

## Commands

```bash
# First audit missing user inputs. This is BEFORE generating route prompts or 256 ideas.
python scripts/brief_gate.py --spec examples/cards_brief_missing.json --max-questions 1
```


```bash
# Create seed and multi-batch plan. A plan is NOT a finished pool. If user-critical unknowns remain, stop and ask. `--require-ready` also checks the brief gate before execution.
python scripts/seed_ideation.py plan --spec examples/four_ideas_funnel.json --wildness 5 > plan.json

# Generate deterministic route prompts for each batch; use seed from plan.json.
python scripts/seed_ideation.py batch --seed 'K7M2-8QVA-T3XP-H6RD' --spec examples/four_ideas_funnel.json --start 1 --format json > batch_001.json
python scripts/seed_ideation.py batch --seed 'K7M2-8QVA-T3XP-H6RD' --spec examples/four_ideas_funnel.json --start 33 --format json > batch_033.json
# ... 65, 97, 129, 161, 193, 225

# Feed the generated *idea* pool and documented evaluations, not route cards.
python scripts/funnel_select.py --spec examples/four_ideas_funnel.json --candidates pool.json --output selection_report.json

# Expand the 4 chosen proposals and validate final deliverable structure.
python scripts/seed_ideation.py validate --spec examples/four_ideas_funnel.json --candidates final.json
```

Existing `new`, `replay`, `mutate`, `validate` commands remain available. `batch` never mutates the seed; separate batch calls with the same spec and seed have stable global numbering. Script replay is deterministic for route prompts, **not** for language-model creative outputs or subjective ratings.

## Critically important distinctions

- **Constraint screening precedes ranking**. A beautiful but incompatible idea is rejected, not awarded a low penalty and kept.
- **Compliance and scoring are different**. `pass` only means the reviewing Agent gave a specific evidence claim; it must be rechecked and is not a mechanical proof.
- **User scope remains authoritative**. An allowed extension can be a viable solution, but a change the user forbade is rejected. Do not silently narrow or broaden the request.
- **Large pool != quality guarantee**. 256 similar superficial name changes do not produce 256 meaningfully distinct approaches. Branch deliberately along relevant design axes.
- **Fairness of diversity**. A diversity heuristic cannot assess semantic differences reliably from tags alone; review near-duplicates manually, including across different groups.
- **No post-hoc fabrication**. The audit must never state an exploration count above the actual recorded pool, or invent score justifications.
- **Practical budget**. At very large P, write very short concepts; discard weak ideas early and spend tokens on finalists. If the user needs only a fast answer, use a smaller P and say so.

## Files

- `scripts/design_audit.py`: staged cross-domain design traceability and honest verification-status audit.
- `references/DESIGN_WORKFLOW.md`: quick/standard/rigorous design lifecycle and re-entry loops.
- `references/DELIVERY_CONTRACT.md`: optional project workbook, criterion traceability, handoff schema and CLI.
- `scripts/seed_ideation.py`: optional seed, plan, reproducible prompt batches, replay/mutate, structural final validation.
- `scripts/brief_gate.py`: evidence-based missing-requirement audit and high-impact question queue; it does **not** understand semantics on its own.
- `references/ELICITATION.md`: compact question policy, status provenance, and on-demand domain banks.
- `scripts/funnel_select.py`: hard-gate evidence presence, duplicate-signature cleanup, multi-stage heuristically diverse selection.
- `references/SPEC.md`: cross-domain request spec and numeric constraints.
- `references/CREATIVE_METHOD.md`: seed associations and semantic review.
- `references/FUNNEL.md`: selection rubric, candidate schema and worked 256 → 4 flow.
- `examples/four_ideas_funnel.json`: generic example, not a fixed project contract.
- `tests/`: regression tests.
