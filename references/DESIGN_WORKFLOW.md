# Domain-neutral design workflow (v1.5)

## Purpose and boundary

This skill facilitates **design work**, not just idea lottery: framing a problem, investigating the current state, exploring or improving options, choosing a direction, describing an implementable solution, checking it, iterating, and handing off useful artifacts. It does **not** autonomously conduct user interviews, test a prototype, verify external facts, or manufacture user approval. Random seed prompts diversify exploration **when beneficial**, not by default for every task.

### Classify the actual job

First identify: **design target** (what will exist), **task verb** (create / redesign / diagnose / compare / refine / specify / review), **intended user**, **constraints and decision owner**, **requested output format** and **definition of success**. Decide whether the user needs *a design*, *multiple alternatives*, *a critique* or *a working implementation*. A design diagram does not substitute for machine-readable source, software functionality or working files.

If asked to update an existing design, establish its real structure, interface, behavior, references and constraints first; avoid treating a speculative visual concept as authoritative. Reference evidence must be from inspected sources. Separate facts, interpretations, assumptions and hypotheses. Existing design invariants remain in force unless the user authorizes changes.

## Modes (select proportionately)

| Mode | Typical request | Process | Evidence bar |
| --- | --- | --- | --- |
| `quick` | narrow improvement, one composition, simple content design | frame → one approach → describe → inspect → deliver | explicit scope, basic success checks; record when research is unnecessary |
| `standard` | substantial UI, gameplay, engineering design, service flow, writing campaign | frame → targeted discovery → compare (or `direct` if one solution required) → decide → detail → review → deliver | alternatives & tradeoffs, traceability, acceptance checks, honest test status |
| `rigorous` | high-impact, irreversible, complex system design | standard + competing models, counterexamples, hazard/edge cases, independent validation plan where possible | sourced claims, deeper test evidence, decision log and unresolved risks |

Use `design.mode` and `design.strategy` in the request spec (`direct` or `compare`). They govern **effort allocation**, not whether the user is allowed one idea. If the user explicitly wants one output, choose `direct`; if they explicitly request competing options, use `compare`. Do not demand an artificial random pool or interview when the task is clear. Escalate only if the user goal or risk merits it.

## Six stages and artifacts

### 1. FRAME — shared problem definition

Capture problem, audience, desired outcome, observed baseline, constraints (must / prefer / explore, and their sources), permitted redesign freedoms, exclusions, success criteria **with checks**, stakeholder/approval authority, open unknowns. For high-impact ambiguity ask one targeted question; otherwise use a documented reversible assumption. `brief_gate.py` can assist with requirement-specific missing inputs.

**Gate:** a designer can distinguish desired outcome from proposed solution and knows what would constitute failure. Do not convert user preferences to mandatory constraints.

### 2. EXPLORE — evidence and solution space

Gather relevant material: existing product/design records, actual user tasks, platform affordances, competitive analogues, operational constraints, engineering interfaces and known failures. Cite evidence in the design workbook. It is legitimate to state that external research was not necessary for a quick self-contained problem; do not simulate having read sources. State plausible alternative causal models and risks. When comparing options, change their *decision structure*, not labels/colors. Preserve a simple baseline option where useful.

**Optional creative branch:** when breadth/diversity is the bottleneck, use `seed_ideation.py plan`/`batch` and `funnel_select.py` to expand and select **real written ideas**. No route cards masquerading as ideas. For ordinary refinement, deterministic heuristic analysis, direct synthesis or two deliberate alternatives may be better. Store route IDs/seed in a separate appendix if used.

**Gate:** options satisfy the actual user brief or are marked incompatible; external findings are distinguishable from guesses.

### 3. DECIDE — justified trade-off

For each viable approach compare: user benefit, mechanism/structural difference, feasibility, dependencies, complexity, maintainability, known failure cases and fit with success criteria. Use scored ranking **only when criteria and the scale have meaning**; scores are subjective and not measured facts. Document what was rejected and why. An Agent can propose a preferred option; it must never claim user approval without real evidence. If the user has not selected among material alternatives, preserve the decision as `agent_proposal`.

**Gate:** chosen approach obeys must rules; the reasons for choosing it over alternatives are recoverable.

### 4. SPECIFY — an actionable design

Expand the chosen design into appropriate authoritative artifacts: e.g. component states and navigation flows; player actions and game system invariants; engineering APIs, data models and failure behavior; service blueprints; visual rules and asset specs; scenario writing or a content style guide. Each relevant artifact points to requirements and contains observable acceptance criteria; examine negative/edge cases and integration boundaries. Do not impose the same format on every domain. Provide actual requested source, editable structures or code when the user requested them, not just prose.

**Gate:** a different practitioner can implement, review or test the design without inventing major rules; each must requirement is linked to at least one concrete artifact.

### 5. VERIFY / ITERATE — challenge the proposal

Use the strongest *available* evidence: walkthrough, heuristic review, paper prototype, runnable model, unit or integration test, scenario simulation, user observation or accessibility check. Associate each acceptance criterion with `pass`, `fail`, `blocked` or `not_run`, method and evidence/issue. `pass` requires observed evidence; never use it for a speculative outcome. Revisions record issue → change → retest scope. Check unintended regressions against existing behavior. If tests are impossible, report unverified limits rather than inventing metrics.

**Gate:** every criterion has a truthful reported status. A structural audit pass does not imply verification passed. Failed or unexecuted tests may be handed off **only as draft/review-ready with remaining work**.

### 6. HANDOFF — what to use and what is still open

Provide the artifacts in the requested medium, their locations/versions, implementation/test notes, scope exclusions, remaining risks or unanswered questions, and decisions requiring user authorization. Output a concise summary to the user; archive the detailed record only when warranted. Never claim release, approval or production readiness from a proposal alone.

**Gate:** all design artifacts are findable; handoff status `draft`, `review_ready` or `validated` is honest. Only report `validated` after *all* declared acceptance checks passed with evidence. User approval is a separate fact, recorded only with source evidence.

## Loops and re-entry

- New factual constraint → FRAME and update requirement sources, then rescreen affected alternatives.
- Same options ineffective → EXPLORE another axis (seed may help).
- Selected direction infeasible → DECIDE again, compare alternatives.
- Detail reveals contradictions → SPECIFY and adjust traceability.
- Test failure → record defect, revise affected artifact, VERIFY again (plus regression set).
- A follow-up design request may enter at any stage; reuse prior approved decisions, but do not assume approval from chat suggestions.

## Prevent bureaucracy and false confidence

- **No universal 256**: use a large pool only for broad divergent design. No candidate pool is needed to fix a known issue or implement an agreed spec.
- **No mandatory research theater**: quick tasks may document a reason for skipping discovery.
- **No fixed game/UI vocabulary**: choose domain-specific checklists only for the user's actual target.
- **No ungrounded approval**: distinguish `agent_proposal` from `user_approved`, no inferred approval.
- **No fabricated experiments**: real tests need logs or reproducible observations; structural checks only validate record completeness.
- **No automatic redesign of existing behavior**: first understand original affordances/structure; changes must be within the current user's requested scope.

## Structured record

See `references/DELIVERY_CONTRACT.md` for a sample `workbook.json` shape and `scripts/design_audit.py` gates. A JSON record is optional for brief prose answers and useful for reusable multi-stage projects. The audit is a **mechanical, declared-evidence checker**, not a semantic expert system. The reviewer must challenge unsupported evidence and the design's actual utility.
