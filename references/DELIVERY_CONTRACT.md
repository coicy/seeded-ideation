# General design record and structural audit (v1.5)

Store a request specification (existing `references/SPEC.md`) and an optional `workbook.json`. The record is **cross-domain**: an artifact can be a UX wireframe, level design, GDD, interface contract, component library, illustration brief, document, marketing campaign, API design, or any other task-defined output. Fields describe *traceability and verification*, not an enforced design format.

## Spec extensions (backward compatible)

```json
{
  "request": "Redesign navigation for a support knowledge product",
  "design": {"mode": "standard", "strategy": "compare"},
  "requirements": [
    {"id":"R1", "text":"Existing bookmarks remain reachable", "level":"must", "source":"user"}
  ]
}
```

`mode`: `quick` / `standard` / `rigorous`; `strategy`: `direct` (one concrete direction) or `compare` (alternatives). Defaults are `standard` and `compare` only **for the optional audit**; legacy `plan`, `batch`, `funnel_select`, `validate` remain unchanged. For clear requests with only one desired result, choose `direct` explicitly. No new field is required by the old commands.

## Workbook schema (author-declared evidence)

```json
{
  "brief": {
    "problem": "Concrete problem, not a preselected solution",
    "users": ["Who uses this design"],
    "outcome": "Outcome the design must enable",
    "success_criteria": [{"id":"S1", "criterion":"Users can complete task", "method":"Walk through task scenario"}],
    "scope": {"in":["Current redesign"], "out":["Excluded future work"]},
    "assumptions": [{"id":"A1", "text":"Unverified assertion", "status":"unverified", "validation":"How to check"}]
  },
  "discovery": {
    "findings": [{"id":"F1", "claim":"Finding", "source":"observation", "evidence":"Exact source or reproducible observation", "confidence":"medium"}],
    "not_needed_reason": "Use only when intentionally skipping external discovery"
  },
  "concepts": [
    {"id":"C1", "summary":"Approach", "principle":"How it differs",
     "tradeoffs":{"benefits":["Benefit"],"costs":["Trade-off"]},
     "requirement_checks":{"R1":{"status":"pass","evidence":"Why R1 is preserved"}}}
  ],
  "decision": {"selected":["C1"], "rationale":"Why", "rejected":[],
               "authority":"agent_proposal"},
  "specification": {"artifacts":[
    {"id":"D1", "name":"Navigation contract", "type":"flow-spec",
     "content":"Concrete design OR use location for a produced artifact",
     "requirements":["R1"],
     "acceptance":[{"id":"AC1", "criterion":"Bookmarks resolve", "method":"Integration test"}],
     "edge_cases":["Stale bookmark"]}
  ]},
  "verification": {"results":[
    {"acceptance_id":"AC1", "status":"not_run", "method":"Integration test", "issue":"No running application available"}
  ]},
  "handoff": {
    "status":"draft", "summary":"What has actually been designed",
    "deliverables":[{"artifact_id":"D1", "location":"docs/navigation.md"}],
    "remaining_work":["Run integration test and review with stakeholders"]
  }
}
```

* If discovery is unnecessary, leave `findings` empty and supply `not_needed_reason`. Do not invent findings.
* For every **must** requirement in the spec, each concept has `requirement_checks[ID]` with status `pass`/`fail`/`uncertain` and evidence. The selected concept may only use `pass` supported by a nonblank explanation; this is a *declaration* requiring human judgment, not proof.
* Every *must* requirement must trace to at least one concrete design artifact; each artifact declares an observable acceptance criterion (globally unique `id`). Artifacts may contain inline `content` or a nonempty `location` for an actual file. `design_audit.py` does not check whether a claimed location exists.
* Verification results must enumerate every acceptance ID. Status may be `pass` (nonempty evidence), `fail`, `blocked` or `not_run` (each nonpass with an `issue` explaining why). `verification_status=declared_pass_review_required` is a truthful name: even all-green self-reports are **not** independent proof.
* Handoff status `validated` is prohibited unless *all* acceptance checks are declared passed. A design can be delivered as `draft` or `review_ready` with explicit remaining work.
* `decision.authority=user_approved` requires `approval_evidence` pointing to an actual user instruction/decision. A preference inferred by an Agent is not approval.
* In multi-option comparisons, the record must include reasons for every discarded option; when no comparison is warranted use `design.strategy=direct`.
* The optional workbook should be modest for lightweight tasks. The output artifact need not be a JSON document; JSON is merely the audit trail.

## CLI

```bash
# Stop at your current stage to audit incrementally, without requiring future documents.
python scripts/design_audit.py --spec examples/general_design_spec.json \
  --workbook examples/general_design_workbook.json --through frame
python scripts/design_audit.py --spec examples/general_design_spec.json \
  --workbook examples/general_design_workbook.json --through specify
python scripts/design_audit.py --spec examples/general_design_spec.json \
  --workbook examples/general_design_workbook.json --through handoff \
  --output audit_report.json
```

Exit code 0 means *structure passed for declared stage(s)*; 1 means missing/inconsistent declarations. Warnings indicate review issues but do not automatically fail the structural check. CLI returns `verification_status` separately. Do not cite a CLI exit 0 as design correctness, real tests passed, or user sign-off.
