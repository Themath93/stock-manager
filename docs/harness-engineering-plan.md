# Harness Engineering Plan (Logic-Safe)

Goal: improve agent friendliness (harness maturity) without changing trading business logic.

Working rule:
- Allowed: docs, maps, checklists, CI quality gates, developer workflow metadata.
- Not allowed in this plan phase: strategy/order/risk/pipeline execution behavior changes.

## Phase 0 - Baseline and Scope Lock

Deliverables:
- Baseline audit snapshot (latest harness score and key weaknesses).
- Scope lock note: "no trading logic modifications".

Exit criteria:
- Team agrees this cycle is documentation and harness hardening only.

## Phase 1 - Knowledge Map Foundation (Current)

Deliverables:
- `docs/knowledge-map.md` (entry points, boundaries, flow, invariants, verification map).
- `docs/harness-week1-execution-plan.md` (week-1 actionable plan with done criteria and evidence).
- Entry-point links from root guidance docs.

Exit criteria:
- New contributor/agent can locate run path and module ownership within 2 jumps.

## Phase 2 - Entry Point Hardening

Deliverables:
- Root docs alignment pass (`README.md`, `AGENTS.md`, `CLAUDE.md`) for stale links and missing pointers.
- Minimal "where to start" section for each core area (CLI, trading, adapter, persistence).

Exit criteria:
- No broken internal doc links in entry docs.
- Agent entry instructions and actual repo structure are consistent.

## Phase 3 - Invariant Enforcement Visibility (No Logic Change)

Deliverables:
- CI quality matrix doc: which gates run in CI (lint/type/test/build).
- Gap list and rollout plan for missing gates.
- Optional pre-commit profile proposal (documentation-level first).

Exit criteria:
- Every required invariant has an explicit "where enforced" location.

## Phase 4 - Progressive Disclosure and Knowledge-in-Repo

Deliverables:
- `docs/` index map (overview -> module docs -> deep references).
- ADR bootstrap (`docs/adr/README.md` + first 2 ADRs for major decisions already in code).

Exit criteria:
- Key architecture decisions are discoverable in-repo without tribal knowledge.

## Phase 5 - Maintenance Loop

Deliverables:
- Monthly drift checklist (broken refs, stale sections, command validity).
- Quarterly harness re-audit template and target score tracking.

Exit criteria:
- Documentation drift is measured and regularly corrected.

## Priority Backlog (Quick Wins)

1. Fix broken/stale links in root docs.
2. Add CI quality-gate visibility table.
3. Add module-level "entry notes" for core directories.
4. Add ADR index and initial records.

## Success Metrics

- Navigation latency: core task entry path found within 2 link hops.
- Drift count: broken internal links reduced to zero in root docs.
- Harness score target: move from current L3 band toward L4 threshold (60+).

## Non-Goals for This Cycle

- No strategy algorithm tuning.
- No order execution path refactor.
- No risk-rule parameter changes.
- No persistence format changes.
