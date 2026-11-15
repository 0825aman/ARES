# 33 — Phase 4 Agent Specifications

**Project:** Multi-Agent Autonomous Researcher (MAAR)
**Phase:** 4 — Intelligence, Evidence Extraction, Fact-Checking and Citation Verification
**Status:** Complete

---

## Overview

Phase 4 introduces one new agent to the MAAR multi-agent system: the **Critic Agent** (also called the Reviewer Agent). This document specifies its design, inputs, outputs, decision logic, cycle-limit enforcement, and integration with the Supervisor.

The Critic Agent operates **only in multi-agent workflow runs**. The sequential workflow (Phase 2) does not invoke the Critic Agent.

---

## Agents in the MAAR System

| Agent | Phase | Scope | Description |
|-------|-------|-------|-------------|
| Planner Agent | Phase 3 | Multi-agent | Decomposes research question into structured tasks |
| Research Agent | Phase 3 | Multi-agent | Executes individual research tasks; collects and stores evidence |
| Supervisor Agent | Phase 3/4 | Multi-agent | Orchestrates the workflow; routes between all nodes |
| Critic Agent | Phase 4 | Multi-agent only | Reviews report quality; identifies unsupported claims, citation issues, contradictions |

---

## Critic Agent

### Location

```
maar/backend/app/agents/critic.py
```

### Purpose

The Critic Agent performs a holistic quality review of a completed research report. It evaluates:

1. **Evidence coverage** — are key claims backed by collected evidence?
2. **Claim support quality** — are high-impact claims well-supported?
3. **Citation integrity** — are source references traceable and accurate?
4. **Reasoning quality** — does the report logic follow from the evidence?
5. **Contradiction handling** — are contradictions between sources acknowledged?
6. **Source quality** — are peer-reviewed or authoritative sources used?

### Input

The Critic Agent receives a `ResearchWorkflowState` containing:

| Field | Type | Description |
|-------|------|-------------|
| `report_id` | `str` | ID of the finalized `ResearchReport` |
| `run_id` | `str` | Run context |
| `claim_ids` | `list[str]` | IDs of all extracted and verified claims |
| `verification_summary` | `dict` | Aggregated claim verification statistics |
| `critic_cycles` | `int` | Current review cycle count (starts at 0) |

### Output — `CriticReview`

The Critic Agent produces a `CriticReview` ORM record with the following fields:

| Field | Type | Semantics |
|-------|------|-----------|
| `overall_assessment` | `str` | `strong` / `adequate` / `weak` / `inadequate` |
| `review_status` | `str` | `approved` / `needs_attention` / `rejected` / `failed` |
| `recommended_action` | `str` | One of the 6 Phase 4 Supervisor decision values |
| `unsupported_claims` | `list[str]` | Claims with insufficient evidence (human-readable descriptions) |
| `citation_issues` | `list[str]` | Specific citation traceability problems |
| `contradictory_findings` | `list[str]` | Identified contradictions between sources |
| `missing_evidence` | `list[str]` | Evidence gaps that were not adequately addressed |
| `source_quality_issues` | `list[str]` | Low-quality or unverifiable source references |
| `reasoning_issues` | `list[str]` | Logical or interpretive problems in the report |
| `review_summary` | `str \| None` | 2–4 sentence narrative assessment |
| `review_version` | `int` | Incremented each review cycle for this run |

### Assessment → Recommended Action Mapping

| `overall_assessment` | Default `recommended_action` |
|----------------------|------------------------------|
| `strong` | `approve_report` |
| `adequate` | `approve_report` |
| `weak` | `revise_report` or `request_reverification` |
| `inadequate` | `revise_report` or `reject` |

The Critic Agent may recommend any of the 6 Phase 4 actions independently of assessment level.

---

## Critic Cycle Lifecycle

### Bounded Review Cycles

The Critic Agent runs at most **2 review cycles per run** (`CRITIC_MAX_REVIEW_CYCLES=2`).

```
finalize_report → claim_extraction_node → critic_node → supervisor_node
                                                   ↑              |
                      (if revise_report)           └──────────────┘
                                                   (cycle_count < 2)
```

### Cycle Limit Enforcement

When `critic_cycles >= CRITIC_MAX_REVIEW_CYCLES`:

- If the Critic's `recommended_action` is `revise_report`, `request_additional_research`, or `request_reverification`: the Supervisor routes to `needs_attention_terminal` or `reject_terminal` based on `overall_assessment`.
- If `overall_assessment` is `weak`: → `needs_attention_terminal`
- If `overall_assessment` is `inadequate`: → `reject_terminal`

**No forced approval ever occurs.** A run may reach `needs_attention` or `rejected` status at the cycle limit — it is never auto-promoted to `approved`.

### Failure Handling

If both LLM parse attempts fail:
- `review_status = "failed"`
- `overall_assessment = "weak"` (conservative fallback)
- `recommended_action = "mark_needs_attention"`
- Run is **not** blocked — continues to terminal node

---

## Supervisor Phase 4 Routing Decisions

The Supervisor handles 12 routing decisions in total. Phase 4 adds 6 new ones:

| Decision | Route to | Condition |
|----------|----------|-----------|
| `approve_report` | `citation_validation_node` | Critic approved the report |
| `request_additional_research` | `planning_node` | More evidence needed |
| `request_reverification` | `claim_extraction_node` | Claims need re-verification |
| `revise_report` | `finalize_report` | Report text needs revision |
| `reject` | `reject_terminal` | Report is fundamentally inadequate |
| `mark_needs_attention` | `needs_attention_terminal` | Issues noted but run continues |

### Phase 3 decisions (unchanged)

| Decision | Route to |
|----------|----------|
| `request_plan` | `planning_node` |
| `revise_plan` | `planning_node` |
| `execute_next_task` | `research_node` |
| `continue_research` | `research_node` |
| `complete_research` | `finalize_report` |
| `fail_workflow` | `fail_workflow` |

---

## Terminal Nodes

### `citation_validation_node`

Invoked when the Critic approves the report. Runs the citation validator service against all citations for this run. Sets `report.has_validated_citations = True` and `report.review_status = "approved"`.

### `reject_terminal`

Marks the run as `rejected`. Sets `report.review_status = "rejected"`. Issues are preserved in the `CriticReview` record for user review.

### `needs_attention_terminal`

Marks the run as `needs_attention`. The report is available but flagged with unresolved critic issues. Sets `report.review_status = "needs_attention"`.

---

## Shared Services Used by the Critic Node

The Critic Agent delegates to two workflow-independent shared services:

| Service | Description |
|---------|-------------|
| `claim_verifier.py` | Verifies atomic claims against evidence (zero `app.graph.*` imports) |
| `citation_validator.py` | Validates citation traceability chain (zero `app.graph.*` imports) |

Both services are callable from the sequential workflow and from LangGraph nodes.

---

## State Fields Added in Phase 4

```python
# ResearchWorkflowState additions (app/graph/state.py)

claim_ids: list[str]                 # IDs of extracted Claim records
verification_summary: dict           # {total, supported, contradicted, ...}
verification_depth: str              # "basic" | "thorough"
critic_review_id: str | None         # FK to latest CriticReview
critic_decision: str | None          # Last recommended_action from Critic
critic_cycles: int                   # Number of critic review cycles completed
citation_validation_passed: bool     # True after citation_validation_node succeeds
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CRITIC_MAX_REVIEW_CYCLES` | `2` | Maximum critic review cycles before terminal |
| `VERIFICATION_DEPTH` | `"basic"` | Default claim extraction depth for new runs |
| `MAX_CLAIMS_PER_RUN` | `20` | Cap on claims extracted per run; excess marked `unverified` |

---

## Testing

Critic Agent tests are in [`tests/test_critic_agent.py`](../backend/tests/test_critic_agent.py) (19 tests, prefix `CA-`).

Key invariants verified:

| Test | Invariant |
|------|-----------|
| `CA-07` | `approve_report` routes to `citation_validation_node` (not a terminal) |
| `CA-10` | Cycle limit forces `needs_attention_terminal` — never `citation_validation_node` |
| `CA-11` | Cycle limit with `inadequate` assessment → `reject_terminal` |
| `CA-19` | Critic LLM parse failure → `needs_attention`, run continues |

The `test_gr4008_no_forced_approval_at_cycle_limit` test in [`test_phase4_workflow.py`](../backend/tests/test_phase4_workflow.py) provides an explicit invariant test for forced-approval absence.
