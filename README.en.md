# Seeded Ideation

[简体中文](README.md) | **English**

> A reusable design workflow for AI agents — from a clear brief to an auditable design, with optional seed-driven exploration.

[![Tests](https://github.com/coicy/seeded-ideation/actions/workflows/tests.yml/badge.svg)](https://github.com/coicy/seeded-ideation/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Seeded Ideation** is a general-purpose design skill for AI agents. It guides problem framing, research, exploration, decisions, detailed specifications, verification, and handoff. It can support gameplay systems, software features, user interfaces, services, and creative content.

For tasks that benefit from divergent thinking, the **independent-seed exploration** mode assigns exactly one independent seed to each path, starts with at least 64 paths, and eliminates half of the candidates at each selection round. For a straightforward design improvement, skip the seeded funnel and work directly.

## Features

- **End-to-end design workflow:** Start from goals, context, and constraints instead of generating random ideas immediately.
- **Adaptive effort:** Choose `quick`, `standard`, or `rigorous`; seed-driven exploration is optional.
- **One seed per path:** Save manifests, generate paths in batches, and replay a single path.
- **Halving selection rounds:** Start from at least 64 independently seeded paths and retain exactly half per round according to the planned quotas.
- **Traceable decisions:** Keep hard requirements, preferences, assumptions, evaluations, and verification status distinct.

> **Important limitation:** The Python tools generate reproducible seeds, route prompts, and structural audit reports. **An AI agent must author and evaluate the actual design proposals.** Generating 64 seeds is not the same as generating 64 completed designs; a structural check does not prove design quality.

## When to use it

| Task | Suggested approach |
| --- | --- |
| Improve an existing UI, game rule, or software feature | `direct`: inspect the current design, then develop an implementable revision |
| Compare alternative design approaches | `compare`: explain structural differences, trade-offs, and acceptance criteria |
| Explore many distinct creative directions | Independent seeds + staged, half-at-a-time selection |
| Review a design specification | `design_audit.py`: inspect declared traceability and verification records |

## Quick start

### 1. Install as a Codex skill

Codex can discover user-level skills under `$HOME/.agents/skills/`. Clone this repository into a dedicated skill directory (Git required).

**macOS / Linux**

```bash
mkdir -p "$HOME/.agents/skills"
git clone https://github.com/coicy/seeded-ideation.git "$HOME/.agents/skills/seeded-ideation"
```

**Windows PowerShell**

```powershell
New-Item -ItemType Directory -Force "$HOME/.agents/skills" | Out-Null
git clone https://github.com/coicy/seeded-ideation.git "$HOME/.agents/skills/seeded-ideation"
```

You can then explicitly ask Codex to use the skill:

> Use `seeded-ideation` to propose four meaningfully different resource-management mechanics for my game. Preserve existing hard constraints, use independent-seed exploration, explain the selection process, and provide testable specifications.

For other agents supporting the Agent Skills format, install the repository in that agent's corresponding skills directory. See [Codex Skills documentation](https://developers.openai.com/codex/skills).

### 2. Run the Python utilities directly

Requirements: Python 3.9+ and Git for cloning. No third-party Python dependencies.

```bash
git clone https://github.com/coicy/seeded-ideation.git
cd seeded-ideation

# Plan the exploration: at least 64 independent seeds
python scripts/seed_ideation.py plan \
  --spec examples/four_ideas_funnel.json > plan.json

# Read the first batch of path-specific seeds and create route prompts
python scripts/seed_ideation.py batch \
  --spec examples/four_ideas_funnel.json \
  --plan plan.json --start 1 --format json > batch_001.json
```

These commands write **`plan.json`** (seed manifest and selection quotas) and **`batch_001.json`** (prompts for the first batch). They do **not** produce completed design concepts. An agent must author a candidate for each path, record requirement checks and scores, and then use the selector; see [Funnel and candidate format](references/FUNNEL.md).

## How it works

```text
User goals and constraints
          |
          v
Frame -> Research -> Design -> Decide -> Specify -> Verify & hand off
                       |
                  If breadth helps
                       v
             64+ independent seeds
                       v
                One seed / path
                       v
              Agent writes concepts
                       v
             Screen, dedupe, evaluate
                       v
                Keep half each round
                       v
                 Final proposals
```

For **four** finalists, the default schedule is **64 → 32 → 16 → 8 → 4**. For **three**, it is **96 → 48 → 24 → 12 → 6 → 3**, so the population halves exactly at every stage. If too few eligible candidates exist, the selector must report an incomplete funnel rather than invent missing candidates.

Replay one saved path:

```bash
python scripts/seed_ideation.py replay \
  --spec examples/four_ideas_funnel.json \
  --plan plan.json --start 35 --format json
```

For candidate schema, selection and evaluation details, see [Funnel reference](references/FUNNEL.md) and [Agent workflow](SKILL.md).

## Documentation and project layout

| Path | Purpose |
| --- | --- |
| [`SKILL.md`](SKILL.md) | Agent instructions and invocation workflow |
| [`references/DESIGN_WORKFLOW.md`](references/DESIGN_WORKFLOW.md) | Domain-neutral design stages |
| [`references/SPEC.md`](references/SPEC.md) | Request specifications and configuration |
| [`references/FUNNEL.md`](references/FUNNEL.md) | Independent seeds, selection, and scoring |
| [`references/DELIVERY_CONTRACT.md`](references/DELIVERY_CONTRACT.md) | Deliverable and acceptance requirements |
| [`examples/`](examples/) | Example briefs and design workbooks |
| [`scripts/`](scripts/) | Planning, batch, selection, and audit utilities |

## Testing and feedback

From the repository root:

```bash
python -m unittest discover -s tests -v
```

Automated tests cover **program behavior** including manifest integrity, independent paths, replay, exact-halving quotas, and structural audits. Real design value still requires task-specific evaluation.

Report bugs or suggest improvements via [GitHub Issues](https://github.com/coicy/seeded-ideation/issues). Maintained by [@coicy](https://github.com/coicy).

## License

Licensed under the [MIT License](LICENSE). Copyright © 2026 [coicy](https://github.com/coicy). Commercial use, modification, redistribution, and private use are permitted, provided the required copyright and license notices are retained. The software is provided **as is**, without warranty.
