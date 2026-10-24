# Request specification (v1.5; backward-compatible)

The skill accepts a short natural-language request (`--request`) or a JSON spec (`--spec`). A spec is strongly recommended when quantities or multiple constraints matter, but the skill does not require a project-specific contract for ordinary creativity.

```json
{
  "request": "The CURRENT user request (verbatim or faithfully summarized)",
  "context": {"summary": "Existing project, optional", "references": ["Known docs, optional"]},
  "requirements": [
    {"id": "R1", "text": "Must produce 20 items", "level": "must", "source": "user"},
    {"id": "R2", "text": "Prefer viable variants", "level": "prefer", "source": "user"},
    {"id": "R3", "text": "Explore more dramatic mechanics", "level": "explore", "source": "user"}
  ],
  "freedoms": [
    {"id": "axis-a", "name": "Interaction design", "description": "May change interaction mechanics"},
    {"id": "axis-b", "name": "Feedback structure", "description": "May vary how results become visible"}
  ],
  "deliverables": {
    "items": 20,
    "variants_min": 2,
    "variants_max": 3,
    "min_distinct_positions": 8,
    "max_new_attributes": 7
  },
  "unknowns": ["Facts worth verifying rather than silently assuming"]
}
```

All fields other than `request` are optional. `requirements.level` is `must`, `prefer` or `explore`; `requirements.source` is `user`, `reference` or `inferred`. Use `user` only when grounded in the user's actual current instructions. Do not disguise an inferred preference as explicit. A spec does not itself become an authoritative project decision.

Quantitative validator input `items.json`:

```json
{
  "items": [
    {"id": "idea-01", "position": "resource allocation",
     "variants": ["A", "B"], "new_attributes": ["moisture"]}
  ]
}
```

The validator measures only exact declared values. It cannot verify whether "resource allocation" actually differs mechanically from other position labels. For a user request with `max_new_attributes`, count unique attribute identifiers **globally** across all ideas. Do not change to "per item" or silently use the maximum.

`new/replay/mutate` default `--count` from `deliverables.items`. This draws an independent random seed for each route card; the AI still must create the final design from the route cards. For a very large requested item count, agents may group candidates into batches without changing the required final quantity.

### Precedence examples

1. Existing game + "add 20 cards without breaking rules": preserve identified rules, design 20 cards, new attributes only if user permits.
2. Existing game + "redesign the entire progression system": the redesign request authorizes exploring changed rules; old progression is context, not immutable.
3. "At most 7 extra fields": a bound of 0 through 7, not a target of 7 or a rule requiring 0.
4. "Keep the skill general": no project-specific names, mechanisms or document layout can be hard-coded as normative constraints.
5. Conflicting references: verify newest relevant sources and describe the conflict; current user-requested modifications take precedence in the proposed design, without claiming unapproved project edits are completed.

## Large-pool staged selection (v1.3)

Optional top-level `ideation` fields:

```json
"ideation": {
  "pool_size": 256,
  "batch_size": 32,
  "require_full_pool": true
}
```

`pool_size` describes **initial short concepts to be actually generated**, not just seed prompts. `require_full_pool` asks the mechanical selector to refuse incomplete input when the chosen pool budget is required. Unless set, the default planning budget is `min(256, deliverables.items * 16)` and the default batch is 32. A user-specified 256/4 plan creates **256 independent cryptographically sampled seed values, each bound to exactly one route**, organized into eight batches of 32 routes. Candidate pools for `funnel_select.py` use the separate schema in `references/FUNNEL.md`; the old `validate` command applies to the **final output** after elaboration. The same global max-new-attributes rule is checked across the selected finalists.

## Requirements interview v1.4

A substantial creative search SHOULD add optional `elicitation` data with evidence-backed facts. The `brief_gate.py` tool supports domain-appropriate prompts without making them binding constraints:

```json
"elicitation": {
  "domain": "cards",
  "facts": {
    "deliverable_interpretation": {"status":"unknown"},
    "desired_outcome": {"status":"confirmed","value":"emergent decision-making","source":"user","evidence":"user explicitly requested emergent designs"},
    "cards_variants": {"status":"unknown"}
  },
  "relevance": {"cards_variants":"high","cards_theme":"low"}
}
```

Statuses `confirmed` and `delegated` require evidence of a user/reference response; `inferred` is provisional. An `unknown` high-priority slot needs clarification. Ask one highest-impact question rather than sending a blanket questionnaire. See `references/ELICITATION.md`. Project/domain question banks are optional reusable prompts, not a fixed game contract.

## General design workflow profile (v1.5)

Optional `design` object: `{"mode":"quick|standard|rigorous", "strategy":"direct|compare"}`.

* `quick`: narrow and self-contained, does not require unnecessary research or many alternative directions.
* `standard`: weigh credible alternatives where appropriate, specify traceable design artifacts, document evaluation.
* `rigorous`: more evidence and deeper risk / edge-case testing, still no fabricated experiments or approvals.
* `direct`: one requested design path, no artificial requirement for multiple options.
* `compare`: meaningful alternatives with documented rejections/choices.

This profile is optional and does not change seed replay, legacy funnel or old structural final validation. `scripts/design_audit.py` validates an optional separate design workbook as described in `references/DELIVERY_CONTRACT.md`.

## Independent seed identity contract (v1.6)

- One independently sampled seed (`ALPHABET` characters, 4–64 long; default 16) ⇔ one numbered creative exploration path. A batch is a collection of different seeds and never a single seed branching into several routes.
- `plan` generates P seeds using `secrets` and writes all of them into `paths`. It does not expose any master seed. For replay, save **all of plan.json**. Re-running `plan` intentionally creates fresh independent seeds.
- `batch --plan plan.json --start N` reads the stored seeds (usually 32 at a time). `replay --plan plan.json --start N` reproduces exactly that route; `replay --seed S` reproduces a single route with seed S. The path's index is an identifier, not an entropy source; same seed+spec+version yields same association independent of numeric path ID.
- `new --count N` draws N independent seeds. `mutate --seed S` outputs a single changed seed and single changed path; it does not create a multi-route family.
- `pool.json` candidates include `path_number`, `seed` and `seed_fingerprint` from `plan.json`. Run `funnel_select.py --plan plan.json` to reject mismatches, duplicate/reused seeds and duplicate path assignments. This confirms **declared linkage only**, not that LLM actually followed the seed.
- The recorded manifest fingerprint is an accidental-corruption check, **not** a cryptographic signature or evidence of independent semantic diversity.
- **Migration:** v1.5 `plan --seed` and `batch --seed` are intentionally rejected. Recreate a manifest; do not disguise one legacy seed split across many old routes as independently sampled seeds.
