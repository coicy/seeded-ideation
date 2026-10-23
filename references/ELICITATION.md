# Requirements interview and question policy (v1.4)

## Why this exists

Prior versions could accurately filter a pool against the wrong specification. **A good funnel cannot recover an omitted user constraint.** The agent must identify decision-critical gaps *before* generating a pool. The skill stays domain-neutral: card questions are optional domain prompts, not assumptions or fixed rules.

## Mandatory for substantial, multi-stage ideation

1. Read the **current user request**, relevant earlier user clarifications and (when applicable) authoritative project context. Extract what is explicitly answered. Never ask something already resolved in the user's conversation or documents.
2. Write a *provisional* spec with a `elicitation` section. Each relevant slot has a status: `confirmed` (user or relevant reference with evidence), `inferred` (agent guess, not permission), `delegated` (user explicitly told us to decide it, cite the delegation), `unknown` or `not_applicable` (with explanation). Do **not** mark an answer confirmed merely because an AI previously guessed it.
3. Consider impact of being wrong: Would plausible interpretations produce *different artifacts, rule systems, evaluation criteria or quantity*? If yes, set `elicitation.relevance[slot]="high"`. If question is irrelevant, set `"irrelevant"` with justification in a separate project brief. Template `critical` slots are default blockers unless confirmed, delegated, or explicitly not applicable.
4. Run `python scripts/brief_gate.py --spec your_request.json --max-questions 1`. If it says `needs_clarification`, **ask the single highest-impact question**, answer pending user reply, then update the spec and re-run. In exceptional situations where multiple *independent* answers are absolutely needed to proceed and one brief exchange is easier, ask two, but never dump an eight-item questionnaire. Do not ask purely optional questions reflexively.
5. If user says “you decide”, “surprise me” or “don't ask”, resolve using `delegated` with precise evidence; choose explicit design assumptions, label them assumptions, and continue. Never invent a grant of freedom.
6. When ready, run `python scripts/seed_ideation.py plan --spec ... --require-ready`. The plan/batch commands check the brief gate automatically whenever `elicitation` is present. The old simple CLI remains usable for fast/lightweight brainstorming, but agents still must understand the request.
7. Re-open the brief **after broad candidate generation** if 30–50% of candidates fail for the same undefined condition, if the best outcomes require an unasked design choice, or if mutually contradictory plausible readings are discovered. Ask one follow-up, do not retroactively change the user request to fit the generated pool.
8. At final delivery, disclose relevant assumptions and distinguish user requirements from self-chosen solutions. Final candidates must obey both hard constraints and the requested *experience objective*. No amount of novelty offsets absent requirements.

## Requirements vs preferences vs freedoms

- **Hard requirement**: directly stated by user, or truly necessary documented existing behavior where user requested consistency. No-go if violated.
- **Preferred target**: guides scoring; need not be frozen as a `must`.
- **Freedoms**: aspects the user left open or explicitly asked to redesign; don't collapse them to arbitrary fixed defaults.
- **Missing high-impact content requirement**: ask before 256-way ideation rather than assuming (e.g. does “4 groups” mean four alternative decks, four synergistic sets or 20 cards partitioned into four categories?).
- **Minor omission**: agent can make a provisional creative choice, visibly stated, and proceed.

## Domain-specific prompts only when useful

The generic question bank is `references/question_banks/generic.json`. Optional banks: `cards.json`, `ui.json`, `software.json`, `writing.json`. The same reusable engine reads all of them and does not make special rules for cards. If a bank question was already answered in earlier context, record it as such and *do not ask again*. When a domain isn't represented, use generic slots and freely record extra questions in the conversational brief.

### Game card design: the questions we previously missed

- **Deliverable structure:** Does four groups mean four competing deck concepts, four interlocking sets, or a 20-card pool partitioned into four groups? Counts / variants belong to *each group* or the final set?
- **Desired play experience:** Is the user seeking emergent storytelling, strategic combos, player control, encounter variety, risk management, etc.? Which is essential, not merely a possible implementation?
- **Card roles and coverage:** Which missing player decisions and gameplay functions should new cards add, versus which old roles should not be duplicated?
- **Composition:** Must cards form combos, work independently, or connect via shared events? Is cross-group synergy desirable?
- **Variant meaning:** Are 2–3 variants mutually exclusive design alternatives, upgrades within one game, or separate collectible/physical card instances?
- **Implementation boundary & balance:** Which present rules must stay; how strong/complex may expansions be? Don't turn a permission such as “at most 7 new attributes” into “must be 0”.
- **Theme & presentation:** Ask only when necessary to decide art direction or game feel, not as a mandatory interview obstacle.

## Illustrative workflow

```bash
python scripts/brief_gate.py --spec examples/cards_brief_missing.json --max-questions 1
# Ask user about the highest-impact unresolved meaning, not all questions.
# Update facts with grounded answers; create a ready brief, then:
python scripts/brief_gate.py --spec examples/cards_brief_resolved_example.json --enforce
python scripts/seed_ideation.py plan --spec examples/cards_brief_resolved_example.json --require-ready --pool-size 256
```

The example with resolved answers is *hypothetical* to demonstrate control flow. It is **not** a claim that the real user gave those answers.

## Implementation limitations

This script is **not** a semantic language model. It checks the presence of documented status, value, evidence, source and question relevance. The agent still has to infer what is missing using the current conversation. It must not create fake evidence to force a `ready` result. No answer should be treated as a binding product decision merely because it appears in a generated JSON specification.
